"""
Advanced Analytics & Business Intelligence Service
Enterprise-grade analytics platform with real-time insights, predictive analytics, and executive reporting
"""

import os
import sys
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import sqlite3
from dataclasses import dataclass
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

# Analytics Data Models
@dataclass
class UserMetrics:
    total_users: int
    active_users: int
    new_users: int
    retention_rate: float
    churn_rate: float

@dataclass
class RevenueMetrics:
    total_revenue: float
    revenue_growth: float
    average_ticket_price: float
    revenue_per_user: float
    projected_revenue: float

@dataclass
class BookingMetrics:
    total_bookings: int
    conversion_rate: float
    cancellation_rate: float
    popular_movies: List[str]
    peak_hours: List[int]

@dataclass
class TheaterMetrics:
    occupancy_rate: float
    most_popular_theaters: List[str]
    seat_utilization: Dict[str, float]
    geographic_distribution: Dict[str, int]

class AdvancedAnalyticsService:
    def __init__(self, db_path: str = "analytics_data.db"):
        self.db_path = db_path
        self.app = FastAPI(title="BookMyMovie Advanced Analytics", version="1.0.0")
        self.setup_database()
        self.setup_routes()
        self.setup_cors()
        
        # Create static directory for serving charts
        os.makedirs("static/charts", exist_ok=True)
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        
    def setup_cors(self):
        """Setup CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_database(self):
        """Initialize analytics database with sample data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create analytics tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            action_data TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS booking_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            user_id INTEGER,
            movie_id INTEGER,
            theater_id INTEGER,
            amount REAL,
            booking_date DATETIME,
            status TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS revenue_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            revenue REAL,
            bookings_count INTEGER,
            theater_id INTEGER
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS movie_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER,
            title TEXT,
            views INTEGER,
            bookings INTEGER,
            revenue REAL,
            rating REAL,
            date DATE
        )
        ''')
        
        # Generate sample analytics data
        self.generate_sample_data(cursor)
        
        conn.commit()
        conn.close()
    
    def generate_sample_data(self, cursor):
        """Generate comprehensive sample data for analytics"""
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM user_analytics")
        if cursor.fetchone()[0] > 0:
            return
        
        # Generate user analytics data (last 30 days)
        base_date = datetime.now() - timedelta(days=30)
        user_actions = ['login', 'search', 'view_movie', 'book_ticket', 'cancel_booking', 'rate_movie']
        
        for day in range(30):
            current_date = base_date + timedelta(days=day)
            daily_actions = np.random.randint(50, 200)  # Random actions per day
            
            for _ in range(daily_actions):
                user_id = np.random.randint(1, 100)
                action = np.random.choice(user_actions)
                action_data = json.dumps({
                    'movie_id': np.random.randint(1, 20),
                    'theater_id': np.random.randint(1, 10),
                    'session_duration': np.random.randint(60, 3600)
                })
                
                cursor.execute('''
                INSERT INTO user_analytics (user_id, action_type, action_data, timestamp)
                VALUES (?, ?, ?, ?)
                ''', (user_id, action, action_data, current_date))
        
        # Generate booking analytics data
        movie_titles = [
            'Avatar: The Way of Water', 'Top Gun: Maverick', 'Black Panther: Wakanda Forever',
            'Thor: Love and Thunder', 'Minions: The Rise of Gru', 'Doctor Strange 2',
            'Jurassic World Dominion', 'The Batman', 'Spider-Man: No Way Home',
            'Fast & Furious 9', 'Dune', 'No Time to Die', 'Eternals', 'Venom 2',
            'Shang-Chi', 'Ghostbusters: Afterlife', 'Matrix Resurrections', 'West Side Story',
            'House of Gucci', 'The French Dispatch'
        ]
        
        for day in range(30):
            current_date = base_date + timedelta(days=day)
            daily_bookings = np.random.randint(20, 80)
            
            for _ in range(daily_bookings):
                booking_id = np.random.randint(1000, 9999)
                user_id = np.random.randint(1, 100)
                movie_id = np.random.randint(1, 20)
                theater_id = np.random.randint(1, 10)
                amount = round(np.random.uniform(8.0, 25.0), 2)
                status = np.random.choice(['completed', 'cancelled'], p=[0.9, 0.1])
                
                cursor.execute('''
                INSERT INTO booking_analytics (booking_id, user_id, movie_id, theater_id, amount, booking_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (booking_id, user_id, movie_id, theater_id, amount, current_date, status))
        
        # Generate revenue analytics data
        for day in range(30):
            current_date = (base_date + timedelta(days=day)).date()
            
            for theater_id in range(1, 11):
                daily_revenue = round(np.random.uniform(500.0, 3000.0), 2)
                bookings_count = np.random.randint(10, 50)
                
                cursor.execute('''
                INSERT INTO revenue_analytics (date, revenue, bookings_count, theater_id)
                VALUES (?, ?, ?, ?)
                ''', (current_date, daily_revenue, bookings_count, theater_id))
        
        # Generate movie analytics data
        for movie_id, title in enumerate(movie_titles, 1):
            for day in range(30):
                current_date = (base_date + timedelta(days=day)).date()
                views = np.random.randint(50, 500)
                bookings = np.random.randint(5, 50)
                revenue = round(bookings * np.random.uniform(10.0, 20.0), 2)
                rating = round(np.random.uniform(6.0, 9.5), 1)
                
                cursor.execute('''
                INSERT INTO movie_analytics (movie_id, title, views, bookings, revenue, rating, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (movie_id, title, views, bookings, revenue, rating, current_date))
    
    def get_user_metrics(self, days: int = 30) -> UserMetrics:
        """Calculate comprehensive user metrics"""
        conn = sqlite3.connect(self.db_path)
        
        # Total and active users
        total_users_query = "SELECT COUNT(DISTINCT user_id) FROM user_analytics"
        active_users_query = f"""
        SELECT COUNT(DISTINCT user_id) FROM user_analytics 
        WHERE timestamp >= date('now', '-{days} days')
        """
        new_users_query = f"""
        SELECT COUNT(DISTINCT user_id) FROM user_analytics 
        WHERE user_id IN (
            SELECT user_id FROM user_analytics 
            GROUP BY user_id 
            HAVING MIN(timestamp) >= date('now', '-{days} days')
        )
        """
        
        total_users = pd.read_sql(total_users_query, conn).iloc[0, 0]
        active_users = pd.read_sql(active_users_query, conn).iloc[0, 0]
        new_users = pd.read_sql(new_users_query, conn).iloc[0, 0]
        
        # Calculate retention and churn rates
        retention_rate = (active_users / total_users * 100) if total_users > 0 else 0
        churn_rate = 100 - retention_rate
        
        conn.close()
        return UserMetrics(
            total_users=total_users,
            active_users=active_users,
            new_users=new_users,
            retention_rate=round(retention_rate, 2),
            churn_rate=round(churn_rate, 2)
        )
    
    def get_revenue_metrics(self, days: int = 30) -> RevenueMetrics:
        """Calculate comprehensive revenue metrics"""
        conn = sqlite3.connect(self.db_path)
        
        # Current period revenue
        current_revenue_query = f"""
        SELECT SUM(revenue) as total_revenue, AVG(revenue/bookings_count) as avg_ticket_price
        FROM revenue_analytics 
        WHERE date >= date('now', '-{days} days')
        """
        
        # Previous period for growth calculation
        previous_revenue_query = f"""
        SELECT SUM(revenue) as prev_revenue
        FROM revenue_analytics 
        WHERE date >= date('now', '-{days*2} days') AND date < date('now', '-{days} days')
        """
        
        current_data = pd.read_sql(current_revenue_query, conn).iloc[0]
        previous_data = pd.read_sql(previous_revenue_query, conn).iloc[0]
        
        total_revenue = current_data['total_revenue'] or 0
        avg_ticket_price = current_data['avg_ticket_price'] or 0
        prev_revenue = previous_data['prev_revenue'] or 1
        
        # Calculate growth rate
        revenue_growth = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        # Revenue per user
        user_metrics = self.get_user_metrics(days)
        revenue_per_user = (total_revenue / user_metrics.active_users) if user_metrics.active_users > 0 else 0
        
        # Projected revenue (simple linear projection)
        projected_revenue = total_revenue * (1 + revenue_growth / 100)
        
        conn.close()
        return RevenueMetrics(
            total_revenue=round(total_revenue, 2),
            revenue_growth=round(revenue_growth, 2),
            average_ticket_price=round(avg_ticket_price, 2),
            revenue_per_user=round(revenue_per_user, 2),
            projected_revenue=round(projected_revenue, 2)
        )
    
    def get_booking_metrics(self, days: int = 30) -> BookingMetrics:
        """Calculate comprehensive booking metrics"""
        conn = sqlite3.connect(self.db_path)
        
        # Total bookings and conversion rate
        total_bookings_query = f"""
        SELECT COUNT(*) as total_bookings,
               SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_bookings
        FROM booking_analytics 
        WHERE booking_date >= date('now', '-{days} days')
        """
        
        booking_data = pd.read_sql(total_bookings_query, conn).iloc[0]
        total_bookings = booking_data['total_bookings']
        cancelled_bookings = booking_data['cancelled_bookings']
        
        # Get user views for conversion calculation
        total_views_query = f"""
        SELECT COUNT(*) as total_views
        FROM user_analytics 
        WHERE action_type = 'view_movie' AND timestamp >= date('now', '-{days} days')
        """
        total_views = pd.read_sql(total_views_query, conn).iloc[0]['total_views']
        
        conversion_rate = (total_bookings / total_views * 100) if total_views > 0 else 0
        cancellation_rate = (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0
        
        # Popular movies
        popular_movies_query = f"""
        SELECT m.title, SUM(b.amount) as revenue
        FROM booking_analytics b
        JOIN movie_analytics m ON b.movie_id = m.movie_id
        WHERE b.booking_date >= date('now', '-{days} days')
        GROUP BY m.title
        ORDER BY revenue DESC
        LIMIT 5
        """
        popular_movies = pd.read_sql(popular_movies_query, conn)['title'].tolist()
        
        # Peak booking hours
        peak_hours_query = f"""
        SELECT strftime('%H', booking_date) as hour, COUNT(*) as bookings
        FROM booking_analytics 
        WHERE booking_date >= date('now', '-{days} days')
        GROUP BY hour
        ORDER BY bookings DESC
        LIMIT 3
        """
        peak_hours = [int(h) for h in pd.read_sql(peak_hours_query, conn)['hour'].tolist()]
        
        conn.close()
        return BookingMetrics(
            total_bookings=total_bookings,
            conversion_rate=round(conversion_rate, 2),
            cancellation_rate=round(cancellation_rate, 2),
            popular_movies=popular_movies,
            peak_hours=peak_hours
        )
    
    def generate_revenue_forecast(self, days_ahead: int = 30) -> Dict[str, Any]:
        """Generate revenue forecast using machine learning"""
        conn = sqlite3.connect(self.db_path)
        
        # Get historical revenue data
        query = """
        SELECT date, SUM(revenue) as daily_revenue
        FROM revenue_analytics
        GROUP BY date
        ORDER BY date
        """
        df = pd.read_sql(query, query)
        df['date'] = pd.to_datetime(df['date'])
        df['day_number'] = (df['date'] - df['date'].min()).dt.days
        
        # Prepare data for ML model
        X = df[['day_number']].values
        y = df['daily_revenue'].values
        
        # Train Random Forest model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # Generate predictions
        last_day = df['day_number'].max()
        future_days = np.array([[last_day + i] for i in range(1, days_ahead + 1)])
        predictions = model.predict(future_days)
        
        # Create forecast data
        forecast_dates = [df['date'].max() + timedelta(days=i) for i in range(1, days_ahead + 1)]
        forecast_data = [
            {
                'date': date.strftime('%Y-%m-%d'),
                'predicted_revenue': round(pred, 2),
                'confidence': round(np.random.uniform(0.85, 0.95), 2)  # Mock confidence
            }
            for date, pred in zip(forecast_dates, predictions)
        ]
        
        # Calculate forecast summary
        total_forecast = sum(predictions)
        avg_daily_forecast = np.mean(predictions)
        growth_trend = (predictions[-1] - predictions[0]) / predictions[0] * 100 if predictions[0] > 0 else 0
        
        conn.close()
        return {
            'forecast_period': days_ahead,
            'total_predicted_revenue': round(total_forecast, 2),
            'average_daily_revenue': round(avg_daily_forecast, 2),
            'growth_trend_percent': round(growth_trend, 2),
            'daily_forecasts': forecast_data,
            'model_accuracy': round(model.score(X, y), 2)
        }
    
    def create_revenue_chart(self) -> str:
        """Create interactive revenue chart"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT date, SUM(revenue) as daily_revenue
        FROM revenue_analytics
        GROUP BY date
        ORDER BY date
        """
        df = pd.read_sql(query, conn)
        
        fig = px.line(df, x='date', y='daily_revenue', 
                     title='Daily Revenue Trend',
                     labels={'daily_revenue': 'Revenue ($)', 'date': 'Date'})
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        
        chart_path = "static/charts/revenue_trend.html"
        fig.write_html(chart_path)
        conn.close()
        return chart_path
    
    def create_user_behavior_chart(self) -> str:
        """Create user behavior analysis chart"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT action_type, COUNT(*) as count
        FROM user_analytics
        WHERE timestamp >= date('now', '-30 days')
        GROUP BY action_type
        ORDER BY count DESC
        """
        df = pd.read_sql(query, conn)
        
        fig = px.pie(df, values='count', names='action_type', 
                    title='User Actions Distribution (Last 30 Days)')
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        
        chart_path = "static/charts/user_behavior.html"
        fig.write_html(chart_path)
        conn.close()
        return chart_path
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """Main analytics dashboard"""
            return """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>BookMyMovie - Advanced Analytics Dashboard</title>
                <style>
                    body { 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        margin: 0; 
                        padding: 20px; 
                        background: linear-gradient(135deg, #0F0F23 0%, #1A1A2E 100%);
                        color: white;
                        min-height: 100vh;
                    }
                    .header { 
                        text-align: center; 
                        margin-bottom: 30px;
                        padding: 20px;
                        background: rgba(229, 9, 20, 0.1);
                        border-radius: 15px;
                        border: 1px solid #E50914;
                    }
                    .header h1 { 
                        color: #E50914; 
                        margin: 0; 
                        font-size: 2.5em;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                    }
                    .header p { 
                        color: #FFD700; 
                        margin: 10px 0 0 0; 
                        font-size: 1.2em;
                    }
                    .metrics-grid { 
                        display: grid; 
                        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
                        gap: 20px; 
                        margin-bottom: 30px; 
                    }
                    .metric-card { 
                        background: rgba(26, 26, 46, 0.8);
                        border: 1px solid #333;
                        border-radius: 15px;
                        padding: 25px;
                        text-align: center;
                        transition: transform 0.3s ease, box-shadow 0.3s ease;
                        backdrop-filter: blur(10px);
                    }
                    .metric-card:hover {
                        transform: translateY(-5px);
                        box-shadow: 0 10px 25px rgba(229, 9, 20, 0.3);
                    }
                    .metric-value { 
                        font-size: 2.5em; 
                        font-weight: bold; 
                        color: #E50914;
                        margin: 10px 0;
                        text-shadow: 1px 1px 3px rgba(0,0,0,0.5);
                    }
                    .metric-label { 
                        font-size: 1em; 
                        color: #FFD700;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }
                    .metric-change { 
                        font-size: 0.9em; 
                        margin-top: 10px; 
                        padding: 5px 10px;
                        border-radius: 20px;
                        background: rgba(255, 215, 0, 0.1);
                        border: 1px solid #FFD700;
                    }
                    .charts-section { 
                        margin-top: 40px; 
                    }
                    .chart-container { 
                        background: rgba(26, 26, 46, 0.8);
                        border: 1px solid #333;
                        border-radius: 15px;
                        padding: 20px;
                        margin-bottom: 30px;
                        backdrop-filter: blur(10px);
                    }
                    .chart-container h3 { 
                        color: #FFD700; 
                        margin-top: 0;
                        font-size: 1.5em;
                        border-bottom: 2px solid #E50914;
                        padding-bottom: 10px;
                    }
                    .api-section { 
                        background: rgba(26, 26, 46, 0.8);
                        border: 1px solid #333;
                        border-radius: 15px;
                        padding: 25px;
                        margin-top: 30px;
                    }
                    .api-section h3 { 
                        color: #FFD700;
                        margin-top: 0;
                    }
                    .api-endpoint { 
                        background: rgba(15, 15, 35, 0.8);
                        border: 1px solid #E50914;
                        border-radius: 8px;
                        padding: 15px;
                        margin: 10px 0;
                        font-family: 'Courier New', monospace;
                    }
                    .refresh-btn {
                        background: linear-gradient(45deg, #E50914, #B20710);
                        color: white;
                        border: none;
                        padding: 12px 25px;
                        border-radius: 25px;
                        cursor: pointer;
                        font-size: 1em;
                        margin: 10px;
                        transition: all 0.3s ease;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                    }
                    .refresh-btn:hover {
                        background: linear-gradient(45deg, #B20710, #E50914);
                        transform: scale(1.05);
                        box-shadow: 0 5px 15px rgba(229, 9, 20, 0.4);
                    }
                    .loading { 
                        text-align: center; 
                        color: #FFD700; 
                        font-style: italic; 
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📊 BookMyMovie Analytics Dashboard</h1>
                    <p>Enterprise Business Intelligence & Predictive Analytics Platform</p>
                    <button class="refresh-btn" onclick="refreshDashboard()">🔄 Refresh Data</button>
                </div>

                <div id="metrics-container">
                    <div class="loading">Loading analytics data...</div>
                </div>

                <div class="charts-section">
                    <div class="chart-container">
                        <h3>📈 Revenue Analytics</h3>
                        <iframe src="/static/charts/revenue_trend.html" width="100%" height="500" frameborder="0"></iframe>
                    </div>
                    
                    <div class="chart-container">
                        <h3>👥 User Behavior Analysis</h3>
                        <iframe src="/static/charts/user_behavior.html" width="100%" height="500" frameborder="0"></iframe>
                    </div>
                </div>

                <div class="api-section">
                    <h3>🚀 API Endpoints</h3>
                    <div class="api-endpoint">GET /metrics/users - User analytics and engagement metrics</div>
                    <div class="api-endpoint">GET /metrics/revenue - Revenue analytics and forecasting</div>
                    <div class="api-endpoint">GET /metrics/bookings - Booking conversion and trends</div>
                    <div class="api-endpoint">GET /forecast/revenue - AI-powered revenue predictions</div>
                    <div class="api-endpoint">GET /reports/executive - Executive summary report</div>
                </div>

                <script>
                    async function loadMetrics() {
                        try {
                            const [users, revenue, bookings] = await Promise.all([
                                fetch('/metrics/users').then(r => r.json()),
                                fetch('/metrics/revenue').then(r => r.json()),
                                fetch('/metrics/bookings').then(r => r.json())
                            ]);

                            document.getElementById('metrics-container').innerHTML = `
                                <div class="metrics-grid">
                                    <div class="metric-card">
                                        <div class="metric-value">${users.total_users.toLocaleString()}</div>
                                        <div class="metric-label">Total Users</div>
                                        <div class="metric-change">Active: ${users.active_users} | New: ${users.new_users}</div>
                                    </div>
                                    <div class="metric-card">
                                        <div class="metric-value">$${revenue.total_revenue.toLocaleString()}</div>
                                        <div class="metric-label">Total Revenue</div>
                                        <div class="metric-change">${revenue.revenue_growth > 0 ? '+' : ''}${revenue.revenue_growth}% Growth</div>
                                    </div>
                                    <div class="metric-card">
                                        <div class="metric-value">${bookings.total_bookings.toLocaleString()}</div>
                                        <div class="metric-label">Total Bookings</div>
                                        <div class="metric-change">${bookings.conversion_rate}% Conversion Rate</div>
                                    </div>
                                    <div class="metric-card">
                                        <div class="metric-value">$${revenue.average_ticket_price}</div>
                                        <div class="metric-label">Avg Ticket Price</div>
                                        <div class="metric-change">RPU: $${revenue.revenue_per_user}</div>
                                    </div>
                                    <div class="metric-card">
                                        <div class="metric-value">${users.retention_rate}%</div>
                                        <div class="metric-label">User Retention</div>
                                        <div class="metric-change">Churn: ${users.churn_rate}%</div>
                                    </div>
                                    <div class="metric-card">
                                        <div class="metric-value">${bookings.cancellation_rate}%</div>
                                        <div class="metric-label">Cancellation Rate</div>
                                        <div class="metric-change">Peak Hours: ${bookings.peak_hours.join(', ')}</div>
                                    </div>
                                </div>
                            `;
                        } catch (error) {
                            document.getElementById('metrics-container').innerHTML = 
                                '<div class="loading" style="color: #E50914;">Error loading metrics. Please try again.</div>';
                        }
                    }

                    function refreshDashboard() {
                        document.getElementById('metrics-container').innerHTML = 
                            '<div class="loading">Refreshing analytics data...</div>';
                        loadMetrics();
                        
                        // Refresh charts
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    }

                    // Load metrics on page load
                    loadMetrics();
                </script>
            </body>
            </html>
            """
        
        @self.app.get("/metrics/users")
        async def get_user_metrics():
            """Get comprehensive user analytics"""
            metrics = self.get_user_metrics()
            return {
                "total_users": metrics.total_users,
                "active_users": metrics.active_users,
                "new_users": metrics.new_users,
                "retention_rate": metrics.retention_rate,
                "churn_rate": metrics.churn_rate
            }
        
        @self.app.get("/metrics/revenue")
        async def get_revenue_metrics():
            """Get comprehensive revenue analytics"""
            metrics = self.get_revenue_metrics()
            return {
                "total_revenue": metrics.total_revenue,
                "revenue_growth": metrics.revenue_growth,
                "average_ticket_price": metrics.average_ticket_price,
                "revenue_per_user": metrics.revenue_per_user,
                "projected_revenue": metrics.projected_revenue
            }
        
        @self.app.get("/metrics/bookings")
        async def get_booking_metrics():
            """Get comprehensive booking analytics"""
            metrics = self.get_booking_metrics()
            return {
                "total_bookings": metrics.total_bookings,
                "conversion_rate": metrics.conversion_rate,
                "cancellation_rate": metrics.cancellation_rate,
                "popular_movies": metrics.popular_movies,
                "peak_hours": metrics.peak_hours
            }
        
        @self.app.get("/forecast/revenue")
        async def get_revenue_forecast(days_ahead: int = Query(30, ge=1, le=90)):
            """Get AI-powered revenue forecast"""
            forecast = self.generate_revenue_forecast(days_ahead)
            return forecast
        
        @self.app.get("/reports/executive")
        async def get_executive_report():
            """Get executive summary report"""
            user_metrics = self.get_user_metrics()
            revenue_metrics = self.get_revenue_metrics()
            booking_metrics = self.get_booking_metrics()
            forecast = self.generate_revenue_forecast(30)
            
            return {
                "report_date": datetime.now().isoformat(),
                "summary": {
                    "total_users": user_metrics.total_users,
                    "total_revenue": revenue_metrics.total_revenue,
                    "revenue_growth": revenue_metrics.revenue_growth,
                    "total_bookings": booking_metrics.total_bookings,
                    "conversion_rate": booking_metrics.conversion_rate,
                    "projected_revenue_30_days": forecast["total_predicted_revenue"]
                },
                "user_analytics": user_metrics.__dict__,
                "revenue_analytics": revenue_metrics.__dict__,
                "booking_analytics": booking_metrics.__dict__,
                "revenue_forecast": forecast,
                "key_insights": [
                    f"Revenue growth of {revenue_metrics.revenue_growth}% compared to previous period",
                    f"User retention rate at {user_metrics.retention_rate}%",
                    f"Average ticket price: ${revenue_metrics.average_ticket_price}",
                    f"Peak booking hours: {', '.join(map(str, booking_metrics.peak_hours))}",
                    f"Most popular movies: {', '.join(booking_metrics.popular_movies[:3])}"
                ],
                "recommendations": [
                    "Implement targeted marketing during peak hours",
                    "Focus retention strategies on high-churn segments",
                    "Optimize pricing for revenue growth",
                    "Enhance user experience for better conversion"
                ]
            }
    
    async def generate_charts(self):
        """Generate all analytics charts"""
        self.create_revenue_chart()
        self.create_user_behavior_chart()
    
    def run(self, host: str = "0.0.0.0", port: int = 8024):
        """Run the analytics service"""
        print(f"""
        🚀 Starting BookMyMovie Advanced Analytics Service...
        
        📊 Analytics Dashboard: http://localhost:{port}
        🔍 API Documentation: http://localhost:{port}/docs
        
        📈 Key Features:
        • Real-time business metrics
        • Predictive revenue analytics
        • User behavior insights
        • Executive reporting
        • Interactive data visualization
        """)
        
        # Generate initial charts
        asyncio.create_task(self.generate_charts())
        
        uvicorn.run(self.app, host=host, port=port)

if __name__ == "__main__":
    # Initialize and run the advanced analytics service
    analytics_service = AdvancedAnalyticsService()
    analytics_service.run()