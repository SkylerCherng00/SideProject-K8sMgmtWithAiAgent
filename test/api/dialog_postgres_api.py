import logging
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import datetime

# Import the RecordAPI from postres_utils
from postgres_utils.record_crud import RecordAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Create FastAPI app instance
app = FastAPI(
    title="Dialog API",
    description="API for storing and retrieving dialog messages in PostgreSQL",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Define data models
class DialogRequest(BaseModel):
    """
    Model for dialog request data
    
    Attributes:
        user_id (int): The ID of the user
        session_id (str): Session identifier for the conversation
        user_message (str): Message from the user
        system_message (str): Response from the system
    """
    user_id: int = Field(default=1, description="User identifier")
    session_id: str = Field(..., description="Session identifier")
    user_message: str = Field(..., description="Message from the user")
    system_message: str = Field(..., description="Response from the system")

class DialogResponse(BaseModel):
    """
    Model for dialog response data
    
    Attributes:
        timestamp (int): Unix timestamp of when the dialog was recorded
        user_id (int): The ID of the user
        session_id (str): Session identifier for the conversation
        user_message (str): Message from the user
        system_message (str): Response from the system
    """
    timestamp: int
    user_id: int
    session_id: str
    user_message: str
    system_message: str

class StatusResponse(BaseModel):
    """
    Model for status response
    
    Attributes:
        status (str): Operation status (success/failed)
        timestamp (str): ISO formatted timestamp
        message (str): Additional status message
    """
    status: str
    timestamp: str
    message: str

# Define API endpoints
@app.get("/dialogs/health", response_model=StatusResponse, tags=["Health"])
async def health_check():
    """
    Check if the API server and database connection are working
    
    Returns:
        StatusResponse: Health status of the API
    """
    try:
        with RecordAPI() as record_api:
            db_connected = record_api.create_tables_if_not_exist()
            
        if db_connected:
            status = "healthy"
            message = "API server is running and database is accessible"
        else:
            status = "unhealthy"
            message = "Database connection failed"
            
        return StatusResponse(
            status=status,
            timestamp=datetime.datetime.now().isoformat(),
            message=message
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return StatusResponse(
            status="error",
            timestamp=datetime.datetime.now().isoformat(),
            message=f"Error during health check: {str(e)}"
        )

@app.get("/dialogs/{user_id}", tags=["Dialogs"])
async def get_dialogs(user_id: int = 1, limit: int = Query(5, description="Maximum number of records to return")):
    """
    Get the most recent dialog records for a specific user
    
    Args:
        user_id (int): The user ID to retrieve dialogs for
        limit (int, optional): Maximum number of records to return, defaults to 5
        
    Returns:
        List[Dict]: List of dialog records or appropriate error response
    """
    try:
        with RecordAPI() as record_api:
            records = record_api.get_records_by_userid(user_id)
            
        if not records:
            raise HTTPException(status_code=404, detail=f"No records found for user ID: {user_id}")
        
        # Sort by timestamp in descending order (newest first) and limit the number of records
        sorted_records = sorted(records, key=lambda x: x.get('timestamp'), reverse=True)[:limit]
        
        return sorted_records
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dialogs: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/dialogs/create_dialog", response_model=StatusResponse, tags=["Dialogs"])
async def create_dialog(dialog: DialogRequest = Body(...)):
    """
    Store a new dialog record in the database
    
    Args:
        dialog (DialogRequest): The dialog data to store
        
    Returns:
        StatusResponse: Status of the operation
    """
    try:
        with RecordAPI() as record_api:
            timestamp = record_api.store_dialog(
                user_id=dialog.user_id,
                session_id=dialog.session_id,
                user_message=dialog.user_message,
                system_message=dialog.system_message
            )
        
        if timestamp:
            return StatusResponse(
                status="success",
                timestamp=datetime.datetime.now().isoformat(),
                message=f"Dialog stored with timestamp: {timestamp}"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to store dialog record")
    
    except Exception as e:
        logger.error(f"Error creating dialog: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Run the API server
if __name__ == "__main__":
    # Ensure the database tables exist
    with RecordAPI() as record_api:
        record_api.create_tables_if_not_exist()
    
    # Define host and port - could be loaded from config in a real-world scenario
    host = "0.0.0.0"
    port = 10003
    
    # Print startup message
    logger.info(f"Starting Dialog API server at http://{host}:{port}")
    
    # Start the server
    uvicorn.run(app, host=host, port=port)

# CURL Examples for Testing the Dialog API
"""
# Dialog API - Curl Examples

This document provides curl examples for testing the Dialog API endpoints.

## Prerequisites

1. Ensure your FastAPI server is running:
   ```bash
   python dialog_api.py
   ```
   The server will be available at http://localhost:10003

2. Make sure you have a running PostgreSQL instance properly configured in 
   postres_utils/config_postgres.yml

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API server is running and can connect to the database.

```bash
curl -X GET "http://localhost:10003/dialogs/health" \
  -H "accept: application/json"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-23T10:00:00.000000",
  "message": "API server is running and database is accessible"
}
```

### 2. Get Dialogs by User ID

**Endpoint:** `GET /dialogs/{user_id}`

**Description:** Retrieve the 5 most recent dialog records for a specific user.

```bash
curl -X GET "http://localhost:10003/dialogs/2" \
  -H "accept: application/json"
```

**Expected Response:**
```json
[
  {
    "timestamp": 1721858867,
    "id": 2,
    "session_id": "session-123",
    "user_message": "Hello, how can you help me?",
    "system_message": "I can answer questions and assist with various tasks."
  },
  {
    "timestamp": 1721758867,
    "id": 2,
    "session_id": "session-123",
    "user_message": "What services do you offer?",
    "system_message": "I offer information retrieval, task assistance, and more."
  }
]
```

### 3. Create a New Dialog

**Endpoint:** `POST /dialogs`

**Description:** Store a new dialog record in the database.

```bash
curl -X POST "http://localhost:10003/dialogs/create_dialog" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "session_id": "session-123",
    "user_message": "Can you explain how to use this API?",
    "system_message": "Sure! This API allows you to store and retrieve dialog messages."
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "timestamp": "2025-07-23T10:05:00.000000",
  "message": "Dialog stored with timestamp: 1721859100"
}
```
"""
