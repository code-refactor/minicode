"""
Version tracking module for GameVault backup engine.

This module manages version history and tracking for game projects.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from gamevault.config import get_config
from gamevault.models import FileInfo, GameVersionType, ProjectVersion
from gamevault.utils import generate_timestamp


class VersionTracker:
    """
    Tracks and manages project versions and their history.
    
    This class handles tracking versions of a game project, including file changes,
    version metadata, and relationships between versions.
    """
    
    def __init__(self, project_name: str, storage_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the version tracker.
        
        Args:
            project_name: Name of the project
            storage_dir: Directory where version data will be stored. If None, uses the default from config.
        """
        config = get_config()
        self.project_name = project_name
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir / "versions" / project_name
        
        # Create the directory structure
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Metadata file for the project
        self.metadata_file = self.storage_dir / "metadata.json"
        
        # Dictionary to store cached versions
        self.versions: Dict[str, ProjectVersion] = {}
        
        # Initialize or load project metadata
        self._init_project()
    
    def _init_project(self) -> None:
        """
        Initialize or load project metadata.
        """
        if self.metadata_file.exists():
            self._load_metadata()
        else:
            # Initialize empty project metadata
            self.metadata = {
                "name": self.project_name,
                "created_at": generate_timestamp(),
                "latest_version_id": None,
                "versions": []
            }
            self._save_metadata()
    
    def _load_metadata(self) -> None:
        """
        Load project metadata from disk.
        """
        with open(self.metadata_file, "r") as f:
            self.metadata = json.load(f)
    
    def _save_metadata(self) -> None:
        """
        Save project metadata to disk.
        """
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)
    
    def _get_version_path(self, version_id: str) -> Path:
        """
        Get the path to a version file.
        
        Args:
            version_id: ID of the version
            
        Returns:
            Path: Path to the version file
        """
        return self.storage_dir / f"{version_id}.json"
    
    def _load_version(self, version_id: str) -> ProjectVersion:
        """
        Load a version from disk.
        
        Args:
            version_id: ID of the version to load
            
        Returns:
            ProjectVersion: The loaded version
            
        Raises:
            FileNotFoundError: If the version doesn't exist
        """
        version_path = self._get_version_path(version_id)
        
        if not version_path.exists():
            raise FileNotFoundError(f"Version {version_id} not found")
        
        with open(version_path, "r") as f:
            version_data = json.load(f)
        
        return ProjectVersion.model_validate(version_data)
    
    def _save_version(self, version: ProjectVersion) -> None:
        """
        Save a version to disk.
        
        Args:
            version: The version to save
        """
        version_path = self._get_version_path(version.id)
        
        with open(version_path, "w") as f:
            json.dump(version.model_dump(), f, indent=2)
    
    def get_version(self, version_id: str) -> ProjectVersion:
        """
        Get a specific version.
        
        Args:
            version_id: ID of the version to get
            
        Returns:
            ProjectVersion: The requested version
            
        Raises:
            FileNotFoundError: If the version doesn't exist
        """
        # Check if the version is cached
        if version_id in self.versions:
            return self.versions[version_id]
        
        # Load the version from disk
        version = self._load_version(version_id)
        
        # Cache the version
        self.versions[version_id] = version
        
        return version
    
    def get_latest_version(self) -> Optional[ProjectVersion]:
        """
        Get the latest version of the project.
        
        Returns:
            Optional[ProjectVersion]: The latest version, or None if no versions exist
        """
        latest_id = self.metadata.get("latest_version_id")
        if latest_id:
            return self.get_version(latest_id)
        return None
    
    def list_versions(self) -> List[Dict]:
        """
        List all versions of the project with basic metadata.
        
        Returns:
            List[Dict]: List of version metadata
        """
        return self.metadata.get("versions", [])
    
    def create_version(
        self, 
        name: str,
        files: Dict[str, FileInfo],
        version_type: GameVersionType = GameVersionType.DEVELOPMENT,
        description: Optional[str] = None,
        is_milestone: bool = False,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = None
    ) -> ProjectVersion:
        """
        Create a new version of the project.
        
        Args:
            name: Name of the version
            files: Dictionary of file paths to file info
            version_type: Type of the version
            description: Description of the version
            is_milestone: Whether this version is a milestone
            tags: List of tags for this version
            parent_id: ID of the parent version
            
        Returns:
            ProjectVersion: The created version
        """
        # If parent_id is not provided, use the latest version
        if parent_id is None:
            latest = self.get_latest_version()
            parent_id = latest.id if latest else None
        
        # Create new version
        version = ProjectVersion(
            timestamp=generate_timestamp(),
            name=name,
            parent_id=parent_id,
            type=version_type,
            tags=tags or [],
            description=description,
            files=files,
            is_milestone=is_milestone
        )
        
        # Save the version
        self._save_version(version)
        
        # Update metadata
        version_meta = {
            "id": version.id,
            "name": version.name,
            "timestamp": version.timestamp,
            "type": version.type,
            "is_milestone": version.is_milestone,
            "parent_id": version.parent_id
        }
        
        self.metadata["versions"].append(version_meta)
        self.metadata["latest_version_id"] = version.id
        self._save_metadata()
        
        # Cache the version
        self.versions[version.id] = version
        
        return version
    
    def get_version_history(self, version_id: Optional[str] = None) -> List[ProjectVersion]:
        """
        Get the history of versions leading to the specified version.
        
        Args:
            version_id: ID of the version. If None, uses the latest version.
            
        Returns:
            List[ProjectVersion]: List of versions in the history
        """
        if version_id is None:
            latest = self.get_latest_version()
            if latest is None:
                return []
            version_id = latest.id
        
        history = []
        current_id = version_id
        
        # Walk backwards through the version history
        while current_id:
            try:
                version = self.get_version(current_id)
                history.append(version)
                current_id = version.parent_id
            except FileNotFoundError:
                break
        
        # Reverse to get chronological order
        history.reverse()
        
        return history
    
    def get_milestones(self) -> List[ProjectVersion]:
        """
        Get all milestone versions.
        
        Returns:
            List[ProjectVersion]: List of milestone versions
        """
        milestones = []
        
        for version_meta in self.metadata.get("versions", []):
            if version_meta.get("is_milestone", False):
                try:
                    version = self.get_version(version_meta["id"])
                    milestones.append(version)
                except FileNotFoundError:
                    continue
        
        return milestones
    
    def get_versions_by_tag(self, tag: str) -> List[ProjectVersion]:
        """
        Get versions with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List[ProjectVersion]: List of versions with the tag
        """
        result = []
        
        for version_meta in self.metadata.get("versions", []):
            try:
                version = self.get_version(version_meta["id"])
                if tag in version.tags:
                    result.append(version)
            except FileNotFoundError:
                continue
        
        return result
    
    def get_versions_by_type(self, version_type: GameVersionType) -> List[ProjectVersion]:
        """
        Get versions of a specific type.
        
        Args:
            version_type: Type to search for
            
        Returns:
            List[ProjectVersion]: List of versions of the specified type
        """
        result = []
        
        for version_meta in self.metadata.get("versions", []):
            if version_meta.get("type") == version_type:
                try:
                    version = self.get_version(version_meta["id"])
                    result.append(version)
                except FileNotFoundError:
                    continue
        
        return result
    
    def delete_version(self, version_id: str) -> bool:
        """
        Delete a version.
        
        Note: This does not delete any files or chunks associated with the version.
        
        Args:
            version_id: ID of the version to delete
            
        Returns:
            bool: True if the version was deleted, False otherwise
        """
        version_path = self._get_version_path(version_id)
        
        if not version_path.exists():
            return False
        
        # Remove from cache
        if version_id in self.versions:
            del self.versions[version_id]
        
        # Remove from metadata
        self.metadata["versions"] = [v for v in self.metadata["versions"] if v["id"] != version_id]
        
        # Update latest version if needed
        if self.metadata.get("latest_version_id") == version_id:
            if self.metadata["versions"]:
                # Sort by timestamp to find the latest
                self.metadata["versions"].sort(key=lambda v: v["timestamp"], reverse=True)
                self.metadata["latest_version_id"] = self.metadata["versions"][0]["id"]
            else:
                self.metadata["latest_version_id"] = None
        
        # Save metadata
        self._save_metadata()
        
        # Delete the version file
        os.remove(version_path)
        
        return True