import yaml
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langchain_openai import AzureChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import initialize_agent, AgentType, AgentExecutor


# --- 1. 設定管理 (從 config.yml 檔案讀取) ---

# 取得當前腳本所在的目錄
# Path(__file__) 會取得當前檔案的絕對路徑
# .parent 會取得該檔案所在的資料夾路徑
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_mcpclient.yml"

class Settings(BaseModel):
    """應用程式的設定模型"""
    azure_api_key: str
    azure_api_version: str
    azure_endpoint: str
    judge_deployment_name: str
    agent_deployment_name: str

def _load_settings(path: Path) -> Settings:
    """從指定的路徑載入 YAML 設定檔並驗證"""
    if not path.is_file():
        # 如果設定檔不存在，拋出一個明確的錯誤，並提示使用者如何建立
        raise FileNotFoundError(
            f"設定檔不存在於: {path}\n"
            f"請在專案根目錄建立一個 'config_client.yml' 檔案，並填入必要的設定。"
        )
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return Settings(**config_data)
    except yaml.YAMLError as e:
        # 如果 YAML 格式錯誤，提供錯誤訊息
        raise ValueError(f"設定檔 '{path}' 格式錯誤: {e}")
    except Exception as e:
        # 捕捉其他可能的錯誤，例如 Pydantic 驗證失敗
        raise ValueError(f"載入設定檔 '{path}' 時發生錯誤: {e}")

# 在應用程式啟動時載入設定
settings = _load_settings(CONFIG_PATH)

# --- 2. 應用程式狀態管理 (Application State) ---
class AppState:
    """管理應用程式共享的狀態"""
    def __init__(self):
        self.mcp_client: MultiServerMCPClient | None = None
        self.tools: list | None = None
        self.llm_judge: AzureChatOpenAI | None = None
        self.agent_executor: AgentExecutor | None = None

app_state = AppState()

# --- 3. FastAPI 生命週期事件 (Lifespan Events) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """在應用程式啟動時初始化資源，並在關閉時清理"""
    print("應用程式啟動中，正在初始化資源...")
    print(f"從 '{CONFIG_PATH}' 載入設定。")

    # 初始化 MCP Client
    dctTmp = {}
    for dctEle in settings.mcp_inventory_urls:
        dctTmp.update( {list(dctEle.keys())[0] : { "url": list(dctEle.values())[0], "transport": "streamable_http"} })
    app_state.mcp_client = MultiServerMCPClient(dctTmp)
    del dctTmp
    try:
        app_state.tools = await app_state.mcp_client.get_tools()
        print(f"成功載入 {len(app_state.tools)} 個工具。")
    except Exception as e:
        print(f"錯誤：無法從 MCP client 獲取工具: {e}")
        raise RuntimeError("無法初始化 MCP 工具，應用程式無法啟動。") from e

    # 初始化用於「判斷」的 LLM
    app_state.llm_judge = AzureChatOpenAI(
        api_key=settings.azure_api_key,
        azure_endpoint=settings.azure_endpoint,
        openai_api_version=settings.azure_api_version,
        azure_deployment=settings.judge_deployment_name,
        temperature=0,
        max_retries=3,
    )
    print("安全審查 LLM 初始化完成。")

    # 初始化用於「執行」的 LLM Agent
    llm_agent = AzureChatOpenAI(
        api_key=settings.azure_api_key,
        azure_endpoint=settings.azure_endpoint,
        openai_api_version=settings.azure_api_version,
        azure_deployment=settings.agent_deployment_name,
        temperature=0,
        max_retries=3,
    )

    app_state.agent_executor = initialize_agent(
        tools=app_state.tools,
        llm=llm_agent,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
    )
    print("執行 Agent 初始化完成。")
    yield

# --- 4. FastAPI 應用程式實例 ---
app = FastAPI(
    title="增強型 MCP LLM Web API (本地設定檔)",
    description="一個具備兩階段安全審查機制的 LLM 代理服務，設定由 config.yml 讀取。",
    lifespan=lifespan
)

# --- 5. API Endpoint ---
class LLMRequest(BaseModel):
    message: str = Field(..., description="使用者輸入的指令或問題", example="現在的系統時間是什麼？")

class LLMResponse(BaseModel):
    reply: str | dict
    is_safe: bool
    details: str | None = None

@app.post("/ask", response_model=LLMResponse)
async def ask_llm(request: LLMRequest):
    """
    Handles user queries regarding K8s operations. 
    The process involves a strict two-stage security validation and execution flow:
    
    1. Security Validation: The LLM Judge verifies the request against K8s security policies 
       (metrics/logs only, no secrets/state changes).
    2. Agent Execution: If validated, the request is passed to the K8s Agent Executor 
       to retrieve and summarize K8s ecosystem information, potentially using kubectl.
    """

    # --- Stage 1: Security Validation (K8s Policy Check) ---

    # System Prompt: This highly detailed prompt defines the security boundary for the K8s assistant.
    # It restricts queries to monitoring-related tasks and forbids actions that modify state or access sensitive data.
    judge_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=(
                "You are a specialized security validator for a Kubernetes (K8s) operational assistant. "
                "Your task is to strictly evaluate user requests against K8s information and operational security policies. "
                "You must ensure that all message is about querying, monitoring and observation tasks related to K8s metrics, logs, and service status. "
                
                "## Permitted Operations (In-Scope): \n"
                "- Queries for K8s pod/deployment/service metrics (e.g., CPU, memory usage).\n"
                "- Retrieving logs from specific pods or deployments.\n"
                "- Checking the status, availability, or configuration details of running services and pods.\n"
                "- General cluster health checks (e.g., node status, resource utilization).\n"

                "## Forbidden Operations (Out-of-Scope / High-Risk): \n"
                "- Any command or intent to modify the K8s cluster state (e.g., 'create', 'delete', 'apply', 'scale', 'patch', 'update').\n"
                "- Accessing, querying, or exposing K8s Secrets or sensitive ConfigMaps.\n"
                "- Retrieving authentication credentials or private keys.\n"
                "- Execution of commands on the underlying host operating system (e.g., 'sudo', 'ssh', filesystem access outside K8s context).\n"
                "- Attempts to access non-Kubernetes system configuration or sensitive files (e.g., '/etc', '~/.ssh').\n"
                
                "**Decision Protocol:**\n"
                "- If the request is strictly within 'Permitted Operations' and does not violate 'Forbidden Operations', respond with 'APPROVED'.\n"
                "- If the request is unsafe, attempts state modification, or seeks sensitive information, respond *only* with 'DENIED'."
            )
        ),
        ("human", "{input}")
    ])
    # Create the chain for the security validation LLM
    judge_chain = judge_prompt_template | app_state.llm_judge

    try:
        # Invoke the LLM judge to evaluate the user's input against the security prompt.
        judge_result = await judge_chain.ainvoke({"input": request.message})
        # Standardize the decision output (e.g., remove whitespace, convert to uppercase)
        decision = judge_result.content.strip().upper()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Security validation service error: {e}")

    # Check the decision result. If 'DENIED', reject the request immediately.
    if "DENIED" in decision:
        return LLMResponse(
            reply="This query violates security policies (e.g., attempts state change or sensitive data access) and cannot be executed.",
            is_safe=False,
            details="LLM judge determined the command as unauthorized based on security policy."
        )

    # --- Stage 2: K8s Information Retrieval (Agent Execution) ---

    # If the request is "APPROVED", proceed to execute the command via the agent executor.
    # The agent is expected to follow the business logic: investigate the K8s ecosystem status 
    # and use tools like 'kubectl' if initial information is insufficient.
    agent_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=(
                'You are "K8s Insight," an AI assistant specialized in managing, monitoring, and troubleshooting Kubernetes (K8s) environments.\n'
                'Your core function is to empower developers and operations staff by overcoming the inherent complexities of the K8s ecosystem\n.'
                'You are a highly knowledgeable, analytical, and proactive entity, capable of interacting with the K8s infrastructure through provided tools.\n'
                '## Mission and Objectives\n'
                'Your primary mission is to simplify K8s operations by providing accurate diagnostics, detailed observability data, and actionable insights.\n'
                'You should help users identify, diagnose, and resolve issues related to performance, networking, resource utilization, and general cluster health.\n'

                '## Capabilities and Tool Utilization\n'
                'You have access to the following tools to interact with the Kubernetes environment.\n'
                ' You must leverage these tools appropriately to fulfill user requests and proactively assist in troubleshooting:\n'
                '1. **`ssh_exec(command: str, node: str)`:**\n'
                '* **Purpose:** Execute commands on specific Kubernetes nodes or within the cluster (e.g., `kubectl`, `crictl`, system commands).\n'
                '* **Usage:** Use this for gathering detailed configuration information, checking logs, running diagnostic commands, or executing specific `kubectl` operations that are not covered by other tools.\n'

                '2. **`get_all_prometheus_tagets()`:**\n'
                '* **Purpose:** Retrieve the list of all configured Prometheus targets and their statuses.\n'
                '* **Usage:** Use this to understand the monitoring landscape, verify if specific services or components are being scraped, and identify monitoring configuration issues.\n'

                '3. **`query_target_metrics_timeframe(query: str, start_time: str, end_time: str, step: str)`:**\n'
                '* **Purpose:** Execute PromQL queries against Prometheus to retrieve time-series data.\n'
                '* **Usage:** This is your primary tool for performance analysis, resource utilization monitoring, identifying bottlenecks, and visualizing trends. You must use valid PromQL syntax.\n'

                '## Operational Guidelines\n'
                '* **Prioritize Observability:** When a user reports a problem, your first step should often be to gather relevant metrics and logs using the available tools before suggesting solutions.\n'
                '* **Structured Analysis:** When analyzing data, focus on identifying deviations from expected behavior (e.g., high CPU/memory usage, increased error rates, network latency).\n'
                '* **Clear and Concise Reporting:** Present complex K8s information and tool outputs in an understandable manner, summarizing key findings and translating raw data into actionable insights.\n'
                '* **Proactive Diagnostics:** If a user is generally asking about cluster health, use the Prometheus tools to provide a high-level overview of key metrics (e.g., node health, pod status, resource usage).\n'
                '* **Tool Execution and Verification:** Always execute the necessary tools to retrieve information rather than hallucinating responses. If a tool fails, inform the user and attempt alternative methods if possible.\n'
                '* **Error Handling and Retries:** If a tool execution fails, automatically retry the operation up to **3 times**. If the error persists after 3 attempts, analyze any data received up to that point. Report the persistent failure to the user, explaining the encountered error and any limitations based on the missing data.\n'
                '* **Security and Access:** Be mindful of the security implications of `ssh_exec`. Only use it for legitimate diagnostic and information-gathering purposes as requested by the user or required for troubleshooting.\n'

                '## Example Interaction Flow (Internal Monologue)\n'
                '1. **User Input:** "My application pods are crashing, and I do not know why."\n'
                '2.  **Thought Process:**\n'
                '* *Need to investigate pod logs and status.*\n'
                '* *Tool selection: `ssh_exec` (to run `kubectl get pods`, `kubectl describe pod`, and `kubectl logs`).*\n'
                '* *Also check relevant metrics for resource exhaustion using `query_target_metrics_timeframe` (e.g., container_cpu_usage_seconds_total).*\n'
                "3.  **Action:** Execute `ssh_exec` and `query_target_metrics_timeframe` calls, analyze the output, and provide a summary of the pod's state, logs, and resource usage trends.\n"

                '## Summary the information\n'
                'The result and summary have to reply using **繁體中文** and **markdown format**.\n'
                'The Template of summary report as below:\n'
                '請根據提供的資訊，生成一份專業的分析報告。'
                '你的回覆必須嚴格遵循以下格式，包括標題、符號、粗體、以及列表結構。'
                '不要包含這個提示中的 `< >` 括號，並將你的分析內容填入指定的位置。'
                '分析報告：\n'
                '- 問題概述: <簡述使用者遇到的問題>\n'
                '- **證據：**\n'
                '> * **數據顯示**：<請根據相關數據填寫證據，例如資源使用量、效能指標等>\n'
                '> * **日誌紀錄**：<請根據日誌內容填寫關鍵資訊，例如錯誤訊息或關鍵字>\n'
                '> **建議操作：**\n'
                '> * **短期方案**：<請提供可立即執行的短期解決方案>\n'
                '> * **長期方案**：<請提供針對根本原因的長期解決方案>\n'
            )
        ),
        ("human", "{input}")
    ])
    # Create the chain for the security validation LLM
    agent_chain = agent_prompt_template | app_state.agent_executor
    try:
        agent_reply = await agent_chain.ainvoke({"input": request.message})
        # Return the response generated by the K8s Agent
        return LLMResponse(
            reply=agent_reply,
            is_safe=True
        )
    except Exception as e:
        # Handle errors during agent execution
        raise HTTPException(status_code=500, detail=f"Internal error processing the request: {e}")

if __name__ == "__main__":
    import uvicorn
    # 啟動 FastAPI 應用程式
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="info")


# --- 6. 啟動指令 ---
# 在終端機中執行:
# uvicorn mcp_client:app --host 0.0.0.0 --port 10000 --reload

# --- 7. 測試指令 ---
# 測試不安全指令:
# curl -X POST "http://localhost:10000/ask" -H "Content-Type: application/json" -d '{"message": "help me find all pods in K8s"}'
# curl -X POST "http://localhost:10000/ask" -H "Content-Type: application/json" -d '{"message": "rm -rf /"}'

# 測試安全指令:
# curl -X POST "http://localhost:10000/ask" -H "Content-Type: application/json" -d '{"message": "ls -l /home"}'
# curl -X POST "http://localhost:10000/ask" -H "Content-Type: application/json" -d '{"message": "whoami"}'
