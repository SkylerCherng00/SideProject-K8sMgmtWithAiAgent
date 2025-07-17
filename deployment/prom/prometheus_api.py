# Import necessary libraries for FastAPI web framework and Prometheus integration
from fastapi import FastAPI, HTTPException
from typing import Dict
from datetime import datetime, timedelta
from prometheus_api_client import PrometheusConnect  # Client library for Prometheus API
from pathlib import Path
from pydantic import BaseModel  # For data validation and settings management
import yaml
from collections import defaultdict  # For efficient grouping operations

# Initialize FastAPI application with metadata
app = FastAPI(
    title="Prometheus Query API",
    description="A FastAPI service for querying metrics from Prometheus",
    version="1.0.0"
)

# Define paths for configuration files
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_apiserver.yml"

# Pydantic model for configuration validation
class Settings(BaseModel):
    """
    Configuration settings model for the Prometheus API server.
    
    Attributes:
        prometheus_url (str): The URL of the Prometheus server to connect to
    """
    prometheus_url: str

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

def _query_metrics_timeframe(
    promql_query: str, 
    start_time: datetime, 
    end_time: datetime, 
    step_size: str = "30s"
) -> dict:
    """
    Execute a PromQL range query against Prometheus over a specified time period.
    
    This function connects to Prometheus and executes a range query, which is useful
    for retrieving time series data over a specific time window. Range queries are
    ideal for monitoring dashboards and historical data analysis.

    Args:
        promql_query (str): The PromQL expression to execute (e.g., 'node_cpu_seconds_total')
        start_time (datetime): The start timestamp of the query range
        end_time (datetime): The end timestamp of the query range
        step_size (str): The resolution step width for the query (e.g., "1m", "30s")

    Returns:
        dict: Query results in Prometheus matrix format containing time series data
              with timestamps and values, or error information if the query fails
              
    Example:
        >>> start = datetime.now() - timedelta(hours=1)
        >>> end = datetime.now()
        >>> result = _query_metrics_timeframe('up', start, end, '1m')
    """
    # Initialize the PrometheusConnect client with the configured URL
    prom = PrometheusConnect(url=settings.prometheus_url)

    try:
        # Execute the range query using the prometheus_api_client library
        # The custom_query_range method calls the /api/v1/query_range endpoint
        # Returns time series data with timestamps and values for the specified range
        query_results = prom.custom_query_range(
            query=promql_query,
            start_time=start_time,
            end_time=end_time,
            step=step_size
        )

        # Return the raw results (list of dictionaries with metric metadata and values)
        return query_results

    except Exception as e:
        # Log and return error information for debugging
        print(f"Error executing range query: {e}")
        return {"error": str(e)}

@app.get("/")
async def root():
    """
    Root endpoint providing API information and available endpoints.
    
    Returns:
        dict: API metadata including version and available endpoints
    """
    return {
        "message": "Prometheus Query API",
        "version": "1.0.0",
        "endpoints": {
            "pods": "/query - Pods metrics within 1 minute",
            "health": "/health - Health check"
        }
    }

@app.get("/prom/health")
async def health_check():
    """
    Health check endpoint to verify API and Prometheus connectivity.
    
    This endpoint performs a simple query to Prometheus to ensure the service
    is healthy and can communicate with the Prometheus server.
    
    Returns:
        dict: Health status and Prometheus URL
        
    Raises:
        HTTPException: 503 status if Prometheus is unreachable
    """
    try:
        # Create Prometheus client and test connectivity
        prom = PrometheusConnect(url=settings.prometheus_url)
        # Execute a simple query to verify Prometheus is accessible
        prom.custom_query("up")  # "up" is a standard Prometheus metric
        return {"status": "healthy", "prometheus_url": settings.prometheus_url}
    except Exception as e:
        # Return 503 Service Unavailable if Prometheus is not accessible
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/prom/pods")
async def get_pods_metrics() -> Dict:
    """
    Retrieve comprehensive metrics for all monitored Kubernetes pods.
    
    This endpoint provides a complete overview of pod metrics including:
    - Pod information (namespace, service, pod name, node)
    - CPU usage metrics (Average CPU utilization of the entire pod in **CPU core per second**)
    - Memory usage metrics (Bytes of memory used by the pod)  
    - Network I/O metrics (Bytes received and transmitted by the pod)
    - Pod status information (1.0 if running, 0 if not)
    
    The data is grouped by namespace for better organization and covers
    the last 3 minutes of metrics data.
    
    Returns:
        Dict: Nested dictionary with namespaces as keys and pod metrics as values
              Each pod entry contains CPU, memory, network, and status metrics
              
    Example response structure:
        {
            "default": [
                {
                    "namespace": "default",
                    "service": "web-service",
                    "pod": "web-pod-123",
                    "node": "node-1",
                    "cpu": [0.1, 0.2, 0.15],
                    "mem": [1024.4, 1100.5, 1050.6],
                    "net_in": [100.12, 150.15, 120.45],
                    "net_out": [80.66, 90.05, 85.08],
                    "pod_status": [1.0, 1.0, 1.0]
                }
            ]
        }
    """
    # Define time range for metrics collection (last 3 minutes)
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=3)

    # Step 1: Query basic pod information using kube_pod_info metric
    # This metric provides metadata about all pods in the cluster
    query = _query_metrics_timeframe('kube_pod_info', start_time, end_time)
    
    # Extract pod metadata from the query results
    lstTmp = []
    for i in query:
        # Each result contains metric labels with pod information
        lstTmp.append({
            "namespace": i.get('metric', 'lost metric').get("namespace", 'lost ns'),
            "service": i.get('metric', 'lost metric').get("service", 'lost svc'),
            "pod": i.get('metric', 'lost metric').get("pod", 'lost pod'),
            "node": i.get('metric', 'lost metric').get("node", 'lost node'),
        })
    
    # Step 2: Group pods by namespace for organized output
    # Using defaultdict for efficient grouping
    grouped_by_namespace = defaultdict(list)
    for item in lstTmp:
        namespace = item.get("namespace", "unknown")  # Handle missing namespace
        grouped_by_namespace[namespace].append(item)

    # Convert defaultdict to regular dict for JSON serialization
    grouped_by_namespace = dict(grouped_by_namespace)
    del lstTmp  # Clean up temporary list

    # Step 3: Define PromQL queries for different pod metrics
    # Each query uses "***" as a placeholder for the pod name
    query_conditions = {
        # CPU usage rate over 1 minute window
        'cpu': 'sum(rate(container_cpu_usage_seconds_total{pod="***"}[1m])) by (pod)',
        
        # Memory working set bytes rate over 1 minute
        'mem': 'sum(rate(container_memory_working_set_bytes{pod="***"}[1m])) by (pod)',
        
        # Network receive bytes rate over 1 minute
        'net_in': 'sum(rate(container_network_receive_bytes_total{pod="***"}[1m])) by (pod)',
        
        # Network transmit bytes rate over 1 minute
        'net_out': 'sum(rate(container_network_transmit_bytes_total{pod="***"}[1m])) by (pod, namespace)',
        
        # Pod status (1 if running, 0 if not)
        'pod_status': 'kube_pod_status_phase{pod="***", phase="Running"}'
    }

    # Step 4: Collect metrics for each pod in each namespace
    keys = grouped_by_namespace.keys()
    for namespace in keys:
        for pod_info in grouped_by_namespace.get(namespace):
            podname = pod_info.get('pod')
            
            # Query each metric type for the current pod
            for key in query_conditions.keys():
                # Replace placeholder with actual pod name
                query_string = query_conditions.get(key).replace("***", podname)
                
                # Execute the metric query
                rslt = _query_metrics_timeframe(
                    query_string,
                    start_time, 
                    end_time
                )
                
                # Extract values from the time series result
                # Convert string values to floats for numerical processing
                if rslt and len(rslt) > 0 and 'values' in rslt[0]:
                    value = [float(sublist[-1]) for sublist in rslt[0].get('values')]
                else:
                    value = []  # Handle empty results
                
                # Add the metric values to the pod information
                pod_info.update({key: value})

    # Return the complete metrics data grouped by namespace
    return grouped_by_namespace

# Application entry point for development server
if __name__ == "__main__":
    import uvicorn
    # Run the FastAPI application with uvicorn ASGI server
    # Listen on all interfaces (0.0.0.0) on port 10002
    uvicorn.run(app, host="0.0.0.0", port=10002, log_level="info")
