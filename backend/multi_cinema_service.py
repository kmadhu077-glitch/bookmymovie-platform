"""
🏢 Multi-Cinema Chain Support Service
Enterprise theater management system with location-based services
Port: 8020
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Path, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import math
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
def init_multi_cinema_db():
    """Initialize the multi-cinema database with comprehensive schema"""
    conn = sqlite3.connect('multi_cinema.db')
    cursor = conn.cursor()
    
    # Cinema Chains table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cinema_chains (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            headquarters_location TEXT,
            total_theaters INTEGER DEFAULT 0,
            total_screens INTEGER DEFAULT 0,
            founded_year INTEGER,
            website TEXT,
            logo_url TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            chain_type TEXT DEFAULT 'multiplex', -- multiplex, drive-in, imax, boutique
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Theaters table (enhanced for chain support)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS theaters (
            id TEXT PRIMARY KEY,
            chain_id TEXT NOT NULL,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            country TEXT NOT NULL,
            postal_code TEXT,
            latitude REAL,
            longitude REAL,
            phone TEXT,
            email TEXT,
            manager_name TEXT,
            total_screens INTEGER DEFAULT 0,
            total_capacity INTEGER DEFAULT 0,
            parking_spaces INTEGER DEFAULT 0,
            facilities JSON, -- parking, food_court, 3d_screens, imax, vip_seats
            operating_hours JSON, -- daily operating hours
            is_active BOOLEAN DEFAULT TRUE,
            opening_date DATE,
            renovation_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chain_id) REFERENCES cinema_chains (id)
        )
    ''')
    
    # Screens table (enhanced)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS screens (
            id TEXT PRIMARY KEY,
            theater_id TEXT NOT NULL,
            screen_number INTEGER NOT NULL,
            name TEXT, -- Screen 1, IMAX Screen, VIP Theater
            screen_type TEXT DEFAULT 'standard', -- standard, imax, 3d, 4dx, vip
            total_seats INTEGER NOT NULL,
            rows INTEGER NOT NULL,
            seats_per_row INTEGER NOT NULL,
            screen_size TEXT, -- dimensions or size category
            sound_system TEXT, -- Dolby Atmos, DTS, etc.
            projection_type TEXT, -- Digital, IMAX, Laser
            accessibility_features JSON, -- wheelchair, hearing_loop, etc.
            premium_features JSON, -- reclining_seats, food_service, etc.
            maintenance_schedule JSON,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (theater_id) REFERENCES theaters (id)
        )
    ''')
    
    # Chain Analytics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chain_analytics (
            id TEXT PRIMARY KEY,
            chain_id TEXT NOT NULL,
            date DATE NOT NULL,
            total_bookings INTEGER DEFAULT 0,
            total_revenue REAL DEFAULT 0.0,
            total_customers INTEGER DEFAULT 0,
            occupancy_rate REAL DEFAULT 0.0,
            avg_ticket_price REAL DEFAULT 0.0,
            top_movie TEXT,
            top_theater TEXT,
            peak_hour TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chain_id) REFERENCES cinema_chains (id)
        )
    ''')
    
    # Location Analytics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS location_analytics (
            id TEXT PRIMARY KEY,
            theater_id TEXT NOT NULL,
            date DATE NOT NULL,
            bookings_count INTEGER DEFAULT 0,
            revenue REAL DEFAULT 0.0,
            customers_count INTEGER DEFAULT 0,
            occupancy_rate REAL DEFAULT 0.0,
            popular_time_slots JSON,
            demographic_data JSON,
            weather_impact REAL DEFAULT 0.0,
            local_events JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (theater_id) REFERENCES theaters (id)
        )
    ''')
    
    # Cross-location bookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cross_location_bookings (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            home_theater_id TEXT,
            booked_theater_id TEXT NOT NULL,
            distance_km REAL,
            booking_reason TEXT, -- convenience, showtimes, pricing, features
            movie_id TEXT,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (home_theater_id) REFERENCES theaters (id),
            FOREIGN KEY (booked_theater_id) REFERENCES theaters (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Pydantic models
class CinemaChain(BaseModel):
    name: str
    description: Optional[str] = None
    headquarters_location: str
    founded_year: Optional[int] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    chain_type: str = "multiplex"

class Theater(BaseModel):
    chain_id: str
    name: str
    address: str
    city: str
    state: str
    country: str
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    parking_spaces: int = 0
    facilities: Optional[Dict] = None
    operating_hours: Optional[Dict] = None
    opening_date: Optional[str] = None

class Screen(BaseModel):
    theater_id: str
    screen_number: int
    name: Optional[str] = None
    screen_type: str = "standard"
    total_seats: int
    rows: int
    seats_per_row: int
    screen_size: Optional[str] = None
    sound_system: Optional[str] = None
    projection_type: Optional[str] = None
    accessibility_features: Optional[Dict] = None
    premium_features: Optional[Dict] = None

class LocationSearch(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 25.0
    chain_filter: Optional[str] = None
    features_filter: Optional[List[str]] = None

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_multi_cinema_db()
    logger.info("🏢 Multi-Cinema Chain Service starting up...")
    yield
    # Shutdown
    logger.info("🏢 Multi-Cinema Chain Service shutting down...")

app = FastAPI(
    title="🏢 Multi-Cinema Chain Management Service",
    description="Enterprise theater management with location-based services",
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

class MultiCinemaService:
    """Enterprise Multi-Cinema Chain Management Service"""
    
    def __init__(self):
        self.db_path = 'multi_cinema.db'
    
    def _get_connection(self):
        return sqlite3.connect(self.db_path)
    
    # Chain Management
    def create_cinema_chain(self, chain_data: CinemaChain) -> Dict[str, Any]:
        """Create a new cinema chain"""
        chain_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO cinema_chains 
            (id, name, description, headquarters_location, founded_year, 
             website, logo_url, contact_email, contact_phone, chain_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            chain_id, chain_data.name, chain_data.description,
            chain_data.headquarters_location, chain_data.founded_year,
            chain_data.website, chain_data.logo_url, chain_data.contact_email,
            chain_data.contact_phone, chain_data.chain_type
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "chain_id": chain_id,
            "name": chain_data.name,
            "status": "created",
            "message": f"Cinema chain '{chain_data.name}' created successfully"
        }
    
    def get_all_chains(self) -> List[Dict[str, Any]]:
        """Get all cinema chains"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, headquarters_location, total_theaters,
                   total_screens, founded_year, chain_type, is_active
            FROM cinema_chains 
            WHERE is_active = TRUE
            ORDER BY name
        ''')
        
        chains = []
        for row in cursor.fetchall():
            chains.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "headquarters_location": row[3],
                "total_theaters": row[4],
                "total_screens": row[5],
                "founded_year": row[6],
                "chain_type": row[7],
                "is_active": row[8]
            })
        
        conn.close()
        return chains
    
    # Theater Management
    def add_theater_to_chain(self, theater_data: Theater) -> Dict[str, Any]:
        """Add a new theater to a chain"""
        theater_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Validate chain exists
        cursor.execute('SELECT id FROM cinema_chains WHERE id = ?', (theater_data.chain_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cinema chain not found")
        
        facilities_json = json.dumps(theater_data.facilities) if theater_data.facilities else None
        hours_json = json.dumps(theater_data.operating_hours) if theater_data.operating_hours else None
        
        cursor.execute('''
            INSERT INTO theaters 
            (id, chain_id, name, address, city, state, country, postal_code,
             latitude, longitude, phone, email, manager_name, parking_spaces,
             facilities, operating_hours, opening_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            theater_id, theater_data.chain_id, theater_data.name,
            theater_data.address, theater_data.city, theater_data.state,
            theater_data.country, theater_data.postal_code, theater_data.latitude,
            theater_data.longitude, theater_data.phone, theater_data.email,
            theater_data.manager_name, theater_data.parking_spaces,
            facilities_json, hours_json, theater_data.opening_date
        ))
        
        # Update chain theater count
        cursor.execute('''
            UPDATE cinema_chains 
            SET total_theaters = total_theaters + 1 
            WHERE id = ?
        ''', (theater_data.chain_id,))
        
        conn.commit()
        conn.close()
        
        return {
            "theater_id": theater_id,
            "name": theater_data.name,
            "chain_id": theater_data.chain_id,
            "status": "created",
            "message": f"Theater '{theater_data.name}' added to chain successfully"
        }
    
    def find_theaters_by_location(self, search: LocationSearch) -> List[Dict[str, Any]]:
        """Find theaters near a location"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build query based on filters
        base_query = '''
            SELECT t.id, t.name, t.address, t.city, t.state, t.latitude, t.longitude,
                   t.facilities, c.name as chain_name, c.chain_type,
                   t.total_screens, t.total_capacity
            FROM theaters t
            JOIN cinema_chains c ON t.chain_id = c.id
            WHERE t.is_active = TRUE AND c.is_active = TRUE
        '''
        
        params = []
        
        if search.chain_filter:
            base_query += ' AND c.id = ?'
            params.append(search.chain_filter)
        
        cursor.execute(base_query, params)
        
        theaters = []
        for row in cursor.fetchall():
            theater_lat, theater_lng = row[5], row[6]
            
            # Calculate distance if coordinates available
            distance = None
            if theater_lat and theater_lng:
                distance = self._calculate_distance(
                    search.latitude, search.longitude,
                    theater_lat, theater_lng
                )
                
                # Filter by radius
                if distance > search.radius_km:
                    continue
            
            facilities = json.loads(row[7]) if row[7] else {}
            
            # Filter by features if specified
            if search.features_filter:
                theater_features = set(facilities.keys())
                required_features = set(search.features_filter)
                if not required_features.issubset(theater_features):
                    continue
            
            theaters.append({
                "id": row[0],
                "name": row[1],
                "address": row[2],
                "city": row[3],
                "state": row[4],
                "latitude": theater_lat,
                "longitude": theater_lng,
                "distance_km": round(distance, 2) if distance else None,
                "facilities": facilities,
                "chain_name": row[8],
                "chain_type": row[9],
                "total_screens": row[10],
                "total_capacity": row[11]
            })
        
        # Sort by distance
        theaters.sort(key=lambda x: x['distance_km'] or float('inf'))
        
        conn.close()
        return theaters
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    # Screen Management
    def add_screen_to_theater(self, screen_data: Screen) -> Dict[str, Any]:
        """Add a screen to a theater"""
        screen_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Validate theater exists
        cursor.execute('SELECT id FROM theaters WHERE id = ?', (screen_data.theater_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Theater not found")
        
        accessibility_json = json.dumps(screen_data.accessibility_features) if screen_data.accessibility_features else None
        premium_json = json.dumps(screen_data.premium_features) if screen_data.premium_features else None
        
        cursor.execute('''
            INSERT INTO screens 
            (id, theater_id, screen_number, name, screen_type, total_seats,
             rows, seats_per_row, screen_size, sound_system, projection_type,
             accessibility_features, premium_features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            screen_id, screen_data.theater_id, screen_data.screen_number,
            screen_data.name, screen_data.screen_type, screen_data.total_seats,
            screen_data.rows, screen_data.seats_per_row, screen_data.screen_size,
            screen_data.sound_system, screen_data.projection_type,
            accessibility_json, premium_json
        ))
        
        # Update theater screen and capacity counts
        cursor.execute('''
            UPDATE theaters 
            SET total_screens = total_screens + 1,
                total_capacity = total_capacity + ?
            WHERE id = ?
        ''', (screen_data.total_seats, screen_data.theater_id))
        
        # Update chain screen count
        cursor.execute('''
            UPDATE cinema_chains 
            SET total_screens = total_screens + 1 
            WHERE id = (SELECT chain_id FROM theaters WHERE id = ?)
        ''', (screen_data.theater_id,))
        
        conn.commit()
        conn.close()
        
        return {
            "screen_id": screen_id,
            "screen_number": screen_data.screen_number,
            "theater_id": screen_data.theater_id,
            "status": "created",
            "message": f"Screen {screen_data.screen_number} added successfully"
        }
    
    # Analytics
    def get_chain_analytics(self, chain_id: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics for a specific chain"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get chain info
        cursor.execute('SELECT name FROM cinema_chains WHERE id = ?', (chain_id,))
        chain_info = cursor.fetchone()
        if not chain_info:
            raise HTTPException(status_code=404, detail="Chain not found")
        
        # Get theater count and locations
        cursor.execute('''
            SELECT COUNT(*) as theater_count,
                   COUNT(DISTINCT city) as cities_count,
                   COUNT(DISTINCT state) as states_count
            FROM theaters WHERE chain_id = ? AND is_active = TRUE
        ''', (chain_id,))
        
        location_stats = cursor.fetchone()
        
        # Get recent analytics
        cursor.execute('''
            SELECT date, total_bookings, total_revenue, occupancy_rate
            FROM chain_analytics 
            WHERE chain_id = ? AND date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC
        ''', (chain_id, days))
        
        daily_analytics = []
        for row in cursor.fetchall():
            daily_analytics.append({
                "date": row[0],
                "bookings": row[1],
                "revenue": row[2],
                "occupancy_rate": row[3]
            })
        
        conn.close()
        
        return {
            "chain_name": chain_info[0],
            "chain_id": chain_id,
            "theater_count": location_stats[0],
            "cities_count": location_stats[1],
            "states_count": location_stats[2],
            "period_days": days,
            "daily_analytics": daily_analytics,
            "summary": {
                "total_bookings": sum(d["bookings"] for d in daily_analytics),
                "total_revenue": sum(d["revenue"] for d in daily_analytics),
                "avg_occupancy": sum(d["occupancy_rate"] for d in daily_analytics) / len(daily_analytics) if daily_analytics else 0
            }
        }

# Initialize service
multi_cinema_service = MultiCinemaService()

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Multi-Cinema Chain Management Dashboard"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🏢 Multi-Cinema Chain Management</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                     color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 30px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .stat-box { background: linear-gradient(45deg, #FF6B6B, #4ECDC4); color: white; 
                       padding: 15px; border-radius: 8px; text-align: center; }
            .chain-item { border-left: 4px solid #667eea; padding: 10px; margin: 10px 0; background: #f8f9fa; }
            .theater-item { border-left: 4px solid #4ECDC4; padding: 8px; margin: 8px 0; background: #f0f8ff; }
            button { background: #667eea; color: white; border: none; padding: 10px 20px; 
                    border-radius: 5px; cursor: pointer; margin: 5px; }
            button:hover { background: #5a6fd8; }
            .search-box { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            .location-result { background: #e8f5e8; padding: 10px; margin: 5px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 Multi-Cinema Chain Management System</h1>
                <p>Enterprise Theater Management • Location-Based Services • Cross-Chain Analytics</p>
            </div>
            
            <div class="grid">
                <!-- Chain Overview -->
                <div class="card">
                    <h3>🏢 Cinema Chains Overview</h3>
                    <div id="chainsContainer">Loading chains...</div>
                    <button onclick="loadChains()">🔄 Refresh Chains</button>
                </div>
                
                <!-- Location Search -->
                <div class="card">
                    <h3>📍 Theater Location Search</h3>
                    <input type="number" id="latitude" placeholder="Latitude (e.g., 40.7128)" class="search-box">
                    <input type="number" id="longitude" placeholder="Longitude (e.g., -74.0060)" class="search-box">
                    <input type="number" id="radius" placeholder="Search Radius (km)" value="25" class="search-box">
                    <button onclick="searchTheaters()">🔍 Search Theaters</button>
                    <div id="searchResults"></div>
                </div>
                
                <!-- Quick Stats -->
                <div class="card">
                    <h3>📊 Platform Statistics</h3>
                    <div id="statsContainer">
                        <div class="stat-box">
                            <h4>Total Chains</h4>
                            <div id="totalChains">-</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="grid" style="margin-top: 20px;">
                <!-- Chain Analytics -->
                <div class="card">
                    <h3>📈 Chain Performance Analytics</h3>
                    <canvas id="chainChart" width="400" height="200"></canvas>
                </div>
                
                <!-- Theater Distribution Map -->
                <div class="card">
                    <h3>🗺️ Theater Distribution</h3>
                    <div id="distributionMap">
                        <p>Geographic distribution of theaters across chains</p>
                        <canvas id="distributionChart" width="400" height="200"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        let chainsData = [];
        
        async function loadChains() {
            try {
                const response = await fetch('/chains/');
                const chains = await response.json();
                chainsData = chains;
                
                const container = document.getElementById('chainsContainer');
                container.innerHTML = chains.map(chain => `
                    <div class="chain-item">
                        <strong>${chain.name}</strong> (${chain.chain_type})<br>
                        📍 ${chain.headquarters_location}<br>
                        🎪 ${chain.total_theaters} theaters • 📺 ${chain.total_screens} screens
                        ${chain.founded_year ? '<br>📅 Founded: ' + chain.founded_year : ''}
                    </div>
                `).join('');
                
                document.getElementById('totalChains').textContent = chains.length;
                updateChainChart(chains);
                
            } catch (error) {
                console.error('Error loading chains:', error);
                document.getElementById('chainsContainer').innerHTML = '<p style="color: red;">Error loading chains</p>';
            }
        }
        
        async function searchTheaters() {
            const lat = document.getElementById('latitude').value;
            const lng = document.getElementById('longitude').value;
            const radius = document.getElementById('radius').value || 25;
            
            if (!lat || !lng) {
                alert('Please enter both latitude and longitude');
                return;
            }
            
            try {
                const response = await fetch('/theaters/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        latitude: parseFloat(lat),
                        longitude: parseFloat(lng),
                        radius_km: parseFloat(radius)
                    })
                });
                
                const theaters = await response.json();
                const resultsDiv = document.getElementById('searchResults');
                
                if (theaters.length === 0) {
                    resultsDiv.innerHTML = '<p>No theaters found in this area</p>';
                    return;
                }
                
                resultsDiv.innerHTML = `
                    <h4>Found ${theaters.length} theaters:</h4>
                    ${theaters.map(theater => `
                        <div class="location-result">
                            <strong>${theater.name}</strong> (${theater.chain_name})<br>
                            📍 ${theater.address}, ${theater.city}, ${theater.state}<br>
                            📏 ${theater.distance_km} km away<br>
                            📺 ${theater.total_screens} screens • 👥 ${theater.total_capacity} capacity
                        </div>
                    `).join('')}
                `;
                
            } catch (error) {
                console.error('Error searching theaters:', error);
                document.getElementById('searchResults').innerHTML = '<p style="color: red;">Error searching theaters</p>';
            }
        }
        
        function updateChainChart(chains) {
            const ctx = document.getElementById('chainChart').getContext('2d');
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: chains.map(c => c.name),
                    datasets: [{
                        label: 'Number of Theaters',
                        data: chains.map(c => c.total_theaters),
                        backgroundColor: 'rgba(102, 126, 234, 0.6)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        // Initialize dashboard
        loadChains();
        
        // Auto-refresh every 30 seconds
        setInterval(loadChains, 30000);
        </script>
    </body>
    </html>
    '''

@app.post("/chains/")
async def create_chain(chain_data: CinemaChain):
    """Create a new cinema chain"""
    return multi_cinema_service.create_cinema_chain(chain_data)

@app.get("/chains/")
async def get_chains():
    """Get all cinema chains"""
    return multi_cinema_service.get_all_chains()

@app.post("/theaters/")
async def add_theater(theater_data: Theater):
    """Add a theater to a chain"""
    return multi_cinema_service.add_theater_to_chain(theater_data)

@app.post("/theaters/search")
async def search_theaters(search: LocationSearch):
    """Search theaters by location"""
    return multi_cinema_service.find_theaters_by_location(search)

@app.post("/screens/")
async def add_screen(screen_data: Screen):
    """Add a screen to a theater"""
    return multi_cinema_service.add_screen_to_theater(screen_data)

@app.get("/chains/{chain_id}/analytics")
async def get_chain_analytics(chain_id: str, days: int = Query(30, ge=1, le=365)):
    """Get analytics for a specific chain"""
    return multi_cinema_service.get_chain_analytics(chain_id, days)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Multi-Cinema Chain Management",
        "status": "healthy",
        "port": 8020,
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Enterprise Chain Management",
            "Location-Based Services", 
            "Multi-Tenant Architecture",
            "Cross-Location Analytics",
            "Geographic Theater Search"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🏢 Starting Multi-Cinema Chain Management Service...")
    print("📍 Service URL: http://127.0.0.1:8020")
    print("📊 Dashboard: http://127.0.0.1:8020/")
    print("📚 API Docs: http://127.0.0.1:8020/docs")
    
    uvicorn.run(app, host="127.0.0.1", port=8020)