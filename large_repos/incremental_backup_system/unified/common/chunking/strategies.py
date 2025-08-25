"""Chunking strategy implementations."""

from typing import List, Tuple
from ..core.interfaces import ChunkingStrategy
from ..utils.hashing import calculate_hash, calculate_xxhash


class FixedSizeChunker(ChunkingStrategy):
    """Fixed-size chunking for simple data."""
    
    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB default
        """
        Initialize fixed-size chunker.
        
        Args:
            chunk_size: Size of each chunk in bytes
        """
        self.chunk_size = chunk_size
    
    def chunk_data(self, data: bytes) -> List[Tuple[bytes, str]]:
        """
        Chunk data into fixed-size pieces.
        
        Args:
            data: Data to chunk
        
        Returns:
            List of (chunk_data, chunk_hash) tuples
        """
        chunks = []
        
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i:i + self.chunk_size]
            chunk_hash = calculate_hash(chunk)
            chunks.append((chunk, chunk_hash))
        
        return chunks
    
    def reassemble_chunks(self, chunks: List[bytes]) -> bytes:
        """
        Reassemble chunks into original data.
        
        Args:
            chunks: List of chunk data
        
        Returns:
            Reassembled data
        """
        return b''.join(chunks)


class RollingHashChunker(ChunkingStrategy):
    """Content-defined chunking using rolling hash."""
    
    def __init__(self, min_size: int = 64 * 1024,  # 64KB
                 avg_size: int = 256 * 1024,  # 256KB
                 max_size: int = 1024 * 1024):  # 1MB
        """
        Initialize rolling hash chunker.
        
        Args:
            min_size: Minimum chunk size
            avg_size: Average/target chunk size
            max_size: Maximum chunk size
        """
        self.min_size = min_size
        self.avg_size = avg_size
        self.max_size = max_size
        
        # Calculate mask for boundary detection
        # The mask determines the average chunk size
        self.mask = avg_size - 1
    
    def chunk_data(self, data: bytes) -> List[Tuple[bytes, str]]:
        """
        Chunk data using rolling hash for content-defined boundaries.
        
        Args:
            data: Data to chunk
        
        Returns:
            List of (chunk_data, chunk_hash) tuples
        """
        chunks = []
        offset = 0
        data_len = len(data)
        
        while offset < data_len:
            chunk_start = offset
            chunk_end = min(offset + self.max_size, data_len)
            
            # Skip to minimum size
            offset += self.min_size
            
            # Find boundary using rolling hash
            if offset < chunk_end:
                boundary = self._find_boundary(data, offset, chunk_end)
                if boundary > 0:
                    chunk_end = boundary
                else:
                    chunk_end = min(offset + self.avg_size, chunk_end)
            
            # Extract chunk
            chunk = data[chunk_start:chunk_end]
            chunk_hash = calculate_hash(chunk)
            chunks.append((chunk, chunk_hash))
            
            offset = chunk_end
        
        return chunks
    
    def reassemble_chunks(self, chunks: List[bytes]) -> bytes:
        """
        Reassemble chunks into original data.
        
        Args:
            chunks: List of chunk data
        
        Returns:
            Reassembled data
        """
        return b''.join(chunks)
    
    def _find_boundary(self, data: bytes, start: int, end: int) -> int:
        """
        Find chunk boundary using rolling hash.
        
        Args:
            data: Data to scan
            start: Start position
            end: End position
        
        Returns:
            Boundary position or -1 if not found
        """
        window_size = 48  # Rolling hash window
        
        if start + window_size > end:
            return -1
        
        # Simple rolling hash implementation
        for i in range(start, end - window_size):
            window = data[i:i + window_size]
            hash_val = int.from_bytes(calculate_xxhash(window).encode()[:8], 'big')
            
            if self._is_boundary(hash_val):
                return i + window_size
        
        return -1
    
    def _is_boundary(self, hash_value: int) -> bool:
        """
        Check if hash value indicates a chunk boundary.
        
        Args:
            hash_value: Hash value to check
        
        Returns:
            True if this is a boundary
        """
        return (hash_value & self.mask) == 0


class DeltaChunker(ChunkingStrategy):
    """Delta-based chunking for versioned data."""
    
    def __init__(self, base_chunker: ChunkingStrategy = None):
        """
        Initialize delta chunker.
        
        Args:
            base_chunker: Base chunking strategy to use
        """
        self.base_chunker = base_chunker or FixedSizeChunker()
        self._reference_data = None
        self._reference_chunks = None
    
    def set_reference(self, reference_data: bytes) -> None:
        """
        Set reference data for delta computation.
        
        Args:
            reference_data: Reference/base data
        """
        self._reference_data = reference_data
        self._reference_chunks = self.base_chunker.chunk_data(reference_data)
    
    def chunk_data(self, data: bytes) -> List[Tuple[bytes, str]]:
        """
        Chunk data with delta encoding against reference.
        
        Args:
            data: Data to chunk
        
        Returns:
            List of (chunk_data, chunk_hash) tuples
        """
        # If no reference, use base chunker
        if self._reference_data is None:
            return self.base_chunker.chunk_data(data)
        
        # For now, use simple chunking
        # In a full implementation, this would compute deltas
        chunks = self.base_chunker.chunk_data(data)
        
        # Mark chunks that are identical to reference chunks
        result = []
        ref_hashes = {chunk_hash for _, chunk_hash in self._reference_chunks}
        
        for chunk_data, chunk_hash in chunks:
            if chunk_hash in ref_hashes:
                # This chunk is identical to reference
                # In a real implementation, we'd store just a reference
                result.append((chunk_data, chunk_hash))
            else:
                result.append((chunk_data, chunk_hash))
        
        return result
    
    def reassemble_chunks(self, chunks: List[bytes]) -> bytes:
        """
        Reassemble chunks into original data.
        
        Args:
            chunks: List of chunk data
        
        Returns:
            Reassembled data
        """
        return self.base_chunker.reassemble_chunks(chunks)