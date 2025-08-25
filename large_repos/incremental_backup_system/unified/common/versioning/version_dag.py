"""Directed Acyclic Graph for version management."""

from typing import Dict, List, Set, Optional, Tuple
from collections import deque
from ..models.version import Version


class VersionDAG:
    """Directed acyclic graph for version relationships."""
    
    def __init__(self):
        """Initialize the version DAG."""
        self._versions: Dict[str, Version] = {}
        self._children: Dict[str, Set[str]] = {}  # parent_id -> set of child_ids
        self._roots: Set[str] = set()  # Version IDs with no parents
    
    def add_version(self, version: Version) -> None:
        """
        Add a version to the DAG.
        
        Args:
            version: Version to add
        
        Raises:
            ValueError: If version would create a cycle
        """
        # Check for cycles
        if version.parent_id and self._would_create_cycle(version.id, version.parent_id):
            raise ValueError(f"Adding version {version.id} would create a cycle")
        
        # Add version
        self._versions[version.id] = version
        
        # Update parent-child relationships
        if version.parent_id:
            if version.parent_id not in self._children:
                self._children[version.parent_id] = set()
            self._children[version.parent_id].add(version.id)
        else:
            self._roots.add(version.id)
        
        # Initialize children set for new version
        if version.id not in self._children:
            self._children[version.id] = set()
    
    def get_version(self, version_id: str) -> Optional[Version]:
        """
        Get a version by ID.
        
        Args:
            version_id: Version ID
        
        Returns:
            Version or None if not found
        """
        return self._versions.get(version_id)
    
    def get_lineage(self, version_id: str) -> List[Version]:
        """
        Get the lineage (path from root to version).
        
        Args:
            version_id: Version ID
        
        Returns:
            List of versions from root to specified version
        """
        if version_id not in self._versions:
            return []
        
        lineage = []
        current_id = version_id
        
        # Walk backwards to root
        while current_id:
            version = self._versions[current_id]
            lineage.append(version)
            current_id = version.parent_id
        
        # Reverse to get root-to-version order
        return list(reversed(lineage))
    
    def get_children(self, version_id: str) -> List[Version]:
        """
        Get direct children of a version.
        
        Args:
            version_id: Version ID
        
        Returns:
            List of child versions
        """
        child_ids = self._children.get(version_id, set())
        return [self._versions[child_id] for child_id in child_ids]
    
    def get_descendants(self, version_id: str) -> List[Version]:
        """
        Get all descendants of a version.
        
        Args:
            version_id: Version ID
        
        Returns:
            List of all descendant versions
        """
        descendants = []
        queue = deque([version_id])
        visited = set()
        
        while queue:
            current_id = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)
            
            for child_id in self._children.get(current_id, set()):
                if child_id not in visited:
                    descendants.append(self._versions[child_id])
                    queue.append(child_id)
        
        return descendants
    
    def find_common_ancestor(self, version_id1: str, version_id2: str) -> Optional[Version]:
        """
        Find the common ancestor of two versions.
        
        Args:
            version_id1: First version ID
            version_id2: Second version ID
        
        Returns:
            Common ancestor version or None
        """
        lineage1 = self.get_lineage(version_id1)
        lineage2 = self.get_lineage(version_id2)
        
        if not lineage1 or not lineage2:
            return None
        
        # Find last common version
        common_ancestor = None
        for v1, v2 in zip(lineage1, lineage2):
            if v1.id == v2.id:
                common_ancestor = v1
            else:
                break
        
        return common_ancestor
    
    def get_branches(self) -> Dict[str, List[Version]]:
        """
        Get all branches (paths from roots to leaves).
        
        Returns:
            Dictionary mapping branch names to version lists
        """
        branches = {}
        leaves = self._find_leaves()
        
        for i, leaf_id in enumerate(leaves):
            branch_name = f"branch_{i}"
            branches[branch_name] = self.get_lineage(leaf_id)
        
        return branches
    
    def get_roots(self) -> List[Version]:
        """
        Get all root versions (versions with no parents).
        
        Returns:
            List of root versions
        """
        return [self._versions[root_id] for root_id in self._roots]
    
    def get_leaves(self) -> List[Version]:
        """
        Get all leaf versions (versions with no children).
        
        Returns:
            List of leaf versions
        """
        leaf_ids = self._find_leaves()
        return [self._versions[leaf_id] for leaf_id in leaf_ids]
    
    def _find_leaves(self) -> Set[str]:
        """Find all leaf version IDs."""
        leaves = set()
        for version_id in self._versions:
            if not self._children[version_id]:
                leaves.add(version_id)
        return leaves
    
    def _would_create_cycle(self, new_id: str, parent_id: str) -> bool:
        """
        Check if adding a version would create a cycle.
        
        Args:
            new_id: New version ID
            parent_id: Parent version ID
        
        Returns:
            True if it would create a cycle
        """
        # If parent doesn't exist yet, can't create cycle
        if parent_id not in self._versions:
            return False
        
        # Check if new_id is an ancestor of parent_id
        current = parent_id
        while current:
            if current == new_id:
                return True
            version = self._versions.get(current)
            current = version.parent_id if version else None
        
        return False
    
    def to_dict(self) -> Dict[str, any]:
        """
        Convert DAG to dictionary representation.
        
        Returns:
            Dictionary with DAG structure
        """
        return {
            'versions': {vid: v.to_dict() for vid, v in self._versions.items()},
            'children': {pid: list(children) for pid, children in self._children.items()},
            'roots': list(self._roots)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> 'VersionDAG':
        """
        Create DAG from dictionary representation.
        
        Args:
            data: Dictionary with DAG structure
        
        Returns:
            VersionDAG instance
        """
        dag = cls()
        
        # Recreate versions
        for version_data in data['versions'].values():
            version = Version(**version_data)
            dag._versions[version.id] = version
        
        # Recreate relationships
        dag._children = {pid: set(children) for pid, children in data['children'].items()}
        dag._roots = set(data['roots'])
        
        return dag