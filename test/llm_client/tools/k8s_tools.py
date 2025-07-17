"""
Kubernetes Tools Module

This module provides a collection of tools for interacting with Kubernetes clusters,
retrieving logs from Loki, and metrics from Prometheus. It's designed to be used with
LangChain's tool system for AI assistants.

Key components:
- CurrentTimeTool: Get current time in UTC+8
- KubectlTool: Execute kubectl commands via SSH to a jump server
- LokiLabelsQueryTool: Query available labels from Loki
- LokiLogsQueryTool: Search logs using LogQL queries
- PrometheusCurrentPodsMetricsTool: Get metrics for Kubernetes pods

Configuration is loaded from config_tools.yml
"""
# 注意使用 LangChain 透過 Tools 的方式加入 Tool Functions 時，說明相關不能有 大跨號 會造成 LangChain 誤解
# 如果透過 LangChain 的 Tool Functions 方式加入，則會自動將 JSON 參數轉成 Tool Function 的參數

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
import yaml
import subprocess
import requests
from typing import Dict, Any, Type

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_tools.yml"

class Settings(BaseModel):
    """
    Configuration settings model for the K8s tools.
    
    Attributes:
        jump_server_host (str): Hostname of the jump server for SSH connections
        jump_server_ssh_arguments (str): SSH arguments used for connecting to the jump server
        loki_api_url (str): URL endpoint for the Loki API service
        prometheus_api_url (str): URL endpoint for the Prometheus API service
    """
    jump_server_host: str
    jump_server_ssh_arguments: str
    loki_api_url: str
    prometheus_api_url: str

def _load_settings(path: Path) -> Settings:
    """
    Load and validate settings from a YAML configuration file.
    
    Args:
        path (Path): Path to the configuration YAML file
        
    Returns:
        Settings: Validated settings object
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        ValueError: If the configuration file has invalid format or missing required fields
    """
    if not path.is_file():
        # 如果設定檔不存在，拋出一個明確的錯誤，並提示使用者如何建立
        raise FileNotFoundError(
            f"Configuration is not existed: {path}\n"
            f"Please create 'config_tools.yml' file and filled the settings."
        )
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return Settings(**config_data)
    except yaml.YAMLError as e:
        # 如果 YAML 格式錯誤，提供錯誤訊息
        raise ValueError(f"Config '{path}' Error format of settings: {e}")
    except Exception as e:
        # 捕捉其他可能的錯誤，例如 Pydantic 驗證失敗
        raise ValueError(f"Error occured while loading '{path}': {e}")

# Initialize settings at module load time
settings = _load_settings(CONFIG_PATH)

class CurrentTimeTool(BaseTool):
    """
    Tool for retrieving the current time in UTC+8 (Taiwan/China/Singapore) timezone.
    
    This simple tool can be used when timestamp information is needed for logging,
    querying time-based services, or providing time context to the user.
    
    Returns:
        Dict containing the current time in 'YYYY-MM-DD HH:MM:SS' format
    """
    name: str = "current_time"
    description: str = "Get the current time in UTC+8 timezone."
    
    def _run(self) -> Dict[str, str]:
        """
        Get the current time in UTC+8 timezone.
        
        Returns:
            Dict[str, str]: Dictionary with key 'current_time' and value as the formatted timestamp
        """
        from datetime import datetime, timezone, timedelta
        current_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
        return {"current_time": current_time}

class KubectlInput(BaseModel):
    """
    Input parameter model for the KubectlTool.
    
    Attributes:
        command (str): The shell command to execute on the jump server,
                      typically kubectl commands for K8s operations
    """
    command: str = Field(..., description="The command to execute on the jump server")

class KubectlTool(BaseTool):
    """
    Tool for executing kubectl commands remotely via SSH to a jump server.
    
    This tool allows execution of Kubernetes commands without direct access to the cluster,
    using a jump server as an intermediary. It's useful for retrieving cluster information,
    debugging, or performing administrative tasks.
    
    Security Note:
        Be careful with command execution privileges as this tool can run arbitrary commands
        on the jump server. Implement proper access controls in production environments.
    """
    name: str = "kubectl_command"
    description: str = ("Execute commands on specific Kubernetes nodes or within the cluster (e.g., kubectl)."
                       "Use for gathering detailed configuration, logs, or diagnostic information."
                       "This tool run kubectl command in a remote jump server via SSH."
                       "Carefully handle sensitive commands and ensure they are safe to execute.")
    args_schema: Type[BaseModel] = KubectlInput
    
    def _run(self, command: str) -> Dict[str, str]:
        """
        Execute a command on the jump server via SSH and return the results.
        
        Args:
            command (str): The shell command to execute
            
        Returns:
            Dict[str, str]: Dictionary containing:
                - status: 'success' or 'error'
                - output: Command output (stdout) or error message (stderr)
                - command: The original command (only included on error)
                
        Note:
            Commands timeout after 30 seconds to prevent hanging operations
        """
        try:
            base_cmd = f"{settings.jump_server_ssh_arguments} {settings.jump_server_host} '{command}'"
            result = subprocess.run(base_cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return {"status": "success", "output": result.stdout.replace(' ',''), "command": command}
            else:
                return {"status": "error", "output": result.stderr, "command": command}
        except Exception as e:
            return {"status": "error", "output": f"執行命令時發生錯誤: {str(e)}", "command": command}

class LokiLabelsQueryTool(BaseTool):
    """
    Tool for retrieving available labels and their values from Loki log management system.
    
    Loki organizes logs with labels (key-value pairs), and this tool helps discover
    what labels are available for filtering logs. It's an essential first step before
    using the LokiLogsQueryTool to construct meaningful log queries.
    
    Example labels might include:
        - app: "grafana", "prometheus", "nginx"
        - namespace: "monitoring", "default", "kube-system"
        - pod: "grafana-5f5f9f9f9f-5f5f9"
    """
    name: str = "loki_labels_query"
    description: str = ("Get all available labels and their values from Loki."
                        "Labels represent metadata fields that can be used to filter logs."
                        "This tool helps identify which labels are available for querying logs."
                        "The results will be returned in a structured format with label names and their values."
                        "This tool provides the hints for constructing LogQL queries."
                        "For instance, you can use labels like 'app' and its values like 'grafana' or 'prometheus'."
                        "Therefore, the query should be in LogQL format, such as a dictionary label (eg. app) = value (eg. grafana).")
    
    def _run(self) -> Dict[str, Any]:
        """
        Query the Loki API for available labels and their values.
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - status: 'success' or 'error'
                - labels: List of available label names and values (on success)
                - error: Error message (on failure)
                
        Note:
            API request times out after 30 seconds
        """
        try:
            # 發送請求到 Loki API
            response = requests.get(
                f"{settings.loki_api_url}/labels",
                timeout=30
            )
            
            # 確保請求成功
            response.raise_for_status()
            
            # 解析並返回標籤數據
            labels_data = response.json()
            return {
                "status": "success",
                "labels": labels_data.get('labels', {})
            }
            
        except requests.exceptions.RequestException as e:
            # 處理 HTTP 請求錯誤
            return {
                "status": "error",
                "error": f"Loki API Request Error: {str(e)}"
            }
        except Exception as e:
            # 處理其他錯誤
            return {
                "status": "error",
                "error": f"Error occurred when getting the labels: {str(e)}"
            }

class LokiLogsQueryInput(BaseModel):
    query: str = Field(..., description="LogQL query string (e.g., dictionary: label = value)")
    start_time: str = Field(..., description="Start time in 'YYYY-MM-DD HH:MM:SS' format (UTC+8 timezone)")
    end_time: str = Field(..., description="End time in 'YYYY-MM-DD HH:MM:SS' format (UTC+8 timezone)")
    limit: int = Field(1000, description="Maximum number of log entries to return")
    debug: bool = Field(False, description="Enable debug mode for additional logging")

class LokiLogsQueryTool(BaseTool):
    """
    Tool for querying logs from Loki using LogQL within a specified time range.
    
    This tool helps find application logs, error messages, or other log data using
    Loki's query language (LogQL). By default, it filters out info-level logs to focus
    on warnings, errors, and critical issues unless debug mode is enabled.
    
    Recommended usage:
    1. First use LokiLabelsQueryTool to discover available labels
    2. Construct a LogQL query using those labels
    3. Specify a time range and use this tool to retrieve matching logs
    
    """
    name: str = "loki_logs_query"
    description: str = ("Look up the label and value ffrom the tool named LokiLabelsQueryTool."
                        "The information for LokiLabelsQueryTool would be helpful to construct the LogQL query."
                        "This tool provides the logs level higher than info (information) by default."
                        "If you want to get all logs, please set the debug parameter to True."
                        "Query logs from Loki using LogQL within a specified time range. "
                        "Use this tool to search for application logs, error messages, or other log data. "
                        "The query should be in LogQL format, such as a dictionary label = value. "
                        "Do not use literal placeholders like 'label' eg. app or value eg. grafana. "
                        "The results will be returned in a structured format with actual log data. "
                        "Determine the most relevant labels and values to filter logs effectively. "
                        "The time range should be specified in 'YYYY-MM-DD HH:MM:SS' format (UTC+8 timezone)."
                        "If the tool cannot find useful logs, trying to use KubectlTool for more detailed logs.")
    args_schema: Type[BaseModel] = LokiLogsQueryInput
    
    def _run(self, query: str, start_time: str, end_time: str, limit: int = 1000, debug: bool= False) -> Dict[str, Any]:
        """
        Query logs from Loki based on LogQL query and time range.
        
        Args:
            query (str): LogQL query string for filtering logs
            start_time (str): Start time in 'YYYY-MM-DD HH:MM:SS' format
            end_time (str): End time in 'YYYY-MM-DD HH:MM:SS' format
            limit (int, optional): Maximum number of logs to return. Defaults to 1000.
            debug (bool, optional): Whether to include info-level logs. Defaults to False.
            
        Returns:
            Dict[str, Any]: Dictionary containing:
                - status: 'success' or 'error'
                - target: The stream identifier from which logs were retrieved
                - logs: List of log entries with timestamps
                - error: Error message (only on failure)
                
        Note:
            When debug=False (default), info-level logs are filtered out to focus on issues
        """
        try:
            # 構建 API 請求參數
            params = {
                'query': query,
                'start_time': start_time,
                'end_time': end_time,
                'limit': limit
            }
            
            # 發送請求到 Loki API
            response = requests.get(
                f"{settings.loki_api_url}/logs",
                params=params,
                timeout=30
            )
            
            # 確保請求成功
            response.raise_for_status()
            
            # 解析並返回日誌數據
            logs_data = response.json()

            if debug:
                return {
                    "status": "success",
                    "target": logs_data.get('stream', 'unknown'),
                    "logs": logs_data.get('values', [])
                }
            else:
                # 留下除了 info 以外的日誌 (by default)
                logs = logs_data.get('values', [])
                if logs:
                    lstTmp = list()
                    for log in logs:
                        if 'info' not in log.get("log",'').lower():
                            lstTmp.append(log)
                        else:
                            pass
                    return {
                        "status": "success",
                        "target": logs_data.get('stream', 'unknown'),
                        "logs": lstTmp if lstTmp else [{'timestamp': end_time, 'log': 'No critical logs found'}]
                    }
                
        except requests.exceptions.RequestException as e:
            # 處理 HTTP 請求錯誤
            return {
                "status": "error",
                "error": f"Loki API Request Error: {str(e)}",
                "query": query
            }
        except Exception as e:
            # 處理其他錯誤
            return {
                "status": "error",
                "error": f"Error occurred when querying logs: {str(e)}",
                "query": query
            }

class PrometheusCurrentPodsMetricsTool(BaseTool):
    """
    Tool for retrieving current metrics for all monitored Kubernetes pods from Prometheus.
    
    This tool provides a comprehensive overview of pod performance metrics, including:
    - CPU usage (cores and percentage)
    - Memory usage (bytes and percentage)
    - Network I/O (bytes in/out)
    - Pod status (running, pending, failed, etc.)
    
    Results are grouped by namespace for better organization. The tool only provides
    current point-in-time metrics, not historical data, and does not include disk I/O metrics.
    
    This is useful for monitoring cluster health, identifying resource bottlenecks,
    or troubleshooting performance issues with specific pods.
    """
    name: str = "prometheus_pods_metrics"
    description: str = ("Get comprehensive metrics for all monitored Kubernetes pods,"
                        "including CPU usage, memory usage, network I/O, and pod status."
                        "This tool does not provide historical data, only current metrics."
                        "This tool does not provide Disk I/O metrics."
                        "Results are grouped by namespace.")
    
    def _run(self) -> Dict[str, Any]:
        """
        Query the Prometheus API for current pod metrics across the cluster.
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - status: 'success' or 'error'
                - pods_metrics: Metrics data organized by namespace and pod (on success)
                - error: Error message (on failure)
                
        Note:
            API request times out after 30 seconds
        """
        try:
            # 發送請求到自定義的 Prometheus API
            response = requests.get(
                f"{settings.prometheus_api_url}/pods",
                timeout=30
            )
            
            # 確保請求成功
            response.raise_for_status()
            
            # 解析並返回 Pod 指標數據
            pods_metrics = response.json()
            return {
                "status": "success",
                "pods_metrics": pods_metrics
            }
            
        except requests.exceptions.RequestException as e:
            # 處理 HTTP 請求錯誤
            return {
                "status": "error",
                "error": f"Prometheus API Request Failed: {str(e)}"
            }
        except Exception as e:
            # 處理其他錯誤
            return {
                "status": "error",
                "error": f"Error occurred when getting the metrics of the Pods: {str(e)}"
            }

# Export collections of tools for different use cases
analysis_tools = [
    CurrentTimeTool(),
    KubectlTool(),
    LokiLabelsQueryTool(),
    LokiLogsQueryTool(),
    PrometheusCurrentPodsMetricsTool()
]

debug_tools = [KubectlTool()]

if __name__ == "__main__":
    # print(LokiLabelsQueryTool()._run())
    # print(LokiLogsQueryTool()._run(
    #     query='{app="grafana"}',
    #     start_time='2025-07-15 13:20:00',
    #     end_time='2025-07-15 13:24:00',
    #     debug=True
    # ))
    # print(CurrentTimeTool()._run())
    ...