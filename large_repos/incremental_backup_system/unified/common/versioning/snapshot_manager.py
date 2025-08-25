"""Snapshot management for the backup system."""

import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from ..models.snapshot import Snapshot, SnapshotDiff
from ..models.file_info import FileInfo
from ..storage.content_store import ContentAddressedStorage
from ..storage.deduplicator import Deduplicator
from ..utils.time_utils import get_timestamp
from ..utils.serialization import save_json, load_json


class SnapshotManager:
    """Manages backup snapshots."""
    
    def __init__(self, storage: ContentAddressedStorage, metadata_path: Path):
        """
        Initialize snapshot manager.
        
        Args:
            storage: Content-addressed storage
            metadata_path: Path for storing snapshot metadata
        """
        self.storage = storage
        self.metadata_path = Path(metadata_path)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        self.deduplicator = Deduplicator(self.metadata_path / "dedup_index.json")
    
    def create_snapshot(self, files: List[FileInfo], 
                       parent_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Snapshot:
        """
        Create a new snapshot.
        
        Args:
            files: List of files to include
            parent_id: Optional parent snapshot ID for incremental backup
            metadata: Optional additional metadata
        
        Returns:
            Created snapshot
        """
        snapshot_id = str(uuid.uuid4())
        timestamp = get_timestamp()
        
        # Store file contents and update deduplication index
        stored_files = []
        for file_info in files:
            # Store file if it has a physical path
            if hasattr(file_info, '_original_path'):
                file_hash = self.storage.store_file(file_info._original_path)
                file_info.hash = file_hash
            
            # Track in deduplicator
            self.deduplicator.add_reference(file_info.hash, snapshot_id)
            stored_files.append(file_info)
        
        # Calculate totals
        total_size = sum(f.size for f in stored_files)
        file_count = len(stored_files)
        
        # Create snapshot
        snapshot = Snapshot(
            id=snapshot_id,
            timestamp=timestamp,
            files=stored_files,
            total_size=total_size,
            file_count=file_count,
            metadata=metadata or {},
            parent_id=parent_id
        )
        
        # Save snapshot metadata
        self._save_snapshot(snapshot)
        
        return snapshot
    
    def restore_snapshot(self, snapshot: Snapshot, target_path: Path) -> None:
        """
        Restore a snapshot to the target path.
        
        Args:
            snapshot: Snapshot to restore
            target_path: Target directory
        """
        target_path = Path(target_path)
        target_path.mkdir(parents=True, exist_ok=True)
        
        for file_info in snapshot.files:
            target_file = target_path / file_info.path
            
            # Retrieve and write file
            self.storage.retrieve_file(file_info.hash, target_file)
            
            # Restore modification time if possible
            if hasattr(file_info, 'modified_time'):
                import os
                os.utime(target_file, (file_info.modified_time, file_info.modified_time))
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """
        Get a snapshot by ID.
        
        Args:
            snapshot_id: Snapshot ID
        
        Returns:
            Snapshot or None if not found
        """
        snapshot_file = self.metadata_path / f"{snapshot_id}.json"
        if not snapshot_file.exists():
            return None
        
        data = load_json(snapshot_file)
        
        # Convert file info dicts to FileInfo objects
        files = [FileInfo(**f) for f in data['files']]
        data['files'] = files
        
        return Snapshot(**data)
    
    def list_snapshots(self) -> List[Snapshot]:
        """
        List all snapshots.
        
        Returns:
            List of snapshots
        """
        snapshots = []
        
        for snapshot_file in self.metadata_path.glob("*.json"):
            if snapshot_file.name == "dedup_index.json":
                continue
            
            try:
                snapshot = self.get_snapshot(snapshot_file.stem)
                if snapshot:
                    snapshots.append(snapshot)
            except Exception:
                continue
        
        # Sort by timestamp
        return sorted(snapshots, key=lambda s: s.timestamp)
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot.
        
        Args:
            snapshot_id: Snapshot ID
        
        Returns:
            True if deleted
        """
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            return False
        
        # Remove from deduplicator and get orphaned content
        orphaned_hashes = self.deduplicator.remove_source(snapshot_id)
        
        # Delete orphaned content from storage
        for hash_key in orphaned_hashes:
            self.storage.delete(hash_key)
        
        # Delete snapshot metadata
        snapshot_file = self.metadata_path / f"{snapshot_id}.json"
        snapshot_file.unlink()
        
        return True
    
    def diff_snapshots(self, old_snapshot: Snapshot, new_snapshot: Snapshot) -> SnapshotDiff:
        """
        Calculate difference between two snapshots.
        
        Args:
            old_snapshot: Older snapshot
            new_snapshot: Newer snapshot
        
        Returns:
            Snapshot difference
        """
        return SnapshotDiff.from_snapshots(old_snapshot, new_snapshot)
    
    def create_incremental_snapshot(self, source_path: Path, 
                                   parent_id: str,
                                   metadata: Optional[Dict[str, Any]] = None) -> Snapshot:
        """
        Create an incremental snapshot based on a parent.
        
        Args:
            source_path: Source directory
            parent_id: Parent snapshot ID
            metadata: Optional metadata
        
        Returns:
            Created incremental snapshot
        """
        parent_snapshot = self.get_snapshot(parent_id)
        if not parent_snapshot:
            raise ValueError(f"Parent snapshot {parent_id} not found")
        
        # Scan current files
        from ..utils.filesystem import scan_directory, get_file_info
        current_files = []
        
        for file_path in scan_directory(source_path):
            file_info = get_file_info(file_path, source_path)
            file_info._original_path = file_path  # Store original path for storage
            current_files.append(file_info)
        
        # Create snapshot with parent reference
        return self.create_snapshot(current_files, parent_id, metadata)
    
    def _save_snapshot(self, snapshot: Snapshot) -> None:
        """Save snapshot metadata to disk."""
        snapshot_file = self.metadata_path / f"{snapshot.id}.json"
        
        # Convert to dict for serialization
        data = snapshot.dict()
        
        # Convert FileInfo objects to dicts
        data['files'] = [f.to_dict() if hasattr(f, 'to_dict') else f.dict() for f in snapshot.files]
        
        save_json(data, snapshot_file)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get snapshot statistics.
        
        Returns:
            Statistics dictionary
        """
        snapshots = self.list_snapshots()
        
        if not snapshots:
            return {
                'total_snapshots': 0,
                'total_files': 0,
                'total_size': 0,
                'deduplication_stats': {}
            }
        
        total_files = sum(s.file_count for s in snapshots)
        total_size = sum(s.total_size for s in snapshots)
        
        return {
            'total_snapshots': len(snapshots),
            'total_files': total_files,
            'total_size': total_size,
            'oldest_snapshot': snapshots[0].created_at.isoformat(),
            'newest_snapshot': snapshots[-1].created_at.isoformat(),
            'deduplication_stats': self.deduplicator.get_statistics(),
            'storage_stats': self.storage.get_storage_stats()
        }