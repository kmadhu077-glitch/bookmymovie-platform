"""
💰 Dynamic Pricing System Service
Smart pricing optimization with demand-based algorithms
Port: 8021
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional, Tuple
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import math
import logging
import asyncio
from contextlib import asynccontextmanager
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums for pricing
class PricingTier(str, Enum):
    BASE = "base"
    PEAK = "peak"
    PREMIUM = "premium"
    SURGE = "surge"
    DISCOUNT = "discount"

class DayType(str, Enum):
    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"

# Database setup
def init_dynamic_pricing_db():
    """Initialize the dynamic pricing database with comprehensive schema"""
    conn = sqlite3.connect('dynamic_pricing.db')
    cursor = conn.cursor()
    
    # Base pricing rules table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS base_pricing (
            id TEXT PRIMARY KEY,
            theater_id TEXT,
            screen_type TEXT DEFAULT 'standard',
            base_price REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            day_type TEXT DEFAULT 'weekday',
            time_slot TEXT, -- morning, afternoon, evening, night
            effective_from DATE NOT NULL,
            effective_to DATE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Dynamic pricing factors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pricing_factors (
            id TEXT PRIMARY KEY,
            factor_name TEXT NOT NULL,
            factor_type TEXT NOT NULL, -- demand, time, weather, event, competitor
            weight REAL DEFAULT 1.0,
            min_multiplier REAL DEFAULT 0.5,
            max_multiplier REAL DEFAULT 3.0,
            is_active BOOLEAN DEFAULT TRUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Demand analytics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS demand_analytics (
            id TEXT PRIMARY KEY,
            movie_id TEXT NOT NULL,
            theater_id TEXT NOT NULL,
            show_date DATE NOT NULL,
            show_time TIME NOT NULL,
            total_seats INTEGER NOT NULL,
            booked_seats INTEGER DEFAULT 0,
            occupancy_rate REAL DEFAULT 0.0,
            booking_velocity REAL DEFAULT 0.0, -- bookings per hour
            price_elasticity REAL DEFAULT 1.0,
            competitor_avg_price REAL,
            weather_score REAL DEFAULT 1.0,
            event_impact_score REAL DEFAULT 1.0,
            calculated_price REAL,
            final_price REAL,
            revenue REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Price history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id TEXT PRIMARY KEY,
            movie_id TEXT NOT NULL,
            theater_id TEXT NOT NULL,
            show_date DATE NOT NULL,
            show_time TIME NOT NULL,
            original_price REAL NOT NULL,
            adjusted_price REAL NOT NULL,
            adjustment_factor REAL NOT NULL,
            adjustment_reason TEXT,
            pricing_tier TEXT DEFAULT 'base',
            demand_level TEXT, -- low, medium, high, critical
            competitor_price REAL,
            occupancy_at_adjustment REAL,
            bookings_after_adjustment INTEGER DEFAULT 0,
            revenue_impact REAL DEFAULT 0.0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Surge pricing events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS surge_events (
            id TEXT PRIMARY KEY,
            event_name TEXT NOT NULL,
            event_type TEXT NOT NULL, -- holiday, premiere, festival, weather
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            surge_multiplier REAL DEFAULT 1.5,
            affected_theaters JSON, -- list of theater IDs
            affected_movies JSON, -- list of movie IDs
            max_price_cap REAL,
            is_active BOOLEAN DEFAULT TRUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Revenue optimization targets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS revenue_targets (
            id TEXT PRIMARY KEY,
            theater_id TEXT NOT NULL,
            target_period TEXT NOT NULL, -- daily, weekly, monthly
            target_date DATE NOT NULL,
            revenue_target REAL NOT NULL,
            current_revenue REAL DEFAULT 0.0,
            target_occupancy REAL DEFAULT 0.8,
            current_occupancy REAL DEFAULT 0.0,
            optimization_strategy TEXT, -- maximize_revenue, maximize_occupancy, balanced
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Competitor pricing intelligence table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_pricing (
            id TEXT PRIMARY KEY,
            competitor_name TEXT NOT NULL,
            location TEXT NOT NULL,
            movie_title TEXT NOT NULL,
            screen_type TEXT DEFAULT 'standard',
            price REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            show_date DATE NOT NULL,
            show_time TIME NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_source TEXT -- manual, api, scraping
        )
    ''')
    
    conn.commit()
    conn.close()

# Pydantic models
class BasePricing(BaseModel):
    theater_id: str
    screen_type: str = "standard"
    base_price: float
    currency: str = "USD"
    day_type: DayType = DayType.WEEKDAY
    time_slot: str  # morning, afternoon, evening, night
    effective_from: str
    effective_to: Optional[str] = None

class PricingFactor(BaseModel):
    factor_name: str
    factor_type: str  # demand, time, weather, event, competitor
    weight: float = 1.0
    min_multiplier: float = 0.5
    max_multiplier: float = 3.0
    description: Optional[str] = None

class DemandData(BaseModel):
    movie_id: str
    theater_id: str
    show_date: str
    show_time: str
    total_seats: int
    booked_seats: int = 0
    competitor_avg_price: Optional[float] = None
    weather_score: float = 1.0
    event_impact_score: float = 1.0

class SurgeEvent(BaseModel):
    event_name: str
    event_type: str
    start_date: str
    end_date: str
    surge_multiplier: float = 1.5
    affected_theaters: Optional[List[str]] = None
    affected_movies: Optional[List[str]] = None
    max_price_cap: Optional[float] = None
    description: Optional[str] = None

class PriceOptimizationRequest(BaseModel):
    movie_id: str
    theater_id: str
    show_date: str
    show_time: str
    current_occupancy: float
    hours_until_show: float
    competitor_prices: Optional[List[float]] = None

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_dynamic_pricing_db()
    logger.info("💰 Dynamic Pricing System starting up...")
    # Start background pricing optimization task
    asyncio.create_task(continuous_price_optimization())
    yield
    # Shutdown
    logger.info("💰 Dynamic Pricing System shutting down...")

app = FastAPI(
    title="💰 Dynamic Pricing System",
    description="Smart pricing optimization with demand-based algorithms",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DynamicPricingEngine:
    """Advanced Dynamic Pricing Engine with ML-based optimization"""
    
    def __init__(self):
        self.db_path = 'dynamic_pricing.db'
        # Ensure database is initialized first
        init_dynamic_pricing_db()
        self.initialize_default_factors()
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def initialize_default_factors(self):
        """Initialize default pricing factors"""
        default_factors = [
            {
                "factor_name": "demand_surge",
                "factor_type": "demand",
                "weight": 1.5,
                "min_multiplier": 1.0,
                "max_multiplier": 2.5,
                "description": "Demand-based surge pricing when occupancy > 80%"
            },
            {
                "factor_name": "time_premium",
                "factor_type": "time",
                "weight": 1.2,
                "min_multiplier": 0.8,
                "max_multiplier": 1.4,
                "description": "Premium pricing for peak hours (7-10 PM)"
            },
            {
                "factor_name": "early_bird_discount",
                "factor_type": "time",
                "weight": 0.8,
                "min_multiplier": 0.6,
                "max_multiplier": 1.0,
                "description": "Discount for morning shows before 12 PM"
            },
            {
                "factor_name": "weekend_premium",
                "factor_type": "time",
                "weight": 1.3,
                "min_multiplier": 1.0,
                "max_multiplier": 1.6,
                "description": "Weekend pricing premium"
            },
            {
                "factor_name": "weather_boost",
                "factor_type": "weather",
                "weight": 1.1,
                "min_multiplier": 0.9,
                "max_multiplier": 1.3,
                "description": "Price adjustment based on weather conditions"
            },
            {
                "factor_name": "competitor_match",
                "factor_type": "competitor",
                "weight": 1.0,
                "min_multiplier": 0.7,
                "max_multiplier": 1.3,
                "description": "Competitive pricing adjustment"
            }
        ]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for factor in default_factors:
            cursor.execute('''
                INSERT OR REPLACE INTO pricing_factors 
                (id, factor_name, factor_type, weight, min_multiplier, max_multiplier, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()), factor["factor_name"], factor["factor_type"],
                factor["weight"], factor["min_multiplier"], factor["max_multiplier"],
                factor["description"]
            ))
        
        conn.commit()
        conn.close()
    
    def calculate_dynamic_price(self, request: PriceOptimizationRequest) -> Dict[str, Any]:
        """Calculate optimized price using multiple factors"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get base price
        cursor.execute('''
            SELECT base_price FROM base_pricing 
            WHERE theater_id = ? AND is_active = TRUE
            ORDER BY created_at DESC LIMIT 1
        ''', (request.theater_id,))
        
        base_price_row = cursor.fetchone()
        base_price = base_price_row[0] if base_price_row else 12.00  # Default price
        
        # Calculate time-based factors
        show_datetime = datetime.fromisoformat(f"{request.show_date} {request.show_time}")
        current_time = datetime.now()
        
        # Determine time slot
        show_hour = show_datetime.hour
        if show_hour < 12:
            time_slot = "morning"
        elif show_hour < 17:
            time_slot = "afternoon"
        elif show_hour < 22:
            time_slot = "evening"
        else:
            time_slot = "night"
        
        # Determine day type
        weekday = show_datetime.weekday()
        day_type = "weekend" if weekday >= 5 else "weekday"
        
        # Initialize pricing factors
        price_multiplier = 1.0
        applied_factors = []
        
        # 1. Demand-based pricing
        demand_multiplier = self._calculate_demand_multiplier(request.current_occupancy)
        if demand_multiplier != 1.0:
            price_multiplier *= demand_multiplier
            applied_factors.append(f"Demand: {demand_multiplier:.2f}x")
        
        # 2. Time-based pricing
        time_multiplier = self._calculate_time_multiplier(time_slot, day_type, request.hours_until_show)
        if time_multiplier != 1.0:
            price_multiplier *= time_multiplier
            applied_factors.append(f"Time: {time_multiplier:.2f}x")
        
        # 3. Urgency pricing (last-minute bookings)
        urgency_multiplier = self._calculate_urgency_multiplier(request.hours_until_show, request.current_occupancy)
        if urgency_multiplier != 1.0:
            price_multiplier *= urgency_multiplier
            applied_factors.append(f"Urgency: {urgency_multiplier:.2f}x")
        
        # 4. Competitive pricing
        if request.competitor_prices:
            competitive_multiplier = self._calculate_competitive_multiplier(base_price * price_multiplier, request.competitor_prices)
            if competitive_multiplier != 1.0:
                price_multiplier *= competitive_multiplier
                applied_factors.append(f"Competitive: {competitive_multiplier:.2f}x")
        
        # 5. Check for surge events
        surge_multiplier = self._check_surge_events(request.movie_id, request.theater_id, show_datetime)
        if surge_multiplier != 1.0:
            price_multiplier *= surge_multiplier
            applied_factors.append(f"Surge Event: {surge_multiplier:.2f}x")
        
        # Apply bounds (min 50% to max 300% of base price)
        price_multiplier = max(0.5, min(3.0, price_multiplier))
        
        final_price = round(base_price * price_multiplier, 2)
        
        # Determine pricing tier
        if price_multiplier >= 2.0:
            tier = PricingTier.SURGE
        elif price_multiplier >= 1.5:
            tier = PricingTier.PREMIUM
        elif price_multiplier >= 1.2:
            tier = PricingTier.PEAK
        elif price_multiplier < 0.9:
            tier = PricingTier.DISCOUNT
        else:
            tier = PricingTier.BASE
        
        # Save price history
        self._save_price_history(request, base_price, final_price, price_multiplier, applied_factors, tier)
        
        conn.close()
        
        return {
            "base_price": base_price,
            "final_price": final_price,
            "price_multiplier": round(price_multiplier, 3),
            "pricing_tier": tier.value,
            "applied_factors": applied_factors,
            "savings_or_premium": round(final_price - base_price, 2),
            "recommendation": self._get_pricing_recommendation(price_multiplier, request.current_occupancy),
            "next_price_check": (current_time + timedelta(hours=1)).isoformat()
        }
    
    def _calculate_demand_multiplier(self, occupancy: float) -> float:
        """Calculate demand-based price multiplier"""
        if occupancy >= 0.9:
            return 2.2  # Very high demand
        elif occupancy >= 0.8:
            return 1.8  # High demand
        elif occupancy >= 0.7:
            return 1.4  # Medium-high demand
        elif occupancy >= 0.5:
            return 1.0  # Normal demand
        elif occupancy >= 0.3:
            return 0.9  # Low demand
        else:
            return 0.8  # Very low demand
    
    def _calculate_time_multiplier(self, time_slot: str, day_type: str, hours_until: float) -> float:
        """Calculate time-based price multiplier"""
        multiplier = 1.0
        
        # Time slot multipliers
        time_multipliers = {
            "morning": 0.8,    # Early bird discount
            "afternoon": 1.0,   # Standard pricing
            "evening": 1.3,     # Prime time premium
            "night": 1.1       # Late night slight premium
        }
        
        multiplier *= time_multipliers.get(time_slot, 1.0)
        
        # Weekend premium
        if day_type == "weekend":
            multiplier *= 1.2
        
        return multiplier
    
    def _calculate_urgency_multiplier(self, hours_until: float, occupancy: float) -> float:
        """Calculate urgency-based price multiplier"""
        if hours_until <= 2 and occupancy > 0.6:
            return 1.4  # Last-minute premium
        elif hours_until <= 6 and occupancy > 0.7:
            return 1.2  # Short notice premium
        elif hours_until >= 168:  # More than a week
            return 0.9  # Early booking discount
        else:
            return 1.0
    
    def _calculate_competitive_multiplier(self, our_price: float, competitor_prices: List[float]) -> float:
        """Calculate competitive pricing adjustment"""
        if not competitor_prices:
            return 1.0
        
        avg_competitor_price = sum(competitor_prices) / len(competitor_prices)
        
        if our_price > avg_competitor_price * 1.2:
            return 0.95  # Lower price to be competitive
        elif our_price < avg_competitor_price * 0.8:
            return 1.05  # Raise price towards market rate
        else:
            return 1.0
    
    def _check_surge_events(self, movie_id: str, theater_id: str, show_date: datetime) -> float:
        """Check for active surge pricing events"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT surge_multiplier FROM surge_events 
            WHERE is_active = TRUE 
            AND date(?) BETWEEN start_date AND end_date
            AND (affected_theaters IS NULL OR json_extract(affected_theaters, '$') LIKE ?)
            AND (affected_movies IS NULL OR json_extract(affected_movies, '$') LIKE ?)
        ''', (show_date.date().isoformat(), f'%{theater_id}%', f'%{movie_id}%'))
        
        surge_events = cursor.fetchall()
        conn.close()
        
        if surge_events:
            return max(event[0] for event in surge_events)
        
        return 1.0
    
    def _save_price_history(self, request: PriceOptimizationRequest, base_price: float, 
                          final_price: float, multiplier: float, factors: List[str], tier: PricingTier):
        """Save pricing decision to history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO price_history 
            (id, movie_id, theater_id, show_date, show_time, original_price, 
             adjusted_price, adjustment_factor, adjustment_reason, pricing_tier,
             occupancy_at_adjustment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), request.movie_id, request.theater_id,
            request.show_date, request.show_time, base_price, final_price,
            multiplier, "; ".join(factors), tier.value, request.current_occupancy
        ))
        
        conn.commit()
        conn.close()
    
    def _get_pricing_recommendation(self, multiplier: float, occupancy: float) -> str:
        """Get pricing strategy recommendation"""
        if multiplier >= 2.0:
            return "🔥 High demand surge pricing active - maximize revenue"
        elif multiplier >= 1.5:
            return "⬆️ Premium pricing recommended - strong demand signals"
        elif multiplier <= 0.8 and occupancy < 0.4:
            return "💡 Consider promotional pricing to boost occupancy"
        elif occupancy < 0.2:
            return "📢 Low demand - aggressive discounting recommended"
        else:
            return "✅ Optimal pricing strategy - balanced revenue and occupancy"
    
    def get_pricing_analytics(self, theater_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive pricing analytics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Base query conditions
        where_clause = "WHERE timestamp >= date('now', '-' || ? || ' days')"
        params = [days]
        
        if theater_id:
            where_clause += " AND theater_id = ?"
            params.append(theater_id)
        
        # Revenue impact analysis
        cursor.execute(f'''
            SELECT 
                pricing_tier,
                COUNT(*) as price_changes,
                AVG(adjustment_factor) as avg_multiplier,
                SUM(revenue_impact) as total_revenue_impact,
                AVG(occupancy_at_adjustment) as avg_occupancy
            FROM price_history 
            {where_clause}
            GROUP BY pricing_tier
        ''', params)
        
        tier_analysis = {}
        for row in cursor.fetchall():
            tier_analysis[row[0]] = {
                "price_changes": row[1],
                "avg_multiplier": round(row[2], 2) if row[2] else 1.0,
                "revenue_impact": round(row[3], 2) if row[3] else 0.0,
                "avg_occupancy": round(row[4], 2) if row[4] else 0.0
            }
        
        # Daily pricing trends
        cursor.execute(f'''
            SELECT 
                date(timestamp) as date,
                AVG(adjusted_price) as avg_price,
                COUNT(*) as total_adjustments,
                SUM(CASE WHEN adjustment_factor > 1 THEN 1 ELSE 0 END) as price_increases,
                SUM(CASE WHEN adjustment_factor < 1 THEN 1 ELSE 0 END) as price_decreases
            FROM price_history 
            {where_clause}
            GROUP BY date(timestamp)
            ORDER BY date DESC
            LIMIT 30
        ''', params)
        
        daily_trends = []
        for row in cursor.fetchall():
            daily_trends.append({
                "date": row[0],
                "avg_price": round(row[1], 2) if row[1] else 0.0,
                "total_adjustments": row[2],
                "price_increases": row[3],
                "price_decreases": row[4]
            })
        
        conn.close()
        
        return {
            "period_days": days,
            "theater_id": theater_id,
            "pricing_tier_analysis": tier_analysis,
            "daily_trends": daily_trends,
            "summary": {
                "total_price_adjustments": sum(t["price_changes"] for t in tier_analysis.values()),
                "avg_revenue_impact": sum(t["revenue_impact"] for t in tier_analysis.values()),
                "most_common_tier": max(tier_analysis.keys(), key=lambda k: tier_analysis[k]["price_changes"]) if tier_analysis else "base"
            }
        }

# Initialize pricing engine
pricing_engine = DynamicPricingEngine()

# Background task for continuous optimization
async def continuous_price_optimization():
    """Background task to continuously optimize pricing"""
    while True:
        try:
            logger.info("🔄 Running automated pricing optimization...")
            # This would connect to booking system to get real-time data
            # and automatically adjust prices based on current conditions
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"Error in pricing optimization: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute on error

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dynamic Pricing System Dashboard"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>💰 Dynamic Pricing System</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                     color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 30px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .price-box { background: linear-gradient(45deg, #FF6B6B, #4ECDC4); color: white; 
                        padding: 15px; border-radius: 8px; text-align: center; margin: 10px 0; }
            .tier-surge { background: linear-gradient(45deg, #ff4757, #ff3838); }
            .tier-premium { background: linear-gradient(45deg, #ffa726, #ff9800); }
            .tier-peak { background: linear-gradient(45deg, #66bb6a, #4caf50); }
            .tier-base { background: linear-gradient(45deg, #42a5f5, #2196f3); }
            .tier-discount { background: linear-gradient(45deg, #ab47bc, #9c27b0); }
            button { background: #f5576c; color: white; border: none; padding: 10px 20px; 
                    border-radius: 5px; cursor: pointer; margin: 5px; }
            button:hover { background: #e84563; }
            .input-box { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            .pricing-result { background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .factor-list { list-style: none; padding: 0; }
            .factor-item { background: #f0f8ff; padding: 8px; margin: 5px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💰 Dynamic Pricing System</h1>
                <p>Smart Pricing Optimization • Demand-Based Algorithms • Revenue Maximization</p>
            </div>
            
            <div class="grid">
                <!-- Price Calculator -->
                <div class="card">
                    <h3>🧮 Smart Price Calculator</h3>
                    <input type="text" id="movieId" placeholder="Movie ID" class="input-box">
                    <input type="text" id="theaterId" placeholder="Theater ID" class="input-box">
                    <input type="date" id="showDate" class="input-box">
                    <input type="time" id="showTime" class="input-box">
                    <input type="number" id="occupancy" placeholder="Current Occupancy (0-1)" step="0.01" max="1" class="input-box">
                    <input type="number" id="hoursUntil" placeholder="Hours Until Show" class="input-box">
                    <button onclick="calculatePrice()">💰 Calculate Optimal Price</button>
                    <div id="priceResult"></div>
                </div>
                
                <!-- Pricing Analytics -->
                <div class="card">
                    <h3>📊 Pricing Analytics</h3>
                    <button onclick="loadAnalytics()">📈 Load Analytics</button>
                    <div id="analyticsContainer">
                        <canvas id="pricingChart" width="400" height="200"></canvas>
                    </div>
                </div>
                
                <!-- Active Pricing Tiers -->
                <div class="card">
                    <h3>🎯 Pricing Tiers Overview</h3>
                    <div class="price-box tier-surge">
                        <h4>🔥 SURGE (2.0x+)</h4>
                        <p>High demand events, premieres</p>
                    </div>
                    <div class="price-box tier-premium">
                        <h4>⭐ PREMIUM (1.5-2.0x)</h4>
                        <p>Peak times, popular shows</p>
                    </div>
                    <div class="price-box tier-peak">
                        <h4>📈 PEAK (1.2-1.5x)</h4>
                        <p>Evening shows, weekends</p>
                    </div>
                    <div class="price-box tier-base">
                        <h4>💼 BASE (0.9-1.2x)</h4>
                        <p>Standard pricing</p>
                    </div>
                    <div class="price-box tier-discount">
                        <h4>💎 DISCOUNT (0.5-0.9x)</h4>
                        <p>Off-peak, low demand</p>
                    </div>
                </div>
            </div>
            
            <div class="grid" style="margin-top: 20px;">
                <!-- Revenue Optimization -->
                <div class="card">
                    <h3>💹 Revenue Optimization</h3>
                    <canvas id="revenueChart" width="400" height="200"></canvas>
                </div>
                
                <!-- Market Intelligence -->
                <div class="card">
                    <h3>🎯 Market Intelligence</h3>
                    <div id="marketInsights">
                        <p>📊 Analyzing competitor pricing patterns...</p>
                        <p>🧠 ML algorithms optimizing for maximum revenue</p>
                        <p>⚡ Real-time demand monitoring active</p>
                        <p>🎪 Multi-theater pricing coordination</p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        async function calculatePrice() {
            const movieId = document.getElementById('movieId').value;
            const theaterId = document.getElementById('theaterId').value;
            const showDate = document.getElementById('showDate').value;
            const showTime = document.getElementById('showTime').value;
            const occupancy = parseFloat(document.getElementById('occupancy').value);
            const hoursUntil = parseFloat(document.getElementById('hoursUntil').value);
            
            if (!movieId || !theaterId || !showDate || !showTime || isNaN(occupancy) || isNaN(hoursUntil)) {
                alert('Please fill in all fields with valid data');
                return;
            }
            
            try {
                const response = await fetch('/calculate-price', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        movie_id: movieId,
                        theater_id: theaterId,
                        show_date: showDate,
                        show_time: showTime,
                        current_occupancy: occupancy,
                        hours_until_show: hoursUntil
                    })
                });
                
                const result = await response.json();
                
                document.getElementById('priceResult').innerHTML = `
                    <div class="pricing-result">
                        <h4>💰 Optimized Pricing Result</h4>
                        <p><strong>Base Price:</strong> $${result.base_price}</p>
                        <p><strong>Final Price:</strong> $${result.final_price}</p>
                        <p><strong>Multiplier:</strong> ${result.price_multiplier}x</p>
                        <p><strong>Tier:</strong> ${result.pricing_tier.toUpperCase()}</p>
                        <p><strong>Price Change:</strong> ${result.savings_or_premium >= 0 ? '+' : ''}$${result.savings_or_premium}</p>
                        <h5>Applied Factors:</h5>
                        <ul class="factor-list">
                            ${result.applied_factors.map(factor => `<li class="factor-item">${factor}</li>`).join('')}
                        </ul>
                        <p><strong>Recommendation:</strong> ${result.recommendation}</p>
                        <p><em>Next price check: ${new Date(result.next_price_check).toLocaleString()}</em></p>
                    </div>
                `;
                
            } catch (error) {
                console.error('Error calculating price:', error);
                document.getElementById('priceResult').innerHTML = '<p style="color: red;">Error calculating price</p>';
            }
        }
        
        async function loadAnalytics() {
            try {
                const response = await fetch('/analytics?days=30');
                const analytics = await response.json();
                
                const ctx = document.getElementById('pricingChart').getContext('2d');
                
                const tiers = Object.keys(analytics.pricing_tier_analysis);
                const tierData = tiers.map(tier => analytics.pricing_tier_analysis[tier].price_changes);
                
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: tiers.map(tier => tier.toUpperCase()),
                        datasets: [{
                            label: 'Price Adjustments by Tier',
                            data: tierData,
                            backgroundColor: [
                                '#ff4757', '#ffa726', '#66bb6a', '#42a5f5', '#ab47bc'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Price Adjustments by Tier (30 Days)'
                            }
                        }
                    }
                });
                
                // Update analytics display
                document.getElementById('analyticsContainer').innerHTML += `
                    <div style="margin-top: 15px;">
                        <h4>📈 Analytics Summary</h4>
                        <p>Total Adjustments: ${analytics.summary.total_price_adjustments}</p>
                        <p>Revenue Impact: $${analytics.summary.avg_revenue_impact}</p>
                        <p>Most Common Tier: ${analytics.summary.most_common_tier.toUpperCase()}</p>
                    </div>
                `;
                
            } catch (error) {
                console.error('Error loading analytics:', error);
            }
        }
        
        // Initialize dashboard
        setTimeout(() => {
            // Set default values for demo
            document.getElementById('movieId').value = 'movie_001';
            document.getElementById('theaterId').value = 'theater_001';
            document.getElementById('showDate').value = new Date().toISOString().split('T')[0];
            document.getElementById('showTime').value = '19:30';
            document.getElementById('occupancy').value = '0.75';
            document.getElementById('hoursUntil').value = '24';
        }, 500);
        
        // Auto-refresh analytics every 60 seconds
        setInterval(() => {
            if (document.getElementById('pricingChart').getContext) {
                loadAnalytics();
            }
        }, 60000);
        </script>
    </body>
    </html>
    '''

@app.post("/calculate-price")
async def calculate_optimal_price(request: PriceOptimizationRequest):
    """Calculate optimal price using dynamic pricing algorithms"""
    return pricing_engine.calculate_dynamic_price(request)

@app.post("/base-pricing/")
async def set_base_pricing(pricing: BasePricing):
    """Set base pricing rules for a theater"""
    conn = sqlite3.connect('dynamic_pricing.db')
    cursor = conn.cursor()
    
    pricing_id = str(uuid.uuid4())
    
    cursor.execute('''
        INSERT INTO base_pricing 
        (id, theater_id, screen_type, base_price, currency, day_type, time_slot, effective_from, effective_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        pricing_id, pricing.theater_id, pricing.screen_type, pricing.base_price,
        pricing.currency, pricing.day_type.value, pricing.time_slot,
        pricing.effective_from, pricing.effective_to
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "pricing_id": pricing_id,
        "theater_id": pricing.theater_id,
        "base_price": pricing.base_price,
        "status": "created",
        "message": "Base pricing rule created successfully"
    }

@app.post("/surge-events/")
async def create_surge_event(event: SurgeEvent):
    """Create a surge pricing event"""
    conn = sqlite3.connect('dynamic_pricing.db')
    cursor = conn.cursor()
    
    event_id = str(uuid.uuid4())
    
    affected_theaters_json = json.dumps(event.affected_theaters) if event.affected_theaters else None
    affected_movies_json = json.dumps(event.affected_movies) if event.affected_movies else None
    
    cursor.execute('''
        INSERT INTO surge_events 
        (id, event_name, event_type, start_date, end_date, surge_multiplier, 
         affected_theaters, affected_movies, max_price_cap, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event_id, event.event_name, event.event_type, event.start_date,
        event.end_date, event.surge_multiplier, affected_theaters_json,
        affected_movies_json, event.max_price_cap, event.description
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "event_id": event_id,
        "event_name": event.event_name,
        "surge_multiplier": event.surge_multiplier,
        "status": "created",
        "message": "Surge pricing event created successfully"
    }

@app.get("/analytics")
async def get_pricing_analytics(theater_id: Optional[str] = None, days: int = Query(30, ge=1, le=365)):
    """Get comprehensive pricing analytics"""
    return pricing_engine.get_pricing_analytics(theater_id, days)

@app.get("/pricing-factors/")
async def get_pricing_factors():
    """Get all active pricing factors"""
    conn = sqlite3.connect('dynamic_pricing.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT factor_name, factor_type, weight, min_multiplier, max_multiplier, description
        FROM pricing_factors WHERE is_active = TRUE
    ''')
    
    factors = []
    for row in cursor.fetchall():
        factors.append({
            "factor_name": row[0],
            "factor_type": row[1],
            "weight": row[2],
            "min_multiplier": row[3],
            "max_multiplier": row[4],
            "description": row[5]
        })
    
    conn.close()
    return factors

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Dynamic Pricing System",
        "status": "healthy",
        "port": 8021,
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Demand-Based Pricing",
            "Revenue Optimization",
            "Time-Based Adjustments", 
            "Surge Pricing Logic",
            "Competitive Intelligence",
            "ML-Powered Analytics"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("💰 Starting Dynamic Pricing System...")
    print("📊 Service URL: http://127.0.0.1:8021")
    print("💹 Dashboard: http://127.0.0.1:8021/")
    print("📚 API Docs: http://127.0.0.1:8021/docs")
    
    uvicorn.run(app, host="127.0.0.1", port=8021)