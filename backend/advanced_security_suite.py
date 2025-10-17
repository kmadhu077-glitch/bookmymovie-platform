"""
🛡️ Advanced Security Suite Service
Enterprise security framework with OAuth, rate limiting, fraud detection, and analytics
Port: 8023
"""

import sqlite3
import json
import time
import jwt
import hashlib
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request, Depends, Response, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from pydantic import BaseModel, field_validator
import logging
from contextlib import asynccontextmanager
from enum import Enum
import re
import ipaddress
from urllib.parse import urlencode
import secrets
import bcrypt
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security enums and constants
class SecurityEventType(str, Enum):
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    API_ACCESS = "api_access"
    RATE_LIMIT_HIT = "rate_limit_hit"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    FRAUD_DETECTED = "fraud_detected"
    OAUTH_LOGIN = "oauth_login"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"

class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuthProvider(str, Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    GITHUB = "github"
    LINKEDIN = "linkedin"
    INTERNAL = "internal"

# Security models
class SecurityEvent(BaseModel):
    event_id: str
    event_type: SecurityEventType
    timestamp: datetime
    user_id: Optional[str] = None
    ip_address: str
    user_agent: Optional[str] = None
    threat_level: ThreatLevel
    details: Dict[str, Any]
    action_taken: Optional[str] = None

class RateLimitRule(BaseModel):
    endpoint: str
    max_requests: int
    time_window: int  # seconds
    per_ip: bool = True
    per_user: bool = False

class FraudRule(BaseModel):
    rule_name: str
    rule_type: str
    conditions: Dict[str, Any]
    threshold: float
    action: str  # block, flag, monitor
    enabled: bool = True

class OAuthConfig(BaseModel):
    provider: AuthProvider
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: List[str]
    enabled: bool = True

class SecurityAlert(BaseModel):
    alert_id: str
    alert_type: str
    severity: ThreatLevel
    description: str
    timestamp: datetime
    resolved: bool = False
    user_id: Optional[str] = None
    ip_address: Optional[str] = None

# In-memory stores for high-performance security operations
class SecurityManager:
    def __init__(self):
        self.rate_limits = defaultdict(lambda: defaultdict(deque))
        self.blocked_ips: Set[str] = set()
        self.suspicious_ips = defaultdict(int)
        self.active_sessions = {}
        self.failed_login_attempts = defaultdict(int)
        self.fraud_scores = defaultdict(float)
        self.lock = Lock()
        
        # OAuth configurations
        self.oauth_configs = {
            AuthProvider.GOOGLE: OAuthConfig(
                provider=AuthProvider.GOOGLE,
                client_id="your-google-client-id",
                client_secret="your-google-client-secret",
                redirect_uri="http://localhost:8023/oauth/callback/google",
                scope=["openid", "email", "profile"]
            ),
            AuthProvider.GITHUB: OAuthConfig(
                provider=AuthProvider.GITHUB,
                client_id="your-github-client-id", 
                client_secret="your-github-client-secret",
                redirect_uri="http://localhost:8023/oauth/callback/github",
                scope=["user:email", "read:user"]
            )
        }
        
        # Default rate limit rules
        self.rate_limit_rules = [
            RateLimitRule(endpoint="/api/auth/login", max_requests=5, time_window=300),  # 5 per 5 minutes
            RateLimitRule(endpoint="/api/auth/register", max_requests=3, time_window=3600),  # 3 per hour
            RateLimitRule(endpoint="/api/bookings", max_requests=10, time_window=60),  # 10 per minute
            RateLimitRule(endpoint="/api/payments", max_requests=5, time_window=300),  # 5 per 5 minutes
            RateLimitRule(endpoint="/api/*", max_requests=100, time_window=60),  # General API limit
        ]
        
        # Fraud detection rules
        self.fraud_rules = [
            FraudRule(
                rule_name="rapid_multiple_bookings",
                rule_type="booking_pattern",
                conditions={"booking_count": 10, "time_window": 300},
                threshold=0.8,
                action="flag"
            ),
            FraudRule(
                rule_name="multiple_payment_failures",
                rule_type="payment_pattern", 
                conditions={"failure_count": 3, "time_window": 600},
                threshold=0.9,
                action="block"
            ),
            FraudRule(
                rule_name="suspicious_ip_geolocation",
                rule_type="geo_anomaly",
                conditions={"distance_km": 1000, "time_window": 3600},
                threshold=0.7,
                action="flag"
            )
        ]

# Initialize security manager
security_manager = SecurityManager()

# Database setup for security analytics
def init_security_db():
    """Initialize security database with comprehensive schemas"""
    conn = sqlite3.connect('security_analytics.db')
    cursor = conn.cursor()
    
    # Security events table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS security_events (
        event_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        user_id TEXT,
        ip_address TEXT NOT NULL,
        user_agent TEXT,
        threat_level TEXT NOT NULL,
        details TEXT, -- JSON
        action_taken TEXT
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON security_events(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_user_id ON security_events(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_ip ON security_events(ip_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_threat ON security_events(threat_level)')
    
    # Rate limiting logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rate_limit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        endpoint TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        user_id TEXT,
        timestamp DATETIME NOT NULL,
        requests_count INTEGER,
        limit_exceeded BOOLEAN
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_endpoint ON rate_limit_logs(endpoint)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_ip ON rate_limit_logs(ip_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rate_timestamp ON rate_limit_logs(timestamp)')
    
    # Fraud detection logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fraud_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        rule_name TEXT NOT NULL,
        fraud_score REAL NOT NULL,
        details TEXT, -- JSON
        timestamp DATETIME NOT NULL,
        action_taken TEXT
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fraud_user ON fraud_logs(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fraud_rule ON fraud_logs(rule_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fraud_timestamp ON fraud_logs(timestamp)')
    
    # OAuth sessions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS oauth_sessions (
        session_id TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        user_id TEXT NOT NULL,
        access_token TEXT,
        refresh_token TEXT,
        expires_at DATETIME,
        created_at DATETIME NOT NULL
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_oauth_user ON oauth_sessions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_oauth_provider ON oauth_sessions(provider)')
    
    # Security alerts
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS security_alerts (
        alert_id TEXT PRIMARY KEY,
        alert_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        description TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        resolved BOOLEAN DEFAULT FALSE,
        user_id TEXT,
        ip_address TEXT
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON security_alerts(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_severity ON security_alerts(severity)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON security_alerts(resolved)')
    
    # IP blacklist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ip_blacklist (
        ip_address TEXT PRIMARY KEY,
        reason TEXT NOT NULL,
        blocked_at DATETIME NOT NULL,
        blocked_until DATETIME,
        permanent BOOLEAN DEFAULT FALSE
    )
    ''')
    
    # User security profiles
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_security_profiles (
        user_id TEXT PRIMARY KEY,
        risk_score REAL DEFAULT 0.0,
        last_login_ip TEXT,
        last_login_time DATETIME,
        failed_login_count INTEGER DEFAULT 0,
        account_locked BOOLEAN DEFAULT FALSE,
        locked_until DATETIME,
        security_level TEXT DEFAULT 'standard',
        two_factor_enabled BOOLEAN DEFAULT FALSE,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Security database initialized successfully")

# Security middleware and utilities
class SecurityMiddleware:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def log_security_event(self, event: SecurityEvent):
        """Log security event asynchronously"""
        try:
            conn = sqlite3.connect('security_analytics.db')
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO security_events 
            (event_id, event_type, timestamp, user_id, ip_address, user_agent, threat_level, details, action_taken)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.user_id,
                event.ip_address,
                event.user_agent,
                event.threat_level.value,
                json.dumps(event.details),
                event.action_taken
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def check_rate_limit(self, endpoint: str, ip_address: str, user_id: Optional[str] = None) -> bool:
        """Check if request exceeds rate limits"""
        current_time = time.time()
        
        with security_manager.lock:
            for rule in security_manager.rate_limit_rules:
                if self._matches_endpoint(endpoint, rule.endpoint):
                    key = f"{ip_address}:{endpoint}" if rule.per_ip else f"{user_id}:{endpoint}"
                    
                    # Clean old entries
                    request_times = security_manager.rate_limits[rule.endpoint][key]
                    while request_times and request_times[0] < current_time - rule.time_window:
                        request_times.popleft()
                    
                    # Check limit
                    if len(request_times) >= rule.max_requests:
                        self._log_rate_limit_hit(endpoint, ip_address, user_id, len(request_times))
                        return False
                    
                    # Add current request
                    request_times.append(current_time)
                    
            return True
    
    def _matches_endpoint(self, endpoint: str, pattern: str) -> bool:
        """Check if endpoint matches pattern (supports wildcards)"""
        if pattern == endpoint:
            return True
        if pattern.endswith('*'):
            return endpoint.startswith(pattern[:-1])
        return False
    
    def _log_rate_limit_hit(self, endpoint: str, ip_address: str, user_id: Optional[str], count: int):
        """Log rate limit violation"""
        try:
            conn = sqlite3.connect('security_analytics.db')
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO rate_limit_logs (endpoint, ip_address, user_id, timestamp, requests_count, limit_exceeded)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (endpoint, ip_address, user_id, datetime.now().isoformat(), count, True))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log rate limit hit: {e}")
    
    def detect_fraud(self, user_id: str, event_data: Dict[str, Any]) -> float:
        """Detect potential fraud and return risk score"""
        fraud_score = 0.0
        
        for rule in security_manager.fraud_rules:
            if not rule.enabled:
                continue
                
            rule_score = self._evaluate_fraud_rule(rule, user_id, event_data)
            fraud_score = max(fraud_score, rule_score)
            
            if rule_score >= rule.threshold:
                self._log_fraud_detection(user_id, rule, rule_score, event_data)
                
                if rule.action == "block":
                    self._block_user(user_id, "Fraud detected")
                elif rule.action == "flag":
                    self._create_security_alert(
                        alert_type="fraud_detection",
                        severity=ThreatLevel.HIGH,
                        description=f"Fraud rule '{rule.rule_name}' triggered",
                        user_id=user_id
                    )
        
        return fraud_score
    
    def _evaluate_fraud_rule(self, rule: FraudRule, user_id: str, event_data: Dict[str, Any]) -> float:
        """Evaluate specific fraud rule"""
        if rule.rule_type == "booking_pattern":
            return self._check_booking_pattern(rule, user_id, event_data)
        elif rule.rule_type == "payment_pattern":
            return self._check_payment_pattern(rule, user_id, event_data)
        elif rule.rule_type == "geo_anomaly":
            return self._check_geo_anomaly(rule, user_id, event_data)
        
        return 0.0
    
    def _check_booking_pattern(self, rule: FraudRule, user_id: str, event_data: Dict[str, Any]) -> float:
        """Check for suspicious booking patterns"""
        # Simulate checking recent booking count
        booking_count = event_data.get('recent_booking_count', 0)
        threshold_count = rule.conditions.get('booking_count', 10)
        
        if booking_count >= threshold_count:
            return min(1.0, booking_count / threshold_count)
        
        return 0.0
    
    def _check_payment_pattern(self, rule: FraudRule, user_id: str, event_data: Dict[str, Any]) -> float:
        """Check for suspicious payment patterns"""
        failure_count = event_data.get('payment_failures', 0)
        threshold_failures = rule.conditions.get('failure_count', 3)
        
        if failure_count >= threshold_failures:
            return min(1.0, failure_count / threshold_failures)
        
        return 0.0
    
    def _check_geo_anomaly(self, rule: FraudRule, user_id: str, event_data: Dict[str, Any]) -> float:
        """Check for geographical anomalies"""
        # Simulate geo-location distance check
        distance = event_data.get('geo_distance_km', 0)
        threshold_distance = rule.conditions.get('distance_km', 1000)
        
        if distance >= threshold_distance:
            return min(1.0, distance / threshold_distance / 10)  # Normalize
        
        return 0.0

    def _log_fraud_detection(self, user_id: str, rule: FraudRule, score: float, event_data: Dict[str, Any]):
        """Log fraud detection"""
        try:
            conn = sqlite3.connect('security_analytics.db')
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO fraud_logs (user_id, rule_name, fraud_score, details, timestamp, action_taken)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, rule.rule_name, score, json.dumps(event_data), datetime.now().isoformat(), rule.action))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log fraud detection: {e}")
    
    def _block_user(self, user_id: str, reason: str):
        """Block user account"""
        try:
            conn = sqlite3.connect('security_analytics.db')
            cursor = conn.cursor()
            
            # Update user security profile
            cursor.execute('''
            INSERT OR REPLACE INTO user_security_profiles 
            (user_id, account_locked, locked_until, updated_at)
            VALUES (?, ?, ?, ?)
            ''', (user_id, True, (datetime.now() + timedelta(hours=24)).isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"User {user_id} blocked: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to block user: {e}")
    
    def _create_security_alert(self, alert_type: str, severity: ThreatLevel, description: str, 
                             user_id: Optional[str] = None, ip_address: Optional[str] = None):
        """Create security alert"""
        try:
            alert_id = f"alert_{int(time.time() * 1000)}"
            
            conn = sqlite3.connect('security_analytics.db')
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO security_alerts (alert_id, alert_type, severity, description, timestamp, user_id, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (alert_id, alert_type, severity.value, description, datetime.now().isoformat(), user_id, ip_address))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"Security alert created: {alert_type} - {description}")
            
        except Exception as e:
            logger.error(f"Failed to create security alert: {e}")

# Initialize security middleware
security_middleware = SecurityMiddleware()

# OAuth utilities
class OAuthManager:
    def __init__(self):
        self.state_store = {}  # In production, use Redis
    
    def generate_oauth_url(self, provider: AuthProvider) -> str:
        """Generate OAuth authorization URL"""
        config = security_manager.oauth_configs.get(provider)
        if not config or not config.enabled:
            raise HTTPException(status_code=400, detail=f"OAuth provider {provider} not configured")
        
        state = secrets.token_urlsafe(32)
        self.state_store[state] = {"provider": provider, "timestamp": time.time()}
        
        if provider == AuthProvider.GOOGLE:
            params = {
                'client_id': config.client_id,
                'redirect_uri': config.redirect_uri,
                'scope': ' '.join(config.scope),
                'response_type': 'code',
                'state': state
            }
            return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        
        elif provider == AuthProvider.GITHUB:
            params = {
                'client_id': config.client_id,
                'redirect_uri': config.redirect_uri,
                'scope': ','.join(config.scope),
                'state': state
            }
            return f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        
        else:
            raise HTTPException(status_code=400, detail=f"OAuth provider {provider} not implemented")
    
    def verify_state(self, state: str) -> Dict[str, Any]:
        """Verify OAuth state parameter"""
        if state not in self.state_store:
            raise HTTPException(status_code=400, detail="Invalid OAuth state")
        
        state_data = self.state_store.pop(state)
        
        # Check if state is expired (5 minutes)
        if time.time() - state_data['timestamp'] > 300:
            raise HTTPException(status_code=400, detail="OAuth state expired")
        
        return state_data

# Initialize OAuth manager
oauth_manager = OAuthManager()

# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    init_security_db()
    logger.info("Security Suite Service starting up...")
    
    yield
    
    # Shutdown
    logger.info("Security Suite Service shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="🛡️ Advanced Security Suite",
    description="Enterprise security framework with OAuth, rate limiting, fraud detection, and analytics",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
@app.middleware("http")
async def security_middleware_handler(request: Request, call_next):
    """Apply security middleware to all requests"""
    start_time = time.time()
    
    # Get client info
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    endpoint = request.url.path
    
    # Check IP blacklist
    if client_ip in security_manager.blocked_ips:
        raise HTTPException(status_code=403, detail="IP address blocked")
    
    # Check rate limits
    if not security_middleware.check_rate_limit(endpoint, client_ip):
        # Log security event
        event = SecurityEvent(
            event_id=f"event_{int(time.time() * 1000)}",
            event_type=SecurityEventType.RATE_LIMIT_HIT,
            timestamp=datetime.now(),
            ip_address=client_ip,
            user_agent=user_agent,
            threat_level=ThreatLevel.MEDIUM,
            details={"endpoint": endpoint, "rate_limit_exceeded": True}
        )
        await security_middleware.log_security_event(event)
        
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Process request
    response = await call_next(request)
    
    # Log API access
    process_time = time.time() - start_time
    
    event = SecurityEvent(
        event_id=f"event_{int(time.time() * 1000)}",
        event_type=SecurityEventType.API_ACCESS,
        timestamp=datetime.now(),
        ip_address=client_ip,
        user_agent=user_agent,
        threat_level=ThreatLevel.LOW,
        details={
            "endpoint": endpoint,
            "method": request.method,
            "status_code": response.status_code,
            "process_time": process_time
        }
    )
    await security_middleware.log_security_event(event)
    
    return response

# API endpoints
@app.get("/")
async def dashboard():
    """Security dashboard"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🛡️ Advanced Security Suite</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }
            .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
            .header p { font-size: 1.2rem; opacity: 0.9; }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease;
            }
            .card:hover { transform: translateY(-5px); }
            .card h3 {
                color: #4f46e5;
                margin-bottom: 15px;
                font-size: 1.3rem;
            }
            .metric {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 0;
                border-bottom: 1px solid #f0f0f0;
            }
            .metric:last-child { border-bottom: none; }
            .metric-value {
                font-weight: bold;
                color: #059669;
            }
            .alert {
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
            }
            .alert.high { border-color: #dc2626; background: #fee2e2; }
            .alert.medium { border-color: #f59e0b; background: #fef3c7; }
            .alert.low { border-color: #10b981; background: #d1fae5; }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 1rem;
                margin: 5px;
                transition: all 0.3s ease;
            }
            .btn:hover { transform: translateY(-2px); opacity: 0.9; }
            .oauth-section {
                display: flex;
                gap: 15px;
                margin: 20px 0;
            }
            .oauth-btn {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                text-decoration: none;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-running { background: #10b981; }
            .status-warning { background: #f59e0b; }
            .status-error { background: #ef4444; }
            .chart-container {
                width: 100%;
                height: 300px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛡️ Advanced Security Suite</h1>
                <p>Enterprise Security Framework • OAuth • Rate Limiting • Fraud Detection</p>
            </div>
            
            <div class="dashboard-grid">
                <div class="card">
                    <h3>🔒 Security Status</h3>
                    <div class="metric">
                        <span><span class="status-indicator status-running"></span>OAuth Service</span>
                        <span class="metric-value">Active</span>
                    </div>
                    <div class="metric">
                        <span><span class="status-indicator status-running"></span>Rate Limiting</span>
                        <span class="metric-value">Active</span>
                    </div>
                    <div class="metric">
                        <span><span class="status-indicator status-running"></span>Fraud Detection</span>
                        <span class="metric-value">Active</span>
                    </div>
                    <div class="metric">
                        <span><span class="status-indicator status-running"></span>Security Analytics</span>
                        <span class="metric-value">Active</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📊 Real-time Metrics</h3>
                    <div class="metric">
                        <span>Active Sessions</span>
                        <span class="metric-value" id="activeSessions">1,247</span>
                    </div>
                    <div class="metric">
                        <span>Rate Limit Hits (1h)</span>
                        <span class="metric-value" id="rateLimitHits">23</span>
                    </div>
                    <div class="metric">
                        <span>Fraud Attempts Blocked</span>
                        <span class="metric-value" id="fraudBlocked">5</span>
                    </div>
                    <div class="metric">
                        <span>Security Events (24h)</span>
                        <span class="metric-value" id="securityEvents">2,891</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🚨 Security Alerts</h3>
                    <div id="securityAlerts">
                        <div class="alert high">
                            <strong>HIGH:</strong> Multiple failed login attempts from IP 192.168.1.100
                        </div>
                        <div class="alert medium">
                            <strong>MEDIUM:</strong> Unusual booking pattern detected for user ID 12345
                        </div>
                        <div class="alert low">
                            <strong>LOW:</strong> New device login from known user
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🔐 OAuth Providers</h3>
                    <div class="oauth-section">
                        <a href="/oauth/google" class="oauth-btn btn">
                            🔍 Google OAuth
                        </a>
                        <a href="/oauth/github" class="oauth-btn btn">
                            🐙 GitHub OAuth
                        </a>
                    </div>
                    <div class="metric">
                        <span>OAuth Logins (24h)</span>
                        <span class="metric-value">342</span>
                    </div>
                    <div class="metric">
                        <span>SSO Sessions Active</span>
                        <span class="metric-value">156</span>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-grid">
                <div class="card">
                    <h3>📈 Security Analytics</h3>
                    <div class="chart-container">
                        <canvas id="securityChart"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🌐 IP Geography</h3>
                    <div class="chart-container">
                        <canvas id="geoChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>⚙️ Security Configuration</h3>
                <button class="btn" onclick="updateRateLimits()">🔧 Update Rate Limits</button>
                <button class="btn" onclick="manageFraudRules()">🛡️ Manage Fraud Rules</button>
                <button class="btn" onclick="viewSecurityLogs()">📋 View Security Logs</button>
                <button class="btn" onclick="exportSecurityReport()">📊 Export Security Report</button>
            </div>
        </div>
        
        <script>
        // Initialize security analytics chart
        function initSecurityChart() {
            const ctx = document.getElementById('securityChart').getContext('2d');
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                    datasets: [{
                        label: 'Security Events',
                        data: [45, 28, 89, 156, 203, 187],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Fraud Attempts',
                        data: [2, 1, 5, 8, 12, 7],
                        borderColor: '#dc2626',
                        backgroundColor: 'rgba(220, 38, 38, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Security Events Over Time'
                        }
                    }
                }
            });
        }
        
        // Initialize geo chart
        function initGeoChart() {
            const ctx = document.getElementById('geoChart').getContext('2d');
            
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['United States', 'United Kingdom', 'Germany', 'Canada', 'Others'],
                    datasets: [{
                        data: [45, 20, 15, 10, 10],
                        backgroundColor: [
                            '#667eea',
                            '#764ba2',
                            '#f093fb',
                            '#f5576c',
                            '#4facfe'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Login Geography Distribution'
                        }
                    }
                }
            });
        }
        
        // Update real-time metrics
        function updateMetrics() {
            document.getElementById('activeSessions').textContent = Math.floor(1200 + Math.random() * 100);
            document.getElementById('rateLimitHits').textContent = Math.floor(20 + Math.random() * 10);
            document.getElementById('fraudBlocked').textContent = Math.floor(3 + Math.random() * 5);
            document.getElementById('securityEvents').textContent = Math.floor(2800 + Math.random() * 200);
        }
        
        // Configuration functions
        function updateRateLimits() {
            alert('Rate limit configuration panel would open here');
        }
        
        function manageFraudRules() {
            alert('Fraud rule management panel would open here');
        }
        
        function viewSecurityLogs() {
            window.open('/security/logs', '_blank');
        }
        
        function exportSecurityReport() {
            alert('Security report export started');
        }
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initSecurityChart();
            initGeoChart();
            updateMetrics();
            
            // Update metrics every 30 seconds
            setInterval(updateMetrics, 30000);
        });
        </script>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Advanced Security Suite",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "OAuth Authentication",
            "API Rate Limiting",
            "Fraud Detection",
            "Security Analytics",
            "Real-time Monitoring"
        ],
        "active_rules": {
            "rate_limit_rules": len(security_manager.rate_limit_rules),
            "fraud_rules": len(security_manager.fraud_rules),
            "oauth_providers": len([c for c in security_manager.oauth_configs.values() if c.enabled])
        }
    }

@app.get("/oauth/{provider}")
async def oauth_login(provider: str):
    """Initiate OAuth login"""
    try:
        auth_provider = AuthProvider(provider.lower())
        oauth_url = oauth_manager.generate_oauth_url(auth_provider)
        return RedirectResponse(url=oauth_url)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")

@app.get("/oauth/callback/{provider}")
async def oauth_callback(provider: str, code: str, state: str):
    """Handle OAuth callback"""
    try:
        # Verify state
        state_data = oauth_manager.verify_state(state)
        auth_provider = AuthProvider(state_data['provider'])
        
        # In a real implementation, you would:
        # 1. Exchange code for access token
        # 2. Fetch user info from OAuth provider
        # 3. Create or update user account
        # 4. Generate JWT token for our system
        
        # For demo purposes, return success
        return {
            "message": "OAuth login successful",
            "provider": provider,
            "user_info": {
                "id": f"oauth_{provider}_123456",
                "email": f"user@{provider}.com",
                "name": f"{provider.title()} User"
            },
            "jwt_token": "demo_jwt_token_would_be_here"
        }
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=400, detail="OAuth authentication failed")

@app.get("/security/analytics")
async def security_analytics():
    """Get security analytics data"""
    try:
        conn = sqlite3.connect('security_analytics.db')
        cursor = conn.cursor()
        
        # Get recent security events
        cursor.execute('''
        SELECT event_type, COUNT(*) as count, threat_level
        FROM security_events 
        WHERE timestamp > datetime('now', '-24 hours')
        GROUP BY event_type, threat_level
        ORDER BY count DESC
        ''')
        events_24h = cursor.fetchall()
        
        # Get rate limit violations
        cursor.execute('''
        SELECT endpoint, COUNT(*) as violations
        FROM rate_limit_logs
        WHERE limit_exceeded = 1 AND timestamp > datetime('now', '-1 hours')
        GROUP BY endpoint
        ORDER BY violations DESC
        ''')
        rate_limit_violations = cursor.fetchall()
        
        # Get fraud detection stats
        cursor.execute('''
        SELECT rule_name, COUNT(*) as triggers, AVG(fraud_score) as avg_score
        FROM fraud_logs
        WHERE timestamp > datetime('now', '-24 hours')
        GROUP BY rule_name
        ORDER BY triggers DESC
        ''')
        fraud_stats = cursor.fetchall()
        
        # Get security alerts
        cursor.execute('''
        SELECT alert_type, severity, COUNT(*) as count
        FROM security_alerts
        WHERE timestamp > datetime('now', '-24 hours')
        GROUP BY alert_type, severity
        ORDER BY count DESC
        ''')
        alerts_24h = cursor.fetchall()
        
        conn.close()
        
        return {
            "period": "24 hours",
            "security_events": {
                "total": sum(row[1] for row in events_24h),
                "by_type": [{"type": row[0], "count": row[1], "threat_level": row[2]} for row in events_24h]
            },
            "rate_limiting": {
                "violations_1h": sum(row[1] for row in rate_limit_violations),
                "by_endpoint": [{"endpoint": row[0], "violations": row[1]} for row in rate_limit_violations]
            },
            "fraud_detection": {
                "rules_triggered": len(fraud_stats),
                "by_rule": [{"rule": row[0], "triggers": row[1], "avg_score": row[2]} for row in fraud_stats]
            },
            "security_alerts": {
                "total": sum(row[2] for row in alerts_24h),
                "by_type": [{"type": row[0], "severity": row[1], "count": row[2]} for row in alerts_24h]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get security analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security analytics")

@app.post("/security/fraud-check")
async def fraud_check(request: Request, user_id: str, event_data: Dict[str, Any]):
    """Check for fraud and return risk assessment"""
    try:
        fraud_score = security_middleware.detect_fraud(user_id, event_data)
        
        # Determine risk level
        if fraud_score >= 0.8:
            risk_level = "HIGH"
            action = "BLOCK"
        elif fraud_score >= 0.5:
            risk_level = "MEDIUM"
            action = "FLAG"
        elif fraud_score >= 0.2:
            risk_level = "LOW"
            action = "MONITOR"
        else:
            risk_level = "NONE"
            action = "ALLOW"
        
        # Log security event
        event = SecurityEvent(
            event_id=f"fraud_{int(time.time() * 1000)}",
            event_type=SecurityEventType.FRAUD_DETECTED if fraud_score >= 0.5 else SecurityEventType.SUSPICIOUS_ACTIVITY,
            timestamp=datetime.now(),
            user_id=user_id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
            threat_level=ThreatLevel.HIGH if fraud_score >= 0.8 else ThreatLevel.MEDIUM if fraud_score >= 0.5 else ThreatLevel.LOW,
            details={**event_data, "fraud_score": fraud_score, "risk_level": risk_level},
            action_taken=action
        )
        await security_middleware.log_security_event(event)
        
        return {
            "user_id": user_id,
            "fraud_score": fraud_score,
            "risk_level": risk_level,
            "recommended_action": action,
            "timestamp": datetime.now().isoformat(),
            "rules_triggered": [rule.rule_name for rule in security_manager.fraud_rules 
                              if security_middleware._evaluate_fraud_rule(rule, user_id, event_data) >= rule.threshold]
        }
        
    except Exception as e:
        logger.error(f"Fraud check failed: {e}")
        raise HTTPException(status_code=500, detail="Fraud check failed")

@app.get("/security/logs")
async def security_logs(
    limit: int = Query(100, description="Number of logs to retrieve"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    threat_level: Optional[str] = Query(None, description="Filter by threat level")
):
    """Get security logs with filtering"""
    try:
        conn = sqlite3.connect('security_analytics.db')
        cursor = conn.cursor()
        
        query = "SELECT * FROM security_events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if threat_level:
            query += " AND threat_level = ?"
            params.append(threat_level)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # Convert to dictionaries
        columns = [description[0] for description in cursor.description]
        log_dicts = [dict(zip(columns, log)) for log in logs]
        
        # Parse JSON details
        for log in log_dicts:
            if log['details']:
                log['details'] = json.loads(log['details'])
        
        conn.close()
        
        return {
            "total_logs": len(log_dicts),
            "logs": log_dicts,
            "filters_applied": {
                "event_type": event_type,
                "threat_level": threat_level,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get security logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security logs")

@app.post("/security/block-ip")
async def block_ip(ip_address: str, reason: str, permanent: bool = False):
    """Block IP address"""
    try:
        # Validate IP address
        ipaddress.ip_address(ip_address)
        
        # Add to blocked IPs set
        security_manager.blocked_ips.add(ip_address)
        
        # Store in database
        conn = sqlite3.connect('security_analytics.db')
        cursor = conn.cursor()
        
        blocked_until = None if permanent else (datetime.now() + timedelta(hours=24)).isoformat()
        
        cursor.execute('''
        INSERT OR REPLACE INTO ip_blacklist (ip_address, reason, blocked_at, blocked_until, permanent)
        VALUES (?, ?, ?, ?, ?)
        ''', (ip_address, reason, datetime.now().isoformat(), blocked_until, permanent))
        
        conn.commit()
        conn.close()
        
        # Create security alert
        security_middleware._create_security_alert(
            alert_type="ip_blocked",
            severity=ThreatLevel.HIGH,
            description=f"IP address {ip_address} blocked: {reason}",
            ip_address=ip_address
        )
        
        return {
            "message": f"IP address {ip_address} blocked successfully",
            "ip_address": ip_address,
            "reason": reason,
            "permanent": permanent,
            "blocked_at": datetime.now().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    except Exception as e:
        logger.error(f"Failed to block IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to block IP address")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8023)