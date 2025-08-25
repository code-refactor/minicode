"""Version manager implementation."""

import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..core.interfaces import VersionManager
from ..models.version import Version
from .version_dag import VersionDAG
from ..utils.time_utils import get_timestamp
from ..utils.serialization import save_json, load_json


class SimpleVersionManager(VersionManager):
    """Simple implementation of version management."""
    
    def __init__(self, metadata_path: Path):
        """
        Initialize version manager.
        
        Args:
            metadata_path: Path for storing version metadata
        """
        self.metadata_path = Path(metadata_path)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        self.dag_file = self.metadata_path / "version_dag.json"
        
        # Load or create DAG
        if self.dag_file.exists():
            dag_data = load_json(self.dag_file)
            self.dag = VersionDAG.from_dict(dag_data)
        else:
            self.dag = VersionDAG()
    
    def create_version(self, snapshot_id: str, parent_id: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new version.
        
        Args:
            snapshot_id: Associated snapshot ID
            parent_id: Optional parent version ID
            metadata: Optional metadata
        
        Returns:
            Created version ID
        """
        version_id = str(uuid.uuid4())
        timestamp = get_timestamp()
        
        version = Version(
            id=version_id,
            timestamp=timestamp,
            parent_id=parent_id,
            snapshot_id=snapshot_id,
            metadata=metadata or {}
        )
        
        # Add to DAG
        self.dag.add_version(version)
        
        # Save DAG
        self._save_dag()
        
        return version_id
    
    def get_version(self, version_id: str) -> Dict[str, Any]:
        """
        Get version information.
        
        Args:
            version_id: Version ID
        
        Returns:
            Version information as dictionary
        
        Raises:
            KeyError: If version not found
        """
        version = self.dag.get_version(version_id)
        if not version:
            raise KeyError(f"Version {version_id} not found")
        
        return version.to_dict()
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """
        List all versions.
        
        Returns:
            List of version dictionaries
        """
        versions = []
        dag_dict = self.dag.to_dict()
        
        for version_data in dag_dict['versions'].values():
            versions.append(version_data)
        
        # Sort by timestamp
        return sorted(versions, key=lambda v: v['timestamp'])
    
    def get_version_history(self, version_id: str) -> List[Dict[str, Any]]:
        """
        Get the history/lineage of a version.
        
        Args:
            version_id: Version ID
        
        Returns:
            List of version dictionaries from root to specified version
        """
        lineage = self.dag.get_lineage(version_id)
        return [v.to_dict() for v in lineage]
    
    def tag_version(self, version_id: str, tag: str) -> None:
        """
        Add a tag to a version.
        
        Args:
            version_id: Version ID
            tag: Tag to add
        
        Raises:
            KeyError: If version not found
        """
        version = self.dag.get_version(version_id)
        if not version:
            raise KeyError(f"Version {version_id} not found")
        
        version.add_tag(tag)
        self._save_dag()
    
    def untag_version(self, version_id: str, tag: str) -> None:
        """
        Remove a tag from a version.
        
        Args:
            version_id: Version ID
            tag: Tag to remove
        """
        version = self.dag.get_version(version_id)
        if version:
            version.remove_tag(tag)
            self._save_dag()
    
    def get_versions_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Get all versions with a specific tag.
        
        Args:
            tag: Tag to search for
        
        Returns:
            List of version dictionaries
        """
        tagged_versions = []
        
        for version in self.dag._versions.values():
            if version.has_tag(tag):
                tagged_versions.append(version.to_dict())
        
        return sorted(tagged_versions, key=lambda v: v['timestamp'])
    
    def get_branches(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all branches in the version tree.
        
        Returns:
            Dictionary mapping branch names to version lists
        """
        branches = self.dag.get_branches()
        return {
            name: [v.to_dict() for v in versions]
            for name, versions in branches.items()
        }
    
    def find_common_ancestor(self, version_id1: str, version_id2: str) -> Optional[Dict[str, Any]]:
        """
        Find the common ancestor of two versions.
        
        Args:
            version_id1: First version ID
            version_id2: Second version ID
        
        Returns:
            Common ancestor version dictionary or None
        """
        ancestor = self.dag.find_common_ancestor(version_id1, version_id2)
        return ancestor.to_dict() if ancestor else None
    
    def _save_dag(self) -> None:
        """Save DAG to disk."""
        dag_data = self.dag.to_dict()
        save_json(dag_data, self.dag_file)