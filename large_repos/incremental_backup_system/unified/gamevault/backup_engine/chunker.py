"""
Chunking module for GameVault backup engine.

This module provides strategies for chunking binary data for efficient storage.
"""

import abc
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np
import xxhash


class ChunkingStrategy(abc.ABC):
    """
    Abstract base class for chunking strategies.
    
    Chunking strategies divide binary data into smaller chunks for efficient
    storage and deduplication.
    """
    
    @abc.abstractmethod
    def chunk_data(self, data: bytes) -> List[bytes]:
        """
        Chunk binary data.
        
        Args:
            data: Binary data to chunk
            
        Returns:
            List[bytes]: List of chunked data
        """
        pass


class FixedSizeChunker(ChunkingStrategy):
    """
    Fixed-size chunking strategy.
    
    This strategy chunks data into fixed-size pieces, which is simple but
    inefficient for detecting duplicated regions.
    """
    
    def __init__(self, chunk_size: int = 1024 * 1024):
        """
        Initialize the fixed-size chunker.
        
        Args:
            chunk_size: Size of each chunk in bytes
        """
        self.chunk_size = chunk_size
    
    def chunk_data(self, data: bytes) -> List[bytes]:
        """
        Chunk binary data into fixed-size pieces.
        
        Args:
            data: Binary data to chunk
            
        Returns:
            List[bytes]: List of chunked data
        """
        chunks = []
        
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i:i + self.chunk_size]
            chunks.append(chunk)
        
        return chunks


class RollingHashChunker(ChunkingStrategy):
    """
    Content-defined chunking using a rolling hash.
    
    This strategy uses a rolling hash to identify chunk boundaries based on
    content, which is more efficient for detecting duplicated regions.
    """
    
    def __init__(
        self,
        min_chunk_size: int = 64 * 1024,
        max_chunk_size: int = 4 * 1024 * 1024,
        window_size: int = 48,
        mask_bits: int = 13
    ):
        """
        Initialize the rolling hash chunker.
        
        Args:
            min_chunk_size: Minimum size of each chunk in bytes
            max_chunk_size: Maximum size of each chunk in bytes
            window_size: Size of the rolling hash window
            mask_bits: Number of bits to consider in the rolling hash
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.window_size = window_size
        self.mask = (1 << mask_bits) - 1
    
    def _is_boundary(self, hash_value: int) -> bool:
        """
        Check if a hash value indicates a chunk boundary.
        
        Args:
            hash_value: Rolling hash value
            
        Returns:
            bool: True if the hash value indicates a boundary
        """
        return (hash_value & self.mask) == 0
    
    def chunk_data(self, data: bytes) -> List[bytes]:
        """
        Chunk binary data using content-defined chunking.

        Args:
            data: Binary data to chunk

        Returns:
            List[bytes]: List of chunked data
        """
        if not data:
            return []

        # If data is smaller than min_chunk_size, return it as a single chunk
        if len(data) <= self.min_chunk_size:
            return [data]

        chunks = []
        start_pos = 0

        # Use a buffer to avoid creating too many small arrays
        buffer = bytearray(self.window_size)

        i = self.min_chunk_size  # Start checking for boundaries after min_chunk_size

        while i < len(data):
            # Fill the buffer with the current window
            window_start = max(0, i - self.window_size)
            window_size = min(self.window_size, i - window_start)
            buffer[:window_size] = data[window_start:i]

            # Calculate rolling hash
            hash_value = xxhash.xxh64(buffer[:window_size]).intdigest()

            # Check if we found a boundary or reached max chunk size
            if (i - start_pos >= self.min_chunk_size and self._is_boundary(hash_value)) or (i - start_pos) >= self.max_chunk_size:
                chunk = data[start_pos:i]
                chunks.append(chunk)
                start_pos = i

            i += 1

        # Add the last chunk if there's data left
        if start_pos < len(data):
            last_chunk = data[start_pos:]

            # If the last chunk is too small, merge it with the previous chunk if there is one
            if len(last_chunk) < self.min_chunk_size and chunks:
                last_full_chunk = chunks.pop()
                last_chunk = last_full_chunk + last_chunk

            chunks.append(last_chunk)

        # Verify all chunks meet the minimum size requirement
        assert all(len(chunk) >= self.min_chunk_size for chunk in chunks[:-1]), "All chunks except the last one must meet minimum size"

        return chunks


class GameAssetChunker(ChunkingStrategy):
    """
    Specialized chunking strategy for game assets.
    
    This strategy uses different approaches based on the asset type to
    optimize storage efficiency.
    """
    
    def __init__(
        self,
        min_chunk_size: int = 64 * 1024,
        max_chunk_size: int = 4 * 1024 * 1024,
        image_chunk_size: int = 1024 * 1024,
        audio_chunk_size: int = 2 * 1024 * 1024
    ):
        """
        Initialize the game asset chunker.
        
        Args:
            min_chunk_size: Minimum size of each chunk in bytes
            max_chunk_size: Maximum size of each chunk in bytes
            image_chunk_size: Chunk size for image files
            audio_chunk_size: Chunk size for audio files
        """
        self.default_chunker = RollingHashChunker(min_chunk_size, max_chunk_size)
        self.image_chunker = FixedSizeChunker(image_chunk_size)
        self.audio_chunker = FixedSizeChunker(audio_chunk_size)
    
    def chunk_data(self, data: bytes, file_extension: Optional[str] = None) -> List[bytes]:
        """
        Chunk binary data based on the file type.
        
        Args:
            data: Binary data to chunk
            file_extension: Extension of the file
            
        Returns:
            List[bytes]: List of chunked data
        """
        if not file_extension:
            return self.default_chunker.chunk_data(data)
        
        # Choose chunking strategy based on file extension
        if file_extension.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".psd"}:
            return self.image_chunker.chunk_data(data)
        elif file_extension.lower() in {".wav", ".mp3", ".ogg", ".flac", ".aif", ".aiff"}:
            return self.audio_chunker.chunk_data(data)
        else:
            return self.default_chunker.chunk_data(data)