"""
Real-time WebSocket Service for BookMyMovie Platform
Live seat availability, booking updates, and instant notifications
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import redis
from models import get_db, Movie, Theater, Screen, Showtime, Booking, User, Notification
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BookMyMovie - Real-time WebSocket Service",
    description="Live updates for seat availability, bookings, and notifications",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis configuration for pub/sub and caching
try:
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_client.ping()
    logger.info("Redis connected successfully")
except redis.ConnectionError:
    logger.warning("Redis not available, using in-memory storage")
    redis_client = None

# Connection management
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "seat_updates": set(),
            "booking_updates": set(),
            "notifications": set(),
            "general": set()
        }
        self.user_connections: Dict[int, WebSocket] = {}
        self.showtime_subscribers: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "general", user_id: int = None, showtime_id: int = None):
        await websocket.accept()
        
        # Add to general channel
        if channel in self.active_connections:
            self.active_connections[channel].add(websocket)
        
        # Track user connection
        if user_id:
            self.user_connections[user_id] = websocket
        
        # Subscribe to showtime updates
        if showtime_id:
            if showtime_id not in self.showtime_subscribers:
                self.showtime_subscribers[showtime_id] = set()
            self.showtime_subscribers[showtime_id].add(websocket)
        
        logger.info(f"New WebSocket connection on channel: {channel}")

    def disconnect(self, websocket: WebSocket):
        # Remove from all channels
        for channel_connections in self.active_connections.values():
            channel_connections.discard(websocket)
        
        # Remove from user connections
        user_id_to_remove = None
        for user_id, connection in self.user_connections.items():
            if connection == websocket:
                user_id_to_remove = user_id
                break
        if user_id_to_remove:
            del self.user_connections[user_id_to_remove]
        
        # Remove from showtime subscriptions
        for showtime_id, subscribers in self.showtime_subscribers.items():
            subscribers.discard(websocket)
        
        logger.info("WebSocket connection closed")

    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast message to all connections in a channel"""
        if channel not in self.active_connections:
            return
        
        message_str = json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "channel": channel,
            **message
        })
        
        disconnected = set()
        for connection in self.active_connections[channel].copy():
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send message to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def send_to_user(self, user_id: int, message: dict):
        """Send message to specific user"""
        if user_id in self.user_connections:
            connection = self.user_connections[user_id]
            message_str = json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "type": "personal",
                **message
            })
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                self.disconnect(connection)

    async def broadcast_to_showtime(self, showtime_id: int, message: dict):
        """Broadcast message to all users watching a specific showtime"""
        if showtime_id not in self.showtime_subscribers:
            return
        
        message_str = json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "showtime_id": showtime_id,
            **message
        })
        
        disconnected = set()
        for connection in self.showtime_subscribers[showtime_id].copy():
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"Failed to send showtime message: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Pydantic Models for WebSocket messages
class SeatUpdateMessage(BaseModel):
    type: str = "seat_update"
    showtime_id: int
    seats: List[Dict[str, Any]]
    available_count: int
    total_count: int

class BookingUpdateMessage(BaseModel):
    type: str = "booking_update"
    booking_id: int
    user_id: int
    status: str
    seats: List[Dict[str, Any]]
    showtime_id: int

class NotificationMessage(BaseModel):
    type: str = "notification"
    user_id: int
    title: str
    message: str
    notification_type: str
    is_read: bool = False

# WebSocket endpoints
@app.websocket("/ws/seats/{showtime_id}")
async def websocket_seat_updates(websocket: WebSocket, showtime_id: int):
    """WebSocket endpoint for real-time seat availability updates"""
    await manager.connect(websocket, "seat_updates", showtime_id=showtime_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle seat selection requests
            if message.get("action") == "select_seats":
                await handle_seat_selection(showtime_id, message, websocket)
            elif message.get("action") == "release_seats":
                await handle_seat_release(showtime_id, message, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/bookings/{user_id}")
async def websocket_booking_updates(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for user-specific booking updates"""
    await manager.connect(websocket, "booking_updates", user_id=user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            # Handle any booking-related messages from client
            message = json.loads(data)
            logger.info(f"Received booking message from user {user_id}: {message}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time notifications"""
    await manager.connect(websocket, "notifications", user_id=user_id)
    
    try:
        # Send unread notifications on connect
        db = next(get_db())
        unread_notifications = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).order_by(Notification.sent_at.desc()).limit(10).all()
        
        for notification in unread_notifications:
            await manager.send_to_user(user_id, {
                "type": "notification",
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "notification_type": notification.notification_type,
                "sent_at": notification.sent_at.isoformat()
            })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle notification read status updates
            if message.get("action") == "mark_read":
                await mark_notification_read(user_id, message.get("notification_id"))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Helper functions
async def handle_seat_selection(showtime_id: int, message: dict, websocket: WebSocket):
    """Handle temporary seat selection"""
    seats = message.get("seats", [])
    user_session = message.get("session_id")
    
    # Store temporary seat hold in Redis (5 minutes)
    if redis_client:
        for seat in seats:
            seat_key = f"seat_hold:{showtime_id}:{seat['row']}{seat['number']}"
            redis_client.setex(seat_key, 300, user_session)  # 5 minutes
    
    # Broadcast seat update to all subscribers
    await manager.broadcast_to_showtime(showtime_id, {
        "type": "seat_selection",
        "seats": seats,
        "action": "selected",
        "session_id": user_session
    })

async def handle_seat_release(showtime_id: int, message: dict, websocket: WebSocket):
    """Handle seat release"""
    seats = message.get("seats", [])
    user_session = message.get("session_id")
    
    # Remove temporary seat hold from Redis
    if redis_client:
        for seat in seats:
            seat_key = f"seat_hold:{showtime_id}:{seat['row']}{seat['number']}"
            redis_client.delete(seat_key)
    
    # Broadcast seat update to all subscribers
    await manager.broadcast_to_showtime(showtime_id, {
        "type": "seat_selection",
        "seats": seats,
        "action": "released",
        "session_id": user_session
    })

async def mark_notification_read(user_id: int, notification_id: int):
    """Mark notification as read"""
    db = next(get_db())
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            
            # Broadcast read status update
            await manager.send_to_user(user_id, {
                "type": "notification_read",
                "notification_id": notification_id
            })
    
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        db.rollback()
    finally:
        db.close()

# HTTP endpoints for triggering WebSocket events
@app.post("/api/realtime/seat-update/{showtime_id}")
async def trigger_seat_update(showtime_id: int, db: Session = Depends(get_db)):
    """Trigger real-time seat availability update"""
    try:
        # Get current seat availability
        showtime = db.query(Showtime).filter(Showtime.id == showtime_id).first()
        if not showtime:
            raise HTTPException(status_code=404, detail="Showtime not found")
        
        # Get booked seats
        bookings = db.query(Booking).filter(
            Booking.showtime_id == showtime_id,
            Booking.status.in_(["confirmed", "pending"])
        ).all()
        
        booked_seats = []
        for booking in bookings:
            if booking.seats:
                booked_seats.extend(booking.seats)
        
        # Broadcast update
        await manager.broadcast_to_showtime(showtime_id, {
            "type": "seat_availability_update",
            "showtime_id": showtime_id,
            "available_seats": showtime.available_seats,
            "total_seats": showtime.total_seats,
            "booked_seats": booked_seats
        })
        
        return {"message": "Seat update broadcasted"}
        
    except Exception as e:
        logger.error(f"Error triggering seat update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/realtime/booking-update")
async def trigger_booking_update(booking_data: dict):
    """Trigger real-time booking update"""
    try:
        user_id = booking_data.get("user_id")
        booking_id = booking_data.get("booking_id")
        status = booking_data.get("status")
        showtime_id = booking_data.get("showtime_id")
        
        # Send update to user
        await manager.send_to_user(user_id, {
            "type": "booking_status_update",
            "booking_id": booking_id,
            "status": status,
            "showtime_id": showtime_id
        })
        
        # Broadcast to showtime subscribers if seats are affected
        if status in ["confirmed", "cancelled"]:
            await trigger_seat_update(showtime_id)
        
        return {"message": "Booking update sent"}
        
    except Exception as e:
        logger.error(f"Error triggering booking update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/realtime/notification")
async def send_notification(notification_data: dict, db: Session = Depends(get_db)):
    """Send real-time notification to user"""
    try:
        user_id = notification_data.get("user_id")
        title = notification_data.get("title")
        message = notification_data.get("message")
        notification_type = notification_data.get("type", "general")
        
        # Create notification in database
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            sent_at=datetime.utcnow()
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Send real-time notification
        await manager.send_to_user(user_id, {
            "type": "new_notification",
            "id": notification.id,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "sent_at": notification.sent_at.isoformat()
        })
        
        return {"message": "Notification sent", "notification_id": notification.id}
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint
@app.get("/health")
async def health_check():
    redis_status = "connected" if redis_client else "not available"
    return {
        "status": "healthy",
        "service": "Real-time WebSocket Service",
        "version": "2.0.0",
        "redis": redis_status,
        "active_connections": sum(len(conns) for conns in manager.active_connections.values()),
        "timestamp": datetime.utcnow()
    }

# Statistics endpoint
@app.get("/api/realtime/stats")
async def get_realtime_stats():
    """Get real-time service statistics"""
    return {
        "active_connections": {
            channel: len(connections) 
            for channel, connections in manager.active_connections.items()
        },
        "user_connections": len(manager.user_connections),
        "showtime_subscriptions": len(manager.showtime_subscribers),
        "redis_available": redis_client is not None,
        "timestamp": datetime.utcnow()
    }

# Background tasks for periodic updates
async def periodic_cleanup():
    """Periodic cleanup of expired seat holds"""
    while True:
        try:
            if redis_client:
                # Clean up expired seat holds
                logger.info("Running periodic cleanup of expired seat holds")
            
            await asyncio.sleep(60)  # Run every minute
            
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
            await asyncio.sleep(60)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(periodic_cleanup())
    logger.info("Real-time WebSocket service started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8008)