"""Snapshot models for backup system."""

from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime
from .file_info import FileInfo


class Snapshot(BaseModel):
    """Backup snapshot metadata."""
    
    id: str = Field(description="Unique snapshot identifier")
    timestamp: float = Field(description="Creation time as Unix timestamp")
    files: List[FileInfo] = Field(description="List of files in snapshot")
    total_size: int = Field(description="Total size of all files")
    file_count: int = Field(description="Number of files")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    parent_id: Optional[str] = Field(default=None, description="Parent snapshot ID for incremental backups")
    
    @property
    def created_at(self) -> datetime:
        """Get creation time as datetime."""
        return datetime.fromtimestamp(self.timestamp)
    
    def get_file_by_path(self, path: str) -> Optional[FileInfo]:
        """Find a file by its path."""
        for file_info in self.files:
            if str(file_info.path) == path:
                return file_info
        return None
    
    def get_files_by_type(self, content_type: str) -> List[FileInfo]:
        """Get all files matching a content type."""
        return [f for f in self.files if f.content_type.startswith(content_type)]
    
    def calculate_stats(self) -> Dict[str, Any]:
        """Calculate snapshot statistics."""
        stats = {
            'total_files': self.file_count,
            'total_size': self.total_size,
            'created_at': self.created_at.isoformat(),
            'file_types': {}
        }
        
        # Count files by type
        for file_info in self.files:
            base_type = file_info.content_type.split('/')[0]
            stats['file_types'][base_type] = stats['file_types'].get(base_type, 0) + 1
        
        return stats


class SnapshotDiff(BaseModel):
    """Difference between two snapshots."""
    
    old_snapshot_id: str = Field(description="ID of the older snapshot")
    new_snapshot_id: str = Field(description="ID of the newer snapshot")
    added_files: List[FileInfo] = Field(description="Files added in new snapshot")
    modified_files: List[FileInfo] = Field(description="Files modified in new snapshot")
    deleted_files: List[FileInfo] = Field(description="Files deleted from old snapshot")
    
    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.added_files) + len(self.modified_files) + len(self.deleted_files)
    
    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return self.total_changes > 0
    
    def get_summary(self) -> Dict[str, int]:
        """Get a summary of changes."""
        return {
            'added': len(self.added_files),
            'modified': len(self.modified_files),
            'deleted': len(self.deleted_files),
            'total': self.total_changes
        }
    
    @classmethod
    def from_snapshots(cls, old_snapshot: Snapshot, new_snapshot: Snapshot) -> 'SnapshotDiff':
        """Create a diff from two snapshots."""
        old_files = {str(f.path): f for f in old_snapshot.files}
        new_files = {str(f.path): f for f in new_snapshot.files}
        
        old_paths = set(old_files.keys())
        new_paths = set(new_files.keys())
        
        # Find added files
        added_paths = new_paths - old_paths
        added_files = [new_files[p] for p in added_paths]
        
        # Find deleted files
        deleted_paths = old_paths - new_paths
        deleted_files = [old_files[p] for p in deleted_paths]
        
        # Find modified files
        common_paths = old_paths & new_paths
        modified_files = []
        for path in common_paths:
            old_file = old_files[path]
            new_file = new_files[path]
            if old_file.hash != new_file.hash or old_file.size != new_file.size:
                modified_files.append(new_file)
        
        return cls(
            old_snapshot_id=old_snapshot.id,
            new_snapshot_id=new_snapshot.id,
            added_files=added_files,
            modified_files=modified_files,
            deleted_files=deleted_files
        )