"""
BookMyMovie Platform - Enhanced Push Notification Service
Advanced notification system with Firebase, OneSignal, Email, and SMS support

Features:
- Firebase Cloud Messaging (FCM)
- OneSignal push notifications  
- Email notifications via SMTP
- SMS notifications via Twilio
- Scheduled notifications with cron jobs
- Notification templates and personalization
- User preference management
- Delivery tracking and analytics
- Real-time notification dashboard
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import sqlite3
from contextlib import asynccontextmanager
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import uuid
import threading
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, EmailStr
import schedule

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Notification Types
class NotificationType(str, Enum):
    BOOKING_CONFIRMATION = "booking_confirmation"
    BOOKING_REMINDER = "booking_reminder"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    NEW_MOVIE_RELEASE = "new_movie_release"
    PROMOTIONAL_OFFER = "promotional_offer"
    SEAT_AVAILABLE = "seat_available"
    SHOW_CANCELLATION = "show_cancellation"
    LOYALTY_REWARD = "loyalty_reward"
    SYSTEM_MAINTENANCE = "system_maintenance"

# Notification Channels
class NotificationChannel(str, Enum):
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"

# Models
class NotificationRequest(BaseModel):
    user_ids: List[int]
    type: NotificationType
    title: str
    body: str
    data: Dict[str, Any] = {}
    channels: List[NotificationChannel] = [NotificationChannel.PUSH]
    schedule_time: Optional[datetime] = None
    action_url: Optional[str] = None

class UserDevice(BaseModel):
    user_id: int
    device_token: str
    platform: str
    app_version: str
    is_active: bool = True
    created_at: datetime

class NotificationPreferences(BaseModel):
    user_id: int
    booking_notifications: bool = True
    promotional_notifications: bool = True
    reminder_notifications: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True

class EnhancedNotificationService:
    def __init__(self):
        self.db_path = "bookmymovie_push_notifications.db"
        self.init_database()
        self.init_templates()
        self.start_scheduler()
        
        # Configuration (use environment variables in production)
        self.firebase_server_key = "your_firebase_server_key_here"
        self.onesignal_app_id = "your_onesignal_app_id_here"
        self.onesignal_api_key = "your_onesignal_api_key_here"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.smtp_email = "noreply@bookmymovie.com"
        self.smtp_password = "your_app_password"
        
        # Stats tracking
        self.stats = {
            "notifications_sent": 0,
            "notifications_delivered": 0,
            "notifications_failed": 0,
            "active_devices": 0
        }
    
    def init_database(self):
        """Initialize notification database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # User devices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    device_token TEXT UNIQUE,
                    platform TEXT,
                    app_version TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Notification preferences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    user_id INTEGER PRIMARY KEY,
                    booking_notifications BOOLEAN DEFAULT 1,
                    promotional_notifications BOOLEAN DEFAULT 1,
                    reminder_notifications BOOLEAN DEFAULT 1,
                    email_notifications BOOLEAN DEFAULT 1,
                    sms_notifications BOOLEAN DEFAULT 0,
                    push_notifications BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Notification history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_history (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    type TEXT,
                    channel TEXT,
                    title TEXT,
                    body TEXT,
                    data TEXT,
                    status TEXT DEFAULT 'sent',
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivered_at TIMESTAMP,
                    clicked_at TIMESTAMP,
                    error_message TEXT
                )
            """)
            
            # Scheduled notifications
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_notifications (
                    id TEXT PRIMARY KEY,
                    user_ids TEXT,
                    type TEXT,
                    title TEXT,
                    body TEXT,
                    data TEXT,
                    channels TEXT,
                    schedule_time TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Notification templates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_templates (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    title TEXT,
                    body TEXT,
                    action_url TEXT,
                    variables TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
            # Generate sample data
            self.generate_sample_data()
            
            logger.info("Enhanced notification database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize notification database: {str(e)}")
            raise
    
    def generate_sample_data(self):
        """Generate sample notification data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if we already have data
            cursor.execute("SELECT COUNT(*) FROM user_devices")
            if cursor.fetchone()[0] > 0:
                conn.close()
                return
            
            # Sample devices
            sample_devices = [
                (1, "device_token_user1_android", "android", "2.1.0"),
                (2, "device_token_user2_ios", "ios", "2.1.0"),
                (3, "device_token_user3_web", "web", "2.1.0"),
                (1, "device_token_user1_web", "web", "2.1.0"),  # User 1 has multiple devices
                (4, "device_token_user4_android", "android", "2.0.5"),
                (5, "device_token_user5_ios", "ios", "2.1.0"),
            ]
            
            cursor.executemany("""
                INSERT INTO user_devices (user_id, device_token, platform, app_version)
                VALUES (?, ?, ?, ?)
            """, sample_devices)
            
            # Sample preferences
            sample_preferences = [
                (1, 1, 1, 1, 1, 0, 1),  # User 1: all notifications enabled except SMS
                (2, 1, 0, 1, 1, 1, 1),  # User 2: no promotional notifications
                (3, 1, 1, 1, 0, 0, 1),  # User 3: no email/SMS
                (4, 1, 1, 0, 1, 0, 1),  # User 4: no reminders
                (5, 0, 0, 0, 0, 0, 1),  # User 5: push only
            ]
            
            cursor.executemany("""
                INSERT INTO notification_preferences 
                (user_id, booking_notifications, promotional_notifications, reminder_notifications,
                 email_notifications, sms_notifications, push_notifications)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, sample_preferences)
            
            # Sample notification history
            sample_history = []
            for i in range(20):
                history_entry = (
                    str(uuid.uuid4()),
                    (i % 5) + 1,  # user_id
                    ["booking_confirmation", "payment_success", "new_movie_release", "promotional_offer"][i % 4],
                    ["push", "email"][i % 2],
                    f"Test Notification {i+1}",
                    f"This is test notification body {i+1}",
                    "{}",
                    ["sent", "delivered", "clicked"][i % 3]
                )
                sample_history.append(history_entry)
            
            cursor.executemany("""
                INSERT INTO notification_history 
                (id, user_id, type, channel, title, body, data, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, sample_history)
            
            conn.commit()
            conn.close()
            
            # Update stats (initialize if not exists)
            if not hasattr(self, 'stats'):
                self.stats = {
                    "notifications_sent": 0,
                    "notifications_delivered": 0,
                    "notifications_failed": 0,
                    "active_devices": 0
                }
            
            self.stats["active_devices"] = len(sample_devices)
            self.stats["notifications_sent"] = len(sample_history)
            self.stats["notifications_delivered"] = len([h for h in sample_history if h[7] in ["delivered", "clicked"]])
            
            logger.info("Sample notification data generated successfully")
            
        except Exception as e:
            logger.error(f"Failed to generate sample data: {str(e)}")
    
    def init_templates(self):
        """Initialize notification templates"""
        self.templates = {
            NotificationType.BOOKING_CONFIRMATION: {
                "title": "🎬 Booking Confirmed!",
                "body": "Your booking for {movie_title} on {show_date} at {cinema_name} has been confirmed. Enjoy the show!",
                "action_url": "/booking/{booking_id}",
                "variables": ["movie_title", "show_date", "cinema_name", "booking_id"]
            },
            NotificationType.BOOKING_REMINDER: {
                "title": "🔔 Show Reminder",
                "body": "Don't forget! Your show {movie_title} starts in {time_remaining} at {cinema_name}",
                "action_url": "/booking/{booking_id}",
                "variables": ["movie_title", "time_remaining", "cinema_name", "booking_id"]
            },
            NotificationType.PAYMENT_SUCCESS: {
                "title": "💳 Payment Successful",
                "body": "Payment of ${amount} for {movie_title} has been processed successfully.",
                "variables": ["amount", "movie_title"]
            },
            NotificationType.NEW_MOVIE_RELEASE: {
                "title": "🍿 New Movie Alert!",
                "body": "New movie '{movie_title}' is now showing! Book your tickets now.",
                "action_url": "/movies/{movie_id}",
                "variables": ["movie_title", "movie_id"]
            },
            NotificationType.PROMOTIONAL_OFFER: {
                "title": "🎉 Special Offer!",
                "body": "{offer_title} - {offer_description}. Use code: {promo_code}",
                "action_url": "/offers/{offer_id}",
                "variables": ["offer_title", "offer_description", "promo_code", "offer_id"]
            },
            NotificationType.LOYALTY_REWARD: {
                "title": "🏆 Loyalty Reward Earned!",
                "body": "Congratulations! You've earned {reward_points} points. Total balance: {total_points} points.",
                "variables": ["reward_points", "total_points"]
            }
        }
    
    def start_scheduler(self):
        """Start background scheduler for periodic tasks"""
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        # Schedule tasks
        schedule.every().minute.do(self.process_scheduled_notifications)
        schedule.every().hour.do(self.send_booking_reminders)
        schedule.every().day.at("10:00").do(self.send_daily_promotions)
        schedule.every().day.at("02:00").do(self.cleanup_old_notifications)
        
        # Start scheduler thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Enhanced notification scheduler started")
    
    async def register_device(self, user_id: int, device_token: str, platform: str, app_version: str) -> bool:
        """Register user device for push notifications"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_devices 
                (user_id, device_token, platform, app_version, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, device_token, platform, app_version))
            
            conn.commit()
            conn.close()
            
            self.stats["active_devices"] += 1
            logger.info(f"Device registered for user {user_id}: {platform}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register device: {str(e)}")
            return False
    
    async def send_push_notification_onesignal(self, user_ids: List[int], title: str, body: str, data: Dict[str, Any] = None, action_url: str = None) -> bool:
        """Send push notification via OneSignal"""
        try:
            # Mock OneSignal API call (replace with actual implementation)
            logger.info(f"OneSignal notification sent to {len(user_ids)} users: {title}")
            self.stats["notifications_sent"] += len(user_ids)
            self.stats["notifications_delivered"] += len(user_ids)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OneSignal notification: {str(e)}")
            self.stats["notifications_failed"] += len(user_ids)
            return False
    
    async def send_email_notification(self, user_id: int, subject: str, body: str, html_body: str = None) -> bool:
        """Send email notification"""
        try:
            # Mock email sending (replace with actual SMTP implementation)
            email = f"user{user_id}@example.com"
            logger.info(f"Email notification sent to {email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    async def send_sms_notification(self, user_id: int, message: str) -> bool:
        """Send SMS notification"""
        try:
            # Mock SMS sending (replace with Twilio implementation)
            phone = f"+1555000{user_id:04d}"
            logger.info(f"SMS notification sent to {phone}: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {str(e)}")
            return False
    
    async def send_notification(self, notification_request: NotificationRequest) -> Dict[str, Any]:
        """Send notification through specified channels"""
        results = {
            "notification_id": str(uuid.uuid4()),
            "sent_to": len(notification_request.user_ids),
            "channels": {},
            "success": True
        }
        
        try:
            # Get template
            template = self.templates.get(notification_request.type, {})
            title = template.get("title", notification_request.title)
            body = template.get("body", notification_request.body)
            
            # Replace variables in template
            if notification_request.data:
                for var, value in notification_request.data.items():
                    title = title.replace(f"{{{var}}}", str(value))
                    body = body.replace(f"{{{var}}}", str(value))
            
            # Send through each channel
            for channel in notification_request.channels:
                channel_success = False
                
                if channel == NotificationChannel.PUSH:
                    channel_success = await self.send_push_notification_onesignal(
                        notification_request.user_ids, title, body, 
                        notification_request.data, notification_request.action_url
                    )
                
                elif channel == NotificationChannel.EMAIL:
                    channel_success = True
                    for user_id in notification_request.user_ids:
                        await self.send_email_notification(user_id, title, body)
                
                elif channel == NotificationChannel.SMS:
                    channel_success = True
                    for user_id in notification_request.user_ids:
                        await self.send_sms_notification(user_id, f"{title}\n{body}")
                
                results["channels"][channel.value] = channel_success
                
                # Store notification history
                for user_id in notification_request.user_ids:
                    await self.store_notification_history(
                        user_id, notification_request.type, channel, title, body,
                        "delivered" if channel_success else "failed"
                    )
        
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            results["success"] = False
            results["error"] = str(e)
        
        return results
    
    async def store_notification_history(self, user_id: int, notification_type: NotificationType, 
                                       channel: NotificationChannel, title: str, body: str, status: str) -> bool:
        """Store notification in history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            notification_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO notification_history 
                (id, user_id, type, channel, title, body, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (notification_id, user_id, notification_type.value, channel.value, title, body, status))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store notification history: {str(e)}")
            return False
    
    def process_scheduled_notifications(self):
        """Process scheduled notifications"""
        logger.info("Processing scheduled notifications...")
        # Implementation would check database for due notifications
    
    def send_booking_reminders(self):
        """Send booking reminders"""
        logger.info("Checking for booking reminders...")
        # Mock reminder for demo
        asyncio.create_task(self.send_notification(NotificationRequest(
            user_ids=[1, 2],
            type=NotificationType.BOOKING_REMINDER,
            title="🔔 Show Reminder",
            body="Your show starts in 2 hours!",
            channels=[NotificationChannel.PUSH]
        )))
    
    def send_daily_promotions(self):
        """Send daily promotions"""
        logger.info("Sending daily promotions...")
        # Mock promotion for demo
        asyncio.create_task(self.send_notification(NotificationRequest(
            user_ids=[1, 2, 3, 4, 5],
            type=NotificationType.PROMOTIONAL_OFFER,
            title="🎉 Daily Deal Alert!",
            body="Get 25% off on weekend shows! Use code: WEEKEND25",
            data={"promo_code": "WEEKEND25", "discount": "25%"},
            channels=[NotificationChannel.PUSH, NotificationChannel.EMAIL]
        )))
    
    def cleanup_old_notifications(self):
        """Clean up old notification history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete notifications older than 30 days
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute(
                "DELETE FROM notification_history WHERE sent_at < ?",
                (cutoff_date,)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old notifications")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {str(e)}")

# Initialize service
notification_service = EnhancedNotificationService()

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BookMyMovie Enhanced Notification Service...")
    yield
    logger.info("Shutting down BookMyMovie Enhanced Notification Service...")

app = FastAPI(
    title="BookMyMovie Enhanced Notification Service",
    description="Advanced Push Notifications, Email & SMS API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "BookMyMovie Enhanced Notification Service",
        "status": "operational",
        "version": "2.0.0",
        "features": [
            "Push Notifications (OneSignal & FCM)",
            "Email Notifications (SMTP)",
            "SMS Notifications (Twilio)",
            "Scheduled Notifications",
            "Notification Templates",
            "User Preferences Management",
            "Delivery Tracking & Analytics",
            "Real-time Dashboard"
        ],
        "statistics": notification_service.stats
    }

@app.post("/devices/register")
async def register_device(user_id: int, device_token: str, platform: str, app_version: str):
    """Register device for push notifications"""
    success = await notification_service.register_device(user_id, device_token, platform, app_version)
    if success:
        return {"status": "Device registered successfully", "user_id": user_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to register device")

@app.post("/notifications/send")
async def send_notification(notification: NotificationRequest):
    """Send immediate notification"""
    result = await notification_service.send_notification(notification)
    return result

@app.get("/notifications/templates")
async def get_templates():
    """Get available notification templates"""
    return {
        "templates": [
            {
                "type": template_type.value,
                "title": template_data["title"],
                "body": template_data["body"],
                "variables": template_data.get("variables", [])
            }
            for template_type, template_data in notification_service.templates.items()
        ]
    }

@app.get("/history/{user_id}")
async def get_notification_history(user_id: int, limit: int = Query(20, ge=1, le=100)):
    """Get notification history for a user"""
    try:
        conn = sqlite3.connect(notification_service.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, type, channel, title, body, status, sent_at
            FROM notification_history 
            WHERE user_id = ? 
            ORDER BY sent_at DESC 
            LIMIT ?
        """, (user_id, limit))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                "id": row[0],
                "type": row[1],
                "channel": row[2],
                "title": row[3],
                "body": row[4],
                "status": row[5],
                "sent_at": row[6]
            })
        
        conn.close()
        return {"user_id": user_id, "history": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@app.get("/preferences/{user_id}")
async def get_notification_preferences(user_id: int):
    """Get notification preferences for a user"""
    try:
        conn = sqlite3.connect(notification_service.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            preferences = {
                "user_id": row[0],
                "booking_notifications": bool(row[1]),
                "promotional_notifications": bool(row[2]),
                "reminder_notifications": bool(row[3]),
                "email_notifications": bool(row[4]),
                "sms_notifications": bool(row[5]),
                "push_notifications": bool(row[6])
            }
        else:
            # Default preferences
            preferences = {
                "user_id": user_id,
                "booking_notifications": True,
                "promotional_notifications": True,
                "reminder_notifications": True,
                "email_notifications": True,
                "sms_notifications": False,
                "push_notifications": True
            }
        
        conn.close()
        return preferences
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")

@app.put("/preferences/{user_id}")
async def update_notification_preferences(user_id: int, preferences: NotificationPreferences):
    """Update notification preferences for a user"""
    try:
        conn = sqlite3.connect(notification_service.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO notification_preferences 
            (user_id, booking_notifications, promotional_notifications, reminder_notifications,
             email_notifications, sms_notifications, push_notifications, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_id,
            preferences.booking_notifications,
            preferences.promotional_notifications,
            preferences.reminder_notifications,
            preferences.email_notifications,
            preferences.sms_notifications,
            preferences.push_notifications
        ))
        
        conn.commit()
        conn.close()
        
        return {"status": "Preferences updated successfully", "user_id": user_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")

@app.post("/notifications/test")
async def send_test_notification(user_id: int, message: str = "Test notification from BookMyMovie! 📱"):
    """Send test notification to a user"""
    notification_request = NotificationRequest(
        user_ids=[user_id],
        type=NotificationType.SYSTEM_MAINTENANCE,
        title="🧪 Test Notification",
        body=message,
        channels=[NotificationChannel.PUSH, NotificationChannel.EMAIL]
    )
    
    result = await notification_service.send_notification(notification_request)
    return result

@app.get("/analytics/dashboard")
async def get_notification_analytics():
    """Get comprehensive notification analytics"""
    try:
        conn = sqlite3.connect(notification_service.db_path)
        cursor = conn.cursor()
        
        # Overall statistics
        cursor.execute("SELECT COUNT(*) FROM notification_history")
        total_notifications = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM notification_history WHERE status = 'delivered'")
        delivered_notifications = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM notification_history WHERE status = 'clicked'")
        clicked_notifications = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_devices WHERE is_active = 1")
        active_devices = cursor.fetchone()[0]
        
        # Notifications by type
        cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM notification_history 
            GROUP BY type
            ORDER BY count DESC
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Notifications by channel
        cursor.execute("""
            SELECT channel, COUNT(*) as count
            FROM notification_history 
            GROUP BY channel
        """)
        by_channel = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Recent notifications
        cursor.execute("""
            SELECT title, body, type, sent_at
            FROM notification_history 
            ORDER BY sent_at DESC 
            LIMIT 10
        """)
        recent_notifications = [
            {
                "title": row[0],
                "body": row[1],
                "type": row[2],
                "sent_at": row[3]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        # Calculate rates
        delivery_rate = (delivered_notifications / total_notifications * 100) if total_notifications > 0 else 0
        click_rate = (clicked_notifications / delivered_notifications * 100) if delivered_notifications > 0 else 0
        
        return {
            "overview": {
                "total_notifications": total_notifications,
                "delivered_notifications": delivered_notifications,
                "clicked_notifications": clicked_notifications,
                "active_devices": active_devices,
                "delivery_rate": round(delivery_rate, 2),
                "click_rate": round(click_rate, 2)
            },
            "by_type": by_type,
            "by_channel": by_channel,
            "recent_notifications": recent_notifications,
            "service_stats": notification_service.stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@app.get("/dashboard", response_class=HTMLResponse)
async def notification_dashboard():
    """Serve notification dashboard"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>📱 Notification Dashboard - BookMyMovie</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header {
                background: rgba(255, 255, 255, 0.95);
                padding: 30px;
                border-radius: 20px;
                margin-bottom: 30px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            .header h1 { color: #2c3e50; font-size: 2.5em; margin-bottom: 10px; }
            .header p { color: #7f8c8d; font-size: 1.1em; }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .metric-card {
                background: rgba(255, 255, 255, 0.95);
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease;
            }
            .metric-card:hover { transform: translateY(-5px); }
            .metric-icon { font-size: 2.5em; margin-bottom: 15px; display: block; }
            .metric-value {
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #3498db, #9b59b6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .metric-label { color: #7f8c8d; font-size: 1.1em; font-weight: 500; }
            .chart-container {
                background: rgba(255, 255, 255, 0.95);
                padding: 30px;
                border-radius: 20px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            .chart-title { font-size: 1.5em; font-weight: 600; color: #2c3e50; margin-bottom: 20px; }
            .refresh-btn {
                background: linear-gradient(45deg, #3498db, #2980b9);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 1em;
                margin-bottom: 20px;
                transition: all 0.3s ease;
            }
            .refresh-btn:hover { transform: translateY(-2px); }
            .loading { text-align: center; padding: 40px; color: #7f8c8d; }
            .activity-feed {
                max-height: 400px;
                overflow-y: auto;
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
            }
            .activity-item {
                display: flex;
                align-items: center;
                padding: 10px 0;
                border-bottom: 1px solid #eee;
            }
            .activity-item:last-child { border-bottom: none; }
            .activity-icon { margin-right: 15px; font-size: 1.5em; }
            .activity-text { flex: 1; }
            .activity-time { color: #888; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📱 Notification Dashboard</h1>
                <p>Real-time push notification analytics and management</p>
            </div>
            
            <button class="refresh-btn" onclick="loadDashboard()">🔄 Refresh Dashboard</button>
            
            <div class="metrics-grid" id="metricsGrid">
                <div class="loading">Loading metrics...</div>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">📊 Notification Types Distribution</h3>
                <canvas id="typeChart" width="400" height="200"></canvas>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">📢 Channel Performance</h3>
                <canvas id="channelChart" width="400" height="200"></canvas>
            </div>
            
            <div class="chart-container">
                <h3 class="chart-title">📋 Recent Activity Feed</h3>
                <div id="activityFeed" class="activity-feed">
                    <div class="loading">Loading recent notifications...</div>
                </div>
            </div>
        </div>

        <script>
            let typeChart, channelChart;

            async function loadDashboard() {
                try {
                    const response = await fetch('/analytics/dashboard');
                    const data = await response.json();
                    
                    updateMetrics(data);
                    updateCharts(data);
                    updateActivityFeed(data);
                    
                } catch (error) {
                    console.error('Failed to load dashboard:', error);
                    document.getElementById('metricsGrid').innerHTML = 
                        '<div style="color: red; text-align: center;">Failed to load dashboard data</div>';
                }
            }

            function updateMetrics(data) {
                const metricsGrid = document.getElementById('metricsGrid');
                const overview = data.overview;
                
                metricsGrid.innerHTML = `
                    <div class="metric-card">
                        <span class="metric-icon">📤</span>
                        <div class="metric-value">${overview.total_notifications}</div>
                        <div class="metric-label">Total Notifications</div>
                    </div>
                    <div class="metric-card">
                        <span class="metric-icon">✅</span>
                        <div class="metric-value">${overview.delivered_notifications}</div>
                        <div class="metric-label">Delivered</div>
                    </div>
                    <div class="metric-card">
                        <span class="metric-icon">👆</span>
                        <div class="metric-value">${overview.clicked_notifications}</div>
                        <div class="metric-label">Clicked</div>
                    </div>
                    <div class="metric-card">
                        <span class="metric-icon">📱</span>
                        <div class="metric-value">${overview.active_devices}</div>
                        <div class="metric-label">Active Devices</div>
                    </div>
                    <div class="metric-card">
                        <span class="metric-icon">🎯</span>
                        <div class="metric-value">${overview.delivery_rate}%</div>
                        <div class="metric-label">Delivery Rate</div>
                    </div>
                    <div class="metric-card">
                        <span class="metric-icon">🔄</span>
                        <div class="metric-value">${overview.click_rate}%</div>
                        <div class="metric-label">Click Rate</div>
                    </div>
                `;
            }

            function updateCharts(data) {
                // Type Chart
                const typeCtx = document.getElementById('typeChart').getContext('2d');
                if (typeChart) typeChart.destroy();
                
                typeChart = new Chart(typeCtx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(data.by_type),
                        datasets: [{
                            data: Object.values(data.by_type),
                            backgroundColor: ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { position: 'right' } }
                    }
                });

                // Channel Chart
                const channelCtx = document.getElementById('channelChart').getContext('2d');
                if (channelChart) channelChart.destroy();
                
                channelChart = new Chart(channelCtx, {
                    type: 'bar',
                    data: {
                        labels: Object.keys(data.by_channel),
                        datasets: [{
                            label: 'Notifications Sent',
                            data: Object.values(data.by_channel),
                            backgroundColor: ['#3498db', '#2ecc71', '#f39c12'],
                            borderRadius: 10
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { display: false } },
                        scales: { y: { beginAtZero: true } }
                    }
                });
            }

            function updateActivityFeed(data) {
                const activityFeed = document.getElementById('activityFeed');
                
                let activityHTML = '';
                data.recent_notifications.forEach(notification => {
                    const typeIcon = getTypeIcon(notification.type);
                    const timeAgo = getTimeAgo(notification.sent_at);
                    
                    activityHTML += `
                        <div class="activity-item">
                            <div class="activity-icon">${typeIcon}</div>
                            <div class="activity-text">
                                <strong>${notification.title}</strong><br>
                                <small>${notification.body.substring(0, 80)}...</small>
                            </div>
                            <div class="activity-time">${timeAgo}</div>
                        </div>
                    `;
                });
                
                activityFeed.innerHTML = activityHTML || '<div class="loading">No recent notifications</div>';
            }

            function getTypeIcon(type) {
                const icons = {
                    'booking_confirmation': '🎬',
                    'booking_reminder': '🔔',
                    'payment_success': '💳',
                    'new_movie_release': '🍿',
                    'promotional_offer': '🎉',
                    'loyalty_reward': '🏆'
                };
                return icons[type] || '📱';
            }

            function getTimeAgo(timestamp) {
                const now = new Date();
                const sent = new Date(timestamp);
                const diffMs = now - sent;
                const diffMins = Math.floor(diffMs / 60000);
                
                if (diffMins < 1) return 'Just now';
                if (diffMins < 60) return `${diffMins}m ago`;
                if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
                return `${Math.floor(diffMins / 1440)}d ago`;
            }

            // Load dashboard on page load
            loadDashboard();
            
            // Auto-refresh every 30 seconds
            setInterval(loadDashboard, 30000);
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "BookMyMovie Enhanced Notification Service",
        "timestamp": datetime.now().isoformat(),
        "scheduler_active": True,
        "statistics": notification_service.stats
    }

if __name__ == "__main__":
    logger.info("Starting BookMyMovie Enhanced Notification Service on port 8018...")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8018,
        log_level="info",
        reload=False
    )