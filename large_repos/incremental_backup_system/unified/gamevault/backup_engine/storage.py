"""
Storage module for GameVault backup engine.

This module handles the low-level storage operations for files and chunks.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Import from common library
from common.storage.backend import LocalStorageBackend
from common.storage.content_store import ContentAddressedStorage
from common.compression.compressor import CompressionManager
from common.utils.hashing import calculate_hash, calculate_xxhash
from gamevault.config import get_config
from gamevault.utils import get_file_hash


class StorageManager:
    """
    Manages the physical storage of backed up files and chunks.
    
    This class handles the writing, reading, and organizing of files and chunks
    in the backup storage location.
    """
    
    def __init__(self, storage_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the storage manager.
        
        Args:
            storage_dir: Directory where files will be stored. If None, uses the default from config.
        """
        config = get_config()
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir / "storage"
        self.files_dir = self.storage_dir / "files"
        self.chunks_dir = self.storage_dir / "chunks"
        
        # Initialize common storage components
        file_backend = LocalStorageBackend(self.files_dir)
        chunk_backend = LocalStorageBackend(self.chunks_dir)
        
        # Create content stores with compression
        self.compression_manager = CompressionManager(algorithm="zstd", level=config.compression_level)
        self.file_store = ContentAddressedStorage(file_backend)
        self.chunk_store = ContentAddressedStorage(chunk_backend)
    
    
    def store_file(self, file_path: Union[str, Path]) -> Tuple[str, str]:
        """
        Store a file in the backup storage.
        
        Args:
            file_path: Path to the file to store
            
        Returns:
            Tuple[str, str]: File ID (hash) and storage indication
        """
        file_path = Path(file_path)
        
        # Read file data and calculate its hash
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Calculate hash of original data for file ID
        file_id = calculate_hash(data)
        
        # Compress the data
        compressed_data = self.compression_manager.compress(data)
        
        # Store using the original data hash as the key
        # Check if already exists
        if self.file_store.exists(file_id):
            storage_path = self.files_dir / file_id[:2] / file_id[2:4] / file_id
            return file_id, str(storage_path)
        
        # Store with the original hash as key
        self.file_store.backend.store(compressed_data, file_id)
        
        # Return the actual storage path
        storage_path = self.files_dir / file_id[:2] / file_id[2:4] / file_id
        return file_id, str(storage_path)
    
    def retrieve_file(self, file_id: str, output_path: Union[str, Path]) -> None:
        """
        Retrieve a file from the backup storage.
        
        Args:
            file_id: ID (hash) of the file to retrieve
            output_path: Path where the file should be written
            
        Raises:
            FileNotFoundError: If the file doesn't exist in storage
        """
        output_path = Path(output_path)
        
        # Retrieve compressed data using the file_id as key
        compressed_data = self.file_store.backend.retrieve(file_id)
        
        # Decompress the data
        data = self.compression_manager.decompress(compressed_data)
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to target file
        with open(output_path, "wb") as f:
            f.write(data)
    
    def store_chunk(self, data: bytes) -> str:
        """
        Store a chunk of data in the backup storage.
        
        Args:
            data: Binary data to store
            
        Returns:
            str: Chunk ID (hash)
        """
        # Calculate hash of original data for chunk ID
        chunk_id = calculate_hash(data)
        
        # Compress the chunk data
        compressed_data = self.compression_manager.compress(data)
        
        # Check if already exists
        if self.chunk_store.exists(chunk_id):
            return chunk_id
        
        # Store with the original hash as key
        self.chunk_store.backend.store(compressed_data, chunk_id)
        
        return chunk_id
    
    def retrieve_chunk(self, chunk_id: str) -> bytes:
        """
        Retrieve a chunk of data from the backup storage.
        
        Args:
            chunk_id: ID (hash) of the chunk to retrieve
            
        Returns:
            bytes: The chunk data
            
        Raises:
            FileNotFoundError: If the chunk doesn't exist in storage
        """
        # Retrieve compressed data using the chunk_id as key
        compressed_data = self.chunk_store.backend.retrieve(chunk_id)
        
        # Decompress and return the data
        return self.compression_manager.decompress(compressed_data)
    
    def file_exists(self, file_id: str) -> bool:
        """
        Check if a file exists in the backup storage.
        
        Args:
            file_id: ID (hash) of the file
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        return self.file_store.exists(file_id)
    
    def chunk_exists(self, chunk_id: str) -> bool:
        """
        Check if a chunk exists in the backup storage.
        
        Args:
            chunk_id: ID (hash) of the chunk
            
        Returns:
            bool: True if the chunk exists, False otherwise
        """
        return self.chunk_store.exists(chunk_id)
    
    def remove_file(self, file_id: str) -> bool:
        """
        Remove a file from the backup storage.
        
        Args:
            file_id: ID (hash) of the file
            
        Returns:
            bool: True if the file was removed, False if it didn't exist
        """
        return self.file_store.delete(file_id)
    
    def remove_chunk(self, chunk_id: str) -> bool:
        """
        Remove a chunk from the backup storage.
        
        Args:
            chunk_id: ID (hash) of the chunk
            
        Returns:
            bool: True if the chunk was removed, False if it didn't exist
        """
        return self.chunk_store.delete(chunk_id)
    
    def get_storage_size(self) -> Dict[str, int]:
        """
        Get the total size of the backup storage.
        
        Returns:
            Dict[str, int]: Dictionary with file and chunk storage sizes
        """
        file_stats = self.file_store.get_storage_stats()
        chunk_stats = self.chunk_store.get_storage_stats()
        
        file_size = file_stats.get('total_storage_size', 0)
        chunk_size = chunk_stats.get('total_storage_size', 0)
        
        return {
            "files": file_size,
            "chunks": chunk_size,
            "total": file_size + chunk_size
        }
    
    def get_file_path_by_hash(self, file_hash: str) -> Optional[Path]:
        """
        Get the storage path for a file using its hash.
        
        Args:
            file_hash: Hash of the file to find
            
        Returns:
            Optional[Path]: Path indication if found, None otherwise
        """
        if self.file_store.exists(file_hash):
            # Return a generic indication since we're using content-addressed storage
            return Path(f"content_store://{file_hash}")
        return None
    
    def get_chunks_for_file(self, file_hash: str) -> Optional[List[str]]:
        """
        Get the list of chunk IDs associated with a file.
        
        This method requires an external mapping of files to chunks.
        In a real implementation, this would query a database or index.
        For now, it implements a simple fallback approach that works
        for files directly managed by this storage system.
        
        Args:
            file_hash: Hash of the file
            
        Returns:
            Optional[List[str]]: List of chunk IDs if found, None otherwise
        """
        # In a full implementation, this would query a database or index
        # As a fallback, we check if there's a chunk with the same ID as the file
        if self.chunk_exists(file_hash):
            return [file_hash]
        
        # For files stored as-is (not chunked), there's typically no chunk mapping
        # A more complete implementation would maintain a file-to-chunks mapping
        if self.file_exists(file_hash):
            return []
            
        return None