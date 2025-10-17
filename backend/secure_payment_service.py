"""
Secure Payment Service for BookMyMovie Platform
PCI Compliance, JWT Authentication, Fraud Detection, and Transaction Security
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from pydantic import BaseModel, Field, validator
from decimal import Decimal
import hashlib
import hmac
import secrets
import uuid
import re

# Import security middleware
from security_middleware import (
    SecurityMiddleware, get_current_user, get_current_admin,
    InputSanitizer, SecurityAuditLogger, require_permission,
    add_security_headers
)
from models import get_db, Payment, Booking, User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BookMyMovie - Secure Payment Service",
    description="PCI-compliant payment processing with fraud detection and security monitoring",
    version="3.0.0"
)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# CORS middleware with security considerations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Total-Count", "X-Rate-Limit-Remaining"]
)

# PCI Compliance Models (Never store full card numbers)
class CardToken(BaseModel):
    """Tokenized card representation for PCI compliance"""
    token: str = Field(..., pattern=r'^[a-zA-Z0-9]{32}$')
    last_four: str = Field(..., pattern=r'^\d{4}$')
    card_type: str = Field(..., pattern=r'^(visa|mastercard|amex|discover)$')
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2025, le=2035)

class PaymentMethodCreate(BaseModel):
    card_number: str = Field(..., pattern=r'^\d{16}$', description="16-digit card number")
    cvv: str = Field(..., pattern=r'^\d{3,4}$', description="3 or 4 digit CVV")
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2025, le=2035)
    cardholder_name: str = Field(..., max_length=100)
    billing_address: Dict[str, str]
    
    @validator('card_number')
    def validate_card_number(cls, v):
        # Luhn algorithm validation
        def luhn_check(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10 == 0
        
        if not luhn_check(v):
            raise ValueError('Invalid card number')
        return v
    
    @validator('cardholder_name')
    def validate_cardholder_name(cls, v):
        if not re.match(r'^[a-zA-Z\s]{2,100}$', v):
            raise ValueError('Cardholder name must contain only letters and spaces')
        return v.upper()

class PaymentRequest(BaseModel):
    booking_id: int
    payment_method_token: str = Field(..., pattern=r'^[a-zA-Z0-9]{32}$')
    amount: Decimal = Field(..., gt=0, le=10000)
    currency: str = Field(default="USD", pattern=r'^[A-Z]{3}$')
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 10000:  # $100 maximum
            raise ValueError('Amount exceeds maximum limit')
        return v

class RefundRequest(BaseModel):
    payment_id: int
    amount: Optional[Decimal] = None  # Partial refund if specified
    reason: str = Field(..., max_length=500)
    
    @validator('reason')
    def validate_reason(cls, v):
        return InputSanitizer.sanitize_string(v)

class PaymentResponse(BaseModel):
    id: int
    booking_id: int
    user_id: int
    amount: float
    currency: str
    payment_method: str
    payment_status: str
    transaction_id: str
    gateway_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class FraudAnalysis(BaseModel):
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., pattern=r'^(low|medium|high|critical)$')
    flags: List[str] = []
    recommendation: str

# Payment Gateway Simulation (Replace with actual gateway in production)
class PaymentGateway:
    """Simulated payment gateway for demo purposes"""
    
    @staticmethod
    def tokenize_card(card_data: PaymentMethodCreate) -> CardToken:
        """Create a secure token for the card (PCI compliance)"""
        # In production, use actual payment gateway tokenization
        token = secrets.token_hex(16)
        
        # Determine card type from number
        first_digit = card_data.card_number[0]
        if first_digit == '4':
            card_type = 'visa'
        elif first_digit == '5':
            card_type = 'mastercard'
        elif first_digit == '3':
            card_type = 'amex'
        else:
            card_type = 'discover'
        
        return CardToken(
            token=token,
            last_four=card_data.card_number[-4:],
            card_type=card_type,
            expiry_month=card_data.expiry_month,
            expiry_year=card_data.expiry_year
        )
    
    @staticmethod
    def process_payment(token: str, amount: Decimal) -> Dict[str, Any]:
        """Process payment using tokenized card"""
        # Simulate payment processing
        transaction_id = f"TXN{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(4).upper()}"
        
        # Simulate different outcomes
        import random
        success_rate = 0.95  # 95% success rate
        
        if random.random() < success_rate:
            return {
                "status": "success",
                "transaction_id": transaction_id,
                "gateway_response_code": "00",
                "gateway_message": "Transaction approved",
                "processor_fee": float(amount * Decimal('0.029'))  # 2.9% processing fee
            }
        else:
            return {
                "status": "failed",
                "transaction_id": transaction_id,
                "gateway_response_code": "05",
                "gateway_message": "Transaction declined",
                "error_code": "INSUFFICIENT_FUNDS"
            }

class FraudDetectionEngine:
    """Advanced fraud detection system"""
    
    @staticmethod
    def analyze_transaction(
        user_id: int, 
        amount: Decimal, 
        client_ip: str,
        db: Session
    ) -> FraudAnalysis:
        """Analyze transaction for fraud indicators"""
        risk_score = 0.0
        flags = []
        
        # Check transaction amount patterns
        if amount > 500:
            risk_score += 15
            flags.append("high_amount")
        
        # Check user's payment history
        recent_payments = db.query(Payment).filter(
            and_(
                Payment.user_id == user_id,
                Payment.created_at >= datetime.now() - timedelta(hours=1)
            )
        ).count()
        
        if recent_payments >= 3:
            risk_score += 25
            flags.append("frequent_transactions")
        
        # Check for rapid successive transactions
        last_payment = db.query(Payment).filter(
            Payment.user_id == user_id
        ).order_by(desc(Payment.created_at)).first()
        
        if last_payment and (datetime.now() - last_payment.created_at).seconds < 60:
            risk_score += 30
            flags.append("rapid_succession")
        
        # Check IP reputation (simplified)
        if client_ip in ["192.168.1.1", "10.0.0.1"]:  # Example suspicious IPs
            risk_score += 20
            flags.append("suspicious_ip")
        
        # Check for weekend/night transactions (higher risk)
        now = datetime.now()
        if now.weekday() >= 5 or now.hour < 6 or now.hour > 23:
            risk_score += 10
            flags.append("off_hours")
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "critical"
            recommendation = "block_transaction"
        elif risk_score >= 50:
            risk_level = "high"
            recommendation = "manual_review"
        elif risk_score >= 30:
            risk_level = "medium"
            recommendation = "additional_verification"
        else:
            risk_level = "low"
            recommendation = "approve"
        
        return FraudAnalysis(
            risk_score=min(risk_score, 100),
            risk_level=risk_level,
            flags=flags,
            recommendation=recommendation
        )

# Payment endpoints
@app.post("/payment-methods/tokenize", response_model=CardToken)
async def tokenize_payment_method(
    card_data: PaymentMethodCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Tokenize payment method for PCI compliance"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Log tokenization attempt (never log card details)
        SecurityAuditLogger.log_security_event(
            "card_tokenization_attempt",
            current_user["id"],
            f"Card type: {card_data.card_number[0]}***, Last 4: {card_data.card_number[-4:]}",
            client_ip
        )
        
        # Tokenize card using payment gateway
        token = PaymentGateway.tokenize_card(card_data)
        
        # Log successful tokenization
        SecurityAuditLogger.log_security_event(
            "card_tokenization_success",
            current_user["id"],
            f"Token created: {token.token[:8]}***, Card type: {token.card_type}",
            client_ip
        )
        
        return token
        
    except Exception as e:
        logger.error(f"Error tokenizing payment method: {e}")
        SecurityAuditLogger.log_security_event(
            "card_tokenization_error",
            current_user["id"],
            str(e),
            client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not tokenize payment method"
        )

@app.post("/payments", response_model=PaymentResponse)
async def process_payment(
    payment_data: PaymentRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a payment"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        # Validate booking exists and belongs to user
        booking = db.query(Booking).filter(
            and_(
                Booking.id == payment_data.booking_id,
                Booking.user_id == current_user["id"]
            )
        ).first()
        
        if not booking:
            SecurityAuditLogger.log_security_event(
                "payment_invalid_booking",
                current_user["id"],
                f"Invalid booking ID: {payment_data.booking_id}",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        if booking.payment_status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment already completed"
            )
        
        # Validate payment amount matches booking
        if abs(float(payment_data.amount) - booking.total_amount) > 0.01:
            SecurityAuditLogger.log_security_event(
                "payment_amount_mismatch",
                current_user["id"],
                f"Expected: {booking.total_amount}, Provided: {payment_data.amount}",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount does not match booking total"
            )
        
        # Fraud detection analysis
        fraud_analysis = FraudDetectionEngine.analyze_transaction(
            current_user["id"], 
            payment_data.amount,
            client_ip,
            db
        )
        
        # Log fraud analysis
        SecurityAuditLogger.log_security_event(
            "payment_fraud_analysis",
            current_user["id"],
            f"Risk score: {fraud_analysis.risk_score}, Level: {fraud_analysis.risk_level}, Flags: {fraud_analysis.flags}",
            client_ip
        )
        
        # Block high-risk transactions
        if fraud_analysis.recommendation == "block_transaction":
            SecurityAuditLogger.log_security_event(
                "payment_blocked_fraud",
                current_user["id"],
                f"Transaction blocked due to high fraud risk: {fraud_analysis.risk_score}",
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transaction blocked due to security concerns. Please contact support."
            )
        
        # Process payment through gateway
        gateway_response = PaymentGateway.process_payment(
            payment_data.payment_method_token,
            payment_data.amount
        )
        
        # Create payment record
        new_payment = Payment(
            booking_id=payment_data.booking_id,
            user_id=current_user["id"],
            amount=float(payment_data.amount),
            currency=payment_data.currency,
            payment_method=f"card_****{payment_data.payment_method_token[-4:]}",
            payment_status="completed" if gateway_response["status"] == "success" else "failed",
            transaction_id=gateway_response["transaction_id"],
            gateway_response=gateway_response,
            fraud_score=fraud_analysis.risk_score,
            created_at=datetime.now()
        )
        
        db.add(new_payment)
        
        # Update booking if payment successful
        if gateway_response["status"] == "success":
            booking.payment_status = "completed"
            booking.booking_status = "confirmed"
            booking.updated_at = datetime.now()
        
        db.commit()
        db.refresh(new_payment)
        
        # Log payment result
        SecurityAuditLogger.log_security_event(
            "payment_processed",
            current_user["id"],
            f"Payment ID: {new_payment.id}, Status: {new_payment.payment_status}, Amount: {payment_data.amount}",
            client_ip
        )
        
        return PaymentResponse(
            id=new_payment.id,
            booking_id=new_payment.booking_id,
            user_id=new_payment.user_id,
            amount=new_payment.amount,
            currency=new_payment.currency,
            payment_method=new_payment.payment_method,
            payment_status=new_payment.payment_status,
            transaction_id=new_payment.transaction_id,
            gateway_response=new_payment.gateway_response,
            created_at=new_payment.created_at,
            updated_at=new_payment.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        SecurityAuditLogger.log_security_event(
            "payment_processing_error",
            current_user["id"],
            str(e),
            client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process payment"
        )

@app.get("/payments", response_model=List[PaymentResponse])
async def get_user_payments(
    request: Request,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's payment history"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        payments = db.query(Payment).filter(
            Payment.user_id == current_user["id"]
        ).order_by(desc(Payment.created_at)).offset(skip).limit(limit).all()
        
        payment_responses = []
        for payment in payments:
            payment_response = PaymentResponse(
                id=payment.id,
                booking_id=payment.booking_id,
                user_id=payment.user_id,
                amount=payment.amount,
                currency=payment.currency,
                payment_method=payment.payment_method,
                payment_status=payment.payment_status,
                transaction_id=payment.transaction_id,
                gateway_response=payment.gateway_response,
                created_at=payment.created_at,
                updated_at=payment.updated_at
            )
            payment_responses.append(payment_response)
        
        # Log access
        SecurityAuditLogger.log_security_event(
            "payments_accessed",
            current_user["id"],
            f"Retrieved {len(payments)} payment records",
            client_ip
        )
        
        return payment_responses
        
    except Exception as e:
        logger.error(f"Error fetching user payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch payments"
        )

@app.post("/payments/{payment_id}/refund")
async def process_refund(
    payment_id: int,
    refund_data: RefundRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a refund (user can request, admin approves)"""
    client_ip = request.client.host if request.client else "unknown"
    
    try:
        payment = db.query(Payment).filter(
            and_(
                Payment.id == payment_id,
                Payment.user_id == current_user["id"]
            )
        ).first()
        
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        if payment.payment_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot refund incomplete payment"
            )
        
        # In production, process actual refund through gateway
        refund_amount = refund_data.amount or payment.amount
        
        if refund_amount > payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund amount cannot exceed payment amount"
            )
        
        # Log refund request
        SecurityAuditLogger.log_security_event(
            "refund_requested",
            current_user["id"],
            f"Payment ID: {payment_id}, Amount: {refund_amount}, Reason: {refund_data.reason[:100]}",
            client_ip
        )
        
        return {
            "message": "Refund request submitted successfully",
            "refund_amount": float(refund_amount),
            "status": "pending_approval"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing refund for payment {payment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process refund request"
        )

# Admin endpoints
@app.get("/admin/payments", response_model=List[PaymentResponse])
@require_permission("admin")
async def get_all_payments(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all payments (admin only)"""
    try:
        query = db.query(Payment)
        
        if user_id:
            query = query.filter(Payment.user_id == user_id)
        
        if status_filter:
            status_filter = InputSanitizer.sanitize_string(status_filter)
            query = query.filter(Payment.payment_status == status_filter)
        
        payments = query.order_by(desc(Payment.created_at)).offset(skip).limit(limit).all()
        
        payment_responses = []
        for payment in payments:
            payment_response = PaymentResponse(
                id=payment.id,
                booking_id=payment.booking_id,
                user_id=payment.user_id,
                amount=payment.amount,
                currency=payment.currency,
                payment_method=payment.payment_method,
                payment_status=payment.payment_status,
                transaction_id=payment.transaction_id,
                gateway_response=payment.gateway_response,
                created_at=payment.created_at,
                updated_at=payment.updated_at
            )
            payment_responses.append(payment_response)
        
        # Log admin access
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "admin_payments_accessed",
            current_admin["id"],
            f"Retrieved {len(payments)} payment records",
            client_ip
        )
        
        return payment_responses
        
    except Exception as e:
        logger.error(f"Error fetching admin payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch payments"
        )

@app.get("/admin/fraud-analysis")
@require_permission("admin")
async def get_fraud_analytics(
    request: Request,
    days: int = 7,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get fraud detection analytics (admin only)"""
    try:
        # Get high-risk transactions
        high_risk_payments = db.query(Payment).filter(
            and_(
                Payment.fraud_score >= 50,
                Payment.created_at >= datetime.now() - timedelta(days=days)
            )
        ).all()
        
        # Calculate fraud statistics
        total_payments = db.query(Payment).filter(
            Payment.created_at >= datetime.now() - timedelta(days=days)
        ).count()
        
        blocked_payments = len([p for p in high_risk_payments if p.payment_status == "failed"])
        
        analytics = {
            "period_days": days,
            "total_payments": total_payments,
            "high_risk_payments": len(high_risk_payments),
            "blocked_payments": blocked_payments,
            "fraud_rate": (len(high_risk_payments) / total_payments * 100) if total_payments > 0 else 0,
            "block_rate": (blocked_payments / total_payments * 100) if total_payments > 0 else 0,
            "high_risk_transactions": [
                {
                    "payment_id": p.id,
                    "user_id": p.user_id,
                    "amount": p.amount,
                    "fraud_score": p.fraud_score,
                    "status": p.payment_status,
                    "created_at": p.created_at.isoformat()
                }
                for p in high_risk_payments[:20]  # Top 20 high-risk
            ]
        }
        
        # Log admin access
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.log_security_event(
            "admin_fraud_analytics_accessed",
            current_admin["id"],
            f"Period: {days} days, High-risk transactions: {len(high_risk_payments)}",
            client_ip
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error fetching fraud analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch fraud analytics"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "secure-payment",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "pci_compliance",
            "jwt_authentication",
            "fraud_detection",
            "tokenization",
            "rate_limiting",
            "audit_logging",
            "rbac"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Secure Payment Service")
    uvicorn.run(app, host="127.0.0.1", port=8015)
