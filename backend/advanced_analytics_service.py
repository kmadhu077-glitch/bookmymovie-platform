"""
BookMyMovie Platform - Advanced Analytics Service
Provides comprehensive analytics, reporting, and business intelligence

Features:
- User behavior analytics
- Booking pattern analysis
- Revenue analytics
- Real-time metrics
- Performance monitoring
- Conversion funnel analysis
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter
import statistics

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import sqlite3
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Analytics Models
class UserAnalytics(BaseModel):
    user_id: int
    total_bookings: int
    total_spent: float
    avg_booking_value: float
    favorite_genre: Optional[str]
    last_booking_date: Optional[datetime]
    registration_date: datetime
    loyalty_score: float

class BookingAnalytics(BaseModel):
    booking_id: int
    user_id: int
    movie_id: int
    cinema_id: int
    showtime_id: int
    seats_booked: int
    total_amount: float
    booking_date: datetime
    payment_method: str
    booking_status: str

class RevenueMetrics(BaseModel):
    period: str
    total_revenue: float
    total_bookings: int
    avg_booking_value: float
    peak_hours: List[str]
    popular_movies: List[Dict[str, Any]]

class AnalyticsDashboard(BaseModel):
    overview: Dict[str, Any]
    user_metrics: Dict[str, Any]
    booking_metrics: Dict[str, Any]
    revenue_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]

class AnalyticsService:
    def __init__(self):
        self.db_path = "bookmymovie_analytics.db"
        self.real_time_metrics = defaultdict(int)
        self.init_database()
    
    def init_database(self):
        """Initialize analytics database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # User analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_analytics (
                    user_id INTEGER PRIMARY KEY,
                    total_bookings INTEGER DEFAULT 0,
                    total_spent REAL DEFAULT 0.0,
                    favorite_genre TEXT,
                    last_booking_date TEXT,
                    registration_date TEXT,
                    loyalty_score REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Booking analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS booking_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_id INTEGER,
                    user_id INTEGER,
                    movie_id INTEGER,
                    cinema_id INTEGER,
                    showtime_id INTEGER,
                    seats_booked INTEGER,
                    total_amount REAL,
                    booking_date TEXT,
                    payment_method TEXT,
                    booking_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Revenue analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revenue_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_type TEXT,
                    period_value TEXT,
                    total_revenue REAL,
                    total_bookings INTEGER,
                    avg_booking_value REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    metric_value REAL,
                    timestamp TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User behavior events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT,
                    event_data TEXT,
                    timestamp TEXT,
                    session_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
            # Generate sample analytics data
            self.generate_sample_analytics_data()
            
            logger.info("Analytics database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize analytics database: {str(e)}")
            raise
    
    def generate_sample_analytics_data(self):
        """Generate sample analytics data for demonstration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we already have data
            cursor.execute("SELECT COUNT(*) FROM booking_analytics")
            if cursor.fetchone()[0] > 0:
                conn.close()
                return
            
            # Sample user analytics
            sample_users = [
                (1, 15, 450.0, "Action", "2024-12-15", "2024-01-15", 85.5),
                (2, 8, 240.0, "Comedy", "2024-12-14", "2024-02-20", 72.0),
                (3, 25, 750.0, "Drama", "2024-12-16", "2024-01-10", 92.5),
                (4, 12, 360.0, "Horror", "2024-12-13", "2024-03-05", 68.0),
                (5, 20, 600.0, "Sci-Fi", "2024-12-15", "2024-01-25", 88.0),
            ]
            
            cursor.executemany("""
                INSERT INTO user_analytics (user_id, total_bookings, total_spent, favorite_genre, 
                                          last_booking_date, registration_date, loyalty_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, sample_users)
            
            # Sample booking analytics
            sample_bookings = []
            for i in range(1, 51):
                booking = (
                    i,  # booking_id
                    (i % 5) + 1,  # user_id
                    (i % 10) + 1,  # movie_id
                    (i % 3) + 1,  # cinema_id
                    (i % 15) + 1,  # showtime_id
                    2 + (i % 4),  # seats_booked
                    25.0 + (i * 2.5),  # total_amount
                    f"2024-12-{10 + (i % 20):02d}",  # booking_date
                    ["Credit Card", "PayPal", "Debit Card"][i % 3],  # payment_method
                    ["Confirmed", "Completed", "Cancelled"][i % 3 if i % 10 != 0 else 2]  # booking_status
                )
                sample_bookings.append(booking)
            
            cursor.executemany("""
                INSERT INTO booking_analytics (booking_id, user_id, movie_id, cinema_id, showtime_id,
                                             seats_booked, total_amount, booking_date, payment_method, booking_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sample_bookings)
            
            # Sample performance metrics
            metrics = [
                ("response_time_auth", 45.5, "2024-12-16 10:00:00"),
                ("response_time_catalog", 38.2, "2024-12-16 10:00:00"),
                ("response_time_booking", 52.1, "2024-12-16 10:00:00"),
                ("cpu_usage", 35.7, "2024-12-16 10:00:00"),
                ("memory_usage", 68.3, "2024-12-16 10:00:00"),
                ("active_users", 125, "2024-12-16 10:00:00"),
                ("conversion_rate", 23.5, "2024-12-16 10:00:00"),
            ]
            
            cursor.executemany("""
                INSERT INTO performance_metrics (metric_name, metric_value, timestamp)
                VALUES (?, ?, ?)
            """, metrics)
            
            conn.commit()
            conn.close()
            
            logger.info("Sample analytics data generated successfully")
            
        except Exception as e:
            logger.error(f"Failed to generate sample analytics data: {str(e)}")
    
    async def track_user_event(self, user_id: int, event_type: str, event_data: Dict[str, Any], 
                             session_id: str = None, ip_address: str = None, user_agent: str = None):
        """Track user behavior events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_events (user_id, event_type, event_data, timestamp, session_id, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, event_type, json.dumps(event_data), datetime.now().isoformat(), 
                  session_id, ip_address, user_agent))
            
            conn.commit()
            conn.close()
            
            # Update real-time metrics
            self.real_time_metrics[f"event_{event_type}"] += 1
            
        except Exception as e:
            logger.error(f"Failed to track user event: {str(e)}")
    
    async def get_user_analytics(self, user_id: Optional[int] = None) -> List[UserAnalytics]:
        """Get user analytics data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("SELECT * FROM user_analytics WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("SELECT * FROM user_analytics")
            
            results = []
            for row in cursor.fetchall():
                user_analytics = UserAnalytics(
                    user_id=row[0],
                    total_bookings=row[1],
                    total_spent=row[2],
                    avg_booking_value=row[2] / row[1] if row[1] > 0 else 0,
                    favorite_genre=row[3],
                    last_booking_date=datetime.fromisoformat(row[4]) if row[4] else None,
                    registration_date=datetime.fromisoformat(row[5]),
                    loyalty_score=row[6]
                )
                results.append(user_analytics)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get user analytics: {str(e)}")
            return []
    
    async def get_booking_analytics(self, period_days: int = 30) -> List[BookingAnalytics]:
        """Get booking analytics data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            start_date = (datetime.now() - timedelta(days=period_days)).isoformat()
            
            cursor.execute("""
                SELECT * FROM booking_analytics 
                WHERE booking_date >= ? 
                ORDER BY booking_date DESC
            """, (start_date,))
            
            results = []
            for row in cursor.fetchall()[1:]:  # Skip the id column
                booking_analytics = BookingAnalytics(
                    booking_id=row[1],
                    user_id=row[2],
                    movie_id=row[3],
                    cinema_id=row[4],
                    showtime_id=row[5],
                    seats_booked=row[6],
                    total_amount=row[7],
                    booking_date=datetime.fromisoformat(row[8]),
                    payment_method=row[9],
                    booking_status=row[10]
                )
                results.append(booking_analytics)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get booking analytics: {str(e)}")
            return []
    
    async def get_revenue_metrics(self, period: str = "daily") -> RevenueMetrics:
        """Get revenue metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total revenue and bookings
            cursor.execute("""
                SELECT 
                    SUM(total_amount) as total_revenue,
                    COUNT(*) as total_bookings,
                    AVG(total_amount) as avg_booking_value
                FROM booking_analytics 
                WHERE booking_status != 'Cancelled'
            """)
            
            revenue_data = cursor.fetchone()
            
            # Get peak hours (mock data for now)
            peak_hours = ["19:00", "20:00", "21:00"]
            
            # Get popular movies (mock data for now)
            popular_movies = [
                {"movie_id": 1, "title": "Avatar 3", "bookings": 25, "revenue": 625.0},
                {"movie_id": 2, "title": "Top Gun 3", "bookings": 20, "revenue": 500.0},
                {"movie_id": 3, "title": "Spider-Man 5", "bookings": 18, "revenue": 450.0}
            ]
            
            conn.close()
            
            return RevenueMetrics(
                period=period,
                total_revenue=revenue_data[0] or 0.0,
                total_bookings=revenue_data[1] or 0,
                avg_booking_value=revenue_data[2] or 0.0,
                peak_hours=peak_hours,
                popular_movies=popular_movies
            )
            
        except Exception as e:
            logger.error(f"Failed to get revenue metrics: {str(e)}")
            return RevenueMetrics(
                period=period,
                total_revenue=0.0,
                total_bookings=0,
                avg_booking_value=0.0,
                peak_hours=[],
                popular_movies=[]
            )
    
    async def get_dashboard_analytics(self) -> AnalyticsDashboard:
        """Get comprehensive dashboard analytics"""
        try:
            # Get all analytics data
            user_analytics = await self.get_user_analytics()
            booking_analytics = await self.get_booking_analytics()
            revenue_metrics = await self.get_revenue_metrics()
            
            # Calculate overview metrics
            overview = {
                "total_users": len(user_analytics),
                "total_bookings": len(booking_analytics),
                "total_revenue": revenue_metrics.total_revenue,
                "avg_booking_value": revenue_metrics.avg_booking_value,
                "active_users_today": self.real_time_metrics.get("active_users_today", 45),
                "conversion_rate": 23.5  # Mock data
            }
            
            # User metrics
            if user_analytics:
                user_metrics = {
                    "avg_loyalty_score": statistics.mean([u.loyalty_score for u in user_analytics]),
                    "avg_bookings_per_user": statistics.mean([u.total_bookings for u in user_analytics]),
                    "avg_spend_per_user": statistics.mean([u.total_spent for u in user_analytics]),
                    "top_genres": ["Action", "Comedy", "Drama", "Sci-Fi", "Horror"]
                }
            else:
                user_metrics = {
                    "avg_loyalty_score": 0,
                    "avg_bookings_per_user": 0,
                    "avg_spend_per_user": 0,
                    "top_genres": []
                }
            
            # Booking metrics
            if booking_analytics:
                booking_metrics = {
                    "total_seats_booked": sum([b.seats_booked for b in booking_analytics]),
                    "avg_seats_per_booking": statistics.mean([b.seats_booked for b in booking_analytics]),
                    "payment_method_distribution": dict(Counter([b.payment_method for b in booking_analytics])),
                    "booking_status_distribution": dict(Counter([b.booking_status for b in booking_analytics]))
                }
            else:
                booking_metrics = {
                    "total_seats_booked": 0,
                    "avg_seats_per_booking": 0,
                    "payment_method_distribution": {},
                    "booking_status_distribution": {}
                }
            
            # Performance metrics
            performance_metrics = {
                "avg_response_time": 42.3,
                "uptime_percentage": 99.8,
                "error_rate": 0.2,
                "cache_hit_rate": 85.7,
                "active_connections": self.real_time_metrics.get("active_connections", 15)
            }
            
            return AnalyticsDashboard(
                overview=overview,
                user_metrics=user_metrics,
                booking_metrics=booking_metrics,
                revenue_metrics=revenue_metrics.dict(),
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            logger.error(f"Failed to get dashboard analytics: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")

# Initialize analytics service
analytics_service = AnalyticsService()

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BookMyMovie Analytics Service...")
    yield
    logger.info("Shutting down BookMyMovie Analytics Service...")

app = FastAPI(
    title="BookMyMovie Analytics Service",
    description="Advanced Analytics and Business Intelligence API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Analytics API Endpoints

@app.get("/")
async def root():
    return {
        "service": "BookMyMovie Analytics Service",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "dashboard": "/dashboard",
            "users": "/users/analytics",
            "bookings": "/bookings/analytics",
            "revenue": "/revenue/metrics",
            "events": "/events/track"
        }
    }

@app.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard():
    """Get comprehensive analytics dashboard"""
    return await analytics_service.get_dashboard_analytics()

@app.get("/users/analytics", response_model=List[UserAnalytics])
async def get_user_analytics(user_id: Optional[int] = Query(None)):
    """Get user analytics data"""
    return await analytics_service.get_user_analytics(user_id)

@app.get("/bookings/analytics", response_model=List[BookingAnalytics])
async def get_booking_analytics(period_days: int = Query(30, ge=1, le=365)):
    """Get booking analytics data"""
    return await analytics_service.get_booking_analytics(period_days)

@app.get("/revenue/metrics", response_model=RevenueMetrics)
async def get_revenue_metrics(period: str = Query("daily", pattern="^(daily|weekly|monthly|yearly)$")):
    """Get revenue metrics"""
    return await analytics_service.get_revenue_metrics(period)

@app.post("/events/track")
async def track_event(
    user_id: int,
    event_type: str,
    event_data: Dict[str, Any],
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Track user behavior events"""
    await analytics_service.track_user_event(
        user_id, event_type, event_data, session_id, ip_address, user_agent
    )
    return {"status": "Event tracked successfully"}

@app.get("/metrics/realtime")
async def get_realtime_metrics():
    """Get real-time platform metrics"""
    return {
        "timestamp": datetime.now().isoformat(),
        "active_users": analytics_service.real_time_metrics.get("active_users", 45),
        "active_sessions": analytics_service.real_time_metrics.get("active_sessions", 32),
        "current_bookings": analytics_service.real_time_metrics.get("current_bookings", 8),
        "revenue_today": analytics_service.real_time_metrics.get("revenue_today", 1250.0),
        "page_views": analytics_service.real_time_metrics.get("page_views", 567),
        "api_requests": analytics_service.real_time_metrics.get("api_requests", 1234)
    }

@app.get("/analytics-dashboard", response_class=HTMLResponse)
async def analytics_dashboard():
    """Serve the analytics dashboard HTML"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BookMyMovie Analytics Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .dashboard { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .metric-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .metric-value { font-size: 2em; font-weight: bold; color: #3498db; }
            .metric-label { color: #666; margin-top: 5px; }
            .chart-container { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .refresh-btn { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
            .refresh-btn:hover { background: #2980b9; }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="header">
                <h1>📊 BookMyMovie Analytics Dashboard</h1>
                <p>Real-time insights and business intelligence</p>
            </div>
            
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
            
            <div class="metrics-grid" id="metricsGrid">
                <!-- Metrics will be loaded here -->
            </div>
            
            <div class="chart-container">
                <h3>Revenue Trends</h3>
                <canvas id="revenueChart" width="400" height="200"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>Booking Status Distribution</h3>
                <canvas id="bookingChart" width="400" height="200"></canvas>
            </div>
        </div>

        <script>
            let revenueChart, bookingChart;

            async function loadDashboard() {
                try {
                    const response = await fetch('/dashboard');
                    const data = await response.json();
                    
                    // Update metrics
                    updateMetrics(data);
                    
                    // Update charts
                    updateCharts(data);
                    
                } catch (error) {
                    console.error('Failed to load dashboard:', error);
                }
            }

            function updateMetrics(data) {
                const metricsGrid = document.getElementById('metricsGrid');
                metricsGrid.innerHTML = `
                    <div class="metric-card">
                        <div class="metric-value">${data.overview.total_users}</div>
                        <div class="metric-label">Total Users</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${data.overview.total_bookings}</div>
                        <div class="metric-label">Total Bookings</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">$${data.overview.total_revenue.toFixed(2)}</div>
                        <div class="metric-label">Total Revenue</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">$${data.overview.avg_booking_value.toFixed(2)}</div>
                        <div class="metric-label">Avg Booking Value</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${data.overview.active_users_today}</div>
                        <div class="metric-label">Active Users Today</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${data.overview.conversion_rate}%</div>
                        <div class="metric-label">Conversion Rate</div>
                    </div>
                `;
            }

            function updateCharts(data) {
                // Revenue Chart
                const revenueCtx = document.getElementById('revenueChart').getContext('2d');
                if (revenueChart) revenueChart.destroy();
                
                revenueChart = new Chart(revenueCtx, {
                    type: 'line',
                    data: {
                        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                        datasets: [{
                            label: 'Revenue',
                            data: [1200, 1900, 3000, 5000, 2000, 3000, 4500],
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });

                // Booking Status Chart
                const bookingCtx = document.getElementById('bookingChart').getContext('2d');
                if (bookingChart) bookingChart.destroy();
                
                const statusData = data.booking_metrics.booking_status_distribution || {};
                
                bookingChart = new Chart(bookingCtx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(statusData),
                        datasets: [{
                            data: Object.values(statusData),
                            backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c']
                        }]
                    },
                    options: {
                        responsive: true
                    }
                });
            }

            function refreshData() {
                loadDashboard();
            }

            // Load dashboard on page load
            loadDashboard();
            
            // Auto-refresh every 30 seconds
            setInterval(loadDashboard, 30000);
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "BookMyMovie Analytics Service",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    logger.info("Starting BookMyMovie Analytics Service on port 8017...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8017,
        log_level="info",
        reload=True
    )