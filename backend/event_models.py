"""
Event Models for Microservice Communication

This module defines Pydantic models for events that are emitted between services.
In a production environment, these would typically be serialized and sent via
message queues like Kafka, RabbitMQ, or cloud-based event systems.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Base class for all events in the system."""
    event_id: str = Field(..., description="Unique identifier for this event")
    source_service: str = Field(..., description="The service that emitted this event")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the event was created")
    event_name: str = Field(..., description="Name/type of the event")


class PaymentSucceededEvent(BaseEvent):
    """Event emitted when a payment is successfully processed."""
    event_name: str = Field(default="PaymentSucceeded", description="Event type")
    transaction_id: str = Field(..., description="Payment transaction ID")
    hold_id: str = Field(..., description="The seat hold ID that was paid for")
    user_id: str = Field(..., description="User who made the payment")
    amount_paid: float = Field(..., description="Amount successfully charged")
    payment_method: str = Field(..., description="Payment method used (e.g., 'CreditCard', 'PayPal')")


class PaymentFailedEvent(BaseEvent):
    """Event emitted when a payment fails."""
    event_name: str = Field(default="PaymentFailed", description="Event type")
    transaction_id: str = Field(..., description="Failed payment transaction ID")
    hold_id: str = Field(..., description="The seat hold ID that failed to be paid for")
    user_id: str = Field(..., description="User who attempted the payment")
    reason: str = Field(..., description="Reason for payment failure")


class BookingConfirmedEvent(BaseEvent):
    """Event emitted when a booking is successfully confirmed."""
    event_name: str = Field(default="BookingConfirmed", description="Event type")
    booking_id: str = Field(..., description="Unique booking identifier")
    user_id: str = Field(..., description="User who made the booking")
    movie_id: str = Field(..., description="Movie that was booked")
    showtime_id: str = Field(..., description="Specific showtime booked")
    seats: list[str] = Field(..., description="List of seat identifiers booked")
    total_amount: float = Field(..., description="Total amount paid for the booking")


class BookingCancelledEvent(BaseEvent):
    """Event emitted when a booking is cancelled."""
    event_name: str = Field(default="BookingCancelled", description="Event type")
    booking_id: str = Field(..., description="Booking that was cancelled")
    user_id: str = Field(..., description="User who cancelled or whose booking was cancelled")
    reason: str = Field(..., description="Reason for cancellation")
    refund_amount: Optional[float] = Field(None, description="Amount refunded, if any")


class SeatHoldCreatedEvent(BaseEvent):
    """Event emitted when seats are temporarily held for a user."""
    event_name: str = Field(default="SeatHoldCreated", description="Event type")
    hold_id: str = Field(..., description="Unique hold identifier")
    user_id: str = Field(..., description="User who requested the hold")
    movie_id: str = Field(..., description="Movie for which seats are held")
    showtime_id: str = Field(..., description="Specific showtime")
    seats: list[str] = Field(..., description="List of seat identifiers held")
    expires_at: datetime = Field(..., description="When the hold expires")


class SeatHoldExpiredEvent(BaseEvent):
    """Event emitted when a seat hold expires without payment."""
    event_name: str = Field(default="SeatHoldExpired", description="Event type")
    hold_id: str = Field(..., description="Hold that expired")
    user_id: str = Field(..., description="User whose hold expired")
    seats: list[str] = Field(..., description="Seats that were released")


class NotificationRequestEvent(BaseEvent):
    """Event emitted to request sending a notification to a user."""
    event_name: str = Field(default="NotificationRequest", description="Event type")
    user_id: str = Field(..., description="Target user for the notification")
    notification_type: str = Field(..., description="Type of notification (email, sms, push)")
    subject: str = Field(..., description="Notification subject/title")
    message: str = Field(..., description="Notification content")
    priority: str = Field(default="normal", description="Priority level (low, normal, high)")