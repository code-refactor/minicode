"""
Milestone Management module for GameVault.

This module provides tools for marking, annotating, and preserving important
development milestones.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from gamevault.backup_engine.engine import BackupEngine
from gamevault.backup_engine.version_tracker import VersionTracker
from gamevault.config import get_config
from gamevault.models import GameVersionType, ProjectVersion
from gamevault.utils import generate_timestamp


class MilestoneManager:
    """
    Manager for game development milestones.
    
    This class provides functionality for marking, annotating, and preserving
    important development milestones.
    """
    
    def __init__(
        self,
        project_name: str,
        version_tracker: Optional[VersionTracker] = None,
        backup_engine: Optional[BackupEngine] = None,
        storage_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the milestone manager.
        
        Args:
            project_name: Name of the project
            version_tracker: Version tracker instance. If None, a new one will be created.
            backup_engine: Backup engine instance. If None, milestone creation will be limited.
            storage_dir: Directory where milestone data will be stored. If None, uses the default from config.
        """
        config = get_config()
        self.project_name = project_name
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir
        
        # Create or use provided components
        self.version_tracker = version_tracker or VersionTracker(project_name, self.storage_dir)
        self.backup_engine = backup_engine
        
        # Directory for milestone annotations
        self.milestones_dir = self.storage_dir / "milestones" / project_name
        os.makedirs(self.milestones_dir, exist_ok=True)
    
    def _get_milestone_path(self, milestone_id: str) -> Path:
        """
        Get the path to a milestone annotation file.
        
        Args:
            milestone_id: ID of the milestone
            
        Returns:
            Path: Path to the milestone annotation file
        """
        return self.milestones_dir / f"{milestone_id}.json"
    
    def create_milestone(
        self,
        name: str,
        version_type: GameVersionType,
        description: str,
        annotations: Dict[str, Any],
        tags: List[str],
        project_path: Optional[Union[str, Path]] = None,
        parent_id: Optional[str] = None
    ) -> ProjectVersion:
        """
        Create a new milestone.
        
        Args:
            name: Name of the milestone
            version_type: Type of the milestone
            description: Description of the milestone
            annotations: Additional annotations for the milestone
            tags: Tags for the milestone
            project_path: Path to the project directory. Required if backup_engine wasn't provided.
            parent_id: ID of the parent version. If None, uses the latest version.
            
        Returns:
            ProjectVersion: The created milestone version
            
        Raises:
            ValueError: If backup_engine wasn't provided and project_path is None
        """
        # Create a backup if backup_engine is available
        if self.backup_engine:
            version = self.backup_engine.create_backup(
                name=name,
                version_type=version_type,
                description=description,
                is_milestone=True,
                tags=tags
            )
        elif project_path:
            # Create a temporary backup engine
            temp_engine = BackupEngine(
                project_name=self.project_name,
                project_path=project_path,
                storage_dir=self.storage_dir
            )
            
            version = temp_engine.create_backup(
                name=name,
                version_type=version_type,
                description=description,
                is_milestone=True,
                tags=tags
            )
        else:
            raise ValueError("Either backup_engine must be provided or project_path must be specified")
        
        # Save additional annotations
        annotation_data = {
            "milestone_id": version.id,
            "name": name,
            "version_type": version_type,
            "description": description,
            "annotations": annotations,
            "tags": tags,
            "created_at": generate_timestamp(),
            "parent_id": parent_id or (version.parent_id if version else None)
        }
        
        milestone_path = self._get_milestone_path(version.id)
        with open(milestone_path, "w") as f:
            json.dump(annotation_data, f, indent=2)
        
        return version
    
    def get_milestone(self, milestone_id: str) -> Dict[str, Any]:
        """
        Get a milestone with its annotations.
        
        Args:
            milestone_id: ID of the milestone
            
        Returns:
            Dict[str, Any]: Milestone data with annotations
            
        Raises:
            FileNotFoundError: If the milestone doesn't exist
        """
        try:
            # Get the version
            version = self.version_tracker.get_version(milestone_id)
            
            # Get annotations
            milestone_path = self._get_milestone_path(milestone_id)
            if milestone_path.exists():
                with open(milestone_path, "r") as f:
                    annotations = json.load(f)
            else:
                annotations = {
                    "milestone_id": version.id,
                    "name": version.name,
                    "version_type": version.type,
                    "description": version.description,
                    "annotations": {},
                    "tags": version.tags,
                    "created_at": version.timestamp,
                    "parent_id": version.parent_id
                }
            
            # Combine data
            milestone_data = {
                **version.model_dump(),
                **annotations
            }
            
            return milestone_data
        
        except FileNotFoundError:
            # Check if annotation file exists even if version is missing
            milestone_path = self._get_milestone_path(milestone_id)
            if milestone_path.exists():
                with open(milestone_path, "r") as f:
                    return json.load(f)
            
            raise FileNotFoundError(f"Milestone {milestone_id} not found")
    
    def update_milestone_annotations(
        self,
        milestone_id: str,
        annotations: Dict[str, Any]
    ) -> bool:
        """
        Update annotations for a milestone.
        
        Args:
            milestone_id: ID of the milestone
            annotations: New or updated annotations
            
        Returns:
            bool: True if the milestone was updated, False if it doesn't exist
        """
        try:
            # Check if the milestone exists
            self.version_tracker.get_version(milestone_id)
            
            # Get existing annotations
            milestone_path = self._get_milestone_path(milestone_id)
            if milestone_path.exists():
                with open(milestone_path, "r") as f:
                    milestone_data = json.load(f)
            else:
                return False
            
            # Update annotations
            milestone_data["annotations"].update(annotations)
            
            # Save updated annotations
            with open(milestone_path, "w") as f:
                json.dump(milestone_data, f, indent=2)
            
            return True
        
        except FileNotFoundError:
            return False
    
    def list_milestones(
        self,
        version_type: Optional[GameVersionType] = None,
        tag: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all milestones with optional filtering.
        
        Args:
            version_type: Filter by version type
            tag: Filter by tag
            
        Returns:
            List[Dict[str, Any]]: List of milestone metadata
        """
        # Get all milestone versions
        all_milestones = self.version_tracker.get_milestones()
        
        # Filter by version type if specified
        if version_type:
            all_milestones = [m for m in all_milestones if m.type == version_type]
        
        # Filter by tag if specified
        if tag:
            all_milestones = [m for m in all_milestones if tag in m.tags]
        
        # Prepare result with annotations
        result = []
        for milestone in all_milestones:
            try:
                milestone_data = self.get_milestone(milestone.id)
                summary = {
                    "id": milestone.id,
                    "name": milestone.name,
                    "version_type": milestone.type,
                    "timestamp": milestone.timestamp,
                    "description": milestone.description,
                    "tags": milestone.tags,
                    "parent_id": milestone.parent_id,
                    "has_annotations": bool(milestone_data.get("annotations", {}))
                }
                result.append(summary)
            except FileNotFoundError:
                # Skip milestones with missing annotation files
                pass
        
        # Sort by timestamp (newest first)
        result.sort(key=lambda m: m["timestamp"], reverse=True)
        
        return result
    
    def restore_milestone(
        self,
        milestone_id: str,
        output_path: Union[str, Path],
        excluded_paths: Optional[List[str]] = None
    ) -> Path:
        """
        Restore a milestone to a directory.
        
        Args:
            milestone_id: ID of the milestone
            output_path: Path where the milestone should be restored
            excluded_paths: List of file paths to exclude from restoration
            
        Returns:
            Path: Path to the restored milestone
            
        Raises:
            ValueError: If backup_engine wasn't provided
            FileNotFoundError: If the milestone doesn't exist
        """
        if not self.backup_engine:
            raise ValueError("Backup engine required for milestone restoration")
        
        # Check if the milestone exists
        self.get_milestone(milestone_id)
        
        # Restore the version
        return self.backup_engine.restore_version(
            version_id=milestone_id,
            output_path=output_path,
            excluded_paths=excluded_paths
        )
    
    def compare_milestones(
        self,
        milestone_id1: str,
        milestone_id2: str
    ) -> Dict[str, Any]:
        """
        Compare two milestones.
        
        Args:
            milestone_id1: ID of the first milestone
            milestone_id2: ID of the second milestone
            
        Returns:
            Dict[str, Any]: Comparison results
            
        Raises:
            ValueError: If backup_engine wasn't provided
            FileNotFoundError: If either milestone doesn't exist
        """
        if not self.backup_engine:
            raise ValueError("Backup engine required for milestone comparison")
        
        # Get the milestones
        milestone1 = self.get_milestone(milestone_id1)
        milestone2 = self.get_milestone(milestone_id2)
        
        # Get file differences
        diff = self.backup_engine.get_version_diff(milestone_id1, milestone_id2)
        
        # Categorize changes
        added = [path for path, change_type in diff.items() if change_type == "added"]
        modified = [path for path, change_type in diff.items() if change_type == "modified"]
        deleted = [path for path, change_type in diff.items() if change_type == "deleted"]
        unchanged = [path for path, change_type in diff.items() if change_type == "unchanged"]
        
        # Compare annotations
        annotations1 = milestone1.get("annotations", {})
        annotations2 = milestone2.get("annotations", {})
        
        annotation_changes = {
            "added": [],
            "modified": [],
            "removed": []
        }
        
        for key in annotations2:
            if key not in annotations1:
                annotation_changes["added"].append(key)
            elif annotations1[key] != annotations2[key]:
                annotation_changes["modified"].append(key)
        
        for key in annotations1:
            if key not in annotations2:
                annotation_changes["removed"].append(key)
        
        # Compare tags
        tags1 = set(milestone1.get("tags", []))
        tags2 = set(milestone2.get("tags", []))
        
        return {
            "milestone1": {
                "id": milestone_id1,
                "name": milestone1.get("name"),
                "version_type": milestone1.get("version_type"),
                "timestamp": milestone1.get("timestamp")
            },
            "milestone2": {
                "id": milestone_id2,
                "name": milestone2.get("name"),
                "version_type": milestone2.get("version_type"),
                "timestamp": milestone2.get("timestamp")
            },
            "file_changes": {
                "added": added,
                "modified": modified,
                "deleted": deleted,
                "unchanged": len(unchanged),
                "total_changes": len(added) + len(modified) + len(deleted)
            },
            "annotation_changes": annotation_changes,
            "tag_changes": {
                "added": list(tags2 - tags1),
                "removed": list(tags1 - tags2),
                "common": list(tags1 & tags2)
            },
            "time_between": abs(milestone2.get("timestamp", 0) - milestone1.get("timestamp", 0))
        }
    
    def delete_milestone(self, milestone_id: str) -> bool:
        """
        Delete a milestone.
        
        This does not delete the actual version, only the milestone annotation.
        
        Args:
            milestone_id: ID of the milestone
            
        Returns:
            bool: True if the milestone was deleted, False if it doesn't exist
        """
        milestone_path = self._get_milestone_path(milestone_id)
        
        if not milestone_path.exists():
            return False
        
        # Delete the annotation file
        os.remove(milestone_path)
        
        # Update the version to mark it as not a milestone
        try:
            version = self.version_tracker.get_version(milestone_id)
            version.is_milestone = False
            self.version_tracker._save_version(version)
        except FileNotFoundError:
            # Version was already deleted, just remove the annotation
            pass
        
        return True
    
    def get_milestone_timeline(self) -> List[Dict[str, Any]]:
        """
        Get a timeline of milestones.
        
        Returns:
            List[Dict[str, Any]]: Milestones in chronological order
        """
        milestones = self.list_milestones()
        
        # Sort by timestamp (oldest first)
        milestones.sort(key=lambda m: m["timestamp"])
        
        # Group by version type
        timeline = []
        for version_type in GameVersionType:
            type_milestones = [m for m in milestones if m["version_type"] == version_type]
            if type_milestones:
                timeline.append({
                    "version_type": version_type,
                    "milestones": type_milestones,
                    "count": len(type_milestones),
                    "first": type_milestones[0]["timestamp"],
                    "last": type_milestones[-1]["timestamp"]
                })
        
        return timeline