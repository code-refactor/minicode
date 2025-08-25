"""Content-addressed storage implementation."""

from pathlib import Path
from typing import Optional, Dict, Any
from ..core.interfaces import StorageBackend
from ..utils.hashing import calculate_file_hash, calculate_hash
from ..utils.filesystem import ensure_directory


class ContentAddressedStorage:
    """Hash-based storage with automatic deduplication."""
    
    def __init__(self, storage_backend: StorageBackend):
        """
        Initialize content-addressed storage.
        
        Args:
            storage_backend: Storage backend to use
        """
        self.backend = storage_backend
        self._stats = {
            'files_stored': 0,
            'files_deduplicated': 0,
            'bytes_stored': 0,
            'bytes_saved': 0
        }
    
    def store_file(self, file_path: Path) -> str:
        """
        Store a file and return its content hash.
        
        Args:
            file_path: Path to the file
        
        Returns:
            Content hash of the file
        """
        # Calculate file hash
        file_hash = calculate_file_hash(file_path)
        
        # Check if already exists (deduplication)
        if self.backend.exists(file_hash):
            self._stats['files_deduplicated'] += 1
            self._stats['bytes_saved'] += file_path.stat().st_size
            return file_hash
        
        # Read and store file
        with open(file_path, 'rb') as f:
            data = f.read()
        
        self.backend.store(data, file_hash)
        self._stats['files_stored'] += 1
        self._stats['bytes_stored'] += len(data)
        
        return file_hash
    
    def store_data(self, data: bytes) -> str:
        """
        Store raw data and return its content hash.
        
        Args:
            data: Data to store
        
        Returns:
            Content hash of the data
        """
        data_hash = calculate_hash(data)
        
        # Check if already exists
        if self.backend.exists(data_hash):
            self._stats['files_deduplicated'] += 1
            self._stats['bytes_saved'] += len(data)
            return data_hash
        
        self.backend.store(data, data_hash)
        self._stats['files_stored'] += 1
        self._stats['bytes_stored'] += len(data)
        
        return data_hash
    
    def retrieve_file(self, hash_key: str, target_path: Path) -> None:
        """
        Retrieve a file by its hash and save to target path.
        
        Args:
            hash_key: Content hash of the file
            target_path: Path to save the file
        """
        data = self.backend.retrieve(hash_key)
        
        # Ensure parent directory exists
        ensure_directory(target_path.parent)
        
        # Write file
        with open(target_path, 'wb') as f:
            f.write(data)
    
    def retrieve_data(self, hash_key: str) -> bytes:
        """
        Retrieve raw data by its hash.
        
        Args:
            hash_key: Content hash of the data
        
        Returns:
            Retrieved data
        """
        return self.backend.retrieve(hash_key)
    
    def exists(self, hash_key: str) -> bool:
        """
        Check if content exists.
        
        Args:
            hash_key: Content hash
        
        Returns:
            True if content exists
        """
        return self.backend.exists(hash_key)
    
    def delete(self, hash_key: str) -> bool:
        """
        Delete content by hash.
        
        Args:
            hash_key: Content hash
        
        Returns:
            True if deleted
        """
        return self.backend.delete(hash_key)
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        stats = self._stats.copy()
        
        # Calculate deduplication ratio
        total_processed = stats['bytes_stored'] + stats['bytes_saved']
        if total_processed > 0:
            stats['deduplication_ratio'] = stats['bytes_saved'] / total_processed
        else:
            stats['deduplication_ratio'] = 0.0
        
        # Get backend size if available
        if hasattr(self.backend, 'get_total_size'):
            stats['total_storage_size'] = self.backend.get_total_size()
        
        return stats
    
    def verify_integrity(self, hash_key: str) -> bool:
        """
        Verify integrity of stored content.
        
        Args:
            hash_key: Content hash
        
        Returns:
            True if content is valid
        """
        try:
            data = self.backend.retrieve(hash_key)
            calculated_hash = calculate_hash(data)
            return calculated_hash == hash_key
        except Exception:
            return False