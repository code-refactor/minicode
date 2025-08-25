"""Storage backend implementations."""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from ..core.interfaces import StorageBackend
from ..utils.filesystem import ensure_directory, atomic_write
from ..utils.hashing import calculate_hash


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: Path):
        """
        Initialize local storage backend.
        
        Args:
            base_path: Base directory for storage
        """
        self.base_path = Path(base_path)
        ensure_directory(self.base_path)
    
    def _get_storage_path(self, key: str) -> Path:
        """
        Get storage path for a key using sharding.
        
        Args:
            key: Storage key (usually a hash)
        
        Returns:
            Full path for storing the data
        """
        # Use first 2 and next 2 chars for sharding
        if len(key) >= 4:
            shard1 = key[:2]
            shard2 = key[2:4]
            return self.base_path / shard1 / shard2 / key
        else:
            return self.base_path / key
    
    def store(self, data: bytes, key: Optional[str] = None) -> str:
        """
        Store data and return the storage key.
        
        Args:
            data: Data to store
            key: Optional storage key (will be generated if not provided)
        
        Returns:
            Storage key
        """
        if key is None:
            key = calculate_hash(data)
        
        storage_path = self._get_storage_path(key)
        
        # Skip if already exists (deduplication)
        if storage_path.exists():
            return key
        
        # Store the data
        atomic_write(storage_path, data)
        return key
    
    def retrieve(self, key: str) -> bytes:
        """
        Retrieve data by key.
        
        Args:
            key: Storage key
        
        Returns:
            Stored data
        
        Raises:
            FileNotFoundError: If key doesn't exist
        """
        storage_path = self._get_storage_path(key)
        
        if not storage_path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        
        with open(storage_path, 'rb') as f:
            return f.read()
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in storage.
        
        Args:
            key: Storage key
        
        Returns:
            True if key exists
        """
        storage_path = self._get_storage_path(key)
        return storage_path.exists()
    
    def delete(self, key: str) -> bool:
        """
        Delete data by key.
        
        Args:
            key: Storage key
        
        Returns:
            True if deleted, False if didn't exist
        """
        storage_path = self._get_storage_path(key)
        
        if storage_path.exists():
            storage_path.unlink()
            
            # Clean up empty directories
            try:
                storage_path.parent.rmdir()
                storage_path.parent.parent.rmdir()
            except OSError:
                pass  # Directory not empty
            
            return True
        return False
    
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all keys with optional prefix filtering.
        
        Args:
            prefix: Optional prefix to filter keys
        
        Returns:
            List of keys
        """
        keys = []
        
        for root, _, files in os.walk(self.base_path):
            for file in files:
                # Skip non-hash files
                if len(file) < 32:  # Assuming at least MD5 hash length
                    continue
                
                if prefix is None or file.startswith(prefix):
                    keys.append(file)
        
        return sorted(keys)
    
    def get_size(self, key: str) -> int:
        """
        Get size of stored data.
        
        Args:
            key: Storage key
        
        Returns:
            Size in bytes
        """
        storage_path = self._get_storage_path(key)
        if storage_path.exists():
            return storage_path.stat().st_size
        return 0
    
    def get_total_size(self) -> int:
        """
        Get total size of all stored data.
        
        Returns:
            Total size in bytes
        """
        total = 0
        for root, _, files in os.walk(self.base_path):
            for file in files:
                file_path = Path(root) / file
                total += file_path.stat().st_size
        return total