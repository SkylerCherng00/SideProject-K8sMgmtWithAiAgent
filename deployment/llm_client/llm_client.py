import yaml
import json
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langchain_openai import AzureChatOpenAI
from langchain.agents import initialize_agent, AgentType, AgentExecutor, create_react_agent
from tools.k8s_tools import analysis_tools, debug_tools

# --- 1. 設定管理 (從 config.yml 檔案讀取) ---

# 取得當前腳本所在的目錄
# Path(__file__) 會取得當前檔案的絕對路徑
# .parent 會取得該檔案所在的資料夾路徑
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_llmclient.yml"
SYSMSG_AGENT_PATH = BASE_DIR / "sysmsg_agent.txt"
SYSMSG_JUDGE_PATH = BASE_DIR / "sysmsg_judge.txt"
SYSMSG_ROUTINE_PATH = BASE_DIR / "sysmsg_routine.txt"


def _is_json_dict(s):
    """
    Check if a string is a valid JSON dictionary.
    
    Args:
        s (str): The string to check.
    
    Returns:
        bool: True if the string is a JSON dictionary, False otherwise.
    """
    try:
        result = json.loads(s)
        return isinstance(result, dict)
    except json.JSONDecodeError:
        return False

# 讀取系統提示訊息
def _load_system_message(path: Path) -> str:
    """
    Load a system prompt message from the specified file path.
    
    Args:
        path (Path): The path to the system message file.
    
    Returns:
        str: The content of the system message file.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If there is an error reading the file.
    """
    if not path.is_file():
        raise FileNotFoundError(f"System message file does not exist at: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Error loading system message file '{path}': {e}")

class Settings(BaseModel):
    """
    Application settings model for Azure OpenAI service.
    
    Attributes:
        azure_api_key (str): API key for Azure OpenAI service.
        azure_api_version (str): API version for Azure OpenAI service.
        azure_endpoint (str): Endpoint URL for Azure OpenAI service.
        judge_deployment_name (str): Deployment name for the judge model (safety check).
        agent_deployment_name (str): Deployment name for the agent model (task execution).
    """
    azure_api_key: str
    azure_api_version: str
    azure_endpoint: str
    judge_deployment_name: str
    agent_deployment_name: str


def _load_settings(path: Path) -> Settings:
    """
    Load and validate YAML settings from the specified path.
    
    Args:
        path (Path): The path to the YAML settings file.
    
    Returns:
        Settings: The validated settings object.
    
    Raises:
        FileNotFoundError: If the settings file does not exist.
        ValueError: If the YAML is invalid or validation fails.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Settings file does not exist at: {path}\n"
            f"Please create a 'config_llmclient.yml' file in the project root with the required settings."
        )
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return Settings(**config_data)
    except yaml.YAMLError as e:
        raise ValueError(f"Settings file '{path}' YAML format error: {e}")
    except Exception as e:
        raise ValueError(f"Error loading settings file '{path}': {e}")

# 在應用程式啟動時載入設定
settings = _load_settings(CONFIG_PATH)

# --- 2. 應用程式狀態管理 (Application State) ---
class AppState:
    """
    Manage shared application state.
    
    Attributes:
        analysis_tools (list | None): List of analysis tools.
        debug_tools (list | None): List of debug tools.
        llm_judge (AzureChatOpenAI | None): LLM for safety checking.
        agent_analyzer (AgentExecutor | None): Agent for analysis tasks.
        agent_executor (AgentExecutor | None): Agent for debug tasks.
        sysmsg_judge (str | None): System prompt for safety check.
        sysmsg_agent (str | None): System prompt for agent execution.
        sysmsg_routine (str | None): System prompt for routine queries.
    """
    def __init__(self):
        self.analysis_tools: list | None = None
        self.debug_tools: list | None = None
        # self.llm_judge: AzureChatOpenAI | None = None
        self.agent_analyzer: AgentExecutor | None = None
        self.agent_executor: AgentExecutor | None = None
        self.sysmsg_judge: str | None = None  # System prompt for safety check
        self.sysmsg_agent: str | None = None  # System prompt for agent execution
        self.sysmsg_routine: str | None = None # System prompt for routine queries
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
    """
    FastAPI lifespan event handler for startup and shutdown.
    
    Initializes resources on application startup and cleans up on shutdown:
        1. Loads K8s tools.
        2. Loads system prompt messages.
        3. Initializes Azure OpenAI LLMs for judge and agent.
        4. Sets up agent executors for debug and analysis.
    
    Args:
        app (FastAPI): The FastAPI application instance.
    """
    print("Application starting, initializing resources...")
    print(f"Loading settings from '{CONFIG_PATH}'.")

    # Load K8s tools
    try:
        app_state.analysis_tools = analysis_tools
        app_state.debug_tools = debug_tools
        print(f"Loaded {len(app_state.analysis_tools) + len(app_state.debug_tools)} K8s tools.")
    except Exception as e:
        print(f"Error: Failed to load K8s tools: {e}")
        raise RuntimeError("Failed to initialize K8s tools, application cannot start.") from e

    # Load system prompt messages
    try:
        app_state.sysmsg_judge = _load_system_message(SYSMSG_JUDGE_PATH)
        app_state.sysmsg_agent = _load_system_message(SYSMSG_AGENT_PATH)
        app_state.sysmsg_routine = _load_system_message(SYSMSG_ROUTINE_PATH)
        print("System prompt messages loaded.")
    except Exception as e:
        print(f"Error: Failed to load system prompt messages: {e}")
        raise RuntimeError("Failed to load system prompt messages, application cannot start.") from e
        
    # Initialize LLM for safety checking (judge)
    app_state.llm_judge = AzureChatOpenAI(
        api_key=settings.azure_api_key,
        azure_endpoint=settings.azure_endpoint,
        openai_api_version=settings.azure_api_version,
        azure_deployment=settings.judge_deployment_name,
        temperature=0,
        max_retries=3,
    )
    print("Safety judge LLM initialized.")

    # Initialize LLM agent for execution
    llm_agent = AzureChatOpenAI(
        api_key=settings.azure_api_key,
        azure_endpoint=settings.azure_endpoint,
        openai_api_version=settings.azure_api_version,
        azure_deployment=settings.agent_deployment_name,
        temperature=0,
        max_retries=3,
    )

    # Initialize agent executor for debug tasks
    prompt = PromptTemplate.from_template(app_state.sysmsg_agent)
    debug_zero_shot_agent = create_react_agent(
        llm=llm_agent,
        tools=app_state.debug_tools,
        prompt=prompt,
    )
    app_state.agent_executor = AgentExecutor(
        agent=debug_zero_shot_agent,
        tools=app_state.debug_tools,
        verbose=False,
        handle_parsing_errors=True
    )

    # Initialize agent executor for analysis tasks
    app_state.agent_analyzer = initialize_agent(
        tools=app_state.analysis_tools,
        llm=llm_agent,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        handle_parsing_errors=True,
    )

    print("Agent executors initialized.")
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
    """
    User query request model for the API.
    
    Attributes:
        message (str): The user's K8s-related query input.
    """
    message: str = Field(..., description="K8s-related user query", example="Show CPU usage for all pods")

class LLMResponse(BaseModel):
    """
    API response model.
    
    Attributes:
        reply (str | dict): The LLM's reply content (string or dictionary).
        is_safe (bool): Whether the query passed the safety check.
        details (str, optional): Additional details if available.
    """
    reply: str | dict
    is_safe: bool

@app.post("/llm/ask", response_model=LLMResponse)
async def ask_llm(request: LLMRequest):
    """
    Handle user queries about Kubernetes operations.
    
    This endpoint performs a strict two-stage process:
        1. Safety check: The LLM judge validates the request against K8s safety policies (only metrics/logs allowed, no secrets/state changes).
        2. Agent execution: If approved, the request is passed to the K8s agent executor to retrieve and summarize K8s ecosystem information using available tools.
    
    Args:
        request (LLMRequest): The user query request.
    
    Returns:
        LLMResponse: The response containing the LLM's reply and safety status.
    """
    # --- Stage 1: Safety check (K8s policy) ---
    # System prompt: loaded from sysmsg_judge.txt, defines safety boundaries
    judge_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=app_state.sysmsg_judge
        ),
        ("human", "{input}")
    ])
    # Create the safety check LLM chain
    judge_chain = judge_prompt_template | app_state.llm_judge

    try:
        # Call the LLM judge to evaluate the user's input
        judge_result = await judge_chain.ainvoke({"input": request.message})
        # Normalize decision output (strip spaces, uppercase)
        decision = judge_result.content.strip().upper()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Safety check service error: {e}")

    # If decision is "DENIED", reject the request
    if "DENIED" in decision:
        return LLMResponse(
            reply={"output": "This query violates safety policy (e.g., attempts to change state or access sensitive data) and cannot be executed."},
            is_safe=False,
            details="LLM judge determined the command is not authorized by safety policy."
        )
    
    # --- Stage 2: K8s information retrieval (agent execution) ---
    # If "APPROVED", execute the command via agent executor
    try:
        agent_reply = app_state.agent_executor.invoke({"input": request.message})
        # The agent's reply is a string in 'output'
        output = agent_reply.get("output", 'no output')
        output = json.loads(output).get("action_input", "no action_input") if _is_json_dict(output) else output
        return LLMResponse(
            reply={"output": output},
            is_safe=True
        )
    except Exception as e:
        # Handle errors during agent execution
        print(f"Agent execution error: {str(e)}")
        error_message = "Internal error occurred while processing the request"
        raise HTTPException(status_code=500, detail=error_message)

@app.post("/llm/ask_current", response_model=LLMResponse)
async def ask_llm_current(request: LLMRequest):
    """
    Handle user queries about the current state of Kubernetes.
    
    This endpoint uses the agent executor to retrieve and summarize information about the K8s ecosystem for the last 30 minutes, using available tools to analyze the current situation.
    
    Args:
        request (LLMRequest): The user query request.
    
    Returns:
        LLMResponse: The response containing the LLM's reply and safety status.
    """
    agent_prompt_template = ChatPromptTemplate.from_messages([
        SystemMessage(
            content=app_state.sysmsg_routine
        ),
        ("human", "{input}")
    ])
    # Create the agent execution LLM chain
    agent_chain = agent_prompt_template | app_state.agent_analyzer
    try:
        agent_reply = await agent_chain.ainvoke({"input": request.message})
        # The agent's reply is a string in 'output'
        output = agent_reply.get("output", 'no output')
        output = json.loads(output).get("action_input", "no action_input") if _is_json_dict(output) else output
        return LLMResponse(
            reply={"output": output},
            is_safe=True
        )
    except Exception as e:
        # Handle errors during agent execution
        print(f"Agent execution error: {str(e)}")
        error_message = "Internal error occurred while processing the request"
        raise HTTPException(status_code=500, detail=error_message)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="info")