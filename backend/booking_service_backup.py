from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import time
import httpx # Required for service-to-service communication

# --- Configuration ---
NOTIFICATION_SERVICE_URL = "http://127.0.0.1:8009/v1/notifications/notify"

# --- Pydantic Models ---

class SeatHoldRequest(BaseModel):
    showtime_id: str
    seat_ids: list[str]
    user_id: str

class SeatHoldRecord(BaseModel):
    hold_id: str
    showtime_id: str
    seat_ids: list[str]
    user_id: str
    expiry_time: float
    message: str

class BookingConfirmationRequest(BaseModel):
    hold_id: str
    transaction_id: str
    amount_paid: float
    payment_method: str

class BookingRecord(BaseModel):
    booking_ref: str
    showtime_id: str
    seats: list[str]
    user_id: str
    transaction_id: str
    status: str

# --- Data Store (Mock Database) ---
MOCK_SEAT_HOLDS = {} # hold_id: SeatHoldRecord
MOCK_BOOKINGS = {} # booking_ref: BookingRecord

# --- FastAPI Setup ---
app = FastAPI(
    title="Booking Service",
    description="Handles seat holds and booking confirmation."
)

# CORS configuration
origins = [
    "http://127.0.0.1",
    "http://localhost",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "Booking"}

@app.post("/v1/holds", response_model=SeatHoldRecord)
async def place_seat_hold(request: SeatHoldRequest):
    """
    Places a temporary hold on the requested seats for 5 minutes.
    """
    hold_id = str(uuid.uuid4())
    expiry_time = time.time() + 300 # 5 minutes expiry

    hold = SeatHoldRecord(
        hold_id=hold_id,
        showtime_id=request.showtime_id,
        seat_ids=request.seat_ids,
        user_id=request.user_id,
        expiry_time=expiry_time,
        message=f"Seats held successfully for 5 minutes. Hold ID: {hold_id}"
    )

    MOCK_SEAT_HOLDS[hold_id] = hold
    return hold

@app.post("/v1/bookings/confirm", response_model=BookingRecord)
async def confirm_booking(request: BookingConfirmationRequest):
    """
    Confirms a booking after successful payment and sends a notification.
    """
    hold = MOCK_SEAT_HOLDS.get(request.hold_id)

    if not hold or time.time() > hold.expiry_time:
        raise HTTPException(status_code=404, detail="Hold not found or has expired.")

    # 1. Create Final Booking Record
    booking_ref = "BKG-" + str(uuid.uuid4())[:8].upper()
    booking = BookingRecord(
        booking_ref=booking_ref,
        showtime_id=hold.showtime_id,
        seats=hold.seat_ids,
        user_id=hold.user_id,
        transaction_id=request.transaction_id,
        status="CONFIRMED"
    )

    MOCK_BOOKINGS[booking_ref] = booking
    
    # 2. Remove the temporary hold
    del MOCK_SEAT_HOLDS[request.hold_id]
    
    # 3. --- NEW: Call Notification Service Asynchronously ---
    notification_data = {
        "booking_ref": booking_ref,
        "user_id": hold.user_id,
        # Mock recipient email
        "recipient_email": f"user_{hold.user_id}@mockcinema.com", 
        "message_type": "BOOKING_CONFIRMATION",
        "details": {
            "showtime_id": hold.showtime_id,
            "seats": hold.seat_ids,
            "amount_paid": request.amount_paid
        }
    }
    
    # Use httpx to make the service-to-service call
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            # This is a non-blocking call. The booking confirmation will return immediately, 
            # even if the notification service takes a moment.
            notification_response = await client.post(NOTIFICATION_SERVICE_URL, json=notification_data)
            
            if notification_response.is_error:
                # Log the failure but continue, as the booking is already complete.
                print(f"WARNING: Notification service call failed. Status: {notification_response.status_code}")
            else:
                print(f"INFO: Notification service responded: {notification_response.json()}")
                
        except httpx.RequestError as e:
            print(f"ERROR: Could not connect to Notification Service: {e}")

    # 4. Return the confirmed booking record to the client
    return booking

# TO RUN THIS SERVICE: uvicorn booking_service:app --host 127.0.0.1 --port 8007