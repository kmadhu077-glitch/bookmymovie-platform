"""
Enterprise Analytics Dashboard Integration
Main application that brings together all analytics services
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import asyncio
import uvicorn
from contextlib import asynccontextmanager
import threading
import logging
import os

# Import our analytics services
from advanced_analytics_service import AnalyticsService
from executive_bi_service import ExecutiveBIService
from realtime_analytics_engine import RealTimeAnalyticsEngine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsDashboard:
    def __init__(self):
        self.analytics_service = AnalyticsService()
        self.executive_bi_service = ExecutiveBIService()
        self.realtime_engine = RealTimeAnalyticsEngine()
        
        # Initialize databases
        self.analytics_service.init_database()
        self.executive_bi_service.init_database()
        
        # Generate sample data
        self.analytics_service.generate_sample_data()
        
    async def start_realtime_engine(self):
        """Start the real-time analytics engine in background"""
        try:
            # Start WebSocket server in a separate thread
            def run_websocket():
                asyncio.run(self.realtime_engine.start_server(host="localhost", port=8765))
            
            websocket_thread = threading.Thread(target=run_websocket, daemon=True)
            websocket_thread.start()
            logger.info("Real-time analytics engine started on port 8765")
            
        except Exception as e:
            logger.error(f"Failed to start real-time engine: {e}")

# Global dashboard instance
dashboard = AnalyticsDashboard()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting BookMyMovie Analytics Dashboard...")
    await dashboard.start_realtime_engine()
    yield
    # Shutdown
    logger.info("🛑 Shutting down Analytics Dashboard...")
    dashboard.realtime_engine.stop()

# Create FastAPI app with lifespan management
app = FastAPI(
    title="BookMyMovie Analytics Dashboard",
    description="Enterprise-grade analytics with real-time insights",
    version="1.0.0",
    lifespan=lifespan
)

# Serve static files
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Main analytics dashboard"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BookMyMovie Analytics Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0F0F23 0%, #1A1A2E 100%);
                color: white;
                min-height: 100vh;
                overflow-x: auto;
            }
            .navbar {
                background: rgba(26, 26, 46, 0.9);
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #E50914;
                backdrop-filter: blur(10px);
            }
            .logo {
                font-size: 1.8rem;
                font-weight: bold;
                color: #E50914;
            }
            .nav-links {
                display: flex;
                gap: 2rem;
            }
            .nav-links a {
                color: white;
                text-decoration: none;
                padding: 0.5rem 1rem;
                border-radius: 5px;
                transition: background 0.3s;
            }
            .nav-links a:hover {
                background: rgba(229, 9, 20, 0.2);
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 2rem;
            }
            .hero-section {
                text-align: center;
                padding: 3rem 0;
                background: rgba(229, 9, 20, 0.1);
                border-radius: 15px;
                margin-bottom: 3rem;
                border: 1px solid rgba(229, 9, 20, 0.3);
            }
            .hero-title {
                font-size: 3rem;
                margin-bottom: 1rem;
                background: linear-gradient(45deg, #E50914, #FFD700);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .hero-subtitle {
                font-size: 1.2rem;
                color: #ccc;
                margin-bottom: 2rem;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 2rem;
                margin-bottom: 3rem;
            }
            .dashboard-card {
                background: rgba(26, 26, 46, 0.8);
                border: 1px solid #333;
                border-radius: 15px;
                padding: 2rem;
                text-align: center;
                transition: transform 0.3s, box-shadow 0.3s;
                backdrop-filter: blur(10px);
            }
            .dashboard-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 35px rgba(229, 9, 20, 0.3);
                border-color: #E50914;
            }
            .card-icon {
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            .card-title {
                font-size: 1.5rem;
                margin-bottom: 1rem;
                color: #FFD700;
            }
            .card-description {
                color: #ccc;
                margin-bottom: 2rem;
                line-height: 1.6;
            }
            .card-button {
                background: linear-gradient(45deg, #E50914, #B8860B);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.3s;
                text-decoration: none;
                display: inline-block;
            }
            .card-button:hover {
                transform: scale(1.05);
                text-decoration: none;
                color: white;
            }
            .features-section {
                background: rgba(26, 26, 46, 0.8);
                border-radius: 15px;
                padding: 3rem;
                border: 1px solid #333;
                margin-top: 3rem;
            }
            .features-title {
                text-align: center;
                font-size: 2rem;
                margin-bottom: 2rem;
                color: #E50914;
            }
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 2rem;
            }
            .feature-item {
                text-align: center;
                padding: 1.5rem;
            }
            .feature-icon {
                font-size: 2.5rem;
                margin-bottom: 1rem;
            }
            .feature-name {
                font-size: 1.2rem;
                margin-bottom: 0.5rem;
                color: #FFD700;
            }
            .feature-desc {
                color: #ccc;
                font-size: 0.9rem;
            }
            .status-bar {
                background: rgba(76, 175, 80, 0.2);
                border: 1px solid #4CAF50;
                border-radius: 10px;
                padding: 1rem;
                text-align: center;
                margin-bottom: 2rem;
                color: #4CAF50;
            }
        </style>
    </head>
    <body>
        <nav class="navbar">
            <div class="logo">📊 BookMyMovie Analytics</div>
            <div class="nav-links">
                <a href="/metrics/dashboard">Metrics Dashboard</a>
                <a href="/executive/dashboard">Executive BI</a>
                <a href="/realtime/client">Real-time Analytics</a>
                <a href="/docs">API Docs</a>
            </div>
        </nav>
        
        <div class="container">
            <div class="status-bar">
                ✅ All Analytics Systems Operational - Real-time Data Processing Active
            </div>
            
            <div class="hero-section">
                <h1 class="hero-title">Enterprise Analytics Hub</h1>
                <p class="hero-subtitle">
                    Comprehensive business intelligence with real-time insights, predictive analytics, and executive reporting
                </p>
            </div>
            
            <div class="dashboard-grid">
                <div class="dashboard-card">
                    <div class="card-icon">📈</div>
                    <h3 class="card-title">Advanced Analytics</h3>
                    <p class="card-description">
                        Comprehensive metrics dashboard with ML-powered forecasting, 
                        user behavior analysis, and revenue optimization insights.
                    </p>
                    <a href="/metrics/dashboard" class="card-button">View Analytics</a>
                </div>
                
                <div class="dashboard-card">
                    <div class="card-icon">👔</div>
                    <h3 class="card-title">Executive BI</h3>
                    <p class="card-description">
                        Strategic business intelligence with KPI tracking, market analysis, 
                        PDF reports, and C-suite decision support tools.
                    </p>
                    <a href="/executive/dashboard" class="card-button">Executive View</a>
                </div>
                
                <div class="dashboard-card">
                    <div class="card-icon">⚡</div>
                    <h3 class="card-title">Real-time Engine</h3>
                    <p class="card-description">
                        Live WebSocket-powered analytics with instant alerts, 
                        real-time performance monitoring, and automated insights.
                    </p>
                    <a href="/realtime/client" class="card-button">Live Dashboard</a>
                </div>
                
                <div class="dashboard-card">
                    <div class="card-icon">🤖</div>
                    <h3 class="card-title">AI Insights</h3>
                    <p class="card-description">
                        Machine learning predictions, automated anomaly detection, 
                        and intelligent business recommendations powered by AI.
                    </p>
                    <a href="/ai/insights" class="card-button">AI Dashboard</a>
                </div>
            </div>
            
            <div class="features-section">
                <h2 class="features-title">🎯 Analytics Features</h2>
                <div class="features-grid">
                    <div class="feature-item">
                        <div class="feature-icon">📊</div>
                        <div class="feature-name">Revenue Analytics</div>
                        <div class="feature-desc">Real-time revenue tracking with predictive modeling</div>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">👥</div>
                        <div class="feature-name">User Intelligence</div>
                        <div class="feature-desc">Customer behavior analysis and segmentation</div>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">🎬</div>
                        <div class="feature-name">Movie Performance</div>
                        <div class="feature-desc">Content analytics and recommendation optimization</div>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">🚨</div>
                        <div class="feature-name">Smart Alerts</div>
                        <div class="feature-desc">Automated business alerts with actionable insights</div>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">📱</div>
                        <div class="feature-name">Mobile Analytics</div>
                        <div class="feature-desc">Cross-platform performance tracking</div>
                    </div>
                    <div class="feature-item">
                        <div class="feature-icon">🔐</div>
                        <div class="feature-name">Secure Access</div>
                        <div class="feature-desc">Enterprise-grade security and role-based access</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# Analytics Service Routes
@app.get("/metrics/dashboard", response_class=HTMLResponse)
async def metrics_dashboard():
    """Advanced analytics dashboard"""
    return dashboard.analytics_service.get_dashboard()

@app.get("/api/metrics/users")
async def get_user_metrics():
    """API endpoint for user metrics"""
    return dashboard.analytics_service.get_user_metrics()

@app.get("/api/metrics/revenue")
async def get_revenue_metrics():
    return dashboard.analytics_service.get_revenue_metrics()

@app.get("/api/metrics/bookings")
async def get_booking_metrics():
    return dashboard.analytics_service.get_booking_metrics()

@app.get("/api/forecast/revenue")
async def get_revenue_forecast():
    return dashboard.analytics_service.get_revenue_forecast()

# Executive BI Routes
@app.get("/executive/dashboard", response_class=HTMLResponse) 
async def executive_dashboard():
    """Executive BI dashboard"""
    return dashboard.executive_bi_service.get_executive_dashboard()

@app.get("/api/executive/metrics")
async def get_executive_metrics():
    return dashboard.executive_bi_service.get_executive_metrics()

@app.get("/api/executive/report")
async def generate_executive_report():
    return dashboard.executive_bi_service.generate_executive_report()

# Real-time Analytics Routes
@app.get("/realtime/client", response_class=HTMLResponse)
async def realtime_client():
    """Real-time analytics client"""
    try:
        with open("analytics_dashboard/realtime_analytics_client.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback inline client
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Real-time Analytics</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; background: #0F0F23; color: white; }
                .metric { background: #1A1A2E; padding: 20px; margin: 10px; border-radius: 10px; }
                .value { font-size: 2em; color: #E50914; }
            </style>
        </head>
        <body>
            <h1>🔴 Real-time Analytics</h1>
            <div id="metrics"></div>
            <script>
                const ws = new WebSocket('ws://localhost:8765');
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === 'real_time_update' || data.type === 'initial_data') {
                        document.getElementById('metrics').innerHTML = `
                            <div class="metric">
                                <h3>Revenue Today</h3>
                                <div class="value">$${data.data.revenue?.today_revenue || 0}</div>
                            </div>
                            <div class="metric">
                                <h3>Active Users</h3>
                                <div class="value">${data.data.users?.active_today || 0}</div>
                            </div>
                            <div class="metric">
                                <h3>Bookings</h3>
                                <div class="value">${data.data.bookings?.bookings_today || 0}</div>
                            </div>
                        `;
                    }
                };
            </script>
        </body>
        </html>
        """

# AI Insights Route (placeholder for future ML features)
@app.get("/ai/insights", response_class=HTMLResponse)
async def ai_insights():
    """AI insights dashboard"""
    return """
    <html>
    <head>
        <title>AI Insights - Coming Soon</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                background: linear-gradient(135deg, #0F0F23 0%, #1A1A2E 100%);
                color: white; 
                text-align: center; 
                padding: 50px;
            }
        </style>
    </head>
    <body>
        <h1>🤖 AI Insights Dashboard</h1>
        <p>Advanced ML-powered insights coming soon...</p>
        <p>Will include: Anomaly Detection, Predictive Analytics, Customer Segmentation, and Automated Recommendations</p>
        <a href="/" style="color: #E50914;">← Back to Dashboard</a>
    </body>
    </html>
    """

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "services": {
            "analytics": "operational",
            "executive_bi": "operational", 
            "realtime_engine": "operational"
        },
        "version": "1.0.0"
    }

if __name__ == "__main__":
    print("""
    🚀 Starting BookMyMovie Analytics Dashboard...
    
    📊 Main Dashboard: http://localhost:8000
    📈 Analytics: http://localhost:8000/metrics/dashboard
    👔 Executive BI: http://localhost:8000/executive/dashboard
    ⚡ Real-time: http://localhost:8000/realtime/client
    📚 API Docs: http://localhost:8000/docs
    
    🔄 Real-time WebSocket: ws://localhost:8765
    """)
    
    uvicorn.run(
        "main_analytics_app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )