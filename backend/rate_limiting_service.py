"""
API Rate Limiting and Throttling Service
Advanced rate limiting with multiple strategies and DDoS protection
"""

import asyncio
import time
import hashlib
import logging
from typing import Dict, Optional, List, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
from functools import wraps
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import ipaddress

logger = logging.getLogger(__name__)

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    requests: int          # Number of requests allowed
    period: int           # Time period in seconds
    burst: int = 0        # Burst allowance (0 = no burst)
    block_duration: int = 300  # Block duration in seconds when exceeded

@dataclass
class ClientInfo:
    """Client request tracking information"""
    ip_address: str
    user_id: Optional[str] = None
    api_key: Optional[str] = None
    user_agent: str = ""
    first_request: float = 0.0
    last_request: float = 0.0
    request_count: int = 0
    blocked_until: float = 0.0
    risk_score: float = 0.0

class TokenBucket:
    """Token bucket algorithm implementation"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens, return True if allowed"""
        now = time.time()
        
        # Refill tokens based on time passed
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False

class SlidingWindowCounter:
    """Sliding window counter for rate limiting"""
    
    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
    
    def is_allowed(self) -> bool:
        """Check if request is allowed within the sliding window"""
        now = time.time()
        
        # Remove old requests outside the window
        while self.requests and self.requests[0] <= now - self.window_size:
            self.requests.popleft()
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def time_until_next_allowed(self) -> float:
        """Get time until next request is allowed"""
        if not self.requests:
            return 0.0
        
        oldest_request = self.requests[0]
        return max(0.0, oldest_request + self.window_size - time.time())

class AdaptiveRateLimiter:
    """Advanced rate limiter with multiple algorithms and DDoS protection"""
    
    def __init__(self):
        self.rules: Dict[str, RateLimitRule] = {}
        self.client_buckets: Dict[str, TokenBucket] = {}
        self.client_windows: Dict[str, SlidingWindowCounter] = {}
        self.client_info: Dict[str, ClientInfo] = {}
        self.blocked_ips: Dict[str, float] = {}  # IP -> blocked_until_timestamp
        self.whitelist: set = set()
        self.blacklist: set = set()
        
        # DDoS protection thresholds
        self.ddos_threshold = 1000  # requests per minute
        self.ddos_window = 60
        self.suspicious_patterns = {
            'rapid_requests': 100,      # requests in 10 seconds
            'identical_requests': 50,   # identical requests
            'user_agent_abuse': 20      # requests with suspicious user agents
        }
        
        # Default rate limit rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules"""
        self.rules = {
            'anonymous': RateLimitRule('anonymous', 100, 3600, 10, 300),      # 100/hour for anonymous
            'authenticated': RateLimitRule('authenticated', 1000, 3600, 50, 300),  # 1000/hour for authenticated
            'premium': RateLimitRule('premium', 5000, 3600, 100, 180),        # 5000/hour for premium
            'api_key': RateLimitRule('api_key', 10000, 3600, 200, 300),       # 10k/hour for API keys
            'search': RateLimitRule('search', 50, 300, 5, 600),               # 50 searches per 5 min
            'booking': RateLimitRule('booking', 10, 600, 2, 1800),            # 10 bookings per 10 min
            'upload': RateLimitRule('upload', 5, 300, 1, 900),                # 5 uploads per 5 min
        }
    
    def add_to_whitelist(self, ip_or_network: str):
        """Add IP or network to whitelist"""
        try:
            network = ipaddress.ip_network(ip_or_network, strict=False)
            self.whitelist.add(network)
            logger.info(f"Added {ip_or_network} to whitelist")
        except ValueError as e:
            logger.error(f"Invalid IP/network for whitelist: {e}")
    
    def add_to_blacklist(self, ip_or_network: str):
        """Add IP or network to blacklist"""
        try:
            network = ipaddress.ip_network(ip_or_network, strict=False)
            self.blacklist.add(network)
            logger.info(f"Added {ip_or_network} to blacklist")
        except ValueError as e:
            logger.error(f"Invalid IP/network for blacklist: {e}")
    
    def _is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            return any(ip_addr in network for network in self.whitelist)
        except ValueError:
            return False
    
    def _is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            return any(ip_addr in network for network in self.blacklist)
        except ValueError:
            return False
    
    def _get_client_key(self, request: Request) -> str:
        """Generate unique client identifier"""
        ip = self._get_client_ip(request)
        user_id = getattr(request.state, 'user_id', None)
        api_key = request.headers.get('X-API-Key')
        
        if api_key:
            return f"api:{hashlib.md5(api_key.encode()).hexdigest()}"
        elif user_id:
            return f"user:{user_id}"
        else:
            return f"ip:{ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address with proxy support"""
        # Check for forwarded headers (reverse proxy support)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown'
    
    def _determine_rule_category(self, request: Request) -> str:
        """Determine which rate limit rule to apply"""
        api_key = request.headers.get('X-API-Key')
        user_id = getattr(request.state, 'user_id', None)
        user_tier = getattr(request.state, 'user_tier', 'basic')
        
        # Endpoint-specific rules
        path = request.url.path
        if '/search' in path:
            return 'search'
        elif '/booking' in path:
            return 'booking'
        elif '/upload' in path:
            return 'upload'
        
        # User-based rules
        if api_key:
            return 'api_key'
        elif user_id:
            return 'premium' if user_tier in ['premium', 'enterprise'] else 'authenticated'
        else:
            return 'anonymous'
    
    def _calculate_risk_score(self, client_info: ClientInfo, request: Request) -> float:
        """Calculate risk score for DDoS detection"""
        risk_score = 0.0
        now = time.time()
        
        # Rapid request pattern
        if client_info.request_count > self.suspicious_patterns['rapid_requests']:
            time_window = now - client_info.first_request
            if time_window < 10:  # 100 requests in 10 seconds
                risk_score += 0.3
        
        # Suspicious User-Agent patterns
        user_agent = request.headers.get('User-Agent', '').lower()
        suspicious_agents = ['bot', 'crawler', 'scraper', 'automated', 'python-requests']
        if any(agent in user_agent for agent in suspicious_agents):
            risk_score += 0.2
        
        # Missing common headers
        if not request.headers.get('Accept'):
            risk_score += 0.1
        if not request.headers.get('Accept-Language'):
            risk_score += 0.1
        
        # Repeated identical requests
        request_hash = hashlib.md5(f"{request.method}{request.url.path}{request.url.query}".encode()).hexdigest()
        if not hasattr(client_info, 'request_hashes'):
            client_info.request_hashes = defaultdict(int)
        
        client_info.request_hashes[request_hash] += 1
        if client_info.request_hashes[request_hash] > self.suspicious_patterns['identical_requests']:
            risk_score += 0.4
        
        return min(risk_score, 1.0)  # Cap at 1.0
    
    async def is_allowed(self, request: Request) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed and return detailed info"""
        client_ip = self._get_client_ip(request)
        now = time.time()
        
        # Check blacklist
        if self._is_blacklisted(client_ip):
            logger.warning(f"Blocked blacklisted IP: {client_ip}")
            return False, {
                'reason': 'blacklisted',
                'retry_after': None,
                'blocked_until': None
            }
        
        # Check whitelist (always allow)
        if self._is_whitelisted(client_ip):
            return True, {'reason': 'whitelisted'}
        
        # Check if IP is currently blocked
        if client_ip in self.blocked_ips:
            if now < self.blocked_ips[client_ip]:
                remaining_time = self.blocked_ips[client_ip] - now
                return False, {
                    'reason': 'temporarily_blocked',
                    'retry_after': int(remaining_time),
                    'blocked_until': self.blocked_ips[client_ip]
                }
            else:
                # Unblock expired blocks
                del self.blocked_ips[client_ip]
        
        # Get client information
        client_key = self._get_client_key(request)
        
        if client_key not in self.client_info:
            self.client_info[client_key] = ClientInfo(
                ip_address=client_ip,
                user_id=getattr(request.state, 'user_id', None),
                api_key=request.headers.get('X-API-Key'),
                user_agent=request.headers.get('User-Agent', ''),
                first_request=now
            )
        
        client_info = self.client_info[client_key]
        client_info.last_request = now
        client_info.request_count += 1
        
        # Calculate risk score
        client_info.risk_score = self._calculate_risk_score(client_info, request)
        
        # DDoS protection - block high-risk clients
        if client_info.risk_score > 0.8:
            block_duration = 3600  # 1 hour for high-risk clients
            self.blocked_ips[client_ip] = now + block_duration
            logger.warning(f"Blocked high-risk IP {client_ip} for {block_duration}s, risk score: {client_info.risk_score}")
            return False, {
                'reason': 'high_risk_detected',
                'retry_after': block_duration,
                'blocked_until': now + block_duration,
                'risk_score': client_info.risk_score
            }
        
        # Determine rate limit rule
        rule_category = self._determine_rule_category(request)
        rule = self.rules.get(rule_category)
        
        if not rule:
            logger.warning(f"No rate limit rule found for category: {rule_category}")
            return True, {'reason': 'no_rule'}
        
        # Check token bucket
        if client_key not in self.client_buckets:
            self.client_buckets[client_key] = TokenBucket(rule.requests, rule.requests / rule.period)
        
        bucket = self.client_buckets[client_key]
        
        # Check sliding window
        if client_key not in self.client_windows:
            self.client_windows[client_key] = SlidingWindowCounter(rule.period, rule.requests)
        
        window = self.client_windows[client_key]
        
        # Apply rate limiting (use sliding window as primary, bucket for burst)
        if not window.is_allowed():
            # Check if we can use burst capacity
            if rule.burst > 0 and bucket.consume():
                logger.info(f"Burst capacity used for {client_key}")
                return True, {'reason': 'burst_allowed', 'rule': rule_category}
            
            # Rate limit exceeded
            retry_after = int(window.time_until_next_allowed())
            
            # Temporary block for repeated violations
            if client_info.request_count > rule.requests * 2:
                self.blocked_ips[client_ip] = now + rule.block_duration
                logger.warning(f"Blocked IP {client_ip} for {rule.block_duration}s due to rate limit violations")
                return False, {
                    'reason': 'rate_limit_exceeded_blocked',
                    'retry_after': rule.block_duration,
                    'blocked_until': now + rule.block_duration,
                    'rule': rule_category
                }
            
            return False, {
                'reason': 'rate_limit_exceeded',
                'retry_after': retry_after,
                'rule': rule_category,
                'limit': rule.requests,
                'period': rule.period
            }
        
        return True, {
            'reason': 'allowed',
            'rule': rule_category,
            'remaining': rule.requests - len(window.requests),
            'reset_time': int(now + rule.period)
        }
    
    def get_client_stats(self, request: Request) -> Dict[str, Any]:
        """Get statistics for a client"""
        client_key = self._get_client_key(request)
        client_info = self.client_info.get(client_key)
        
        if not client_info:
            return {'error': 'Client not found'}
        
        return {
            'client_key': client_key,
            'ip_address': client_info.ip_address,
            'request_count': client_info.request_count,
            'risk_score': client_info.risk_score,
            'first_request': client_info.first_request,
            'last_request': client_info.last_request,
            'is_blocked': client_info.ip_address in self.blocked_ips
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics"""
        now = time.time()
        
        # Clean up expired blocks
        expired_blocks = [ip for ip, until in self.blocked_ips.items() if until < now]
        for ip in expired_blocks:
            del self.blocked_ips[ip]
        
        return {
            'total_clients': len(self.client_info),
            'blocked_ips': len(self.blocked_ips),
            'rules': {name: asdict(rule) for name, rule in self.rules.items()},
            'whitelist_count': len(self.whitelist),
            'blacklist_count': len(self.blacklist),
            'high_risk_clients': sum(1 for client in self.client_info.values() if client.risk_score > 0.5)
        }

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, rate_limiter: AdaptiveRateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and static files
        if request.url.path in ['/health', '/metrics'] or request.url.path.startswith('/static'):
            return await call_next(request)
        
        # Check rate limit
        is_allowed, info = await self.rate_limiter.is_allowed(request)
        
        if not is_allowed:
            # Add rate limit headers
            headers = {
                'X-RateLimit-Limit': str(info.get('limit', 0)),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(info.get('reset_time', 0)),
            }
            
            if 'retry_after' in info and info['retry_after']:
                headers['Retry-After'] = str(info['retry_after'])
            
            # Determine status code based on reason
            if info['reason'] in ['blacklisted', 'high_risk_detected']:
                status_code = status.HTTP_403_FORBIDDEN
                message = "Access forbidden"
            else:
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
                message = "Rate limit exceeded"
            
            raise HTTPException(
                status_code=status_code,
                detail={
                    'error': message,
                    'reason': info['reason'],
                    'retry_after': info.get('retry_after'),
                },
                headers=headers
            )
        
        # Add success headers
        response = await call_next(request)
        response.headers['X-RateLimit-Rule'] = info.get('rule', 'unknown')
        response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', 0))
        
        return response

# Rate limiting decorators
def rate_limit(rule_name: str = None, requests: int = None, period: int = None):
    """Decorator for function-level rate limiting"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # This would integrate with the global rate limiter
            # For now, just pass through
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Global rate limiter instance
global_rate_limiter = AdaptiveRateLimiter()

# Utility functions
def init_rate_limiter(custom_rules: Dict[str, RateLimitRule] = None):
    """Initialize rate limiter with custom rules"""
    if custom_rules:
        global_rate_limiter.rules.update(custom_rules)
    
    # Add common IP ranges to whitelist (internal networks)
    global_rate_limiter.add_to_whitelist('127.0.0.0/8')    # localhost
    global_rate_limiter.add_to_whitelist('10.0.0.0/8')     # private network
    global_rate_limiter.add_to_whitelist('172.16.0.0/12')  # private network
    global_rate_limiter.add_to_whitelist('192.168.0.0/16') # private network
    
    logger.info("Rate limiter initialized with default configuration")