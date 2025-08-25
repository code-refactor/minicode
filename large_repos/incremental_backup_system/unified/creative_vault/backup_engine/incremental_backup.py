"""
Incremental Backup Engine for artistic content.

This module provides the core functionality for detecting changes, creating
deltas, and maintaining version history of creative files.
"""

import json
import os
import shutil
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field

# Import common library components
from common.core.interfaces import BackupEngine as CommonBackupEngine
from common.models.file_info import FileInfo
from common.models.snapshot import Snapshot, SnapshotDiff
from common.storage.backend import LocalStorageBackend
from common.storage.content_store import ContentAddressedStorage
from common.storage.deduplicator import Deduplicator
from common.utils.filesystem import scan_directory, detect_file_type, ensure_directory
from common.utils.hashing import calculate_file_hash, calculate_hash
from common.utils.time_utils import get_timestamp, format_timestamp
from common.utils.serialization import save_json, load_json

# Import creative vault specific interfaces and utilities
from creative_vault.utils import BackupConfig, create_unique_id


class CreativeSnapshotInfo(BaseModel):
    """Creative Vault specific snapshot information extending the common Snapshot model."""
    
    id: str
    timestamp: datetime
    source_path: Path
    files_count: int
    total_size: int
    new_files: List[str]  # Changed to List[str] for JSON serialization
    modified_files: List[str]  # Changed to List[str] for JSON serialization
    deleted_files: List[str]  # Changed to List[str] for JSON serialization
    metadata: Dict[str, Any] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: str
        }
    
    def to_common_snapshot(self, files: List[FileInfo]) -> Snapshot:
        """Convert to common Snapshot model."""
        return Snapshot(
            id=self.id,
            timestamp=self.timestamp.timestamp(),
            files=files,
            total_size=self.total_size,
            file_count=self.files_count,
            metadata=self.metadata
        )


class DeltaBackupEngine(CommonBackupEngine):
    """Implementation of the incremental backup engine using delta storage."""
    
    def __init__(self, config: Optional[BackupConfig] = None):
        """Initialize the backup engine.
        
        Args:
            config: Optional configuration for the backup engine
        """
        self.config = config or BackupConfig(repository_path=Path("backups"))
        self._repository_path = self.config.repository_path
        self._snapshots_path = self._repository_path / "snapshots"
        self._objects_path = self._repository_path / "objects"
        self._metadata_path = self._repository_path / "metadata"
        
        # Initialize common storage components
        self._storage_backend = LocalStorageBackend(self._objects_path)
        self._content_store = ContentAddressedStorage(self._storage_backend)
        self._deduplicator = Deduplicator(self._metadata_path / "dedup_index.json")
        
        # Cache of file hashes to avoid recalculating
        self._hash_cache: Dict[Path, str] = {}
        
        # Cache of file metadata
        self._file_metadata_cache: Dict[Path, Dict[str, Any]] = {}
    
    def initialize_repository(self, root_path: Path) -> None:
        """Initialize a new backup repository at the specified path.
        
        Args:
            root_path: Path where the backup repository will be created
            
        Returns:
            bool: True if initialization was successful
        """
        # Update repository path
        self._repository_path = root_path
        self._snapshots_path = self._repository_path / "snapshots"
        self._objects_path = self._repository_path / "objects"
        self._metadata_path = self._repository_path / "metadata"
        
        # Create directory structure using common utilities
        ensure_directory(self._snapshots_path)
        ensure_directory(self._objects_path)
        ensure_directory(self._metadata_path)
        
        # Reinitialize storage components with new paths
        self._storage_backend = LocalStorageBackend(self._objects_path)
        self._content_store = ContentAddressedStorage(self._storage_backend)
        self._deduplicator = Deduplicator(self._metadata_path / "dedup_index.json")
        
        # Create repository metadata
        repo_metadata = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "config": self.config.model_dump(),
        }
        save_json(repo_metadata, self._repository_path / "repository.json")
        
        return True
    
    def create_snapshot(self, source_path: Path, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new snapshot of the source directory.
        
        Args:
            source_path: Path to the directory to backup
            metadata: Optional metadata to store with the snapshot
            
        Returns:
            str: Unique ID of the created snapshot
        """
        snapshot_id = create_unique_id("snapshot-")
        snapshot_path = self._snapshots_path / snapshot_id
        snapshot_path.mkdir(parents=True, exist_ok=True)
        
        # Scan the source directory using common utilities
        file_paths = scan_directory(source_path)
        current_files = [FileInfo.from_path(fp, source_path) for fp in file_paths]
        
        # Get the previous snapshot if available
        previous_snapshot = self._get_latest_snapshot()
        previous_files = {}
        
        if previous_snapshot:
            # Load the previous file list
            previous_files_path = self._snapshots_path / previous_snapshot / "files.json"
            if previous_files_path.exists():
                previous_file_list = load_json(previous_files_path)
                previous_files = {Path(f["path"]): f for f in previous_file_list}
        
        # Identify new, modified, and deleted files
        new_files = []
        modified_files = []
        deleted_files = []
        unchanged_files = []
        
        # Current files as a dictionary for easy lookup
        current_files_dict = {f.path: f for f in current_files}
        
        # Check for new and modified files
        for file_info in current_files:
            file_path = file_info.path
            
            if file_path not in previous_files:
                new_files.append(file_path)
                # Hash is already calculated by FileInfo.from_path()
            else:
                prev_file = previous_files[file_path]
                # Check if the file has been modified
                if prev_file["modified_time"] != file_info.modified_time or prev_file["size"] != file_info.size:
                    modified_files.append(file_path)
                    # Hash is already calculated by FileInfo.from_path()
                else:
                    unchanged_files.append(file_path)
                    # Reuse hash from previous snapshot
                    file_info.hash = prev_file["hash"]
        
        # Check for deleted files
        for file_path in previous_files:
            if file_path not in current_files_dict:
                deleted_files.append(file_path)
        
        # Create snapshot metadata
        total_size = sum(f.size for f in current_files)
        snapshot_info = CreativeSnapshotInfo(
            id=snapshot_id,
            timestamp=datetime.now(),
            source_path=source_path,
            files_count=len(current_files),
            total_size=total_size,
            new_files=[str(p) for p in new_files],
            modified_files=[str(p) for p in modified_files],
            deleted_files=[str(p) for p in deleted_files],
            metadata=metadata or {}
        )
        
        # Save snapshot metadata
        save_json(snapshot_info.model_dump(), snapshot_path / "info.json")
        
        # Save file list
        file_list = [f.model_dump() for f in current_files]
        save_json(file_list, snapshot_path / "files.json")
        
        # Store new and modified files using content store
        for file_path in new_files + modified_files:
            full_path = source_path / file_path
            file_hash = self._content_store.store_file(full_path)
            # Add reference for deduplication
            self._deduplicator.add_reference(file_hash, snapshot_id)
        
        # Create snapshot manifest that lists all files in this snapshot
        manifest = {
            "id": snapshot_id,
            "timestamp": datetime.now().isoformat(),
            "files": {}
        }
        
        for file_info in current_files:
            manifest["files"][str(file_info.path)] = {
                "hash": file_info.hash,
                "size": file_info.size,
                "modified_time": file_info.modified_time,
                "content_type": file_info.content_type
            }
        
        # Save the manifest
        save_json(manifest, snapshot_path / "manifest.json")
        
        return snapshot_id
    
    def restore_snapshot(self, snapshot_id: str, target_path: Path) -> None:
        """Restore a specific snapshot to the target path.
        
        Args:
            snapshot_id: ID of the snapshot to restore
            target_path: Path where the snapshot will be restored
            
        Returns:
            bool: True if restore was successful
        """
        snapshot_path = self._snapshots_path / snapshot_id
        
        if not snapshot_path.exists():
            raise ValueError(f"Snapshot {snapshot_id} does not exist")
        
        # Create target directory if it doesn't exist using common utilities
        ensure_directory(target_path)
        
        # Load the snapshot manifest
        manifest_path = snapshot_path / "manifest.json"
        manifest = load_json(manifest_path)
        
        # Restore each file using content store
        for file_path_str, file_info in manifest["files"].items():
            file_path = Path(file_path_str)
            file_hash = file_info["hash"]
            
            target_file_path = target_path / file_path
            
            # Create target file directory if needed
            ensure_directory(target_file_path.parent)
            
            # Retrieve the file from content store
            if not self._content_store.exists(file_hash):
                raise FileNotFoundError(f"Content not found for {file_path} (hash: {file_hash})")
            
            self._content_store.retrieve_file(file_hash, target_file_path)
        
        return True
    
    def get_snapshot_info(self, snapshot_id: str) -> Dict[str, Any]:
        """Get metadata about a specific snapshot.
        
        Args:
            snapshot_id: ID of the snapshot
            
        Returns:
            Dict containing snapshot metadata
        """
        snapshot_path = self._snapshots_path / snapshot_id
        info_path = snapshot_path / "info.json"
        
        if not info_path.exists():
            raise ValueError(f"Snapshot {snapshot_id} does not exist")
        
        return load_json(info_path)
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all snapshots matching the filter criteria.
        
        Args:
            filter_criteria: Optional criteria to filter snapshots
            
        Returns:
            List of dictionaries containing snapshot metadata
        """
        result = []
        
        for snapshot_dir in self._snapshots_path.iterdir():
            if not snapshot_dir.is_dir():
                continue
            
            info_path = snapshot_dir / "info.json"
            if not info_path.exists():
                continue
            
            try:
                info = load_json(info_path)
                result.append(info)
            except Exception as e:
                print(f"Error reading snapshot info {snapshot_dir.name}: {e}")
        
        # Sort by timestamp
        result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return result
    
    def list_snapshots_filtered(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List snapshots with filter criteria (creative vault specific method).
        
        Args:
            filter_criteria: Optional criteria to filter snapshots
            
        Returns:
            List of dictionaries containing snapshot metadata
        """
        all_snapshots = self.list_snapshots()
        
        if not filter_criteria:
            return all_snapshots
        
        filtered_result = []
        for info in all_snapshots:
            match = True
            for key, value in filter_criteria.items():
                if key not in info or info[key] != value:
                    match = False
                    break
            
            if match:
                filtered_result.append(info)
        
        return filtered_result
    
    def _get_latest_snapshot(self) -> Optional[str]:
        """Get the ID of the most recent snapshot.
        
        Returns:
            str: The ID of the most recent snapshot, or None if no snapshots exist
        """
        snapshots = self.list_snapshots()
        if not snapshots:
            return None
        
        return snapshots[0]["id"]
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics using common components.
        
        Returns:
            Dictionary with storage statistics
        """
        content_stats = self._content_store.get_storage_stats()
        dedup_stats = self._deduplicator.get_statistics()
        
        return {
            **content_stats,
            **dedup_stats,
            'repository_path': str(self._repository_path)
        }
    
    def cleanup_orphaned_content(self) -> List[str]:
        """Clean up orphaned content that is no longer referenced.
        
        Returns:
            List of cleaned up content hashes
        """
        orphaned = self._deduplicator.cleanup_orphaned()
        cleaned = []
        
        for hash_key in orphaned:
            if self._content_store.delete(hash_key):
                cleaned.append(hash_key)
        
        return cleaned