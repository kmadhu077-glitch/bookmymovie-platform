import time
import random
import json
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Enhanced Payment Models ---

class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PHONEPE = "phonepe"
    GOOGLEPAY = "googlepay"
    PAYTM = "paytm"
    UPI = "upi"
    NET_BANKING = "net_banking"

class CardType(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    RUPAY = "rupay"
    AMEX = "american_express"

class CardDetails(BaseModel):
    card_number: str = Field(..., min_length=13, max_length=19)
    cardholder_name: str
    expiry_month: str = Field(..., pattern=r"^(0[1-9]|1[0-2])$")
    expiry_year: str = Field(..., pattern=r"^20[2-9][0-9]$")
    cvv: str = Field(..., min_length=3, max_length=4)
    card_type: CardType

class UpiDetails(BaseModel):
    upi_id: str = Field(..., pattern=r"^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$")
    name: str

class PhonePeDetails(BaseModel):
    mobile_number: str = Field(..., pattern=r"^[6-9][0-9]{9}$")
    upi_pin: str = Field(..., min_length=4, max_length=6)

class GooglePayDetails(BaseModel):
    gmail_id: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@gmail\.com$")
    mobile_number: str = Field(..., pattern=r"^[6-9][0-9]{9}$")

class NetBankingDetails(BaseModel):
    bank_name: str
    account_number: str = Field(..., min_length=8, max_length=20)
    ifsc_code: str = Field(..., pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")

class EnhancedPaymentRequest(BaseModel):
    hold_id: str = Field(..., example="HOLD_ABCDE")
    user_id: str = Field(..., example="USER_12345")
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethod
    
    # Payment method specific details (only one should be provided)
    card_details: Optional[CardDetails] = None
    upi_details: Optional[UpiDetails] = None
    phonepe_details: Optional[PhonePeDetails] = None
    googlepay_details: Optional[GooglePayDetails] = None
    netbanking_details: Optional[NetBankingDetails] = None
    
    # Additional fields
    save_payment_method: bool = False
    billing_address: Optional[Dict] = None

class PaymentResponse(BaseModel):
    transaction_id: str
    status: str  # SUCCESS, FAILED, PENDING
    message: str
    payment_method: str
    gateway_response: Optional[Dict] = None
    processing_fee: float = 0.0
    
class SavedPaymentMethod(BaseModel):
    method_id: str
    user_id: str
    payment_method: PaymentMethod
    display_name: str  # e.g., "****1234 Visa", "john@gmail.com", "+91****1234"
    is_default: bool = False
    created_at: str

# --- Mock Databases ---
MOCK_TRANSACTIONS = {}
SAVED_PAYMENT_METHODS = {}

# --- Helper Functions ---

def generate_transaction_id() -> str:
    return f"TXN_{int(time.time() * 1000)}{random.randint(100, 999)}"

def generate_method_id() -> str:
    return f"METHOD_{int(time.time() * 1000)}{random.randint(100, 999)}"

def validate_card_number(card_number: str) -> bool:
    """Luhn algorithm for card validation (simplified)"""
    # Remove spaces and dashes
    card_number = card_number.replace(" ", "").replace("-", "")
    
    # Basic validation
    if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
        return False
    
    # Mock validation - in real app, use proper Luhn algorithm
    return True

def get_card_type(card_number: str) -> str:
    """Detect card type from card number"""
    card_number = card_number.replace(" ", "").replace("-", "")
    
    if card_number.startswith(('4',)):
        return "visa"
    elif card_number.startswith(('5', '2')):
        return "mastercard"
    elif card_number.startswith(('6',)):
        return "rupay"
    elif card_number.startswith(('3',)):
        return "american_express"
    else:
        return "unknown"

def process_card_payment(card_details: CardDetails, amount: float) -> Dict:
    """Mock card payment processing"""
    
    # Validate card
    if not validate_card_number(card_details.card_number):
        return {"success": False, "error": "Invalid card number"}
    
    # Mock gateway processing
    success_rate = 0.95  # 95% success rate
    
    if random.random() < success_rate:
        return {
            "success": True,
            "gateway_transaction_id": f"CARD_{random.randint(100000, 999999)}",
            "authorization_code": f"AUTH{random.randint(100000, 999999)}",
            "processing_fee": round(amount * 0.02, 2)  # 2% processing fee
        }
    else:
        errors = [
            "Insufficient funds",
            "Card expired", 
            "Invalid CVV",
            "Transaction declined by bank",
            "Card blocked"
        ]
        return {"success": False, "error": random.choice(errors)}

def process_upi_payment(payment_details, amount: float) -> Dict:
    """Mock UPI payment processing"""
    
    success_rate = 0.92  # 92% success rate for UPI
    
    if random.random() < success_rate:
        return {
            "success": True,
            "gateway_transaction_id": f"UPI_{random.randint(100000000000, 999999999999)}",
            "processing_fee": round(amount * 0.005, 2)  # 0.5% processing fee
        }
    else:
        errors = [
            "UPI PIN incorrect",
            "Transaction failed",
            "Bank server unavailable",
            "Daily limit exceeded"
        ]
        return {"success": False, "error": random.choice(errors)}

def process_phonepe_payment(phonepe_details: PhonePeDetails, amount: float) -> Dict:
    """Mock PhonePe payment processing"""
    return process_upi_payment(phonepe_details, amount)

def process_googlepay_payment(googlepay_details: GooglePayDetails, amount: float) -> Dict:
    """Mock GooglePay payment processing"""
    return process_upi_payment(googlepay_details, amount)

def process_netbanking_payment(netbanking_details: NetBankingDetails, amount: float) -> Dict:
    """Mock Net Banking payment processing"""
    
    success_rate = 0.88  # 88% success rate for net banking
    
    if random.random() < success_rate:
        return {
            "success": True,
            "gateway_transaction_id": f"NB_{random.randint(100000000000, 999999999999)}",
            "processing_fee": round(amount * 0.01, 2)  # 1% processing fee
        }
    else:
        errors = [
            "Invalid account details",
            "Session timeout",
            "Bank server maintenance",
            "Transaction limit exceeded"
        ]
        return {"success": False, "error": random.choice(errors)}

# --- FastAPI Application ---
app = FastAPI(
    title="Enhanced Payment Gateway Service",
    description="Multi-payment method gateway supporting cards, UPI, PhonePe, GooglePay, and more",
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

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "enhanced_payment_gateway"}

@app.post("/v2/payments/process", response_model=PaymentResponse)
async def process_enhanced_payment(request: EnhancedPaymentRequest):
    """Process payment using various payment methods"""
    
    transaction_id = generate_transaction_id()
    
    # Route to appropriate payment processor
    if request.payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
        if not request.card_details:
            raise HTTPException(status_code=400, detail="Card details required for card payments")
        result = process_card_payment(request.card_details, request.amount)
        
    elif request.payment_method == PaymentMethod.PHONEPE:
        if not request.phonepe_details:
            raise HTTPException(status_code=400, detail="PhonePe details required")
        result = process_phonepe_payment(request.phonepe_details, request.amount)
        
    elif request.payment_method == PaymentMethod.GOOGLEPAY:
        if not request.googlepay_details:
            raise HTTPException(status_code=400, detail="GooglePay details required")
        result = process_googlepay_payment(request.googlepay_details, request.amount)
        
    elif request.payment_method == PaymentMethod.UPI:
        if not request.upi_details:
            raise HTTPException(status_code=400, detail="UPI details required")
        result = process_upi_payment(request.upi_details, request.amount)
        
    elif request.payment_method == PaymentMethod.NET_BANKING:
        if not request.netbanking_details:
            raise HTTPException(status_code=400, detail="Net banking details required")
        result = process_netbanking_payment(request.netbanking_details, request.amount)
        
    else:
        raise HTTPException(status_code=400, detail="Unsupported payment method")
    
    # Save payment method if requested
    if request.save_payment_method and result["success"]:
        save_payment_method_for_user(request)
    
    # Store transaction
    transaction_data = {
        "transaction_id": transaction_id,
        "hold_id": request.hold_id,
        "user_id": request.user_id,
        "amount": request.amount,
        "payment_method": request.payment_method.value,
        "status": "SUCCESS" if result["success"] else "FAILED",
        "created_at": datetime.now().isoformat(),
        "gateway_response": result
    }
    
    MOCK_TRANSACTIONS[transaction_id] = transaction_data
    
    # Prepare response
    if result["success"]:
        return PaymentResponse(
            transaction_id=transaction_id,
            status="SUCCESS",
            message="Payment processed successfully",
            payment_method=request.payment_method.value,
            gateway_response=result,
            processing_fee=result.get("processing_fee", 0.0)
        )
    else:
        return PaymentResponse(
            transaction_id=transaction_id,
            status="FAILED",
            message=f"Payment failed: {result['error']}",
            payment_method=request.payment_method.value,
            gateway_response=result
        )

@app.get("/v2/payments/methods/supported")
async def get_supported_payment_methods():
    """Get all supported payment methods"""
    return {
        "payment_methods": [
            {
                "method": "credit_card",
                "display_name": "Credit Card",
                "processing_fee": "2.0%",
                "supported_cards": ["visa", "mastercard", "rupay", "american_express"]
            },
            {
                "method": "debit_card", 
                "display_name": "Debit Card",
                "processing_fee": "1.5%",
                "supported_cards": ["visa", "mastercard", "rupay"]
            },
            {
                "method": "phonepe",
                "display_name": "PhonePe",
                "processing_fee": "0.5%"
            },
            {
                "method": "googlepay",
                "display_name": "Google Pay", 
                "processing_fee": "0.5%"
            },
            {
                "method": "upi",
                "display_name": "UPI",
                "processing_fee": "0.5%"
            },
            {
                "method": "net_banking",
                "display_name": "Net Banking",
                "processing_fee": "1.0%"
            }
        ]
    }

@app.get("/v2/payments/user/{user_id}/methods", response_model=List[SavedPaymentMethod])
async def get_saved_payment_methods(user_id: str):
    """Get saved payment methods for a user"""
    user_methods = [method for method in SAVED_PAYMENT_METHODS.values() if method["user_id"] == user_id]
    return user_methods

@app.delete("/v2/payments/user/{user_id}/methods/{method_id}")
async def delete_saved_payment_method(user_id: str, method_id: str):
    """Delete a saved payment method"""
    if method_id in SAVED_PAYMENT_METHODS and SAVED_PAYMENT_METHODS[method_id]["user_id"] == user_id:
        del SAVED_PAYMENT_METHODS[method_id]
        return {"message": "Payment method deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Payment method not found")

@app.get("/v2/payments/transaction/{transaction_id}")
async def get_transaction_details(transaction_id: str):
    """Get transaction details"""
    if transaction_id not in MOCK_TRANSACTIONS:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return MOCK_TRANSACTIONS[transaction_id]

def save_payment_method_for_user(request: EnhancedPaymentRequest):
    """Save payment method for future use"""
    method_id = generate_method_id()
    
    if request.payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
        display_name = f"****{request.card_details.card_number[-4:]} {request.card_details.card_type.value.title()}"
    elif request.payment_method == PaymentMethod.PHONEPE:
        display_name = f"PhonePe +91****{request.phonepe_details.mobile_number[-4:]}"
    elif request.payment_method == PaymentMethod.GOOGLEPAY:
        display_name = f"GPay {request.googlepay_details.gmail_id}"
    elif request.payment_method == PaymentMethod.UPI:
        display_name = f"UPI {request.upi_details.upi_id}"
    else:
        display_name = f"{request.payment_method.value.title()}"
    
    saved_method = SavedPaymentMethod(
        method_id=method_id,
        user_id=request.user_id,
        payment_method=request.payment_method,
        display_name=display_name,
        is_default=False,  # User can set default later
        created_at=datetime.now().isoformat()
    )
    
    SAVED_PAYMENT_METHODS[method_id] = saved_method.dict()

# Run: uvicorn enhanced_payment_service:app --host 127.0.0.1 --port 8011 --reload