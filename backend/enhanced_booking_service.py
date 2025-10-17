"""
Enhanced Booking Service with Database Integration and Real-time Features
Comprehensive booking management with seat selection and inventory tracking
"""

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
from enum import Enum
import logging
import json
import asyncio
import aiohttp
from models import get_db, Booking, Showtime, Movie, Theater, Screen, User, Payment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BookMyMovie - Enhanced Booking Service",
    description="Advanced booking management with real-time seat selection and inventory tracking",
    version="2.0.0"
)

# Real-time service configuration
REALTIME_SERVICE_URL = "http://127.0.0.1:8006"

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Enums
class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class SeatStatus(str, Enum):
    AVAILABLE = "available"
    SELECTED = "selected"
    BOOKED = "booked"
    BLOCKED = "blocked"

# Pydantic Models
class SeatPosition(BaseModel):
    row: str = Field(..., description="Seat row (A, B, C, etc.)")
    number: int = Field(..., ge=1, description="Seat number within the row")

class SeatInfo(BaseModel):
    row: str
    number: int
    status: SeatStatus
    price: float
    seat_type: str = "regular"  # regular, premium, vip

class BookingCreate(BaseModel):
    showtime_id: int
    seats: List[SeatPosition] = Field(..., min_items=1, max_items=10)
    total_amount: float = Field(..., gt=0)
    discount_code: Optional[str] = None

class BookingUpdate(BaseModel):
    status: Optional[BookingStatus] = None
    seats: Optional[List[SeatPosition]] = None

class BookingResponse(BaseModel):
    id: int
    user_id: int
    showtime_id: int
    booking_reference: str
    seats: List[Dict]
    total_amount: float
    discount_amount: float
    final_amount: float
    status: BookingStatus
    booking_date: datetime
    show_date: date
    show_time: datetime
    
    # Related data
    movie_title: Optional[str] = None
    theater_name: Optional[str] = None
    screen_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class ShowtimeSeats(BaseModel):
    showtime_id: int
    movie_title: str
    theater_name: str
    screen_name: str
    show_date: date
    show_time: datetime
    total_seats: int
    available_seats: int
    seat_map: List[List[SeatInfo]]
    price_tiers: Dict[str, float]

class BookingStats(BaseModel):
    total_bookings: int
    confirmed_bookings: int
    pending_bookings: int
    cancelled_bookings: int
    total_revenue: float
    average_booking_value: float
    popular_showtimes: List[Dict]
    occupancy_rate: float

# Utility Functions
def generate_booking_reference() -> str:
    """Generate unique booking reference"""
    import uuid
    return f"BK{datetime.utcnow().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

def get_seat_map(screen_id: int, showtime_id: int, db: Session) -> List[List[SeatInfo]]:
    """Generate seat map for a screen with booking status"""
    # This is a simplified seat map generation
    # In a real system, this would come from the screen configuration
    
    # Get screen info (assuming standard layout for demo)
    screen = db.query(Screen).filter(Screen.id == screen_id).first()
    if not screen:
        return []
    
    # Get booked seats for this showtime
    booked_seats = db.query(Booking).filter(
        Booking.showtime_id == showtime_id,
        Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING])
    ).all()
    
    # Extract booked seat positions
    booked_positions = set()
    for booking in booked_seats:
        if booking.seats:
            for seat in booking.seats:
                if isinstance(seat, dict):
                    booked_positions.add(f"{seat.get('row')}{seat.get('number')}")
                else:
                    booked_positions.add(f"{seat['row']}{seat['number']}")
    
    # Generate standard seat map (10 rows, 12 seats per row)
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
    seat_map = []
    
    for row in rows:
        row_seats = []
        for seat_num in range(1, 13):  # 12 seats per row
            seat_id = f"{row}{seat_num}"
            status = SeatStatus.BOOKED if seat_id in booked_positions else SeatStatus.AVAILABLE
            
            # Pricing tiers (premium for middle rows, regular for others)
            if row in ['D', 'E', 'F', 'G']:
                price = 150.0  # Premium seats
                seat_type = "premium"
            elif row in ['A', 'B']:
                price = 100.0  # Economy seats
                seat_type = "economy"
            else:
                price = 120.0  # Regular seats
                seat_type = "regular"
            
            seat_info = SeatInfo(
                row=row,
                number=seat_num,
                status=status,
                price=price,
                seat_type=seat_type
            )
            row_seats.append(seat_info)
        
        seat_map.append(row_seats)
    
    return seat_map

def validate_seat_availability(showtime_id: int, seats: List[SeatPosition], db: Session) -> bool:
    """Check if requested seats are available"""
    # Get existing bookings for this showtime
    booked_seats = db.query(Booking).filter(
        Booking.showtime_id == showtime_id,
        Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING])
    ).all()
    
    # Extract booked seat positions
    booked_positions = set()
    for booking in booked_seats:
        if booking.seats:
            for seat in booking.seats:
                if isinstance(seat, dict):
                    booked_positions.add(f"{seat.get('row')}{seat.get('number')}")
    
    # Check if any requested seat is already booked
    for seat in seats:
        seat_id = f"{seat.row}{seat.number}"
        if seat_id in booked_positions:
            return False
    
    return True

async def notify_realtime_service(endpoint: str, data: dict):
    """Send notification to real-time service"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{REALTIME_SERVICE_URL}/{endpoint}", json=data) as response:
                if response.status == 200:
                    logger.info(f"Real-time notification sent to {endpoint}")
                else:
                    logger.warning(f"Real-time notification failed: {response.status}")
    except Exception as e:
        logger.error(f"Error sending real-time notification: {e}")

async def send_booking_notification(user_id: int, title: str, message: str, notification_type: str = "booking"):
    """Send booking-related notification"""
    await notify_realtime_service("api/realtime/notification", {
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notification_type
    })

async def trigger_seat_update(showtime_id: int):
    """Trigger real-time seat availability update"""
    await notify_realtime_service(f"api/realtime/seat-update/{showtime_id}", {})

# Authentication dependency (simplified for demo)
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Extract user ID from JWT token (simplified)"""
    # In a real implementation, this would validate the JWT token
    # For demo purposes, we'll return a default user ID
    return 1

# Health Check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Enhanced Booking Service",
        "version": "2.0.0",
        "timestamp": datetime.utcnow()
    }

# Booking Endpoints
@app.get("/v1/booking/showtime/{showtime_id}/seats", response_model=ShowtimeSeats)
async def get_showtime_seats(showtime_id: int, db: Session = Depends(get_db)):
    """Get seat map and availability for a showtime"""
    try:
        # Get showtime with related data
        showtime_query = db.query(
            Showtime, Movie.title, Theater.name, Screen.screen_name
        ).join(Movie, Showtime.movie_id == Movie.id)\
         .join(Theater, Showtime.theater_id == Theater.id)\
         .join(Screen, Showtime.screen_id == Screen.id)\
         .filter(Showtime.id == showtime_id, Showtime.is_active == True)
        
        result = showtime_query.first()
        if not result:
            raise HTTPException(status_code=404, detail="Showtime not found")
        
        showtime, movie_title, theater_name, screen_name = result
        
        # Generate seat map
        seat_map = get_seat_map(showtime.screen_id, showtime_id, db)
        
        # Calculate availability
        total_seats = sum(len(row) for row in seat_map)
        available_seats = sum(1 for row in seat_map for seat in row if seat.status == SeatStatus.AVAILABLE)
        
        # Price tiers
        price_tiers = {
            "economy": 100.0,
            "regular": 120.0,
            "premium": 150.0,
            "vip": 200.0
        }
        
        return ShowtimeSeats(
            showtime_id=showtime_id,
            movie_title=movie_title,
            theater_name=theater_name,
            screen_name=screen_name,
            show_date=showtime.show_date,
            show_time=showtime.show_time,
            total_seats=total_seats,
            available_seats=available_seats,
            seat_map=seat_map,
            price_tiers=price_tiers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching seats for showtime {showtime_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/v1/booking/create", response_model=BookingResponse)
async def create_booking(
    booking_data: BookingCreate,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new booking"""
    try:
        # Validate showtime
        showtime = db.query(Showtime).filter(
            Showtime.id == booking_data.showtime_id,
            Showtime.is_active == True,
            Showtime.show_date >= date.today()
        ).first()
        
        if not showtime:
            raise HTTPException(status_code=404, detail="Showtime not found or expired")
        
        # Validate seat availability
        if not validate_seat_availability(booking_data.showtime_id, booking_data.seats, db):
            raise HTTPException(status_code=409, detail="One or more selected seats are not available")
        
        # Calculate pricing
        total_calculated = 0.0
        seat_details = []
        
        for seat in booking_data.seats:
            # Get seat price based on position (simplified pricing logic)
            if seat.row in ['D', 'E', 'F', 'G']:
                price = 150.0
                seat_type = "premium"
            elif seat.row in ['A', 'B']:
                price = 100.0
                seat_type = "economy"
            else:
                price = 120.0
                seat_type = "regular"
            
            total_calculated += price
            seat_details.append({
                "row": seat.row,
                "number": seat.number,
                "price": price,
                "seat_type": seat_type
            })
        
        # Validate total amount
        if abs(booking_data.total_amount - total_calculated) > 0.01:
            raise HTTPException(
                status_code=400, 
                detail=f"Total amount mismatch. Expected: {total_calculated}, Received: {booking_data.total_amount}"
            )
        
        # Apply discount if provided
        discount_amount = 0.0
        if booking_data.discount_code:
            # Simplified discount logic
            if booking_data.discount_code == "FIRST10":
                discount_amount = booking_data.total_amount * 0.1
        
        final_amount = booking_data.total_amount - discount_amount
        
        # Create booking
        booking = Booking(
            user_id=user_id,
            showtime_id=booking_data.showtime_id,
            booking_reference=generate_booking_reference(),
            seats=seat_details,
            total_amount=booking_data.total_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            status=BookingStatus.PENDING,
            booking_date=datetime.utcnow()
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Get related data for response
        showtime_data = db.query(
            Showtime, Movie.title, Theater.name, Screen.screen_name
        ).join(Movie, Showtime.movie_id == Movie.id)\
         .join(Theater, Showtime.theater_id == Theater.id)\
         .join(Screen, Showtime.screen_id == Screen.id)\
         .filter(Showtime.id == booking.showtime_id).first()
        
        # Prepare response
        booking_response = BookingResponse.from_orm(booking)
        if showtime_data:
            _, movie_title, theater_name, screen_name = showtime_data
            booking_response.movie_title = movie_title
            booking_response.theater_name = theater_name
            booking_response.screen_name = screen_name
            booking_response.show_date = showtime.show_date
            booking_response.show_time = showtime.show_time
        
        # Add background task for booking confirmation timeout
        background_tasks.add_task(schedule_booking_timeout, booking.id, db)
        
        # Send real-time notifications
        background_tasks.add_task(
            send_booking_notification,
            user_id,
            "Booking Created",
            f"Your booking {booking.booking_reference} has been created. Please complete payment within 15 minutes.",
            "booking"
        )
        
        # Trigger seat availability update
        background_tasks.add_task(trigger_seat_update, booking.showtime_id)
        
        return booking_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/booking/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get booking details by ID"""
    try:
        # Get booking
        booking = db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.user_id == user_id
        ).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Get related data
        showtime_data = db.query(
            Showtime, Movie.title, Theater.name, Screen.screen_name
        ).join(Movie, Showtime.movie_id == Movie.id)\
         .join(Theater, Showtime.theater_id == Theater.id)\
         .join(Screen, Showtime.screen_id == Screen.id)\
         .filter(Showtime.id == booking.showtime_id).first()
        
        # Prepare response
        booking_response = BookingResponse.from_orm(booking)
        if showtime_data:
            showtime, movie_title, theater_name, screen_name = showtime_data
            booking_response.movie_title = movie_title
            booking_response.theater_name = theater_name
            booking_response.screen_name = screen_name
            booking_response.show_date = showtime.show_date
            booking_response.show_time = showtime.show_time
        
        return booking_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching booking {booking_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/booking/user/bookings", response_model=List[BookingResponse])
async def get_user_bookings(
    status: Optional[BookingStatus] = None,
    skip: int = 0,
    limit: int = 20,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get user's booking history"""
    try:
        query = db.query(Booking).filter(Booking.user_id == user_id)
        
        if status:
            query = query.filter(Booking.status == status)
        
        bookings = query.order_by(Booking.booking_date.desc()).offset(skip).limit(limit).all()
        
        # Enhance with related data
        enhanced_bookings = []
        for booking in bookings:
            showtime_data = db.query(
                Showtime, Movie.title, Theater.name, Screen.screen_name
            ).join(Movie, Showtime.movie_id == Movie.id)\
             .join(Theater, Showtime.theater_id == Theater.id)\
             .join(Screen, Showtime.screen_id == Screen.id)\
             .filter(Showtime.id == booking.showtime_id).first()
            
            booking_response = BookingResponse.from_orm(booking)
            if showtime_data:
                showtime, movie_title, theater_name, screen_name = showtime_data
                booking_response.movie_title = movie_title
                booking_response.theater_name = theater_name
                booking_response.screen_name = screen_name
                booking_response.show_date = showtime.show_date
                booking_response.show_time = showtime.show_time
            
            enhanced_bookings.append(booking_response)
        
        return enhanced_bookings
        
    except Exception as e:
        logger.error(f"Error fetching user bookings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/v1/booking/{booking_id}/confirm")
async def confirm_booking(
    booking_id: int,
    payment_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Confirm booking after successful payment"""
    try:
        # Get booking
        booking = db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.user_id == user_id,
            Booking.status == BookingStatus.PENDING
        ).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Pending booking not found")
        
        # Verify payment (simplified)
        # In a real system, you would verify the payment with the payment gateway
        
        # Update booking status
        booking.status = BookingStatus.CONFIRMED
        booking.updated_at = datetime.utcnow()
        
        # Create payment record
        payment = Payment(
            booking_id=booking.id,
            user_id=user_id,
            amount=booking.final_amount,
            payment_method="credit_card",  # This would come from payment data
            transaction_id=payment_id,
            status="completed",
            payment_date=datetime.utcnow()
        )
        
        db.add(payment)
        db.commit()
        
        # Send real-time notifications
        asyncio.create_task(
            send_booking_notification(
                user_id,
                "Booking Confirmed!",
                f"Your booking {booking.booking_reference} has been confirmed. Enjoy your movie!",
                "booking"
            )
        )
        
        # Trigger seat availability update
        asyncio.create_task(trigger_seat_update(booking.showtime_id))
        
        return {"message": "Booking confirmed successfully", "booking_id": booking_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming booking {booking_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/v1/booking/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Cancel a booking"""
    try:
        # Get booking
        booking = db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.user_id == user_id
        ).first()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        if booking.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
            raise HTTPException(status_code=400, detail="Booking cannot be cancelled")
        
        # Check cancellation policy (e.g., can't cancel 2 hours before show)
        showtime = db.query(Showtime).filter(Showtime.id == booking.showtime_id).first()
        if showtime:
            show_datetime = datetime.combine(showtime.show_date, showtime.show_time.time())
            if datetime.utcnow() > show_datetime - timedelta(hours=2):
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot cancel booking less than 2 hours before show time"
                )
        
        # Update booking status
        booking.status = BookingStatus.CANCELLED
        booking.updated_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Booking cancelled successfully", "booking_id": booking_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

# Statistics and Analytics
@app.get("/v1/booking/stats", response_model=BookingStats)
async def get_booking_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get booking statistics"""
    try:
        # Set date range if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Base query with date filter
        base_query = db.query(Booking).filter(
            func.date(Booking.booking_date) >= start_date,
            func.date(Booking.booking_date) <= end_date
        )
        
        # Count bookings by status
        total_bookings = base_query.count()
        confirmed_bookings = base_query.filter(Booking.status == BookingStatus.CONFIRMED).count()
        pending_bookings = base_query.filter(Booking.status == BookingStatus.PENDING).count()
        cancelled_bookings = base_query.filter(Booking.status == BookingStatus.CANCELLED).count()
        
        # Calculate revenue
        revenue_query = base_query.filter(Booking.status == BookingStatus.CONFIRMED)
        total_revenue = db.query(func.sum(Booking.final_amount)).filter(
            Booking.id.in_(revenue_query.with_entities(Booking.id))
        ).scalar() or 0.0
        
        # Calculate average booking value
        average_booking_value = total_revenue / confirmed_bookings if confirmed_bookings > 0 else 0.0
        
        # Popular showtimes
        popular_showtimes = db.query(
            Showtime.id,
            Movie.title,
            Theater.name,
            func.count(Booking.id).label('booking_count')
        ).join(Booking, Showtime.id == Booking.showtime_id)\
         .join(Movie, Showtime.movie_id == Movie.id)\
         .join(Theater, Showtime.theater_id == Theater.id)\
         .filter(
             func.date(Booking.booking_date) >= start_date,
             func.date(Booking.booking_date) <= end_date,
             Booking.status == BookingStatus.CONFIRMED
         ).group_by(Showtime.id, Movie.title, Theater.name)\
          .order_by(func.count(Booking.id).desc())\
          .limit(5).all()
        
        popular_showtimes_list = [
            {
                "showtime_id": st[0],
                "movie_title": st[1],
                "theater_name": st[2],
                "booking_count": st[3]
            }
            for st in popular_showtimes
        ]
        
        # Calculate occupancy rate (simplified)
        occupancy_rate = (confirmed_bookings / total_bookings * 100) if total_bookings > 0 else 0.0
        
        return BookingStats(
            total_bookings=total_bookings,
            confirmed_bookings=confirmed_bookings,
            pending_bookings=pending_bookings,
            cancelled_bookings=cancelled_bookings,
            total_revenue=total_revenue,
            average_booking_value=average_booking_value,
            popular_showtimes=popular_showtimes_list,
            occupancy_rate=occupancy_rate
        )
        
    except Exception as e:
        logger.error(f"Error fetching booking stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Background Tasks
async def schedule_booking_timeout(booking_id: int, db: Session):
    """Cancel booking if not confirmed within timeout period"""
    import asyncio
    await asyncio.sleep(900)  # 15 minutes timeout
    
    try:
        booking = db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.status == BookingStatus.PENDING
        ).first()
        
        if booking:
            booking.status = BookingStatus.CANCELLED
            booking.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Booking {booking_id} auto-cancelled due to timeout")
    
    except Exception as e:
        logger.error(f"Error in booking timeout task: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)