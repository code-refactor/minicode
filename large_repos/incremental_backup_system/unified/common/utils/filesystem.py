"""Filesystem utilities for the backup system."""

import os
import json
import tempfile
import shutil
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any
from ..models.file_info import FileInfo


def scan_directory(path: Path, patterns: Optional[List[str]] = None,
                  ignore_patterns: Optional[List[str]] = None) -> List[Path]:
    """
    Scan directory recursively for files.
    
    Args:
        path: Directory to scan
        patterns: Include patterns (glob style)
        ignore_patterns: Exclude patterns (glob style)
    
    Returns:
        List of file paths
    """
    if not path.exists():
        return []
    
    files = []
    ignore_patterns = ignore_patterns or []
    
    # Default ignore patterns
    default_ignores = ['.git', '__pycache__', '*.pyc', '.DS_Store', 'Thumbs.db']
    ignore_patterns.extend(default_ignores)
    
    for root, dirs, filenames in os.walk(path):
        root_path = Path(root)
        
        # Filter directories
        dirs[:] = [d for d in dirs if not any(
            root_path.joinpath(d).match(pattern) for pattern in ignore_patterns
        )]
        
        # Filter files
        for filename in filenames:
            file_path = root_path / filename
            
            # Check ignore patterns
            if any(file_path.match(pattern) for pattern in ignore_patterns):
                continue
            
            # Check include patterns
            if patterns:
                if not any(file_path.match(pattern) for pattern in patterns):
                    continue
            
            files.append(file_path)
    
    return sorted(files)


def get_file_info(file_path: Path, base_path: Optional[Path] = None) -> FileInfo:
    """
    Get file information.
    
    Args:
        file_path: Path to the file
        base_path: Base path for relative path calculation
    
    Returns:
        FileInfo object
    """
    return FileInfo.from_path(file_path, base_path)


def ensure_directory(path: Path) -> None:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)


def atomic_write(path: Path, data: bytes) -> None:
    """
    Write data to file atomically.
    
    Args:
        path: File path
        data: Data to write
    """
    # Ensure parent directory exists
    ensure_directory(path.parent)
    
    # Write to temporary file first
    with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    
    # Atomic rename
    tmp_path.replace(path)


def detect_file_type(file_path: Path) -> str:
    """
    Detect file type based on extension and content.
    
    Args:
        file_path: Path to the file
    
    Returns:
        MIME type string
    """
    # Try to detect from extension first
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type:
        return mime_type
    
    # Try to detect from content (simple detection)
    try:
        with open(file_path, 'rb') as f:
            header = f.read(512)
        
        # Check for common binary file signatures
        if header.startswith(b'\x89PNG'):
            return 'image/png'
        elif header.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return 'image/gif'
        elif header.startswith(b'%PDF'):
            return 'application/pdf'
        elif header.startswith(b'PK\x03\x04'):
            return 'application/zip'
        elif header.startswith(b'\x1f\x8b'):
            return 'application/gzip'
        
        # Check if it's text
        try:
            header.decode('utf-8')
            return 'text/plain'
        except UnicodeDecodeError:
            pass
    except Exception:
        pass
    
    # Default to binary
    return 'application/octet-stream'