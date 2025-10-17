"""
Database Models for BookMyMovie Platform  
SQLite-compatible version for development
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

# Database Models  
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    preferred_language = Column(String, default="English")
    membership_level = Column(String, default="standard")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    bookings = relationship("Booking", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    reviews = relationship("Review", back_populates="user")

class Movie(Base):
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    genre = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)  # in minutes
    rating = Column(Float, nullable=True)
    release_date = Column(DateTime, nullable=False)
    poster_url = Column(String, nullable=True)
    trailer_url = Column(String, nullable=True)
    director = Column(String, nullable=True)
    cast = Column(JSON, nullable=True)  # List of actors
    language = Column(String, default="English")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    showtimes = relationship("Showtime", back_populates="movie")
    reviews = relationship("Review", back_populates="movie")

class Theater(Base):
    __tablename__ = "theaters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    total_screens = Column(Integer, default=1)
    facilities = Column(JSON, nullable=True)  # ["IMAX", "Dolby", "3D", etc.]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    screens = relationship("Screen", back_populates="theater")
    showtimes = relationship("Showtime", back_populates="theater")

class Screen(Base):
    __tablename__ = "screens"
    
    id = Column(Integer, primary_key=True, index=True)
    theater_id = Column(Integer, ForeignKey("theaters.id"), nullable=False)
    screen_number = Column(Integer, nullable=False)
    screen_name = Column(String, nullable=True)
    total_seats = Column(Integer, nullable=False)
    screen_type = Column(String, default="Standard")  # Standard, IMAX, 4DX, etc.
    seat_layout = Column(JSON, nullable=False)  # Seat configuration
    is_active = Column(Boolean, default=True)
    
    # Relationships
    theater = relationship("Theater", back_populates="screens")
    showtimes = relationship("Showtime", back_populates="screen")

class Showtime(Base):
    __tablename__ = "showtimes"
    
    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    theater_id = Column(Integer, ForeignKey("theaters.id"), nullable=False)
    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False)
    show_date = Column(DateTime, nullable=False, index=True)
    show_time = Column(DateTime, nullable=False, index=True)
    price = Column(Float, nullable=False)
    available_seats = Column(Integer, nullable=False)
    total_seats = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    movie = relationship("Movie", back_populates="showtimes")
    theater = relationship("Theater", back_populates="showtimes")
    screen = relationship("Screen", back_populates="showtimes")
    bookings = relationship("Booking", back_populates="showtime")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    showtime_id = Column(Integer, ForeignKey("showtimes.id"), nullable=False)
    booking_reference = Column(String, unique=True, nullable=False, index=True)
    seats = Column(JSON, nullable=False)  # List of seat details
    total_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)
    booking_status = Column(String, default="pending")  # pending, confirmed, cancelled, completed
    payment_status = Column(String, default="pending")  # pending, completed, failed
    booking_date = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    showtime = relationship("Showtime", back_populates="bookings")
    payments = relationship("Payment", back_populates="booking")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    payment_method = Column(String, nullable=False)  # credit_card, debit_card, upi, net_banking
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    payment_status = Column(String, default="pending")  # pending, completed, failed, refunded
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    gateway_response = Column(JSON, nullable=True)
    fraud_score = Column(Float, default=0.0)  # Fraud detection score
    payment_date = Column(DateTime, default=func.now())
    refund_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="payments")
    booking = relationship("Booking", back_populates="payments")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    rating = Column(Float, nullable=False)  # 1-10 scale
    review_text = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)  # Only users who booked can review
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reviews")
    movie = relationship("Movie", back_populates="reviews")

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="admin")  # admin, super_admin, manager
    permissions = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String, nullable=False)  # booking, payment, promotional, system
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, default=func.now())
    read_at = Column(DateTime, nullable=True)

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # page_view, booking, payment, etc.
    event_data = Column(JSON, nullable=False)
    user_id = Column(Integer, nullable=True)
    session_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)