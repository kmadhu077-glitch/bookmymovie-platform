import time
import hashlib
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Architecture Configuration ---
# Mocking a persistent user database
USER_DATABASE: Dict[str, dict] = {}

# --- Pydantic Models for API Contracts ---

class UserRegistration(BaseModel):
    """Schema for user registration request."""
    email: str = Field(..., example="jane.doe@example.com")
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters.")
    name: str = Field(..., example="Jane Doe")

class UserLogin(BaseModel):
    """Schema for user login request."""
    email: str = Field(..., example="jane.doe@example.com")
    password: str = Field(..., description="User password.")

class UserProfile(BaseModel):
    """Schema for returning non-sensitive user profile data."""
    user_id: str
    email: str
    name: str

class AuthToken(BaseModel):
    """Schema for the successful authentication response."""
    user_id: str
    access_token: str = Field(..., description="The token used to authorize future requests.")
    token_type: str = "bearer"
    expires_in: int = 3600 # 1 hour

# --- Helper Functions ---

def hash_password(password: str) -> str:
    """Simple password hashing using SHA256 (for mock purpose)."""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_user_id() -> str:
    """Generates a mock unique user ID."""
    return f"USER_{int(time.time() * 1000)}"

def generate_mock_token(user_id: str) -> str:
    """Generates a mock JWT/session token."""
    # In a real app, this would be a proper JWT signed with a secret key
    return f"MOCK_JWT.{user_id}.{int(time.time())}"

# --- FastAPI Application Instance ---
app = FastAPI(
    title="User & Auth Microservice (Python/FastAPI)",
    description="Handles user registration, authentication, and profile management."
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Service Health Check (NEW) ---
@app.get("/health", status_code=200, summary="Service Health Check")
async def get_health():
    """
    Health Check Endpoint.
    Returns HTTP 200 OK if the service is running.
    """
    return {"status": "ok", "service": "auth"}

# --- API Endpoints ---

@app.post(
    "/v1/auth/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user."
)
async def register_user(user: UserRegistration):
    """Registers a new user and stores their hashed credentials."""
    if user.email in USER_DATABASE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists."
        )

    user_id = generate_user_id()
    
    USER_DATABASE[user.email] = {
        "user_id": user_id,
        "email": user.email,
        "name": user.name,
        "hashed_password": hash_password(user.password)
    }

    return UserProfile(user_id=user_id, email=user.email, name=user.name)

@app.post(
    "/v1/auth/login",
    response_model=AuthToken,
    summary="Log in an existing user and return an access token."
)
async def login_user(login_data: UserLogin):
    """Authenticates the user and issues an access token."""
    user_record = USER_DATABASE.get(login_data.email)
    
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials."
        )
        
    if hash_password(login_data.password) != user_record["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials."
        )

    token = generate_mock_token(user_record["user_id"])
    
    return AuthToken(
        user_id=user_record["user_id"],
        access_token=token
    )
