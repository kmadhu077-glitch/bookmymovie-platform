"""
Secure Real-time Service for BookMyMovie Platform
WebSocket Authentication, Connection Security, and Real-time Updates
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError
import jwt
from contextlib import asynccontextmanager

# Import security middleware
from security_middleware import (
    SecurityMiddleware, JWTManager, SecurityAuditLogger, InputSanitizer
)
from models import get_db, User, Booking, Showtime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection management
class ConnectionManager:
    """Manage WebSocket connections with authentication"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, Set[str]] = {}  # user_id -> connection_ids
        self.connection_metadata: Dict[str, Dict] = {}  # connection_id -> metadata
        self.room_connections: Dict[str, Set[str]] = {}  # room_id -> connection_ids
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: int, user_data: dict):
        """Accept WebSocket connection after authentication"""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Store connection metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "username": user_data.get("username"),
            "connected_at": datetime.now(),
            "last_activity": datetime.now(),
            "ip_address": websocket.client.host if websocket.client else "unknown"
        }
        
        logger.info(f"User {user_id} connected with connection {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove connection"""
        if connection_id in self.active_connections:
            connection_data = self.connection_metadata.get(connection_id, {})
            user_id = connection_data.get("user_id")
            
            # Remove from active connections
            del self.active_connections[connection_id]
            
            # Remove from user connections
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # Remove from rooms
            for room_id, connections in self.room_connections.items():
                connections.discard(connection_id)
            
            # Remove metadata
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            logger.info(f"Connection {connection_id} disconnected")
    
    async def join_room(self, connection_id: str, room_id: str):
        """Join a specific room (e.g., showtime room for seat updates)"""
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        
        self.room_connections[room_id].add(connection_id)
        
        # Update last activity
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["last_activity"] = datetime.now()
    
    async def leave_room(self, connection_id: str, room_id: str):
        """Leave a room"""
        if room_id in self.room_connections:
            self.room_connections[room_id].discard(connection_id)
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to a specific user (all their connections)"""
        if user_id in self.user_connections:
            message_json = json.dumps(message)
            disconnected_connections = []
            
            for connection_id in self.user_connections[user_id].copy():
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_text(message_json)
                        # Update last activity
                        if connection_id in self.connection_metadata:
                            self.connection_metadata[connection_id]["last_activity"] = datetime.now()
                    except Exception as e:
                        logger.error(f"Error sending message to connection {connection_id}: {e}")
                        disconnected_connections.append(connection_id)
            
            # Clean up disconnected connections
            for conn_id in disconnected_connections:
                self.disconnect(conn_id)
    
    async def broadcast_to_room(self, message: dict, room_id: str, exclude_connection: Optional[str] = None):
        """Broadcast message to all connections in a room"""
        if room_id not in self.room_connections:
            return
        
        message_json = json.dumps(message)
        disconnected_connections = []
        
        for connection_id in self.room_connections[room_id].copy():
            if connection_id == exclude_connection:
                continue
                
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_text(message_json)
                    # Update last activity
                    if connection_id in self.connection_metadata:
                        self.connection_metadata[connection_id]["last_activity"] = datetime.now()
                except Exception as e:
                    logger.error(f"Error broadcasting to connection {connection_id}: {e}")
                    disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for conn_id in disconnected_connections:
            self.disconnect(conn_id)
    
    async def broadcast_to_all(self, message: dict, exclude_user: Optional[int] = None):
        """Broadcast message to all connected users"""
        message_json = json.dumps(message)
        disconnected_connections = []
        
        for connection_id, websocket in self.active_connections.items():
            connection_data = self.connection_metadata.get(connection_id, {})
            user_id = connection_data.get("user_id")
            
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                await websocket.send_text(message_json)
                # Update last activity
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_activity"] = datetime.now()
            except Exception as e:
                logger.error(f"Error broadcasting to connection {connection_id}: {e}")
                disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for conn_id in disconnected_connections:
            self.disconnect(conn_id)
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "unique_users": len(self.user_connections),
            "active_rooms": len([room for room, connections in self.room_connections.items() if connections]),
            "connections_by_room": {room: len(connections) for room, connections in self.room_connections.items()},
            "recent_connections": [
                {
                    "connection_id": conn_id,
                    "user_id": metadata["user_id"],
                    "username": metadata["username"],
                    "connected_at": metadata["connected_at"].isoformat(),
                    "last_activity": metadata["last_activity"].isoformat()
                }
                for conn_id, metadata in list(self.connection_metadata.items())[-10:]  # Last 10 connections
            ]
        }

# Global connection manager
manager = ConnectionManager()

# Message models
class WebSocketMessage(BaseModel):
    type: str
    data: dict
    room_id: Optional[str] = None

class SeatUpdateMessage(BaseModel):
    showtime_id: int
    seat_row: str
    seat_number: int
    action: str  # 'select', 'release', 'book'
    user_id: int

class BookingNotification(BaseModel):
    booking_id: int
    user_id: int
    message: str
    type: str  # 'success', 'error', 'info'

# Background tasks
async def cleanup_inactive_connections():
    """Clean up connections that have been inactive"""
    while True:
        try:
            current_time = datetime.now()
            inactive_connections = []
            
            for conn_id, metadata in manager.connection_metadata.items():
                last_activity = metadata.get("last_activity", current_time)
                if (current_time - last_activity).total_seconds() > 3600:  # 1 hour timeout
                    inactive_connections.append(conn_id)
            
            for conn_id in inactive_connections:
                if conn_id in manager.active_connections:
                    try:
                        await manager.active_connections[conn_id].close(code=1001, reason="Inactive connection")
                    except:
                        pass
                manager.disconnect(conn_id)
                
                # Log cleanup
                metadata = manager.connection_metadata.get(conn_id, {})
                user_id = metadata.get("user_id")
                SecurityAuditLogger.log_security_event(
                    "websocket_inactive_cleanup",
                    user_id,
                    f"Connection {conn_id} cleaned up due to inactivity"
                )
            
            if inactive_connections:
                logger.info(f"Cleaned up {len(inactive_connections)} inactive connections")
            
        except Exception as e:
            logger.error(f"Error in connection cleanup: {e}")
        
        await asyncio.sleep(300)  # Check every 5 minutes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background tasks
    cleanup_task = asyncio.create_task(cleanup_inactive_connections())
    
    yield
    
    # Cleanup
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

# FastAPI app
app = FastAPI(
    title="BookMyMovie - Secure Real-time Service",
    description="Secure WebSocket service with JWT authentication and real-time updates",
    version="3.0.0",
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"]
)

# WebSocket authentication
async def authenticate_websocket(websocket: WebSocket, token: str, db: Session) -> Optional[dict]:
    """Authenticate WebSocket connection using JWT token"""
    try:
        # Verify JWT token
        payload = JWTManager.verify_token(token, "access")
        user_id = int(payload.get("sub"))
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            return None
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
        
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None

# WebSocket endpoints
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """Main WebSocket endpoint with authentication"""
    connection_id = f"conn_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(websocket)}"
    client_ip = websocket.client.host if websocket.client else "unknown"
    
    # Check for token in query parameters
    if not token:
        query_params = dict(websocket.query_params)
        token = query_params.get("token")
    
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        SecurityAuditLogger.log_security_event(
            "websocket_auth_missing_token",
            None,
            f"Connection attempt without token from {client_ip}",
            client_ip
        )
        return
    
    # Authenticate user
    db = next(get_db())
    user_data = await authenticate_websocket(websocket, token, db)
    
    if not user_data:
        await websocket.close(code=4003, reason="Invalid authentication token")
        SecurityAuditLogger.log_security_event(
            "websocket_auth_failed",
            None,
            f"Failed authentication attempt from {client_ip}",
            client_ip
        )
        return
    
    # Accept connection
    await manager.connect(websocket, connection_id, user_data["id"], user_data)
    
    # Log successful connection
    SecurityAuditLogger.log_security_event(
        "websocket_connected",
        user_data["id"],
        f"Connection ID: {connection_id}",
        client_ip
    )
    
    # Send welcome message
    welcome_message = {
        "type": "connection_established",
        "data": {
            "connection_id": connection_id,
            "user": user_data,
            "server_time": datetime.now().isoformat()
        }
    }
    await websocket.send_text(json.dumps(welcome_message))
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse and validate message
                message_data = json.loads(data)
                message = WebSocketMessage(**message_data)
                
                # Sanitize message data
                message.data = {
                    key: InputSanitizer.sanitize_string(str(value)) if isinstance(value, str) else value
                    for key, value in message.data.items()
                }
                
                # Process message based on type
                await handle_websocket_message(connection_id, message, user_data, db)
                
            except (json.JSONDecodeError, ValidationError) as e:
                # Send error response for invalid messages
                error_message = {
                    "type": "error",
                    "data": {"message": "Invalid message format", "error": str(e)}
                }
                await websocket.send_text(json.dumps(error_message))
                
                SecurityAuditLogger.log_security_event(
                    "websocket_invalid_message",
                    user_data["id"],
                    f"Invalid message from connection {connection_id}: {str(e)}",
                    client_ip
                )
            
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
        SecurityAuditLogger.log_security_event(
            "websocket_disconnected",
            user_data["id"],
            f"Connection ID: {connection_id}",
            client_ip
        )
    except Exception as e:
        logger.error(f"WebSocket error for connection {connection_id}: {e}")
        manager.disconnect(connection_id)
        SecurityAuditLogger.log_security_event(
            "websocket_error",
            user_data["id"],
            f"Connection error: {str(e)}",
            client_ip
        )

async def handle_websocket_message(connection_id: str, message: WebSocketMessage, user_data: dict, db: Session):
    """Handle different types of WebSocket messages"""
    
    message_type = message.type
    data = message.data
    user_id = user_data["id"]
    
    if message_type == "join_room":
        # Join a specific room (e.g., showtime for seat updates)
        room_id = data.get("room_id")
        if room_id:
            await manager.join_room(connection_id, room_id)
            
            # Send confirmation
            response = {
                "type": "room_joined",
                "data": {"room_id": room_id, "status": "success"}
            }
            await manager.active_connections[connection_id].send_text(json.dumps(response))
            
            SecurityAuditLogger.log_security_event(
                "websocket_room_joined",
                user_id,
                f"Joined room: {room_id}",
            )
    
    elif message_type == "leave_room":
        # Leave a room
        room_id = data.get("room_id")
        if room_id:
            await manager.leave_room(connection_id, room_id)
            
            response = {
                "type": "room_left",
                "data": {"room_id": room_id, "status": "success"}
            }
            await manager.active_connections[connection_id].send_text(json.dumps(response))
    
    elif message_type == "seat_selection":
        # Handle seat selection/release
        try:
            seat_update = SeatUpdateMessage(**data)
            
            # Validate showtime exists
            showtime = db.query(Showtime).filter(Showtime.id == seat_update.showtime_id).first()
            if not showtime:
                raise ValueError("Invalid showtime")
            
            # Broadcast seat update to showtime room
            room_id = f"showtime_{seat_update.showtime_id}"
            update_message = {
                "type": "seat_update",
                "data": {
                    "showtime_id": seat_update.showtime_id,
                    "seat": {"row": seat_update.seat_row, "number": seat_update.seat_number},
                    "action": seat_update.action,
                    "user_id": user_id,
                    "username": user_data["username"],
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            await manager.broadcast_to_room(update_message, room_id, exclude_connection=connection_id)
            
            SecurityAuditLogger.log_security_event(
                "websocket_seat_update",
                user_id,
                f"Seat {seat_update.action}: {seat_update.seat_row}{seat_update.seat_number} for showtime {seat_update.showtime_id}",
            )
            
        except Exception as e:
            error_message = {
                "type": "error",
                "data": {"message": "Invalid seat selection data", "error": str(e)}
            }
            await manager.active_connections[connection_id].send_text(json.dumps(error_message))
    
    elif message_type == "ping":
        # Handle ping for connection keep-alive
        pong_message = {
            "type": "pong",
            "data": {"timestamp": datetime.now().isoformat()}
        }
        await manager.active_connections[connection_id].send_text(json.dumps(pong_message))
    
    else:
        # Unknown message type
        error_message = {
            "type": "error",
            "data": {"message": f"Unknown message type: {message_type}"}
        }
        await manager.active_connections[connection_id].send_text(json.dumps(error_message))

# HTTP endpoints for triggering real-time notifications
@app.post("/notifications/booking")
async def send_booking_notification(
    notification: BookingNotification,
    request: Request
):
    """Send booking notification to user"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        message = {
            "type": "booking_notification",
            "data": {
                "booking_id": notification.booking_id,
                "message": InputSanitizer.sanitize_string(notification.message),
                "notification_type": notification.type,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        await manager.send_personal_message(message, notification.user_id)
        
        SecurityAuditLogger.log_security_event(
            "booking_notification_sent",
            notification.user_id,
            f"Booking ID: {notification.booking_id}, Type: {notification.type}",
            client_ip
        )
        
        return {"message": "Notification sent successfully"}
        
    except Exception as e:
        logger.error(f"Error sending booking notification: {e}")
        raise HTTPException(status_code=500, detail="Could not send notification")

@app.post("/notifications/seat-unavailable")
async def notify_seat_unavailable(
    showtime_id: int,
    seat_row: str,
    seat_number: int,
    request: Request
):
    """Notify room about seat becoming unavailable"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        message = {
            "type": "seat_unavailable",
            "data": {
                "showtime_id": showtime_id,
                "seat": {"row": seat_row, "number": seat_number},
                "timestamp": datetime.now().isoformat()
            }
        }
        
        room_id = f"showtime_{showtime_id}"
        await manager.broadcast_to_room(message, room_id)
        
        SecurityAuditLogger.log_security_event(
            "seat_unavailable_notification",
            None,
            f"Seat {seat_row}{seat_number} unavailable for showtime {showtime_id}",
            client_ip
        )
        
        return {"message": "Seat unavailable notification sent"}
        
    except Exception as e:
        logger.error(f"Error sending seat notification: {e}")
        raise HTTPException(status_code=500, detail="Could not send seat notification")

@app.get("/connections/stats")
async def get_connection_stats(request: Request):
    """Get WebSocket connection statistics"""
    try:
        stats = manager.get_connection_stats()
        
        # Log stats access
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "websocket_stats_accessed",
            None,
            f"Stats requested: {stats['total_connections']} connections, {stats['unique_users']} users",
            client_ip
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching connection stats: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch connection statistics")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = manager.get_connection_stats()
    return {
        "status": "healthy",
        "service": "secure-realtime",
        "timestamp": datetime.now().isoformat(),
        "connections": {
            "total": stats["total_connections"],
            "unique_users": stats["unique_users"],
            "active_rooms": stats["active_rooms"]
        },
        "features": [
            "jwt_websocket_auth",
            "real_time_updates",
            "room_management",
            "connection_security",
            "audit_logging",
            "rate_limiting"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Secure Real-time Service")
    uvicorn.run(app, host="127.0.0.1", port=8016)