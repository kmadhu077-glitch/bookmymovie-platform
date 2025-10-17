"""
Executive Business Intelligence Dashboard
Advanced reporting and analytics for business executives and stakeholders
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import sqlite3
from dataclasses import dataclass
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.piecharts import Pie
import io

@dataclass
class ExecutiveMetrics:
    """Executive-level metrics and KPIs"""
    period: str
    total_revenue: float
    revenue_growth: float
    user_acquisition: int
    user_retention: float
    market_share_growth: float
    profit_margin: float
    customer_lifetime_value: float
    operational_efficiency: float

@dataclass
class MarketAnalysis:
    """Market analysis and competitive intelligence"""
    market_size: float
    market_growth_rate: float
    competitive_position: str
    market_trends: List[str]
    opportunities: List[str]
    threats: List[str]

class ExecutiveBI:
    def __init__(self, analytics_db_path: str = "analytics_data.db"):
        self.analytics_db_path = analytics_db_path
        self.app = FastAPI(title="BookMyMovie Executive BI", version="1.0.0")
        self.setup_routes()
        self.setup_cors()
        
        # Create directories for reports and charts
        os.makedirs("static/executive_charts", exist_ok=True)
        os.makedirs("static/reports", exist_ok=True)
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
    
    def calculate_executive_metrics(self, period_days: int = 30) -> ExecutiveMetrics:
        """Calculate executive-level KPIs"""
        conn = sqlite3.connect(self.analytics_db_path)
        
        # Revenue metrics
        current_revenue_query = f"""
        SELECT SUM(revenue) as total_revenue
        FROM revenue_analytics 
        WHERE date >= date('now', '-{period_days} days')
        """
        
        previous_revenue_query = f"""
        SELECT SUM(revenue) as prev_revenue
        FROM revenue_analytics 
        WHERE date >= date('now', '-{period_days*2} days') 
        AND date < date('now', '-{period_days} days')
        """
        
        current_revenue = pd.read_sql(current_revenue_query, conn).iloc[0]['total_revenue'] or 0
        previous_revenue = pd.read_sql(previous_revenue_query, conn).iloc[0]['prev_revenue'] or 1
        
        revenue_growth = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0
        
        # User acquisition and retention
        user_acquisition_query = f"""
        SELECT COUNT(DISTINCT user_id) as new_users
        FROM user_analytics 
        WHERE user_id IN (
            SELECT user_id FROM user_analytics 
            GROUP BY user_id 
            HAVING MIN(timestamp) >= date('now', '-{period_days} days')
        )
        """
        
        retention_query = f"""
        SELECT 
            COUNT(DISTINCT CASE WHEN recent_activity THEN user_id END) * 100.0 / 
            COUNT(DISTINCT user_id) as retention_rate
        FROM (
            SELECT 
                user_id,
                MAX(timestamp) >= date('now', '-7 days') as recent_activity
            FROM user_analytics
            WHERE timestamp >= date('now', '-{period_days} days')
            GROUP BY user_id
        )
        """
        
        new_users = pd.read_sql(user_acquisition_query, conn).iloc[0]['new_users'] or 0
        retention_rate = pd.read_sql(retention_query, conn).iloc[0]['retention_rate'] or 0
        
        # Calculate derived metrics
        profit_margin = np.random.uniform(15, 25)  # Mock profit margin
        customer_lifetime_value = current_revenue / max(new_users, 1) * 12  # Annualized CLV
        operational_efficiency = np.random.uniform(75, 90)  # Mock operational efficiency
        market_share_growth = np.random.uniform(2, 8)  # Mock market share growth
        
        conn.close()
        return ExecutiveMetrics(
            period=f"Last {period_days} days",
            total_revenue=round(current_revenue, 2),
            revenue_growth=round(revenue_growth, 2),
            user_acquisition=new_users,
            user_retention=round(retention_rate, 2),
            market_share_growth=round(market_share_growth, 2),
            profit_margin=round(profit_margin, 2),
            customer_lifetime_value=round(customer_lifetime_value, 2),
            operational_efficiency=round(operational_efficiency, 2)
        )
    
    def generate_market_analysis(self) -> MarketAnalysis:
        """Generate market analysis and competitive intelligence"""
        # Mock market analysis data (in real scenario, this would come from market research APIs)
        return MarketAnalysis(
            market_size=12.5e9,  # $12.5B
            market_growth_rate=8.5,
            competitive_position="Strong #2 position",
            market_trends=[
                "Increasing demand for premium cinema experiences",
                "Growth in mobile-first booking platforms",
                "Rising adoption of AI-powered recommendations",
                "Shift towards subscription-based models",
                "Integration of social features in entertainment apps"
            ],
            opportunities=[
                "Expand into emerging markets",
                "Develop premium subscription tier",
                "Partner with streaming platforms",
                "Launch corporate booking solutions",
                "Implement dynamic pricing optimization"
            ],
            threats=[
                "Increased competition from tech giants",
                "Economic downturn affecting discretionary spending",
                "Changing consumer preferences post-pandemic",
                "Regulatory changes in data privacy",
                "Theater closures in key markets"
            ]
        )
    
    def create_executive_dashboard_chart(self) -> str:
        """Create comprehensive executive dashboard chart"""
        conn = sqlite3.connect(self.analytics_db_path)
        
        # Get revenue trend data
        revenue_query = """
        SELECT date, SUM(revenue) as daily_revenue
        FROM revenue_analytics
        WHERE date >= date('now', '-90 days')
        GROUP BY date
        ORDER BY date
        """
        revenue_df = pd.read_sql(revenue_query, conn)
        
        # Get user growth data
        user_query = """
        SELECT 
            date(timestamp) as date,
            COUNT(DISTINCT user_id) as daily_active_users
        FROM user_analytics
        WHERE timestamp >= date('now', '-90 days')
        GROUP BY date(timestamp)
        ORDER BY date
        """
        user_df = pd.read_sql(user_query, conn)
        
        # Get booking data
        booking_query = """
        SELECT 
            date(booking_date) as date,
            COUNT(*) as daily_bookings,
            SUM(amount) as daily_booking_revenue
        FROM booking_analytics
        WHERE booking_date >= date('now', '-90 days')
        GROUP BY date(booking_date)
        ORDER BY date
        """
        booking_df = pd.read_sql(booking_query, conn)
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Revenue Trend (90 Days)', 'Daily Active Users', 
                           'Booking Volume', 'Revenue vs Bookings Correlation'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Revenue trend
        fig.add_trace(
            go.Scatter(x=revenue_df['date'], y=revenue_df['daily_revenue'],
                      mode='lines+markers', name='Daily Revenue',
                      line=dict(color='#E50914', width=3)),
            row=1, col=1
        )
        
        # User growth
        fig.add_trace(
            go.Scatter(x=user_df['date'], y=user_df['daily_active_users'],
                      mode='lines+markers', name='Daily Active Users',
                      line=dict(color='#FFD700', width=3)),
            row=1, col=2
        )
        
        # Booking volume
        fig.add_trace(
            go.Bar(x=booking_df['date'], y=booking_df['daily_bookings'],
                   name='Daily Bookings', marker_color='#00CED1'),
            row=2, col=1
        )
        
        # Revenue vs Bookings correlation
        fig.add_trace(
            go.Scatter(x=booking_df['daily_bookings'], y=booking_df['daily_booking_revenue'],
                      mode='markers', name='Revenue vs Bookings',
                      marker=dict(color='#32CD32', size=8)),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=800,
            title_text="Executive Dashboard - Key Performance Indicators",
            title_font_size=20,
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(15,15,35,0.95)',
            font_color='white'
        )
        
        # Update axes
        fig.update_xaxes(gridcolor='#333333', gridwidth=1)
        fig.update_yaxes(gridcolor='#333333', gridwidth=1)
        
        chart_path = "static/executive_charts/executive_dashboard.html"
        fig.write_html(chart_path)
        conn.close()
        return chart_path
    
    def create_predictive_analytics_chart(self) -> str:
        """Create predictive analytics and forecasting chart"""
        conn = sqlite3.connect(self.analytics_db_path)
        
        # Get historical data for prediction
        query = """
        SELECT date, SUM(revenue) as daily_revenue
        FROM revenue_analytics
        GROUP BY date
        ORDER BY date
        """
        df = pd.read_sql(query, conn)
        df['date'] = pd.to_datetime(df['date'])
        df['day_number'] = (df['date'] - df['date'].min()).dt.days
        
        # Prepare ML model
        X = df[['day_number']].values
        y = df['daily_revenue'].values
        
        # Split data for training
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train multiple models
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        
        rf_model.fit(X_train, y_train)
        gb_model.fit(X_train, y_train)
        
        # Generate future predictions
        last_day = df['day_number'].max()
        future_days = np.array([[last_day + i] for i in range(1, 61)])  # 60 days ahead
        
        rf_predictions = rf_model.predict(future_days)
        gb_predictions = gb_model.predict(future_days)
        
        # Create future dates
        future_dates = [df['date'].max() + timedelta(days=i) for i in range(1, 61)]
        
        # Create the chart
        fig = go.Figure()
        
        # Historical data
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['daily_revenue'],
                      mode='lines+markers', name='Historical Revenue',
                      line=dict(color='#E50914', width=2),
                      marker=dict(size=4))
        )
        
        # Random Forest predictions
        fig.add_trace(
            go.Scatter(x=future_dates, y=rf_predictions,
                      mode='lines', name='RF Forecast',
                      line=dict(color='#FFD700', width=3, dash='dash'))
        )
        
        # Gradient Boosting predictions
        fig.add_trace(
            go.Scatter(x=future_dates, y=gb_predictions,
                      mode='lines', name='GB Forecast',
                      line=dict(color='#00CED1', width=3, dash='dot'))
        )
        
        # Add confidence interval for RF model
        rf_upper = rf_predictions * 1.1
        rf_lower = rf_predictions * 0.9
        
        fig.add_trace(
            go.Scatter(x=future_dates, y=rf_upper,
                      mode='lines', name='Upper Bound',
                      line=dict(color='rgba(255,215,0,0.3)', width=0),
                      showlegend=False)
        )
        
        fig.add_trace(
            go.Scatter(x=future_dates, y=rf_lower,
                      mode='lines', name='Lower Bound',
                      line=dict(color='rgba(255,215,0,0.3)', width=0),
                      fill='tonexty', fillcolor='rgba(255,215,0,0.2)',
                      showlegend=False)
        )
        
        # Update layout
        fig.update_layout(
            title="Revenue Forecasting - AI-Powered Predictions (60 Days)",
            xaxis_title="Date",
            yaxis_title="Revenue ($)",
            height=600,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(15,15,35,0.95)',
            font_color='white',
            title_font_size=18
        )
        
        fig.update_xaxes(gridcolor='#333333', gridwidth=1)
        fig.update_yaxes(gridcolor='#333333', gridwidth=1)
        
        chart_path = "static/executive_charts/predictive_analytics.html"
        fig.write_html(chart_path)
        conn.close()
        return chart_path
    
    def generate_executive_report_pdf(self) -> str:
        """Generate comprehensive executive report in PDF format"""
        # Get data for report
        metrics = self.calculate_executive_metrics(30)
        market_analysis = self.generate_market_analysis()
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#E50914'),
            alignment=1  # Center alignment
        )
        
        story.append(Paragraph("BookMyMovie Executive Report", title_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        summary_text = f"""
        <b>Reporting Period:</b> {metrics.period}<br/>
        <b>Total Revenue:</b> ${metrics.total_revenue:,.2f}<br/>
        <b>Revenue Growth:</b> {metrics.revenue_growth}%<br/>
        <b>New User Acquisition:</b> {metrics.user_acquisition:,}<br/>
        <b>User Retention Rate:</b> {metrics.user_retention}%<br/>
        <b>Market Share Growth:</b> {metrics.market_share_growth}%<br/>
        <b>Profit Margin:</b> {metrics.profit_margin}%<br/>
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Key Metrics Table
        story.append(Paragraph("Key Performance Indicators", styles['Heading2']))
        
        kpi_data = [
            ['Metric', 'Value', 'Status'],
            ['Total Revenue', f'${metrics.total_revenue:,.2f}', '📈 Growing'],
            ['Revenue Growth', f'{metrics.revenue_growth}%', '✅ Positive' if metrics.revenue_growth > 0 else '⚠️ Declining'],
            ['User Retention', f'{metrics.user_retention}%', '✅ Strong' if metrics.user_retention > 70 else '⚠️ Needs Attention'],
            ['Customer LTV', f'${metrics.customer_lifetime_value:,.2f}', '📊 Healthy'],
            ['Operational Efficiency', f'{metrics.operational_efficiency}%', '🎯 Optimized']
        ]
        
        kpi_table = Table(kpi_data)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E50914')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(kpi_table)
        story.append(PageBreak())
        
        # Market Analysis
        story.append(Paragraph("Market Analysis & Competitive Intelligence", styles['Heading2']))
        
        market_text = f"""
        <b>Market Size:</b> ${market_analysis.market_size/1e9:.1f}B<br/>
        <b>Market Growth Rate:</b> {market_analysis.market_growth_rate}%<br/>
        <b>Competitive Position:</b> {market_analysis.competitive_position}<br/><br/>
        
        <b>Key Market Trends:</b><br/>
        {' <br/>'.join([f"• {trend}" for trend in market_analysis.market_trends])}<br/><br/>
        
        <b>Strategic Opportunities:</b><br/>
        {' <br/>'.join([f"• {opp}" for opp in market_analysis.opportunities])}<br/><br/>
        
        <b>Potential Threats:</b><br/>
        {' <br/>'.join([f"• {threat}" for threat in market_analysis.threats])}
        """
        
        story.append(Paragraph(market_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Recommendations
        story.append(Paragraph("Strategic Recommendations", styles['Heading2']))
        recommendations_text = """
        <b>1. Revenue Optimization:</b> Implement dynamic pricing strategies during peak demand periods<br/>
        <b>2. User Engagement:</b> Enhance mobile app features to improve retention rates<br/>
        <b>3. Market Expansion:</b> Consider expansion into emerging markets with high growth potential<br/>
        <b>4. Technology Investment:</b> Increase AI/ML capabilities for better personalization<br/>
        <b>5. Partnership Strategy:</b> Explore strategic partnerships with streaming platforms<br/>
        """
        story.append(Paragraph(recommendations_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Save to file
        report_filename = f"executive_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        report_path = f"static/reports/{report_filename}"
        
        with open(report_path, 'wb') as f:
            f.write(buffer.read())
        
        return report_path
    
    def setup_routes(self):
        """Setup FastAPI routes for executive BI"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def executive_dashboard():
            """Executive BI Dashboard"""
            return """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>BookMyMovie Executive BI Dashboard</title>
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
                        padding: 30px;
                        background: rgba(229, 9, 20, 0.1);
                        border-radius: 20px;
                        border: 2px solid #E50914;
                        backdrop-filter: blur(10px);
                    }
                    .header h1 { 
                        color: #E50914; 
                        margin: 0; 
                        font-size: 3em;
                        text-shadow: 2px 2px 6px rgba(0,0,0,0.7);
                    }
                    .header p { 
                        color: #FFD700; 
                        margin: 15px 0 0 0; 
                        font-size: 1.4em;
                        font-weight: 500;
                    }
                    .executive-grid { 
                        display: grid; 
                        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
                        gap: 25px; 
                        margin-bottom: 40px; 
                    }
                    .executive-card { 
                        background: rgba(26, 26, 46, 0.9);
                        border: 2px solid #333;
                        border-radius: 20px;
                        padding: 30px;
                        text-align: center;
                        transition: all 0.4s ease;
                        backdrop-filter: blur(15px);
                        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    }
                    .executive-card:hover {
                        transform: translateY(-8px);
                        box-shadow: 0 15px 40px rgba(229, 9, 20, 0.4);
                        border-color: #E50914;
                    }
                    .executive-value { 
                        font-size: 3em; 
                        font-weight: bold; 
                        color: #E50914;
                        margin: 15px 0;
                        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                    }
                    .executive-label { 
                        font-size: 1.2em; 
                        color: #FFD700;
                        text-transform: uppercase;
                        letter-spacing: 2px;
                        font-weight: 600;
                    }
                    .executive-change { 
                        font-size: 1em; 
                        margin-top: 15px; 
                        padding: 8px 16px;
                        border-radius: 25px;
                        background: rgba(255, 215, 0, 0.15);
                        border: 1px solid #FFD700;
                        font-weight: 500;
                    }
                    .charts-section { 
                        margin-top: 50px; 
                    }
                    .chart-container { 
                        background: rgba(26, 26, 46, 0.9);
                        border: 2px solid #333;
                        border-radius: 20px;
                        padding: 30px;
                        margin-bottom: 40px;
                        backdrop-filter: blur(15px);
                        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    }
                    .chart-container h3 { 
                        color: #FFD700; 
                        margin-top: 0;
                        font-size: 1.8em;
                        border-bottom: 3px solid #E50914;
                        padding-bottom: 15px;
                        font-weight: 600;
                    }
                    .action-buttons { 
                        text-align: center; 
                        margin: 40px 0; 
                    }
                    .action-btn {
                        background: linear-gradient(45deg, #E50914, #B20710);
                        color: white;
                        border: none;
                        padding: 15px 30px;
                        border-radius: 30px;
                        cursor: pointer;
                        font-size: 1.1em;
                        margin: 10px;
                        transition: all 0.3s ease;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        font-weight: 600;
                        text-decoration: none;
                        display: inline-block;
                    }
                    .action-btn:hover {
                        background: linear-gradient(45deg, #B20710, #E50914);
                        transform: scale(1.05);
                        box-shadow: 0 8px 20px rgba(229, 9, 20, 0.5);
                    }
                    .loading { 
                        text-align: center; 
                        color: #FFD700; 
                        font-style: italic;
                        font-size: 1.2em;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📊 Executive Business Intelligence</h1>
                    <p>Strategic Analytics & Performance Dashboard</p>
                </div>

                <div id="metrics-container">
                    <div class="loading">Loading executive metrics...</div>
                </div>

                <div class="action-buttons">
                    <a href="/generate-report" class="action-btn" target="_blank">📑 Generate PDF Report</a>
                    <button class="action-btn" onclick="refreshData()">🔄 Refresh Data</button>
                    <a href="/market-analysis" class="action-btn">📈 Market Analysis</a>
                </div>

                <div class="charts-section">
                    <div class="chart-container">
                        <h3>📊 Executive Dashboard - KPIs</h3>
                        <iframe src="/static/executive_charts/executive_dashboard.html" width="100%" height="800" frameborder="0"></iframe>
                    </div>
                    
                    <div class="chart-container">
                        <h3>🔮 Predictive Analytics & Forecasting</h3>
                        <iframe src="/static/executive_charts/predictive_analytics.html" width="100%" height="600" frameborder="0"></iframe>
                    </div>
                </div>

                <script>
                    async function loadExecutiveMetrics() {
                        try {
                            const metrics = await fetch('/executive-metrics').then(r => r.json());

                            document.getElementById('metrics-container').innerHTML = `
                                <div class="executive-grid">
                                    <div class="executive-card">
                                        <div class="executive-value">$${(metrics.total_revenue/1000000).toFixed(1)}M</div>
                                        <div class="executive-label">Total Revenue</div>
                                        <div class="executive-change">${metrics.revenue_growth > 0 ? '+' : ''}${metrics.revenue_growth}% Growth</div>
                                    </div>
                                    <div class="executive-card">
                                        <div class="executive-value">${metrics.user_retention}%</div>
                                        <div class="executive-label">User Retention</div>
                                        <div class="executive-change">${metrics.user_acquisition.toLocaleString()} New Users</div>
                                    </div>
                                    <div class="executive-card">
                                        <div class="executive-value">${metrics.market_share_growth}%</div>
                                        <div class="executive-label">Market Share Growth</div>
                                        <div class="executive-change">Strong Position</div>
                                    </div>
                                    <div class="executive-card">
                                        <div class="executive-value">${metrics.profit_margin}%</div>
                                        <div class="executive-label">Profit Margin</div>
                                        <div class="executive-change">Healthy Margins</div>
                                    </div>
                                    <div class="executive-card">
                                        <div class="executive-value">$${(metrics.customer_lifetime_value/1000).toFixed(1)}K</div>
                                        <div class="executive-label">Customer LTV</div>
                                        <div class="executive-change">Strong Value</div>
                                    </div>
                                    <div class="executive-card">
                                        <div class="executive-value">${metrics.operational_efficiency}%</div>
                                        <div class="executive-label">Operational Efficiency</div>
                                        <div class="executive-change">Optimized Operations</div>
                                    </div>
                                </div>
                            `;
                        } catch (error) {
                            document.getElementById('metrics-container').innerHTML = 
                                '<div class="loading" style="color: #E50914;">Error loading metrics. Please try again.</div>';
                        }
                    }

                    function refreshData() {
                        document.getElementById('metrics-container').innerHTML = 
                            '<div class="loading">Refreshing executive metrics...</div>';
                        loadExecutiveMetrics();
                        
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    }

                    loadExecutiveMetrics();
                </script>
            </body>
            </html>
            """
        
        @self.app.get("/executive-metrics")
        async def get_executive_metrics():
            """Get executive-level metrics"""
            metrics = self.calculate_executive_metrics()
            return metrics.__dict__
        
        @self.app.get("/market-analysis")
        async def get_market_analysis():
            """Get market analysis data"""
            analysis = self.generate_market_analysis()
            return analysis.__dict__
        
        @self.app.get("/generate-report")
        async def generate_report():
            """Generate and download executive PDF report"""
            try:
                report_path = self.generate_executive_report_pdf()
                return FileResponse(
                    report_path, 
                    filename=f"executive_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    media_type='application/pdf'
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
        
        @self.app.get("/generate-charts")
        async def generate_charts():
            """Generate executive charts"""
            dashboard_chart = self.create_executive_dashboard_chart()
            predictive_chart = self.create_predictive_analytics_chart()
            return {
                "dashboard_chart": dashboard_chart,
                "predictive_chart": predictive_chart,
                "status": "Charts generated successfully"
            }
    
    def run(self, host: str = "0.0.0.0", port: int = 8025):
        """Run the executive BI service"""
        print(f"""
        🚀 Starting BookMyMovie Executive BI Service...
        
        📊 Executive Dashboard: http://localhost:{port}
        🔍 API Documentation: http://localhost:{port}/docs
        
        💼 Executive Features:
        • Strategic KPI monitoring
        • Predictive revenue analytics
        • Market competitive analysis
        • Executive PDF reporting
        • Real-time business insights
        """)
        
        # Generate initial charts
        self.create_executive_dashboard_chart()
        self.create_predictive_analytics_chart()
        
        uvicorn.run(self.app, host=host, port=port)

if __name__ == "__main__":
    # Initialize and run the executive BI service
    executive_bi = ExecutiveBI()
    executive_bi.run()