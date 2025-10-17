"""
Multi-Factor Authentication (MFA) and Advanced Authentication Service
Enterprise-grade authentication with MFA, biometrics, and adaptive security
"""

import asyncio
import logging
import json
import hashlib
import hmac
import secrets
import time
import base64
import qrcode
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from io import BytesIO
import sqlite3

# Cryptography for secure operations
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from cryptography.hazmat.primitives.twofactor import InvalidToken
import pyotp

# JWT for secure tokens
import jwt
from passlib.hash import bcrypt
from passlib.context import CryptContext

# Email and SMS (would use actual services in production)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

@dataclass
class AuthenticationAttempt:
    """Authentication attempt record"""
    attempt_id: str
    user_id: str
    ip_address: str
    user_agent: str
    auth_method: str  # 'password', 'totp', 'sms', 'email', 'biometric'
    success: bool
    failure_reason: Optional[str]
    timestamp: datetime
    geo_location: Optional[Dict[str, str]] = None
    device_fingerprint: Optional[str] = None
    risk_score: float = 0.0

@dataclass
class MFAMethod:
    """MFA method configuration"""
    method_id: str
    user_id: str
    method_type: str  # 'totp', 'sms', 'email', 'backup_codes', 'push'
    is_enabled: bool
    is_primary: bool
    config_data: Dict[str, Any]  # Method-specific configuration
    created_at: datetime
    last_used: Optional[datetime] = None
    use_count: int = 0

@dataclass
class SecurityToken:
    """Security token for authentication"""
    token_id: str
    user_id: str
    token_type: str  # 'access', 'refresh', 'mfa_challenge', 'password_reset'
    token_value: str
    expires_at: datetime
    is_used: bool = False
    created_at: datetime = None
    metadata: Dict[str, Any] = None

@dataclass
class DeviceInfo:
    """Trusted device information"""
    device_id: str
    user_id: str
    device_name: str
    device_type: str  # 'mobile', 'desktop', 'tablet'
    fingerprint: str
    ip_address: str
    user_agent: str
    is_trusted: bool
    first_seen: datetime
    last_seen: datetime
    trust_expires: Optional[datetime] = None

@dataclass
class BiometricTemplate:
    """Biometric authentication template"""
    template_id: str
    user_id: str
    biometric_type: str  # 'fingerprint', 'face', 'voice'
    template_hash: str  # Hashed biometric template
    quality_score: float
    created_at: datetime
    is_active: bool = True

class TOTPManager:
    """Time-based One-Time Password manager"""
    
    def __init__(self):
        self.issuer_name = "BookMyMovie"
    
    def generate_secret(self) -> str:
        """Generate new TOTP secret"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str) -> bytes:
        """Generate QR code for TOTP setup"""
        
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        return img_buffer.getvalue()
    
    def verify_totp(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token"""
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=window)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False
    
    def get_current_token(self, secret: str) -> str:
        """Get current TOTP token (for testing)"""
        totp = pyotp.TOTP(secret)
        return totp.now()

class BackupCodeManager:
    """Backup authentication codes manager"""
    
    def __init__(self):
        self.code_length = 8
        self.code_count = 10
    
    def generate_backup_codes(self, user_id: str) -> List[str]:
        """Generate backup codes for user"""
        
        codes = []
        for _ in range(self.code_count):
            # Generate random alphanumeric code
            code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') 
                          for _ in range(self.code_length))
            codes.append(code)
        
        return codes
    
    def hash_backup_codes(self, codes: List[str]) -> List[str]:
        """Hash backup codes for storage"""
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return [pwd_context.hash(code) for code in codes]
    
    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> Tuple[bool, str]:
        """Verify backup code and return which code was used"""
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        for i, hashed_code in enumerate(hashed_codes):
            if pwd_context.verify(code, hashed_code):
                return True, hashed_code
        
        return False, None

class SMSProvider:
    """SMS provider for sending authentication codes"""
    
    def __init__(self, provider_config: Dict[str, Any] = None):
        self.config = provider_config or {}
        # In production, you would initialize actual SMS provider (Twilio, AWS SNS, etc.)
    
    async def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message"""
        
        try:
            # Simulate SMS sending
            logger.info(f"SMS sent to {phone_number}: {message}")
            return True
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False
    
    def generate_sms_code(self) -> str:
        """Generate SMS verification code"""
        return f"{secrets.randbelow(1000000):06d}"

class EmailProvider:
    """Email provider for sending authentication codes"""
    
    def __init__(self, smtp_config: Dict[str, Any] = None):
        self.config = smtp_config or {
            'smtp_server': 'localhost',
            'smtp_port': 587,
            'username': 'noreply@bookmymovie.com',
            'password': 'password',
            'use_tls': True
        }
    
    async def send_email(self, recipient: str, subject: str, body: str, 
                        is_html: bool = False) -> bool:
        """Send email message"""
        
        try:
            # Simulate email sending
            logger.info(f"Email sent to {recipient}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    def generate_email_code(self) -> str:
        """Generate email verification code"""
        return f"{secrets.randbelow(1000000):06d}"

class BiometricProcessor:
    """Biometric authentication processor"""
    
    def __init__(self):
        self.supported_types = ['fingerprint', 'face', 'voice']
    
    def process_biometric_template(self, biometric_data: bytes, 
                                 biometric_type: str) -> Tuple[str, float]:
        """Process biometric data and create template hash"""
        
        if biometric_type not in self.supported_types:
            raise ValueError(f"Unsupported biometric type: {biometric_type}")
        
        # Simulate biometric processing
        # In production, this would use actual biometric processing libraries
        
        # Create template hash
        template_hash = hashlib.sha256(biometric_data).hexdigest()
        
        # Simulate quality score
        quality_score = min(100.0, len(biometric_data) / 1000.0 * 100)
        
        return template_hash, quality_score
    
    def verify_biometric(self, template_hash: str, biometric_data: bytes) -> Tuple[bool, float]:
        """Verify biometric against stored template"""
        
        # Create hash of provided biometric
        provided_hash = hashlib.sha256(biometric_data).hexdigest()
        
        # In production, this would use actual biometric matching algorithms
        # with similarity thresholds rather than exact hash matching
        
        match = template_hash == provided_hash
        confidence = 100.0 if match else 0.0
        
        return match, confidence

class DeviceTrustManager:
    """Device trust and fingerprinting manager"""
    
    def __init__(self):
        self.trust_duration = timedelta(days=30)  # Trust devices for 30 days
    
    def generate_device_fingerprint(self, request_data: Dict[str, Any]) -> str:
        """Generate device fingerprint from request data"""
        
        # Combine various device characteristics
        fingerprint_data = {
            'user_agent': request_data.get('user_agent', ''),
            'screen_resolution': request_data.get('screen_resolution', ''),
            'timezone': request_data.get('timezone', ''),
            'language': request_data.get('language', ''),
            'platform': request_data.get('platform', ''),
            'plugins': request_data.get('plugins', []),
            'canvas_fingerprint': request_data.get('canvas_fingerprint', '')
        }
        
        # Create fingerprint hash
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint = hashlib.sha256(fingerprint_string.encode()).hexdigest()
        
        return fingerprint
    
    def is_trusted_device(self, user_id: str, device_fingerprint: str) -> bool:
        """Check if device is trusted for user"""
        
        # This would query the database for trusted devices
        # For now, simulate with simple logic
        return False  # Always require MFA for demo
    
    def trust_device(self, user_id: str, device_info: DeviceInfo) -> bool:
        """Mark device as trusted"""
        
        device_info.is_trusted = True
        device_info.trust_expires = datetime.now() + self.trust_duration
        
        # In production, save to database
        logger.info(f"Device {device_info.device_id} trusted for user {user_id}")
        return True

class AdaptiveAuthenticationEngine:
    """Adaptive authentication based on risk assessment"""
    
    def __init__(self):
        # Risk factors and their weights
        self.risk_factors = {
            'new_device': 25,
            'new_location': 20,
            'unusual_time': 10,
            'high_velocity': 30,
            'suspicious_ip': 40,
            'failed_attempts': 15
        }
        
        # Risk thresholds for MFA requirements
        self.mfa_thresholds = {
            'low': 20,
            'medium': 40,
            'high': 60
        }
    
    def assess_authentication_risk(self, user_id: str, request_data: Dict[str, Any],
                                 device_info: Optional[DeviceInfo] = None) -> Tuple[float, List[str]]:
        """Assess risk for authentication attempt"""
        
        risk_score = 0.0
        risk_factors = []
        
        # Check for new device
        if not device_info or not device_info.is_trusted:
            risk_score += self.risk_factors['new_device']
            risk_factors.append('new_device')
        
        # Check for suspicious timing
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 23:
            risk_score += self.risk_factors['unusual_time']
            risk_factors.append('unusual_time')
        
        # Check IP reputation (simplified)
        ip_address = request_data.get('ip_address', '')
        if self._is_suspicious_ip(ip_address):
            risk_score += self.risk_factors['suspicious_ip']
            risk_factors.append('suspicious_ip')
        
        # Check for high velocity attacks
        if self._check_high_velocity(user_id, ip_address):
            risk_score += self.risk_factors['high_velocity']
            risk_factors.append('high_velocity')
        
        return risk_score, risk_factors
    
    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP address is suspicious"""
        
        # Simplified suspicious IP check
        # In production, this would check against threat intelligence feeds
        
        suspicious_patterns = [
            '10.0.0.',  # Internal IPs shouldn't be external
            '192.168.',  # Internal IPs
            '127.0.0.',  # Loopback
        ]
        
        return any(ip_address.startswith(pattern) for pattern in suspicious_patterns)
    
    def _check_high_velocity(self, user_id: str, ip_address: str) -> bool:
        """Check for high velocity authentication attempts"""
        
        # Simplified velocity check
        # In production, this would check recent authentication attempts
        return False
    
    def determine_mfa_requirement(self, risk_score: float) -> Tuple[bool, List[str]]:
        """Determine MFA requirement based on risk score"""
        
        if risk_score >= self.mfa_thresholds['high']:
            return True, ['totp', 'sms', 'email']  # Require strong MFA
        elif risk_score >= self.mfa_thresholds['medium']:
            return True, ['totp', 'sms']  # Require moderate MFA
        elif risk_score >= self.mfa_thresholds['low']:
            return True, ['email']  # Require basic MFA
        else:
            return False, []  # No MFA required

class MFAService:
    """Multi-Factor Authentication service"""
    
    def __init__(self):
        # Initialize managers
        self.totp_manager = TOTPManager()
        self.backup_manager = BackupCodeManager()
        self.sms_provider = SMSProvider()
        self.email_provider = EmailProvider()
        self.biometric_processor = BiometricProcessor()
        self.device_manager = DeviceTrustManager()
        self.adaptive_engine = AdaptiveAuthenticationEngine()
        
        # Database
        self.db_path = "mfa_database.db"
        self._init_database()
        
        # JWT configuration
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
        self.jwt_algorithm = 'HS256'
        
        # Password context
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Active MFA challenges
        self.active_challenges = {}
    
    def _init_database(self):
        """Initialize MFA database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # MFA methods table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mfa_methods (
                method_id TEXT PRIMARY KEY,
                user_id TEXT,
                method_type TEXT,
                is_enabled INTEGER,
                is_primary INTEGER,
                config_data TEXT,
                created_at TEXT,
                last_used TEXT,
                use_count INTEGER
            )
        """)
        
        # Authentication attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_attempts (
                attempt_id TEXT PRIMARY KEY,
                user_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                auth_method TEXT,
                success INTEGER,
                failure_reason TEXT,
                timestamp TEXT,
                geo_location TEXT,
                device_fingerprint TEXT,
                risk_score REAL
            )
        """)
        
        # Security tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_tokens (
                token_id TEXT PRIMARY KEY,
                user_id TEXT,
                token_type TEXT,
                token_value TEXT,
                expires_at TEXT,
                is_used INTEGER,
                created_at TEXT,
                metadata TEXT
            )
        """)
        
        # Trusted devices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trusted_devices (
                device_id TEXT PRIMARY KEY,
                user_id TEXT,
                device_name TEXT,
                device_type TEXT,
                fingerprint TEXT,
                ip_address TEXT,
                user_agent TEXT,
                is_trusted INTEGER,
                first_seen TEXT,
                last_seen TEXT,
                trust_expires TEXT
            )
        """)
        
        # Biometric templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS biometric_templates (
                template_id TEXT PRIMARY KEY,
                user_id TEXT,
                biometric_type TEXT,
                template_hash TEXT,
                quality_score REAL,
                created_at TEXT,
                is_active INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def setup_totp(self, user_id: str, user_email: str) -> Dict[str, Any]:
        """Setup TOTP for user"""
        
        try:
            # Generate secret
            secret = self.totp_manager.generate_secret()
            
            # Generate QR code
            qr_code = self.totp_manager.generate_qr_code(user_email, secret)
            
            # Create MFA method
            method = MFAMethod(
                method_id=secrets.token_hex(16),
                user_id=user_id,
                method_type='totp',
                is_enabled=False,  # Will be enabled after verification
                is_primary=False,
                config_data={'secret': secret},
                created_at=datetime.now()
            )
            
            # Store in database (temporarily)
            await self._store_mfa_method(method)
            
            return {
                'method_id': method.method_id,
                'secret': secret,
                'qr_code': base64.b64encode(qr_code).decode(),
                'setup_complete': False
            }
            
        except Exception as e:
            logger.error(f"TOTP setup failed for user {user_id}: {e}")
            raise
    
    async def verify_totp_setup(self, user_id: str, method_id: str, token: str) -> bool:
        """Verify TOTP setup and enable"""
        
        try:
            # Get method
            method = await self._get_mfa_method(method_id)
            if not method or method.user_id != user_id:
                return False
            
            # Verify token
            secret = method.config_data['secret']
            if self.totp_manager.verify_totp(secret, token):
                # Enable method
                method.is_enabled = True
                await self._update_mfa_method(method)
                
                # Generate backup codes
                backup_codes = self.backup_manager.generate_backup_codes(user_id)
                hashed_codes = self.backup_manager.hash_backup_codes(backup_codes)
                
                # Store backup codes
                backup_method = MFAMethod(
                    method_id=secrets.token_hex(16),
                    user_id=user_id,
                    method_type='backup_codes',
                    is_enabled=True,
                    is_primary=False,
                    config_data={'codes': hashed_codes},
                    created_at=datetime.now()
                )
                await self._store_mfa_method(backup_method)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"TOTP verification failed: {e}")
            return False
    
    async def setup_sms_mfa(self, user_id: str, phone_number: str) -> Dict[str, Any]:
        """Setup SMS MFA for user"""
        
        try:
            # Send verification code
            code = self.sms_provider.generate_sms_code()
            message = f"Your BookMyMovie verification code is: {code}"
            
            success = await self.sms_provider.send_sms(phone_number, message)
            if not success:
                raise Exception("Failed to send SMS")
            
            # Store challenge
            challenge_id = secrets.token_hex(16)
            self.active_challenges[challenge_id] = {
                'user_id': user_id,
                'method_type': 'sms',
                'code': code,
                'phone_number': phone_number,
                'expires_at': datetime.now() + timedelta(minutes=10)
            }
            
            return {
                'challenge_id': challenge_id,
                'phone_number': phone_number[-4:].rjust(len(phone_number), '*'),
                'expires_in': 600  # 10 minutes
            }
            
        except Exception as e:
            logger.error(f"SMS MFA setup failed: {e}")
            raise
    
    async def verify_sms_setup(self, challenge_id: str, code: str) -> bool:
        """Verify SMS setup"""
        
        try:
            challenge = self.active_challenges.get(challenge_id)
            if not challenge or datetime.now() > challenge['expires_at']:
                return False
            
            if challenge['code'] == code:
                # Create MFA method
                method = MFAMethod(
                    method_id=secrets.token_hex(16),
                    user_id=challenge['user_id'],
                    method_type='sms',
                    is_enabled=True,
                    is_primary=False,
                    config_data={'phone_number': challenge['phone_number']},
                    created_at=datetime.now()
                )
                
                await self._store_mfa_method(method)
                
                # Remove challenge
                del self.active_challenges[challenge_id]
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"SMS verification failed: {e}")
            return False
    
    async def initiate_mfa_challenge(self, user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate MFA challenge based on risk assessment"""
        
        try:
            # Get device info
            device_fingerprint = self.device_manager.generate_device_fingerprint(request_data)
            device_info = await self._get_device_info(user_id, device_fingerprint)
            
            # Assess risk
            risk_score, risk_factors = self.adaptive_engine.assess_authentication_risk(
                user_id, request_data, device_info
            )
            
            # Determine MFA requirement
            requires_mfa, allowed_methods = self.adaptive_engine.determine_mfa_requirement(risk_score)
            
            if not requires_mfa:
                # Generate access token
                access_token = self._generate_jwt_token(user_id, 'access')
                return {
                    'requires_mfa': False,
                    'access_token': access_token,
                    'risk_score': risk_score
                }
            
            # Get user's enabled MFA methods
            user_methods = await self._get_user_mfa_methods(user_id)
            available_methods = [
                method for method in user_methods
                if method.method_type in allowed_methods and method.is_enabled
            ]
            
            if not available_methods:
                raise Exception("No MFA methods available")
            
            # Create MFA challenge token
            challenge_token = self._generate_jwt_token(user_id, 'mfa_challenge', expires_in=300)  # 5 minutes
            
            return {
                'requires_mfa': True,
                'challenge_token': challenge_token,
                'available_methods': [
                    {
                        'method_id': method.method_id,
                        'method_type': method.method_type,
                        'is_primary': method.is_primary
                    }
                    for method in available_methods
                ],
                'risk_score': risk_score,
                'risk_factors': risk_factors
            }
            
        except Exception as e:
            logger.error(f"MFA challenge initiation failed: {e}")
            raise
    
    async def verify_mfa_challenge(self, challenge_token: str, method_id: str, 
                                 code: str) -> Dict[str, Any]:
        """Verify MFA challenge"""
        
        try:
            # Decode challenge token
            payload = jwt.decode(challenge_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            user_id = payload['user_id']
            
            if payload['token_type'] != 'mfa_challenge':
                raise Exception("Invalid challenge token")
            
            # Get MFA method
            method = await self._get_mfa_method(method_id)
            if not method or method.user_id != user_id or not method.is_enabled:
                raise Exception("Invalid MFA method")
            
            # Verify based on method type
            verification_result = False
            
            if method.method_type == 'totp':
                secret = method.config_data['secret']
                verification_result = self.totp_manager.verify_totp(secret, code)
            
            elif method.method_type == 'sms':
                # In production, verify SMS code from cache
                verification_result = True  # Simplified for demo
            
            elif method.method_type == 'backup_codes':
                hashed_codes = method.config_data['codes']
                verification_result, used_code = self.backup_manager.verify_backup_code(code, hashed_codes)
                
                if verification_result:
                    # Remove used backup code
                    method.config_data['codes'] = [
                        c for c in hashed_codes if c != used_code
                    ]
                    await self._update_mfa_method(method)
            
            # Log authentication attempt
            await self._log_auth_attempt(
                user_id=user_id,
                auth_method=method.method_type,
                success=verification_result,
                failure_reason=None if verification_result else "Invalid code"
            )
            
            if verification_result:
                # Update method usage
                method.last_used = datetime.now()
                method.use_count += 1
                await self._update_mfa_method(method)
                
                # Generate access token
                access_token = self._generate_jwt_token(user_id, 'access')
                refresh_token = self._generate_jwt_token(user_id, 'refresh', expires_in=604800)  # 7 days
                
                return {
                    'success': True,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'method_used': method.method_type
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid verification code'
                }
                
        except Exception as e:
            logger.error(f"MFA verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_jwt_token(self, user_id: str, token_type: str, expires_in: int = 3600) -> str:
        """Generate JWT token"""
        
        payload = {
            'user_id': user_id,
            'token_type': token_type,
            'iat': datetime.now().timestamp(),
            'exp': (datetime.now() + timedelta(seconds=expires_in)).timestamp()
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    async def _store_mfa_method(self, method: MFAMethod):
        """Store MFA method in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO mfa_methods 
            (method_id, user_id, method_type, is_enabled, is_primary, config_data, 
             created_at, last_used, use_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            method.method_id,
            method.user_id,
            method.method_type,
            int(method.is_enabled),
            int(method.is_primary),
            json.dumps(method.config_data),
            method.created_at.isoformat(),
            method.last_used.isoformat() if method.last_used else None,
            method.use_count
        ))
        
        conn.commit()
        conn.close()
    
    async def _get_mfa_method(self, method_id: str) -> Optional[MFAMethod]:
        """Get MFA method from database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT method_id, user_id, method_type, is_enabled, is_primary, config_data,
                   created_at, last_used, use_count
            FROM mfa_methods 
            WHERE method_id = ?
        """, (method_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return MFAMethod(
                method_id=row[0],
                user_id=row[1],
                method_type=row[2],
                is_enabled=bool(row[3]),
                is_primary=bool(row[4]),
                config_data=json.loads(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                last_used=datetime.fromisoformat(row[7]) if row[7] else None,
                use_count=row[8]
            )
        
        return None
    
    async def _update_mfa_method(self, method: MFAMethod):
        """Update MFA method in database"""
        await self._store_mfa_method(method)  # Same as store with REPLACE
    
    async def _get_user_mfa_methods(self, user_id: str) -> List[MFAMethod]:
        """Get all MFA methods for user"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT method_id, user_id, method_type, is_enabled, is_primary, config_data,
                   created_at, last_used, use_count
            FROM mfa_methods 
            WHERE user_id = ?
            ORDER BY is_primary DESC, created_at ASC
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        methods = []
        for row in rows:
            method = MFAMethod(
                method_id=row[0],
                user_id=row[1],
                method_type=row[2],
                is_enabled=bool(row[3]),
                is_primary=bool(row[4]),
                config_data=json.loads(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                last_used=datetime.fromisoformat(row[7]) if row[7] else None,
                use_count=row[8]
            )
            methods.append(method)
        
        return methods
    
    async def _get_device_info(self, user_id: str, fingerprint: str) -> Optional[DeviceInfo]:
        """Get device information"""
        
        # In production, query database for device info
        return None  # For demo, always return new device
    
    async def _log_auth_attempt(self, user_id: str, auth_method: str, success: bool, 
                               failure_reason: str = None, **kwargs):
        """Log authentication attempt"""
        
        attempt = AuthenticationAttempt(
            attempt_id=secrets.token_hex(16),
            user_id=user_id,
            ip_address=kwargs.get('ip_address', ''),
            user_agent=kwargs.get('user_agent', ''),
            auth_method=auth_method,
            success=success,
            failure_reason=failure_reason,
            timestamp=datetime.now(),
            geo_location=kwargs.get('geo_location'),
            device_fingerprint=kwargs.get('device_fingerprint'),
            risk_score=kwargs.get('risk_score', 0.0)
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO auth_attempts 
            (attempt_id, user_id, ip_address, user_agent, auth_method, success,
             failure_reason, timestamp, geo_location, device_fingerprint, risk_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            attempt.attempt_id,
            attempt.user_id,
            attempt.ip_address,
            attempt.user_agent,
            attempt.auth_method,
            int(attempt.success),
            attempt.failure_reason,
            attempt.timestamp.isoformat(),
            json.dumps(attempt.geo_location) if attempt.geo_location else None,
            attempt.device_fingerprint,
            attempt.risk_score
        ))
        
        conn.commit()
        conn.close()

# Global MFA service
mfa_service = MFAService()

# Utility functions
async def setup_user_totp(user_id: str, user_email: str) -> Dict[str, Any]:
    """Setup TOTP for user"""
    return await mfa_service.setup_totp(user_id, user_email)

async def verify_user_totp_setup(user_id: str, method_id: str, token: str) -> bool:
    """Verify TOTP setup"""
    return await mfa_service.verify_totp_setup(user_id, method_id, token)

async def authenticate_with_mfa(user_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Authenticate user with MFA"""
    return await mfa_service.initiate_mfa_challenge(user_id, request_data)

async def verify_mfa_code(challenge_token: str, method_id: str, code: str) -> Dict[str, Any]:
    """Verify MFA code"""
    return await mfa_service.verify_mfa_challenge(challenge_token, method_id, code)