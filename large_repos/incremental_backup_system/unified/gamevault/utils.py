"""
Utility functions for GameVault.

This module contains utility functions used throughout the backup system.
"""

from pathlib import Path
from typing import Generator, List, Optional, Set, Union

# Import from common library
from common.utils.hashing import calculate_file_hash, calculate_xxhash
from common.utils.filesystem import scan_directory as common_scan_directory, get_file_info
from common.utils.time_utils import get_timestamp, format_timestamp as common_format_timestamp
from common.compression.compressor import CompressionManager


def get_file_hash(file_path: Union[str, Path], chunk_size: int = 8192) -> str:
    """
    Calculate the SHA-256 hash of a file.
    
    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read from the file
        
    Returns:
        str: Hexadecimal digest of the file hash
    """
    return calculate_file_hash(Path(file_path), algorithm="sha256", chunk_size=chunk_size)


def get_file_xxhash(file_path: Union[str, Path], chunk_size: int = 8192) -> str:
    """
    Calculate a faster xxHash64 hash of a file.
    
    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read from the file (ignored for xxhash)
        
    Returns:
        str: Hexadecimal digest of the file hash
    """
    # Read file data and use common library xxhash function
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return calculate_xxhash(data)
    except (IOError, OSError) as e:
        raise ValueError(f"Failed to calculate xxhash for {file_path}: {str(e)}")


# Global compression manager instance (lazy initialization)
_compression_manager = None

def _get_compression_manager() -> CompressionManager:
    """Get or create the global compression manager."""
    global _compression_manager
    if _compression_manager is None:
        _compression_manager = CompressionManager(algorithm="zstd", level=3)
    return _compression_manager


def compress_data(data: bytes, level: int = 3) -> bytes:
    """
    Compress binary data using zstd.
    
    Args:
        data: Binary data to compress
        level: Compression level (0-22)
        
    Returns:
        bytes: Compressed data
    """
    # Create a compression manager with the specified level
    manager = CompressionManager(algorithm="zstd", level=level)
    return manager.compress(data)


def decompress_data(compressed_data: bytes) -> bytes:
    """
    Decompress binary data using zstd.
    
    Args:
        compressed_data: Compressed binary data
        
    Returns:
        bytes: Decompressed data
    """
    manager = _get_compression_manager()
    return manager.decompress(compressed_data)


def get_file_modification_time(file_path: Union[str, Path]) -> float:
    """
    Get the modification time of a file as a Unix timestamp.
    
    Args:
        file_path: Path to the file
        
    Returns:
        float: Modification time as a Unix timestamp
    """
    file_info = get_file_info(Path(file_path))
    return file_info.modified_time


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        int: Size of the file in bytes
    """
    file_info = get_file_info(Path(file_path))
    return file_info.size


def format_timestamp(timestamp: float) -> str:
    """
    Format a Unix timestamp as a human-readable string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        str: Formatted timestamp
    """
    return common_format_timestamp(timestamp, "%Y-%m-%d %H:%M:%S")


def generate_timestamp() -> float:
    """
    Generate a current timestamp.
    
    Returns:
        float: Current Unix timestamp
    """
    return get_timestamp()


def is_binary_file(file_path: Union[str, Path], binary_extensions: Optional[Set[str]] = None) -> bool:
    """
    Check if a file is binary based on its extension.
    
    Args:
        file_path: Path to the file
        binary_extensions: Set of binary file extensions
        
    Returns:
        bool: True if the file is binary, False otherwise
    """
    if binary_extensions is None:
        from gamevault.config import get_config
        binary_extensions = get_config().binary_extensions
    
    file_path = Path(file_path)
    return file_path.suffix.lower() in binary_extensions


def scan_directory(
    directory: Union[str, Path], 
    ignore_patterns: Optional[List[str]] = None
) -> Generator[Path, None, None]:
    """
    Scan a directory recursively for files, ignoring specified patterns.
    
    Args:
        directory: Directory to scan
        ignore_patterns: List of glob patterns to ignore
        
    Yields:
        Path: Path to each file found
    """
    if ignore_patterns is None:
        from gamevault.config import get_config
        ignore_patterns = get_config().ignore_patterns
    
    # Use common library scan_directory function
    files = common_scan_directory(Path(directory), ignore_patterns=ignore_patterns)
    
    # Yield each file (converting from list to generator for backward compatibility)
    for file_path in files:
        yield file_path