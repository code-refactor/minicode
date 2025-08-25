"""Core interfaces for the unified backup system."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


class BackupEngine(ABC):
    """Base interface for backup operations."""
    
    @abstractmethod
    def initialize_repository(self, path: Path) -> None:
        """Initialize a new backup repository."""
        pass
    
    @abstractmethod
    def create_snapshot(self, source_path: Path, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new backup snapshot."""
        pass
    
    @abstractmethod
    def restore_snapshot(self, snapshot_id: str, target_path: Path) -> None:
        """Restore a snapshot to the target path."""
        pass
    
    @abstractmethod
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots."""
        pass
    
    @abstractmethod
    def get_snapshot_info(self, snapshot_id: str) -> Dict[str, Any]:
        """Get detailed information about a snapshot."""
        pass


class StorageBackend(ABC):
    """Base interface for storage operations."""
    
    @abstractmethod
    def store(self, data: bytes, key: Optional[str] = None) -> str:
        """Store data and return the storage key."""
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> bytes:
        """Retrieve data by key."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in storage."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data by key."""
        pass
    
    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys with optional prefix filtering."""
        pass


class VersionManager(ABC):
    """Base interface for version management."""
    
    @abstractmethod
    def create_version(self, snapshot_id: str, parent_id: Optional[str] = None, 
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new version."""
        pass
    
    @abstractmethod
    def get_version(self, version_id: str) -> Dict[str, Any]:
        """Get version information."""
        pass
    
    @abstractmethod
    def list_versions(self) -> List[Dict[str, Any]]:
        """List all versions."""
        pass
    
    @abstractmethod
    def get_version_history(self, version_id: str) -> List[Dict[str, Any]]:
        """Get the history/lineage of a version."""
        pass
    
    @abstractmethod
    def tag_version(self, version_id: str, tag: str) -> None:
        """Add a tag to a version."""
        pass


class ChunkingStrategy(ABC):
    """Base interface for chunking strategies."""
    
    @abstractmethod
    def chunk_data(self, data: bytes) -> List[Tuple[bytes, str]]:
        """
        Chunk data into smaller pieces.
        Returns list of (chunk_data, chunk_hash) tuples.
        """
        pass
    
    @abstractmethod
    def reassemble_chunks(self, chunks: List[bytes]) -> bytes:
        """Reassemble chunks into original data."""
        pass


class CompressionStrategy(ABC):
    """Base interface for compression strategies."""
    
    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compress data."""
        pass
    
    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        pass
    
    @abstractmethod
    def estimate_ratio(self, data: bytes) -> float:
        """Estimate compression ratio without actually compressing."""
        pass


class DiffGenerator(ABC):
    """Base interface for generating differences between versions."""
    
    @abstractmethod
    def generate_diff(self, old_data: bytes, new_data: bytes) -> bytes:
        """Generate a diff between two versions."""
        pass
    
    @abstractmethod
    def apply_diff(self, old_data: bytes, diff_data: bytes) -> bytes:
        """Apply a diff to recreate the new version."""
        pass
    
    @abstractmethod
    def is_diff_efficient(self, old_data: bytes, new_data: bytes) -> bool:
        """Check if using diff would be more efficient than storing full data."""
        pass


class FileHandler(ABC):
    """Base interface for file type specific handling."""
    
    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Check if this handler can process the given file."""
        pass
    
    @abstractmethod
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a file and return metadata."""
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from a file."""
        pass