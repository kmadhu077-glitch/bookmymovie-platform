import time
import random
import re
from typing import Dict, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import hashlib

# --- SMS & OTP Service for Mobile Authentication ---

class MobileLoginRequest(BaseModel):
    """Request OTP for mobile number"""
    mobile_number: str = Field(..., example="+919876543210")
    country_code: str = Field(default="+91", example="+91")
    
    @validator('mobile_number')
    def validate_mobile(cls, v):
        # Remove spaces and special characters
        clean_mobile = re.sub(r'[^\d+]', '', v)
        if not re.match(r'^\+?[1-9]\d{1,14}$', clean_mobile):
            raise ValueError('Invalid mobile number format')
        return clean_mobile

class OTPVerificationRequest(BaseModel):
    """Verify OTP for mobile number"""
    mobile_number: str
    otp: str = Field(..., min_length=4, max_length=6)
    session_id: str

class OTPResponse(BaseModel):
    """Response after requesting OTP"""
    session_id: str
    message: str
    expires_in: int = 300  # 5 minutes
    mobile_number: str

class MobileAuthToken(BaseModel):
    """Auth token after successful OTP verification"""
    user_id: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    mobile_number: str

class UserProfile(BaseModel):
    """User profile for mobile users"""
    user_id: str
    mobile_number: str
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime
    is_verified: bool = True

# --- In-Memory Storage (Replace with Redis/Database in production) ---
MOBILE_USERS: Dict[str, dict] = {}  # mobile_number: user_data
OTP_SESSIONS: Dict[str, dict] = {}  # session_id: {mobile, otp, expires}
ACTIVE_TOKENS: Dict[str, dict] = {}  # token: user_data

# --- Helper Functions ---

def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return f"{random.randint(100000, 999999)}"

def generate_session_id() -> str:
    """Generate unique session ID"""
    return f"SMS_{int(time.time() * 1000)}{random.randint(100, 999)}"

def generate_user_id() -> str:
    """Generate unique user ID"""
    return f"MOB_{int(time.time() * 1000)}"

def generate_token(user_id: str) -> str:
    """Generate authentication token"""
    return f"MOB_TOKEN.{user_id}.{int(time.time())}.{random.randint(1000, 9999)}"

def send_sms(mobile_number: str, message: str) -> bool:
    """Mock SMS sending (replace with real SMS gateway like Twilio)"""
    print(f"📱 SMS SENT to {mobile_number}: {message}")
    # In production, integrate with:
    # - Twilio SMS API
    # - AWS SNS
    # - Firebase Cloud Messaging
    # - Other SMS providers
    return True

def clean_expired_otps():
    """Clean up expired OTP sessions"""
    current_time = time.time()
    expired_sessions = [
        session_id for session_id, data in OTP_SESSIONS.items()
        if current_time > data['expires']
    ]
    for session_id in expired_sessions:
        del OTP_SESSIONS[session_id]

# --- FastAPI App Setup ---
app = FastAPI(
    title="Mobile Authentication & SMS Service",
    description="Handles mobile number authentication with OTP verification"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.get("/health")
def health_check():
    """Service health check"""
    return {"status": "ok", "service": "mobile_auth"}

@app.post("/v1/mobile/request-otp", response_model=OTPResponse)
async def request_otp(request: MobileLoginRequest):
    """
    Step 1: Request OTP for mobile number
    """
    clean_expired_otps()
    
    mobile = request.mobile_number
    if not mobile.startswith('+'):
        mobile = request.country_code + mobile.lstrip('0')
    
    # Generate OTP and session
    otp = generate_otp()
    session_id = generate_session_id()
    expires = time.time() + 300  # 5 minutes
    
    # Store OTP session
    OTP_SESSIONS[session_id] = {
        'mobile_number': mobile,
        'otp': otp,
        'expires': expires,
        'attempts': 0
    }
    
    # Send SMS (mock)
    sms_message = f"Your BookMyMovie login OTP is: {otp}. Valid for 5 minutes. Do not share this code."
    send_sms(mobile, sms_message)
    
    return OTPResponse(
        session_id=session_id,
        message="OTP sent successfully to your mobile number",
        mobile_number=mobile
    )

@app.post("/v1/mobile/verify-otp", response_model=MobileAuthToken)
async def verify_otp(request: OTPVerificationRequest):
    """
    Step 2: Verify OTP and authenticate user
    """
    clean_expired_otps()
    
    session = OTP_SESSIONS.get(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP session"
        )
    
    # Check if session expired
    if time.time() > session['expires']:
        del OTP_SESSIONS[request.session_id]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )
    
    # Check OTP
    if session['otp'] != request.otp:
        session['attempts'] += 1
        if session['attempts'] >= 3:
            del OTP_SESSIONS[request.session_id]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many failed attempts. Please request a new OTP."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {3 - session['attempts']} attempts remaining."
        )
    
    # OTP verified successfully
    mobile_number = session['mobile_number']
    del OTP_SESSIONS[request.session_id]
    
    # Get or create user
    user_data = MOBILE_USERS.get(mobile_number)
    if not user_data:
        # Create new user
        user_id = generate_user_id()
        user_data = {
            'user_id': user_id,
            'mobile_number': mobile_number,
            'name': None,
            'email': None,
            'created_at': datetime.utcnow(),
            'is_verified': True,
            'login_count': 0
        }
        MOBILE_USERS[mobile_number] = user_data
    
    user_data['login_count'] += 1
    user_data['last_login'] = datetime.utcnow()
    
    # Generate auth token
    token = generate_token(user_data['user_id'])
    ACTIVE_TOKENS[token] = {
        'user_id': user_data['user_id'],
        'mobile_number': mobile_number,
        'expires': time.time() + 3600  # 1 hour
    }
    
    return MobileAuthToken(
        user_id=user_data['user_id'],
        access_token=token,
        mobile_number=mobile_number
    )

@app.get("/v1/mobile/profile", response_model=UserProfile)
async def get_mobile_profile(authorization: str = Header(..., description="Bearer token")):
    """
    Get user profile for mobile authenticated user
    """
    # Extract token from "Bearer TOKEN" format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization.split(" ")[1]
    token_data = ACTIVE_TOKENS.get(token)
    
    if not token_data or time.time() > token_data['expires']:
        if token in ACTIVE_TOKENS:
            del ACTIVE_TOKENS[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid"
        )
    
    mobile_number = token_data['mobile_number']
    user_data = MOBILE_USERS[mobile_number]
    
    return UserProfile(
        user_id=user_data['user_id'],
        mobile_number=user_data['mobile_number'],
        name=user_data.get('name'),
        email=user_data.get('email'),
        created_at=user_data['created_at'],
        is_verified=user_data['is_verified']
    )

@app.post("/v1/mobile/update-profile")
async def update_mobile_profile(
    name: Optional[str] = None,
    email: Optional[str] = None,
    authorization: str = Header(..., description="Bearer token")
):
    """
    Update user profile information
    """
    # Extract and validate token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization.split(" ")[1]
    token_data = ACTIVE_TOKENS.get(token)
    
    if not token_data or time.time() > token_data['expires']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid"
        )
    
    mobile_number = token_data['mobile_number']
    user_data = MOBILE_USERS[mobile_number]
    
    # Update profile
    if name:
        user_data['name'] = name
    if email:
        user_data['email'] = email
    
    user_data['updated_at'] = datetime.utcnow()
    
    return {"message": "Profile updated successfully"}

@app.post("/v1/mobile/logout")
async def mobile_logout(authorization: str = Header(..., description="Bearer token")):
    """
    Logout and invalidate token
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization.split(" ")[1]
    if token in ACTIVE_TOKENS:
        del ACTIVE_TOKENS[token]
    
    return {"message": "Logged out successfully"}

# --- Admin/Debug Endpoints ---

@app.get("/v1/mobile/admin/stats")
async def get_mobile_stats():
    """
    Get mobile authentication statistics (for admin)
    """
    clean_expired_otps()
    
    return {
        "total_mobile_users": len(MOBILE_USERS),
        "active_sessions": len(OTP_SESSIONS),
        "active_tokens": len(ACTIVE_TOKENS),
        "recent_users": [
            {
                "mobile": mobile[-4:].rjust(10, '*'),  # Mask mobile number
                "login_count": data.get('login_count', 0),
                "last_login": data.get('last_login')
            }
            for mobile, data in list(MOBILE_USERS.items())[-5:]
        ]
    }

# TO RUN: uvicorn backend.mobile_auth_service:app --host 127.0.0.1 --port 8013 --reload