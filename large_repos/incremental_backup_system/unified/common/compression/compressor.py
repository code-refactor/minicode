"""Compression manager for the backup system."""

import zlib
import gzip
from typing import Optional
from ..core.interfaces import CompressionStrategy


class ZlibCompressor(CompressionStrategy):
    """Zlib compression implementation."""
    
    def __init__(self, level: int = 6):
        """
        Initialize zlib compressor.
        
        Args:
            level: Compression level (1-9)
        """
        self.level = max(1, min(9, level))
    
    def compress(self, data: bytes) -> bytes:
        """Compress data using zlib."""
        return zlib.compress(data, self.level)
    
    def decompress(self, data: bytes) -> bytes:
        """Decompress zlib data."""
        return zlib.decompress(data)
    
    def estimate_ratio(self, data: bytes) -> float:
        """Estimate compression ratio."""
        # Sample first 10KB for estimation
        sample_size = min(len(data), 10240)
        sample = data[:sample_size]
        compressed = self.compress(sample)
        return len(compressed) / len(sample)


class GzipCompressor(CompressionStrategy):
    """Gzip compression implementation."""
    
    def __init__(self, level: int = 6):
        """
        Initialize gzip compressor.
        
        Args:
            level: Compression level (1-9)
        """
        self.level = max(1, min(9, level))
    
    def compress(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data, compresslevel=self.level)
    
    def decompress(self, data: bytes) -> bytes:
        """Decompress gzip data."""
        return gzip.decompress(data)
    
    def estimate_ratio(self, data: bytes) -> float:
        """Estimate compression ratio."""
        sample_size = min(len(data), 10240)
        sample = data[:sample_size]
        compressed = self.compress(sample)
        return len(compressed) / len(sample)


class ZstdCompressor(CompressionStrategy):
    """Zstandard compression implementation (with fallback to zlib)."""
    
    def __init__(self, level: int = 3):
        """
        Initialize zstd compressor.
        
        Args:
            level: Compression level (1-22)
        """
        self.level = level
        self._has_zstd = False
        self._fallback = ZlibCompressor(6)
        
        try:
            import zstandard
            self._has_zstd = True
            self._cctx = zstandard.ZstdCompressor(level=level)
            self._dctx = zstandard.ZstdDecompressor()
        except ImportError:
            pass
    
    def compress(self, data: bytes) -> bytes:
        """Compress data using zstd or fallback."""
        if self._has_zstd:
            return self._cctx.compress(data)
        return self._fallback.compress(data)
    
    def decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        if self._has_zstd:
            return self._dctx.decompress(data)
        return self._fallback.decompress(data)
    
    def estimate_ratio(self, data: bytes) -> float:
        """Estimate compression ratio."""
        sample_size = min(len(data), 10240)
        sample = data[:sample_size]
        compressed = self.compress(sample)
        return len(compressed) / len(sample)


class CompressionManager:
    """Manages different compression algorithms."""
    
    def __init__(self, algorithm: str = "zstd", level: Optional[int] = None):
        """
        Initialize compression manager.
        
        Args:
            algorithm: Compression algorithm (zlib, gzip, zstd)
            level: Compression level (algorithm-specific)
        """
        self.algorithm = algorithm.lower()
        
        # Set default levels
        if level is None:
            default_levels = {
                'zlib': 6,
                'gzip': 6,
                'zstd': 3
            }
            level = default_levels.get(self.algorithm, 6)
        
        # Create compressor
        if self.algorithm == 'zlib':
            self.compressor = ZlibCompressor(level)
        elif self.algorithm == 'gzip':
            self.compressor = GzipCompressor(level)
        elif self.algorithm == 'zstd':
            self.compressor = ZstdCompressor(level)
        else:
            # Default to zlib
            self.compressor = ZlibCompressor(level)
    
    def compress(self, data: bytes) -> bytes:
        """
        Compress data.
        
        Args:
            data: Data to compress
        
        Returns:
            Compressed data
        """
        # Don't compress very small data, but still add header
        if len(data) < 100:
            return b'U' + data
        
        compressed = self.compressor.compress(data)
        
        # Only use compression if it reduces size
        if len(compressed) < len(data):
            # Add compression header
            return b'C' + compressed
        else:
            # Store uncompressed with header
            return b'U' + data
    
    def decompress(self, data: bytes) -> bytes:
        """
        Decompress data.
        
        Args:
            data: Data to decompress
        
        Returns:
            Decompressed data
        """
        if not data:
            return data
        
        # Check compression header
        if data[0:1] == b'C':
            return self.compressor.decompress(data[1:])
        elif data[0:1] == b'U':
            return data[1:]
        else:
            # Legacy data without header, try to decompress
            try:
                return self.compressor.decompress(data)
            except:
                # Assume uncompressed
                return data
    
    def estimate_ratio(self, data: bytes) -> float:
        """
        Estimate compression ratio.
        
        Args:
            data: Data to estimate
        
        Returns:
            Estimated ratio (compressed_size / original_size)
        """
        return self.compressor.estimate_ratio(data)
    
    def should_compress(self, data: bytes, threshold: float = 0.9) -> bool:
        """
        Check if data should be compressed.
        
        Args:
            data: Data to check
            threshold: Compression ratio threshold
        
        Returns:
            True if compression is beneficial
        """
        if len(data) < 100:
            return False
        
        ratio = self.estimate_ratio(data)
        return ratio < threshold