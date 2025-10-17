"""
Payment Gateway Integration Service
Enterprise payment processing with multiple providers
"""

import asyncio
import logging
import json
import hashlib
import hmac
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal
import aiohttp
import stripe
from paypal.paypalrestsdk import Payment as PayPalPayment
import os
from enum import Enum

logger = logging.getLogger(__name__)

class PaymentProvider(Enum):
    """Supported payment providers"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    RAZORPAY = "razorpay"
    SQUARE = "square"
    ADYEN = "adyen"

class PaymentStatus(Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

@dataclass
class PaymentRequest:
    """Payment request data structure"""
    amount: Decimal
    currency: str
    description: str
    customer_email: str
    customer_name: str
    booking_id: str
    provider: PaymentProvider
    metadata: Dict[str, Any] = None
    success_url: str = None
    cancel_url: str = None
    payment_method: str = None

@dataclass
class PaymentResult:
    """Payment processing result"""
    transaction_id: str
    status: PaymentStatus
    provider: PaymentProvider
    amount: Decimal
    currency: str
    provider_response: Dict[str, Any]
    payment_url: str = None
    error_message: str = None
    fees: Decimal = None
    created_at: datetime = None

@dataclass
class RefundRequest:
    """Refund request data structure"""
    transaction_id: str
    amount: Decimal
    reason: str
    provider: PaymentProvider
    metadata: Dict[str, Any] = None

@dataclass
class RefundResult:
    """Refund processing result"""
    refund_id: str
    transaction_id: str
    status: PaymentStatus
    amount: Decimal
    provider_response: Dict[str, Any]
    error_message: str = None
    created_at: datetime = None

class StripePaymentProcessor:
    """Stripe payment processing implementation"""
    
    def __init__(self):
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        self.publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """Process payment through Stripe"""
        try:
            # Create Stripe payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(request.amount * 100),  # Stripe uses cents
                currency=request.currency.lower(),
                description=request.description,
                metadata={
                    'booking_id': request.booking_id,
                    'customer_email': request.customer_email,
                    **(request.metadata or {})
                },
                receipt_email=request.customer_email,
                automatic_payment_methods={'enabled': True}
            )
            
            return PaymentResult(
                transaction_id=payment_intent.id,
                status=PaymentStatus.PENDING,
                provider=PaymentProvider.STRIPE,
                amount=request.amount,
                currency=request.currency,
                provider_response=payment_intent,
                payment_url=None,  # For client-side completion
                created_at=datetime.now()
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment failed: {e}")
            return PaymentResult(
                transaction_id="",
                status=PaymentStatus.FAILED,
                provider=PaymentProvider.STRIPE,
                amount=request.amount,
                currency=request.currency,
                provider_response={},
                error_message=str(e),
                created_at=datetime.now()
            )
    
    async def create_checkout_session(self, request: PaymentRequest) -> PaymentResult:
        """Create Stripe checkout session"""
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': request.currency.lower(),
                        'product_data': {
                            'name': f'Movie Booking - {request.description}',
                        },
                        'unit_amount': int(request.amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.success_url or 'http://localhost:3000/success',
                cancel_url=request.cancel_url or 'http://localhost:3000/cancel',
                customer_email=request.customer_email,
                metadata={
                    'booking_id': request.booking_id,
                    **(request.metadata or {})
                }
            )
            
            return PaymentResult(
                transaction_id=session.id,
                status=PaymentStatus.PENDING,
                provider=PaymentProvider.STRIPE,
                amount=request.amount,
                currency=request.currency,
                provider_response=session,
                payment_url=session.url,
                created_at=datetime.now()
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session failed: {e}")
            return PaymentResult(
                transaction_id="",
                status=PaymentStatus.FAILED,
                provider=PaymentProvider.STRIPE,
                amount=request.amount,
                currency=request.currency,
                provider_response={},
                error_message=str(e),
                created_at=datetime.now()
            )
    
    async def refund_payment(self, request: RefundRequest) -> RefundResult:
        """Process refund through Stripe"""
        try:
            refund = stripe.Refund.create(
                payment_intent=request.transaction_id,
                amount=int(request.amount * 100) if request.amount else None,
                reason=request.reason,
                metadata=request.metadata or {}
            )
            
            return RefundResult(
                refund_id=refund.id,
                transaction_id=request.transaction_id,
                status=PaymentStatus.REFUNDED,
                amount=Decimal(refund.amount) / 100,
                provider_response=refund,
                created_at=datetime.now()
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund failed: {e}")
            return RefundResult(
                refund_id="",
                transaction_id=request.transaction_id,
                status=PaymentStatus.FAILED,
                amount=request.amount,
                provider_response={},
                error_message=str(e),
                created_at=datetime.now()
            )
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return True
        except (ValueError, stripe.error.SignatureVerificationError):
            return False

class PayPalPaymentProcessor:
    """PayPal payment processing implementation"""
    
    def __init__(self):
        self.client_id = os.getenv('PAYPAL_CLIENT_ID')
        self.client_secret = os.getenv('PAYPAL_CLIENT_SECRET')
        self.mode = os.getenv('PAYPAL_MODE', 'sandbox')  # sandbox or live
        self.base_url = "https://api-m.sandbox.paypal.com" if self.mode == 'sandbox' else "https://api-m.paypal.com"
        
    async def get_access_token(self) -> str:
        """Get PayPal access token"""
        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=auth,
                data={'grant_type': 'client_credentials'},
                headers={'Accept': 'application/json'}
            ) as response:
                data = await response.json()
                return data.get('access_token')
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """Process payment through PayPal"""
        try:
            access_token = await self.get_access_token()
            
            payment_data = {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": request.currency.upper(),
                        "value": str(request.amount)
                    },
                    "description": request.description,
                    "custom_id": request.booking_id
                }],
                "application_context": {
                    "return_url": request.success_url or "http://localhost:3000/success",
                    "cancel_url": request.cancel_url or "http://localhost:3000/cancel",
                    "brand_name": "BookMyMovie",
                    "user_action": "PAY_NOW"
                }
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v2/checkout/orders",
                    json=payment_data,
                    headers=headers
                ) as response:
                    data = await response.json()
                    
                    if response.status == 201:
                        # Find approval URL
                        approval_url = None
                        for link in data.get('links', []):
                            if link.get('rel') == 'approve':
                                approval_url = link.get('href')
                                break
                        
                        return PaymentResult(
                            transaction_id=data['id'],
                            status=PaymentStatus.PENDING,
                            provider=PaymentProvider.PAYPAL,
                            amount=request.amount,
                            currency=request.currency,
                            provider_response=data,
                            payment_url=approval_url,
                            created_at=datetime.now()
                        )
                    else:
                        raise Exception(f"PayPal API error: {data}")
            
        except Exception as e:
            logger.error(f"PayPal payment failed: {e}")
            return PaymentResult(
                transaction_id="",
                status=PaymentStatus.FAILED,
                provider=PaymentProvider.PAYPAL,
                amount=request.amount,
                currency=request.currency,
                provider_response={},
                error_message=str(e),
                created_at=datetime.now()
            )
    
    async def capture_payment(self, order_id: str) -> PaymentResult:
        """Capture PayPal payment"""
        try:
            access_token = await self.get_access_token()
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                    headers=headers
                ) as response:
                    data = await response.json()
                    
                    if response.status == 201:
                        capture = data['purchase_units'][0]['payments']['captures'][0]
                        
                        return PaymentResult(
                            transaction_id=capture['id'],
                            status=PaymentStatus.COMPLETED,
                            provider=PaymentProvider.PAYPAL,
                            amount=Decimal(capture['amount']['value']),
                            currency=capture['amount']['currency_code'],
                            provider_response=data,
                            created_at=datetime.now()
                        )
                    else:
                        raise Exception(f"PayPal capture error: {data}")
                        
        except Exception as e:
            logger.error(f"PayPal capture failed: {e}")
            return PaymentResult(
                transaction_id="",
                status=PaymentStatus.FAILED,
                provider=PaymentProvider.PAYPAL,
                amount=Decimal('0'),
                currency="USD",
                provider_response={},
                error_message=str(e),
                created_at=datetime.now()
            )

class RazorpayPaymentProcessor:
    """Razorpay payment processing (popular in India)"""
    
    def __init__(self):
        self.key_id = os.getenv('RAZORPAY_KEY_ID')
        self.key_secret = os.getenv('RAZORPAY_KEY_SECRET')
        self.base_url = "https://api.razorpay.com"
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """Process payment through Razorpay"""
        try:
            auth = aiohttp.BasicAuth(self.key_id, self.key_secret)
            
            order_data = {
                "amount": int(request.amount * 100),  # Razorpay uses paise
                "currency": request.currency.upper(),
                "receipt": request.booking_id,
                "notes": {
                    "booking_id": request.booking_id,
                    "customer_email": request.customer_email,
                    **(request.metadata or {})
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/orders",
                    json=order_data,
                    auth=auth
                ) as response:
                    data = await response.json()
                    
                    if response.status == 200:
                        return PaymentResult(
                            transaction_id=data['id'],
                            status=PaymentStatus.PENDING,
                            provider=PaymentProvider.RAZORPAY,
                            amount=request.amount,
                            currency=request.currency,
                            provider_response=data,
                            created_at=datetime.now()
                        )
                    else:
                        raise Exception(f"Razorpay API error: {data}")
            
        except Exception as e:
            logger.error(f"Razorpay payment failed: {e}")
            return PaymentResult(
                transaction_id="",
                status=PaymentStatus.FAILED,
                provider=PaymentProvider.RAZORPAY,
                amount=request.amount,
                currency=request.currency,
                provider_response={},
                error_message=str(e),
                created_at=datetime.now()
            )

class PaymentGatewayService:
    """Main payment gateway service with multiple providers"""
    
    def __init__(self):
        self.processors = {
            PaymentProvider.STRIPE: StripePaymentProcessor(),
            PaymentProvider.PAYPAL: PayPalPaymentProcessor(),
            PaymentProvider.RAZORPAY: RazorpayPaymentProcessor()
        }
        self.default_provider = PaymentProvider.STRIPE
        
    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """Process payment using specified provider"""
        try:
            processor = self.processors.get(request.provider)
            if not processor:
                raise ValueError(f"Unsupported payment provider: {request.provider}")
            
            # Add fraud detection check
            fraud_check = await self._fraud_detection_check(request)
            if fraud_check['high_risk']:
                return PaymentResult(
                    transaction_id="",
                    status=PaymentStatus.FAILED,
                    provider=request.provider,
                    amount=request.amount,
                    currency=request.currency,
                    provider_response={},
                    error_message="Payment blocked due to fraud detection",
                    created_at=datetime.now()
                )
            
            # Process payment
            result = await processor.process_payment(request)
            
            # Log transaction
            await self._log_transaction(request, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Payment processing failed: {e}")
            return PaymentResult(
                transaction_id="",
                status=PaymentStatus.FAILED,
                provider=request.provider,
                amount=request.amount,
                currency=request.currency,
                provider_response={},
                error_message=str(e),
                created_at=datetime.now()
            )
    
    async def create_checkout_session(self, request: PaymentRequest) -> PaymentResult:
        """Create hosted checkout session"""
        if request.provider == PaymentProvider.STRIPE:
            return await self.processors[PaymentProvider.STRIPE].create_checkout_session(request)
        elif request.provider == PaymentProvider.PAYPAL:
            return await self.processors[PaymentProvider.PAYPAL].process_payment(request)
        else:
            return await self.process_payment(request)
    
    async def refund_payment(self, request: RefundRequest) -> RefundResult:
        """Process refund"""
        try:
            processor = self.processors.get(request.provider)
            if not processor:
                raise ValueError(f"Unsupported payment provider: {request.provider}")
            
            result = await processor.refund_payment(request)
            
            # Log refund
            await self._log_refund(request, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Refund processing failed: {e}")
            return RefundResult(
                refund_id="",
                transaction_id=request.transaction_id,
                status=PaymentStatus.FAILED,
                amount=request.amount,
                provider_response={},
                error_message=str(e),
                created_at=datetime.now()
            )
    
    async def _fraud_detection_check(self, request: PaymentRequest) -> Dict[str, Any]:
        """Basic fraud detection check"""
        risk_factors = []
        
        # Check for unusual amounts
        if request.amount > Decimal('1000'):
            risk_factors.append("high_amount")
        
        # Check email domain
        email_domain = request.customer_email.split('@')[1].lower()
        suspicious_domains = ['tempmail.com', '10minutemail.com', 'guerrillamail.com']
        if email_domain in suspicious_domains:
            risk_factors.append("suspicious_email")
        
        # Simple risk scoring
        risk_score = len(risk_factors) * 0.3
        
        return {
            'risk_score': risk_score,
            'high_risk': risk_score > 0.5,
            'risk_factors': risk_factors
        }
    
    async def _log_transaction(self, request: PaymentRequest, result: PaymentResult):
        """Log payment transaction"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'booking_id': request.booking_id,
            'transaction_id': result.transaction_id,
            'provider': result.provider.value,
            'amount': float(result.amount),
            'currency': result.currency,
            'status': result.status.value,
            'customer_email': request.customer_email
        }
        
        logger.info(f"Payment transaction: {json.dumps(log_data)}")
    
    async def _log_refund(self, request: RefundRequest, result: RefundResult):
        """Log refund transaction"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'transaction_id': request.transaction_id,
            'refund_id': result.refund_id,
            'provider': request.provider.value,
            'amount': float(result.amount),
            'status': result.status.value,
            'reason': request.reason
        }
        
        logger.info(f"Refund transaction: {json.dumps(log_data)}")
    
    async def get_payment_methods(self, provider: PaymentProvider) -> List[Dict[str, Any]]:
        """Get available payment methods for provider"""
        methods = {
            PaymentProvider.STRIPE: [
                {'type': 'card', 'name': 'Credit/Debit Card', 'supported': True},
                {'type': 'bank_transfer', 'name': 'Bank Transfer', 'supported': True},
                {'type': 'digital_wallet', 'name': 'Digital Wallets', 'supported': True}
            ],
            PaymentProvider.PAYPAL: [
                {'type': 'paypal', 'name': 'PayPal Account', 'supported': True},
                {'type': 'card', 'name': 'Credit/Debit Card', 'supported': True}
            ],
            PaymentProvider.RAZORPAY: [
                {'type': 'card', 'name': 'Credit/Debit Card', 'supported': True},
                {'type': 'netbanking', 'name': 'Net Banking', 'supported': True},
                {'type': 'upi', 'name': 'UPI', 'supported': True},
                {'type': 'wallet', 'name': 'Digital Wallets', 'supported': True}
            ]
        }
        
        return methods.get(provider, [])
    
    async def get_transaction_status(self, transaction_id: str, provider: PaymentProvider) -> Dict[str, Any]:
        """Get transaction status from provider"""
        try:
            if provider == PaymentProvider.STRIPE:
                payment_intent = stripe.PaymentIntent.retrieve(transaction_id)
                return {
                    'transaction_id': transaction_id,
                    'status': payment_intent.status,
                    'amount': payment_intent.amount / 100,
                    'currency': payment_intent.currency,
                    'provider': 'stripe'
                }
            
            # Add other providers as needed
            
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return {
                'transaction_id': transaction_id,
                'status': 'unknown',
                'error': str(e)
            }

# Global payment service instance
payment_service = PaymentGatewayService()

# Utility functions
def create_payment_request(
    amount: float,
    currency: str,
    booking_id: str,
    customer_email: str,
    customer_name: str,
    description: str,
    provider: str = "stripe"
) -> PaymentRequest:
    """Create payment request from booking data"""
    return PaymentRequest(
        amount=Decimal(str(amount)),
        currency=currency,
        description=description,
        customer_email=customer_email,
        customer_name=customer_name,
        booking_id=booking_id,
        provider=PaymentProvider(provider)
    )

def create_refund_request(
    transaction_id: str,
    amount: float,
    reason: str,
    provider: str
) -> RefundRequest:
    """Create refund request"""
    return RefundRequest(
        transaction_id=transaction_id,
        amount=Decimal(str(amount)),
        reason=reason,
        provider=PaymentProvider(provider)
    )