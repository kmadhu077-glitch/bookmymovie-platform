"""
Secure Enhanced Catalog Service with Security Middleware Integration
JWT Authentication, Rate Limiting, and Input Validation
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, date
import logging

# Import security middleware
from security_middleware import (
    SecurityMiddleware, get_current_user, get_current_admin,
    InputSanitizer, SecurityAuditLogger, require_permission
)
from models import get_db, Movie, Theater, Screen, Showtime, Review

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BookMyMovie - Secure Catalog Service",
    description="Secure movie catalog with JWT authentication and rate limiting",
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

# Pydantic Models for Request/Response
class MovieBase(BaseModel):
    title: str
    description: Optional[str] = None
    genre: str
    duration: int
    director: Optional[str] = None
    cast: Optional[List[str]] = None
    language: str = "English"
    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None

class MovieCreate(MovieBase):
    release_date: date

class MovieUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[str] = None
    duration: Optional[int] = None
    director: Optional[str] = None
    cast: Optional[List[str]] = None
    language: Optional[str] = None
    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None
    release_date: Optional[date] = None

class MovieResponse(MovieBase):
    id: int
    release_date: date
    average_rating: Optional[float] = None
    total_reviews: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class TheaterBase(BaseModel):
    name: str
    location: str
    address: Optional[str] = None
    phone: Optional[str] = None
    facilities: Optional[List[str]] = None

class TheaterCreate(TheaterBase):
    pass

class TheaterResponse(TheaterBase):
    id: int
    total_screens: int = 0
    is_active: bool = True
    created_at: datetime

    class Config:
        orm_mode = True

class ShowtimeResponse(BaseModel):
    id: int
    movie_id: int
    theater_id: int
    screen_id: int
    show_date: date
    show_time: str
    price: float
    available_seats: int
    total_seats: int
    movie_title: Optional[str] = None
    theater_name: Optional[str] = None
    screen_name: Optional[str] = None

    class Config:
        orm_mode = True

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    movie_id: int
    user_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    username: Optional[str] = None

    class Config:
        orm_mode = True

# Public endpoints (no authentication required)
@app.get("/movies", response_model=List[MovieResponse])
async def get_movies(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    genre: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get movies with filtering and pagination"""
    try:
        # Sanitize search input
        if search:
            search = InputSanitizer.sanitize_string(search)
        
        query = db.query(Movie).filter(Movie.is_active == True)
        
        # Apply filters
        if genre:
            genre = InputSanitizer.sanitize_string(genre)
            query = query.filter(Movie.genre.ilike(f"%{genre}%"))
        
        if language:
            language = InputSanitizer.sanitize_string(language)
            query = query.filter(Movie.language.ilike(f"%{language}%"))
        
        if search:
            query = query.filter(
                or_(
                    Movie.title.ilike(f"%{search}%"),
                    Movie.description.ilike(f"%{search}%"),
                    Movie.director.ilike(f"%{search}%")
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        movies = query.offset(skip).limit(limit).all()
        
        # Calculate average ratings
        movie_responses = []
        for movie in movies:
            reviews = db.query(Review).filter(Review.movie_id == movie.id).all()
            avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else None
            
            movie_response = MovieResponse(
                id=movie.id,
                title=movie.title,
                description=movie.description,
                genre=movie.genre,
                duration=movie.duration,
                director=movie.director,
                cast=movie.cast,
                language=movie.language,
                poster_url=movie.poster_url,
                trailer_url=movie.trailer_url,
                release_date=movie.release_date,
                average_rating=round(avg_rating, 2) if avg_rating else None,
                total_reviews=len(reviews),
                is_active=movie.is_active,
                created_at=movie.created_at,
                updated_at=movie.updated_at
            )
            movie_responses.append(movie_response)
        
        # Log successful request
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "catalog_movies_accessed",
            details=f"Retrieved {len(movies)} movies, filters: genre={genre}, language={language}, search={search}",
            ip_address=client_ip
        )
        
        return movie_responses
        
    except Exception as e:
        logger.error(f"Error fetching movies: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch movies")

@app.get("/movies/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get movie by ID"""
    try:
        movie = db.query(Movie).filter(
            Movie.id == movie_id, 
            Movie.is_active == True
        ).first()
        
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Calculate average rating
        reviews = db.query(Review).filter(Review.movie_id == movie.id).all()
        avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else None
        
        movie_response = MovieResponse(
            id=movie.id,
            title=movie.title,
            description=movie.description,
            genre=movie.genre,
            duration=movie.duration,
            director=movie.director,
            cast=movie.cast,
            language=movie.language,
            poster_url=movie.poster_url,
            trailer_url=movie.trailer_url,
            release_date=movie.release_date,
            average_rating=round(avg_rating, 2) if avg_rating else None,
            total_reviews=len(reviews),
            is_active=movie.is_active,
            created_at=movie.created_at,
            updated_at=movie.updated_at
        )
        
        # Log movie access
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "catalog_movie_viewed",
            details=f"Movie ID: {movie_id}, Title: {movie.title}",
            ip_address=client_ip
        )
        
        return movie_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching movie {movie_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch movie")

@app.get("/theaters", response_model=List[TheaterResponse])
async def get_theaters(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get theaters with filtering and pagination"""
    try:
        query = db.query(Theater).filter(Theater.is_active == True)
        
        if location:
            location = InputSanitizer.sanitize_string(location)
            query = query.filter(Theater.location.ilike(f"%{location}%"))
        
        theaters = query.offset(skip).limit(limit).all()
        
        # Add screen count for each theater
        theater_responses = []
        for theater in theaters:
            screen_count = db.query(Screen).filter(Screen.theater_id == theater.id).count()
            
            theater_response = TheaterResponse(
                id=theater.id,
                name=theater.name,
                location=theater.location,
                address=theater.address,
                phone=theater.phone,
                facilities=theater.facilities,
                total_screens=screen_count,
                is_active=theater.is_active,
                created_at=theater.created_at
            )
            theater_responses.append(theater_response)
        
        # Log theater access
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "catalog_theaters_accessed",
            details=f"Retrieved {len(theaters)} theaters, location filter: {location}",
            ip_address=client_ip
        )
        
        return theater_responses
        
    except Exception as e:
        logger.error(f"Error fetching theaters: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch theaters")

@app.get("/showtimes", response_model=List[ShowtimeResponse])
async def get_showtimes(
    request: Request,
    movie_id: Optional[int] = None,
    theater_id: Optional[int] = None,
    show_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get showtimes with filtering"""
    try:
        query = db.query(Showtime).join(Movie).join(Theater).join(Screen)
        
        # Apply filters
        if movie_id:
            query = query.filter(Showtime.movie_id == movie_id)
        
        if theater_id:
            query = query.filter(Showtime.theater_id == theater_id)
        
        if show_date:
            query = query.filter(Showtime.show_date == show_date)
        else:
            # Default to today and future dates
            query = query.filter(Showtime.show_date >= date.today())
        
        showtimes = query.offset(skip).limit(limit).all()
        
        # Build response with movie and theater details
        showtime_responses = []
        for showtime in showtimes:
            movie = db.query(Movie).filter(Movie.id == showtime.movie_id).first()
            theater = db.query(Theater).filter(Theater.id == showtime.theater_id).first()
            screen = db.query(Screen).filter(Screen.id == showtime.screen_id).first()
            
            showtime_response = ShowtimeResponse(
                id=showtime.id,
                movie_id=showtime.movie_id,
                theater_id=showtime.theater_id,
                screen_id=showtime.screen_id,
                show_date=showtime.show_date,
                show_time=showtime.show_time,
                price=float(showtime.price),
                available_seats=showtime.available_seats,
                total_seats=showtime.total_seats,
                movie_title=movie.title if movie else None,
                theater_name=theater.name if theater else None,
                screen_name=screen.name if screen else None
            )
            showtime_responses.append(showtime_response)
        
        # Log showtime access
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "catalog_showtimes_accessed",
            details=f"Retrieved {len(showtimes)} showtimes, movie_id={movie_id}, theater_id={theater_id}, date={show_date}",
            ip_address=client_ip
        )
        
        return showtime_responses
        
    except Exception as e:
        logger.error(f"Error fetching showtimes: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch showtimes")

# Protected endpoints (require authentication)
@app.post("/movies/{movie_id}/reviews", response_model=ReviewResponse)
async def create_review(
    movie_id: int,
    review_data: ReviewCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a movie review (authenticated users only)"""
    try:
        # Check if movie exists
        movie = db.query(Movie).filter(Movie.id == movie_id, Movie.is_active == True).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Check if user already reviewed this movie
        existing_review = db.query(Review).filter(
            Review.movie_id == movie_id,
            Review.user_id == current_user["id"]
        ).first()
        
        if existing_review:
            raise HTTPException(status_code=409, detail="You have already reviewed this movie")
        
        # Sanitize comment
        comment = InputSanitizer.sanitize_string(review_data.comment) if review_data.comment else None
        
        # Create review
        review = Review(
            movie_id=movie_id,
            user_id=current_user["id"],
            rating=review_data.rating,
            comment=comment,
            created_at=datetime.utcnow()
        )
        
        db.add(review)
        db.commit()
        db.refresh(review)
        
        # Log review creation
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "review_created",
            current_user["id"],
            f"Movie ID: {movie_id}, Rating: {review_data.rating}",
            client_ip
        )
        
        return ReviewResponse(
            id=review.id,
            movie_id=review.movie_id,
            user_id=review.user_id,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
            username=current_user["username"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail="Could not create review")

@app.get("/movies/{movie_id}/reviews", response_model=List[ReviewResponse])
async def get_movie_reviews(
    movie_id: int,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get reviews for a specific movie"""
    try:
        # Check if movie exists
        movie = db.query(Movie).filter(Movie.id == movie_id, Movie.is_active == True).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Get reviews with user information
        reviews = db.query(Review).filter(Review.movie_id == movie_id)\
                   .order_by(Review.created_at.desc())\
                   .offset(skip).limit(limit).all()
        
        review_responses = []
        for review in reviews:
            # Get username (would join with User table in production)
            username = f"user_{review.user_id}"  # Placeholder
            
            review_response = ReviewResponse(
                id=review.id,
                movie_id=review.movie_id,
                user_id=review.user_id,
                rating=review.rating,
                comment=review.comment,
                created_at=review.created_at,
                username=username
            )
            review_responses.append(review_response)
        
        # Log review access
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "movie_reviews_accessed",
            details=f"Movie ID: {movie_id}, Retrieved {len(reviews)} reviews",
            ip_address=client_ip
        )
        
        return review_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch reviews")

# Admin endpoints (require admin privileges)
@app.post("/admin/movies", response_model=MovieResponse)
@require_permission("admin")
async def create_movie(
    movie_data: MovieCreate,
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new movie (admin only)"""
    try:
        # Sanitize input data
        title = InputSanitizer.sanitize_string(movie_data.title)
        description = InputSanitizer.sanitize_string(movie_data.description) if movie_data.description else None
        genre = InputSanitizer.sanitize_string(movie_data.genre)
        director = InputSanitizer.sanitize_string(movie_data.director) if movie_data.director else None
        language = InputSanitizer.sanitize_string(movie_data.language)
        
        # Create movie
        movie = Movie(
            title=title,
            description=description,
            genre=genre,
            duration=movie_data.duration,
            director=director,
            cast=movie_data.cast,
            language=language,
            poster_url=movie_data.poster_url,
            trailer_url=movie_data.trailer_url,
            release_date=movie_data.release_date,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        db.add(movie)
        db.commit()
        db.refresh(movie)
        
        # Log movie creation
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "movie_created",
            current_admin["id"],
            f"Movie: {title}, ID: {movie.id}",
            client_ip
        )
        
        return MovieResponse(
            id=movie.id,
            title=movie.title,
            description=movie.description,
            genre=movie.genre,
            duration=movie.duration,
            director=movie.director,
            cast=movie.cast,
            language=movie.language,
            poster_url=movie.poster_url,
            trailer_url=movie.trailer_url,
            release_date=movie.release_date,
            average_rating=None,
            total_reviews=0,
            is_active=movie.is_active,
            created_at=movie.created_at,
            updated_at=movie.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error creating movie: {e}")
        raise HTTPException(status_code=500, detail="Could not create movie")

@app.put("/admin/movies/{movie_id}", response_model=MovieResponse)
@require_permission("admin")
async def update_movie(
    movie_id: int,
    movie_data: MovieUpdate,
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a movie (admin only)"""
    try:
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Update fields that are provided
        update_data = movie_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field in ["title", "description", "genre", "director", "language"] and value:
                value = InputSanitizer.sanitize_string(value)
            setattr(movie, field, value)
        
        movie.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(movie)
        
        # Calculate current ratings
        reviews = db.query(Review).filter(Review.movie_id == movie.id).all()
        avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else None
        
        # Log movie update
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "movie_updated",
            current_admin["id"],
            f"Movie ID: {movie_id}, Fields: {list(update_data.keys())}",
            client_ip
        )
        
        return MovieResponse(
            id=movie.id,
            title=movie.title,
            description=movie.description,
            genre=movie.genre,
            duration=movie.duration,
            director=movie.director,
            cast=movie.cast,
            language=movie.language,
            poster_url=movie.poster_url,
            trailer_url=movie.trailer_url,
            release_date=movie.release_date,
            average_rating=round(avg_rating, 2) if avg_rating else None,
            total_reviews=len(reviews),
            is_active=movie.is_active,
            created_at=movie.created_at,
            updated_at=movie.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating movie {movie_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not update movie")

@app.delete("/admin/movies/{movie_id}")
@require_permission("admin")
async def delete_movie(
    movie_id: int,
    request: Request,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Soft delete a movie (admin only)"""
    try:
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Soft delete
        movie.is_active = False
        movie.updated_at = datetime.utcnow()
        db.commit()
        
        # Log movie deletion
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "movie_deleted",
            current_admin["id"],
            f"Movie ID: {movie_id}, Title: {movie.title}",
            client_ip
        )
        
        return {"message": f"Movie '{movie.title}' has been deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting movie {movie_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not delete movie")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "secure-catalog",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "jwt_authentication",
            "rate_limiting",
            "input_validation",
            "audit_logging",
            "rbac"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Secure Catalog Service")
    uvicorn.run(app, host="127.0.0.1", port=8012)