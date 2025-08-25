"""Hashing utilities for the backup system."""

import hashlib
from pathlib import Path
from typing import Optional, Union


def calculate_hash(data: bytes, algorithm: str = "sha256") -> str:
    """
    Calculate hash of data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm to use (sha256, sha1, md5)
    
    Returns:
        Hex string of the hash
    """
    if algorithm not in ['sha256', 'sha1', 'md5']:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def calculate_file_hash(file_path: Path, algorithm: str = "sha256", 
                        chunk_size: int = 8192) -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use
        chunk_size: Size of chunks to read
    
    Returns:
        Hex string of the file hash
    """
    if algorithm not in ['sha256', 'sha1', 'md5']:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def calculate_xxhash(data: bytes, seed: int = 0) -> str:
    """
    Calculate xxHash for fast non-cryptographic hashing.
    Falls back to SHA-256 if xxhash is not available.
    
    Args:
        data: Data to hash
        seed: Seed value for xxHash
    
    Returns:
        Hex string of the hash
    """
    try:
        import xxhash
        return xxhash.xxh64(data, seed=seed).hexdigest()
    except ImportError:
        # Fallback to SHA-256 if xxhash not available
        return calculate_hash(data, 'sha256')[:16]  # Use first 16 chars for similar length