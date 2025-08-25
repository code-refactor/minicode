"""
Version management for feature values.

This module provides a wrapper around the common library version manager
for feature-specific version operations while maintaining compatibility.
"""

import time
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from datetime import datetime

from common.core.version import VersionManager as CommonVersionManager


class Version:
    """
    Represents a specific version of a feature value.
    
    This class encapsulates a feature value with its version metadata,
    including timestamp, version number, and creation information.
    """
    
    def __init__(
        self,
        value: Any,
        version_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a version.
        
        Args:
            value: The feature value
            version_id: Optional unique identifier for this version
            timestamp: Optional creation timestamp (defaults to current time)
            created_by: Optional identifier of the creator
            description: Optional description of this version
            metadata: Optional additional metadata
        """
        self.value = value
        self.version_id = version_id or str(uuid.uuid4())
        self.timestamp = timestamp or time.time()
        self.created_by = created_by
        self.description = description
        self.metadata = metadata or {}
        
    @property
    def created_at(self) -> datetime:
        """Get the creation time as a datetime object."""
        # Use UTC timestamp to avoid timezone issues
        return datetime.utcfromtimestamp(self.timestamp).replace(microsecond=0)
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this version to a dictionary.
        
        Returns:
            Dictionary representation of this version
        """
        return {
            "version_id": self.version_id,
            "value": self.value,
            "timestamp": self.timestamp,
            "created_by": self.created_by,
            "description": self.description,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Version':
        """
        Create a Version from a dictionary.
        
        Args:
            data: Dictionary containing version data
            
        Returns:
            A new Version instance
        """
        return cls(
            value=data["value"],
            version_id=data["version_id"],
            timestamp=data["timestamp"],
            created_by=data.get("created_by"),
            description=data.get("description"),
            metadata=data.get("metadata", {})
        )
        
    def __eq__(self, other: object) -> bool:
        """Check if two versions are equal."""
        if not isinstance(other, Version):
            return False
        return self.version_id == other.version_id
        
    def __lt__(self, other: 'Version') -> bool:
        """Compare versions by timestamp."""
        return self.timestamp < other.timestamp
        
    def __repr__(self) -> str:
        """String representation of this version."""
        date_str = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"Version(id={self.version_id}, timestamp={date_str})"


class VersionManager:
    """
    Manages versioned feature values.
    
    This class wraps the common library VersionManager to provide
    feature-specific functionality while maintaining compatibility.
    """
    
    def __init__(self, max_versions_per_feature: Optional[int] = None):
        """
        Initialize a version manager.
        
        Args:
            max_versions_per_feature: Optional maximum number of versions to retain per feature
        """
        # Use common library version manager as backend
        self._common_version_manager = CommonVersionManager(max_versions_per_feature)
        
        # Optional limit on the number of versions to retain
        self._max_versions = max_versions_per_feature
        
        # Maintain _versions dict for backward compatibility with tests
        self._versions: Dict[str, Dict[str, List[Version]]] = {}
        self._current_versions: Dict[str, Dict[str, str]] = {}  # {entity_id: {feature_name: version_id}}
        
    def add_version(
        self,
        entity_id: str,
        feature_name: str,
        value: Any,
        version_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Version:
        """
        Add a new version of a feature.
        
        Args:
            entity_id: ID of the entity this feature belongs to
            feature_name: Name of the feature
            value: Value of the feature
            version_id: Optional unique identifier for this version
            timestamp: Optional creation timestamp
            created_by: Optional identifier of the creator
            description: Optional description of this version
            metadata: Optional additional metadata
            
        Returns:
            The created Version object
        """
        # Add enhanced metadata for feature-specific info
        enhanced_metadata = metadata or {}
        if description:
            enhanced_metadata['description'] = description
        
        # Use common version manager to add version
        common_version = self._common_version_manager.add_version(
            entity_id=entity_id,
            item_name=feature_name,
            value=value,
            created_by=created_by or "system",
            metadata=enhanced_metadata
        )
        
        # Create wrapper Version object with expected interface
        version = Version(
            value=value,
            version_id=common_version.id,
            timestamp=common_version.timestamp.timestamp(),
            created_by=common_version.created_by,
            description=description,
            metadata=metadata
        )
        
        # Maintain backward compatibility with _versions dict
        if entity_id not in self._versions:
            self._versions[entity_id] = {}
        if feature_name not in self._versions[entity_id]:
            self._versions[entity_id][feature_name] = []
        self._versions[entity_id][feature_name].append(version)
        
        # Prune old versions if needed
        if self._max_versions and len(self._versions[entity_id][feature_name]) > self._max_versions:
            self._versions[entity_id][feature_name] = self._versions[entity_id][feature_name][-self._max_versions:]
        
        # Update current version
        if entity_id not in self._current_versions:
            self._current_versions[entity_id] = {}
        self._current_versions[entity_id][feature_name] = version.version_id
        
        return version
    
    def get_version(
        self,
        entity_id: str,
        feature_name: str,
        version_id: Optional[str] = None,
        version_number: Optional[int] = None,
        timestamp: Optional[float] = None
    ) -> Optional[Version]:
        """
        Get a specific version of a feature.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            version_id: Optional specific version ID to retrieve
            version_number: Optional version number (0 is most recent, 1 is previous, etc.)
            timestamp: Optional timestamp to get the version at a specific time
            
        Returns:
            The Version object if found, None otherwise
            
        Note:
            If multiple identifiers are provided, version_id takes precedence,
            followed by version_number, then timestamp.
        """
        # Convert timestamp to datetime if provided
        timestamp_dt = None
        if timestamp is not None:
            timestamp_dt = datetime.fromtimestamp(timestamp)
        
        # Get version from common version manager
        common_version = self._common_version_manager.get_version(
            entity_id=entity_id,
            item_name=feature_name,
            version_id=version_id,
            version_number=version_number,
            timestamp=timestamp_dt
        )
        
        if common_version is None:
            return None
        
        # Convert back to feature version format
        description = common_version.metadata.get('description')
        return Version(
            value=common_version.value,
            version_id=common_version.id,
            timestamp=common_version.timestamp.timestamp(),
            created_by=common_version.created_by,
            description=description,
            metadata=common_version.metadata
        )
    
    def get_value(
        self,
        entity_id: str,
        feature_name: str,
        version_id: Optional[str] = None,
        version_number: Optional[int] = None,
        timestamp: Optional[float] = None,
        default: Any = None
    ) -> Any:
        """
        Get the value of a specific feature version.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            version_id: Optional specific version ID to retrieve
            version_number: Optional version number (0 is most recent, 1 is previous, etc.)
            timestamp: Optional timestamp to get the value at a specific time
            default: Value to return if the version is not found
            
        Returns:
            The feature value if found, default otherwise
        """
        version = self.get_version(
            entity_id=entity_id,
            feature_name=feature_name,
            version_id=version_id,
            version_number=version_number,
            timestamp=timestamp
        )
        
        return version.value if version is not None else default
    
    def get_current(
        self,
        entity_id: str,
        feature_name: str,
        default: Any = None
    ) -> Any:
        """
        Get the current value of a feature.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            default: Value to return if the feature is not found
            
        Returns:
            The current feature value if found, default otherwise
        """
        return self.get_value(entity_id, feature_name, default=default)
    
    def get_history(
        self,
        entity_id: str,
        feature_name: str,
        limit: Optional[int] = None,
        since_timestamp: Optional[float] = None,
        until_timestamp: Optional[float] = None
    ) -> List[Version]:
        """
        Get the version history of a feature.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            limit: Optional maximum number of versions to return
            since_timestamp: Optional filter for versions after this time
            until_timestamp: Optional filter for versions before this time
            
        Returns:
            List of Version objects, sorted by timestamp (most recent first)
        """
        # Convert timestamps to datetime objects
        since_timestamp_dt = None
        until_timestamp_dt = None
        if since_timestamp is not None:
            since_timestamp_dt = datetime.fromtimestamp(since_timestamp)
        if until_timestamp is not None:
            until_timestamp_dt = datetime.fromtimestamp(until_timestamp)
        
        # Get history from common version manager
        common_versions = self._common_version_manager.get_history(
            entity_id=entity_id,
            item_name=feature_name,
            limit=limit,
            since_timestamp=since_timestamp_dt,
            until_timestamp=until_timestamp_dt
        )
        
        # Convert back to feature version format
        versions = []
        for common_version in common_versions:
            description = common_version.metadata.get('description')
            version = Version(
                value=common_version.value,
                version_id=common_version.id,
                timestamp=common_version.timestamp.timestamp(),
                created_by=common_version.created_by,
                description=description,
                metadata=common_version.metadata
            )
            versions.append(version)
        
        return versions
    
    def get_versions_at(
        self,
        entity_id: str,
        feature_names: List[str],
        timestamp: float
    ) -> Dict[str, Version]:
        """
        Get versions of multiple features at a specific point in time.
        
        Args:
            entity_id: ID of the entity
            feature_names: List of feature names to retrieve
            timestamp: The point in time to retrieve versions for
            
        Returns:
            Dictionary of feature_name -> Version objects
        """
        result = {}
        for feature_name in feature_names:
            version = self.get_version(entity_id, feature_name, timestamp=timestamp)
            if version is not None:
                result[feature_name] = version
                
        return result
    
    def delete_history(
        self,
        entity_id: str,
        feature_name: Optional[str] = None
    ) -> int:
        """
        Delete version history for an entity or feature.
        
        Args:
            entity_id: ID of the entity
            feature_name: Optional feature name (if None, all features for the entity are deleted)
            
        Returns:
            Number of versions deleted
        """
        deleted = 0
        if feature_name is not None:
            # Delete a specific feature
            deleted = self._common_version_manager.delete_item_history(entity_id, feature_name)
            
            # Update local dicts for backward compatibility
            if entity_id in self._versions and feature_name in self._versions[entity_id]:
                del self._versions[entity_id][feature_name]
                if not self._versions[entity_id]:
                    del self._versions[entity_id]
            
            if entity_id in self._current_versions and feature_name in self._current_versions[entity_id]:
                del self._current_versions[entity_id][feature_name]
                if not self._current_versions[entity_id]:
                    del self._current_versions[entity_id]
        else:
            # Delete all features for the entity
            deleted = self._common_version_manager.delete_entity_history(entity_id)
            
            # Update local dicts for backward compatibility
            if entity_id in self._versions:
                del self._versions[entity_id]
            
            # Remove all current versions for this entity
            if entity_id in self._current_versions:
                del self._current_versions[entity_id]
        
        return deleted
    
    def get_entities(self) -> List[str]:
        """
        Get all entity IDs in the version manager.
        
        Returns:
            List of entity IDs
        """
        # Get all unique entity IDs from the common version manager
        stats = self._common_version_manager.get_stats()
        # We need to extract entity IDs from version keys
        entity_ids = set()
        for key in self._common_version_manager._versions.keys():
            entity_id, _ = key
            entity_ids.add(entity_id)
        return list(entity_ids)
    
    def get_features(self, entity_id: str) -> List[str]:
        """
        Get all feature names for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            List of feature names
        """
        # Get all feature names for the entity from the common version manager
        feature_names = set()
        for key in self._common_version_manager._versions.keys():
            eid, feature_name = key
            if eid == entity_id:
                feature_names.add(feature_name)
        return list(feature_names)
    
    def has_feature(self, entity_id: str, feature_name: str) -> bool:
        """
        Check if a feature exists for an entity.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            
        Returns:
            True if the feature exists, False otherwise
        """
        key = (entity_id, feature_name)
        return key in self._common_version_manager._versions