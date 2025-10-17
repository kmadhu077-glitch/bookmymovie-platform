"""
Communication Services Integration
Integration with email (SendGrid), SMS (Twilio), push notifications (FCM)
"""

import asyncio
import aiohttp
import smtplib
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push_notification"
    WEBHOOK = "webhook"

class MessagePriority(Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class MessageStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    COMPLAINED = "complained"

@dataclass
class Attachment:
    """Email attachment structure"""
    filename: str
    content: bytes
    content_type: str

@dataclass
class MessageRequest:
    """Unified message request structure"""
    recipient: str  # email, phone, or device token
    subject: str = None  # For email
    content: str = ""
    message_type: MessageType = MessageType.EMAIL
    priority: MessagePriority = MessagePriority.NORMAL
    template_id: str = None
    template_data: Dict[str, Any] = None
    attachments: List[Attachment] = None
    sender_name: str = None
    reply_to: str = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class MessageResult:
    """Message sending result"""
    success: bool
    message_id: str = None
    status: MessageStatus = MessageStatus.PENDING
    error_message: str = None
    provider_response: Dict[str, Any] = None
    timestamp: datetime = None

class SendGridService:
    """SendGrid email service integration"""
    
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@bookmymovie.com')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'BookMyMovie')
        self.base_url = "https://api.sendgrid.com/v3"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_email(self, request: MessageRequest) -> MessageResult:
        """Send email via SendGrid API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Build email payload
            payload = {
                'personalizations': [{
                    'to': [{'email': request.recipient}],
                    'subject': request.subject
                }],
                'from': {
                    'email': self.from_email,
                    'name': request.sender_name or self.from_name
                },
                'content': [{
                    'type': 'text/html',
                    'value': request.content
                }]
            }
            
            # Add reply-to if specified
            if request.reply_to:
                payload['reply_to'] = {'email': request.reply_to}
            
            # Add template if specified
            if request.template_id:
                payload['template_id'] = request.template_id
                if request.template_data:
                    payload['personalizations'][0]['dynamic_template_data'] = request.template_data
            
            # Add attachments if any
            if request.attachments:
                payload['attachments'] = []
                for attachment in request.attachments:
                    payload['attachments'].append({
                        'content': base64.b64encode(attachment.content).decode(),
                        'filename': attachment.filename,
                        'type': attachment.content_type,
                        'disposition': 'attachment'
                    })
            
            # Add tags and metadata
            if request.tags:
                payload['categories'] = request.tags
            
            if request.metadata:
                payload['custom_args'] = request.metadata
            
            async with self.session.post(f"{self.base_url}/mail/send", headers=headers, json=payload) as response:
                if response.status in [200, 202]:
                    message_id = response.headers.get('X-Message-Id', f"sg_{datetime.now().timestamp()}")
                    return MessageResult(
                        success=True,
                        message_id=message_id,
                        status=MessageStatus.SENT,
                        timestamp=datetime.now()
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"SendGrid API error: {response.status} - {error_text}")
                    return MessageResult(
                        success=False,
                        status=MessageStatus.FAILED,
                        error_message=f"SendGrid API error: {response.status}",
                        provider_response={'status': response.status, 'error': error_text},
                        timestamp=datetime.now()
                    )
        
        except Exception as e:
            logger.error(f"SendGrid email send failed: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def send_template_email(self, recipient: str, template_id: str, template_data: Dict[str, Any], 
                                subject: str = None, sender_name: str = None) -> MessageResult:
        """Send templated email"""
        request = MessageRequest(
            recipient=recipient,
            subject=subject,
            message_type=MessageType.EMAIL,
            template_id=template_id,
            template_data=template_data,
            sender_name=sender_name
        )
        
        return await self.send_email(request)
    
    async def get_email_stats(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get email delivery statistics"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            async with self.session.get(f"{self.base_url}/stats", headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get SendGrid stats: {response.status}")
                    return {}
        
        except Exception as e:
            logger.error(f"Failed to get SendGrid stats: {e}")
            return {}

class TwilioService:
    """Twilio SMS service integration"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_FROM_NUMBER')
        self.client = None
        
        if self.account_sid and self.auth_token:
            self.client = TwilioClient(self.account_sid, self.auth_token)
    
    async def send_sms(self, request: MessageRequest) -> MessageResult:
        """Send SMS via Twilio"""
        try:
            if not self.client:
                return MessageResult(
                    success=False,
                    status=MessageStatus.FAILED,
                    error_message="Twilio client not configured",
                    timestamp=datetime.now()
                )
            
            # Send SMS
            message = self.client.messages.create(
                body=request.content,
                from_=self.from_number,
                to=request.recipient
            )
            
            return MessageResult(
                success=True,
                message_id=message.sid,
                status=MessageStatus.SENT,
                provider_response={'sid': message.sid, 'status': message.status},
                timestamp=datetime.now()
            )
        
        except TwilioException as e:
            logger.error(f"Twilio SMS send failed: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                timestamp=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get SMS message status"""
        try:
            if not self.client:
                return {'error': 'Twilio client not configured'}
            
            message = self.client.messages(message_sid).fetch()
            
            return {
                'sid': message.sid,
                'status': message.status,
                'direction': message.direction,
                'from': message.from_,
                'to': message.to,
                'body': message.body,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'date_created': message.date_created.isoformat() if message.date_created else None,
                'date_sent': message.date_sent.isoformat() if message.date_sent else None,
                'date_updated': message.date_updated.isoformat() if message.date_updated else None
            }
        
        except Exception as e:
            logger.error(f"Failed to get Twilio message status: {e}")
            return {'error': str(e)}
    
    async def send_bulk_sms(self, recipients: List[str], content: str) -> List[MessageResult]:
        """Send SMS to multiple recipients"""
        results = []
        
        for recipient in recipients:
            request = MessageRequest(
                recipient=recipient,
                content=content,
                message_type=MessageType.SMS
            )
            result = await self.send_sms(request)
            results.append(result)
            
            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        
        return results

class FirebaseCloudMessagingService:
    """Firebase Cloud Messaging (FCM) for push notifications"""
    
    def __init__(self):
        self.server_key = os.getenv('FCM_SERVER_KEY')
        self.base_url = "https://fcm.googleapis.com/fcm/send"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_push_notification(self, request: MessageRequest) -> MessageResult:
        """Send push notification via FCM"""
        try:
            headers = {
                'Authorization': f'key={self.server_key}',
                'Content-Type': 'application/json'
            }
            
            # Build FCM payload
            payload = {
                'to': request.recipient,  # Device token
                'notification': {
                    'title': request.subject,
                    'body': request.content,
                },
                'data': request.metadata or {}
            }
            
            # Set priority
            if request.priority == MessagePriority.HIGH or request.priority == MessagePriority.URGENT:
                payload['priority'] = 'high'
            else:
                payload['priority'] = 'normal'
            
            async with self.session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    if response_data.get('success', 0) > 0:
                        return MessageResult(
                            success=True,
                            message_id=response_data.get('multicast_id'),
                            status=MessageStatus.SENT,
                            provider_response=response_data,
                            timestamp=datetime.now()
                        )
                    else:
                        error_msg = response_data.get('results', [{}])[0].get('error', 'Unknown FCM error')
                        return MessageResult(
                            success=False,
                            status=MessageStatus.FAILED,
                            error_message=error_msg,
                            provider_response=response_data,
                            timestamp=datetime.now()
                        )
                else:
                    error_text = await response.text()
                    return MessageResult(
                        success=False,
                        status=MessageStatus.FAILED,
                        error_message=f"FCM API error: {response.status}",
                        provider_response={'status': response.status, 'error': error_text},
                        timestamp=datetime.now()
                    )
        
        except Exception as e:
            logger.error(f"FCM push notification failed: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def send_topic_notification(self, topic: str, title: str, body: str, 
                                    data: Dict[str, Any] = None) -> MessageResult:
        """Send notification to a topic"""
        try:
            headers = {
                'Authorization': f'key={self.server_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'to': f'/topics/{topic}',
                'notification': {
                    'title': title,
                    'body': body,
                },
                'data': data or {}
            }
            
            async with self.session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return MessageResult(
                        success=True,
                        message_id=response_data.get('message_id'),
                        status=MessageStatus.SENT,
                        provider_response=response_data,
                        timestamp=datetime.now()
                    )
                else:
                    error_text = await response.text()
                    return MessageResult(
                        success=False,
                        status=MessageStatus.FAILED,
                        error_message=f"FCM topic notification failed: {response.status}",
                        provider_response={'status': response.status, 'error': error_text},
                        timestamp=datetime.now()
                    )
        
        except Exception as e:
            logger.error(f"FCM topic notification failed: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                timestamp=datetime.now()
            )

class CommunicationService:
    """Unified communication service orchestrator"""
    
    def __init__(self):
        self.email_service = SendGridService()
        self.sms_service = TwilioService()
        self.push_service = FirebaseCloudMessagingService()
        
        # Message templates
        self.templates = {
            'booking_confirmation': {
                'email': {
                    'subject': 'Booking Confirmation - {movie_title}',
                    'template': 'booking_confirmation_email'
                },
                'sms': {
                    'template': 'Your booking for {movie_title} on {show_date} at {cinema_name} is confirmed. Booking ID: {booking_id}'
                },
                'push': {
                    'title': 'Booking Confirmed',
                    'body': 'Your tickets for {movie_title} are ready!'
                }
            },
            'booking_reminder': {
                'email': {
                    'subject': 'Movie Reminder - {movie_title} Today!',
                    'template': 'booking_reminder_email'
                },
                'sms': {
                    'template': 'Reminder: {movie_title} today at {show_time} at {cinema_name}. Show your booking ID: {booking_id}'
                },
                'push': {
                    'title': 'Movie Reminder',
                    'body': "Don't forget! {movie_title} starts in 2 hours"
                }
            },
            'payment_success': {
                'email': {
                    'subject': 'Payment Successful - BookMyMovie',
                    'template': 'payment_success_email'
                },
                'sms': {
                    'template': 'Payment of ${amount} successful for {movie_title}. Booking confirmed!'
                }
            },
            'new_movie_alert': {
                'email': {
                    'subject': 'New Movie Alert - {movie_title}',
                    'template': 'new_movie_alert_email'
                },
                'push': {
                    'title': 'New Movie Available',
                    'body': '{movie_title} is now showing! Book your tickets now.'
                }
            }
        }
    
    async def send_message(self, request: MessageRequest) -> MessageResult:
        """Send message via appropriate service"""
        try:
            if request.message_type == MessageType.EMAIL:
                async with self.email_service as service:
                    return await service.send_email(request)
            
            elif request.message_type == MessageType.SMS:
                return await self.sms_service.send_sms(request)
            
            elif request.message_type == MessageType.PUSH:
                async with self.push_service as service:
                    return await service.send_push_notification(request)
            
            else:
                return MessageResult(
                    success=False,
                    status=MessageStatus.FAILED,
                    error_message=f"Unsupported message type: {request.message_type}",
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            logger.error(f"Message send failed: {e}")
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def send_multi_channel_notification(
        self, 
        user_id: str,
        template_name: str, 
        template_data: Dict[str, Any],
        channels: List[MessageType] = None,
        user_preferences: Dict[str, Any] = None
    ) -> Dict[MessageType, MessageResult]:
        """Send notification across multiple channels"""
        
        results = {}
        channels = channels or [MessageType.EMAIL, MessageType.SMS, MessageType.PUSH]
        
        # Get user contact information (this would come from your user service)
        user_contacts = await self._get_user_contacts(user_id, user_preferences)
        
        template = self.templates.get(template_name)
        if not template:
            error_result = MessageResult(
                success=False,
                status=MessageStatus.FAILED,
                error_message=f"Template {template_name} not found",
                timestamp=datetime.now()
            )
            return {channel: error_result for channel in channels}
        
        # Send via each requested channel
        tasks = []
        
        for channel in channels:
            if channel in template and user_contacts.get(channel.value):
                request = self._build_message_request(
                    channel, 
                    template[channel.value], 
                    template_data, 
                    user_contacts[channel.value]
                )
                tasks.append(self._send_with_channel_type(channel, request))
        
        # Execute all sends concurrently
        if tasks:
            channel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Map results back to channels
            channel_index = 0
            for channel in channels:
                if channel.value in template and user_contacts.get(channel.value):
                    result = channel_results[channel_index]
                    if isinstance(result, Exception):
                        results[channel] = MessageResult(
                            success=False,
                            status=MessageStatus.FAILED,
                            error_message=str(result),
                            timestamp=datetime.now()
                        )
                    else:
                        results[channel] = result
                    channel_index += 1
        
        return results
    
    async def _send_with_channel_type(self, channel: MessageType, request: MessageRequest) -> MessageResult:
        """Send message with specific channel type"""
        request.message_type = channel
        return await self.send_message(request)
    
    def _build_message_request(
        self, 
        channel: MessageType, 
        template_config: Dict[str, Any], 
        data: Dict[str, Any], 
        recipient: str
    ) -> MessageRequest:
        """Build message request from template"""
        
        if channel == MessageType.EMAIL:
            subject = template_config.get('subject', '').format(**data)
            content = self._render_email_template(template_config.get('template'), data)
            
            return MessageRequest(
                recipient=recipient,
                subject=subject,
                content=content,
                message_type=channel,
                template_id=template_config.get('sendgrid_template_id'),
                template_data=data if template_config.get('sendgrid_template_id') else None
            )
        
        elif channel == MessageType.SMS:
            content = template_config.get('template', '').format(**data)
            
            return MessageRequest(
                recipient=recipient,
                content=content,
                message_type=channel
            )
        
        elif channel == MessageType.PUSH:
            title = template_config.get('title', '').format(**data)
            body = template_config.get('body', '').format(**data)
            
            return MessageRequest(
                recipient=recipient,
                subject=title,
                content=body,
                message_type=channel,
                metadata=data
            )
        
        return MessageRequest(recipient=recipient, content="", message_type=channel)
    
    def _render_email_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render email template (placeholder implementation)"""
        # This would integrate with your template engine (Jinja2, etc.)
        # For now, return a basic HTML template
        
        basic_templates = {
            'booking_confirmation_email': f"""
            <html>
                <body>
                    <h2>Booking Confirmation</h2>
                    <p>Dear {data.get('user_name', 'Customer')},</p>
                    <p>Your booking for <strong>{data.get('movie_title')}</strong> has been confirmed.</p>
                    <p><strong>Details:</strong></p>
                    <ul>
                        <li>Movie: {data.get('movie_title')}</li>
                        <li>Date: {data.get('show_date')}</li>
                        <li>Time: {data.get('show_time')}</li>
                        <li>Cinema: {data.get('cinema_name')}</li>
                        <li>Seats: {data.get('seats')}</li>
                        <li>Booking ID: {data.get('booking_id')}</li>
                    </ul>
                    <p>Thank you for choosing BookMyMovie!</p>
                </body>
            </html>
            """,
            'booking_reminder_email': f"""
            <html>
                <body>
                    <h2>Movie Reminder</h2>
                    <p>Dear {data.get('user_name', 'Customer')},</p>
                    <p>This is a reminder that you have tickets for <strong>{data.get('movie_title')}</strong> today!</p>
                    <p><strong>Show Details:</strong></p>
                    <ul>
                        <li>Time: {data.get('show_time')}</li>
                        <li>Cinema: {data.get('cinema_name')}</li>
                        <li>Seats: {data.get('seats')}</li>
                    </ul>
                    <p>Don't forget to arrive 15 minutes early. Enjoy the show!</p>
                </body>
            </html>
            """
        }
        
        return basic_templates.get(template_name, f"<p>{data}</p>")
    
    async def _get_user_contacts(self, user_id: str, preferences: Dict[str, Any] = None) -> Dict[str, str]:
        """Get user contact information (placeholder implementation)"""
        # This would integrate with your user service to get actual contact info
        # For now, return dummy data
        
        return {
            'email': f'user_{user_id}@example.com',
            'sms': f'+1234567890',  # Would be real phone number
            'push': f'device_token_{user_id}'  # Would be real FCM token
        }
    
    async def get_message_analytics(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get communication analytics across all services"""
        analytics = {}
        
        # Get email stats
        async with self.email_service as service:
            analytics['email'] = await service.get_email_stats(start_date, end_date)
        
        # Add SMS and push analytics here when available
        analytics['sms'] = {'placeholder': 'SMS analytics would go here'}
        analytics['push'] = {'placeholder': 'Push notification analytics would go here'}
        
        return analytics

# Global communication service instance
communication_service = CommunicationService()

# Utility functions for common use cases
async def send_booking_confirmation(user_id: str, booking_data: Dict[str, Any], channels: List[MessageType] = None):
    """Send booking confirmation across specified channels"""
    return await communication_service.send_multi_channel_notification(
        user_id=user_id,
        template_name='booking_confirmation',
        template_data=booking_data,
        channels=channels or [MessageType.EMAIL, MessageType.SMS]
    )

async def send_movie_reminder(user_id: str, booking_data: Dict[str, Any]):
    """Send movie reminder notifications"""
    return await communication_service.send_multi_channel_notification(
        user_id=user_id,
        template_name='booking_reminder',
        template_data=booking_data,
        channels=[MessageType.EMAIL, MessageType.SMS, MessageType.PUSH]
    )

async def send_payment_notification(user_id: str, payment_data: Dict[str, Any]):
    """Send payment success notification"""
    return await communication_service.send_multi_channel_notification(
        user_id=user_id,
        template_name='payment_success',
        template_data=payment_data,
        channels=[MessageType.EMAIL, MessageType.SMS]
    )

async def send_new_movie_alert(user_ids: List[str], movie_data: Dict[str, Any]):
    """Send new movie alerts to multiple users"""
    results = {}
    
    for user_id in user_ids:
        results[user_id] = await communication_service.send_multi_channel_notification(
            user_id=user_id,
            template_name='new_movie_alert',
            template_data=movie_data,
            channels=[MessageType.EMAIL, MessageType.PUSH]
        )
    
    return results