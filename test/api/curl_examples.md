# Loki API - Curl Examples

This document provides comprehensive curl examples for testing the Loki FastAPI endpoints.

## Prerequisites

1. Ensure your FastAPI server is running:
   ```bash
   python loki_api.py
   ```
   The server will be available at `http://192.168.72.10:8000`

2. Make sure you have a running Loki instance and the `config_apiserver.yml` file is properly configured.

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API server is running and can connect to Loki.

```bash
curl -X GET "http://192.168.72.10:8000/health" \
  -H "accept: application/json"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00.000000",
  "loki_url": "http://loki:3100",
  "loki_accessible": true
}
```

### 2. Get Labels

**Endpoint:** `GET /labels`

**Description:** Retrieve all available labels and their values from Loki.

```bash
curl -X GET "http://192.168.72.10:8000/labels" \
  -H "accept: application/json"
```

**Expected Response:**
```json
{
  "labels": {
    "job": ["nginx", "app", "system"],
    "level": ["info", "error", "debug"],
    "app": ["calico-node", "calico-kube-controllers"]
  }
}
```

### 3. Query Logs (GET)

**Endpoint:** `GET /logs`

**Description:** Query logs from Loki using LogQL within a specified time range.

#### Basic Query

```bash
curl -X GET "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -G \
  --data-urlencode "query={job=\"o11y/grafana\"}" \
  --data-urlencode "start_time=2025-07-15 12:00:00" \
  --data-urlencode "end_time=2025-07-15 12:30:00" \
  --data-urlencode "limit=100"
```

#### Advanced Queries

**Query with multiple labels:**
```bash
curl -X GET "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -G \
  --data-urlencode "query={job=\"nginx\", level=\"error\"}" \
  --data-urlencode "start_time=2024-01-01 10:00:00" \
  --data-urlencode "end_time=2024-01-01 11:00:00" \
  --data-urlencode "limit=50"
```

**Query with regex pattern:**
```bash
curl -X GET "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -G \
  --data-urlencode "query={job=~\".*nginx.*\"}" \
  --data-urlencode "start_time=2024-01-01 10:00:00" \
  --data-urlencode "end_time=2024-01-01 11:00:00" \
  --data-urlencode "limit=100"
```

**Query with log content filter:**
```bash
curl -X GET "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -G \
  --data-urlencode "query={job=\"nginx\"} |= \"error\"" \
  --data-urlencode "start_time=2024-01-01 10:00:00" \
  --data-urlencode "end_time=2024-01-01 11:00:00" \
  --data-urlencode "limit=100"
```

**Query for recent logs (last hour):**
```bash
# First, get current time in the required format
current_time=$(date '+%Y-%m-%d %H:%M:%S')
one_hour_ago=$(date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S')

curl -X GET "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -G \
  --data-urlencode "query={job=~\".+\"}" \
  --data-urlencode "start_time=$one_hour_ago" \
  --data-urlencode "end_time=$current_time" \
  --data-urlencode "limit=10"
```

### 4. Query Logs (POST)

**Endpoint:** `POST /logs`

**Description:** Query logs from Loki via POST request (useful for complex queries).

#### Basic POST Query

```bash
curl -X POST "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{job=\"nginx\"}",
    "start_time": "2024-01-01 10:00:00",
    "end_time": "2024-01-01 11:00:00",
    "limit": 100
  }'
```

#### Complex POST Query

```bash
curl -X POST "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{job=\"nginx\", level=\"error\"} |= \"timeout\" |~ \".*connection.*\"",
    "start_time": "2024-01-01 10:00:00",
    "end_time": "2024-01-01 11:00:00",
    "limit": 50
  }'
```

## Expected Response Format

All log query endpoints return responses in the following format:

```json
{
  "stream": {
    "job": "nginx",
    "level": "info",
    "app": "web-server"
  },
  "values": [
    {
      "timestamp": "2024-01-01T10:30:00.000000",
      "log": "192.168.1.1 - - [01/Jan/2024:10:30:00 +0000] \"GET /api/health HTTP/1.1\" 200 15"
    },
    {
      "timestamp": "2024-01-01T10:31:00.000000",
      "log": "192.168.1.2 - - [01/Jan/2024:10:31:00 +0000] \"POST /api/logs HTTP/1.1\" 201 1234"
    }
  ]
}
```

## Error Handling

If an error occurs, the API will return an HTTP error status with details:

```json
{
  "detail": {
    "error": "Invalid LogQL query",
    "status": "query_error"
  }
}
```

## Common LogQL Query Examples

### Basic Label Matching
- `{job="nginx"}` - All logs from nginx job
- `{job="nginx", level="error"}` - Error logs from nginx
- `{job=~"nginx.*"}` - Jobs starting with "nginx"

### Content Filtering
- `{job="nginx"} |= "error"` - Logs containing "error"
- `{job="nginx"} |~ ".*timeout.*"` - Logs matching regex pattern
- `{job="nginx"} != "debug"` - Logs not containing "debug"

### Time-based Queries
- Use the start_time and end_time parameters in 'YYYY-MM-DD HH:MM:SS' format
- Times are interpreted in the server's timezone

## Testing with Different Time Ranges

### Last 10 minutes
```bash
current_time=$(date '+%Y-%m-%d %H:%M:%S')
ten_minutes_ago=$(date -d '10 minutes ago' '+%Y-%m-%d %H:%M:%S')

curl -X GET "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -G \
  --data-urlencode "query={job=~\".+\"}" \
  --data-urlencode "start_time=$ten_minutes_ago" \
  --data-urlencode "end_time=$current_time" \
  --data-urlencode "limit=20"
```

### Specific time range
```bash
curl -X GET "http://192.168.72.10:8000/logs" \
  -H "accept: application/json" \
  -G \
  --data-urlencode "query={job=\"nginx\"}" \
  --data-urlencode "start_time=2024-01-01 09:00:00" \
  --data-urlencode "end_time=2024-01-01 17:00:00" \
  --data-urlencode "limit=100"
```

## Interactive API Documentation

Once your server is running, you can also access the interactive API documentation:

- **Swagger UI:** `http://192.168.72.10:8000/docs`
- **ReDoc:** `http://192.168.72.10:8000/redoc`

These interfaces provide a user-friendly way to test the API endpoints with proper validation and examples.
