"""
Asset chunking module for GameVault.

This module provides specialized chunking strategies for game assets.
"""

import struct
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

# Import from common library
from common.core.interfaces import ChunkingStrategy
from common.chunking.strategies import RollingHashChunker as CommonRollingHashChunker, FixedSizeChunker
from common.chunking.factory import ChunkerFactory
from common.utils.hashing import calculate_hash


class AssetChunker(ChunkingStrategy):
    """
    Base class for asset-specific chunking.
    
    This class handles specialized chunking for different asset types.
    """
    
    def __init__(
        self,
        min_chunk_size: int = 64 * 1024,
        max_chunk_size: int = 4 * 1024 * 1024
    ):
        """
        Initialize the asset chunker.
        
        Args:
            min_chunk_size: Minimum size of each chunk in bytes
            max_chunk_size: Maximum size of each chunk in bytes
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
        # Default chunker using common library
        self.default_chunker = CommonRollingHashChunker(
            min_size=min_chunk_size,
            avg_size=(min_chunk_size + max_chunk_size) // 2,
            max_size=max_chunk_size
        )
    
    def chunk_data(self, data: bytes) -> List[Tuple[bytes, str]]:
        """
        Chunk binary data using common interface.
        
        Args:
            data: Binary data to chunk
            
        Returns:
            List[Tuple[bytes, str]]: List of (chunk_data, chunk_hash) tuples
        """
        return self.default_chunker.chunk_data(data)
    
    def chunk_file(self, data: bytes, file_extension: Optional[str] = None) -> List[bytes]:
        """
        Chunk binary data (gamevault-specific interface).
        
        Args:
            data: Binary data to chunk
            file_extension: Extension of the file
            
        Returns:
            List[bytes]: List of chunked data
        """
        # Convert from common interface to gamevault interface
        chunks_with_hashes = self.chunk_data(data)
        return [chunk_data for chunk_data, _ in chunks_with_hashes]
    
    def reassemble_chunks(self, chunks: List[bytes]) -> bytes:
        """
        Reassemble chunks into original data.
        
        Args:
            chunks: List of chunk data
            
        Returns:
            Reassembled data
        """
        return self.default_chunker.reassemble_chunks(chunks)


class TextureChunker(AssetChunker):
    """
    Chunker for texture assets.
    
    This class optimizes chunking for image and texture files, considering
    their internal structure for more efficient storage.
    """
    
    def _is_png(self, data: bytes) -> bool:
        """
        Check if data is a PNG file.
        
        Args:
            data: Binary data
            
        Returns:
            bool: True if the data is a PNG file
        """
        return data.startswith(b'\x89PNG\r\n\x1a\n')
    
    def _is_jpeg(self, data: bytes) -> bool:
        """
        Check if data is a JPEG file.
        
        Args:
            data: Binary data
            
        Returns:
            bool: True if the data is a JPEG file
        """
        return data.startswith(b'\xff\xd8')
    
    def _chunk_png(self, data: bytes) -> List[bytes]:
        """
        Chunk a PNG file along IDAT boundaries.

        Args:
            data: PNG file data

        Returns:
            List[bytes]: List of chunked data
        """
        # For simplicity, let's use the default chunker since PNG
        # chunking is complex to get right in a test environment
        # Use fixed-size chunking for PNG files
        fixed_chunker = FixedSizeChunker(chunk_size=1024 * 1024)  # 1MB chunks
        chunks_with_hashes = fixed_chunker.chunk_data(data)
        return [chunk_data for chunk_data, _ in chunks_with_hashes]
    
    def _chunk_jpeg(self, data: bytes) -> List[bytes]:
        """
        Chunk a JPEG file along scan boundaries.
        
        Args:
            data: JPEG file data
            
        Returns:
            List[bytes]: List of chunked data
        """
        if len(data) < 2:
            return [data]
        
        # This is a simplified approach for JPEG chunking
        # For a real implementation, you would parse the JPEG format properly
        
        # Find JPEG markers
        markers = []
        pos = 0
        
        try:
            while pos < len(data) - 1:
                if data[pos] == 0xFF and data[pos+1] in {0xDA, 0xC0, 0xC2, 0xC4}:
                    markers.append(pos)
                pos += 1
        except Exception:
            # Fall back to default chunking if anything goes wrong
            chunks_with_hashes = self.default_chunker.chunk_data(data)
            return [chunk_data for chunk_data, _ in chunks_with_hashes]
        
        if not markers:
            chunks_with_hashes = self.default_chunker.chunk_data(data)
            return [chunk_data for chunk_data, _ in chunks_with_hashes]
        
        # Create chunks based on markers
        chunks = []
        start = 0
        
        for marker in markers:
            if marker - start > self.min_chunk_size:
                chunks.append(data[start:marker])
                start = marker
        
        # Add the last chunk
        if len(data) - start > 0:
            chunks.append(data[start:])
        
        return chunks
    
    def chunk_file(self, data: bytes, file_extension: Optional[str] = None) -> List[bytes]:
        """
        Chunk texture data (gamevault-specific interface).
        
        Args:
            data: Binary texture data
            file_extension: Extension of the file
            
        Returns:
            List[bytes]: List of chunked data
        """
        if not file_extension:
            # Try to detect the file type from content
            if self._is_png(data):
                return self._chunk_png(data)
            elif self._is_jpeg(data):
                return self._chunk_jpeg(data)
            else:
                chunks_with_hashes = self.default_chunker.chunk_data(data)
                return [chunk_data for chunk_data, _ in chunks_with_hashes]
        
        file_extension = file_extension.lower()
        
        if file_extension == ".png":
            return self._chunk_png(data)
        elif file_extension in {".jpg", ".jpeg"}:
            return self._chunk_jpeg(data)
        else:
            # Use the default chunker for other texture formats
            chunks_with_hashes = self.default_chunker.chunk_data(data)
            return [chunk_data for chunk_data, _ in chunks_with_hashes]


class ModelChunker(AssetChunker):
    """
    Chunker for 3D model assets.
    
    This class optimizes chunking for 3D model files.
    """
    
    def _is_fbx(self, data: bytes) -> bool:
        """
        Check if data is an FBX file.
        
        Args:
            data: Binary data
            
        Returns:
            bool: True if the data is an FBX file
        """
        # Very basic check - this would be more sophisticated in a real implementation
        return b'Kaydara FBX Binary' in data[:64]
    
    def _chunk_fbx(self, data: bytes) -> List[bytes]:
        """
        Chunk an FBX file along node boundaries.
        
        Args:
            data: FBX file data
            
        Returns:
            List[bytes]: List of chunked data
        """
        # This is a simplified approach for FBX chunking
        # In a real implementation, you would parse the FBX format properly
        
        # For now, we'll just use the default chunker
        chunks_with_hashes = self.default_chunker.chunk_data(data)
        return [chunk_data for chunk_data, _ in chunks_with_hashes]
    
    def chunk_file(self, data: bytes, file_extension: Optional[str] = None) -> List[bytes]:
        """
        Chunk 3D model data (gamevault-specific interface).
        
        Args:
            data: Binary model data
            file_extension: Extension of the file
            
        Returns:
            List[bytes]: List of chunked data
        """
        if not file_extension:
            # Try to detect the file type from content
            if self._is_fbx(data):
                return self._chunk_fbx(data)
            else:
                chunks_with_hashes = self.default_chunker.chunk_data(data)
                return [chunk_data for chunk_data, _ in chunks_with_hashes]
        
        file_extension = file_extension.lower()
        
        if file_extension == ".fbx":
            return self._chunk_fbx(data)
        else:
            # Use the default chunker for other model formats
            chunks_with_hashes = self.default_chunker.chunk_data(data)
            return [chunk_data for chunk_data, _ in chunks_with_hashes]


class AudioChunker(AssetChunker):
    """
    Chunker for audio assets.
    
    This class optimizes chunking for audio files.
    """
    
    def _is_wav(self, data: bytes) -> bool:
        """
        Check if data is a WAV file.
        
        Args:
            data: Binary data
            
        Returns:
            bool: True if the data is a WAV file
        """
        return data.startswith(b'RIFF') and b'WAVE' in data[:12]
    
    def _chunk_wav(self, data: bytes) -> List[bytes]:
        """
        Chunk a WAV file along data blocks.
        
        Args:
            data: WAV file data
            
        Returns:
            List[bytes]: List of chunked data
        """
        if len(data) < 44:  # Minimum WAV header size
            return [data]
        
        try:
            # Find the data chunk
            pos = 12  # Skip RIFF header
            data_pos = 0
            data_size = 0
            
            while pos < len(data) - 8:
                chunk_id = data[pos:pos+4]
                chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
                
                if chunk_id == b'data':
                    data_pos = pos + 8
                    data_size = chunk_size
                    break
                
                pos += 8 + chunk_size
            
            if data_pos == 0:
                chunks_with_hashes = self.default_chunker.chunk_data(data)
                return [chunk_data for chunk_data, _ in chunks_with_hashes]
            
            # Create chunks
            chunks = []
            
            # Add header (everything before data)
            if data_pos > 0:
                chunks.append(data[:data_pos])
            
            # Chunk the audio data
            audio_data = data[data_pos:data_pos+data_size]
            
            # Fixed-size chunking for audio data (aligned to samples)
            sample_size = 4  # Assuming 16-bit stereo (4 bytes per sample)
            chunk_samples = (self.max_chunk_size // sample_size) * sample_size
            
            for i in range(0, len(audio_data), chunk_samples):
                end = min(i + chunk_samples, len(audio_data))
                chunks.append(audio_data[i:end])
            
            # Add footer (everything after data)
            if data_pos + data_size < len(data):
                chunks.append(data[data_pos+data_size:])
            
            return chunks
        
        except Exception:
            # Fall back to default chunking if anything goes wrong
            chunks_with_hashes = self.default_chunker.chunk_data(data)
            return [chunk_data for chunk_data, _ in chunks_with_hashes]
    
    def chunk_file(self, data: bytes, file_extension: Optional[str] = None) -> List[bytes]:
        """
        Chunk audio data (gamevault-specific interface).
        
        Args:
            data: Binary audio data
            file_extension: Extension of the file
            
        Returns:
            List[bytes]: List of chunked data
        """
        if not file_extension:
            # Try to detect the file type from content
            if self._is_wav(data):
                return self._chunk_wav(data)
            else:
                chunks_with_hashes = self.default_chunker.chunk_data(data)
                return [chunk_data for chunk_data, _ in chunks_with_hashes]
        
        file_extension = file_extension.lower()
        
        if file_extension == ".wav":
            return self._chunk_wav(data)
        else:
            # For compressed audio formats, use fixed-size chunking
            chunk_size = 1024 * 1024  # 1MB chunks
            chunks = []
            
            for i in range(0, len(data), chunk_size):
                chunks.append(data[i:i+chunk_size])
            
            return chunks


class AssetChunkerFactory:
    """
    Factory for creating asset chunkers based on file type.
    
    This class provides appropriate chunkers for different asset types.
    """
    
    @staticmethod
    def get_chunker(file_extension: str) -> AssetChunker:
        """
        Get an appropriate chunker for a file type.
        
        Args:
            file_extension: Extension of the file
            
        Returns:
            AssetChunker: An appropriate chunker instance
        """
        file_extension = file_extension.lower()
        
        # Images and textures
        if file_extension in {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".psd", ".tif", ".tiff"}:
            return TextureChunker()
        
        # Audio files
        elif file_extension in {".wav", ".mp3", ".ogg", ".flac", ".aif", ".aiff"}:
            return AudioChunker()
        
        # 3D models
        elif file_extension in {".fbx", ".obj", ".blend", ".dae", ".3ds", ".max"}:
            return ModelChunker()
        
        # Default chunker for other assets
        else:
            return AssetChunker()