import time
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import httpx

# --- Admin Authentication & Models ---

class AdminLogin(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., min_length=8)

class AdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    role: str = "admin"

class MovieManagement(BaseModel):
    title: str
    description: str
    duration_minutes: int
    genre: str
    rating: float
    poster_url: str
    release_date: str
    status: str = "active"  # active, coming_soon, inactive

class TheaterManagement(BaseModel):
    name: str
    location: str
    total_seats: int
    seat_layout: dict  # {"rows": 10, "seats_per_row": 15}
    facilities: List[str] = []  # ["AC", "Dolby", "IMAX"]

class ShowtimeManagement(BaseModel):
    movie_id: str
    theater_id: str
    start_time: datetime
    end_time: datetime
    price_per_seat: float
    available_seats: int

class UserAnalytics(BaseModel):
    total_users: int
    active_users_today: int
    new_registrations_today: int
    user_growth_rate: float

class BookingAnalytics(BaseModel):
    total_bookings: int
    bookings_today: int
    revenue_today: float
    popular_movies: List[dict]
    occupancy_rate: float

# --- Mock Database ---
ADMIN_CREDENTIALS = {
    "admin": {
        "username": "admin",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "super_admin"
    },
    "manager": {
        "username": "manager", 
        "password_hash": hashlib.sha256("manager123".encode()).hexdigest(),
        "role": "theater_manager"
    }
}

MOCK_MOVIES_DB = {}
MOCK_THEATERS_DB = {}
MOCK_SHOWTIMES_DB = {}
ACTIVE_ADMIN_TOKENS = {}

# --- Helper Functions ---

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_admin_token(username: str) -> str:
    return f"ADMIN_TOKEN_{username}_{int(time.time())}"

def verify_admin_token(token: str) -> Optional[dict]:
    return ACTIVE_ADMIN_TOKENS.get(token)

# --- Security ---
security = HTTPBearer()

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    admin_info = verify_admin_token(token)
    if not admin_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin token"
        )
    return admin_info

# --- FastAPI App ---
app = FastAPI(
    title="BookMyMovie Admin Panel API",
    description="Comprehensive admin panel for managing the entire movie booking system",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication Endpoints ---

@app.post("/v1/admin/login", response_model=AdminToken)
async def admin_login(login_data: AdminLogin):
    """Admin authentication endpoint"""
    admin = ADMIN_CREDENTIALS.get(login_data.username)
    
    if not admin or admin["password_hash"] != hash_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials"
        )
    
    token = generate_admin_token(login_data.username)
    ACTIVE_ADMIN_TOKENS[token] = {
        "username": login_data.username,
        "role": admin["role"],
        "login_time": time.time()
    }
    
    return AdminToken(
        access_token=token,
        role=admin["role"]
    )

@app.post("/v1/admin/logout")
async def admin_logout(current_admin: dict = Depends(get_current_admin)):
    """Admin logout endpoint"""
    # In a real app, you'd invalidate the token
    return {"message": "Logged out successfully"}

# --- Movie Management ---

@app.get("/v1/admin/movies")
async def get_all_movies(current_admin: dict = Depends(get_current_admin)):
    """Get all movies for admin management"""
    # In real implementation, fetch from catalog service
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://127.0.0.1:8005/v1/catalog/movies")
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return {"movies": list(MOCK_MOVIES_DB.values()), "total": len(MOCK_MOVIES_DB)}

@app.post("/v1/admin/movies")
async def create_movie(movie: MovieManagement, current_admin: dict = Depends(get_current_admin)):
    """Create a new movie"""
    movie_id = f"movie_{int(time.time())}"
    movie_data = movie.dict()
    movie_data["movie_id"] = movie_id
    movie_data["created_by"] = current_admin["username"]
    movie_data["created_at"] = datetime.now().isoformat()
    
    MOCK_MOVIES_DB[movie_id] = movie_data
    return {"message": "Movie created successfully", "movie_id": movie_id}

@app.put("/v1/admin/movies/{movie_id}")
async def update_movie(movie_id: str, movie: MovieManagement, current_admin: dict = Depends(get_current_admin)):
    """Update an existing movie"""
    if movie_id not in MOCK_MOVIES_DB:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    movie_data = movie.dict()
    movie_data["updated_by"] = current_admin["username"]
    movie_data["updated_at"] = datetime.now().isoformat()
    
    MOCK_MOVIES_DB[movie_id].update(movie_data)
    return {"message": "Movie updated successfully"}

@app.delete("/v1/admin/movies/{movie_id}")
async def delete_movie(movie_id: str, current_admin: dict = Depends(get_current_admin)):
    """Delete a movie"""
    if movie_id not in MOCK_MOVIES_DB:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    del MOCK_MOVIES_DB[movie_id]
    return {"message": "Movie deleted successfully"}

# --- Theater Management ---

@app.get("/v1/admin/theaters")
async def get_all_theaters(current_admin: dict = Depends(get_current_admin)):
    """Get all theaters"""
    return {"theaters": list(MOCK_THEATERS_DB.values()), "total": len(MOCK_THEATERS_DB)}

@app.post("/v1/admin/theaters")
async def create_theater(theater: TheaterManagement, current_admin: dict = Depends(get_current_admin)):
    """Create a new theater"""
    theater_id = f"theater_{int(time.time())}"
    theater_data = theater.dict()
    theater_data["theater_id"] = theater_id
    theater_data["created_by"] = current_admin["username"]
    
    MOCK_THEATERS_DB[theater_id] = theater_data
    return {"message": "Theater created successfully", "theater_id": theater_id}

# --- User Management ---

@app.get("/v1/admin/users")
async def get_all_users(current_admin: dict = Depends(get_current_admin)):
    """Get all users for admin management"""
    # Mock user data - in real app, fetch from auth service
    mock_users = [
        {
            "user_id": "user_1",
            "email": "john@example.com",
            "name": "John Doe",
            "registration_date": "2024-01-15",
            "total_bookings": 5,
            "status": "active"
        },
        {
            "user_id": "user_2", 
            "email": "jane@example.com",
            "name": "Jane Smith",
            "registration_date": "2024-02-20",
            "total_bookings": 3,
            "status": "active"
        }
    ]
    return {"users": mock_users, "total": len(mock_users)}

@app.put("/v1/admin/users/{user_id}/status")
async def update_user_status(user_id: str, status: str, current_admin: dict = Depends(get_current_admin)):
    """Update user status (active/inactive/banned)"""
    return {"message": f"User {user_id} status updated to {status}"}

# --- Analytics & Reports ---

@app.get("/v1/admin/analytics/dashboard")
async def get_dashboard_analytics(current_admin: dict = Depends(get_current_admin)):
    """Get comprehensive dashboard analytics"""
    
    # Mock analytics data
    user_analytics = UserAnalytics(
        total_users=1250,
        active_users_today=89,
        new_registrations_today=12,
        user_growth_rate=15.8
    )
    
    booking_analytics = BookingAnalytics(
        total_bookings=5680,
        bookings_today=45,
        revenue_today=22500.0,
        popular_movies=[
            {"title": "Cybernetic Hearts", "bookings": 234},
            {"title": "Quantum Leap", "bookings": 189},
            {"title": "Neon Dreams", "bookings": 156}
        ],
        occupancy_rate=78.5
    )
    
    return {
        "user_analytics": user_analytics.dict(),
        "booking_analytics": booking_analytics.dict(),
        "system_health": {
            "services_status": "all_healthy",
            "uptime": "99.8%",
            "avg_response_time": "120ms"
        }
    }

@app.get("/v1/admin/analytics/revenue")
async def get_revenue_analytics(
    period: str = "weekly",  # daily, weekly, monthly
    current_admin: dict = Depends(get_current_admin)
):
    """Get revenue analytics for specified period"""
    
    # Mock revenue data
    if period == "daily":
        data = [
            {"date": "2024-10-15", "revenue": 22500, "bookings": 45},
            {"date": "2024-10-14", "revenue": 18900, "bookings": 38},
            {"date": "2024-10-13", "revenue": 25600, "bookings": 51}
        ]
    elif period == "weekly":
        data = [
            {"week": "Week 42", "revenue": 145000, "bookings": 290},
            {"week": "Week 41", "revenue": 132000, "bookings": 264},
            {"week": "Week 40", "revenue": 156000, "bookings": 312}
        ]
    else:  # monthly
        data = [
            {"month": "October", "revenue": 580000, "bookings": 1160},
            {"month": "September", "revenue": 520000, "bookings": 1040},
            {"month": "August", "revenue": 615000, "bookings": 1230}
        ]
    
    return {"period": period, "data": data}

# --- System Health & Configuration ---

@app.get("/health")
async def health_check():
    """Admin service health check"""
    return {"status": "ok", "service": "admin"}

@app.get("/v1/admin/system/status")
async def get_system_status(current_admin: dict = Depends(get_current_admin)):
    """Get overall system status"""
    
    services = ["catalog", "auth", "booking", "payment", "notification"]
    service_status = {}
    
    for service_name in services:
        port_map = {
            "catalog": 8005, "auth": 8006, "booking": 8007,
            "payment": 8008, "notification": 8009
        }
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"http://127.0.0.1:{port_map[service_name]}/health")
                service_status[service_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            service_status[service_name] = "down"
    
    return {
        "services": service_status,
        "overall_health": "healthy" if all(s != "down" for s in service_status.values()) else "degraded"
    }

# Run command: uvicorn admin_service:app --host 127.0.0.1 --port 8010 --reload