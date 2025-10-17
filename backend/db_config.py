"""
Database Connection Configuration
Environment-based database connection management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/bookmymovie"
)

# For development, you can also use SQLite
SQLITE_URL = "sqlite:///./bookmymovie.db"

# Choose database based on environment
if os.getenv("ENVIRONMENT", "development") == "development" and not os.getenv("USE_POSTGRES"):
    # Use SQLite for development
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True  # Set to False in production
    )
    logger.info("Using SQLite database for development")
else:
    # Use PostgreSQL for production
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False  # Set to True for SQL debugging
    )
    logger.info("Using PostgreSQL database")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Database dependency for FastAPI
def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database initialization
def create_tables():
    """Create all database tables"""
    try:
        from database import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False

def init_sample_data():
    """Initialize database with sample data"""
    try:
        from database import (
            init_sample_movies, init_sample_theaters, 
            init_sample_users, init_sample_showtimes
        )
        
        db = SessionLocal()
        
        try:
            # Initialize sample data
            init_sample_movies(db)
            init_sample_theaters(db)
            init_sample_users(db)
            init_sample_showtimes(db)
            
            db.commit()
            logger.info("Sample data initialized successfully")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error initializing sample data: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in init_sample_data: {e}")
        return False

def reset_database():
    """Reset database by dropping and recreating all tables"""
    try:
        from database import Base
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")
        
        # Recreate tables
        Base.metadata.create_all(bind=engine)
        logger.info("All tables recreated")
        
        # Initialize sample data
        init_sample_data()
        
        return True
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False

# Health check
def check_database_connection():
    """Check if database connection is working"""
    try:
        db = SessionLocal()
        # Try to execute a simple query
        db.execute("SELECT 1")
        db.close()
        logger.info("Database connection is healthy")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

if __name__ == "__main__":
    # Initialize database when run directly
    print("Initializing BookMyMovie Database...")
    
    # Create tables
    if create_tables():
        print("✅ Database tables created")
        
        # Initialize sample data
        if init_sample_data():
            print("✅ Sample data initialized")
            print("\n🚀 Database setup complete!")
            print("\nSample users created:")
            print("- Email: john@example.com, Password: password123")
            print("- Email: jane@example.com, Password: password123")
            print("- Email: admin@bookmymovie.com, Password: admin123")
        else:
            print("❌ Failed to initialize sample data")
    else:
        print("❌ Failed to create database tables")