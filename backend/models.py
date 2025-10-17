"""
Database Models Import Module
Imports all models with the correct SQLite configuration
"""

from db_config import engine, SessionLocal, get_db
from db_models import (
    Base, User, Movie, Theater, Screen, Showtime, 
    Booking, Payment, Review, Admin, Notification, Analytics
)

# Create all tables if they don't exist
Base.metadata.create_all(bind=engine)

# Export everything for easy importing
__all__ = [
    'engine', 'SessionLocal', 'get_db',
    'Base', 'User', 'Movie', 'Theater', 'Screen', 'Showtime',
    'Booking', 'Payment', 'Review', 'Admin', 'Notification', 'Analytics'
]