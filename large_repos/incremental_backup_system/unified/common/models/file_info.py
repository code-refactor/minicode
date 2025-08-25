"""File information models."""

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FileInfo(BaseModel):
    """Universal file metadata."""
    
    path: Path = Field(description="File path relative to backup root")
    size: int = Field(description="File size in bytes")
    modified_time: float = Field(description="Last modification time as Unix timestamp")
    hash: str = Field(description="Content hash (SHA-256)")
    content_type: str = Field(description="MIME type or file type identifier")
    chunks: List[str] = Field(default_factory=list, description="List of chunk hashes if chunked")
    is_binary: bool = Field(default=False, description="Whether the file is binary")
    
    class Config:
        json_encoders = {
            Path: str
        }
    
    @property
    def modified_datetime(self) -> datetime:
        """Get modification time as datetime."""
        return datetime.fromtimestamp(self.modified_time)
    
    def to_dict(self) -> dict:
        """Convert to dictionary with path as string."""
        data = self.dict()
        data['path'] = str(self.path)
        return data
    
    @classmethod
    def from_path(cls, file_path: Path, base_path: Optional[Path] = None) -> 'FileInfo':
        """Create FileInfo from a file path."""
        import hashlib
        import mimetypes
        
        stat = file_path.stat()
        relative_path = file_path.relative_to(base_path) if base_path else file_path
        
        # Calculate hash
        hash_obj = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_obj.update(chunk)
        
        # Detect content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = 'application/octet-stream'
        
        # Simple binary detection
        is_binary = content_type.startswith('application/') or \
                   content_type.startswith('image/') or \
                   content_type.startswith('audio/') or \
                   content_type.startswith('video/')
        
        return cls(
            path=relative_path,
            size=stat.st_size,
            modified_time=stat.st_mtime,
            hash=hash_obj.hexdigest(),
            content_type=content_type,
            is_binary=is_binary
        )