import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# --- 1. Pydantic Models for Movie Catalog ---
class Movie(BaseModel):
    """Schema for a movie in the catalog."""
    movie_id: str
    title: str
    description: str
    genre: str
    duration_minutes: int
    rating: float
    poster_url: str

class Showtime(BaseModel):
    """Schema for a movie showtime."""
    showtime_id: str
    movie_id: str
    start_time: str
    theater_name: str
    price_per_seat: float
    total_seats: int

# --- 2. Initialize FastAPI App ---
# This service runs on port 8005 for the movie booking system.
app = FastAPI(title="Movie Catalog Service", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. Mock Movie Database ---
MOCK_MOVIES = [
    Movie(
        movie_id="movie_001",
        title="The Dark Knight",
        description="When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
        genre="Action",
        duration_minutes=152,
        rating=9.0,
        poster_url="https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg"
    ),
    Movie(
        movie_id="movie_002", 
        title="Inception",
        description="A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
        genre="Sci-Fi",
        duration_minutes=148,
        rating=8.8,
        poster_url="https://image.tmdb.org/t/p/w500/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg"
    ),
    Movie(
        movie_id="movie_003",
        title="Interstellar", 
        description="A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        genre="Sci-Fi",
        duration_minutes=169,
        rating=8.6,
        poster_url="https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg"
    ),
    Movie(
        movie_id="movie_004",
        title="The Avengers",
        description="Earth's mightiest heroes must come together and learn to fight as a team if they are going to stop the mischievous Loki and his alien army from enslaving humanity.",
        genre="Action",
        duration_minutes=143,
        rating=8.0,
        poster_url="https://image.tmdb.org/t/p/w500/RYMX2wcKCBAr24UyPD7xwmjaTn.jpg"
    ),
    Movie(
        movie_id="movie_005",
        title="Parasite",
        description="A poor family schemes to become employed by a wealthy family and infiltrate their household by posing as unrelated, highly qualified individuals.",
        genre="Thriller",
        duration_minutes=132,
        rating=8.6,
        poster_url="https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg"
    )
]

# --- 4. Mock Showtimes Database ---
MOCK_SHOWTIMES = [
    # The Dark Knight showtimes
    Showtime(
        showtime_id="show_001",
        movie_id="movie_001", 
        start_time="2025-10-15T19:00:00",
        theater_name="IMAX Theater 1",
        price_per_seat=15.99,
        total_seats=120
    ),
    Showtime(
        showtime_id="show_002",
        movie_id="movie_001",
        start_time="2025-10-15T22:00:00", 
        theater_name="Cinema Hall A",
        price_per_seat=12.99,
        total_seats=100
    ),
    # Inception showtimes
    Showtime(
        showtime_id="show_003",
        movie_id="movie_002",
        start_time="2025-10-15T20:30:00",
        theater_name="IMAX Theater 2", 
        price_per_seat=16.99,
        total_seats=150
    ),
    Showtime(
        showtime_id="show_004",
        movie_id="movie_002",
        start_time="2025-10-16T18:00:00",
        theater_name="Cinema Hall B",
        price_per_seat=13.99,
        total_seats=80
    ),
    # Interstellar showtimes
    Showtime(
        showtime_id="show_005", 
        movie_id="movie_003",
        start_time="2025-10-15T21:00:00",
        theater_name="Premium Theater",
        price_per_seat=18.99,
        total_seats=60
    ),
    # The Avengers showtimes
    Showtime(
        showtime_id="show_006",
        movie_id="movie_004",
        start_time="2025-10-16T19:30:00",
        theater_name="IMAX Theater 1",
        price_per_seat=15.99,
        total_seats=120
    ),
    # Parasite showtimes
    Showtime(
        showtime_id="show_007",
        movie_id="movie_005",
        start_time="2025-10-16T20:00:00",
        theater_name="Art House Cinema",
        price_per_seat=14.99,
        total_seats=90
    )
]

# --- 5. API Endpoints ---

@app.get("/health")
def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "service": "catalog"}

@app.get("/v1/catalog/movies", response_model=List[Movie], summary="Get all movies")
async def get_all_movies():
    """
    Returns a list of all movies currently playing.
    """
    print("Catalog Service: Received request for all movies.")
    return MOCK_MOVIES

@app.get("/v1/catalog/movies/{movie_id}", response_model=Movie, summary="Get movie by ID")
async def get_movie_by_id(movie_id: str):
    """
    Returns details for a specific movie.
    """
    print(f"Catalog Service: Received request for movie ID: {movie_id}")
    movie = next((m for m in MOCK_MOVIES if m.movie_id == movie_id), None)
    
    if movie is None:
        raise HTTPException(status_code=404, detail=f"Movie with ID {movie_id} not found")
        
    return movie

@app.get("/v1/catalog/showtimes/{movie_id}", response_model=List[Showtime], summary="Get showtimes for a movie")
async def get_showtimes_for_movie(movie_id: str):
    """
    Returns all available showtimes for a specific movie.
    """
    print(f"Catalog Service: Received request for showtimes of movie ID: {movie_id}")
    
    # Verify movie exists
    movie = next((m for m in MOCK_MOVIES if m.movie_id == movie_id), None)
    if movie is None:
        raise HTTPException(status_code=404, detail=f"Movie with ID {movie_id} not found")
    
    # Get showtimes for this movie
    showtimes = [s for s in MOCK_SHOWTIMES if s.movie_id == movie_id]
    return showtimes

# --- 6. Main Execution Block ---
if __name__ == "__main__":
    print("Starting Movie Catalog Service on http://0.0.0.0:8005")
    uvicorn.run(app, host="0.0.0.0", port=8005, log_level="info")
