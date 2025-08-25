"""Tests for the Crypto Utilities module."""

import os
import base64
import time
import hashlib
import hmac
from typing import Tuple

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from securetask.utils.crypto import CryptoManager


def test_crypto_manager_init():
    """Test initialization of CryptoManager."""
    # Test with auto-generated key
    crypto_manager = CryptoManager()
    assert crypto_manager.key is not None
    assert isinstance(crypto_manager.key, bytes)
    assert len(crypto_manager.key) == 44  # Base64 encoded Fernet key length
    assert crypto_manager.cipher is not None
    
    # Test with provided key
    test_key = Fernet.generate_key()
    crypto_manager = CryptoManager(key=test_key)
    assert crypto_manager.key == test_key
    assert crypto_manager.cipher is not None


def test_encrypt_decrypt():
    """Test encryption and decryption functionality."""
    # Create a crypto manager
    crypto_manager = CryptoManager()
    
    # Test with a simple string
    test_data = b"This is test data"
    
    # Encrypt the data
    encrypted, digest = crypto_manager.encrypt(test_data)
    
    # Verify encrypted data is different from original
    assert encrypted != test_data
    assert digest is not None
    assert isinstance(digest, bytes)
    
    # Decrypt and verify
    decrypted = crypto_manager.decrypt(encrypted, digest)
    assert decrypted == test_data
    
    # Test with empty data
    empty_data = b""
    encrypted_empty, digest_empty = crypto_manager.encrypt(empty_data)
    decrypted_empty = crypto_manager.decrypt(encrypted_empty, digest_empty)
    assert decrypted_empty == empty_data
    
    # Test with binary data
    binary_data = os.urandom(1024)
    encrypted_binary, digest_binary = crypto_manager.encrypt(binary_data)
    decrypted_binary = crypto_manager.decrypt(encrypted_binary, digest_binary)
    assert decrypted_binary == binary_data


def test_integrity_verification():
    """Test integrity verification during decryption."""
    crypto_manager = CryptoManager()
    
    # Encrypt some data
    test_data = b"Data that must maintain integrity"
    encrypted, digest = crypto_manager.encrypt(test_data)
    
    # Tamper with the encrypted data
    tampered_data = bytearray(encrypted)
    tampered_data[10] = (tampered_data[10] + 1) % 256
    
    # Attempt to decrypt with original digest should fail
    with pytest.raises(ValueError, match="Integrity verification failed"):
        crypto_manager.decrypt(bytes(tampered_data), digest)
    
    # Tamper with the digest
    tampered_digest = bytearray(digest)
    tampered_digest[0] = (tampered_digest[0] + 1) % 256
    
    # Attempt to decrypt with tampered digest should fail
    with pytest.raises(ValueError, match="Integrity verification failed"):
        crypto_manager.decrypt(encrypted, bytes(tampered_digest))
    
    # Correct data and digest should still work
    decrypted = crypto_manager.decrypt(encrypted, digest)
    assert decrypted == test_data


def test_derive_key_from_password():
    """Test key derivation from password."""
    # Test with auto-generated salt
    password = "secure-password-123"
    key, salt = CryptoManager.derive_key_from_password(password)
    
    assert key is not None
    assert salt is not None
    assert isinstance(key, bytes)
    assert isinstance(salt, bytes)
    assert len(salt) == 16  # Default salt length
    
    # Test with provided salt
    test_salt = os.urandom(16)
    key2, salt2 = CryptoManager.derive_key_from_password(password, test_salt)
    
    assert salt2 == test_salt
    
    # Test deterministic key derivation
    key3, _ = CryptoManager.derive_key_from_password(password, test_salt)
    assert key3 == key2
    
    # Different passwords should produce different keys
    key4, _ = CryptoManager.derive_key_from_password("different-password", test_salt)
    assert key4 != key2
    
    # Test that the derived key has the correct format for Fernet
    try:
        Fernet(key)  # Should not raise an exception if key is valid
    except Exception as e:
        pytest.fail(f"Derived key is not valid for Fernet: {e}")


def test_hash_data():
    """Test the hash_data method."""
    test_data = b"Data to be hashed"
    
    # Get hash from CryptoManager
    hash_result = CryptoManager.hash_data(test_data)
    
    # Verify the result is a string
    assert isinstance(hash_result, str)
    
    # Verify the length (SHA-256 produces 64 hex characters)
    assert len(hash_result) == 64
    
    # Verify it matches the expected SHA-256 hash
    expected_hash = hashlib.sha256(test_data).hexdigest()
    assert hash_result == expected_hash
    
    # Test with empty data
    empty_hash = CryptoManager.hash_data(b"")
    assert empty_hash == hashlib.sha256(b"").hexdigest()
    
    # Test that different data produces different hashes
    different_hash = CryptoManager.hash_data(b"Different data")
    assert different_hash != hash_result


def test_generate_random_id():
    """Test the generate_random_id method."""
    # Generate a random ID
    random_id = CryptoManager.generate_random_id()
    
    # Verify it's a string
    assert isinstance(random_id, str)
    
    # Verify length (16 bytes = 32 hex characters)
    assert len(random_id) == 32
    
    # Generate another ID and verify it's different
    another_id = CryptoManager.generate_random_id()
    assert another_id != random_id
    
    # Verify it's a valid hex string
    try:
        int(random_id, 16)  # Should not raise if valid hex
    except ValueError:
        pytest.fail("Generated ID is not a valid hex string")


def test_encrypt_decrypt_performance():
    """Test the performance of encryption and decryption operations."""
    crypto_manager = CryptoManager()
    
    # Data sizes to test
    data_sizes = [
        1024,        # 1 KB
        1024 * 10,   # 10 KB
        1024 * 100,  # 100 KB
    ]
    
    for size in data_sizes:
        test_data = os.urandom(size)
        
        # Time encryption
        start_time = time.time()
        encrypted, digest = crypto_manager.encrypt(test_data)
        encrypt_time = time.time() - start_time
        
        # Time decryption
        start_time = time.time()
        decrypted = crypto_manager.decrypt(encrypted, digest)
        decrypt_time = time.time() - start_time
        
        # Verify correct decryption
        assert decrypted == test_data
        
        # Encryption should take less than 50ms for small to medium data
        if size <= 1024 * 10:  # Up to 10KB
            assert encrypt_time < 0.050, f"Encryption of {size/1024}KB took {encrypt_time*1000:.2f}ms, should be <50ms"
            assert decrypt_time < 0.050, f"Decryption of {size/1024}KB took {decrypt_time*1000:.2f}ms, should be <50ms"
        else:
            # For larger data (100KB), allow up to 200ms
            assert encrypt_time < 0.200, f"Encryption of {size/1024}KB took {encrypt_time*1000:.2f}ms, should be <200ms"
            assert decrypt_time < 0.200, f"Decryption of {size/1024}KB took {decrypt_time*1000:.2f}ms, should be <200ms"


def test_key_reuse():
    """Test that the same key can be reused across different instances."""
    # Create a crypto manager and get its key
    crypto_manager1 = CryptoManager()
    key = crypto_manager1.key
    
    # Create another crypto manager with the same key
    crypto_manager2 = CryptoManager(key=key)
    
    # Test data
    test_data = b"This data should be decryptable by both managers"
    
    # Encrypt with the first manager
    encrypted, digest = crypto_manager1.encrypt(test_data)
    
    # Decrypt with the second manager
    decrypted = crypto_manager2.decrypt(encrypted, digest)
    
    # Verify the data is correctly decrypted
    assert decrypted == test_data
    
    # Now encrypt with the second manager
    encrypted2, digest2 = crypto_manager2.encrypt(test_data)
    
    # Decrypt with the first manager
    decrypted2 = crypto_manager1.decrypt(encrypted2, digest2)
    
    # Verify the data is correctly decrypted
    assert decrypted2 == test_data


def test_different_keys():
    """Test that different keys produce incompatible encryptions."""
    # Create two crypto managers with different keys
    crypto_manager1 = CryptoManager()
    crypto_manager2 = CryptoManager()
    
    # Ensure keys are different
    assert crypto_manager1.key != crypto_manager2.key
    
    # Test data
    test_data = b"This data should not be decryptable across managers"
    
    # Encrypt with the first manager
    encrypted, digest = crypto_manager1.encrypt(test_data)
    
    # Try to decrypt with the second manager
    with pytest.raises(Exception):
        crypto_manager2.decrypt(encrypted, digest)