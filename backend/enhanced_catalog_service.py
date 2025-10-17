"""
Enhanced Catalog Service with PostgreSQL Database Integration
Real-time movie catalog with advanced features
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, date
import logging
from models import get_db, Movie, Theater, Screen, Showtime, Review

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BookMyMovie - Enhanced Catalog Service",
    description="Advanced movie catalog with database integration and real-time features",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    rating: Optional[float] = None
    director: Optional[str] = None
    cast: Optional[List[str]] = None
    language: Optional[str] = None
    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None
    is_active: Optional[bool] = None

class MovieResponse(MovieBase):
    id: int
    rating: Optional[float] = None
    release_date: date
    is_active: bool
    created_at: datetime
    total_reviews: Optional[int] = 0
    average_rating: Optional[float] = None
    
    class Config:
        from_attributes = True

class TheaterBase(BaseModel):
    name: str
    location: str
    address: str
    city: str
    state: str
    zip_code: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    facilities: Optional[List[str]] = None

class TheaterResponse(TheaterBase):
    id: int
    total_screens: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ShowtimeResponse(BaseModel):
    id: int
    movie_id: int
    theater_id: int
    screen_id: int
    show_date: date
    show_time: datetime
    price: float
    available_seats: int
    total_seats: int
    movie_title: Optional[str] = None
    theater_name: Optional[str] = None
    screen_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class MovieSearchFilters(BaseModel):
    genre: Optional[str] = None
    language: Optional[str] = None
    rating_min: Optional[float] = None
    rating_max: Optional[float] = None
    release_year: Optional[int] = None
    duration_min: Optional[int] = None
    duration_max: Optional[int] = None

# Health Check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Enhanced Catalog Service",
        "version": "2.0.0",
        "timestamp": datetime.utcnow()
    }

# Movies Endpoints
@app.get("/v1/catalog/movies", response_model=List[MovieResponse])
async def get_movies(
    skip: int = Query(0, ge=0, description="Number of movies to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of movies to return"),
    search: Optional[str] = Query(None, description="Search in title, description, cast"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    language: Optional[str] = Query(None, description="Filter by language"),
    rating_min: Optional[float] = Query(None, ge=0, le=10, description="Minimum rating"),
    sort_by: Optional[str] = Query("created_at", description="Sort by: title, rating, release_date, created_at"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: Session = Depends(get_db)
):
    """Get movies with advanced filtering, search, and pagination"""
    try:
        # Start with base query
        query = db.query(Movie).filter(Movie.is_active == True)
        
        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Movie.title).contains(search_term),
                    func.lower(Movie.description).contains(search_term),
                    func.lower(Movie.director).contains(search_term),
                    Movie.cast.op('::text').ilike(search_term)
                )
            )
        
        # Apply filters
        if genre:
            query = query.filter(func.lower(Movie.genre) == genre.lower())
        
        if language:
            query = query.filter(func.lower(Movie.language) == language.lower())
        
        if rating_min:
            query = query.filter(Movie.rating >= rating_min)
        
        # Apply sorting
        if sort_by == "title":
            order_col = Movie.title
        elif sort_by == "rating":
            order_col = Movie.rating
        elif sort_by == "release_date":
            order_col = Movie.release_date
        else:
            order_col = Movie.created_at
        
        if sort_order.lower() == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())
        
        # Apply pagination
        movies = query.offset(skip).limit(limit).all()
        
        # Enhance with review data
        enhanced_movies = []
        for movie in movies:
            movie_dict = MovieResponse.from_orm(movie).__dict__
            
            # Get review statistics
            review_stats = db.query(
                func.count(Review.id).label('total_reviews'),
                func.avg(Review.rating).label('average_rating')
            ).filter(Review.movie_id == movie.id).first()
            
            movie_dict['total_reviews'] = review_stats.total_reviews or 0
            movie_dict['average_rating'] = float(review_stats.average_rating) if review_stats.average_rating else None
            
            enhanced_movies.append(movie_dict)
        
        return enhanced_movies
        
    except Exception as e:
        logger.error(f"Error fetching movies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/catalog/movies/{movie_id}", response_model=MovieResponse)
async def get_movie_by_id(movie_id: int, db: Session = Depends(get_db)):
    """Get detailed movie information by ID"""
    try:
        movie = db.query(Movie).filter(Movie.id == movie_id, Movie.is_active == True).first()
        
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Get review statistics
        review_stats = db.query(
            func.count(Review.id).label('total_reviews'),
            func.avg(Review.rating).label('average_rating')
        ).filter(Review.movie_id == movie.id).first()
        
        movie_response = MovieResponse.from_orm(movie)
        movie_response.total_reviews = review_stats.total_reviews or 0
        movie_response.average_rating = float(review_stats.average_rating) if review_stats.average_rating else None
        
        return movie_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching movie {movie_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/catalog/movies/{movie_id}/showtimes", response_model=List[ShowtimeResponse])
async def get_movie_showtimes(
    movie_id: int,
    show_date: Optional[date] = Query(None, description="Filter by show date"),
    city: Optional[str] = Query(None, description="Filter by city"),
    db: Session = Depends(get_db)
):
    """Get showtimes for a specific movie"""
    try:
        # Verify movie exists
        movie = db.query(Movie).filter(Movie.id == movie_id, Movie.is_active == True).first()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        # Build showtimes query
        query = db.query(Showtime, Movie.title, Theater.name, Screen.screen_name)\
                  .join(Movie, Showtime.movie_id == Movie.id)\
                  .join(Theater, Showtime.theater_id == Theater.id)\
                  .join(Screen, Showtime.screen_id == Screen.id)\
                  .filter(
                      Showtime.movie_id == movie_id,
                      Showtime.is_active == True,
                      Theater.is_active == True,
                      Screen.is_active == True
                  )
        
        # Apply filters
        if show_date:
            query = query.filter(func.date(Showtime.show_date) == show_date)
        
        if city:
            query = query.filter(func.lower(Theater.city) == city.lower())
        
        # Order by show time
        query = query.order_by(Showtime.show_date, Showtime.show_time)
        
        results = query.all()
        
        # Format response
        showtimes = []
        for showtime, movie_title, theater_name, screen_name in results:
            showtime_response = ShowtimeResponse.from_orm(showtime)
            showtime_response.movie_title = movie_title
            showtime_response.theater_name = theater_name
            showtime_response.screen_name = screen_name
            showtimes.append(showtime_response)
        
        return showtimes
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching showtimes for movie {movie_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Theaters Endpoints
@app.get("/v1/catalog/theaters", response_model=List[TheaterResponse])
async def get_theaters(
    city: Optional[str] = Query(None, description="Filter by city"),
    movie_id: Optional[int] = Query(None, description="Filter by movie availability"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get theaters with optional filtering"""
    try:
        query = db.query(Theater).filter(Theater.is_active == True)
        
        if city:
            query = query.filter(func.lower(Theater.city) == city.lower())
        
        if movie_id:
            # Only theaters that have showtimes for this movie
            query = query.join(Showtime, Theater.id == Showtime.theater_id)\
                         .filter(
                             Showtime.movie_id == movie_id,
                             Showtime.is_active == True
                         ).distinct()
        
        theaters = query.order_by(Theater.name).offset(skip).limit(limit).all()
        return [TheaterResponse.from_orm(theater) for theater in theaters]
        
    except Exception as e:
        logger.error(f"Error fetching theaters: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Genre and Statistics Endpoints
@app.get("/v1/catalog/genres")
async def get_genres(db: Session = Depends(get_db)):
    """Get all available genres"""
    try:
        genres = db.query(Movie.genre)\
                   .filter(Movie.is_active == True)\
                   .distinct()\
                   .order_by(Movie.genre)\
                   .all()
        
        return {"genres": [genre[0] for genre in genres]}
        
    except Exception as e:
        logger.error(f"Error fetching genres: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/catalog/languages")
async def get_languages(db: Session = Depends(get_db)):
    """Get all available languages"""
    try:
        languages = db.query(Movie.language)\
                      .filter(Movie.is_active == True)\
                      .distinct()\
                      .order_by(Movie.language)\
                      .all()
        
        return {"languages": [lang[0] for lang in languages]}
        
    except Exception as e:
        logger.error(f"Error fetching languages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/catalog/cities")
async def get_cities(db: Session = Depends(get_db)):
    """Get all cities with active theaters"""
    try:
        cities = db.query(Theater.city)\
                   .filter(Theater.is_active == True)\
                   .distinct()\
                   .order_by(Theater.city)\
                   .all()
        
        return {"cities": [city[0] for city in cities]}
        
    except Exception as e:
        logger.error(f"Error fetching cities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/catalog/stats")
async def get_catalog_stats(db: Session = Depends(get_db)):
    """Get catalog statistics"""
    try:
        # Count active movies
        total_movies = db.query(func.count(Movie.id)).filter(Movie.is_active == True).scalar()
        
        # Count active theaters
        total_theaters = db.query(func.count(Theater.id)).filter(Theater.is_active == True).scalar()
        
        # Count total screens
        total_screens = db.query(func.sum(Theater.total_screens)).filter(Theater.is_active == True).scalar()
        
        # Count active showtimes for today and future
        today = date.today()
        active_showtimes = db.query(func.count(Showtime.id))\
                             .filter(
                                 Showtime.is_active == True,
                                 func.date(Showtime.show_date) >= today
                             ).scalar()
        
        # Top genres
        top_genres = db.query(Movie.genre, func.count(Movie.id).label('count'))\
                       .filter(Movie.is_active == True)\
                       .group_by(Movie.genre)\
                       .order_by(func.count(Movie.id).desc())\
                       .limit(5)\
                       .all()
        
        return {
            "total_movies": total_movies or 0,
            "total_theaters": total_theaters or 0,
            "total_screens": total_screens or 0,
            "active_showtimes": active_showtimes or 0,
            "top_genres": [{"genre": genre, "count": count} for genre, count in top_genres],
            "last_updated": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error fetching catalog stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)