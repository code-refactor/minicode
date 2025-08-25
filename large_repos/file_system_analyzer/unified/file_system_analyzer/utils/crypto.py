"""
Cryptographic utilities for secure logging and evidence integrity.

This module provides cryptographic functions for creating secure hashes,
digital signatures, and verifying the integrity of audit logs and evidence.
"""

import os
import hmac
import uuid
import hashlib
import base64
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple, ByteString

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.exceptions import InvalidSignature

# Import from common library
from common.utils.crypto import SimpleCryptoProvider


class CryptoProvider(SimpleCryptoProvider):
    """Provider of cryptographic functions for secure logging and verification."""
    
    def __init__(
        self, 
        hmac_key: Optional[bytes] = None,
        private_key_pem: Optional[bytes] = None,
        public_key_pem: Optional[bytes] = None,
        key_id: Optional[str] = None
    ):
        """Initialize with cryptographic keys."""
        # Generate a random HMAC key if none provided
        self.hmac_key = hmac_key or os.urandom(32)
        self.key_id = key_id or str(uuid.uuid4())
        
        # Load or generate RSA keys if needed
        self.private_key = None
        self.public_key = None
        
        if private_key_pem:
            self.private_key = load_pem_private_key(
                private_key_pem,
                password=None
            )
            # Generate public key from private key if not provided
            if not public_key_pem:
                self.public_key = self.private_key.public_key()
        
        if public_key_pem:
            self.public_key = load_pem_public_key(public_key_pem)
    
    @classmethod
    def generate(cls) -> "CryptoProvider":
        """Generate a new crypto provider with fresh keys."""
        # Generate a random HMAC key
        hmac_key = os.urandom(32)
        
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Serialize keys to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return cls(
            hmac_key=hmac_key,
            private_key_pem=private_pem,
            public_key_pem=public_pem
        )
    
    def hmac_sign(self, data: bytes) -> bytes:
        """Create an HMAC signature of the data."""
        return hmac.new(self.hmac_key, data, hashlib.sha256).digest()
    
    def hmac_verify(self, data: bytes, signature: bytes) -> bool:
        """Verify an HMAC signature of the data."""
        expected = self.hmac_sign(data)
        return hmac.compare_digest(expected, signature)
    
    def rsa_sign(self, data: bytes) -> Optional[bytes]:
        """Create an RSA signature of the data hash."""
        if not self.private_key:
            return None
            
        return self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    def rsa_verify(self, data: bytes, signature: bytes) -> bool:
        """Verify an RSA signature of the data hash."""
        if not self.public_key:
            return False
            
        try:
            self.public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False
    
    def export_public_key(self) -> bytes:
        """Export the public key in PEM format."""
        if not self.public_key:
            raise ValueError("No public key available to export")
            
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def secure_hash(self, data: bytes) -> str:
        """Create a secure hash of data."""
        return hashlib.sha256(data).hexdigest()
    
    def timestamp_signature(self, data: bytes) -> Dict[str, str]:
        """Create a timestamped signature of data."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data_with_timestamp = data + timestamp.encode()
        
        hmac_sig = self.hmac_sign(data_with_timestamp)
        rsa_sig = self.rsa_sign(data_with_timestamp) if self.private_key else None
        
        result = {
            "timestamp": timestamp,
            "hmac": base64.b64encode(hmac_sig).decode(),
            "key_id": self.key_id
        }
        
        if rsa_sig:
            result["rsa"] = base64.b64encode(rsa_sig).decode()
            
        return result
    
    def verify_timestamped_signature(self, 
                                    data: bytes, 
                                    signature: Dict[str, str]) -> bool:
        """Verify a timestamped signature of data."""
        try:
            timestamp = signature["timestamp"]
            hmac_sig = base64.b64decode(signature["hmac"])
            
            data_with_timestamp = data + timestamp.encode()
            
            # Verify HMAC
            valid_hmac = self.hmac_verify(data_with_timestamp, hmac_sig)
            
            # Verify RSA if present
            valid_rsa = True
            if "rsa" in signature and self.public_key:
                rsa_sig = base64.b64decode(signature["rsa"])
                valid_rsa = self.rsa_verify(data_with_timestamp, rsa_sig)
                
            return valid_hmac and valid_rsa
        except (KeyError, ValueError):
            return False