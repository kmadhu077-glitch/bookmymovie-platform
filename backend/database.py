"""
Database Configuration and Models for BookMyMovie Platform
PostgreSQL integration with SQLAlchemy ORM
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os
from datetime import datetime

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bookmymovie:password123@localhost/bookmymovie_db")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
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
    seats_booked = Column(JSON, nullable=False)  # List of seat IDs
    total_amount = Column(Float, nullable=False)
    booking_status = Column(String, default="confirmed")  # confirmed, cancelled, completed
    booking_date = Column(DateTime, default=func.now())
    payment_status = Column(String, default="pending")  # pending, completed, failed, refunded
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
    payment_status = Column(String, default="pending")  # pending, completed, failed, refunded
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    gateway_response = Column(JSON, nullable=True)
    payment_date = Column(DateTime, default=func.now())
    refund_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
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

# Database Utility Functions
def get_db():
    """Database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

def drop_tables():
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All database tables dropped!")

def init_sample_movies(db):
    """Initialize sample movies"""
    movies = [
        Movie(
            title="Avengers: Endgame",
            description="After the devastating events of Infinity War, the universe is in ruins.",
            genre="Action",
            duration=181,
            rating=8.4,
            release_date=datetime(2019, 4, 26),
            poster_url="https://example.com/avengers-endgame.jpg",
            director="Anthony Russo, Joe Russo",
            cast=["Robert Downey Jr.", "Chris Evans", "Mark Ruffalo", "Chris Hemsworth"],
            language="English"
        ),
        Movie(
            title="Inception",
            description="A thief who steals corporate secrets through dream-sharing technology.",
            genre="Sci-Fi", 
            duration=148,
            rating=8.8,
            release_date=datetime(2010, 7, 16),
            poster_url="https://example.com/inception.jpg",
            director="Christopher Nolan",
            cast=["Leonardo DiCaprio", "Marion Cotillard", "Tom Hardy"],
            language="English"
        ),
        Movie(
            title="The Dark Knight",
            description="When the menace known as the Joker wreaks havoc on Gotham.",
            genre="Action",
            duration=152,
            rating=9.0,
            release_date=datetime(2008, 7, 18),
            poster_url="https://example.com/dark-knight.jpg",
            director="Christopher Nolan", 
            cast=["Christian Bale", "Heath Ledger", "Aaron Eckhart"],
            language="English"
        )
    ]
    db.add_all(movies)

def init_sample_theaters(db):
    """Initialize sample theaters"""
    theaters = [
        Theater(
            name="IMAX Downtown",
            location="Downtown Plaza",
            address="123 Main Street",
            city="New York",
            state="NY",
            zip_code="10001",
            phone_number="+1-555-0123",
            email="contact@imaxdowntown.com",
            total_screens=3,
            facilities=["IMAX", "Dolby Atmos", "3D", "Premium Seating"]
        ),
        Theater(
            name="Cinema Plus Mall",
            location="Shopping Mall Center", 
            address="456 Mall Avenue",
            city="New York",
            state="NY", 
            zip_code="10002",
            phone_number="+1-555-0456",
            email="info@cinemaplusmall.com",
            total_screens=5,
            facilities=["4DX", "Dolby Vision", "Luxury Recliner"]
        )
    ]
    db.add_all(theaters)

def init_sample_users(db):
    """Initialize sample users"""
    try:
        import bcrypt
        
        def hash_password(password: str) -> str:
            # Ensure password is not longer than 72 bytes for bcrypt
            password_bytes = password.encode('utf-8')[:72]
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        users = [
            User(
                email="john@example.com",
                username="john_doe",
                password_hash=hash_password("password123"),
                full_name="John Doe",
                phone_number="+1-555-1234",
                is_verified=True
            ),
            User(
                email="jane@example.com", 
                username="jane_smith",
                password_hash=hash_password("password123"),
                full_name="Jane Smith",
                phone_number="+1-555-5678",
                is_verified=True
            )
        ]
        
        # Sample admin
        admin = Admin(
            username="admin",
            email="admin@bookmymovie.com",
            password_hash=hash_password("admin123"),
            full_name="System Administrator",
            role="super_admin",
            permissions=["all"]
        )
        
        db.add_all(users)
        db.add(admin)
        
    except ImportError:
        # Fallback to simple hashing if bcrypt not available
        print("⚠️ bcrypt not available, using simple hashing (not for production)")
        import hashlib
        
        def simple_hash(password: str) -> str:
            return hashlib.sha256(password.encode()).hexdigest()
        
        users = [
            User(
                email="john@example.com",
                username="john_doe",
                password_hash=simple_hash("password123"),
                full_name="John Doe",
                phone_number="+1-555-1234",
                is_verified=True
            ),
            User(
                email="jane@example.com", 
                username="jane_smith",
                password_hash=simple_hash("password123"),
                full_name="Jane Smith",
                phone_number="+1-555-5678",
                is_verified=True
            )
        ]
        
        # Sample admin
        admin = Admin(
            username="admin",
            email="admin@bookmymovie.com",
            password_hash=simple_hash("admin123"),
            full_name="System Administrator",
            role="super_admin",
            permissions=["all"]
        )
        
        db.add_all(users)
        db.add(admin)

def init_sample_showtimes(db):
    """Initialize sample showtimes"""
    from datetime import timedelta
    
    # Get movies and theaters first
    movies = db.query(Movie).limit(3).all()
    theaters = db.query(Theater).limit(2).all()
    
    if movies and theaters:
        # Create screens for theaters
        screens = []
        for theater in theaters:
            for i in range(1, theater.total_screens + 1):
                screen = Screen(
                    theater_id=theater.id,
                    screen_number=i,
                    screen_name=f"Screen {i}",
                    total_seats=120,
                    screen_type="Standard",
                    seat_layout={"rows": 10, "seats_per_row": 12}
                )
                screens.append(screen)
        
        db.add_all(screens)
        db.commit()
        
        # Create showtimes
        showtimes = []
        base_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        
        for movie in movies:
            for theater in theaters:
                theater_screens = db.query(Screen).filter(Screen.theater_id == theater.id).all()
                for screen in theater_screens:
                    for day_offset in range(7):  # Next 7 days
                        show_date = base_date + timedelta(days=day_offset)
                        for time_offset in [0, 3, 6]:  # 10am, 1pm, 4pm shows
                            show_time = show_date + timedelta(hours=time_offset)
                            
                            showtime = Showtime(
                                movie_id=movie.id,
                                theater_id=theater.id,
                                screen_id=screen.id,
                                show_date=show_time.date(),
                                show_time=show_time,
                                price=150.0,
                                available_seats=120,
                                total_seats=120
                            )
                            showtimes.append(showtime)
        
        db.add_all(showtimes)

def init_sample_data():
    """Initialize database with sample data"""
    db = SessionLocal()
    
    try:
        # Initialize all sample data
        init_sample_movies(db)
        init_sample_theaters(db)
        init_sample_users(db)
        db.commit()
        
        # Initialize showtimes after other data is committed
        init_sample_showtimes(db)
        db.commit()
        
        print("✅ Sample data initialized successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error initializing sample data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Initializing BookMyMovie Database...")
    create_tables()
    init_sample_data()
    print("🎬 Database setup complete!")