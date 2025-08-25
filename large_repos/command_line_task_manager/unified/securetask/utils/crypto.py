"""Cryptographic utilities for SecureTask."""

import os
import base64
import hashlib
import hmac
from typing import Dict, Any, Tuple, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CryptoManager:
    """
    Manages cryptographic operations for secure data handling.
    
    This class provides encryption, decryption, and integrity verification
    functionality used throughout the SecureTask system.
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize the crypto manager with a secure key.
        
        Args:
            key: Optional encryption key. If not provided, a new one is generated
        """
        self.key = key if key else Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: bytes) -> Tuple[bytes, bytes]:
        """
        Encrypt data with integrity protection.
        
        Args:
            data: The binary data to encrypt
            
        Returns:
            Tuple containing (encrypted_data, hmac_digest)
        """
        encrypted = self.cipher.encrypt(data)
        digest = hmac.new(self.key, encrypted, hashlib.sha256).digest()
        return encrypted, digest
    
    def decrypt(self, encrypted_data: bytes, digest: bytes) -> bytes:
        """
        Decrypt data with integrity verification.
        
        Args:
            encrypted_data: The encrypted data
            digest: The HMAC digest for verification
            
        Returns:
            The decrypted data
            
        Raises:
            ValueError: If integrity verification fails
        """
        calculated_digest = hmac.new(self.key, encrypted_data, hashlib.sha256).digest()
        
        if not hmac.compare_digest(digest, calculated_digest):
            raise ValueError("Integrity verification failed: data may have been tampered with")
        
        return self.cipher.decrypt(encrypted_data)
    
    @staticmethod
    def derive_key_from_password(
        password: str, 
        salt: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        Derive a secure key from a password.
        
        Args:
            password: The password to derive a key from
            salt: Optional salt. If not provided, a random salt is generated
            
        Returns:
            Tuple containing (derived_key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    @staticmethod
    def hash_data(data: bytes) -> str:
        """
        Create a secure hash of data.
        
        Args:
            data: The data to hash
            
        Returns:
            Hex digest of the hash
        """
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def generate_random_id() -> str:
        """
        Generate a secure random identifier.
        
        Returns:
            A secure random hex string
        """
        return os.urandom(16).hex()