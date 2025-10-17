from pydantic import BaseModel, Field
from typing import List, Optional

# ----------------------------------------------------------------------
# API Models used by the Booking Service
# ----------------------------------------------------------------------

# Mock Catalog Models (used internally by the Booking Service mock function)
class Movie(BaseModel):
    """Placeholder for Movie data structure from Catalog Service."""
    movie_id: str
    title: str
    duration_minutes: int
    rating: str

class Showtime(BaseModel):
    """Placeholder for Showtime data structure from Catalog Service."""
    showtime_id: str
    movie_id: str
    start_time: str
    theater_name: str
    price_per_seat: float = Field(..., gt=0)


# Seat Status Model
class SeatStatus(BaseModel):
    """Represents the current state of a single seat."""
    id: str = Field(..., description="Unique seat identifier (e.g., A1, B10).")
    status: str = Field(..., description="Current status: 'available', 'held', or 'booked'.")


# Seat Hold Request/Response
class HoldRequest(BaseModel):
    """Request to place a temporary hold on seats."""
    user_id: str = Field(..., description="ID of the user placing the hold.")
    showtime_id: str = Field(..., description="ID of the showtime.")
    seat_ids: List[str] = Field(..., description="List of seats to hold.")

class HoldResponse(BaseModel):
    """Response returned after a successful seat hold."""
    hold_id: str
    status: str = "HELD"
    total_price: float


# Booking Confirmation
class HoldConfirmation(BaseModel):
    """Request to confirm a hold into a final booking after payment."""
    user_id: str = Field(..., description="ID of the user confirming.")
    hold_id: str = Field(..., description="The temporary hold ID.")
    transaction_id: str = Field(..., description="The unique ID from the Payment Service.")

class BookingResponse(BaseModel):
    """Final response returned after a successful booking confirmation."""
    booking_ref: str = Field(..., description="User-facing booking reference code.")
    showtime_id: str
    seat_ids: List[str]
    user_id: str
    status: str = "CONFIRMED"
