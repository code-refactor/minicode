"""
Cryptographic utilities for the File System Analyzer unified library.

This module provides cryptographic functions for secure hashing, digital signatures,
and integrity verification, with fallback implementations that only use the Python
standard library.
"""

import os
import hmac
import uuid
import hashlib
import base64
import secrets
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Tuple, ByteString
from pathlib import Path

from ..core.types import HashAlgorithm, FilePath

logger = logging.getLogger(__name__)


def hash_data(data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
    """
    Calculate hash of data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm to use
        
    Returns:
        Hex string of the hash
    """
    if algorithm == HashAlgorithm.MD5:
        hasher = hashlib.md5()
    elif algorithm == HashAlgorithm.SHA1:
        hasher = hashlib.sha1()
    elif algorithm == HashAlgorithm.SHA256:
        hasher = hashlib.sha256()
    elif algorithm == HashAlgorithm.SHA512:
        hasher = hashlib.sha512()
    else:
        hasher = hashlib.sha256()
        
    hasher.update(data)
    return hasher.hexdigest()


def hash_file(file_path: FilePath, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use
        
    Returns:
        Hex string of the hash
    """
    path = Path(file_path)
    
    if algorithm == HashAlgorithm.MD5:
        hasher = hashlib.md5()
    elif algorithm == HashAlgorithm.SHA1:
        hasher = hashlib.sha1()
    elif algorithm == HashAlgorithm.SHA256:
        hasher = hashlib.sha256()
    elif algorithm == HashAlgorithm.SHA512:
        hasher = hashlib.sha512()
    else:
        hasher = hashlib.sha256()
        
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing file {file_path}: {e}")
        raise


def generate_secure_id() -> str:
    """
    Generate a cryptographically secure random ID.
    
    Returns:
        Secure random ID string
    """
    return secrets.token_hex(16)


def create_signature(data: bytes, key: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
    """
    Create an HMAC signature of data.
    
    Args:
        data: Data to sign
        key: Signing key
        algorithm: Hash algorithm to use
        
    Returns:
        Base64-encoded signature
    """
    if algorithm == HashAlgorithm.MD5:
        digest = hashlib.md5
    elif algorithm == HashAlgorithm.SHA1:
        digest = hashlib.sha1
    elif algorithm == HashAlgorithm.SHA256:
        digest = hashlib.sha256
    elif algorithm == HashAlgorithm.SHA512:
        digest = hashlib.sha512
    else:
        digest = hashlib.sha256
        
    signature = hmac.new(key, data, digest).digest()
    return base64.b64encode(signature).decode('ascii')


def verify_signature(data: bytes, signature: str, key: bytes, 
                    algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> bool:
    """
    Verify an HMAC signature.
    
    Args:
        data: Original data
        signature: Base64-encoded signature to verify
        key: Signing key
        algorithm: Hash algorithm used
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        expected_signature = create_signature(data, key, algorithm)
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False


class SimpleCryptoProvider:
    """
    Simple cryptographic provider using only standard library functions.
    
    This is a fallback implementation that doesn't require external dependencies
    but provides basic cryptographic functionality.
    """
    
    def __init__(self, hmac_key: Optional[bytes] = None, key_id: Optional[str] = None):
        """
        Initialize with cryptographic keys.
        
        Args:
            hmac_key: HMAC key for signing
            key_id: Identifier for the key
        """
        self.hmac_key = hmac_key or self._generate_key()
        self.key_id = key_id or generate_secure_id()
        
    @staticmethod
    def _generate_key(length: int = 32) -> bytes:
        """Generate a random key."""
        return secrets.token_bytes(length)
        
    def hmac_sign(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> bytes:
        """Create an HMAC signature of the data."""
        if algorithm == HashAlgorithm.MD5:
            digest = hashlib.md5
        elif algorithm == HashAlgorithm.SHA1:
            digest = hashlib.sha1
        elif algorithm == HashAlgorithm.SHA256:
            digest = hashlib.sha256
        elif algorithm == HashAlgorithm.SHA512:
            digest = hashlib.sha512
        else:
            digest = hashlib.sha256
            
        return hmac.new(self.hmac_key, data, digest).digest()
        
    def hmac_verify(self, data: bytes, signature: bytes, 
                   algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> bool:
        """Verify an HMAC signature of the data."""
        expected = self.hmac_sign(data, algorithm)
        return hmac.compare_digest(expected, signature)
        
    def secure_hash(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """Create a secure hash of data."""
        return hash_data(data, algorithm)
        
    def timestamp_signature(self, data: bytes, 
                          algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> Dict[str, str]:
        """Create a timestamped signature of data."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data_with_timestamp = data + timestamp.encode('utf-8')
        
        hmac_sig = self.hmac_sign(data_with_timestamp, algorithm)
        
        return {
            "timestamp": timestamp,
            "hmac": base64.b64encode(hmac_sig).decode('ascii'),
            "key_id": self.key_id,
            "algorithm": algorithm.value
        }
        
    def verify_timestamped_signature(self, data: bytes, signature: Dict[str, str]) -> bool:
        """Verify a timestamped signature of data."""
        try:
            timestamp = signature["timestamp"]
            hmac_sig = base64.b64decode(signature["hmac"])
            algorithm = HashAlgorithm(signature.get("algorithm", "sha256"))
            
            data_with_timestamp = data + timestamp.encode('utf-8')
            return self.hmac_verify(data_with_timestamp, hmac_sig, algorithm)
            
        except (KeyError, ValueError, Exception):
            return False


# Try to import cryptography library for advanced features
try:
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key, load_pem_public_key
    )
    from cryptography.exceptions import InvalidSignature
    
    CRYPTOGRAPHY_AVAILABLE = True
    
    class AdvancedCryptoProvider(SimpleCryptoProvider):
        """
        Advanced cryptographic provider with RSA support.
        
        This requires the cryptography library but provides RSA signatures
        and key management.
        """
        
        def __init__(
            self, 
            hmac_key: Optional[bytes] = None,
            private_key_pem: Optional[bytes] = None,
            public_key_pem: Optional[bytes] = None,
            key_id: Optional[str] = None
        ):
            """Initialize with cryptographic keys."""
            super().__init__(hmac_key, key_id)
            
            # Load or generate RSA keys
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
        def generate(cls) -> "AdvancedCryptoProvider":
            """Generate a new crypto provider with fresh keys."""
            # Generate a random HMAC key
            hmac_key = cls._generate_key()
            
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
            
        def timestamp_signature(self, data: bytes, 
                              algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> Dict[str, str]:
            """Create a timestamped signature with both HMAC and RSA."""
            timestamp = datetime.now(timezone.utc).isoformat()
            data_with_timestamp = data + timestamp.encode('utf-8')
            
            hmac_sig = self.hmac_sign(data_with_timestamp, algorithm)
            rsa_sig = self.rsa_sign(data_with_timestamp) if self.private_key else None
            
            result = {
                "timestamp": timestamp,
                "hmac": base64.b64encode(hmac_sig).decode('ascii'),
                "key_id": self.key_id,
                "algorithm": algorithm.value
            }
            
            if rsa_sig:
                result["rsa"] = base64.b64encode(rsa_sig).decode('ascii')
                
            return result
            
        def verify_timestamped_signature(self, data: bytes, signature: Dict[str, str]) -> bool:
            """Verify a timestamped signature with both HMAC and RSA validation."""
            try:
                timestamp = signature["timestamp"]
                hmac_sig = base64.b64decode(signature["hmac"])
                algorithm = HashAlgorithm(signature.get("algorithm", "sha256"))
                
                data_with_timestamp = data + timestamp.encode('utf-8')
                
                # Verify HMAC
                valid_hmac = self.hmac_verify(data_with_timestamp, hmac_sig, algorithm)
                
                # Verify RSA if present
                valid_rsa = True
                if "rsa" in signature and self.public_key:
                    rsa_sig = base64.b64decode(signature["rsa"])
                    valid_rsa = self.rsa_verify(data_with_timestamp, rsa_sig)
                    
                return valid_hmac and valid_rsa
                
            except (KeyError, ValueError, Exception):
                return False
    
    # Use advanced provider as default
    CryptoProvider = AdvancedCryptoProvider
    
except ImportError:
    # Fall back to simple provider
    CRYPTOGRAPHY_AVAILABLE = False
    CryptoProvider = SimpleCryptoProvider
    logger.info("cryptography library not available, using simple crypto provider")


class FileIntegrityChecker:
    """
    File integrity checker using cryptographic hashes.
    """
    
    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.SHA256):
        """Initialize with hash algorithm."""
        self.algorithm = algorithm
        self.known_hashes: Dict[str, str] = {}
        
    def add_file(self, file_path: FilePath) -> str:
        """
        Add a file to integrity checking and return its hash.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hash of the file
        """
        path_str = str(Path(file_path).absolute())
        file_hash = hash_file(file_path, self.algorithm)
        self.known_hashes[path_str] = file_hash
        return file_hash
        
    def verify_file(self, file_path: FilePath) -> Tuple[bool, Optional[str]]:
        """
        Verify a file's integrity.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (is_valid, current_hash)
        """
        path_str = str(Path(file_path).absolute())
        
        if path_str not in self.known_hashes:
            return False, None
            
        try:
            current_hash = hash_file(file_path, self.algorithm)
            is_valid = current_hash == self.known_hashes[path_str]
            return is_valid, current_hash
        except Exception:
            return False, None
            
    def get_changed_files(self) -> List[Tuple[str, str, str]]:
        """
        Get list of files that have changed.
        
        Returns:
            List of tuples: (file_path, old_hash, new_hash)
        """
        changed = []
        
        for file_path, old_hash in self.known_hashes.items():
            try:
                new_hash = hash_file(file_path, self.algorithm)
                if new_hash != old_hash:
                    changed.append((file_path, old_hash, new_hash))
            except Exception:
                # File may have been deleted or is inaccessible
                changed.append((file_path, old_hash, "ERROR"))
                
        return changed
        
    def export_hashes(self, output_path: FilePath) -> bool:
        """
        Export known hashes to a file.
        
        Args:
            output_path: Path to write hashes to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            
            export_data = {
                "algorithm": self.algorithm.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hashes": self.known_hashes
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            return True
        except Exception as e:
            logger.error(f"Error exporting hashes: {e}")
            return False
            
    def import_hashes(self, input_path: FilePath) -> bool:
        """
        Import known hashes from a file.
        
        Args:
            input_path: Path to read hashes from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            
            with open(input_path, 'r') as f:
                data = json.load(f)
                
            # Verify algorithm matches
            if data.get("algorithm") != self.algorithm.value:
                logger.warning(f"Algorithm mismatch: {data.get('algorithm')} vs {self.algorithm.value}")
                
            self.known_hashes.update(data.get("hashes", {}))
            return True
            
        except Exception as e:
            logger.error(f"Error importing hashes: {e}")
            return False