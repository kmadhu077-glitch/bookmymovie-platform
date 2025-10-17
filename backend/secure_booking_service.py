"""
Secure Booking Service for BookMyMovie Platform
JWT Authentication, Rate Limiting, Input Validation, and Booking Security
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field, validator
from decimal import Decimal
import uuid

# Import security middleware
from security_middleware import (
    SecurityMiddleware, get_current_user, get_current_admin,
    InputSanitizer, SecurityAuditLogger, require_permission,
    add_security_headers
)
from models import get_db, Booking, Payment, User, Movie, Showtime, Theater, Screen

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BookMyMovie - Secure Booking Service",
    description="Secure booking management with JWT authentication and fraud protection",
    version="3.0.0"
)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# CORS middleware with security considerations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Total-Count", "X-Rate-Limit-Remaining"]
)

# Pydantic Models
class SeatSelection(BaseModel):
    row: str = Field(..., pattern=r'^[A-Z]$', description="Seat row (A-Z)")
    number: int = Field(..., ge=1, le=50, description="Seat number (1-50)")

class BookingCreate(BaseModel):
    showtime_id: int
    seats: List[SeatSelection] = Field(..., min_items=1, max_items=10)
    total_amount: Decimal = Field(..., gt=0, description="Total booking amount")
    
    @validator('seats')
    def validate_seats(cls, v):
        if len(v) != len(set((seat.row, seat.number) for seat in v)):
            raise ValueError('Duplicate seats are not allowed')
        return v
    
    @validator('total_amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        # Basic range validation (in production, calculate from seat prices)
        if v > 10000:  # $100 per seat max, 10 seats max
            raise ValueError('Amount exceeds maximum allowed')
        return v

class BookingUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern=r'^(confirmed|cancelled|completed)$')
    
class BookingResponse(BaseModel):
    id: int
    user_id: int
    showtime_id: int
    seats: List[Dict[str, Any]]
    total_amount: float
    booking_status: str
    payment_status: str
    booking_reference: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Related information
    movie_title: Optional[str] = None
    theater_name: Optional[str] = None
    show_date: Optional[str] = None
    show_time: Optional[str] = None

    class Config:
        orm_mode = True

class PaymentRequest(BaseModel):
    booking_id: int
    payment_method: str = Field(..., pattern=r'^(credit_card|debit_card|upi|wallet)$')
    card_last_four: Optional[str] = Field(None, pattern=r'^\d{4}$')
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        allowed_methods = ['credit_card', 'debit_card', 'upi', 'wallet']
        if v not in allowed_methods:
            raise ValueError(f'Payment method must be one of: {allowed_methods}')
        return v

# Booking endpoints (require authentication)
@app.post("/bookings", response_model=BookingResponse)
async def create_booking(
    booking_data: BookingCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new booking (authenticated users only)"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Validate showtime exists and is active
        showtime = db.query(Showtime).filter(
            Showtime.id == booking_data.showtime_id
        ).first()
        
        if not showtime:
            SecurityAuditLogger.log_security_event(
                "booking_invalid_showtime",
                current_user["id"],
                f"Invalid showtime ID: {booking_data.showtime_id}",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Showtime not found"
            )
        
        # Check if showtime is in the future
        show_datetime = datetime.combine(showtime.show_date, datetime.strptime(showtime.show_time, "%H:%M").time())
        if show_datetime <= datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book past showtimes"
            )
        
        # Validate seat availability
        existing_bookings = db.query(Booking).filter(
            and_(
                Booking.showtime_id == booking_data.showtime_id,
                Booking.booking_status.in_(['confirmed', 'completed'])
            )
        ).all()
        
        # Extract booked seats
        booked_seats = set()
        for booking in existing_bookings:
            if booking.seats:
                for seat in booking.seats:
                    booked_seats.add((seat.get('row'), seat.get('number')))
        
        # Check for conflicts
        requested_seats = set((seat.row, seat.number) for seat in booking_data.seats)
        conflicting_seats = requested_seats.intersection(booked_seats)
        
        if conflicting_seats:
            SecurityAuditLogger.log_security_event(
                "booking_seat_conflict",
                current_user["id"],
                f"Attempted to book occupied seats: {conflicting_seats}",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Seats already booked: {conflicting_seats}"
            )
        
        # Fraud detection - Check for suspicious booking patterns
        user_recent_bookings = db.query(Booking).filter(
            and_(
                Booking.user_id == current_user["id"],
                Booking.created_at >= datetime.now() - timedelta(hours=1)
            )
        ).count()
        
        if user_recent_bookings >= 5:  # Max 5 bookings per hour
            SecurityAuditLogger.log_security_event(
                "booking_rate_limit_exceeded",
                current_user["id"],
                f"User exceeded booking rate limit: {user_recent_bookings} bookings in last hour",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many bookings in short time. Please try again later."
            )
        
        # Generate booking reference
        booking_reference = f"BM{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        # Create booking
        new_booking = Booking(
            user_id=current_user["id"],
            showtime_id=booking_data.showtime_id,
            seats=[{"row": seat.row, "number": seat.number} for seat in booking_data.seats],
            total_amount=float(booking_data.total_amount),
            booking_status="pending",
            payment_status="pending",
            booking_reference=booking_reference,
            created_at=datetime.now()
        )
        
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        
        # Update available seats in showtime
        showtime.available_seats -= len(booking_data.seats)
        db.commit()
        
        # Get related information for response
        movie = db.query(Movie).filter(Movie.id == showtime.movie_id).first()
        theater = db.query(Theater).filter(Theater.id == showtime.theater_id).first()
        
        # Log successful booking
        SecurityAuditLogger.log_security_event(
            "booking_created",
            current_user["id"],
            f"Booking ID: {new_booking.id}, Seats: {len(booking_data.seats)}, Amount: {booking_data.total_amount}",
            client_ip
        )
        
        # Schedule booking expiration (in background)
        background_tasks.add_task(schedule_booking_expiration, new_booking.id)
        
        return BookingResponse(
            id=new_booking.id,
            user_id=new_booking.user_id,
            showtime_id=new_booking.showtime_id,
            seats=new_booking.seats,
            total_amount=new_booking.total_amount,
            booking_status=new_booking.booking_status,
            payment_status=new_booking.payment_status,
            booking_reference=new_booking.booking_reference,
            created_at=new_booking.created_at,
            updated_at=new_booking.updated_at,
            movie_title=movie.title if movie else None,
            theater_name=theater.name if theater else None,
            show_date=showtime.show_date.strftime("%Y-%m-%d") if showtime.show_date else None,
            show_time=showtime.show_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        SecurityAuditLogger.log_security_event(
            "booking_creation_error",
            current_user["id"],
            str(e),
            client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create booking"
        )

@app.get("/bookings", response_model=List[BookingResponse])
async def get_user_bookings(
    request: Request,
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's bookings"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        query = db.query(Booking).filter(Booking.user_id == current_user["id"])
        
        if status_filter:
            status_filter = InputSanitizer.sanitize_string(status_filter)
            query = query.filter(Booking.booking_status == status_filter)
        
        bookings = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit).all()
        
        booking_responses = []
        for booking in bookings:
            # Get related information
            showtime = db.query(Showtime).filter(Showtime.id == booking.showtime_id).first()
            movie = db.query(Movie).filter(Movie.id == showtime.movie_id).first() if showtime else None
            theater = db.query(Theater).filter(Theater.id == showtime.theater_id).first() if showtime else None
            
            booking_response = BookingResponse(
                id=booking.id,
                user_id=booking.user_id,
                showtime_id=booking.showtime_id,
                seats=booking.seats or [],
                total_amount=booking.total_amount,
                booking_status=booking.booking_status,
                payment_status=booking.payment_status,
                booking_reference=booking.booking_reference,
                created_at=booking.created_at,
                updated_at=booking.updated_at,
                movie_title=movie.title if movie else None,
                theater_name=theater.name if theater else None,
                show_date=showtime.show_date.strftime("%Y-%m-%d") if showtime and showtime.show_date else None,
                show_time=showtime.show_time if showtime else None
            )
            booking_responses.append(booking_response)
        
        # Log successful access
        SecurityAuditLogger.log_security_event(
            "bookings_accessed",
            current_user["id"],
            f"Retrieved {len(bookings)} bookings with filter: {status_filter}",
            client_ip
        )
        
        return booking_responses
        
    except Exception as e:
        logger.error(f"Error fetching user bookings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch bookings"
        )

@app.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific booking details"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        booking = db.query(Booking).filter(
            and_(
                Booking.id == booking_id,
                Booking.user_id == current_user["id"]  # Users can only see their own bookings
            )
        ).first()
        
        if not booking:
            SecurityAuditLogger.log_security_event(
                "booking_unauthorized_access",
                current_user["id"],
                f"Attempted to access booking ID: {booking_id}",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Get related information
        showtime = db.query(Showtime).filter(Showtime.id == booking.showtime_id).first()
        movie = db.query(Movie).filter(Movie.id == showtime.movie_id).first() if showtime else None
        theater = db.query(Theater).filter(Theater.id == showtime.theater_id).first() if showtime else None
        
        return BookingResponse(
            id=booking.id,
            user_id=booking.user_id,
            showtime_id=booking.showtime_id,
            seats=booking.seats or [],
            total_amount=booking.total_amount,
            booking_status=booking.booking_status,
            payment_status=booking.payment_status,
            booking_reference=booking.booking_reference,
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            movie_title=movie.title if movie else None,
            theater_name=theater.name if theater else None,
            show_date=showtime.show_date.strftime("%Y-%m-%d") if showtime and showtime.show_date else None,
            show_time=showtime.show_time if showtime else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching booking {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch booking"
        )

@app.put("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a booking"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        booking = db.query(Booking).filter(
            and_(
                Booking.id == booking_id,
                Booking.user_id == current_user["id"]
            )
        ).first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if booking.booking_status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled"
            )
        
        if booking.booking_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel completed booking"
            )
        
        # Check if cancellation is allowed (e.g., not too close to show time)
        showtime = db.query(Showtime).filter(Showtime.id == booking.showtime_id).first()
        if showtime:
            show_datetime = datetime.combine(showtime.show_date, datetime.strptime(showtime.show_time, "%H:%M").time())
            if show_datetime <= datetime.now() + timedelta(hours=2):  # Must cancel 2 hours before
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot cancel booking less than 2 hours before show time"
                )
            
            # Release seats
            showtime.available_seats += len(booking.seats) if booking.seats else 0
        
        # Update booking status
        booking.booking_status = "cancelled"
        booking.updated_at = datetime.now()
        db.commit()
        
        # Log cancellation
        SecurityAuditLogger.log_security_event(
            "booking_cancelled",
            current_user["id"],
            f"Booking ID: {booking_id}, Seats released: {len(booking.seats) if booking.seats else 0}",
            client_ip
        )
        
        return {"message": "Booking cancelled successfully", "booking_id": booking_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling booking {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not cancel booking"
        )

@app.post("/bookings/{booking_id}/payment", response_model=Dict[str, Any])
async def process_payment(
    booking_id: int,
    payment_data: PaymentRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process payment for a booking"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Validate booking exists and belongs to user
        booking = db.query(Booking).filter(
            and_(
                Booking.id == booking_id,
                Booking.user_id == current_user["id"]
            )
        ).first()
        
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if booking.payment_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already completed"
            )
        
        if booking.booking_status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot pay for cancelled booking"
            )
        
        # Fraud detection for payment
        recent_payments = db.query(Payment).filter(
            and_(
                Payment.user_id == current_user["id"],
                Payment.created_at >= datetime.now() - timedelta(minutes=10)
            )
        ).count()
        
        if recent_payments >= 3:  # Max 3 payments in 10 minutes
            SecurityAuditLogger.log_security_event(
                "payment_rate_limit_exceeded",
                current_user["id"],
                f"User exceeded payment rate limit: {recent_payments} payments in last 10 minutes",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many payment attempts. Please try again later."
            )
        
        # Create payment record
        payment_reference = f"PAY{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        new_payment = Payment(
            booking_id=booking_id,
            user_id=current_user["id"],
            amount=booking.total_amount,
            payment_method=payment_data.payment_method,
            payment_status="completed",  # In production, integrate with payment gateway
            transaction_id=payment_reference,
            created_at=datetime.now()
        )
        
        db.add(new_payment)
        
        # Update booking status
        booking.payment_status = "completed"
        booking.booking_status = "confirmed"
        booking.updated_at = datetime.now()
        
        db.commit()
        
        # Log successful payment
        SecurityAuditLogger.log_security_event(
            "payment_processed",
            current_user["id"],
            f"Payment ID: {new_payment.id}, Amount: {booking.total_amount}, Method: {payment_data.payment_method}",
            client_ip
        )
        
        return {
            "message": "Payment processed successfully",
            "payment_reference": payment_reference,
            "booking_status": booking.booking_status,
            "payment_status": booking.payment_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing payment for booking {booking_id}: {e}")
        SecurityAuditLogger.log_security_event(
            "payment_processing_error",
            current_user["id"],
            str(e),
            client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process payment"
        )

# Admin endpoints
@app.get("/admin/bookings", response_model=List[BookingResponse])
@require_permission("admin")
async def get_all_bookings(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all bookings (admin only)"""
    try:
        query = db.query(Booking)
        
        if user_id:
            query = query.filter(Booking.user_id == user_id)
        
        if status_filter:
            status_filter = InputSanitizer.sanitize_string(status_filter)
            query = query.filter(Booking.booking_status == status_filter)
        
        bookings = query.order_by(Booking.created_at.desc()).offset(skip).limit(limit).all()
        total = query.count()
        
        booking_responses = []
        for booking in bookings:
            showtime = db.query(Showtime).filter(Showtime.id == booking.showtime_id).first()
            movie = db.query(Movie).filter(Movie.id == showtime.movie_id).first() if showtime else None
            theater = db.query(Theater).filter(Theater.id == showtime.theater_id).first() if showtime else None
            
            booking_response = BookingResponse(
                id=booking.id,
                user_id=booking.user_id,
                showtime_id=booking.showtime_id,
                seats=booking.seats or [],
                total_amount=booking.total_amount,
                booking_status=booking.booking_status,
                payment_status=booking.payment_status,
                booking_reference=booking.booking_reference,
                created_at=booking.created_at,
                updated_at=booking.updated_at,
                movie_title=movie.title if movie else None,
                theater_name=theater.name if theater else None,
                show_date=showtime.show_date.strftime("%Y-%m-%d") if showtime and showtime.show_date else None,
                show_time=showtime.show_time if showtime else None
            )
            booking_responses.append(booking_response)
        
        # Log admin access
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "admin_bookings_accessed",
            current_admin["id"],
            f"Retrieved {len(bookings)} bookings, filters: user_id={user_id}, status={status_filter}",
            client_ip
        )
        
        return booking_responses
        
    except Exception as e:
        logger.error(f"Error fetching admin bookings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch bookings"
        )

@app.put("/admin/bookings/{booking_id}/status")
@require_permission("admin")
async def update_booking_status(
    booking_id: int,
    booking_update: BookingUpdate,
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update booking status (admin only)"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        old_status = booking.booking_status
        booking.booking_status = booking_update.status
        booking.updated_at = datetime.now()
        
        db.commit()
        
        # Log status change
        SecurityAuditLogger.log_security_event(
            "admin_booking_status_changed",
            current_admin["id"],
            f"Booking ID: {booking_id}, Status: {old_status} -> {booking_update.status}",
            client_ip
        )
        
        return {"message": f"Booking status updated to {booking_update.status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating booking status {booking_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update booking status"
        )

# Utility functions
async def schedule_booking_expiration(booking_id: int):
    """Schedule booking to expire if not paid within time limit"""
    # In production, use a task queue like Celery
    logger.info(f"Booking {booking_id} scheduled for expiration check in 15 minutes")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "secure-booking",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "jwt_authentication",
            "rate_limiting",
            "input_validation",
            "audit_logging",
            "fraud_detection",
            "rbac"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Secure Booking Service")
    uvicorn.run(app, host="127.0.0.1", port=8014)