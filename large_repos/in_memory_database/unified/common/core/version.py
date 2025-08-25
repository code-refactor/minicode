"""Version management system for the unified library."""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from threading import RLock
import json
import uuid


@dataclass
class Version:
    """Represents a versioned item."""
    id: str
    value: Any
    version_number: int
    timestamp: datetime
    created_by: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_version_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary."""
        return {
            'id': self.id,
            'value': self.value,
            'version_number': self.version_number,
            'timestamp': self.timestamp.isoformat(),
            'created_by': self.created_by,
            'metadata': self.metadata,
            'parent_version_id': self.parent_version_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Version':
        """Create version from dictionary."""
        return cls(
            id=data['id'],
            value=data['value'],
            version_number=data['version_number'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            created_by=data['created_by'],
            metadata=data.get('metadata', {}),
            parent_version_id=data.get('parent_version_id')
        )


class VersionManager:
    """Manages version history for entities and items."""
    
    def __init__(self, max_versions_per_item: Optional[int] = None):
        """Initialize version manager.
        
        Args:
            max_versions_per_item: Maximum versions to keep per item (None = unlimited)
        """
        self._versions: Dict[Tuple[str, str], List[Version]] = {}
        self._version_by_id: Dict[str, Version] = {}
        self._latest_versions: Dict[Tuple[str, str], Version] = {}
        self._lock = RLock()
        self.max_versions_per_item = max_versions_per_item
    
    def add_version(self, entity_id: str, item_name: str, value: Any,
                   created_by: str = "system",
                   metadata: Optional[Dict[str, Any]] = None,
                   parent_version_id: Optional[str] = None) -> Version:
        """Add a new version for an entity's item.
        
        Args:
            entity_id: ID of the entity
            item_name: Name of the item being versioned
            value: The value to version
            created_by: Creator of this version
            metadata: Optional metadata for the version
            parent_version_id: Optional parent version ID for lineage
        
        Returns:
            The created Version object
        """
        with self._lock:
            key = (entity_id, item_name)
            
            # Get current version number
            if key in self._versions:
                version_number = len(self._versions[key]) + 1
            else:
                version_number = 1
                self._versions[key] = []
            
            # Create new version
            version = Version(
                id=str(uuid.uuid4()),
                value=value,
                version_number=version_number,
                timestamp=datetime.now(),
                created_by=created_by,
                metadata=metadata or {},
                parent_version_id=parent_version_id
            )
            
            # Store version
            self._versions[key].append(version)
            self._version_by_id[version.id] = version
            self._latest_versions[key] = version
            
            # Prune old versions if needed
            if self.max_versions_per_item and len(self._versions[key]) > self.max_versions_per_item:
                self._prune_oldest(key)
            
            return version
    
    def get_version(self, entity_id: str, item_name: str,
                   version_id: Optional[str] = None,
                   version_number: Optional[int] = None,
                   timestamp: Optional[datetime] = None) -> Optional[Version]:
        """Get a specific version of an entity's item.
        
        Args:
            entity_id: ID of the entity
            item_name: Name of the item
            version_id: Specific version ID to retrieve
            version_number: Specific version number to retrieve
            timestamp: Get version at or before this timestamp
        
        Returns:
            The requested Version or None if not found
        """
        with self._lock:
            # Get by version ID
            if version_id:
                return self._version_by_id.get(version_id)
            
            key = (entity_id, item_name)
            
            if key not in self._versions:
                return None
            
            versions = self._versions[key]
            
            # Get by version number
            if version_number is not None:
                for v in versions:
                    if v.version_number == version_number:
                        return v
                return None
            
            # Get by timestamp
            if timestamp:
                # Find the latest version at or before timestamp
                valid_versions = [v for v in versions if v.timestamp <= timestamp]
                if valid_versions:
                    return max(valid_versions, key=lambda v: v.timestamp)
                return None
            
            # Get latest version
            return self._latest_versions.get(key)
    
    def get_latest(self, entity_id: str, item_name: str) -> Optional[Version]:
        """Get the latest version of an entity's item.
        
        Args:
            entity_id: ID of the entity
            item_name: Name of the item
        
        Returns:
            The latest Version or None if not found
        """
        with self._lock:
            key = (entity_id, item_name)
            return self._latest_versions.get(key)
    
    def get_history(self, entity_id: str, item_name: str,
                   limit: Optional[int] = None,
                   since_timestamp: Optional[datetime] = None,
                   until_timestamp: Optional[datetime] = None) -> List[Version]:
        """Get version history for an entity's item.
        
        Args:
            entity_id: ID of the entity
            item_name: Name of the item
            limit: Maximum number of versions to return
            since_timestamp: Only return versions after this timestamp
            until_timestamp: Only return versions before this timestamp
        
        Returns:
            List of Version objects, newest first
        """
        with self._lock:
            key = (entity_id, item_name)
            
            if key not in self._versions:
                return []
            
            versions = self._versions[key].copy()
            
            # Apply timestamp filters
            if since_timestamp:
                versions = [v for v in versions if v.timestamp > since_timestamp]
            
            if until_timestamp:
                versions = [v for v in versions if v.timestamp <= until_timestamp]
            
            # Sort newest first
            versions.sort(key=lambda v: v.timestamp, reverse=True)
            
            # Apply limit
            if limit:
                versions = versions[:limit]
            
            return versions
    
    def get_lineage(self, version_id: str, max_depth: Optional[int] = None) -> List[Version]:
        """Get the lineage (parent chain) of a version.
        
        Args:
            version_id: ID of the version to trace
            max_depth: Maximum depth to trace (None = unlimited)
        
        Returns:
            List of Version objects from oldest ancestor to the specified version
        """
        with self._lock:
            lineage = []
            current_id = version_id
            depth = 0
            
            while current_id and (max_depth is None or depth < max_depth):
                version = self._version_by_id.get(current_id)
                if not version:
                    break
                
                lineage.append(version)
                current_id = version.parent_version_id
                depth += 1
            
            # Return oldest to newest
            return list(reversed(lineage))
    
    def prune_history(self, max_versions: int) -> int:
        """Prune old versions across all items.
        
        Args:
            max_versions: Maximum versions to keep per item
        
        Returns:
            Number of versions pruned
        """
        with self._lock:
            total_pruned = 0
            
            for key in list(self._versions.keys()):
                versions = self._versions[key]
                
                if len(versions) > max_versions:
                    # Keep the newest versions
                    versions.sort(key=lambda v: v.timestamp)
                    to_remove = versions[:-max_versions]
                    
                    for version in to_remove:
                        del self._version_by_id[version.id]
                        total_pruned += 1
                    
                    self._versions[key] = versions[-max_versions:]
            
            return total_pruned
    
    def delete_entity_history(self, entity_id: str) -> int:
        """Delete all version history for an entity.
        
        Args:
            entity_id: ID of the entity
        
        Returns:
            Number of versions deleted
        """
        with self._lock:
            deleted = 0
            keys_to_delete = []
            
            for key in self._versions:
                if key[0] == entity_id:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                versions = self._versions[key]
                for version in versions:
                    del self._version_by_id[version.id]
                    deleted += 1
                
                del self._versions[key]
                self._latest_versions.pop(key, None)
            
            return deleted
    
    def delete_item_history(self, entity_id: str, item_name: str) -> int:
        """Delete all version history for a specific item.
        
        Args:
            entity_id: ID of the entity
            item_name: Name of the item
        
        Returns:
            Number of versions deleted
        """
        with self._lock:
            key = (entity_id, item_name)
            
            if key not in self._versions:
                return 0
            
            versions = self._versions[key]
            for version in versions:
                del self._version_by_id[version.id]
            
            deleted = len(versions)
            del self._versions[key]
            self._latest_versions.pop(key, None)
            
            return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about version storage.
        
        Returns:
            Dictionary with version statistics
        """
        with self._lock:
            total_versions = sum(len(v) for v in self._versions.values())
            
            return {
                'total_entities': len(set(k[0] for k in self._versions.keys())),
                'total_items': len(self._versions),
                'total_versions': total_versions,
                'average_versions_per_item': total_versions / len(self._versions) if self._versions else 0,
                'max_versions_per_item': self.max_versions_per_item
            }
    
    def _prune_oldest(self, key: Tuple[str, str]) -> None:
        """Prune the oldest version for a specific item."""
        versions = self._versions[key]
        if not versions:
            return
        
        # Sort by timestamp and remove oldest
        versions.sort(key=lambda v: v.timestamp)
        oldest = versions.pop(0)
        
        # Remove from ID index
        del self._version_by_id[oldest.id]
        
        # Update version numbers
        for i, v in enumerate(versions):
            v.version_number = i + 1