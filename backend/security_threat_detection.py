"""
Advanced Threat Detection and Security Monitoring System
Enterprise-grade security with real-time threat detection and monitoring
"""

import asyncio
import logging
import json
import hashlib
import hmac
import ipaddress
import re
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor
import sqlite3

# Security libraries
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

# Rate limiting and pattern detection
from collections import Counter
import geoip2.database
import geoip2.errors

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Security event structure"""
    event_id: str
    event_type: str  # 'authentication', 'authorization', 'suspicious_activity', 'data_access'
    severity: str  # 'low', 'medium', 'high', 'critical'
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    endpoint: str
    method: str
    timestamp: datetime
    details: Dict[str, Any]
    geo_location: Optional[Dict[str, str]] = None
    risk_score: float = 0.0
    blocked: bool = False

@dataclass
class ThreatIndicator:
    """Threat indicator for pattern matching"""
    indicator_type: str  # 'ip', 'user_agent', 'pattern', 'behavioral'
    value: str
    severity: str
    description: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True

@dataclass
class SecurityAlert:
    """Security alert structure"""
    alert_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    affected_resources: List[str]
    indicators: List[ThreatIndicator]
    recommendations: List[str]
    created_at: datetime
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class RiskAssessment:
    """Risk assessment result"""
    user_id: str
    ip_address: str
    risk_score: float
    risk_factors: List[Dict[str, Any]]
    recommended_actions: List[str]
    requires_additional_verification: bool
    assessment_timestamp: datetime

class ThreatDetectionEngine:
    """Advanced threat detection engine"""
    
    def __init__(self):
        # Threat indicators database
        self.threat_indicators = {}
        self.behavioral_patterns = defaultdict(deque)
        
        # IP reputation and geolocation
        self.ip_reputation = {}
        self.geo_db = None
        
        # Attack pattern signatures
        self.attack_signatures = {
            'sql_injection': [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b.*\b(FROM|INTO|WHERE|SET)\b)",
                r"(UNION.*SELECT|' OR '1'='1)",
                r"(\bOR\b.*=.*\bOR\b|\bAND\b.*=.*\bAND\b)",
            ],
            'xss': [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"onload\s*=",
                r"onerror\s*=",
            ],
            'path_traversal': [
                r"\.\.\/",
                r"\.\.\\",
                r"\/etc\/passwd",
                r"\/windows\/system32",
            ],
            'command_injection': [
                r";\s*(cat|ls|pwd|whoami|id)\b",
                r"\|\s*(cat|ls|pwd|whoami|id)\b",
                r"&&\s*(cat|ls|pwd|whoami|id)\b",
            ]
        }
        
        # Suspicious user agents
        self.suspicious_agents = {
            'bot_indicators': [
                'bot', 'crawler', 'spider', 'scraper', 'scanner',
                'curl', 'wget', 'python-requests', 'go-http-client'
            ],
            'security_tools': [
                'nmap', 'masscan', 'zap', 'burp', 'sqlmap',
                'nikto', 'dirb', 'gobuster', 'wfuzz'
            ]
        }
        
        # Rate limiting windows
        self.rate_windows = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '1h': timedelta(hours=1),
            '24h': timedelta(hours=24)
        }
        
        # Behavioral analysis
        self.user_behavior = defaultdict(lambda: {
            'login_times': deque(maxlen=100),
            'ip_addresses': deque(maxlen=20),
            'user_agents': deque(maxlen=10),
            'endpoints': deque(maxlen=100),
            'failed_attempts': deque(maxlen=50)
        })
        
        # Initialize GeoIP database if available
        self._init_geoip()
    
    def _init_geoip(self):
        """Initialize GeoIP database"""
        try:
            # In production, you would have a GeoLite2 database
            # self.geo_db = geoip2.database.Reader('GeoLite2-City.mmdb')
            logger.info("GeoIP database would be initialized here")
        except Exception as e:
            logger.warning(f"GeoIP database not available: {e}")
    
    def detect_threats(self, request_data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect threats in incoming request"""
        
        threats = []
        
        # Extract request details
        url = request_data.get('url', '')
        method = request_data.get('method', '')
        headers = request_data.get('headers', {})
        body = request_data.get('body', '')
        ip_address = request_data.get('ip_address', '')
        user_agent = headers.get('User-Agent', '')
        
        # Check for attack patterns in URL and body
        combined_data = f"{url} {body}"
        
        for attack_type, patterns in self.attack_signatures.items():
            for pattern in patterns:
                if re.search(pattern, combined_data, re.IGNORECASE):
                    threat = ThreatIndicator(
                        indicator_type='pattern',
                        value=pattern,
                        severity='high',
                        description=f"Potential {attack_type} attack detected",
                        created_at=datetime.now()
                    )
                    threats.append(threat)
        
        # Check suspicious user agents
        if user_agent:
            for category, indicators in self.suspicious_agents.items():
                for indicator in indicators:
                    if indicator.lower() in user_agent.lower():
                        threat = ThreatIndicator(
                            indicator_type='user_agent',
                            value=user_agent,
                            severity='medium',
                            description=f"Suspicious user agent: {category}",
                            created_at=datetime.now()
                        )
                        threats.append(threat)
        
        # Check IP reputation
        if ip_address in self.ip_reputation:
            reputation = self.ip_reputation[ip_address]
            if reputation['risk_level'] == 'high':
                threat = ThreatIndicator(
                    indicator_type='ip',
                    value=ip_address,
                    severity='high',
                    description=f"High-risk IP address: {reputation['reason']}",
                    created_at=datetime.now()
                )
                threats.append(threat)
        
        return threats
    
    def analyze_behavioral_anomalies(self, user_id: str, request_data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Analyze behavioral anomalies for user"""
        
        anomalies = []
        
        if not user_id:
            return anomalies
        
        user_behavior = self.user_behavior[user_id]
        current_time = datetime.now()
        ip_address = request_data.get('ip_address', '')
        user_agent = request_data.get('headers', {}).get('User-Agent', '')
        endpoint = request_data.get('url', '')
        
        # Analyze login time patterns
        user_behavior['login_times'].append(current_time.hour)
        if len(user_behavior['login_times']) >= 10:
            # Check for unusual login times
            common_hours = Counter(user_behavior['login_times']).most_common(3)
            if current_time.hour not in [hour for hour, _ in common_hours]:
                # Login at unusual time
                if all(abs(current_time.hour - hour) > 6 for hour, _ in common_hours):
                    anomaly = ThreatIndicator(
                        indicator_type='behavioral',
                        value=f"unusual_login_time_{current_time.hour}",
                        severity='medium',
                        description=f"Login at unusual time: {current_time.hour}:00",
                        created_at=datetime.now()
                    )
                    anomalies.append(anomaly)
        
        # Analyze IP address patterns
        user_behavior['ip_addresses'].append(ip_address)
        if len(user_behavior['ip_addresses']) >= 5:
            unique_ips = set(user_behavior['ip_addresses'])
            if len(unique_ips) > 3:  # Multiple IPs in short time
                anomaly = ThreatIndicator(
                    indicator_type='behavioral',
                    value=f"multiple_ips_{len(unique_ips)}",
                    severity='high',
                    description=f"Multiple IP addresses used: {len(unique_ips)} in recent activity",
                    created_at=datetime.now()
                )
                anomalies.append(anomaly)
        
        # Analyze geographic anomalies (if GeoIP available)
        if self.geo_db and ip_address:
            try:
                # Would implement geo-location analysis here
                pass
            except Exception as e:
                logger.debug(f"Geo-location analysis failed: {e}")
        
        # Analyze user agent consistency
        user_behavior['user_agents'].append(user_agent)
        if len(user_behavior['user_agents']) >= 5:
            unique_agents = set(filter(None, user_behavior['user_agents']))
            if len(unique_agents) > 2:  # Multiple user agents
                anomaly = ThreatIndicator(
                    indicator_type='behavioral',
                    value=f"multiple_user_agents_{len(unique_agents)}",
                    severity='medium',
                    description=f"Multiple user agents detected: {len(unique_agents)}",
                    created_at=datetime.now()
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    def check_rate_limits(self, user_id: Optional[str], ip_address: str, endpoint: str) -> Optional[ThreatIndicator]:
        """Check if request exceeds rate limits"""
        
        current_time = datetime.now()
        
        # Define rate limits per endpoint category
        rate_limits = {
            'auth': {'1m': 5, '5m': 10, '1h': 50},
            'api': {'1m': 100, '5m': 300, '1h': 1000},
            'default': {'1m': 30, '5m': 100, '1h': 500}
        }
        
        # Categorize endpoint
        if any(auth_path in endpoint for auth_path in ['/login', '/register', '/reset']):
            category = 'auth'
        elif '/api/' in endpoint:
            category = 'api'
        else:
            category = 'default'
        
        # Check rates for both user and IP
        identifiers = []
        if user_id:
            identifiers.append(f"user_{user_id}")
        identifiers.append(f"ip_{ip_address}")
        
        for identifier in identifiers:
            # Initialize tracking if needed
            if identifier not in self.behavioral_patterns:
                self.behavioral_patterns[identifier] = deque(maxlen=1000)
            
            # Add current request
            self.behavioral_patterns[identifier].append(current_time)
            
            # Check rate limits
            for window_name, window_duration in self.rate_windows.items():
                if window_name not in rate_limits[category]:
                    continue
                
                limit = rate_limits[category][window_name]
                cutoff_time = current_time - window_duration
                
                # Count requests in window
                recent_requests = [
                    req_time for req_time in self.behavioral_patterns[identifier]
                    if req_time > cutoff_time
                ]
                
                if len(recent_requests) > limit:
                    return ThreatIndicator(
                        indicator_type='rate_limit',
                        value=f"{identifier}_{endpoint}",
                        severity='high',
                        description=f"Rate limit exceeded: {len(recent_requests)} requests in {window_name} (limit: {limit})",
                        created_at=datetime.now()
                    )
        
        return None
    
    def assess_risk_score(self, threats: List[ThreatIndicator], user_id: Optional[str], 
                         request_data: Dict[str, Any]) -> float:
        """Calculate overall risk score"""
        
        base_score = 0.0
        
        # Score based on threat indicators
        severity_scores = {'low': 10, 'medium': 25, 'high': 50, 'critical': 100}
        
        for threat in threats:
            base_score += severity_scores.get(threat.severity, 0)
        
        # Additional factors
        ip_address = request_data.get('ip_address', '')
        
        # New user factor
        if not user_id or user_id not in self.user_behavior:
            base_score += 15  # New users are slightly more risky
        
        # IP reputation factor
        if ip_address in self.ip_reputation:
            reputation = self.ip_reputation[ip_address]
            if reputation['risk_level'] == 'high':
                base_score += 30
            elif reputation['risk_level'] == 'medium':
                base_score += 15
        
        # Time-based factors
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 23:  # Late night/early morning
            base_score += 5
        
        # Normalize to 0-100 scale
        risk_score = min(100.0, base_score)
        
        return risk_score
    
    def update_ip_reputation(self, ip_address: str, reputation_data: Dict[str, Any]):
        """Update IP reputation information"""
        
        self.ip_reputation[ip_address] = {
            'risk_level': reputation_data.get('risk_level', 'low'),
            'reason': reputation_data.get('reason', ''),
            'last_updated': datetime.now(),
            'source': reputation_data.get('source', 'manual')
        }
    
    def add_threat_indicator(self, indicator: ThreatIndicator):
        """Add new threat indicator"""
        
        key = f"{indicator.indicator_type}_{indicator.value}"
        self.threat_indicators[key] = indicator

class SecurityAuditLogger:
    """Comprehensive security audit logging"""
    
    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = log_file
        self.db_path = "security_audit.db"
        self._init_database()
        
        # Setup file logging
        self.audit_logger = logging.getLogger('security_audit')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)
    
    def _init_database(self):
        """Initialize audit database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Security events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT,
                severity TEXT,
                user_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                endpoint TEXT,
                method TEXT,
                timestamp TEXT,
                details TEXT,
                geo_location TEXT,
                risk_score REAL,
                blocked INTEGER
            )
        """)
        
        # Security alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_alerts (
                alert_id TEXT PRIMARY KEY,
                alert_type TEXT,
                severity TEXT,
                title TEXT,
                description TEXT,
                affected_resources TEXT,
                indicators TEXT,
                recommendations TEXT,
                created_at TEXT,
                acknowledged INTEGER,
                resolved INTEGER
            )
        """)
        
        # Compliance logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_logs (
                log_id TEXT PRIMARY KEY,
                compliance_type TEXT,
                action TEXT,
                user_id TEXT,
                data_type TEXT,
                details TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_security_event(self, event: SecurityEvent):
        """Log security event"""
        
        try:
            # Database logging
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_events 
                (event_id, event_type, severity, user_id, ip_address, user_agent, 
                 endpoint, method, timestamp, details, geo_location, risk_score, blocked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.event_type,
                event.severity,
                event.user_id,
                event.ip_address,
                event.user_agent,
                event.endpoint,
                event.method,
                event.timestamp.isoformat(),
                json.dumps(event.details),
                json.dumps(event.geo_location) if event.geo_location else None,
                event.risk_score,
                int(event.blocked)
            ))
            
            conn.commit()
            conn.close()
            
            # File logging
            log_message = (
                f"SecurityEvent: {event.event_type} | "
                f"Severity: {event.severity} | "
                f"User: {event.user_id or 'anonymous'} | "
                f"IP: {event.ip_address} | "
                f"Endpoint: {event.endpoint} | "
                f"Risk: {event.risk_score:.2f} | "
                f"Blocked: {event.blocked}"
            )
            
            if event.severity in ['high', 'critical']:
                self.audit_logger.error(log_message)
            elif event.severity == 'medium':
                self.audit_logger.warning(log_message)
            else:
                self.audit_logger.info(log_message)
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def log_security_alert(self, alert: SecurityAlert):
        """Log security alert"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_alerts 
                (alert_id, alert_type, severity, title, description, affected_resources,
                 indicators, recommendations, created_at, acknowledged, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.alert_type,
                alert.severity,
                alert.title,
                alert.description,
                json.dumps(alert.affected_resources),
                json.dumps([asdict(indicator) for indicator in alert.indicators], default=str),
                json.dumps(alert.recommendations),
                alert.created_at.isoformat(),
                int(alert.acknowledged),
                int(alert.resolved)
            ))
            
            conn.commit()
            conn.close()
            
            # File logging
            self.audit_logger.critical(
                f"SecurityAlert: {alert.title} | "
                f"Type: {alert.alert_type} | "
                f"Severity: {alert.severity} | "
                f"Resources: {len(alert.affected_resources)}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log security alert: {e}")
    
    def log_compliance_event(self, compliance_type: str, action: str, user_id: str,
                           data_type: str, details: Dict[str, Any]):
        """Log compliance-related event (GDPR, PCI DSS, etc.)"""
        
        try:
            log_id = hashlib.sha256(
                f"{compliance_type}_{action}_{user_id}_{datetime.now()}".encode()
            ).hexdigest()[:16]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO compliance_logs 
                (log_id, compliance_type, action, user_id, data_type, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                compliance_type,
                action,
                user_id,
                data_type,
                json.dumps(details),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # File logging
            self.audit_logger.info(
                f"ComplianceEvent: {compliance_type} | "
                f"Action: {action} | "
                f"User: {user_id} | "
                f"DataType: {data_type}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log compliance event: {e}")
    
    def get_security_events(self, start_date: datetime = None, end_date: datetime = None,
                          severity: str = None, event_type: str = None) -> List[SecurityEvent]:
        """Retrieve security events with filters"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM security_events WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            query += " ORDER BY timestamp DESC LIMIT 1000"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            events = []
            for row in rows:
                event = SecurityEvent(
                    event_id=row[0],
                    event_type=row[1],
                    severity=row[2],
                    user_id=row[3],
                    ip_address=row[4],
                    user_agent=row[5],
                    endpoint=row[6],
                    method=row[7],
                    timestamp=datetime.fromisoformat(row[8]),
                    details=json.loads(row[9]) if row[9] else {},
                    geo_location=json.loads(row[10]) if row[10] else None,
                    risk_score=row[11],
                    blocked=bool(row[12])
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to retrieve security events: {e}")
            return []

class VulnerabilityScanner:
    """Automated vulnerability scanning"""
    
    def __init__(self):
        self.scan_results = {}
        self.vulnerability_database = {}
        self._load_vulnerability_patterns()
    
    def _load_vulnerability_patterns(self):
        """Load known vulnerability patterns"""
        
        # Common web vulnerabilities to scan for
        self.vulnerability_database = {
            'outdated_dependencies': {
                'description': 'Outdated or vulnerable dependencies',
                'severity': 'high',
                'check_method': 'dependency_check'
            },
            'weak_ssl_config': {
                'description': 'Weak SSL/TLS configuration',
                'severity': 'medium',
                'check_method': 'ssl_check'
            },
            'exposed_debug_info': {
                'description': 'Debug information exposed in production',
                'severity': 'medium',
                'check_method': 'debug_check'
            },
            'missing_security_headers': {
                'description': 'Missing security headers',
                'severity': 'medium',
                'check_method': 'header_check'
            },
            'weak_authentication': {
                'description': 'Weak authentication mechanisms',
                'severity': 'high',
                'check_method': 'auth_check'
            }
        }
    
    async def scan_application(self, target_url: str) -> Dict[str, Any]:
        """Perform comprehensive vulnerability scan"""
        
        scan_id = hashlib.sha256(f"{target_url}_{datetime.now()}".encode()).hexdigest()[:12]
        
        scan_results = {
            'scan_id': scan_id,
            'target_url': target_url,
            'scan_timestamp': datetime.now().isoformat(),
            'vulnerabilities': [],
            'summary': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }
        
        # Run individual vulnerability checks
        for vuln_id, vuln_info in self.vulnerability_database.items():
            try:
                check_method = getattr(self, f"_{vuln_info['check_method']}")
                result = await check_method(target_url)
                
                if result['vulnerable']:
                    vulnerability = {
                        'id': vuln_id,
                        'title': vuln_info['description'],
                        'severity': vuln_info['severity'],
                        'details': result['details'],
                        'recommendations': result.get('recommendations', [])
                    }
                    
                    scan_results['vulnerabilities'].append(vulnerability)
                    scan_results['summary'][vuln_info['severity']] += 1
            
            except Exception as e:
                logger.error(f"Vulnerability check {vuln_id} failed: {e}")
        
        # Store scan results
        self.scan_results[scan_id] = scan_results
        
        return scan_results
    
    async def _dependency_check(self, target_url: str) -> Dict[str, Any]:
        """Check for outdated or vulnerable dependencies"""
        
        # In a real implementation, this would check package versions
        # against known vulnerability databases
        
        return {
            'vulnerable': False,
            'details': 'Dependency check simulated - would check requirements.txt against CVE database',
            'recommendations': [
                'Update all dependencies to latest versions',
                'Use dependency vulnerability scanners in CI/CD'
            ]
        }
    
    async def _ssl_check(self, target_url: str) -> Dict[str, Any]:
        """Check SSL/TLS configuration"""
        
        # Simulated SSL check
        return {
            'vulnerable': False,
            'details': 'SSL configuration appears secure',
            'recommendations': [
                'Ensure TLS 1.2+ is used',
                'Disable weak cipher suites',
                'Implement HSTS headers'
            ]
        }
    
    async def _debug_check(self, target_url: str) -> Dict[str, Any]:
        """Check for exposed debug information"""
        
        # Check for common debug endpoints/info
        debug_indicators = [
            '/debug', '/admin', '/.env', '/config',
            'traceback', 'stack trace', 'debug=true'
        ]
        
        return {
            'vulnerable': False,
            'details': 'No debug information exposed',
            'recommendations': [
                'Ensure DEBUG=False in production',
                'Remove debug endpoints',
                'Implement proper error handling'
            ]
        }
    
    async def _header_check(self, target_url: str) -> Dict[str, Any]:
        """Check for missing security headers"""
        
        required_headers = [
            'X-Frame-Options',
            'X-XSS-Protection',
            'X-Content-Type-Options',
            'Strict-Transport-Security',
            'Content-Security-Policy'
        ]
        
        return {
            'vulnerable': True,  # Assume some headers are missing for demo
            'details': f'Missing security headers: {", ".join(required_headers[:2])}',
            'recommendations': [
                'Implement all required security headers',
                'Use CSP to prevent XSS attacks',
                'Enable HSTS for HTTPS enforcement'
            ]
        }
    
    async def _auth_check(self, target_url: str) -> Dict[str, Any]:
        """Check authentication mechanisms"""
        
        return {
            'vulnerable': False,
            'details': 'Authentication mechanisms appear secure',
            'recommendations': [
                'Implement multi-factor authentication',
                'Use strong password policies',
                'Implement account lockout mechanisms'
            ]
        }

class SecurityMonitoringService:
    """Main security monitoring and threat detection service"""
    
    def __init__(self):
        self.threat_engine = ThreatDetectionEngine()
        self.audit_logger = SecurityAuditLogger()
        self.vulnerability_scanner = VulnerabilityScanner()
        
        # Monitoring configuration
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Alert thresholds
        self.alert_thresholds = {
            'high_risk_events': 5,  # Alert after 5 high-risk events in 1 hour
            'failed_logins': 10,    # Alert after 10 failed logins from same IP
            'rate_limit_violations': 3  # Alert after 3 rate limit violations
        }
        
        # Real-time metrics
        self.metrics = {
            'events_processed': 0,
            'threats_detected': 0,
            'alerts_generated': 0,
            'blocked_requests': 0
        }
        
    async def analyze_request(self, request_data: Dict[str, Any]) -> RiskAssessment:
        """Analyze incoming request for security threats"""
        
        user_id = request_data.get('user_id')
        ip_address = request_data.get('ip_address', '')
        
        # Detect threats
        threats = self.threat_engine.detect_threats(request_data)
        
        # Analyze behavioral anomalies
        behavioral_threats = self.threat_engine.analyze_behavioral_anomalies(
            user_id, request_data
        )
        threats.extend(behavioral_threats)
        
        # Check rate limits
        rate_threat = self.threat_engine.check_rate_limits(
            user_id, ip_address, request_data.get('url', '')
        )
        if rate_threat:
            threats.append(rate_threat)
        
        # Calculate risk score
        risk_score = self.threat_engine.assess_risk_score(threats, user_id, request_data)
        
        # Determine risk factors
        risk_factors = [
            {
                'type': threat.indicator_type,
                'description': threat.description,
                'severity': threat.severity,
                'value': threat.value
            }
            for threat in threats
        ]
        
        # Determine recommended actions
        recommended_actions = []
        requires_additional_verification = False
        
        if risk_score >= 70:
            recommended_actions.extend([
                'block_request',
                'trigger_security_review',
                'notify_security_team'
            ])
            requires_additional_verification = True
        elif risk_score >= 40:
            recommended_actions.extend([
                'require_additional_authentication',
                'increase_monitoring',
                'rate_limit_user'
            ])
            requires_additional_verification = True
        elif risk_score >= 20:
            recommended_actions.extend([
                'log_for_review',
                'monitor_closely'
            ])
        
        # Create risk assessment
        risk_assessment = RiskAssessment(
            user_id=user_id or 'anonymous',
            ip_address=ip_address,
            risk_score=risk_score,
            risk_factors=risk_factors,
            recommended_actions=recommended_actions,
            requires_additional_verification=requires_additional_verification,
            assessment_timestamp=datetime.now()
        )
        
        # Create and log security event
        event = SecurityEvent(
            event_id=hashlib.sha256(f"{ip_address}_{datetime.now()}".encode()).hexdigest()[:12],
            event_type='request_analysis',
            severity=self._determine_event_severity(risk_score),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=request_data.get('headers', {}).get('User-Agent', ''),
            endpoint=request_data.get('url', ''),
            method=request_data.get('method', ''),
            timestamp=datetime.now(),
            details={
                'threats_detected': len(threats),
                'risk_factors': risk_factors,
                'recommended_actions': recommended_actions
            },
            risk_score=risk_score,
            blocked=risk_score >= 70
        )
        
        self.audit_logger.log_security_event(event)
        
        # Update metrics
        self.metrics['events_processed'] += 1
        if threats:
            self.metrics['threats_detected'] += 1
        if risk_score >= 70:
            self.metrics['blocked_requests'] += 1
        
        # Check for alert conditions
        await self._check_alert_conditions(event, threats)
        
        return risk_assessment
    
    def _determine_event_severity(self, risk_score: float) -> str:
        """Determine event severity based on risk score"""
        
        if risk_score >= 80:
            return 'critical'
        elif risk_score >= 60:
            return 'high'
        elif risk_score >= 30:
            return 'medium'
        else:
            return 'low'
    
    async def _check_alert_conditions(self, event: SecurityEvent, threats: List[ThreatIndicator]):
        """Check if alert conditions are met"""
        
        # Get recent high-risk events
        recent_events = self.audit_logger.get_security_events(
            start_date=datetime.now() - timedelta(hours=1),
            severity='high'
        )
        
        # Check for alert conditions
        if len(recent_events) >= self.alert_thresholds['high_risk_events']:
            alert = SecurityAlert(
                alert_id=hashlib.sha256(f"high_risk_{datetime.now()}".encode()).hexdigest()[:12],
                alert_type='high_risk_activity',
                severity='high',
                title='High Risk Activity Detected',
                description=f'{len(recent_events)} high-risk security events in the last hour',
                affected_resources=[event.ip_address, event.endpoint],
                indicators=threats,
                recommendations=[
                    'Review security events',
                    'Consider blocking suspicious IPs',
                    'Increase monitoring levels'
                ],
                created_at=datetime.now()
            )
            
            self.audit_logger.log_security_alert(alert)
            self.metrics['alerts_generated'] += 1
    
    async def perform_security_scan(self, target_url: str) -> Dict[str, Any]:
        """Perform comprehensive security scan"""
        
        return await self.vulnerability_scanner.scan_application(target_url)
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get real-time security metrics"""
        
        return {
            **self.metrics,
            'timestamp': datetime.now().isoformat(),
            'monitoring_status': 'active' if self.monitoring_active else 'inactive'
        }
    
    def get_security_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive security dashboard data"""
        
        # Get recent events by severity
        recent_events = self.audit_logger.get_security_events(
            start_date=datetime.now() - timedelta(hours=24)
        )
        
        events_by_severity = defaultdict(int)
        events_by_type = defaultdict(int)
        top_risk_ips = Counter()
        
        for event in recent_events:
            events_by_severity[event.severity] += 1
            events_by_type[event.event_type] += 1
            if event.risk_score > 50:
                top_risk_ips[event.ip_address] += 1
        
        return {
            'metrics': self.get_security_metrics(),
            'events_by_severity': dict(events_by_severity),
            'events_by_type': dict(events_by_type),
            'top_risk_ips': dict(top_risk_ips.most_common(10)),
            'recent_high_risk_events': len([
                e for e in recent_events if e.severity in ['high', 'critical']
            ]),
            'total_events_24h': len(recent_events),
            'scan_results': list(self.vulnerability_scanner.scan_results.values())[-5:]
        }

# Global security monitoring service
security_service = SecurityMonitoringService()

# Utility functions
async def analyze_request_security(request_data: Dict[str, Any]) -> RiskAssessment:
    """Analyze request for security threats"""
    return await security_service.analyze_request(request_data)

async def perform_vulnerability_scan(target_url: str) -> Dict[str, Any]:
    """Perform vulnerability scan"""
    return await security_service.perform_security_scan(target_url)

def log_compliance_event(compliance_type: str, action: str, user_id: str, 
                        data_type: str, details: Dict[str, Any]):
    """Log compliance event"""
    security_service.audit_logger.log_compliance_event(
        compliance_type, action, user_id, data_type, details
    )

def get_security_dashboard():
    """Get security dashboard data"""
    return security_service.get_security_dashboard_data()

def update_threat_intelligence(ip_address: str, reputation_data: Dict[str, Any]):
    """Update threat intelligence"""
    security_service.threat_engine.update_ip_reputation(ip_address, reputation_data)