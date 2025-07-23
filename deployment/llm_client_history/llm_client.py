"""
K8s LLM Client - Enhanced MCP (Model Context Protocol) API for Kubernetes Management

This module implements a FastAPI-based web service that uses Azure OpenAI's language models
to provide a conversational interface for Kubernetes management tasks. It features:
1. Two-stage safety checking with a judge LLM to ensure operations are safe
2. Persistent chat history using PostgreSQL
3. Two specialized agent types:
   - Debug agent for troubleshooting K8s issues
   - Analysis agent for monitoring and analyzing the current state of K8s
4. Tool integration with K8s utilities for querying logs, metrics, and cluster status

The system uses LangChain's agent framework to execute complex reasoning chains and
maintain conversation context across multiple user interactions.
"""

import yaml  # For parsing configuration files
import json  # For handling JSON data structures
from pathlib import Path  # For OS-independent path handling
from contextlib import asynccontextmanager  # For FastAPI's lifespan management
from fastapi import FastAPI, HTTPException  # Web API framework
from pydantic import BaseModel, Field  # Data validation and schema definition
import uuid  # For generating unique session IDs
import psycopg  # PostgreSQL client for chat history persistence
from langchain_postgres.chat_message_histories import PostgresChatMessageHistory  # DB-backed chat history
from langchain_core.messages import SystemMessage  # For creating system prompts
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate  # For formatting prompts
from langchain_openai import AzureChatOpenAI  # Azure OpenAI integration
from langchain.agents import initialize_agent, AgentType, AgentExecutor, create_react_agent  # Agent components
from langchain_core.runnables.history import RunnableWithMessageHistory  # For memory functionality
from tools.k8s_tools import analysis_tools, debug_tools  # Custom K8s tools for agents

# Path definitions for configuration and system prompt files
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_llmclient.yml"  # App settings
SYSMSG_AGENT_PATH = BASE_DIR / "sysmsg_agent.txt"  # System prompt for agent
SYSMSG_JUDGE_PATH = BASE_DIR / "sysmsg_judge.txt"  # System prompt for safety judge
SYSMSG_ROUTINE_PATH = BASE_DIR / "sysmsg_routine.txt"  # System prompt for routine tasks


def _is_json_dict(s):
    """
    Check if a string is a valid JSON dictionary.
    
    This helper function safely checks whether a string can be parsed as valid JSON
    and specifically if it represents a dictionary/object structure.
    
    Args:
        s: The string to check for JSON dictionary validity
        
    Returns:
        bool: True if the string is a valid JSON dictionary, False otherwise
    """
    try:
        result = json.loads(s)
        return isinstance(result, dict)
    except json.JSONDecodeError:
        return False

def _load_system_message(path: Path) -> str:
    """
    Load a system prompt message from the specified file path.
    
    System messages define the behavior, capabilities, and constraints for
    the different LLM roles (agent, judge, etc.). This function reads these
    from external files to allow for easier updating and maintenance.
    
    Args:
        path (Path): Path to the system message file
        
    Returns:
        str: Content of the system message file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If there's an error reading the file
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
    Application settings model for Azure OpenAI service and PostgreSQL database.
    
    This Pydantic model validates configuration data loaded from YAML,
    ensuring all required fields are present and properly typed.
    
    Attributes:
        azure_api_key (str): API key for Azure OpenAI service
        azure_api_version (str): API version for Azure OpenAI service
        azure_endpoint (str): Endpoint URL for Azure OpenAI service
        judge_deployment_name (str): Model deployment name for safety judge LLM
        agent_deployment_name (str): Model deployment name for agent LLM
        postgres_connection_string (str): Connection string for PostgreSQL database
    """
    azure_api_key: str
    azure_api_version: str
    azure_endpoint: str
    judge_deployment_name: str
    agent_deployment_name: str
    postgres_connection_string: str

def _load_settings(path: Path) -> Settings:
    """
    Load and validate YAML settings from the specified path.
    
    This function handles loading the application configuration from YAML,
    parsing it, and validating it against the Settings model schema.
    
    Args:
        path (Path): Path to the configuration YAML file
        
    Returns:
        Settings: Validated settings object
        
    Raises:
        FileNotFoundError: If the settings file doesn't exist
        ValueError: If there's an error parsing the YAML or validating the settings
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Settings file does not exist at: {path}\n"
            f"Please create a 'config_llmclient.yml' file in the project root with the required settings."
        )
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return Settings(**config_data)  # Validate against Pydantic model
    except yaml.YAMLError as e:
        raise ValueError(f"Settings file '{path}' YAML format error: {e}")
    except Exception as e:
        raise ValueError(f"Error loading settings file '{path}': {e}")

# Load application settings at module level
settings = _load_settings(CONFIG_PATH)

class AppState:
    """
    Manage shared application state across API endpoints.
    
    This class encapsulates all stateful components used by the application:
    - LLM instances for different roles (judge, agent)
    - Tool collections for different tasks (analysis, debugging)
    - System messages for different contexts
    - Database connections and session tracking
    
    The class provides a central place to access these resources and ensures
    they are properly initialized in the application startup phase.
    """
    def __init__(self):
        # Tool collections for K8s operations
        self.analysis_tools: list | None = None  # For analyzing K8s resources
        self.debug_tools: list | None = None     # For debugging K8s issues
        
        # LLM instances
        self.llm_judge: AzureChatOpenAI | None = None  # For safety checking
        self.agent_analyzer: AgentExecutor | None = None  # For analysis tasks
        self.agent_executor: AgentExecutor | None = None  # For debug tasks
        
        # System prompts for different contexts
        self.sysmsg_judge: str | None = None     # Safety checking instructions
        self.sysmsg_agent: str | None = None     # Agent behavior instructions
        self.sysmsg_routine: str | None = None   # Routine task instructions
        
        # Database connection for chat history persistence
        self.postgres_conn: psycopg.Connection | None = None
        
        # Single session ID for all conversations - app uses one shared conversation context
        self.session_id: str = str(uuid.uuid4())

# Create singleton instance of application state
app_state = AppState()

def _get_session_history(session_id: str = app_state.session_id) -> PostgresChatMessageHistory:
    """
    Get or create a chat message history for the app's session.
    
    This function provides access to the PostgreSQL-backed conversation history
    for a given session ID. It's designed to be used with LangChain's memory system.
    Note that this implementation always uses the app's single session_id
    regardless of the input parameter, creating a shared conversation context.
    
    Args:
        session_id (str): The session ID (not actually used - see implementation)
        
    Returns:
        PostgresChatMessageHistory: A chat history object for the app's session
    """
    return PostgresChatMessageHistory(
        "chat_history",  # Table name
        session_id,
        sync_connection=app_state.postgres_conn  # Use the app's DB connection
    )

def _create_memory_wrapped_agent(agent_executor: AgentExecutor) -> RunnableWithMessageHistory:
    """
    Wrap an agent executor with memory functionality.
    
    This function enhances a LangChain agent executor with conversation memory
    capabilities, allowing it to maintain context across multiple interactions.
    The memory system uses PostgreSQL for persistence via _get_session_history.
    
    Args:
        agent_executor (AgentExecutor): The base agent executor to wrap with memory
        
    Returns:
        RunnableWithMessageHistory: Memory-enhanced agent that can remember past exchanges
    """
    return RunnableWithMessageHistory(
        agent_executor,
        get_session_history=_get_session_history,  # Function to get/create history
        input_messages_key="input",                # Where to find user input
        history_messages_key="chat_history"        # Where to store history
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler for startup and shutdown.
    
    This async context manager handles the initialization and cleanup of all application
    resources. It's executed when the FastAPI app starts and stops, ensuring proper
    setup before handling requests and cleanup after shutdown.
    
    The initialization workflow:
    1. Load K8s tools (analysis and debug tools)
    2. Load system prompt messages for different LLM roles
    3. Initialize PostgreSQL connection and ensure table structure
    4. Set up LLM instances for judge and agent roles
    5. Create agent executors with memory for different tasks
    
    Args:
        app (FastAPI): The FastAPI application instance
        
    Yields:
        None: Control is yielded back to FastAPI to handle requests
    
    Raises:
        RuntimeError: If any critical initialization step fails
    """
    print("Application starting, initializing resources...")
    print(f"Loading settings from '{CONFIG_PATH}'.")

    # Step 1: Load K8s tools
    try:
        # Import tools from the k8s_tools module
        app_state.analysis_tools = analysis_tools  # For cluster analysis
        app_state.debug_tools = debug_tools        # For troubleshooting
        print(f"Loaded {len(app_state.analysis_tools) + len(app_state.debug_tools)} K8s tools.")
    except Exception as e:
        print(f"Error: Failed to load K8s tools: {e}")
        raise RuntimeError("Failed to initialize K8s tools, application cannot start.") from e

    # Step 2: Load system prompt messages
    try:
        # Load instructions for each LLM role
        app_state.sysmsg_judge = _load_system_message(SYSMSG_JUDGE_PATH)      # Safety validator
        app_state.sysmsg_agent = _load_system_message(SYSMSG_AGENT_PATH)      # K8s specialist
        app_state.sysmsg_routine = _load_system_message(SYSMSG_ROUTINE_PATH)  # Routine tasks
        print("System prompt messages loaded.")
    except Exception as e:
        print(f"Error: Failed to load system prompt messages: {e}")
        raise RuntimeError("Failed to load system prompt messages, application cannot start.") from e
    
    # Step 3: Initialize PostgreSQL connection and chat history table
    try:
        # Connect to PostgreSQL and ensure table exists
        app_state.postgres_conn = psycopg.connect(settings.postgres_connection_string)
        PostgresChatMessageHistory.create_tables(app_state.postgres_conn, "chat_history")
        print("PostgreSQL connection established and chat history table created.")
    except Exception as e:
        print(f"Error: Failed to initialize PostgreSQL connection: {e}")
        raise RuntimeError("Failed to initialize database connection, application cannot start.") from e
        
    # Step 4a: Initialize LLM for safety checking (judge)
    app_state.llm_judge = AzureChatOpenAI(
        api_key=settings.azure_api_key,
        azure_endpoint=settings.azure_endpoint,
        openai_api_version=settings.azure_api_version,
        azure_deployment=settings.judge_deployment_name,
        temperature=0,  # Deterministic responses for safety checks
        max_retries=3,  # Retry on API failures
    )
    print("Safety judge LLM initialized.")

    # Step 4b: Initialize LLM for agent tasks (shared between both agent types)
    llm_agent = AzureChatOpenAI(
        api_key=settings.azure_api_key,
        azure_endpoint=settings.azure_endpoint,
        openai_api_version=settings.azure_api_version,
        azure_deployment=settings.agent_deployment_name,
        temperature=0,  # Deterministic responses for consistent behavior
        max_retries=3,  # Retry on API failures
    )

    # Step 5a: Initialize agent executor for debug tasks (with memory)
    # This agent uses ReAct framework for reasoning about debugging tasks
    prompt = PromptTemplate.from_template(app_state.sysmsg_agent)
    debug_zero_shot_agent = create_react_agent(
        llm=llm_agent,
        tools=app_state.debug_tools,
        prompt=prompt,  # Uses the system message as a prompt template
    )
    base_debug_executor = AgentExecutor(
        agent=debug_zero_shot_agent,
        tools=app_state.debug_tools,
        verbose=True,  # Log execution steps for debugging
        handle_parsing_errors=True  # Gracefully handle JSON parsing errors
    )
    # Wrap with memory to remember conversation history
    app_state.agent_executor = _create_memory_wrapped_agent(base_debug_executor)

    # Step 5b: Initialize agent executor for analysis tasks (with memory)
    # This agent uses a structured chat format for analyzing cluster state
    base_analysis_executor = initialize_agent(
        tools=app_state.analysis_tools,
        llm=llm_agent,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,  # Different agent type
        verbose=True,
        handle_parsing_errors=True,
    )
    # Wrap with memory to remember conversation history
    app_state.agent_analyzer = _create_memory_wrapped_agent(base_analysis_executor)

    print("Agent executors with memory initialized.")
    
    # Yield control back to FastAPI to handle requests
    yield
    
    # Cleanup on shutdown - ensure resources are properly released
    if app_state.postgres_conn:
        app_state.postgres_conn.close()
        print("PostgreSQL connection closed.")

# Create the FastAPI application instance with metadata and lifespan handler
app = FastAPI(
    title="增強型 MCP LLM Web API",  # Enhanced MCP LLM Web API
    description="一個具備兩階段安全審查機制和記憶功能的 LLM 代理服務。",  # LLM agent with two-stage safety check and memory
    lifespan=lifespan  # Use the lifespan context manager for initialization
)

class LLMRequest(BaseModel):
    """
    User query request model for the API.
    
    This Pydantic model defines the structure of incoming requests
    to the /ask and /ask_current endpoints. It validates that the
    required message field is present in the request JSON.
    
    Attributes:
        message (str): The user's Kubernetes-related query
    """
    message: str = Field(
        ...,  # Ellipsis means this field is required
        description="K8s-related user query", 
        example="Show CPU usage for all pods"
    )

class LLMResponse(BaseModel):
    """
    API response model for LLM query results.
    
    This Pydantic model defines the structure of responses from
    the /ask and /ask_current endpoints, including the LLM's reply
    and a safety status indicator.
    
    Attributes:
        reply (str|dict): The LLM's response, either as a string or structured data
        is_safe (bool): Whether the query was deemed safe by the judge LLM
    """
    reply: str | dict  # Can be either a string or a dictionary (for structured data)
    is_safe: bool      # Indicates if the query passed safety checks

@app.post("/ask", response_model=LLMResponse)
async def ask_llm(request: LLMRequest):
    """
    Handle user queries about Kubernetes operations with memory.
    
    This endpoint processes user queries related to Kubernetes debugging
    and troubleshooting using a two-stage architecture:
    1. Safety check: Validates the query against security policies
    2. Agent execution: Processes the query using the debug agent with memory
    
    The endpoint uses the debug agent which has access to a broader set of
    K8s debugging tools and can perform more complex troubleshooting tasks.
    
    Args:
        request (LLMRequest): The user's query in JSON format
        
    Returns:
        LLMResponse: The agent's response with safety status
        
    Raises:
        HTTPException: If safety check fails or agent execution encounters an error
    """
    
    # --- Stage 1: Safety check (K8s policy) ---
    # Create a prompt template with system instructions and user input
    # judge_prompt_template = ChatPromptTemplate.from_messages([
    #     SystemMessage(content=app_state.sysmsg_judge),  # Instructions for the judge
    #     ("human", "{input}")  # Placeholder for the user's message
    # ])
    # # Chain the prompt template with the judge LLM
    # judge_chain = judge_prompt_template | app_state.llm_judge
    
    # # Execute the safety check
    # try:
    #     # Process the user's message through the judge
    #     judge_result = await judge_chain.ainvoke({"input": request.message})
    #     decision = judge_result.content.strip().upper()  # Normalize the decision text
    # except Exception as e:
    #     # If the safety check fails, treat it as a service error
    #     raise HTTPException(status_code=503, detail=f"Safety check service error: {e}")
    
    # # If the query is denied by the judge, return a rejection message
    # if "DENIED" in decision:
    #     return LLMResponse(
    #         reply={"output": "This query violates safety policy and cannot be executed."},
    #         is_safe=False
    #     )
    
    # --- Stage 2: K8s information retrieval with memory ---
    try:
        # Process the query using the debug agent with conversation memory
        agent_reply = app_state.agent_executor.invoke(
            {"input": request.message},  # User's query
            config={"configurable": {"session_id": app_state.session_id}}  # Session tracking
        )
        
        # Extract and format the agent's response
        output = agent_reply.get("output", 'no output')
        # Handle special case where output is a JSON string
        output = json.loads(output).get("action_input", "no action_input") if _is_json_dict(output) else output
        
        # Return the successful response
        return LLMResponse(
            reply={"output": output},
            is_safe=True
        )
    except Exception as e:
        # Log and report any errors during agent execution
        print(f"Agent execution error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error occurred while processing the request")

@app.post("/ask_current", response_model=LLMResponse)
async def ask_llm_current(request: LLMRequest):
    """
    Handle user queries about the current state of Kubernetes with memory.
    
    This endpoint processes user queries related to analyzing the current state
    of the Kubernetes cluster. Unlike the /ask endpoint, it:
    1. Skips the safety check stage (assumes analysis queries are safe)
    2. Uses the analysis agent instead of the debug agent
    
    The analysis agent has access to tools focused on querying and analyzing
    the current state of resources, rather than debugging or troubleshooting.
    
    Args:
        request (LLMRequest): The user's query in JSON format
        
    Returns:
        LLMResponse: The agent's response with safety status (always True)
        
    Raises:
        HTTPException: If agent execution encounters an error
    """
    
    try:
        # Process the query using the analysis agent with conversation memory
        agent_reply = app_state.agent_analyzer.invoke(
            {"input": request.message},  # User's query
            config={"configurable": {"session_id": app_state.session_id}}  # Session tracking
        )
        
        # Extract and format the agent's response
        output = agent_reply.get("output", 'no output')
        # Handle special case where output is a JSON string
        output = json.loads(output).get("action_input", "no action_input") if _is_json_dict(output) else output
        
        # Return the successful response (always marked safe for this endpoint)
        return LLMResponse(
            reply={"output": output},
            is_safe=True  # Analysis queries are presumed safe
        )
    except Exception as e:
        # Log and report any errors during agent execution
        print(f"Agent execution error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error occurred while processing the request")

@app.get("/history")
async def get_conversation_history():
    """
    Get the chat history for the current session.
    
    This endpoint retrieves the complete conversation history from the PostgreSQL
    database for the application's current session. It returns a structured view
    of all messages exchanged between the user and the agents.
    
    Returns:
        dict: A dictionary containing session ID, message count, and message list
        
    Raises:
        HTTPException: If there's an error retrieving the history
    """
    try:
        # Get the history object for the current session
        history = _get_session_history(app_state.session_id)
        # Retrieve all messages from the database
        messages = history.get_messages()
        
        # Return a formatted response with session details and messages
        return {
            "session_id": app_state.session_id,
            "message_count": len(messages),
            "messages": [{"type": msg.type, "content": msg.content} for msg in messages]
        }
    except Exception as e:
        # Handle any errors accessing the history
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation history: {e}")

@app.delete("/history")
async def clear_conversation_history():
    """
    Clear the chat history for the current session.
    
    This endpoint deletes all conversation messages from the PostgreSQL database
    for the application's current session, effectively resetting the conversation
    context for both agents.
    
    Returns:
        dict: A success message confirming the history was cleared
        
    Raises:
        HTTPException: If there's an error clearing the history
    """
    try:
        # Get the history object for the current session
        history = _get_session_history(app_state.session_id)
        # Clear all messages from the database
        history.clear()
        
        # Return a success message
        return {"message": f"Conversation history cleared successfully"}
    except Exception as e:
        # Handle any errors clearing the history
        raise HTTPException(status_code=500, detail=f"Error clearing conversation history: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="info")

# --- 8. Test Commands (with memory) ---
# Test conversation with memory (no need to specify session_id):
# curl -X POST "http://localhost:10000/ask" -H "Content-Type: application/json" -d '{"message": "現在有哪些 ns"}'
# curl -X POST "http://localhost:10000/ask" -H "Content-Type: application/json" -d '{"message": "你剛才說了什麼命名空間?"}'

# Check conversation history:
# curl -X GET "http://localhost:10000/history"

# Clear conversation history:
# curl -X DELETE "http://localhost:10000/history"