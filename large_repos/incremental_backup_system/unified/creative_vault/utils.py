"""
Utility functions for the CreativeVault backup system.

This module provides common utility functions used across the various
components of the CreativeVault backup system.
"""

import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

# Import common utilities
from common.utils import (
    calculate_file_hash,
    detect_file_type,
    scan_directory as common_scan_directory,
    save_json,
    load_json,
    format_timestamp,
    get_timestamp
)
from common.models.file_info import FileInfo as CommonFileInfo


# Compatibility alias for FileInfo - use the common version
FileInfo = CommonFileInfo


class BackupConfig(BaseModel):
    """Configuration for the backup system."""
    
    repository_path: Path
    compression_level: int = 6
    deduplication_enabled: bool = True
    max_delta_chain_length: int = 10
    thumbnail_size: Tuple[int, int] = (256, 256)
    max_versions_per_file: Optional[int] = None
    storage_quota: Optional[int] = None
    
    def model_dump(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation of this object
        """
        result = {
            "repository_path": str(self.repository_path),
            "compression_level": self.compression_level,
            "deduplication_enabled": self.deduplication_enabled,
            "max_delta_chain_length": self.max_delta_chain_length,
            "thumbnail_size": self.thumbnail_size,
            "max_versions_per_file": self.max_versions_per_file,
            "storage_quota": self.storage_quota
        }
        return result
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for backwards compatibility).
        
        Returns:
            Dictionary representation of this object
        """
        return self.model_dump()


# calculate_file_hash is imported from common.utils and available directly


def detect_creative_file_type(file_path: Path) -> str:
    """Detect the type of a creative file based on its extension and content.
    
    This is a creative_vault-specific wrapper that returns categories like
    "image", "model", "adobe_project" instead of MIME types.
    
    Args:
        file_path: Path to the file
        
    Returns:
        String representing the file type (e.g., "image", "model", "project")
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Check by extension first
    extension = file_path.suffix.lower()
    
    # Image formats
    if extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', '.webp']:
        return "image"
    
    # 3D model formats
    if extension in ['.obj', '.fbx', '.blend', '.3ds', '.dae', '.glb', '.gltf', '.stl', '.ply']:
        return "model"
    
    # Adobe project formats
    if extension in ['.psd', '.ai', '.indd', '.aep', '.prproj']:
        return "adobe_project"
    
    # Autodesk formats
    if extension in ['.max', '.mb', '.ma', '.c4d']:
        return "3d_project"
    
    # If we can't determine by extension, try to check content
    try:
        with file_path.open('rb') as f:
            header = f.read(8)
            
            # Check for common file signatures
            if header.startswith(b'\x89PNG'):
                return "image"
            if header.startswith(b'\xff\xd8'):
                return "image"
            if header.startswith(b'BLENDER'):
                return "model"
    except Exception:
        pass
    
    # If we can't determine the type, return a generic type based on whether it's binary or text
    try:
        with file_path.open('r', encoding='utf-8') as f:
            f.read(1024)
        return "text"
    except UnicodeDecodeError:
        return "binary"


# Backward compatibility alias
detect_file_type = detect_creative_file_type


def scan_directory(directory_path: Path, include_patterns: Optional[List[str]] = None, 
                 exclude_patterns: Optional[List[str]] = None) -> List[FileInfo]:
    """Scan a directory and return information about all files.
    
    This is a creative_vault-specific wrapper that returns FileInfo objects
    with creative file type detection.
    
    Args:
        directory_path: Path to the directory to scan
        include_patterns: Optional list of glob patterns to include
        exclude_patterns: Optional list of glob patterns to exclude
        
    Returns:
        List of FileInfo objects for all matching files
        
    Raises:
        FileNotFoundError: If the directory does not exist
    """
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    # Use the common scan_directory to get file paths
    file_paths = common_scan_directory(directory_path, include_patterns, exclude_patterns)
    
    result = []
    for path in file_paths:
        try:
            # Create FileInfo using the common version, but override content_type with creative type
            file_info = FileInfo.from_path(path, directory_path)
            
            # Override content_type with creative-specific type detection
            creative_type = detect_creative_file_type(path)
            
            # Create a new FileInfo with the creative content_type
            result.append(
                FileInfo(
                    path=file_info.path,
                    size=file_info.size,
                    modified_time=file_info.modified_time,
                    hash=file_info.hash,
                    content_type=creative_type,
                    chunks=file_info.chunks,
                    is_binary=file_info.is_binary
                )
            )
        except Exception as e:
            # Log error and continue
            print(f"Error processing file {path}: {e}")
    
    return result


def create_timestamp() -> str:
    """Create a formatted timestamp for the current time.
    
    Returns:
        String containing the timestamp in the format YYYY-MM-DD_HH-MM-SS
    """
    return format_timestamp(get_timestamp(), '%Y-%m-%d_%H-%M-%S')


def create_unique_id(prefix: str = "") -> str:
    """Create a unique ID string.
    
    Args:
        prefix: Optional prefix to add to the ID
        
    Returns:
        String containing a unique ID
    """
    timestamp = int(time.time() * 1000)
    random_part = random.randint(0, 999999)
    return f"{prefix}{timestamp}_{random_part:06d}"


# save_json and load_json are imported from common.utils and available directly
