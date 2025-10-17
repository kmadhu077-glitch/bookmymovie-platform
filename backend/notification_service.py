import time
from typing import Dict, List, Optional
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Pydantic Models for API Contracts ---

class NotificationRequest(BaseModel):
    """Schema for a request to send a notification."""
    user_id: str = Field(..., description="Target user ID.")
    type: str = Field(..., description="Notification channel (e.g., 'email', 'sms', 'push').")
    message: str = Field(..., description="The main content of the notification.")
    details: Dict = Field(default_factory=dict, description="Additional contextual data (e.g., booking reference).")

class NotificationResponse(BaseModel):
    """Schema for the response after attempting to send a notification."""
    status: str = Field(..., example="SENT")
    notification_id: str
    channel: str = Field(..., example="email")
    timestamp: str

# --- Helper Functions ---

def generate_notification_id() -> str:
    """Generates a mock unique notification ID."""
    return f"NOTIF_{int(time.time() * 1000)}"

# --- FastAPI Application Instance ---
app = FastAPI(
    title="Notification Microservice (Python/FastAPI)",
    description="Handles sending asynchronous communications (email, SMS) to users."
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Service Health Check (FIX) ---
@app.get("/health", status_code=200, summary="Service Health Check")
async def get_health():
    """
    Health Check Endpoint.
    Returns HTTP 200 OK if the service is running.
    """
    return {"status": "ok", "service": "notification"}

# --- API Endpoints ---

@app.post(
    "/v1/notifications/send",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Accepts a request and simulates sending a notification."
)
async def send_notification(request: NotificationRequest):
    """
    Simulates the process of sending an email, SMS, or push notification.
    In a real system, this would queue the request to a Celery/Kafka worker.
    """
    
    # Log the incoming request details
    print("\n----------------------------------------------------")
    print(f"[INFO] Received request to send {request.type.upper()} notification:")
    print(f"  > To User: {request.user_id}")
    print(f"  > Message: {request.message[:60]}...")
    print(f"  > Details: {request.details}")
    print(f"[INFO] Notification mocked as successfully sent.")
    print("----------------------------------------------------\n")

    # Mock the time delay for external service call
    # await asyncio.sleep(0.1) 
    
    return NotificationResponse(
        status="SENT",
        notification_id=generate_notification_id(),
        channel=request.type,
        timestamp=str(time.time())
    )
