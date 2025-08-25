"""
Core backup engine for GameVault.

This module provides the main backup engine functionality.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, cast

import bsdiff4

# Import from common library
from common.core.interfaces import ChunkingStrategy
from common.models.file_info import FileInfo as CommonFileInfo
from common.models.snapshot import Snapshot
from common.utils.filesystem import scan_directory as common_scan_directory
from common.utils.time_utils import get_timestamp

from gamevault.backup_engine.chunker import RollingHashChunker
from gamevault.backup_engine.storage import StorageManager
from gamevault.backup_engine.version_tracker import VersionTracker
from gamevault.config import get_config
from gamevault.models import FileInfo, GameVersionType, ProjectVersion
from gamevault.utils import (get_file_hash, get_file_size,
                           get_file_modification_time, is_binary_file)


class BackupEngine:
    """
    Core backup engine for GameVault.
    
    This class orchestrates the backup process, managing file scanning,
    change detection, storage, and version tracking.
    """
    
    def __init__(
        self,
        project_name: str,
        project_path: Union[str, Path],
        storage_dir: Optional[Union[str, Path]] = None,
        chunking_strategy: Optional[ChunkingStrategy] = None
    ):
        """
        Initialize the backup engine.
        
        Args:
            project_name: Name of the project
            project_path: Path to the project directory
            storage_dir: Directory where backups will be stored. If None, uses the default from config.
            chunking_strategy: Strategy for chunking binary files. If None, uses RollingHashChunker.
        """
        config = get_config()
        self.config = config
        self.project_name = project_name
        self.project_path = Path(project_path)
        
        # Directory for storing backups
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir
        
        # Initialize components
        self.storage_manager = StorageManager(self.storage_dir)
        self.version_tracker = VersionTracker(project_name, self.storage_dir)
        self.chunking_strategy = chunking_strategy or RollingHashChunker(
            min_chunk_size=config.min_chunk_size,
            max_chunk_size=config.max_chunk_size
        )
    
    def _scan_project_files(self) -> Dict[str, Dict]:
        """
        Scan the project directory for files.
        
        Returns:
            Dict[str, Dict]: Dictionary of file paths to file metadata
        """
        files = {}
        
        # Use common library scan function
        file_paths = common_scan_directory(self.project_path, ignore_patterns=self.config.ignore_patterns)
        
        for file_path in file_paths:
            rel_path = str(file_path.relative_to(self.project_path))
            
            files[rel_path] = {
                "path": rel_path,
                "size": get_file_size(file_path),
                "modified_time": get_file_modification_time(file_path),
                "is_binary": is_binary_file(file_path, self.config.binary_extensions),
                "abs_path": str(file_path)
            }
        
        return files
    
    def _detect_changes(
        self, 
        current_files: Dict[str, Dict], 
        prev_version: Optional[ProjectVersion] = None
    ) -> Tuple[Dict[str, Dict], Dict[str, FileInfo], Set[str]]:
        """
        Detect changes between the current state and the previous version.
        
        Args:
            current_files: Dictionary of current file paths to file metadata
            prev_version: Previous version to compare against
            
        Returns:
            Tuple containing:
                Dict[str, Dict]: Files that have changed
                Dict[str, FileInfo]: Files from the previous version that haven't changed
                Set[str]: Paths that have been deleted
        """
        if prev_version is None:
            # No previous version, all files are new
            return current_files, {}, set()
        
        changed_files = {}
        unchanged_files = {}
        deleted_files = set()
        
        # Check for changed or unchanged files
        for rel_path, file_meta in current_files.items():
            if rel_path in prev_version.files:
                prev_file = prev_version.files[rel_path]
                abs_path = file_meta["abs_path"]
                
                # Calculate current file hash to properly detect changes
                current_hash = get_file_hash(abs_path)
                
                # Check if content has actually changed by comparing hash values
                if current_hash != prev_file.hash or file_meta["modified_time"] > prev_file.modified_time:
                    changed_files[rel_path] = file_meta
                else:
                    # File hasn't changed, use info from previous version
                    unchanged_files[rel_path] = prev_file
            else:
                # New file
                changed_files[rel_path] = file_meta
        
        # Check for deleted files
        for rel_path in prev_version.files:
            if rel_path not in current_files:
                deleted_files.add(rel_path)
        
        return changed_files, unchanged_files, deleted_files
    
    def _process_text_file(self, file_path: Union[str, Path]) -> Tuple[str, str]:
        """
        Process a text file for backup.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple[str, str]: File ID (hash) and storage path
        """
        return self.storage_manager.store_file(file_path)
    
    def _process_binary_file(self, file_path: Union[str, Path]) -> Tuple[str, List[str]]:
        """
        Process a binary file for backup using chunking.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple[str, List[str]]: File hash and list of chunk IDs
        """
        file_path = Path(file_path)
        
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Calculate file hash
        file_hash = get_file_hash(file_path)
        
        # Chunk the file
        chunks = self.chunking_strategy.chunk_data(data)
        
        # Store chunks
        chunk_ids = []
        for chunk in chunks:
            chunk_id = self.storage_manager.store_chunk(chunk)
            chunk_ids.append(chunk_id)
        
        return file_hash, chunk_ids
    
    def _process_file(self, file_path: Union[str, Path], is_binary: bool) -> FileInfo:
        """
        Process a file for backup.
        
        Args:
            file_path: Path to the file
            is_binary: Whether the file is binary
            
        Returns:
            FileInfo: Information about the processed file
        """
        file_path = Path(file_path)
        rel_path = str(file_path.relative_to(self.project_path))
        size = get_file_size(file_path)
        modified_time = get_file_modification_time(file_path)
        
        if is_binary:
            file_hash, chunks = self._process_binary_file(file_path)
            return FileInfo(
                path=rel_path,
                size=size,
                hash=file_hash,
                modified_time=modified_time,
                is_binary=True,
                chunks=chunks
            )
        else:
            file_hash, storage_path = self._process_text_file(file_path)
            return FileInfo(
                path=rel_path,
                size=size,
                hash=file_hash,
                modified_time=modified_time,
                is_binary=False,
                storage_path=storage_path
            )
    
    def create_backup(
        self,
        name: str,
        version_type: GameVersionType = GameVersionType.DEVELOPMENT,
        description: Optional[str] = None,
        is_milestone: bool = False,
        tags: Optional[List[str]] = None
    ) -> ProjectVersion:
        """
        Create a backup of the project.
        
        Args:
            name: Name of the backup version
            version_type: Type of the version
            description: Description of the version
            is_milestone: Whether this version is a milestone
            tags: List of tags for this version
            
        Returns:
            ProjectVersion: The created version
        """
        # Get previous version if it exists
        prev_version = self.version_tracker.get_latest_version()
        
        # Scan project files
        current_files = self._scan_project_files()
        
        # Detect changes
        changed_files, unchanged_files, deleted_files = self._detect_changes(current_files, prev_version)
        
        # Process changed files
        processed_files = {}
        
        # Add unchanged files
        processed_files.update(unchanged_files)
        
        # Process and add changed files
        for rel_path, file_meta in changed_files.items():
            is_binary = file_meta["is_binary"]
            abs_path = file_meta["abs_path"]
            
            file_info = self._process_file(abs_path, is_binary)
            processed_files[rel_path] = file_info
        
        # Create a new version
        version = self.version_tracker.create_version(
            name=name,
            files=processed_files,
            version_type=version_type,
            description=description,
            is_milestone=is_milestone,
            tags=tags,
            parent_id=prev_version.id if prev_version else None
        )
        
        return version
    
    def restore_version(
        self,
        version_id: str,
        output_path: Optional[Union[str, Path]] = None,
        excluded_paths: Optional[List[str]] = None
    ) -> Path:
        """
        Restore a version of the project.
        
        Args:
            version_id: ID of the version to restore
            output_path: Path where the version should be restored. If None, creates a new directory.
            excluded_paths: List of file paths to exclude from restoration
            
        Returns:
            Path: Path to the restored project
            
        Raises:
            FileNotFoundError: If the version doesn't exist
        """
        # Get the version
        version = self.version_tracker.get_version(version_id)
        
        # Determine output path
        if output_path is None:
            timestamp = int(get_timestamp())
            output_path = self.project_path.parent / f"{self.project_name}_restore_{timestamp}"
        
        output_path = Path(output_path)
        
        # Create output directory
        os.makedirs(output_path, exist_ok=True)
        
        # Convert excluded paths to set for faster lookup
        excluded = set(excluded_paths or [])
        
        # Restore each file
        for rel_path, file_info in version.files.items():
            if rel_path in excluded:
                continue
            
            file_path = output_path / rel_path
            
            # Create parent directories
            os.makedirs(file_path.parent, exist_ok=True)
            
            if file_info.is_binary and file_info.chunks:
                # Restore binary file from chunks
                chunks = []
                for chunk_id in file_info.chunks:
                    chunk_data = self.storage_manager.retrieve_chunk(chunk_id)
                    chunks.append(chunk_data)
                
                # Combine chunks
                with open(file_path, "wb") as f:
                    for chunk in chunks:
                        f.write(chunk)
            else:
                # Restore text file
                file_id = file_info.hash
                self.storage_manager.retrieve_file(file_id, file_path)
        
        return output_path
    
    def get_version_diff(
        self, 
        version_id1: str, 
        version_id2: str
    ) -> Dict[str, str]:
        """
        Get the differences between two versions.
        
        Args:
            version_id1: ID of the first version
            version_id2: ID of the second version
            
        Returns:
            Dict[str, str]: Dictionary of file paths to change types
                (added, modified, deleted, unchanged)
        """
        # Get the versions
        version1 = self.version_tracker.get_version(version_id1)
        version2 = self.version_tracker.get_version(version_id2)
        
        diff = {}
        
        # Check for added, modified, or unchanged files
        for rel_path, file_info in version2.files.items():
            if rel_path not in version1.files:
                diff[rel_path] = "added"
            elif file_info.hash != version1.files[rel_path].hash:
                # Hash difference means content changed
                diff[rel_path] = "modified"
            elif file_info.size != version1.files[rel_path].size:
                # Size difference is another indicator of modification
                diff[rel_path] = "modified"
            elif file_info.modified_time != version1.files[rel_path].modified_time:
                # Modified time difference can indicate changes
                # This is a more aggressive detection of changes
                diff[rel_path] = "modified"
            else:
                diff[rel_path] = "unchanged"
        
        # Check for deleted files
        for rel_path in version1.files:
            if rel_path not in version2.files:
                diff[rel_path] = "deleted"
        
        return diff
    
    def get_storage_stats(self) -> Dict[str, int]:
        """
        Get statistics about the backup storage.
        
        Returns:
            Dict[str, int]: Dictionary with storage statistics
        """
        return self.storage_manager.get_storage_size()


# Import chunker here to avoid circular imports
from gamevault.backup_engine.chunker import ChunkingStrategy, RollingHashChunker