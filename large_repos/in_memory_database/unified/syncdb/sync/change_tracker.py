"""
Change tracking system for efficient synchronization - integrated with common library.
"""
from typing import Dict, List, Any, Optional, Set, Tuple
import time
import json
from dataclasses import dataclass
import copy

# Import from common library
from common.core.version import VersionManager, Version
from common.core.serialization import Serializable, ExtendedJSONEncoder, ExtendedJSONDecoder
from common.utils.threading import ThreadSafeCache, atomic_operation


@dataclass
class ChangeRecord(Serializable):
    """Represents a single change to a record - extends common Serializable."""
    id: int  # Sequential ID for ordering changes
    table_name: str
    primary_key: Tuple  # Primary key values as a tuple
    operation: str  # "insert", "update", or "delete"
    timestamp: float  # Unix timestamp
    client_id: str  # ID of the client that made the change
    old_data: Optional[Dict[str, Any]]  # Previous state (None for inserts)
    new_data: Optional[Dict[str, Any]]  # New state (None for deletes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "id": self.id,
            "table_name": self.table_name,
            "primary_key": self.primary_key,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "client_id": self.client_id,
            "old_data": self.old_data,
            "new_data": self.new_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChangeRecord':
        """Create a ChangeRecord from a dictionary."""
        return cls(
            id=data["id"],
            table_name=data["table_name"],
            primary_key=tuple(data["primary_key"]),
            operation=data["operation"],
            timestamp=data["timestamp"],
            client_id=data["client_id"],
            old_data=data["old_data"],
            new_data=data["new_data"]
        )
    
    def to_version(self, entity_id: str) -> Version:
        """Convert ChangeRecord to common Version object."""
        from datetime import datetime
        return Version(
            id=str(self.id),
            value=self.to_dict(),
            version_number=self.id,
            timestamp=datetime.fromtimestamp(self.timestamp),
            created_by=self.client_id,
            metadata={
                'table_name': self.table_name,
                'operation': self.operation,
                'primary_key': str(self.primary_key)
            }
        )


class ChangeTracker:
    """
    Tracks changes to database records for efficient synchronization.
    Uses common VersionManager for underlying storage.
    """
    def __init__(self, max_history_size: int = 10000):
        self.changes: Dict[str, List[ChangeRecord]] = {}  # Table name -> changes
        self.max_history_size = max_history_size
        self.counters: Dict[str, int] = {}  # Table name -> next change ID
        
        # Use common library components
        self.version_manager = VersionManager(max_versions_per_item=max_history_size)
        self.cache = ThreadSafeCache(max_size=1000)  # Cache for frequently accessed changes
    
    @atomic_operation
    def record_change(self, 
                     table_name: str, 
                     primary_key: Tuple,
                     operation: str, 
                     old_data: Optional[Dict[str, Any]], 
                     new_data: Optional[Dict[str, Any]],
                     client_id: str) -> ChangeRecord:
        """
        Record a change to a database record with atomic operation.
        
        Args:
            table_name: Name of the table
            primary_key: Primary key values as a tuple
            operation: "insert", "update", or "delete"
            old_data: Previous state (None for inserts)
            new_data: New state (None for deletes)
            client_id: ID of the client that made the change
            
        Returns:
            The created ChangeRecord
        """
        # Initialize table changes if not already done
        if table_name not in self.changes:
            self.changes[table_name] = []
            self.counters[table_name] = 0
        
        # Get the next change ID for this table
        change_id = self.counters[table_name]
        self.counters[table_name] += 1
        
        # Create the change record
        change = ChangeRecord(
            id=change_id,
            table_name=table_name,
            primary_key=primary_key,
            operation=operation,
            timestamp=time.time(),
            client_id=client_id,
            old_data=copy.deepcopy(old_data) if old_data else None,
            new_data=copy.deepcopy(new_data) if new_data else None
        )
        
        # Add to the change log
        self.changes[table_name].append(change)
        
        # Also store in version manager for advanced versioning features
        entity_id = f"{table_name}:{str(primary_key)}"
        self.version_manager.add_version(
            entity_id=entity_id,
            item_name="change_record", 
            value=change.to_dict(),
            created_by=client_id,
            metadata={
                'operation': operation,
                'table_name': table_name
            }
        )
        
        # Prune history if necessary
        self._prune_history(table_name)
        
        return change
    
    def _prune_history(self, table_name: str) -> None:
        """
        Prune change history for a table if it exceeds max_history_size.
        """
        table_changes = self.changes.get(table_name, [])
        if len(table_changes) > self.max_history_size:
            # Keep only the most recent changes
            self.changes[table_name] = table_changes[-self.max_history_size:]
    
    def get_changes_since(self, 
                         table_name: str, 
                         since_id: int, 
                         exclude_client_id: Optional[str] = None) -> List[ChangeRecord]:
        """
        Get all changes to a table since a given change ID.
        
        Args:
            table_name: Name of the table
            since_id: Get changes with ID greater than this
            exclude_client_id: Optionally exclude changes made by this client
            
        Returns:
            List of changes since the given ID
        """
        table_changes = self.changes.get(table_name, [])
        
        # Filter changes by ID and optionally by client ID
        filtered_changes = [
            change for change in table_changes
            if change.id > since_id and (exclude_client_id is None or change.client_id != exclude_client_id)
        ]
        
        return filtered_changes
    
    def get_latest_change_id(self, table_name: str) -> int:
        """
        Get the ID of the latest change for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Latest change ID, or -1 if no changes exist
        """
        if table_name not in self.changes or not self.changes[table_name]:
            return -1
        
        return self.changes[table_name][-1].id
    
    def serialize_changes(self, changes: List[ChangeRecord]) -> str:
        """
        Serialize changes to JSON using common serialization.
        
        Args:
            changes: List of changes to serialize
            
        Returns:
            JSON string representation
        """
        change_dicts = [change.to_dict() for change in changes]
        return json.dumps(change_dicts, cls=ExtendedJSONEncoder)
    
    def deserialize_changes(self, json_str: str) -> List[ChangeRecord]:
        """
        Deserialize changes from JSON using common serialization.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            List of ChangeRecord objects
        """
        change_dicts = json.loads(json_str, cls=ExtendedJSONDecoder)
        return [ChangeRecord.from_dict(change_dict) for change_dict in change_dicts]


class VersionVector(Serializable):
    """
    Tracks the version of data across multiple clients using a vector clock.
    Used for detecting conflicts during synchronization.
    Extended from common Serializable.
    """
    def __init__(self, client_id: str, initial_value: int = 0):
        self.vector: Dict[str, int] = {client_id: initial_value}
        self.client_id = client_id
    
    def increment(self) -> None:
        """Increment the version for the current client."""
        self.vector[self.client_id] = self.vector.get(self.client_id, 0) + 1
    
    def update(self, other: 'VersionVector') -> None:
        """Merge with another version vector, taking the max value for each client."""
        for client_id, version in other.vector.items():
            self.vector[client_id] = max(self.vector.get(client_id, 0), version)
    
    def dominates(self, other: 'VersionVector') -> bool:
        """
        Check if this version vector dominates another.
        
        Returns True if this vector is strictly greater than or equal to the other
        in all dimensions, and strictly greater in at least one dimension.
        """
        strictly_greater = False
        
        # Check all client IDs in the other vector
        for client_id, other_version in other.vector.items():
            this_version = self.vector.get(client_id, 0)
            
            if this_version < other_version:
                return False
            
            if this_version > other_version:
                strictly_greater = True
        
        # Check if we have any client IDs not in the other vector
        for client_id, this_version in self.vector.items():
            if client_id not in other.vector and this_version > 0:
                strictly_greater = True
        
        return strictly_greater
    
    def concurrent_with(self, other: 'VersionVector') -> bool:
        """
        Check if this version vector is concurrent with another.
        
        Returns True if neither vector dominates the other, indicating
        that they represent concurrent modifications.
        """
        return not self.dominates(other) and not other.dominates(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            'vector': dict(self.vector),
            'client_id': self.client_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionVector':
        """Create a VersionVector from a dictionary."""
        if 'client_id' in data:
            # New format with client_id included
            vector = cls(data['client_id'], 0)
            vector.vector = dict(data['vector'])
            return vector
        else:
            # Legacy format - backward compatibility
            # Try to infer client_id from the first key
            client_id = next(iter(data.keys())) if data else 'unknown'
            vector = cls(client_id, 0)
            vector.vector = dict(data)
            return vector