"""Version management models."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Version(BaseModel):
    """Version metadata for backup system."""
    
    id: str = Field(description="Unique version identifier")
    timestamp: float = Field(description="Creation time as Unix timestamp")
    parent_id: Optional[str] = Field(default=None, description="Parent version ID")
    snapshot_id: str = Field(description="Associated snapshot ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Version metadata")
    tags: List[str] = Field(default_factory=list, description="Version tags")
    message: Optional[str] = Field(default=None, description="Version description/message")
    author: Optional[str] = Field(default=None, description="Author of the version")
    
    @property
    def created_at(self) -> datetime:
        """Get creation time as datetime."""
        return datetime.fromtimestamp(self.timestamp)
    
    def has_tag(self, tag: str) -> bool:
        """Check if version has a specific tag."""
        return tag in self.tags
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the version."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the version."""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'created_at': self.created_at.isoformat(),
            'parent_id': self.parent_id,
            'snapshot_id': self.snapshot_id,
            'metadata': self.metadata,
            'tags': self.tags,
            'message': self.message,
            'author': self.author
        }