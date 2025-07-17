'''
0. System Message 皆由 Gemini AI 協助生成
1. `ask` API 不穩定，不明原因終止分析行為直接 `> Finished chain.` 經測試與 agent_executor 的 system message 有關
  - 將 sysmsg_agent.txt.org 內容改成 ReAct Prompt 後，有時能夠正常執行
  - 有將轉導邏輯簡化到只剩 Debug 功能，但仍會不正常終止
  - 透過 chain 的方式 `agent_chain = agent_prompt_template | app_state.agent_executor` 不穩定
2. `ask_current` API 卻能正常使用，原因不明
'''

import yaml
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langchain_openai import AzureChatOpenAI
from langchain.agents import initialize_agent, AgentType, AgentExecutor
from tools.k8s_tools import analysis_tools, debug_tools

# --- 1. 設定管理 (從 config.yml 檔案讀取) ---

# 取得當前腳本所在的目錄
# Path(__file__) 會取得當前檔案的絕對路徑
# .parent 會取得該檔案所在的資料夾路徑
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_llmclient_org.yml"
SYSMSG_AGENT_PATH = BASE_DIR / "sysmsg_agent.txt.org" # <--
SYSMSG_JUDGE_PATH = BASE_DIR / "sysmsg_judge.txt"
SYSMSG_ROUTINE_PATH = BASE_DIR / "sysmsg_routine.txt"
SYSMSG_TRANSLATOR_PATH = BASE_DIR / "sysmsg_translator.txt"


def _is_json_dict(s):
    try:
        result = json.loads(s)
        return isinstance(result, dict)
    except json.JSONDecodeError:
        return False

# 讀取系統提示訊息
def _load_system_message(path: Path) -> str:
    """從指定的路徑載入系統提示訊息"""
    if not path.is_file():
        raise FileNotFoundError(f"系統提示訊息檔案不存在於: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"載入系統提示訊息檔案 '{path}' 時發生錯誤: {e}")

class Settings(BaseModel):
    """應用程式的設定模型
    
    包含 Azure OpenAI 服務所需的設定:
    - azure_api_key: Azure OpenAI 服務的 API 金鑰
    - azure_api_version: Azure OpenAI 服務的 API 版本
    - azure_endpoint: Azure OpenAI 服務的端點 URL
    - judge_deployment_name: 用於安全審查的部署模型名稱
    - agent_deployment_name: 用於執行代理的部署模型名稱
    """
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
            f"請在專案根目錄建立一個 'config_llmclient.yml' 檔案，並填入必要的設定。"
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
        self.analysis_tools: list | None = None
        self.debug_tools: list | None = None
        self.llm_judge: AzureChatOpenAI | None = None
        self.agent_analyzer: AgentExecutor | None = None
        self.agent_executor: AgentExecutor | None = None
        self.sysmsg_judge: str | None = None  # 用於安全審查的系統提示訊息
        self.sysmsg_agent: str | None = None  # 用於執行代理的系統提示訊息
        self.sysmsg_routine: str | None = None # 用於常規查詢的系統提示訊息
        self.sysmsg_translator: str | None = None  # 用於翻譯的系統提示訊息
app_state = AppState()

# --- 3. FastAPI 生命週期事件 (Lifespan Events) ---
# 這個部分處理應用程式的啟動和關閉時的事件
# 包括:
# 1. 載入 K8s 工具 (從 tools/k8s_tools.py)
# 2. 載入系統提示訊息 (從 sysmsg_*.txt 文件)
# 3. 初始化 Azure OpenAI 服務的 LLM 模型
# 4. 建立執行代理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """在應用程式啟動時初始化資源，並在關閉時清理"""
    print("應用程式啟動中，正在初始化資源...")
    print(f"從 '{CONFIG_PATH}' 載入設定。")

    # 載入 K8s 工具
    try:
        # 使用已導入的 tools
        app_state.analysis_tools = analysis_tools
        app_state.debug_tools = debug_tools
        print(f"成功載入 {len(app_state.analysis_tools) + len(app_state.debug_tools)} 個 K8s 工具。")
    except Exception as e:
        print(f"錯誤：無法載入 K8s 工具: {e}")
        raise RuntimeError("無法初始化 K8s 工具，應用程式無法啟動。") from e

    # 載入系統提示訊息
    try:
        app_state.sysmsg_judge = _load_system_message(SYSMSG_JUDGE_PATH)
        app_state.sysmsg_agent = _load_system_message(SYSMSG_AGENT_PATH)
        app_state.sysmsg_routine = _load_system_message(SYSMSG_ROUTINE_PATH)
        app_state.sysmsg_translator = _load_system_message(SYSMSG_TRANSLATOR_PATH)
        print("系統提示訊息載入完成。")
    except Exception as e:
        print(f"錯誤：無法載入系統提示訊息: {e}")
        raise RuntimeError("無法載入系統提示訊息，應用程式無法啟動。") from e
        
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

    # 使用工具初始化代理執行器 (除錯用) !!!
    app_state.agent_executor = initialize_agent(
        tools=app_state.debug_tools,
        llm=llm_agent,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
    )

    # 使用工具初始化代理執行器 (分析用)
    app_state.agent_analyzer = initialize_agent(
        tools=app_state.analysis_tools,
        llm=llm_agent,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
    )

    print("執行 Agent 初始化完成。")
    yield

# --- 4. FastAPI 應用程式實例 ---
# 建立 FastAPI 應用程式並設定其標題、描述和生命週期事件處理函數
app = FastAPI(
    title="增強型 MCP LLM Web API",
    description="一個具備兩階段安全審查機制的 LLM 代理服務。",
    lifespan=lifespan
)

# --- 5. API Endpoint ---
# 這個部分定義了 API 端點，用於處理使用者查詢
# 包含以下流程:
# 1. 接收使用者的查詢請求
# 2. 通過安全審查 LLM 驗證查詢是否安全 (使用 sysmsg_judge.txt 的系統提示)
# 3. 如果安全，通過代理 LLM 執行查詢 (使用 sysmsg_agent.txt 的系統提示和 K8s 工具)
# 4. 返回結果給使用者
class LLMRequest(BaseModel):
    """使用者查詢請求模型
    
    包含:
    - message: 使用者輸入的 K8s 相關查詢
    """
    message: str = Field(..., description="使用者輸入的 K8s 相關查詢", example="顯示所有 pod 的 CPU 使用率")

class LLMResponse(BaseModel):
    """API 回應模型
    
    包含:
    - reply: LLM 的回應內容 (字串或字典)
    - is_safe: 查詢是否通過安全審查
    - details: 額外的詳細資訊 (如果有)
    """
    reply: str | dict
    is_safe: bool

@app.post("/ask", response_model=LLMResponse)
async def ask_llm(request: LLMRequest):
    """
    處理使用者關於 K8s 操作的查詢。
    該流程涉及嚴格的兩階段安全驗證和執行流程：
    
    1. 安全驗證：LLM 評判根據 K8s 安全策略驗證請求
       (僅限指標/日誌，不允許機密/狀態更改)。
    2. 代理執行：如果驗證通過，請求將傳遞給 K8s 代理執行器
       來檢索和匯總 K8s 生態系統信息，可能會使用提供的工具。
    """
    # --- 階段 1: 安全驗證 (K8s 安全策略檢查) ---

    # 系統提示：從 sysmsg_judge.txt 檔案載入的系統提示，用於定義安全界限
    # 它限制查詢只能是監控相關任務，並禁止修改狀態或存取敏感資料的操作
    judge_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=app_state.sysmsg_judge
        ),
        ("human", "{input}")
    ])
    # 創建安全驗證 LLM 的鏈
    judge_chain = judge_prompt_template | app_state.llm_judge

    try:
        # 調用 LLM 評判來根據安全提示評估使用者的輸入
        judge_result = await judge_chain.ainvoke({"input": request.message})
        # 標準化決策輸出 (例如，刪除空格，轉為大寫)
        decision = judge_result.content.strip().upper()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"安全驗證服務錯誤: {e}")

    # 檢查決策結果。如果是「DENIED」，立即拒絕請求
    if "DENIED" in decision:
        return LLMResponse(
            reply="此查詢違反安全策略 (例如，嘗試更改狀態或存取敏感資料)，無法執行。",
            is_safe=False,
            details="LLM 評判根據安全策略判定該命令未獲授權。"
        )
    
    # 翻譯使用者的輸入 (直接用中文問 會造成斷鏈 目前原因不明)
    translator_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=app_state.sysmsg_translator
        ),
        ("human", "{input}")
    ])
    translator_chain = translator_prompt_template | app_state.llm_judge

    try:
        translator_result = await translator_chain.ainvoke({"input": request.message})
        translated_msg = translator_result.content
        # print(f"Translated message: {translated_msg}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"翻譯服務錯誤: {e}")

    # --- 階段 2: K8s 資訊檢索 (代理執行) ---

    # 如果請求為「APPROVED」，則通過代理執行器執行命令
    # 該代理預期會遵循業務邏輯：調查 K8s 生態系統狀態
    # 並在初始資訊不足時使用像 K8s 工具
    agent_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=app_state.sysmsg_agent 
        ),
        ("human", "{input}")
    ])
    # 創建代理執行 LLM 的鏈
    agent_chain = agent_prompt_template | app_state.agent_executor
    try:
        # agent_reply = await agent_chain.ainvoke({"input": request.message})
        agent_reply = await agent_chain.ainvoke({"input": translated_msg})

        # 返回由 K8s 代理生成的回應
        # 注意 'output' 結果是字串 !!!
        # print(f"Agent reply: {agent_reply.get("output",{})}, type:{type(agent_reply.get("output",{}))}")
        output = agent_reply.get("output", 'no output')
        output = json.loads(output).get("action_input", "no action_input") if _is_json_dict(output) else output
        return LLMResponse(
            reply={"output": output},
            is_safe=True
        )
    except Exception as e:
        # 處理代理執行期間的錯誤
        print(f"Agent execution error: {str(e)}")
        error_message = "處理請求時發生內部錯誤"
        raise HTTPException(status_code=500, detail=error_message)

@app.post("/ask_current", response_model=LLMResponse)
async def ask_llm_current(request: LLMRequest):
    """
    處理使用者關於 K8s 當前狀態的查詢。
    
    - 代理執行：來檢索和匯總 K8s 生態系統信息近 30 分鐘的資訊，可能會使用提供的工具，
          彙整當前的資訊並分析目前 K8s 的當前的態勢
    """
    agent_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=app_state.sysmsg_routine
        ),
        ("human", "{input}")
    ])
    # 創建代理執行 LLM 的鏈
    agent_chain = agent_prompt_template | app_state.agent_analyzer
    try:
        agent_reply = await agent_chain.ainvoke({"input": request.message})
        # 返回由 K8s 代理生成的回應
        output = agent_reply.get("output", 'no output')
        output = json.loads(output).get("action_input", "no action_input") if _is_json_dict(output) else output
        return LLMResponse(
            reply={"output": output},
            is_safe=True
        )
    except Exception as e:
        # 處理代理執行期間的錯誤
        print(f"Agent execution error: {str(e)}")
        error_message = "處理請求時發生內部錯誤"
        raise HTTPException(status_code=500, detail=error_message)

if __name__ == "__main__":
    import uvicorn
    # 啟動 FastAPI 應用程式
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="info")


# --- 6. 啟動指令 ---
# 在終端機中執行:
# uvicorn llm_client:app --host 0.0.0.0 --port 10000 --reload

# --- 7. 測試指令 ---
# 測試不安全指令 (將被拒絕):
# curl -X POST "http://localhost:10000/ask" -H "Content-Type: application/json" -d '{"message": "刪除所有的 pod"}'
# curl -X POST "http://localhost:10000/ask" -H "Content-Type: application/json" -d '{"message": "修改 K8s 的節點配置"}'

# 測試安全指令 (將被接受並執行):
# curl -X POST "http://192.168.72.10:10000/ask" -H "Content-Type: application/json" -d '{"message": "現在有哪些 ns"}'

# routine test
# curl -X POST "http://192.168.72.10:10000/ask_current" -H "Content-Type: application/json" -d '{ "message": "What is the current status of our Kubernetes cluster over the last 30 minutes? Are there any alerts, critical errors, or significant resource utilization issues?"}'