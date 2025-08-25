"""
Asset compression module for GameVault.

This module provides specialized compression algorithms for game assets.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, BinaryIO

import bsdiff4

# Import from common library
from common.core.interfaces import CompressionStrategy
from common.compression.compressor import CompressionManager, ZstdCompressor
from common.compression.delta import DeltaCompressor as CommonDeltaCompressor


class AssetCompressor(CompressionStrategy):
    """
    Base class for asset compression.
    
    This class serves as a base for specialized asset compressors
    that optimize storage of game assets.
    """
    
    def __init__(self, compression_level: int = 3):
        """
        Initialize the asset compressor.
        
        Args:
            compression_level: Compression level (0-22 for zstd)
        """
        self.compression_manager = CompressionManager(algorithm="zstd", level=compression_level)
    
    def compress(self, data: bytes) -> bytes:
        """
        Compress binary asset data.
        
        Args:
            data: Binary data to compress
            
        Returns:
            bytes: Compressed data
        """
        return self.compression_manager.compress(data)
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """
        Decompress binary asset data.
        
        Args:
            compressed_data: Compressed binary data
            
        Returns:
            bytes: Decompressed data
        """
        return self.compression_manager.decompress(compressed_data)
    
    def estimate_ratio(self, data: bytes) -> float:
        """
        Estimate compression ratio.
        
        Args:
            data: Data to estimate
            
        Returns:
            Estimated ratio
        """
        return self.compression_manager.estimate_ratio(data)


class TextureCompressor(AssetCompressor):
    """
    Specialized compressor for texture assets.
    
    This class optimizes storage of texture assets like images and textures.
    """
    
    def __init__(self, compression_level: int = 3):
        """
        Initialize the texture compressor.
        
        Args:
            compression_level: Compression level (0-22 for zstd)
        """
        # For texture assets, we use a higher compression level
        # than the default to achieve better compression ratios  
        super().__init__(compression_level)


class AudioCompressor(AssetCompressor):
    """
    Specialized compressor for audio assets.
    
    This class optimizes storage of audio assets like sound effects and music.
    """
    
    def __init__(self, compression_level: int = 2):
        """
        Initialize the audio compressor.
        
        Args:
            compression_level: Compression level (0-22 for zstd)
        """
        # Audio files are often already compressed, so we use a lower
        # compression level to avoid diminishing returns
        super().__init__(compression_level)


class ModelCompressor(AssetCompressor):
    """
    Specialized compressor for 3D model assets.
    
    This class optimizes storage of 3D model assets.
    """
    
    def __init__(self, compression_level: int = 5):
        """
        Initialize the model compressor.
        
        Args:
            compression_level: Compression level (0-22 for zstd)
        """
        # 3D models often have good compression potential,
        # so we use a higher compression level
        super().__init__(compression_level)


class DeltaCompressor:
    """
    Delta compressor for storing differences between asset versions.
    
    This class uses binary diffing to store only the changes between
    versions of an asset, rather than entire copies.
    """
    
    def __init__(self, compression_level: int = 9):
        """
        Initialize delta compressor.
        
        Args:
            compression_level: Compression level for delta patches
        """
        self.delta_compressor = CommonDeltaCompressor()
        self.compression_manager = CompressionManager(algorithm="zstd", level=compression_level)
    
    def create_delta(self, source_data: bytes, target_data: bytes) -> bytes:
        """
        Create a binary delta between source and target data.
        
        Args:
            source_data: Original binary data
            target_data: New binary data
            
        Returns:
            bytes: Delta patch
        """
        return self.delta_compressor.create_delta(source_data, target_data)
    
    def apply_delta(self, source_data: bytes, delta_data: bytes) -> bytes:
        """
        Apply a delta patch to source data to produce target data.
        
        Args:
            source_data: Original binary data
            delta_data: Delta patch
            
        Returns:
            bytes: Reconstructed target data
        """
        return self.delta_compressor.apply_delta(source_data, delta_data)
    
    def is_delta_efficient(self, source_data: bytes, target_data: bytes) -> bool:
        """
        Check if using delta would be more efficient.
        
        Args:
            source_data: Original binary data
            target_data: New binary data
            
        Returns:
            bool: True if delta is more efficient
        """
        return self.delta_compressor.is_delta_efficient(source_data, target_data)
    
    def compress_delta(self, delta_data: bytes) -> bytes:
        """
        Compress a delta patch.
        
        Args:
            delta_data: Delta patch data
            
        Returns:
            bytes: Compressed delta patch
        """
        # Delta patches compress very well, so we use a high compression level
        return self.compression_manager.compress(delta_data)
    
    def decompress_delta(self, compressed_delta: bytes) -> bytes:
        """
        Decompress a compressed delta patch.
        
        Args:
            compressed_delta: Compressed delta patch
            
        Returns:
            bytes: Decompressed delta patch
        """
        return self.compression_manager.decompress(compressed_delta)


class AssetCompressorFactory:
    """
    Factory for creating asset compressors based on file type.
    
    This class provides appropriate compressors for different asset types.
    """
    
    @staticmethod
    def get_compressor(file_extension: str) -> AssetCompressor:
        """
        Get an appropriate compressor for a file type.
        
        Args:
            file_extension: Extension of the file
            
        Returns:
            AssetCompressor: An appropriate compressor instance
        """
        file_extension = file_extension.lower()
        
        # Images and textures
        if file_extension in {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".psd", ".tif", ".tiff"}:
            return TextureCompressor()
        
        # Audio files
        elif file_extension in {".wav", ".mp3", ".ogg", ".flac", ".aif", ".aiff"}:
            return AudioCompressor()
        
        # 3D models
        elif file_extension in {".fbx", ".obj", ".blend", ".dae", ".3ds", ".max"}:
            return ModelCompressor()
        
        # Default compressor for other assets
        else:
            return AssetCompressor()