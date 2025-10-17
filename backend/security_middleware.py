"""
Security Middleware for BookMyMovie Platform
JWT Authentication, Rate Limiting, Input Validation, Security Headers
"""

import jwt
import time
import redis
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator, EmailStr
from sqlalchemy.orm import Session
import bcrypt
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security Configuration
class SecurityConfig:
    JWT_SECRET_KEY = "your-super-secret-jwt-key-change-in-production-2025"
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = 100  # requests per minute
    RATE_LIMIT_WINDOW = 60     # seconds
    
    # Password requirements
    MIN_PASSWORD_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL_CHARS = True
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline';",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

# Redis connection for rate limiting and sessions
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    logger.info("Redis connected for security features")
except redis.ConnectionError:
    logger.warning("Redis not available, using in-memory rate limiting")
    redis_client = None

# In-memory storage fallback for rate limiting
rate_limit_store: Dict[str, Dict] = {}

# Pydantic models for validation
class UserRegistration(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 30:
            raise ValueError('Username must be 3-30 characters long')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < SecurityConfig.MIN_PASSWORD_LENGTH:
            raise ValueError(f'Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters long')
        
        if SecurityConfig.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if SecurityConfig.REQUIRE_LOWERCASE and not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if SecurityConfig.REQUIRE_DIGITS and not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        if SecurityConfig.REQUIRE_SPECIAL_CHARS and not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        if not re.match(r'^[a-zA-Z\s]+$', v):
            raise ValueError('Full name can only contain letters and spaces')
        return v.strip()
    
    @validator('phone')
    def validate_phone(cls, v):
        if v is None:
            return v
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', v)
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError('Phone number must be 10-15 digits long')
        return f"+{cleaned}"

class UserLogin(BaseModel):
    username: str
    password: str
    remember_me: bool = False

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class PasswordReset(BaseModel):
    email: EmailStr
    
class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        # Use same validation as UserRegistration
        return UserRegistration.validate_password(v)

# JWT Token Management
class JWTManager:
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=SecurityConfig.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, SecurityConfig.JWT_SECRET_KEY, algorithm=SecurityConfig.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=SecurityConfig.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, SecurityConfig.JWT_SECRET_KEY, algorithm=SecurityConfig.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SecurityConfig.JWT_SECRET_KEY, algorithms=[SecurityConfig.JWT_ALGORITHM])
            
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}"
                )
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

# Password Security
class PasswordManager:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def generate_password_reset_token() -> str:
        """Generate secure password reset token"""
        return secrets.token_urlsafe(32)

# Rate Limiting
class RateLimiter:
    @staticmethod
    def get_client_id(request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from token first
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = JWTManager.verify_token(token)
                return f"user:{payload.get('sub')}"
            except:
                pass
        
        # Fallback to IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return f"ip:{forwarded_for.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    @staticmethod
    def is_rate_limited(client_id: str, endpoint: str = "default") -> bool:
        """Check if client is rate limited"""
        key = f"rate_limit:{endpoint}:{client_id}"
        current_time = int(time.time())
        window_start = current_time - SecurityConfig.RATE_LIMIT_WINDOW
        
        if redis_client:
            try:
                # Use Redis for distributed rate limiting
                pipe = redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                pipe.zadd(key, {str(current_time): current_time})
                pipe.expire(key, SecurityConfig.RATE_LIMIT_WINDOW)
                results = pipe.execute()
                
                request_count = results[1]
                return request_count >= SecurityConfig.RATE_LIMIT_REQUESTS
                
            except Exception as e:
                logger.error(f"Redis rate limiting error: {e}")
                # Fall back to in-memory rate limiting
        
        # In-memory rate limiting fallback
        if key not in rate_limit_store:
            rate_limit_store[key] = []
        
        # Clean old requests
        rate_limit_store[key] = [
            req_time for req_time in rate_limit_store[key] 
            if req_time > window_start
        ]
        
        # Add current request
        rate_limit_store[key].append(current_time)
        
        return len(rate_limit_store[key]) > SecurityConfig.RATE_LIMIT_REQUESTS

# Security Middleware
class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Check rate limiting
            client_id = RateLimiter.get_client_id(request)
            endpoint = scope["path"]
            
            if RateLimiter.is_rate_limited(client_id, endpoint):
                response = {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"retry-after", str(SecurityConfig.RATE_LIMIT_WINDOW).encode()]
                    ]
                }
                await send(response)
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail":"Rate limit exceeded. Too many requests."}'
                })
                return
        
        await self.app(scope, receive, send)

# Authentication Dependencies
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    try:
        payload = JWTManager.verify_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        return {"id": int(user_id), "username": payload.get("username")}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )

async def get_current_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to ensure current user is admin"""
    # This would typically check admin status in database
    # For demo, assume user_id 1 is admin
    if current_user["id"] != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# Input Sanitization
class InputSanitizer:
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""
        
        # Remove potential XSS characters
        sanitized = re.sub(r'[<>"\']', '', value.strip())
        
        # Limit length
        return sanitized[:max_length]
    
    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """Sanitize input for SQL (though we use SQLAlchemy ORM)"""
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
        sanitized = value
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        return sanitized
    
    @staticmethod
    def validate_file_upload(filename: str, allowed_extensions: List[str]) -> bool:
        """Validate file upload"""
        if not filename:
            return False
        
        # Check extension
        extension = filename.lower().split('.')[-1]
        if extension not in allowed_extensions:
            return False
        
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        return True

# Security Headers Middleware
def add_security_headers(response):
    """Add security headers to response"""
    for header, value in SecurityConfig.SECURITY_HEADERS.items():
        response.headers[header] = value
    return response

# Audit Logging
class SecurityAuditLogger:
    @staticmethod
    def log_authentication_attempt(username: str, success: bool, ip_address: str, user_agent: str = None):
        """Log authentication attempts"""
        logger.info(f"Auth attempt - User: {username}, Success: {success}, IP: {ip_address}, UA: {user_agent}")
        
        # Store in Redis or database for monitoring
        if redis_client:
            try:
                audit_key = f"audit:auth:{username}:{int(time.time())}"
                audit_data = {
                    "username": username,
                    "success": success,
                    "ip_address": ip_address,
                    "user_agent": user_agent or "unknown",
                    "timestamp": datetime.utcnow().isoformat()
                }
                redis_client.setex(audit_key, 86400, str(audit_data))  # 24 hours
            except Exception as e:
                logger.error(f"Failed to store audit log: {e}")
    
    @staticmethod
    def log_security_event(event_type: str, user_id: int = None, details: str = None, ip_address: str = None):
        """Log security events"""
        logger.warning(f"Security event - Type: {event_type}, User: {user_id}, Details: {details}, IP: {ip_address}")
        
        if redis_client:
            try:
                event_key = f"audit:security:{event_type}:{int(time.time())}"
                event_data = {
                    "event_type": event_type,
                    "user_id": user_id,
                    "details": details or "",
                    "ip_address": ip_address or "unknown",
                    "timestamp": datetime.utcnow().isoformat()
                }
                redis_client.setex(event_key, 86400 * 7, str(event_data))  # 7 days
            except Exception as e:
                logger.error(f"Failed to store security event: {e}")

# Session Management
class SessionManager:
    @staticmethod
    def create_session(user_id: int, ip_address: str, user_agent: str) -> str:
        """Create user session"""
        session_id = secrets.token_urlsafe(32)
        
        if redis_client:
            try:
                session_key = f"session:{session_id}"
                session_data = {
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "created_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat()
                }
                redis_client.setex(session_key, 3600, str(session_data))  # 1 hour
                return session_id
            except Exception as e:
                logger.error(f"Failed to create session: {e}")
        
        return session_id
    
    @staticmethod
    def validate_session(session_id: str, ip_address: str) -> Optional[Dict]:
        """Validate user session"""
        if not redis_client:
            return None
        
        try:
            session_key = f"session:{session_id}"
            session_data = redis_client.get(session_key)
            
            if not session_data:
                return None
            
            session_info = eval(session_data)  # In production, use proper JSON
            
            # Check IP address (optional security measure)
            if session_info.get("ip_address") != ip_address:
                SecurityAuditLogger.log_security_event(
                    "session_ip_mismatch", 
                    session_info.get("user_id"),
                    f"Expected: {session_info.get('ip_address')}, Got: {ip_address}",
                    ip_address
                )
                return None
            
            # Update last activity
            session_info["last_activity"] = datetime.utcnow().isoformat()
            redis_client.setex(session_key, 3600, str(session_info))
            
            return session_info
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    @staticmethod
    def invalidate_session(session_id: str):
        """Invalidate user session"""
        if redis_client:
            try:
                session_key = f"session:{session_id}"
                redis_client.delete(session_key)
            except Exception as e:
                logger.error(f"Failed to invalidate session: {e}")

# Security decorators
def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # In a real application, check user permissions from database
            # For demo, assume all authenticated users have basic permissions
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def log_security_event(event_type: str):
    """Decorator to log security events"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                SecurityAuditLogger.log_security_event(event_type, details=f"Success: {func.__name__}")
                return result
            except Exception as e:
                SecurityAuditLogger.log_security_event(
                    event_type, 
                    details=f"Failed: {func.__name__} - {str(e)}"
                )
                raise
        return wrapper
    return decorator

# Health check for security features
def get_security_health() -> Dict[str, Any]:
    """Get security system health status"""
    health_status = {
        "redis_available": redis_client is not None,
        "jwt_configured": bool(SecurityConfig.JWT_SECRET_KEY),
        "rate_limiting_active": True,
        "security_headers_enabled": True,
        "audit_logging_active": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if redis_client:
        try:
            redis_client.ping()
            health_status["redis_status"] = "connected"
        except:
            health_status["redis_status"] = "disconnected"
            health_status["redis_available"] = False
    
    return health_status

# Export all security components
__all__ = [
    'SecurityConfig', 'JWTManager', 'PasswordManager', 'RateLimiter',
    'SecurityMiddleware', 'InputSanitizer', 'SecurityAuditLogger',
    'SessionManager', 'get_current_user', 'get_current_admin',
    'add_security_headers', 'require_permission', 'log_security_event',
    'get_security_health', 'UserRegistration', 'UserLogin', 'TokenResponse',
    'PasswordReset', 'PasswordChange'
]