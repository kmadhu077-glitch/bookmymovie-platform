"""
Data Encryption and Security Compliance Service
Advanced encryption, key management, and compliance (GDPR, PCI DSS)
"""

import asyncio
import logging
import json
import os
import secrets
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
from enum import Enum
import sqlite3

# Advanced cryptography
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes, serialization, padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend

# AES encryption
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

logger = logging.getLogger(__name__)

class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class ComplianceStandard(Enum):
    """Supported compliance standards"""
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    SOX = "sox"
    ISO27001 = "iso27001"

@dataclass
class EncryptionKey:
    """Encryption key information"""
    key_id: str
    key_type: str  # 'symmetric', 'asymmetric_public', 'asymmetric_private'
    algorithm: str  # 'AES256', 'RSA2048', 'RSA4096'
    key_data: bytes
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    purpose: str = "general"  # 'general', 'database', 'file_storage', 'transport'
    metadata: Dict[str, Any] = None

@dataclass
class EncryptedData:
    """Encrypted data container"""
    data_id: str
    encrypted_data: bytes
    encryption_method: str
    key_id: str
    iv: Optional[bytes] = None  # Initialization vector
    tag: Optional[bytes] = None  # Authentication tag for authenticated encryption
    metadata: Dict[str, Any] = None
    created_at: datetime = None

@dataclass
class DataAccessLog:
    """Data access audit log"""
    log_id: str
    user_id: str
    data_type: str
    operation: str  # 'create', 'read', 'update', 'delete', 'encrypt', 'decrypt'
    data_classification: DataClassification
    success: bool
    ip_address: str
    user_agent: str
    timestamp: datetime
    details: Dict[str, Any]
    compliance_context: List[ComplianceStandard] = None

@dataclass
class ComplianceEvent:
    """Compliance-related event"""
    event_id: str
    event_type: str  # 'data_request', 'data_deletion', 'consent_given', 'consent_withdrawn'
    compliance_standard: ComplianceStandard
    user_id: str
    data_subject_id: Optional[str]  # For GDPR, the data subject
    request_details: Dict[str, Any]
    processing_status: str  # 'pending', 'in_progress', 'completed', 'failed'
    response_data: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None

class KeyManagementService:
    """Advanced key management and rotation"""
    
    def __init__(self):
        self.key_store = {}
        self.key_rotation_schedule = {}
        self.key_derivation_params = {
            'pbkdf2_iterations': 100000,
            'scrypt_n': 2**14,
            'scrypt_r': 8,
            'scrypt_p': 1
        }
        
        # Initialize master key (in production, use HSM or secure key store)
        self.master_key = self._get_or_create_master_key()
        
        # Key rotation intervals
        self.rotation_intervals = {
            'database': timedelta(days=90),
            'file_storage': timedelta(days=180),
            'transport': timedelta(days=30),
            'general': timedelta(days=365)
        }
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        
        master_key_file = "master_key.key"
        
        if os.path.exists(master_key_file):
            with open(master_key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new master key
            master_key = Fernet.generate_key()
            
            # In production, store in secure key management system
            with open(master_key_file, 'wb') as f:
                f.write(master_key)
            
            logger.info("New master key generated")
            return master_key
    
    def generate_symmetric_key(self, algorithm: str = 'AES256', purpose: str = 'general') -> EncryptionKey:
        """Generate symmetric encryption key"""
        
        key_id = secrets.token_hex(16)
        
        if algorithm == 'AES256':
            key_data = get_random_bytes(32)  # 256 bits
        elif algorithm == 'AES128':
            key_data = get_random_bytes(16)  # 128 bits
        else:
            raise ValueError(f"Unsupported symmetric algorithm: {algorithm}")
        
        # Encrypt key data with master key
        fernet = Fernet(self.master_key)
        encrypted_key_data = fernet.encrypt(key_data)
        
        encryption_key = EncryptionKey(
            key_id=key_id,
            key_type='symmetric',
            algorithm=algorithm,
            key_data=encrypted_key_data,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.rotation_intervals.get(purpose, self.rotation_intervals['general']),
            purpose=purpose,
            metadata={'master_key_encrypted': True}
        )
        
        self.key_store[key_id] = encryption_key
        
        logger.info(f"Generated symmetric key {key_id} for purpose: {purpose}")
        return encryption_key
    
    def generate_asymmetric_keypair(self, key_size: int = 2048, purpose: str = 'general') -> Tuple[EncryptionKey, EncryptionKey]:
        """Generate RSA keypair"""
        
        # Generate RSA keypair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Encrypt private key with master key
        fernet = Fernet(self.master_key)
        encrypted_private_key = fernet.encrypt(private_pem)
        
        # Create key objects
        key_id_base = secrets.token_hex(16)
        
        private_key_obj = EncryptionKey(
            key_id=f"{key_id_base}_private",
            key_type='asymmetric_private',
            algorithm=f'RSA{key_size}',
            key_data=encrypted_private_key,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.rotation_intervals.get(purpose, self.rotation_intervals['general']),
            purpose=purpose,
            metadata={'master_key_encrypted': True, 'keypair_id': key_id_base}
        )
        
        public_key_obj = EncryptionKey(
            key_id=f"{key_id_base}_public",
            key_type='asymmetric_public',
            algorithm=f'RSA{key_size}',
            key_data=public_pem,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.rotation_intervals.get(purpose, self.rotation_intervals['general']),
            purpose=purpose,
            metadata={'keypair_id': key_id_base}
        )
        
        # Store keys
        self.key_store[private_key_obj.key_id] = private_key_obj
        self.key_store[public_key_obj.key_id] = public_key_obj
        
        logger.info(f"Generated RSA keypair {key_id_base} (size: {key_size}) for purpose: {purpose}")
        return private_key_obj, public_key_obj
    
    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Get encryption key by ID"""
        return self.key_store.get(key_id)
    
    def decrypt_key_data(self, encryption_key: EncryptionKey) -> bytes:
        """Decrypt key data using master key"""
        
        if encryption_key.metadata and encryption_key.metadata.get('master_key_encrypted'):
            fernet = Fernet(self.master_key)
            return fernet.decrypt(encryption_key.key_data)
        else:
            return encryption_key.key_data
    
    def rotate_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Rotate encryption key"""
        
        old_key = self.key_store.get(key_id)
        if not old_key:
            return None
        
        # Generate new key with same parameters
        if old_key.key_type == 'symmetric':
            new_key = self.generate_symmetric_key(old_key.algorithm, old_key.purpose)
        else:
            # For asymmetric keys, generate new keypair
            key_size = int(old_key.algorithm.replace('RSA', ''))
            private_key, public_key = self.generate_asymmetric_keypair(key_size, old_key.purpose)
            new_key = private_key if old_key.key_type == 'asymmetric_private' else public_key
        
        # Deactivate old key
        old_key.is_active = False
        
        logger.info(f"Rotated key {key_id} to {new_key.key_id}")
        return new_key
    
    def derive_key(self, password: str, salt: bytes, algorithm: str = 'PBKDF2') -> bytes:
        """Derive key from password"""
        
        if algorithm == 'PBKDF2':
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=self.key_derivation_params['pbkdf2_iterations'],
                backend=default_backend()
            )
        elif algorithm == 'Scrypt':
            kdf = Scrypt(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                n=self.key_derivation_params['scrypt_n'],
                r=self.key_derivation_params['scrypt_r'],
                p=self.key_derivation_params['scrypt_p'],
                backend=default_backend()
            )
        else:
            raise ValueError(f"Unsupported KDF algorithm: {algorithm}")
        
        return kdf.derive(password.encode())

class AdvancedEncryptionService:
    """Advanced encryption and decryption service"""
    
    def __init__(self, key_manager: KeyManagementService):
        self.key_manager = key_manager
    
    def encrypt_data_symmetric(self, data: Union[str, bytes], key_id: str, 
                              algorithm: str = 'AES-GCM') -> EncryptedData:
        """Encrypt data using symmetric encryption"""
        
        # Get encryption key
        encryption_key = self.key_manager.get_key(key_id)
        if not encryption_key or encryption_key.key_type != 'symmetric':
            raise ValueError(f"Invalid symmetric key: {key_id}")
        
        # Decrypt key data
        key_data = self.key_manager.decrypt_key_data(encryption_key)
        
        # Convert string to bytes if needed
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        data_id = secrets.token_hex(16)
        
        if algorithm == 'AES-GCM':
            # AES-GCM provides authenticated encryption
            iv = get_random_bytes(12)  # 96-bit IV for GCM
            cipher = AES.new(key_data, AES.MODE_GCM, nonce=iv)
            encrypted_data, tag = cipher.encrypt_and_digest(data)
            
            return EncryptedData(
                data_id=data_id,
                encrypted_data=encrypted_data,
                encryption_method=algorithm,
                key_id=key_id,
                iv=iv,
                tag=tag,
                created_at=datetime.now()
            )
        
        elif algorithm == 'AES-CBC':
            # AES-CBC with HMAC for authentication
            iv = get_random_bytes(16)  # 128-bit IV
            cipher = AES.new(key_data, AES.MODE_CBC, iv)
            padded_data = pad(data, AES.block_size)
            encrypted_data = cipher.encrypt(padded_data)
            
            # HMAC for authentication
            hmac_key = hashlib.sha256(key_data + b'hmac').digest()
            tag = hmac.new(hmac_key, iv + encrypted_data, hashlib.sha256).digest()
            
            return EncryptedData(
                data_id=data_id,
                encrypted_data=encrypted_data,
                encryption_method=algorithm,
                key_id=key_id,
                iv=iv,
                tag=tag,
                created_at=datetime.now()
            )
        
        else:
            raise ValueError(f"Unsupported encryption algorithm: {algorithm}")
    
    def decrypt_data_symmetric(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt data using symmetric encryption"""
        
        # Get encryption key
        encryption_key = self.key_manager.get_key(encrypted_data.key_id)
        if not encryption_key or encryption_key.key_type != 'symmetric':
            raise ValueError(f"Invalid symmetric key: {encrypted_data.key_id}")
        
        # Decrypt key data
        key_data = self.key_manager.decrypt_key_data(encryption_key)
        
        if encrypted_data.encryption_method == 'AES-GCM':
            cipher = AES.new(key_data, AES.MODE_GCM, nonce=encrypted_data.iv)
            decrypted_data = cipher.decrypt_and_verify(encrypted_data.encrypted_data, encrypted_data.tag)
            return decrypted_data
        
        elif encrypted_data.encryption_method == 'AES-CBC':
            # Verify HMAC first
            hmac_key = hashlib.sha256(key_data + b'hmac').digest()
            expected_tag = hmac.new(hmac_key, encrypted_data.iv + encrypted_data.encrypted_data, hashlib.sha256).digest()
            
            if not hmac.compare_digest(encrypted_data.tag, expected_tag):
                raise ValueError("HMAC verification failed")
            
            cipher = AES.new(key_data, AES.MODE_CBC, encrypted_data.iv)
            padded_data = cipher.decrypt(encrypted_data.encrypted_data)
            decrypted_data = unpad(padded_data, AES.block_size)
            return decrypted_data
        
        else:
            raise ValueError(f"Unsupported decryption algorithm: {encrypted_data.encryption_method}")
    
    def encrypt_data_asymmetric(self, data: Union[str, bytes], public_key_id: str) -> EncryptedData:
        """Encrypt data using asymmetric encryption"""
        
        # Get public key
        public_key_obj = self.key_manager.get_key(public_key_id)
        if not public_key_obj or public_key_obj.key_type != 'asymmetric_public':
            raise ValueError(f"Invalid public key: {public_key_id}")
        
        # Convert string to bytes if needed
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Load public key
        public_key = serialization.load_pem_public_key(public_key_obj.key_data, backend=default_backend())
        
        # For large data, use hybrid encryption (RSA + AES)
        if len(data) > 190:  # RSA-2048 can encrypt up to 190 bytes with OAEP padding
            # Generate random AES key
            aes_key = get_random_bytes(32)
            
            # Encrypt data with AES
            iv = get_random_bytes(12)
            cipher = AES.new(aes_key, AES.MODE_GCM, nonce=iv)
            encrypted_data, tag = cipher.encrypt_and_digest(data)
            
            # Encrypt AES key with RSA
            encrypted_aes_key = public_key.encrypt(
                aes_key,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Combine encrypted key and data
            combined_data = len(encrypted_aes_key).to_bytes(4, byteorder='big') + encrypted_aes_key + encrypted_data
            
            return EncryptedData(
                data_id=secrets.token_hex(16),
                encrypted_data=combined_data,
                encryption_method='RSA-OAEP+AES-GCM',
                key_id=public_key_id,
                iv=iv,
                tag=tag,
                created_at=datetime.now()
            )
        else:
            # Direct RSA encryption for small data
            encrypted_data = public_key.encrypt(
                data,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return EncryptedData(
                data_id=secrets.token_hex(16),
                encrypted_data=encrypted_data,
                encryption_method='RSA-OAEP',
                key_id=public_key_id,
                created_at=datetime.now()
            )
    
    def decrypt_data_asymmetric(self, encrypted_data: EncryptedData, private_key_id: str) -> bytes:
        """Decrypt data using asymmetric encryption"""
        
        # Get private key
        private_key_obj = self.key_manager.get_key(private_key_id)
        if not private_key_obj or private_key_obj.key_type != 'asymmetric_private':
            raise ValueError(f"Invalid private key: {private_key_id}")
        
        # Decrypt key data
        private_key_data = self.key_manager.decrypt_key_data(private_key_obj)
        
        # Load private key
        private_key = serialization.load_pem_private_key(private_key_data, password=None, backend=default_backend())
        
        if encrypted_data.encryption_method == 'RSA-OAEP+AES-GCM':
            # Hybrid decryption
            data = encrypted_data.encrypted_data
            
            # Extract encrypted AES key length
            aes_key_length = int.from_bytes(data[:4], byteorder='big')
            
            # Extract encrypted AES key
            encrypted_aes_key = data[4:4+aes_key_length]
            
            # Extract encrypted data
            encrypted_payload = data[4+aes_key_length:]
            
            # Decrypt AES key with RSA
            aes_key = private_key.decrypt(
                encrypted_aes_key,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt data with AES
            cipher = AES.new(aes_key, AES.MODE_GCM, nonce=encrypted_data.iv)
            decrypted_data = cipher.decrypt_and_verify(encrypted_payload, encrypted_data.tag)
            
            return decrypted_data
        
        elif encrypted_data.encryption_method == 'RSA-OAEP':
            # Direct RSA decryption
            decrypted_data = private_key.decrypt(
                encrypted_data.encrypted_data,
                asym_padding.OAEP(
                    mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted_data
        
        else:
            raise ValueError(f"Unsupported decryption algorithm: {encrypted_data.encryption_method}")

class ComplianceManager:
    """Compliance management for GDPR, PCI DSS, etc."""
    
    def __init__(self):
        self.db_path = "compliance.db"
        self._init_database()
        
        # Data retention policies (in days)
        self.retention_policies = {
            DataClassification.PUBLIC: 2555,  # 7 years
            DataClassification.INTERNAL: 1825,  # 5 years
            DataClassification.CONFIDENTIAL: 1095,  # 3 years
            DataClassification.RESTRICTED: 365  # 1 year
        }
        
        # GDPR processing lawful bases
        self.gdpr_lawful_bases = [
            'consent',
            'contract',
            'legal_obligation',
            'vital_interests',
            'public_task',
            'legitimate_interests'
        ]
    
    def _init_database(self):
        """Initialize compliance database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Data access logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_access_logs (
                log_id TEXT PRIMARY KEY,
                user_id TEXT,
                data_type TEXT,
                operation TEXT,
                data_classification TEXT,
                success INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TEXT,
                details TEXT,
                compliance_context TEXT
            )
        """)
        
        # Compliance events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT,
                compliance_standard TEXT,
                user_id TEXT,
                data_subject_id TEXT,
                request_details TEXT,
                processing_status TEXT,
                response_data TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        """)
        
        # Data subject consents table (GDPR)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_consents (
                consent_id TEXT PRIMARY KEY,
                data_subject_id TEXT,
                purpose TEXT,
                lawful_basis TEXT,
                consent_given INTEGER,
                consent_timestamp TEXT,
                withdrawn_timestamp TEXT,
                data_categories TEXT,
                retention_period INTEGER
            )
        """)
        
        # Data processing activities (GDPR Article 30)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_activities (
                activity_id TEXT PRIMARY KEY,
                controller TEXT,
                processor TEXT,
                purpose TEXT,
                lawful_basis TEXT,
                data_categories TEXT,
                data_subjects TEXT,
                recipients TEXT,
                third_country_transfers TEXT,
                retention_period INTEGER,
                technical_measures TEXT,
                organizational_measures TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_data_access(self, access_log: DataAccessLog):
        """Log data access for compliance"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO data_access_logs 
                (log_id, user_id, data_type, operation, data_classification, success,
                 ip_address, user_agent, timestamp, details, compliance_context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                access_log.log_id,
                access_log.user_id,
                access_log.data_type,
                access_log.operation,
                access_log.data_classification.value,
                int(access_log.success),
                access_log.ip_address,
                access_log.user_agent,
                access_log.timestamp.isoformat(),
                json.dumps(access_log.details),
                json.dumps([std.value for std in access_log.compliance_context or []])
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log data access: {e}")
    
    def process_gdpr_request(self, request_type: str, data_subject_id: str, 
                           request_details: Dict[str, Any]) -> ComplianceEvent:
        """Process GDPR data subject request"""
        
        event_id = secrets.token_hex(16)
        
        event = ComplianceEvent(
            event_id=event_id,
            event_type=request_type,
            compliance_standard=ComplianceStandard.GDPR,
            user_id=data_subject_id,  # For GDPR, user is the data subject
            data_subject_id=data_subject_id,
            request_details=request_details,
            processing_status='pending',
            created_at=datetime.now()
        )
        
        # Store event
        self._store_compliance_event(event)
        
        # Process based on request type
        if request_type == 'access_request':  # Article 15
            self._process_access_request(event)
        elif request_type == 'rectification_request':  # Article 16
            self._process_rectification_request(event)
        elif request_type == 'erasure_request':  # Article 17 (Right to be forgotten)
            self._process_erasure_request(event)
        elif request_type == 'portability_request':  # Article 20
            self._process_portability_request(event)
        elif request_type == 'restriction_request':  # Article 18
            self._process_restriction_request(event)
        
        return event
    
    def _process_access_request(self, event: ComplianceEvent):
        """Process GDPR access request (Article 15)"""
        
        try:
            data_subject_id = event.data_subject_id
            
            # Collect all personal data for the data subject
            personal_data = {
                'user_profile': self._get_user_profile_data(data_subject_id),
                'booking_history': self._get_booking_data(data_subject_id),
                'payment_information': self._get_payment_data(data_subject_id),
                'preferences': self._get_preference_data(data_subject_id),
                'communication_logs': self._get_communication_data(data_subject_id),
                'consent_records': self._get_consent_records(data_subject_id)
            }
            
            # Generate response
            response_data = {
                'request_fulfilled': True,
                'data_provided': personal_data,
                'processing_purposes': self._get_processing_purposes(data_subject_id),
                'data_recipients': self._get_data_recipients(),
                'retention_periods': self._get_retention_periods(),
                'data_sources': self._get_data_sources(data_subject_id)
            }
            
            # Update event
            event.processing_status = 'completed'
            event.response_data = response_data
            event.completed_at = datetime.now()
            
            self._update_compliance_event(event)
            
        except Exception as e:
            logger.error(f"Access request processing failed: {e}")
            event.processing_status = 'failed'
            event.response_data = {'error': str(e)}
            self._update_compliance_event(event)
    
    def _process_erasure_request(self, event: ComplianceEvent):
        """Process GDPR erasure request (Article 17)"""
        
        try:
            data_subject_id = event.data_subject_id
            
            # Check if erasure is legally possible
            erasure_assessment = self._assess_erasure_eligibility(data_subject_id)
            
            if erasure_assessment['can_erase']:
                # Perform data erasure
                erasure_results = {
                    'user_profile': self._erase_user_profile(data_subject_id),
                    'booking_history': self._anonymize_booking_data(data_subject_id),
                    'payment_information': self._erase_payment_data(data_subject_id),
                    'preferences': self._erase_preference_data(data_subject_id),
                    'communication_logs': self._erase_communication_data(data_subject_id)
                }
                
                response_data = {
                    'request_fulfilled': True,
                    'erasure_completed': True,
                    'erasure_details': erasure_results
                }
            else:
                response_data = {
                    'request_fulfilled': False,
                    'erasure_completed': False,
                    'reason': erasure_assessment['reason']
                }
            
            event.processing_status = 'completed'
            event.response_data = response_data
            event.completed_at = datetime.now()
            
            self._update_compliance_event(event)
            
        except Exception as e:
            logger.error(f"Erasure request processing failed: {e}")
            event.processing_status = 'failed'
            event.response_data = {'error': str(e)}
            self._update_compliance_event(event)
    
    def _process_portability_request(self, event: ComplianceEvent):
        """Process GDPR data portability request (Article 20)"""
        
        try:
            data_subject_id = event.data_subject_id
            
            # Export data in machine-readable format
            portable_data = {
                'user_profile': self._export_user_profile(data_subject_id),
                'preferences': self._export_preferences(data_subject_id),
                'booking_history': self._export_booking_history(data_subject_id),
                'reviews_ratings': self._export_reviews_ratings(data_subject_id)
            }
            
            # Generate JSON export
            export_data = {
                'export_format': 'JSON',
                'export_timestamp': datetime.now().isoformat(),
                'data_subject_id': data_subject_id,
                'data': portable_data
            }
            
            response_data = {
                'request_fulfilled': True,
                'export_format': 'JSON',
                'export_data': export_data
            }
            
            event.processing_status = 'completed'
            event.response_data = response_data
            event.completed_at = datetime.now()
            
            self._update_compliance_event(event)
            
        except Exception as e:
            logger.error(f"Portability request processing failed: {e}")
            event.processing_status = 'failed'
            event.response_data = {'error': str(e)}
            self._update_compliance_event(event)
    
    def _store_compliance_event(self, event: ComplianceEvent):
        """Store compliance event in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO compliance_events 
            (event_id, event_type, compliance_standard, user_id, data_subject_id,
             request_details, processing_status, response_data, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.event_type,
            event.compliance_standard.value,
            event.user_id,
            event.data_subject_id,
            json.dumps(event.request_details),
            event.processing_status,
            json.dumps(event.response_data) if event.response_data else None,
            event.created_at.isoformat(),
            event.completed_at.isoformat() if event.completed_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def _update_compliance_event(self, event: ComplianceEvent):
        """Update compliance event in database"""
        self._store_compliance_event(event)  # Same as store with REPLACE
    
    # Placeholder methods for data operations (would integrate with actual data layer)
    def _get_user_profile_data(self, user_id: str) -> Dict[str, Any]:
        return {"message": "User profile data would be retrieved here"}
    
    def _get_booking_data(self, user_id: str) -> Dict[str, Any]:
        return {"message": "Booking data would be retrieved here"}
    
    def _get_payment_data(self, user_id: str) -> Dict[str, Any]:
        return {"message": "Payment data would be retrieved here"}
    
    def _get_preference_data(self, user_id: str) -> Dict[str, Any]:
        return {"message": "Preference data would be retrieved here"}
    
    def _get_communication_data(self, user_id: str) -> Dict[str, Any]:
        return {"message": "Communication data would be retrieved here"}
    
    def _get_consent_records(self, user_id: str) -> Dict[str, Any]:
        return {"message": "Consent records would be retrieved here"}
    
    def _get_processing_purposes(self, user_id: str) -> List[str]:
        return ["Service provision", "Marketing", "Analytics", "Legal compliance"]
    
    def _get_data_recipients(self) -> List[str]:
        return ["Internal teams", "Payment processors", "Analytics providers"]
    
    def _get_retention_periods(self) -> Dict[str, str]:
        return {
            "Profile data": "Until account deletion",
            "Booking data": "7 years for tax purposes",
            "Marketing data": "Until consent withdrawn"
        }
    
    def _get_data_sources(self, user_id: str) -> List[str]:
        return ["User registration", "Booking activities", "Website interactions"]
    
    def _assess_erasure_eligibility(self, user_id: str) -> Dict[str, Any]:
        # Simplified erasure assessment
        return {
            'can_erase': True,
            'reason': None
        }
    
    def _erase_user_profile(self, user_id: str) -> Dict[str, Any]:
        return {"status": "Profile data anonymized"}
    
    def _anonymize_booking_data(self, user_id: str) -> Dict[str, Any]:
        return {"status": "Booking data anonymized for legal retention"}
    
    def _erase_payment_data(self, user_id: str) -> Dict[str, Any]:
        return {"status": "Payment references removed"}
    
    def _erase_preference_data(self, user_id: str) -> Dict[str, Any]:
        return {"status": "Preferences deleted"}
    
    def _erase_communication_data(self, user_id: str) -> Dict[str, Any]:
        return {"status": "Communication logs anonymized"}
    
    def _export_user_profile(self, user_id: str) -> Dict[str, Any]:
        return {"name": "John Doe", "email": "john@example.com", "created": "2024-01-01"}
    
    def _export_preferences(self, user_id: str) -> Dict[str, Any]:
        return {"genres": ["Action", "Comedy"], "theaters": ["Theater A", "Theater B"]}
    
    def _export_booking_history(self, user_id: str) -> List[Dict[str, Any]]:
        return [{"movie": "Movie A", "date": "2024-01-15", "theater": "Theater A"}]
    
    def _export_reviews_ratings(self, user_id: str) -> List[Dict[str, Any]]:
        return [{"movie": "Movie A", "rating": 5, "review": "Great movie!"}]

class DataSecurityService:
    """Main data security and compliance service"""
    
    def __init__(self):
        self.key_manager = KeyManagementService()
        self.encryption_service = AdvancedEncryptionService(self.key_manager)
        self.compliance_manager = ComplianceManager()
        
        # Initialize default encryption keys
        self._initialize_default_keys()
    
    def _initialize_default_keys(self):
        """Initialize default encryption keys"""
        
        # Database encryption key
        self.db_key = self.key_manager.generate_symmetric_key('AES256', 'database')
        
        # File storage encryption key
        self.file_key = self.key_manager.generate_symmetric_key('AES256', 'file_storage')
        
        # Transport encryption keypair
        self.transport_private_key, self.transport_public_key = \
            self.key_manager.generate_asymmetric_keypair(2048, 'transport')
        
        logger.info("Default encryption keys initialized")
    
    async def encrypt_sensitive_data(self, data: Union[str, bytes], 
                                   data_classification: DataClassification,
                                   purpose: str = 'database') -> EncryptedData:
        """Encrypt sensitive data based on classification"""
        
        # Select appropriate key and algorithm based on classification
        if data_classification == DataClassification.RESTRICTED:
            # Use strongest encryption for restricted data
            key_id = self.db_key.key_id
            algorithm = 'AES-GCM'
        elif data_classification == DataClassification.CONFIDENTIAL:
            key_id = self.db_key.key_id
            algorithm = 'AES-GCM'
        else:
            key_id = self.db_key.key_id
            algorithm = 'AES-CBC'
        
        encrypted_data = self.encryption_service.encrypt_data_symmetric(data, key_id, algorithm)
        
        # Log encryption activity for compliance
        access_log = DataAccessLog(
            log_id=secrets.token_hex(16),
            user_id='system',  # System encryption
            data_type='sensitive_data',
            operation='encrypt',
            data_classification=data_classification,
            success=True,
            ip_address='127.0.0.1',
            user_agent='DataSecurityService',
            timestamp=datetime.now(),
            details={'algorithm': algorithm, 'key_id': key_id},
            compliance_context=[ComplianceStandard.GDPR, ComplianceStandard.PCI_DSS]
        )
        
        self.compliance_manager.log_data_access(access_log)
        
        return encrypted_data
    
    async def decrypt_sensitive_data(self, encrypted_data: EncryptedData, 
                                   user_id: str, purpose: str) -> bytes:
        """Decrypt sensitive data with access logging"""
        
        try:
            decrypted_data = self.encryption_service.decrypt_data_symmetric(encrypted_data)
            
            # Log successful decryption
            access_log = DataAccessLog(
                log_id=secrets.token_hex(16),
                user_id=user_id,
                data_type='sensitive_data',
                operation='decrypt',
                data_classification=DataClassification.CONFIDENTIAL,  # Assume confidential
                success=True,
                ip_address='127.0.0.1',
                user_agent='DataSecurityService',
                timestamp=datetime.now(),
                details={'purpose': purpose, 'data_id': encrypted_data.data_id},
                compliance_context=[ComplianceStandard.GDPR]
            )
            
            self.compliance_manager.log_data_access(access_log)
            
            return decrypted_data
            
        except Exception as e:
            # Log failed decryption
            access_log = DataAccessLog(
                log_id=secrets.token_hex(16),
                user_id=user_id,
                data_type='sensitive_data',
                operation='decrypt',
                data_classification=DataClassification.CONFIDENTIAL,
                success=False,
                ip_address='127.0.0.1',
                user_agent='DataSecurityService',
                timestamp=datetime.now(),
                details={'error': str(e), 'data_id': encrypted_data.data_id},
                compliance_context=[ComplianceStandard.GDPR]
            )
            
            self.compliance_manager.log_data_access(access_log)
            raise
    
    async def process_gdpr_request(self, request_type: str, user_id: str, 
                                 request_details: Dict[str, Any]) -> ComplianceEvent:
        """Process GDPR data subject request"""
        
        return self.compliance_manager.process_gdpr_request(request_type, user_id, request_details)
    
    async def rotate_encryption_keys(self) -> Dict[str, Any]:
        """Rotate encryption keys"""
        
        results = {}
        
        # Rotate database key
        new_db_key = self.key_manager.rotate_key(self.db_key.key_id)
        if new_db_key:
            self.db_key = new_db_key
            results['database_key'] = 'rotated'
        
        # Rotate file storage key
        new_file_key = self.key_manager.rotate_key(self.file_key.key_id)
        if new_file_key:
            self.file_key = new_file_key
            results['file_storage_key'] = 'rotated'
        
        # Rotate transport keys
        new_private_key = self.key_manager.rotate_key(self.transport_private_key.key_id)
        if new_private_key:
            # Find corresponding public key
            keypair_id = self.transport_private_key.metadata['keypair_id']
            public_key_id = f"{keypair_id}_public"
            new_public_key = self.key_manager.rotate_key(public_key_id)
            
            if new_public_key:
                self.transport_private_key = new_private_key
                self.transport_public_key = new_public_key
                results['transport_keys'] = 'rotated'
        
        logger.info(f"Key rotation completed: {results}")
        return results
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status"""
        
        # Get key status
        active_keys = len([k for k in self.key_manager.key_store.values() if k.is_active])
        
        # Get compliance status (simplified)
        compliance_status = {
            ComplianceStandard.GDPR.value: 'compliant',
            ComplianceStandard.PCI_DSS.value: 'compliant',
            ComplianceStandard.ISO27001.value: 'in_progress'
        }
        
        return {
            'encryption_status': 'active',
            'active_keys': active_keys,
            'key_rotation_due': [],  # Would check expiry dates
            'compliance_status': compliance_status,
            'last_security_scan': datetime.now().isoformat(),
            'security_level': 'enterprise'
        }

# Global data security service
data_security_service = DataSecurityService()

# Utility functions
async def encrypt_user_data(data: Union[str, bytes], classification: DataClassification) -> EncryptedData:
    """Encrypt user data"""
    return await data_security_service.encrypt_sensitive_data(data, classification)

async def decrypt_user_data(encrypted_data: EncryptedData, user_id: str, purpose: str) -> bytes:
    """Decrypt user data"""
    return await data_security_service.decrypt_sensitive_data(encrypted_data, user_id, purpose)

async def handle_gdpr_request(request_type: str, user_id: str, details: Dict[str, Any]) -> ComplianceEvent:
    """Handle GDPR data subject request"""
    return await data_security_service.process_gdpr_request(request_type, user_id, details)

async def rotate_security_keys() -> Dict[str, Any]:
    """Rotate all security keys"""
    return await data_security_service.rotate_encryption_keys()

def get_compliance_status() -> Dict[str, Any]:
    """Get compliance status"""
    return data_security_service.get_security_status()