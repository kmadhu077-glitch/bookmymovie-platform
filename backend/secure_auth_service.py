"""
Secure Authentication Service for BookMyMovie Platform
JWT Authentication, Password Security, Rate Limiting, Input Validation
Enhanced with High-Performance Caching Layer
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import enhanced caching layer
from cache_manager import cache_manager, session_manager, rate_limiter, cache_result

# Import performance middleware
from performance_middleware import create_performance_middleware

# Import our security middleware
from security_middleware import (
    SecurityConfig, JWTManager, PasswordManager, RateLimiter,
    SecurityMiddleware, InputSanitizer, SecurityAuditLogger,
    SessionManager, get_current_user, get_current_admin,
    add_security_headers, require_permission, log_security_event,
    get_security_health, UserRegistration, UserLogin, TokenResponse,
    PasswordReset, PasswordChange
)
from models import get_db, User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BookMyMovie - Secure Authentication Service",
    description="Secure authentication with JWT, rate limiting, and input validation",
    version="4.0.0"
)

# Add performance middleware (before security for optimal processing)
app.add_middleware(create_performance_middleware(min_size=500, compression_level=6))

# Add security middleware
app.add_middleware(SecurityMiddleware)

# CORS middleware with security considerations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Total-Count", "X-Rate-Limit-Remaining"]
)

# Security models
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    token: str
    new_password: str

# Authentication endpoints
@app.post("/auth/register", response_model=Dict[str, Any])
async def register_user(
    user_data: UserRegistration,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user with comprehensive validation"""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            SecurityAuditLogger.log_security_event(
                "registration_duplicate_attempt",
                details=f"Username: {user_data.username}, Email: {user_data.email}",
                ip_address=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email already registered"
            )
        
        # Hash password
        hashed_password = PasswordManager.hash_password(user_data.password)
        
        # Create user
        new_user = User(
            username=InputSanitizer.sanitize_string(user_data.username),
            email=user_data.email,  # Already validated by Pydantic
            password_hash=hashed_password,
            full_name=InputSanitizer.sanitize_string(user_data.full_name),
            phone_number=user_data.phone,
            created_at=datetime.utcnow(),
            is_active=True,
            is_verified=False  # Require email verification
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Log successful registration
        SecurityAuditLogger.log_authentication_attempt(
            user_data.username, True, client_ip, user_agent
        )
        
        # Create session
        session_id = SessionManager.create_session(new_user.id, client_ip, user_agent)
        
        # Generate tokens
        access_token = JWTManager.create_access_token(
            data={"sub": str(new_user.id), "username": new_user.username}
        )
        refresh_token = JWTManager.create_refresh_token(
            data={"sub": str(new_user.id), "username": new_user.username}
        )
        
        return {
            "message": "User registered successfully",
            "user_id": new_user.id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": SecurityConfig.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "session_id": session_id,
            "email_verification_required": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        SecurityAuditLogger.log_security_event(
            "registration_error",
            details=str(e),
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.post("/auth/login", response_model=LoginResponse)
async def login_user(
    user_credentials: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Authenticate user with security measures"""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        # Enhanced rate limiting for login attempts
        rate_limit_key = f"login_attempts:{client_ip}:{user_credentials.username}"
        is_allowed, rate_info = rate_limiter.is_allowed(rate_limit_key, limit=5, window=300)  # 5 attempts per 5 minutes
        
        if not is_allowed:
            log_security_event(
                "rate_limit_exceeded",
                user_id="unknown",
                ip_address=client_ip,
                user_agent=user_agent,
                details=f"Login rate limit exceeded: {rate_info}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Try again in {rate_info['retry_after']} seconds.",
                headers={"Retry-After": str(rate_info['retry_after'])}
            )
        
        # Find user
        user = db.query(User).filter(
            User.username == user_credentials.username
        ).first()
        
        if not user or not PasswordManager.verify_password(
            user_credentials.password, user.password_hash
        ):
            SecurityAuditLogger.log_authentication_attempt(
                user_credentials.username, False, client_ip, user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        if not user.is_active:
            SecurityAuditLogger.log_security_event(
                "login_inactive_user",
                user.id,
                f"Username: {user_credentials.username}",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Log successful login
        SecurityAuditLogger.log_authentication_attempt(
            user_credentials.username, True, client_ip, user_agent
        )
        
        # Create session
        session_id = SessionManager.create_session(user.id, client_ip, user_agent)
        
        # Generate tokens
        token_expires = timedelta(
            days=SecurityConfig.JWT_REFRESH_TOKEN_EXPIRE_DAYS if user_credentials.remember_me 
            else SecurityConfig.JWT_ACCESS_TOKEN_EXPIRE_MINUTES / (24 * 60)
        )
        
        access_token = JWTManager.create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=token_expires if user_credentials.remember_me else None
        )
        refresh_token = JWTManager.create_refresh_token(
            data={"sub": str(user.id), "username": user.username}
        )
        
        # Add security headers
        response = add_security_headers(response)
        
        # Set secure cookie for session
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=3600  # 1 hour
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=SecurityConfig.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "email_verified": user.is_verified
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        SecurityAuditLogger.log_security_event(
            "login_error",
            details=str(e),
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Verify refresh token
        payload = JWTManager.verify_token(refresh_request.refresh_token, "refresh")
        user_id = payload.get("sub")
        
        # Verify user still exists and is active
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Generate new access token
        access_token = JWTManager.create_access_token(
            data={"sub": str(user.id), "username": user.username}
        )
        
        # Generate new refresh token
        refresh_token = JWTManager.create_refresh_token(
            data={"sub": str(user.id), "username": user.username}
        )
        
        SecurityAuditLogger.log_security_event(
            "token_refresh",
            user.id,
            "Token refreshed successfully",
            client_ip
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=SecurityConfig.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        SecurityAuditLogger.log_security_event(
            "token_refresh_error",
            details=str(e),
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )

@app.post("/auth/logout")
async def logout_user(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """Logout user and invalidate session"""
    client_ip = request.client.host if request.client else "unknown"
    session_id = request.cookies.get("session_id")
    
    try:
        # Invalidate session
        if session_id:
            SessionManager.invalidate_session(session_id)
        
        # Clear session cookie
        response.delete_cookie("session_id")
        
        SecurityAuditLogger.log_security_event(
            "user_logout",
            current_user["id"],
            "User logged out successfully",
            client_ip
        )
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@app.post("/auth/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Get user from database
        user = db.query(User).filter(User.id == current_user["id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not PasswordManager.verify_password(password_data.current_password, user.password_hash):
            SecurityAuditLogger.log_security_event(
                "password_change_invalid_current",
                current_user["id"],
                "Invalid current password provided",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = PasswordManager.hash_password(password_data.new_password)
        
        # Update password
        user.password_hash = new_password_hash
        user.password_changed_at = datetime.utcnow()
        db.commit()
        
        SecurityAuditLogger.log_security_event(
            "password_change_success",
            current_user["id"],
            "Password changed successfully",
            client_ip
        )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        SecurityAuditLogger.log_security_event(
            "password_change_error",
            current_user["id"],
            str(e),
            client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@app.post("/auth/request-password-reset")
async def request_password_reset(
    reset_request: PasswordReset,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset token"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == reset_request.email).first()
        
        # Always return success to prevent email enumeration
        if not user:
            SecurityAuditLogger.log_security_event(
                "password_reset_unknown_email",
                details=f"Email: {reset_request.email}",
                ip_address=client_ip
            )
            return {"message": "If the email exists, a reset link has been sent"}
        
        # Generate reset token
        reset_token = PasswordManager.generate_password_reset_token()
        
        # Store reset token (in production, use database with expiry)
        # For demo, we'll log it
        logger.info(f"Password reset token for {user.email}: {reset_token}")
        
        # Send email (would implement actual email sending in production)
        background_tasks.add_task(send_password_reset_email, user.email, reset_token)
        
        SecurityAuditLogger.log_security_event(
            "password_reset_requested",
            user.id,
            f"Reset token generated for {user.email}",
            client_ip
        )
        
        return {"message": "If the email exists, a reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        return {"message": "If the email exists, a reset link has been sent"}

@app.get("/auth/me")
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile with caching"""
    try:
        # Try to get user profile from cache first
        cache_key = f"user_profile:{current_user['id']}"
        cached_profile = cache_manager.get(cache_key)
        
        if cached_profile:
            logger.info(f"Profile cache hit for user {current_user['id']}")
            return cached_profile
        
        # If not cached, query database
        user = db.query(User).filter(User.id == current_user["id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create profile response
        profile_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone_number,
            "email_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        
        # Cache the profile for 5 minutes
        cache_manager.set(cache_key, profile_data, 300)
        logger.info(f"Cached profile for user {current_user['id']}")
        
        return profile_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve profile"
        )

@app.get("/auth/sessions")
async def get_user_sessions(
    current_user: dict = Depends(get_current_user)
):
    """Get user's active sessions"""
    # This would typically query active sessions from Redis/database
    # For demo, return placeholder data
    return {
        "active_sessions": [
            {
                "session_id": "demo-session-1",
                "created_at": datetime.utcnow().isoformat(),
                "ip_address": "127.0.0.1",
                "user_agent": "Mozilla/5.0...",
                "current": True
            }
        ]
    }

@app.delete("/auth/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Revoke a specific session"""
    try:
        SessionManager.invalidate_session(session_id)
        
        SecurityAuditLogger.log_security_event(
            "session_revoked",
            current_user["id"],
            f"Session {session_id} revoked"
        )
        
        return {"message": "Session revoked successfully"}
        
    except Exception as e:
        logger.error(f"Session revocation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not revoke session"
        )

# Admin endpoints
@app.get("/auth/admin/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        total = db.query(User).count()
        
        return {
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "email_verified": user.is_verified,
                    "created_at": user.created_at,
                    "last_login": user.last_login
                }
                for user in users
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve users"
        )

@app.put("/auth/admin/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update user status (admin only)"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = is_active
        db.commit()
        
        SecurityAuditLogger.log_security_event(
            "user_status_changed",
            current_admin["id"],
            f"User {user_id} status changed to {'active' if is_active else 'inactive'}"
        )
        
        return {"message": f"User status updated to {'active' if is_active else 'inactive'}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update user status"
        )

# Security monitoring endpoints
@app.get("/auth/security/health")
async def get_security_status():
    """Get security system health"""
    return get_security_health()

@app.get("/auth/security/audit")
async def get_security_audit_log(
    limit: int = 100,
    current_admin: dict = Depends(get_current_admin)
):
    """Get security audit log (admin only)"""
    # This would query audit logs from Redis/database
    # For demo, return placeholder data
    return {
        "audit_entries": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "login_success",
                "user_id": 1,
                "ip_address": "127.0.0.1",
                "details": "Successful login"
            }
        ],
        "total": 1,
        "limit": limit
    }

@app.get("/auth/cache-stats")
async def get_cache_statistics(
    current_user: dict = Depends(get_current_admin)
):
    """Get cache performance statistics (admin only)"""
    try:
        cache_stats = cache_manager.get_stats()
        
        # Calculate hit ratio
        if cache_stats.get('backend') == 'memory':
            hits = cache_stats.get('memory_hits', 0)
            misses = cache_stats.get('memory_misses', 0)
        else:
            hits = cache_stats.get('redis_hits', 0)
            misses = cache_stats.get('redis_misses', 0)
        
        total_requests = hits + misses
        hit_ratio = (hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_backend": cache_stats.get('backend'),
            "cache_stats": cache_stats,
            "performance_metrics": {
                "hit_ratio_percentage": round(hit_ratio, 2),
                "total_requests": total_requests,
                "cache_hits": hits,
                "cache_misses": misses
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve cache statistics"
        )

@app.get("/auth/performance-stats")
async def get_performance_statistics(
    current_user: dict = Depends(get_current_admin)
):
    """Get comprehensive performance statistics (admin only)"""
    try:
        from performance_middleware import get_performance_middleware
        
        # Get performance stats from middleware
        perf_middleware = get_performance_middleware()
        performance_stats = perf_middleware.get_performance_stats()
        
        # Get cache stats
        cache_stats = cache_manager.get_stats()
        
        # Calculate cache hit ratio
        if cache_stats.get('backend') == 'memory':
            hits = cache_stats.get('memory_hits', 0)
            misses = cache_stats.get('memory_misses', 0)
        else:
            hits = cache_stats.get('redis_hits', 0)
            misses = cache_stats.get('redis_misses', 0)
        
        total_cache_requests = hits + misses
        cache_hit_ratio = (hits / total_cache_requests * 100) if total_cache_requests > 0 else 0
        
        return {
            "service_name": "Authentication Service",
            "timestamp": datetime.utcnow().isoformat(),
            "performance_metrics": {
                "response_times": {
                    "average_ms": performance_stats.get('avg_response_time_ms', 0),
                    "fastest_ms": performance_stats.get('fastest_request_ms', 0),
                    "slowest_ms": performance_stats.get('slowest_request_ms', 0)
                },
                "request_volume": {
                    "total_requests_5min": performance_stats.get('total_requests', 0),
                    "requests_per_minute": performance_stats.get('requests_per_minute', 0),
                    "slow_requests": performance_stats.get('slow_requests', 0)
                },
                "status_codes": performance_stats.get('status_code_distribution', {}),
                "cache_performance": {
                    "backend": cache_stats.get('backend', 'unknown'),
                    "hit_ratio_percentage": round(cache_hit_ratio, 2),
                    "total_cache_requests": total_cache_requests,
                    "cache_hits": hits,
                    "cache_misses": misses
                }
            },
            "health_indicators": {
                "avg_response_healthy": performance_stats.get('avg_response_time_ms', 0) < 500,
                "cache_performance_healthy": cache_hit_ratio > 70,
                "error_rate_healthy": performance_stats.get('total_requests', 1) > 0 and 
                                    (performance_stats.get('status_code_distribution', {}).get('500', 0) / 
                                     performance_stats.get('total_requests', 1)) < 0.01
            }
        }
        
    except Exception as e:
        logger.error(f"Performance stats error: {e}")
        return {
            "service_name": "Authentication Service",
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Could not retrieve performance statistics",
            "details": str(e)
        }

# Utility functions
async def send_password_reset_email(email: str, reset_token: str):
    """Send password reset email (placeholder implementation)"""
    # In production, integrate with email service
    logger.info(f"Sending password reset email to {email} with token: {reset_token}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "secure-auth",
        "timestamp": datetime.utcnow().isoformat(),
        "security": get_security_health()
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Secure Authentication Service")
    uvicorn.run(app, host="127.0.0.1", port=8013)