from fastapi import FastAPI, HTTPException, Query
import requests
import datetime
import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Tuple
import logging
from typing import Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI application with metadata
app = FastAPI(
    title="Loki Query API",
    description="A FastAPI service for querying logs from Loki",
    version="1.0.0"
)

# Configuration
# Define paths for configuration files
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_apiserver.yml"

class LogEntry(BaseModel):
    """
    Model for individual log entries.
    
    Attributes:
        timestamp (str): ISO 8601 formatted timestamp
        log (str): The actual log message
    """
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    log: str = Field(..., description="The actual log message")

class LogQueryResponse(BaseModel):
    """
    Response model for log queries.
    
    Attributes:
        stream (Dict[str, Any]): Stream labels/metadata
        values (List[LogEntry]): List of log entries
    """
    stream: Dict[str, Any] = Field(..., description="Stream labels and metadata")
    values: List[LogEntry] = Field(..., description="List of log entries")

class LabelsResponse(BaseModel):
    """
    Response model for labels endpoint.
    
    Attributes:
        labels (Dict[str, List[str]]): Dictionary mapping label names to their possible values
    """
    labels: Dict[str, List[str]] = Field(..., description="Dictionary mapping label names to their possible values")

class Settings(BaseModel):
    """
    Configuration settings model for the Loki API server.
    
    Attributes:
        loki_url (str): The URL of the Loki server to connect to
    """
    loki_url: str

def _load_settings(path: Path) -> Settings:
    """
    Load and validate configuration settings from a YAML file.
    
    This function reads the configuration file, validates its structure,
    and returns a Settings object with the parsed configuration.
    
    Args:
        path (Path): Path to the YAML configuration file
        
    Returns:
        Settings: Validated configuration settings object
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        ValueError: If the YAML format is invalid or required fields are missing
    """
    # Check if configuration file exists
    if not path.is_file():
        raise FileNotFoundError(
            f"設定檔不存在於: {path}\n"
            f"請在專案根目錄建立一個 'config_apiserver.yml' 檔案，並填入必要的設定。"
        )
    try:
        # Read and parse YAML configuration file
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        # Validate configuration using Pydantic model
        return Settings(**config_data)
    except yaml.YAMLError as e:
        raise ValueError(f"設定檔 '{path}' 格式錯誤: {e}")
    except Exception as e:
        raise ValueError(f"載入設定檔 '{path}' 時發生錯誤: {e}")

# Load configuration settings at startup
settings = _load_settings(CONFIG_PATH)

# Helper functions (refactored from the original functions)
def _get_loki_labels_values() -> Tuple[Dict[str, List[str]], Optional[Dict[str, str]]]:
    """
    Internal helper function to fetch available label names and their values from Loki.
    
    This function communicates with the Loki API to retrieve all available labels
    and their corresponding values. Labels represent the 'targets' or streams of logs.
    
    Returns:
        Tuple[Dict[str, List[str]], Optional[Dict[str, str]]]: 
            - First element: Dictionary mapping label names to lists of their values
            - Second element: Error details if any, None on success
            
    Example:
        labels, error = _get_loki_labels_values()
        if error is None:
            print(labels)  # {'app':grafana ['nginx', 'app'], 'level': ['info', 'error']}
    """
    try:
        logger.info("Fetching labels from Loki API")
        response = requests.get(f"{settings.loki_url}/loki/api/v1/labels")
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'success':
            label_values = dict()
            for label in data['data']:
                # Fetch values for each label
                values_response = requests.get(f"{settings.loki_url}/loki/api/v1/label/{label}/values")
                values_response.raise_for_status()
                values_data = values_response.json()
                
                if values_data['status'] == 'success':
                    label_values[label] = values_data['data']
                else:
                    return {}, {"error": values_data.get('error', 'Unknown error'), "status": values_data['status']}
            logger.info(f"Successfully fetched {len(label_values)} labels")
            return label_values, None
        else:
            return {}, {"error": data.get('error', 'Unknown error'), "status": data['status']}
    
    except Exception as e:
        logger.error(f"Error fetching labels: {e}")
        return {}, {"error": f"An unexpected error occurred: {e}", "status": "unknown_error"}

def _query_loki_logs(query: str, start_time_str: str, end_time_str: str, limit: int = 1000) -> Tuple[Dict[str, Any], Optional[Dict[str, str]]]:
    """
    Internal helper function to query Loki for logs matching a LogQL query within a specified time range.
    
    This function sends a query to Loki's query_range endpoint to retrieve log entries
    that match the specified LogQL query within the given time range.
    
    Args:
        query (str): The LogQL query string (e.g., '{app="grafananginx"}')
        start_time_str (str): Start time in 'YYYY-MM-DD HH:MM:SS' format (This function would minus 8 hours for UTC-8 timezone)
        end_time_str (str): End time in 'YYYY-MM-DD HH:MM:SS' format (This function would minus 8 hours for UTC-8 timezone)
        limit (int): The maximum number of log lines to retrieve. Default is 1000.
        
    Returns:
        Tuple[Dict[str, Any], Optional[Dict[str, str]]]:
            - First element: Dictionary containing stream info and log values
            - Second element: Error details if any, None on success
            
    Example:
        logs, error = _query_loki_logs('{app="grafananginx"}', '2024-01-01 10:00:00', '2024-01-01 11:00:00', 100)
        if error is None:
            print(logs['values'])  # List of log entries
    """
    try:
        logger.info(f"Querying Loki with query: {query}")
        # UTC-8 timezone adjustment
        start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=8)
        end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=8) 

        params = {
            'query': query,
            'start': int(start_time.timestamp() * 1e9), # Loki expects nanoseconds
            'end': int(end_time.timestamp() * 1e9),     # Loki expects nanoseconds
            'limit': limit
        }
        response = requests.get(f"{settings.loki_url}/loki/api/v1/query_range", params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'success':
            # Format the output for easier consumption in an API
            formatted_results = {}
            if data.get('data','').get('resultType','') == 'streams': # Ensure it's stream data
                for result in data.get('data','').get('result',''):
                    stream_labels = result.get('stream')
                    values = []
                    for entry in result.get('values'):
                        timestamp_ns = int(entry[0])
                        log_line = entry[1]
                        timestamp = datetime.datetime.fromtimestamp(timestamp_ns / 1e9).isoformat() # ISO 8601
                        values.append({"timestamp": timestamp, "log": log_line})
                    formatted_results.update({"stream": stream_labels, "values": values})
            logger.info(f"Successfully retrieved {len(formatted_results.get('values', []))} log entries")
            return formatted_results, None
        else:
            return {}, {"error": data.get('error', 'Unknown error'), "status": data['status']}
    except Exception as e:
        logger.error(f"Error querying logs: {e}")
        return {}, {"error": f"An unexpected error occurred: {e}", "status": "unknown_error"}

# FastAPI endpoints
@app.get("/labels", 
         response_model=LabelsResponse,
         summary="Get available log labels",
         description="Retrieve all available labels and their values from Loki. Labels represent the metadata fields that can be used to filter logs.",
         response_description="Dictionary mapping label names to their possible values")
async def get_labels():
    """
    Get all available labels and their values from Loki.
    
    This endpoint fetches all available labels from Loki, which represent the metadata
    fields that can be used to filter and query logs. Each label has a set of possible
    values that can be used in LogQL queries.
    
    Returns:
        LabelsResponse: Dictionary containing all labels and their possible values
        
    Raises:
        HTTPException: If there's an error communicating with Loki or processing the response
        
    Example:
        GET /labels
        Response: {"label-1": ['calico-node', 'loki'], "label-2": ['grafana']}
    """
    labels, error = _get_loki_labels_values()
    
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    return LabelsResponse(labels=labels)

@app.get("/logs",
         response_model=Union[LogQueryResponse, dict],
         summary="Query logs from Loki",
         description="Query logs from Loki using LogQL within a specified time range",
         response_description="Log entries matching the query criteria")
async def get_logs(
    query: str = Query(..., description="LogQL query string", examples='{app="tempo"}'),
    start_time: str = Query(..., description="Start time in 'YYYY-MM-DD HH:MM:SS' format", examples="2024-01-01 10:00:00"),
    end_time: str = Query(..., description="End time in 'YYYY-MM-DD HH:MM:SS' format", examples="2024-01-01 11:00:00"),
    limit: int = Query(default=1000, description="Maximum number of log entries to return", examples=100)
):
    """
    Query logs from Loki using LogQL within a specified time range.
    
    This endpoint allows you to query logs from Loki using LogQL (Log Query Language).
    You can specify time ranges and limit the number of results returned.
    
    Args:
        query (str): LogQL query string (e.g., '{app="grafananginx"}', '{level="error"}')
        start_time (str): Start time in 'YYYY-MM-DD HH:MM:SS' format (Use UTC+8 timezone)
        end_time (str): End time in 'YYYY-MM-DD HH:MM:SS' format (Use UTC+8 timezone)
        limit (int): Maximum number of log entries to return (default: 1000)
        
    Returns:
        LogQueryResponse: Log entries matching the query criteria (JSON format containing "stream" and "values", the "values" contains a list of logs including "timestamp" (UTC+0), "log")
        
    Raises:
        HTTPException: If there's an error with the query or communicating with Loki
        
    Example:
        GET /logs?query={app="tempo"}&start_time='2024-01-01 10:00:00'&end_time='2024-01-01 11:00:00'&limit=100
    """
    logs, error = _query_loki_logs(query, start_time, end_time, limit)
    if error:
        raise HTTPException(status_code=500, detail=error)
    if logs:
        return LogQueryResponse(**logs)
    return {}

@app.get("/health",
         summary="Health check endpoint",
         description="Check if the API server is running and can connect to Loki",
         response_description="Health status information")
async def health_check():
    """
    Health check endpoint to verify API server status and Loki connectivity.
    
    This endpoint provides a simple way to check if the API server is running
    and can successfully communicate with the configured Loki instance.
    
    Returns:
        dict: Health status information including timestamp and Loki connectivity
        
    Example:
        GET /health
        Response: {
            "status": "healthy",
            "timestamp": "2024-01-01T10:00:00",
            "loki_url": "http://loki:3100",
            "loki_accessible": true
        }
    """
    try:
        # Test Loki connectivity
        response = requests.get(f"{settings.loki_url}/ready", timeout=5)
        loki_accessible = response.status_code == 200
    except:
        loki_accessible = False
    
    return {
        "status": "healthy" if loki_accessible else "degraded",
        "timestamp": datetime.datetime.now().isoformat(),
        "loki_url": settings.loki_url,
        "loki_accessible": loki_accessible
    }

if __name__ == "__main__":
    import uvicorn
    # print(_get_loki_labels_values())
    # print(_query_loki_logs('{app="grafana"}', '2025-07-15 13:20:00', '2025-07-15 13:24:00'))
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
