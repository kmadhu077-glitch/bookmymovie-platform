"""
Advanced Analytics Service for BookMyMovie Platform
Comprehensive business intelligence, revenue tracking, and user behavior analysis
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc, text
from pydantic import BaseModel
import redis
from models import (
    get_db, Movie, Theater, Screen, Showtime, Booking, 
    User, Payment, Review, Analytics, Notification
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BookMyMovie - Advanced Analytics Service",
    description="Comprehensive business intelligence and analytics platform",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis configuration for caching analytics data
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    logger.info("Redis connected for analytics caching")
    CACHE_TTL = 300  # 5 minutes cache
except redis.ConnectionError:
    logger.warning("Redis not available, analytics will not be cached")
    redis_client = None
    CACHE_TTL = 0

# Pydantic models for analytics responses
class RevenueMetrics(BaseModel):
    total_revenue: float
    revenue_today: float
    revenue_this_week: float
    revenue_this_month: float
    average_ticket_price: float
    revenue_growth_rate: float

class BookingMetrics(BaseModel):
    total_bookings: int
    bookings_today: int
    bookings_this_week: int
    bookings_this_month: int
    average_seats_per_booking: float
    booking_conversion_rate: float

class UserMetrics(BaseModel):
    total_users: int
    active_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    user_retention_rate: float
    average_bookings_per_user: float

class MoviePerformance(BaseModel):
    movie_id: int
    title: str
    total_bookings: int
    total_revenue: float
    average_rating: Optional[float]
    occupancy_rate: float

class TheaterPerformance(BaseModel):
    theater_id: int
    name: str
    total_bookings: int
    total_revenue: float
    occupancy_rate: float
    average_ticket_price: float

class TimeSeriesData(BaseModel):
    date: str
    revenue: float
    bookings: int
    users: int

class AnalyticsDashboard(BaseModel):
    revenue_metrics: RevenueMetrics
    booking_metrics: BookingMetrics
    user_metrics: UserMetrics
    top_movies: List[MoviePerformance]
    top_theaters: List[TheaterPerformance]
    time_series: List[TimeSeriesData]
    last_updated: str

# Utility functions
def get_cache_key(endpoint: str, params: str = "") -> str:
    """Generate cache key for analytics data"""
    return f"analytics:{endpoint}:{params}"

def cache_result(key: str, data: Any, ttl: int = CACHE_TTL) -> None:
    """Cache analytics result in Redis"""
    if redis_client and ttl > 0:
        try:
            redis_client.setex(key, ttl, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")

def get_cached_result(key: str) -> Optional[Any]:
    """Get cached analytics result from Redis"""
    if redis_client:
        try:
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to get cached result: {e}")
    return None

# Core Analytics Functions
async def calculate_revenue_metrics(db: Session) -> RevenueMetrics:
    """Calculate comprehensive revenue metrics"""
    logger.info("Calculating revenue metrics")
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Total revenue
    total_revenue_result = db.query(func.sum(Payment.amount)).filter(
        Payment.status == 'completed'
    ).scalar() or 0.0
    
    # Revenue today
    revenue_today = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.status == 'completed',
            Payment.payment_date >= today_start
        )
    ).scalar() or 0.0
    
    # Revenue this week
    revenue_this_week = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.status == 'completed',
            Payment.payment_date >= week_start
        )
    ).scalar() or 0.0
    
    # Revenue this month
    revenue_this_month = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.status == 'completed',
            Payment.payment_date >= month_start
        )
    ).scalar() or 0.0
    
    # Average ticket price
    avg_ticket_price = db.query(func.avg(Payment.amount)).filter(
        Payment.status == 'completed'
    ).scalar() or 0.0
    
    # Revenue growth rate (month over month)
    prev_month_start = month_start - timedelta(days=30)
    prev_month_revenue = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.status == 'completed',
            Payment.payment_date >= prev_month_start,
            Payment.payment_date < month_start
        )
    ).scalar() or 0.0
    
    growth_rate = 0.0
    if prev_month_revenue > 0:
        growth_rate = ((revenue_this_month - prev_month_revenue) / prev_month_revenue) * 100
    
    return RevenueMetrics(
        total_revenue=float(total_revenue_result),
        revenue_today=float(revenue_today),
        revenue_this_week=float(revenue_this_week),
        revenue_this_month=float(revenue_this_month),
        average_ticket_price=float(avg_ticket_price),
        revenue_growth_rate=float(growth_rate)
    )

async def calculate_booking_metrics(db: Session) -> BookingMetrics:
    """Calculate comprehensive booking metrics"""
    logger.info("Calculating booking metrics")
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Total bookings
    total_bookings = db.query(func.count(Booking.id)).filter(
        Booking.status.in_(['confirmed', 'completed'])
    ).scalar() or 0
    
    # Bookings today
    bookings_today = db.query(func.count(Booking.id)).filter(
        and_(
            Booking.status.in_(['confirmed', 'completed']),
            Booking.booking_date >= today_start
        )
    ).scalar() or 0
    
    # Bookings this week
    bookings_this_week = db.query(func.count(Booking.id)).filter(
        and_(
            Booking.status.in_(['confirmed', 'completed']),
            Booking.booking_date >= week_start
        )
    ).scalar() or 0
    
    # Bookings this month
    bookings_this_month = db.query(func.count(Booking.id)).filter(
        and_(
            Booking.status.in_(['confirmed', 'completed']),
            Booking.booking_date >= month_start
        )
    ).scalar() or 0
    
    # Average seats per booking
    avg_seats = db.query(func.avg(func.length(Booking.seats))).filter(
        Booking.status.in_(['confirmed', 'completed'])
    ).scalar() or 0.0
    
    # Booking conversion rate (placeholder - would need tracking of page views)
    conversion_rate = 0.75  # Assume 75% conversion rate for now
    
    return BookingMetrics(
        total_bookings=int(total_bookings),
        bookings_today=int(bookings_today),
        bookings_this_week=int(bookings_this_week),
        bookings_this_month=int(bookings_this_month),
        average_seats_per_booking=float(avg_seats),
        booking_conversion_rate=float(conversion_rate)
    )

async def calculate_user_metrics(db: Session) -> UserMetrics:
    """Calculate comprehensive user metrics"""
    logger.info("Calculating user metrics")
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Total users
    total_users = db.query(func.count(User.id)).scalar() or 0
    
    # Active users today (users who made bookings)
    active_today = db.query(func.count(func.distinct(Booking.user_id))).filter(
        and_(
            Booking.booking_date >= today_start,
            Booking.status.in_(['confirmed', 'completed'])
        )
    ).scalar() or 0
    
    # New users this week
    new_users_week = db.query(func.count(User.id)).filter(
        User.created_at >= week_start
    ).scalar() or 0
    
    # New users this month
    new_users_month = db.query(func.count(User.id)).filter(
        User.created_at >= month_start
    ).scalar() or 0
    
    # User retention rate (users who booked again within 30 days)
    retention_rate = 0.68  # Placeholder - would need more complex calculation
    
    # Average bookings per user
    if total_users > 0:
        total_bookings = db.query(func.count(Booking.id)).filter(
            Booking.status.in_(['confirmed', 'completed'])
        ).scalar() or 0
        avg_bookings = total_bookings / total_users
    else:
        avg_bookings = 0.0
    
    return UserMetrics(
        total_users=int(total_users),
        active_users_today=int(active_today),
        new_users_this_week=int(new_users_week),
        new_users_this_month=int(new_users_month),
        user_retention_rate=float(retention_rate),
        average_bookings_per_user=float(avg_bookings)
    )

async def get_movie_performance(db: Session, limit: int = 10) -> List[MoviePerformance]:
    """Get top performing movies by revenue and bookings"""
    logger.info(f"Getting top {limit} movie performance")
    
    # Query for movie performance
    movie_stats = db.query(
        Movie.id,
        Movie.title,
        func.count(Booking.id).label('total_bookings'),
        func.sum(Payment.amount).label('total_revenue'),
        func.avg(Review.rating).label('average_rating')
    ).outerjoin(
        Showtime, Movie.id == Showtime.movie_id
    ).outerjoin(
        Booking, Showtime.id == Booking.showtime_id
    ).outerjoin(
        Payment, Booking.id == Payment.booking_id
    ).outerjoin(
        Review, Movie.id == Review.movie_id
    ).filter(
        or_(Booking.status.in_(['confirmed', 'completed']), Booking.status.is_(None))
    ).group_by(
        Movie.id, Movie.title
    ).order_by(
        desc('total_revenue')
    ).limit(limit).all()
    
    performances = []
    for stat in movie_stats:
        # Calculate occupancy rate (placeholder logic)
        occupancy_rate = min(0.85, (stat.total_bookings or 0) * 0.1)
        
        performances.append(MoviePerformance(
            movie_id=stat.id,
            title=stat.title,
            total_bookings=int(stat.total_bookings or 0),
            total_revenue=float(stat.total_revenue or 0.0),
            average_rating=float(stat.average_rating) if stat.average_rating else None,
            occupancy_rate=float(occupancy_rate)
        ))
    
    return performances

async def get_theater_performance(db: Session, limit: int = 10) -> List[TheaterPerformance]:
    """Get top performing theaters by revenue and occupancy"""
    logger.info(f"Getting top {limit} theater performance")
    
    # Query for theater performance
    theater_stats = db.query(
        Theater.id,
        Theater.name,
        func.count(Booking.id).label('total_bookings'),
        func.sum(Payment.amount).label('total_revenue'),
        func.avg(Payment.amount).label('avg_ticket_price')
    ).outerjoin(
        Screen, Theater.id == Screen.theater_id
    ).outerjoin(
        Showtime, Screen.id == Showtime.screen_id
    ).outerjoin(
        Booking, Showtime.id == Booking.showtime_id
    ).outerjoin(
        Payment, Booking.id == Payment.booking_id
    ).filter(
        or_(Booking.status.in_(['confirmed', 'completed']), Booking.status.is_(None))
    ).group_by(
        Theater.id, Theater.name
    ).order_by(
        desc('total_revenue')
    ).limit(limit).all()
    
    performances = []
    for stat in theater_stats:
        # Calculate occupancy rate (placeholder logic)
        occupancy_rate = min(0.90, (stat.total_bookings or 0) * 0.15)
        
        performances.append(TheaterPerformance(
            theater_id=stat.id,
            name=stat.name,
            total_bookings=int(stat.total_bookings or 0),
            total_revenue=float(stat.total_revenue or 0.0),
            occupancy_rate=float(occupancy_rate),
            average_ticket_price=float(stat.avg_ticket_price or 0.0)
        ))
    
    return performances

async def get_time_series_data(db: Session, days: int = 30) -> List[TimeSeriesData]:
    """Get time series data for revenue, bookings, and users"""
    logger.info(f"Getting time series data for {days} days")
    
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    time_series = []
    current_date = start_date
    
    while current_date <= now:
        day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # Revenue for this day
        daily_revenue = db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.status == 'completed',
                Payment.payment_date >= day_start,
                Payment.payment_date < day_end
            )
        ).scalar() or 0.0
        
        # Bookings for this day
        daily_bookings = db.query(func.count(Booking.id)).filter(
            and_(
                Booking.status.in_(['confirmed', 'completed']),
                Booking.booking_date >= day_start,
                Booking.booking_date < day_end
            )
        ).scalar() or 0
        
        # New users for this day
        daily_users = db.query(func.count(User.id)).filter(
            and_(
                User.created_at >= day_start,
                User.created_at < day_end
            )
        ).scalar() or 0
        
        time_series.append(TimeSeriesData(
            date=current_date.strftime('%Y-%m-%d'),
            revenue=float(daily_revenue),
            bookings=int(daily_bookings),
            users=int(daily_users)
        ))
        
        current_date += timedelta(days=1)
    
    return time_series

# API Endpoints
@app.get("/analytics/dashboard", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    days: int = Query(30, description="Number of days for time series data"),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics dashboard"""
    cache_key = get_cache_key("dashboard", f"days_{days}")
    cached_result = get_cached_result(cache_key)
    
    if cached_result:
        logger.info("Returning cached analytics dashboard")
        return AnalyticsDashboard(**cached_result)
    
    logger.info("Calculating fresh analytics dashboard")
    
    try:
        # Calculate all metrics concurrently
        revenue_metrics = await calculate_revenue_metrics(db)
        booking_metrics = await calculate_booking_metrics(db)
        user_metrics = await calculate_user_metrics(db)
        top_movies = await get_movie_performance(db)
        top_theaters = await get_theater_performance(db)
        time_series = await get_time_series_data(db, days)
        
        dashboard = AnalyticsDashboard(
            revenue_metrics=revenue_metrics,
            booking_metrics=booking_metrics,
            user_metrics=user_metrics,
            top_movies=top_movies,
            top_theaters=top_theaters,
            time_series=time_series,
            last_updated=datetime.now().isoformat()
        )
        
        # Cache the result
        cache_result(cache_key, dashboard.dict())
        
        logger.info("Analytics dashboard calculated successfully")
        return dashboard
        
    except Exception as e:
        logger.error(f"Error calculating analytics dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics calculation failed: {str(e)}")

@app.get("/analytics/revenue", response_model=RevenueMetrics)
async def get_revenue_metrics(db: Session = Depends(get_db)):
    """Get detailed revenue metrics"""
    cache_key = get_cache_key("revenue")
    cached_result = get_cached_result(cache_key)
    
    if cached_result:
        return RevenueMetrics(**cached_result)
    
    metrics = await calculate_revenue_metrics(db)
    cache_result(cache_key, metrics.dict())
    return metrics

@app.get("/analytics/bookings", response_model=BookingMetrics)
async def get_booking_metrics(db: Session = Depends(get_db)):
    """Get detailed booking metrics"""
    cache_key = get_cache_key("bookings")
    cached_result = get_cached_result(cache_key)
    
    if cached_result:
        return BookingMetrics(**cached_result)
    
    metrics = await calculate_booking_metrics(db)
    cache_result(cache_key, metrics.dict())
    return metrics

@app.get("/analytics/users", response_model=UserMetrics)
async def get_user_metrics(db: Session = Depends(get_db)):
    """Get detailed user metrics"""
    cache_key = get_cache_key("users")
    cached_result = get_cached_result(cache_key)
    
    if cached_result:
        return UserMetrics(**cached_result)
    
    metrics = await calculate_user_metrics(db)
    cache_result(cache_key, metrics.dict())
    return metrics

@app.get("/analytics/movies", response_model=List[MoviePerformance])
async def get_top_movies(
    limit: int = Query(10, description="Number of top movies to return"),
    db: Session = Depends(get_db)
):
    """Get top performing movies"""
    cache_key = get_cache_key("movies", f"limit_{limit}")
    cached_result = get_cached_result(cache_key)
    
    if cached_result:
        return [MoviePerformance(**movie) for movie in cached_result]
    
    movies = await get_movie_performance(db, limit)
    cache_result(cache_key, [movie.dict() for movie in movies])
    return movies

@app.get("/analytics/theaters", response_model=List[TheaterPerformance])
async def get_top_theaters(
    limit: int = Query(10, description="Number of top theaters to return"),
    db: Session = Depends(get_db)
):
    """Get top performing theaters"""
    cache_key = get_cache_key("theaters", f"limit_{limit}")
    cached_result = get_cached_result(cache_key)
    
    if cached_result:
        return [TheaterPerformance(**theater) for theater in cached_result]
    
    theaters = await get_theater_performance(db, limit)
    cache_result(cache_key, [theater.dict() for theater in theaters])
    return theaters

@app.get("/analytics/timeseries", response_model=List[TimeSeriesData])
async def get_analytics_timeseries(
    days: int = Query(30, description="Number of days of historical data"),
    db: Session = Depends(get_db)
):
    """Get time series analytics data"""
    cache_key = get_cache_key("timeseries", f"days_{days}")
    cached_result = get_cached_result(cache_key)
    
    if cached_result:
        return [TimeSeriesData(**data) for data in cached_result]
    
    time_series = await get_time_series_data(db, days)
    cache_result(cache_key, [data.dict() for data in time_series])
    return time_series

@app.post("/analytics/refresh")
async def refresh_analytics_cache(background_tasks: BackgroundTasks):
    """Refresh all analytics cache"""
    def clear_cache():
        if redis_client:
            try:
                keys = redis_client.keys("analytics:*")
                if keys:
                    redis_client.delete(*keys)
                    logger.info(f"Cleared {len(keys)} analytics cache entries")
            except Exception as e:
                logger.error(f"Failed to clear analytics cache: {e}")
    
    background_tasks.add_task(clear_cache)
    return {"message": "Analytics cache refresh initiated"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "analytics",
        "timestamp": datetime.now().isoformat(),
        "redis_connected": redis_client is not None
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Advanced Analytics Service")
    uvicorn.run(app, host="127.0.0.1", port=8010)