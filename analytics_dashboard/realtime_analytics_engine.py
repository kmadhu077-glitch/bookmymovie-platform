"""
Real-time Business Intelligence Engine
Advanced analytics with real-time streaming, predictive modeling, and automated insights
"""

import asyncio
import websockets
import json
from datetime import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Any
import sqlite3
from dataclasses import dataclass, asdict
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RealTimeMetric:
    """Real-time metric data structure"""
    timestamp: str
    metric_name: str
    value: float
    trend: str  # 'up', 'down', 'stable'
    alert_level: str  # 'normal', 'warning', 'critical'

@dataclass
class BusinessAlert:
    """Business alert data structure"""
    alert_id: str
    timestamp: str
    severity: str  # 'info', 'warning', 'critical'
    category: str  # 'revenue', 'users', 'performance'
    title: str
    description: str
    recommended_action: str

class RealTimeAnalyticsEngine:
    def __init__(self, analytics_db_path: str = "analytics_data.db"):
        self.analytics_db_path = analytics_db_path
        self.connected_clients = set()
        self.is_running = False
        self.metrics_cache = {}
        
    async def register_client(self, websocket):
        """Register new WebSocket client"""
        self.connected_clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.connected_clients)}")
        
        # Send initial data to new client
        await self.send_initial_data(websocket)
    
    async def unregister_client(self, websocket):
        """Unregister WebSocket client"""
        self.connected_clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.connected_clients)}")
    
    async def send_initial_data(self, websocket):
        """Send initial dashboard data to client"""
        try:
            initial_data = {
                "type": "initial_data",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "revenue": await self.get_current_revenue_metrics(),
                    "users": await self.get_current_user_metrics(),
                    "bookings": await self.get_current_booking_metrics(),
                    "alerts": await self.get_current_alerts()
                }
            }
            await websocket.send(json.dumps(initial_data))
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast update to all connected clients"""
        if not self.connected_clients:
            return
        
        message = json.dumps({
            "type": "real_time_update",
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        
        # Send to all connected clients
        disconnected = set()
        for client in self.connected_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        for client in disconnected:
            await self.unregister_client(client)
    
    async def get_current_revenue_metrics(self) -> Dict[str, Any]:
        """Get current revenue metrics"""
        conn = sqlite3.connect(self.analytics_db_path)
        
        # Today's revenue
        today_revenue_query = """
        SELECT COALESCE(SUM(revenue), 0) as today_revenue
        FROM revenue_analytics 
        WHERE date = date('now')
        """
        
        # Yesterday's revenue for comparison
        yesterday_revenue_query = """
        SELECT COALESCE(SUM(revenue), 0) as yesterday_revenue
        FROM revenue_analytics 
        WHERE date = date('now', '-1 day')
        """
        
        # This month's revenue
        month_revenue_query = """
        SELECT COALESCE(SUM(revenue), 0) as month_revenue
        FROM revenue_analytics 
        WHERE date >= date('now', 'start of month')
        """
        
        today_revenue = pd.read_sql(today_revenue_query, conn).iloc[0]['today_revenue']
        yesterday_revenue = pd.read_sql(yesterday_revenue_query, conn).iloc[0]['yesterday_revenue']
        month_revenue = pd.read_sql(month_revenue_query, conn).iloc[0]['month_revenue']
        
        # Calculate growth
        daily_growth = ((today_revenue - yesterday_revenue) / yesterday_revenue * 100) if yesterday_revenue > 0 else 0
        
        conn.close()
        return {
            "today_revenue": round(today_revenue, 2),
            "yesterday_revenue": round(yesterday_revenue, 2),
            "month_revenue": round(month_revenue, 2),
            "daily_growth": round(daily_growth, 2),
            "trend": "up" if daily_growth > 0 else "down" if daily_growth < 0 else "stable"
        }
    
    async def get_current_user_metrics(self) -> Dict[str, Any]:
        """Get current user metrics"""
        conn = sqlite3.connect(self.analytics_db_path)
        
        # Active users today
        active_today_query = """
        SELECT COUNT(DISTINCT user_id) as active_today
        FROM user_analytics 
        WHERE date(timestamp) = date('now')
        """
        
        # Active users yesterday
        active_yesterday_query = """
        SELECT COUNT(DISTINCT user_id) as active_yesterday
        FROM user_analytics 
        WHERE date(timestamp) = date('now', '-1 day')
        """
        
        # New users today
        new_today_query = """
        SELECT COUNT(DISTINCT user_id) as new_today
        FROM user_analytics 
        WHERE user_id IN (
            SELECT user_id FROM user_analytics 
            GROUP BY user_id 
            HAVING date(MIN(timestamp)) = date('now')
        )
        """
        
        active_today = pd.read_sql(active_today_query, conn).iloc[0]['active_today']
        active_yesterday = pd.read_sql(active_yesterday_query, conn).iloc[0]['active_yesterday']
        new_today = pd.read_sql(new_today_query, conn).iloc[0]['new_today']
        
        # Calculate growth
        user_growth = ((active_today - active_yesterday) / active_yesterday * 100) if active_yesterday > 0 else 0
        
        conn.close()
        return {
            "active_today": active_today,
            "active_yesterday": active_yesterday,
            "new_today": new_today,
            "user_growth": round(user_growth, 2),
            "trend": "up" if user_growth > 0 else "down" if user_growth < 0 else "stable"
        }
    
    async def get_current_booking_metrics(self) -> Dict[str, Any]:
        """Get current booking metrics"""
        conn = sqlite3.connect(self.analytics_db_path)
        
        # Bookings today
        bookings_today_query = """
        SELECT COUNT(*) as bookings_today, COALESCE(SUM(amount), 0) as revenue_today
        FROM booking_analytics 
        WHERE date(booking_date) = date('now') AND status = 'completed'
        """
        
        # Bookings yesterday
        bookings_yesterday_query = """
        SELECT COUNT(*) as bookings_yesterday
        FROM booking_analytics 
        WHERE date(booking_date) = date('now', '-1 day') AND status = 'completed'
        """
        
        # Conversion rate today
        conversion_query = """
        SELECT 
            COUNT(*) as total_bookings,
            (SELECT COUNT(*) FROM user_analytics WHERE date(timestamp) = date('now') AND action_type = 'view_movie') as total_views
        FROM booking_analytics 
        WHERE date(booking_date) = date('now') AND status = 'completed'
        """
        
        bookings_data = pd.read_sql(bookings_today_query, conn).iloc[0]
        bookings_yesterday = pd.read_sql(bookings_yesterday_query, conn).iloc[0]['bookings_yesterday']
        conversion_data = pd.read_sql(conversion_query, conn).iloc[0]
        
        bookings_today = bookings_data['bookings_today']
        booking_growth = ((bookings_today - bookings_yesterday) / bookings_yesterday * 100) if bookings_yesterday > 0 else 0
        conversion_rate = (conversion_data['total_bookings'] / conversion_data['total_views'] * 100) if conversion_data['total_views'] > 0 else 0
        
        conn.close()
        return {
            "bookings_today": bookings_today,
            "bookings_yesterday": bookings_yesterday,
            "booking_growth": round(booking_growth, 2),
            "conversion_rate": round(conversion_rate, 2),
            "revenue_today": round(bookings_data['revenue_today'], 2),
            "trend": "up" if booking_growth > 0 else "down" if booking_growth < 0 else "stable"
        }
    
    async def get_current_alerts(self) -> List[BusinessAlert]:
        """Generate current business alerts"""
        alerts = []
        
        # Get current metrics for alert generation
        revenue_metrics = await self.get_current_revenue_metrics()
        user_metrics = await self.get_current_user_metrics()
        booking_metrics = await self.get_current_booking_metrics()
        
        # Revenue alerts
        if revenue_metrics['daily_growth'] < -10:
            alerts.append(BusinessAlert(
                alert_id="REV001",
                timestamp=datetime.now().isoformat(),
                severity="warning",
                category="revenue",
                title="Revenue Decline Alert",
                description=f"Daily revenue declined by {abs(revenue_metrics['daily_growth']):.1f}%",
                recommended_action="Review pricing strategy and promotional campaigns"
            ))
        
        # User growth alerts
        if user_metrics['user_growth'] < -5:
            alerts.append(BusinessAlert(
                alert_id="USR001",
                timestamp=datetime.now().isoformat(),
                severity="warning",
                category="users",
                title="User Engagement Drop",
                description=f"Daily active users decreased by {abs(user_metrics['user_growth']):.1f}%",
                recommended_action="Implement user re-engagement campaigns"
            ))
        
        # Conversion rate alerts
        if booking_metrics['conversion_rate'] < 2.0:
            alerts.append(BusinessAlert(
                alert_id="CNV001",
                timestamp=datetime.now().isoformat(),
                severity="critical",
                category="conversion",
                title="Low Conversion Rate",
                description=f"Conversion rate dropped to {booking_metrics['conversion_rate']:.1f}%",
                recommended_action="Optimize booking flow and user experience"
            ))
        
        # High performance alerts (positive)
        if revenue_metrics['daily_growth'] > 15:
            alerts.append(BusinessAlert(
                alert_id="REV002",
                timestamp=datetime.now().isoformat(),
                severity="info",
                category="revenue",
                title="Exceptional Revenue Growth",
                description=f"Daily revenue increased by {revenue_metrics['daily_growth']:.1f}%",
                recommended_action="Analyze success factors for replication"
            ))
        
        return alerts
    
    async def generate_real_time_insights(self) -> Dict[str, Any]:
        """Generate real-time business insights"""
        revenue_metrics = await self.get_current_revenue_metrics()
        user_metrics = await self.get_current_user_metrics()
        booking_metrics = await self.get_current_booking_metrics()
        
        # AI-powered insights (simplified simulation)
        insights = []
        
        # Revenue insights
        if revenue_metrics['trend'] == 'up' and booking_metrics['trend'] == 'up':
            insights.append({
                "type": "positive",
                "title": "Revenue & Booking Momentum",
                "description": "Both revenue and bookings are trending upward",
                "confidence": 0.85
            })
        
        # User behavior insights
        if user_metrics['new_today'] > user_metrics['active_today'] * 0.1:
            insights.append({
                "type": "opportunity",
                "title": "High New User Acquisition",
                "description": "Strong new user growth detected",
                "confidence": 0.78
            })
        
        # Conversion optimization insights
        avg_ticket_value = booking_metrics['revenue_today'] / max(booking_metrics['bookings_today'], 1)
        if avg_ticket_value > 15:
            insights.append({
                "type": "positive",
                "title": "Premium Booking Trend",
                "description": "Users are booking higher-value tickets",
                "confidence": 0.82
            })
        
        return {
            "insights": insights,
            "performance_score": np.random.randint(75, 95),  # Mock overall score
            "recommendation": "Focus on maintaining current growth momentum",
            "next_review": (datetime.now().replace(hour=datetime.now().hour + 1, minute=0, second=0)).isoformat()
        }
    
    async def analytics_loop(self):
        """Main analytics loop that continuously generates updates"""
        while self.is_running:
            try:
                # Generate current metrics
                revenue_metrics = await self.get_current_revenue_metrics()
                user_metrics = await self.get_current_user_metrics()
                booking_metrics = await self.get_current_booking_metrics()
                alerts = await self.get_current_alerts()
                insights = await self.generate_real_time_insights()
                
                # Create update package
                update_data = {
                    "revenue": revenue_metrics,
                    "users": user_metrics,
                    "bookings": booking_metrics,
                    "alerts": [asdict(alert) for alert in alerts],
                    "insights": insights,
                    "system_status": "operational"
                }
                
                # Broadcast to all clients
                await self.broadcast_update(update_data)
                
                # Wait before next update (every 30 seconds)
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                # Handle client messages if needed
                data = json.loads(message)
                if data.get('type') == 'ping':
                    await websocket.send(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
                elif data.get('type') == 'request_update':
                    await self.send_initial_data(websocket)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start the WebSocket server"""
        self.is_running = True
        
        # Start the analytics loop
        analytics_task = asyncio.create_task(self.analytics_loop())
        
        # Start WebSocket server
        logger.info(f"Starting Real-time Analytics WebSocket server on ws://{host}:{port}")
        
        async with websockets.serve(self.websocket_handler, host, port):
            logger.info("Real-time Analytics Engine is running...")
            await asyncio.Future()  # Run forever
    
    def stop(self):
        """Stop the analytics engine"""
        self.is_running = False
        logger.info("Real-time Analytics Engine stopped")

# Create HTML client for testing
WEBSOCKET_CLIENT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BookMyMovie Real-time Analytics</title>
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
        .metrics-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .metric-card { 
            background: rgba(26, 26, 46, 0.8);
            border: 1px solid #333;
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
        }
        .metric-value { 
            font-size: 2em; 
            font-weight: bold; 
            color: #E50914;
            margin: 10px 0;
        }
        .metric-label { 
            color: #FFD700;
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-connected { background-color: #4CAF50; }
        .status-disconnected { background-color: #F44336; }
        .alerts-section {
            background: rgba(26, 26, 46, 0.8);
            border: 1px solid #333;
            border-radius: 15px;
            padding: 25px;
            margin-top: 30px;
        }
        .alert {
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid;
        }
        .alert-warning { border-left-color: #FF9800; background: rgba(255, 152, 0, 0.1); }
        .alert-critical { border-left-color: #F44336; background: rgba(244, 67, 54, 0.1); }
        .alert-info { border-left-color: #2196F3; background: rgba(33, 150, 243, 0.1); }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Real-time Business Analytics</h1>
        <p>Live Dashboard with WebSocket Updates</p>
        <div>
            <span id="connection-status" class="status-indicator status-disconnected"></span>
            <span id="status-text">Connecting...</span>
        </div>
    </div>

    <div id="metrics-container" class="metrics-grid">
        <!-- Metrics will be populated here -->
    </div>

    <div id="alerts-container" class="alerts-section">
        <h3>🚨 Business Alerts</h3>
        <div id="alerts-list">
            <p>Loading alerts...</p>
        </div>
    </div>

    <script>
        let websocket;
        let reconnectInterval = 5000;
        
        function connect() {
            websocket = new WebSocket('ws://localhost:8765');
            
            websocket.onopen = function(event) {
                console.log('Connected to analytics server');
                document.getElementById('connection-status').className = 'status-indicator status-connected';
                document.getElementById('status-text').textContent = 'Connected - Live Updates';
                
                // Send ping to keep connection alive
                setInterval(() => {
                    if (websocket.readyState === WebSocket.OPEN) {
                        websocket.send(JSON.stringify({type: 'ping'}));
                    }
                }, 30000);
            };
            
            websocket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                console.log('Received data:', data);
                
                if (data.type === 'initial_data' || data.type === 'real_time_update') {
                    updateDashboard(data.data);
                }
            };
            
            websocket.onclose = function(event) {
                console.log('Disconnected from analytics server');
                document.getElementById('connection-status').className = 'status-indicator status-disconnected';
                document.getElementById('status-text').textContent = 'Disconnected - Attempting Reconnection';
                
                setTimeout(connect, reconnectInterval);
            };
            
            websocket.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function updateDashboard(data) {
            // Update metrics
            if (data.revenue && data.users && data.bookings) {
                document.getElementById('metrics-container').innerHTML = `
                    <div class="metric-card">
                        <div class="metric-label">Today's Revenue</div>
                        <div class="metric-value">$${data.revenue.today_revenue.toLocaleString()}</div>
                        <div>Growth: ${data.revenue.daily_growth > 0 ? '+' : ''}${data.revenue.daily_growth}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Active Users Today</div>
                        <div class="metric-value">${data.users.active_today.toLocaleString()}</div>
                        <div>New Users: ${data.users.new_today}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Bookings Today</div>
                        <div class="metric-value">${data.bookings.bookings_today.toLocaleString()}</div>
                        <div>Conversion: ${data.bookings.conversion_rate}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Performance Score</div>
                        <div class="metric-value">${data.insights ? data.insights.performance_score : 'N/A'}%</div>
                        <div>System Status: ${data.system_status || 'Operational'}</div>
                    </div>
                `;
            }
            
            // Update alerts
            if (data.alerts) {
                const alertsHtml = data.alerts.length > 0 ? 
                    data.alerts.map(alert => `
                        <div class="alert alert-${alert.severity}">
                            <strong>${alert.title}</strong><br>
                            ${alert.description}<br>
                            <em>Action: ${alert.recommended_action}</em>
                        </div>
                    `).join('') : 
                    '<p>No active alerts - All systems operating normally</p>';
                    
                document.getElementById('alerts-list').innerHTML = alertsHtml;
            }
        }
        
        // Start connection
        connect();
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    # Save WebSocket client HTML
    with open("realtime_analytics_client.html", "w") as f:
        f.write(WEBSOCKET_CLIENT_HTML)
    
    # Start the real-time analytics engine
    engine = RealTimeAnalyticsEngine()
    
    print("""
    🚀 Starting BookMyMovie Real-time Analytics Engine...
    
    📊 WebSocket Server: ws://localhost:8765
    🌐 Test Client: realtime_analytics_client.html
    
    🔄 Real-time Features:
    • Live revenue tracking
    • User engagement monitoring  
    • Booking conversion analytics
    • Automated business alerts
    • Predictive insights
    """)
    
    try:
        asyncio.run(engine.start_server())
    except KeyboardInterrupt:
        print("\n🛑 Real-time Analytics Engine stopped")
        engine.stop()