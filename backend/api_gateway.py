import uvicorn
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Dict, Any

# --- CONFIGURATION ---

# The port the API Gateway runs on (the only port the frontend talks to)
GATEWAY_PORT = 8008

# Define the internal base URLs for each microservice
SERVICE_MAPPING = {
    # Path prefix: (Service Name, Internal Base URL)
    "/auth": ("Auth Service", "http://localhost:8005"),
    "/catalog": ("Catalog Service", "http://localhost:8000"),
    "/booking": ("Booking Service", "http://localhost:8006"),
    "/payment": ("Payment Service", "http://localhost:8007"),
}

# --- APP SETUP ---

app = FastAPI(
    title="API Gateway",
    description="Single entry point for all microservices.",
    version="1.0.0"
)

# Crucial for allowing the React frontend (likely on a different port/origin) to talk to the Gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize HTTP client for forwarding requests
# Use a timeout to prevent hanging connections
client = httpx.AsyncClient(timeout=30.0) 

# --- CORE ROUTING LOGIC ---

# Catch-all route to handle all incoming requests and forward them
@app.api_route("/{service_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_request(request: Request, service_path: str):
    """
    Identifies the target service based on the path and forwards the request.
    Handles response and error propagation.
    """
    
    # 1. Identify the target service based on the path prefix
    base_path = f"/{service_path.split('/')[0]}"
    
    if base_path not in SERVICE_MAPPING:
        # If the prefix doesn't match a known service, return 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Route not found for path: /{service_path}"
        )

    service_name, target_base_url = SERVICE_MAPPING[base_path]
    
    # The actual path to send to the target service (e.g., /v1/users/register)
    target_path = service_path[len(base_path):] 
    target_url = f"{target_base_url}{target_path}"
    
    # 2. Extract necessary request details
    method = request.method
    headers_to_forward = {}
    
    # Forward essential headers, especially Authorization for security
    for header, value in request.headers.items():
        if header.lower() in ["content-type", "authorization", "accept", "cookie"]:
            headers_to_forward[header] = value

    try:
        # Get the request body if present (important for POST/PUT/PATCH)
        request_data = await request.body()
        
        # 3. Forward the request using httpx
        response = await client.request(
            method=method,
            url=target_url,
            headers=headers_to_forward,
            params=request.query_params,
            content=request_data
        )

        # 4. Return the response back to the client
        # Use a raw Response object to maintain original status code, headers, and content type
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("Content-Type")
        )

    except httpx.ConnectError:
        # Handle case where the target microservice is down
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"Service unavailable: {service_name} at {target_base_url}"}
        )
    except Exception as e:
        # Catch any other unexpected error
        print(f"An unexpected error occurred: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred in the Gateway."}
        )

# --- STARTUP COMMAND ---

if __name__ == "__main__":
    print(f"--- API Gateway is starting on port {GATEWAY_PORT} ---")
    print("Mapped Services:")
    for prefix, (name, url) in SERVICE_MAPPING.items():
        print(f"  {prefix} -> {name} ({url})")
        
    uvicorn.run(app, host="0.0.0.0", port=GATEWAY_PORT)
