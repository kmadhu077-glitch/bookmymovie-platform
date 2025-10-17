import time
import hashlib
import random
import string
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import httpx

# --- Enhanced User Models ---

class MobileLoginRequest(BaseModel):
    mobile_number: str = Field(..., pattern=r"^[6-9][0-9]{9}$")
    
class OTPVerificationRequest(BaseModel):
    mobile_number: str = Field(..., pattern=r"^[6-9][0-9]{9}$")
    otp_code: str = Field(..., min_length=6, max_length=6)

class UserProfile(BaseModel):
    user_id: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    profile_image_url: Optional[str] = None
    preferred_language: str = "english"
    preferred_theaters: List[str] = []
    notification_preferences: Dict = {}
    created_at: str
    last_login: str

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = Field(None, pattern=r"^(male|female|other|prefer_not_to_say)$")
    preferred_language: Optional[str] = "english"
    preferred_theaters: Optional[List[str]] = []

class BookingHistory(BaseModel):
    booking_id: str
    movie_title: str
    theater_name: str
    showtime: str
    seats: List[str]
    total_amount: float
    booking_date: str
    status: str  # confirmed, cancelled, completed
    ticket_url: Optional[str] = None
    can_cancel: bool = True

class UserPreferences(BaseModel):
    favorite_genres: List[str] = []
    preferred_showtime_slots: List[str] = []  # morning, afternoon, evening, night
    notification_email: bool = True
    notification_sms: bool = True
    notification_push: bool = True
    language: str = "english"
    city: str = "delhi"

class NotificationSettings(BaseModel):
    booking_confirmations: bool = True
    promotional_offers: bool = True
    movie_recommendations: bool = True
    showtime_reminders: bool = True
    payment_updates: bool = True
    email_notifications: bool = True
    sms_notifications: bool = True
    push_notifications: bool = True

class UserStats(BaseModel):
    total_bookings: int
    total_amount_spent: float
    favorite_theater: str
    favorite_genre: str
    movies_watched: int
    loyalty_points: int
    membership_tier: str  # bronze, silver, gold, platinum

# --- Mock Databases ---
MOBILE_OTP_STORE = {}  # mobile_number: {otp, expiry, verified}
USER_PROFILES_DB = {}
USER_BOOKINGS_DB = {}
USER_PREFERENCES_DB = {}

# --- Helper Functions ---

def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_sms_otp(mobile_number: str, otp: str) -> bool:
    """Mock SMS sending function"""
    print(f"📱 SMS sent to +91{mobile_number}: Your BookMyMovie OTP is {otp}")
    return True

def generate_user_id() -> str:
    return f"USER_{int(time.time() * 1000)}"

def generate_booking_id() -> str:
    return f"BKG_{int(time.time() * 1000)}"

# --- Security ---
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify user token and return user info"""
    token = credentials.credentials
    
    # Mock token verification - in real app, verify JWT
    if token.startswith("USER_TOKEN_") or token.startswith("MOCK_JWT."):
        user_id = token.split("_")[-1].split(".")[1] if "MOCK_JWT" in token else token.split("_")[-1]
        if user_id in USER_PROFILES_DB:
            return USER_PROFILES_DB[user_id]
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token"
    )

# --- FastAPI App ---
app = FastAPI(
    title="Enhanced User Panel API",
    description="Comprehensive user management with mobile login, profiles, and preferences",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mobile Authentication ---

@app.post("/v2/auth/mobile/send-otp")
async def send_mobile_otp(request: MobileLoginRequest):
    """Send OTP to mobile number for authentication"""
    
    mobile_number = request.mobile_number
    otp = generate_otp()
    expiry_time = time.time() + 300  # 5 minutes expiry
    
    # Store OTP
    MOBILE_OTP_STORE[mobile_number] = {
        "otp": otp,
        "expiry": expiry_time,
        "verified": False,
        "attempts": 0
    }
    
    # Send SMS
    sms_sent = send_sms_otp(mobile_number, otp)
    
    if sms_sent:
        return {
            "message": f"OTP sent to +91{mobile_number}",
            "expires_in": 300,
            "can_resend_after": 60
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to send OTP")

@app.post("/v2/auth/mobile/verify-otp")
async def verify_mobile_otp(request: OTPVerificationRequest):
    """Verify OTP and create/login user"""
    
    mobile_number = request.mobile_number
    otp_code = request.otp_code
    
    # Check if OTP exists
    otp_data = MOBILE_OTP_STORE.get(mobile_number)
    if not otp_data:
        raise HTTPException(status_code=400, detail="OTP not found. Please request a new OTP.")
    
    # Check expiry
    if time.time() > otp_data["expiry"]:
        del MOBILE_OTP_STORE[mobile_number]
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new OTP.")
    
    # Check attempts
    if otp_data["attempts"] >= 3:
        del MOBILE_OTP_STORE[mobile_number]
        raise HTTPException(status_code=400, detail="Too many invalid attempts. Please request a new OTP.")
    
    # Verify OTP
    if otp_data["otp"] != otp_code:
        MOBILE_OTP_STORE[mobile_number]["attempts"] += 1
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Mark as verified
    MOBILE_OTP_STORE[mobile_number]["verified"] = True
    
    # Check if user exists
    existing_user = None
    for user_id, profile in USER_PROFILES_DB.items():
        if profile.get("mobile_number") == mobile_number:
            existing_user = profile
            break
    
    if existing_user:
        # Login existing user
        user_token = f"USER_TOKEN_{existing_user['user_id']}"
        existing_user["last_login"] = datetime.now().isoformat()
        
        return {
            "message": "Login successful",
            "user_id": existing_user["user_id"],
            "access_token": user_token,
            "token_type": "bearer",
            "is_new_user": False,
            "profile": existing_user
        }
    else:
        # Create new user
        user_id = generate_user_id()
        user_profile = {
            "user_id": user_id,
            "mobile_number": mobile_number,
            "name": f"User {mobile_number[-4:]}",  # Default name
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "email": None,
            "preferred_language": "english",
            "notification_preferences": {
                "sms": True,
                "email": False,
                "push": True
            }
        }
        
        USER_PROFILES_DB[user_id] = user_profile
        user_token = f"USER_TOKEN_{user_id}"
        
        return {
            "message": "Account created successfully",
            "user_id": user_id,
            "access_token": user_token,
            "token_type": "bearer",
            "is_new_user": True,
            "profile": user_profile
        }

# --- User Profile Management ---

@app.get("/v2/user/profile", response_model=UserProfile)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    return UserProfile(**current_user)

@app.put("/v2/user/profile")
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile"""
    
    user_id = current_user["user_id"]
    
    # Update profile fields
    for field, value in profile_update.dict(exclude_unset=True).items():
        if value is not None:
            USER_PROFILES_DB[user_id][field] = value
    
    USER_PROFILES_DB[user_id]["updated_at"] = datetime.now().isoformat()
    
    return {
        "message": "Profile updated successfully",
        "profile": USER_PROFILES_DB[user_id]
    }

@app.post("/v2/user/profile/image")
async def upload_profile_image(
    image_url: str,  # In real app, handle file upload
    current_user: dict = Depends(get_current_user)
):
    """Upload profile image"""
    
    user_id = current_user["user_id"]
    USER_PROFILES_DB[user_id]["profile_image_url"] = image_url
    
    return {"message": "Profile image updated successfully"}

# --- Booking History ---

@app.get("/v2/user/bookings", response_model=List[BookingHistory])
async def get_booking_history(current_user: dict = Depends(get_current_user)):
    """Get user's booking history"""
    
    user_id = current_user["user_id"]
    
    # Mock booking data
    mock_bookings = [
        {
            "booking_id": "BKG_123456",
            "movie_title": "Cybernetic Hearts",
            "theater_name": "PVR Select City Walk",
            "showtime": "2024-10-15T19:00:00",
            "seats": ["A1", "A2"],
            "total_amount": 500.0,
            "booking_date": "2024-10-10T14:30:00",
            "status": "confirmed",
            "can_cancel": True
        },
        {
            "booking_id": "BKG_123457",
            "movie_title": "Quantum Leap",
            "theater_name": "INOX Nehru Place",
            "showtime": "2024-10-12T21:30:00",
            "seats": ["B5"],
            "total_amount": 300.0,
            "booking_date": "2024-10-08T16:45:00",
            "status": "completed",
            "can_cancel": False
        }
    ]
    
    return mock_bookings

@app.post("/v2/user/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a booking"""
    
    # Mock cancellation logic
    cancellation_fee = 50.0
    refund_amount = 450.0
    
    return {
        "message": "Booking cancelled successfully",
        "booking_id": booking_id,
        "cancellation_fee": cancellation_fee,
        "refund_amount": refund_amount,
        "refund_timeline": "3-5 business days"
    }

# --- User Preferences ---

@app.get("/v2/user/preferences", response_model=UserPreferences)
async def get_user_preferences(current_user: dict = Depends(get_current_user)):
    """Get user preferences"""
    
    user_id = current_user["user_id"]
    
    # Return stored preferences or defaults
    preferences = USER_PREFERENCES_DB.get(user_id, UserPreferences().dict())
    return UserPreferences(**preferences)

@app.put("/v2/user/preferences")
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user)
):
    """Update user preferences"""
    
    user_id = current_user["user_id"]
    USER_PREFERENCES_DB[user_id] = preferences.dict()
    
    return {"message": "Preferences updated successfully"}

@app.get("/v2/user/notifications/settings", response_model=NotificationSettings)
async def get_notification_settings(current_user: dict = Depends(get_current_user)):
    """Get notification settings"""
    
    # Return current notification settings
    return NotificationSettings()

@app.put("/v2/user/notifications/settings")
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: dict = Depends(get_current_user)
):
    """Update notification settings"""
    
    user_id = current_user["user_id"]
    USER_PROFILES_DB[user_id]["notification_preferences"] = settings.dict()
    
    return {"message": "Notification settings updated successfully"}

# --- User Statistics & Loyalty ---

@app.get("/v2/user/stats", response_model=UserStats)
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """Get user statistics and loyalty information"""
    
    # Mock user statistics
    stats = UserStats(
        total_bookings=12,
        total_amount_spent=3600.0,
        favorite_theater="PVR Select City Walk",
        favorite_genre="Action",
        movies_watched=12,
        loyalty_points=360,
        membership_tier="silver"
    )
    
    return stats

@app.get("/v2/user/recommendations")
async def get_movie_recommendations(current_user: dict = Depends(get_current_user)):
    """Get personalized movie recommendations"""
    
    # Mock recommendations based on user preferences
    recommendations = [
        {
            "movie_id": "movie_001",
            "title": "Neon Dreams",
            "genre": "Sci-Fi",
            "rating": 8.5,
            "reason": "Based on your love for sci-fi movies"
        },
        {
            "movie_id": "movie_002", 
            "title": "Time Paradox",
            "genre": "Thriller",
            "rating": 8.2,
            "reason": "Trending in your area"
        }
    ]
    
    return {"recommendations": recommendations}

# --- Loyalty & Rewards ---

@app.get("/v2/user/loyalty/points")
async def get_loyalty_points(current_user: dict = Depends(get_current_user)):
    """Get user's loyalty points and rewards"""
    
    return {
        "current_points": 360,
        "tier": "silver",
        "next_tier_points_required": 140,
        "available_rewards": [
            {
                "reward_id": "reward_001",
                "title": "₹100 Off on Next Booking",
                "points_required": 100,
                "validity": "30 days"
            },
            {
                "reward_id": "reward_002",
                "title": "Free Popcorn",
                "points_required": 50,
                "validity": "15 days"
            }
        ]
    }

@app.post("/v2/user/loyalty/redeem/{reward_id}")
async def redeem_loyalty_reward(
    reward_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Redeem loyalty reward"""
    
    return {
        "message": "Reward redeemed successfully",
        "reward_id": reward_id,
        "coupon_code": "BMM100OFF",
        "validity": "30 days"
    }

# --- Health Check ---

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "enhanced_user_panel"}

# Run: uvicorn enhanced_user_service:app --host 127.0.0.1 --port 8012 --reload