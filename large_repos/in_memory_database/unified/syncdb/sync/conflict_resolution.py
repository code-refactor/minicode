"""
Conflict resolution strategies for handling concurrent modifications.
Integrated with common library serialization.
"""
from typing import Dict, List, Any, Optional, Callable, Tuple, Protocol
import copy
import time
import json
from dataclasses import dataclass, field

# Import from common library
from common.core.serialization import Serializable, ExtendedJSONEncoder, ExtendedJSONDecoder
from common.utils.threading import ThreadSafeCache, atomic_operation
from common.utils.validation import ValidationError

from .change_tracker import ChangeRecord


class ConflictResolver(Protocol):
    """Protocol defining the interface for conflict resolvers."""
    def resolve(self, 
               table_name: str, 
               client_change: ChangeRecord, 
               server_record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolve a conflict between client and server.
        
        Args:
            table_name: Name of the table
            client_change: Change from the client
            server_record: Current record on the server
            
        Returns:
            Resolved record, or None to reject the client change
        """
        ...


@dataclass
class ConflictMetadata(Serializable):
    """Metadata about a conflict and its resolution - extends common Serializable."""
    table_name: str
    primary_key: Tuple
    conflict_time: float
    client_id: str
    client_change: Dict[str, Any]
    server_record: Optional[Dict[str, Any]]
    resolution: Optional[Dict[str, Any]]
    resolution_strategy: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization."""
        return {
            "table_name": self.table_name,
            "primary_key": self.primary_key,
            "conflict_time": self.conflict_time,
            "client_id": self.client_id,
            "client_change": self.client_change,
            "server_record": self.server_record,
            "resolution": self.resolution,
            "resolution_strategy": self.resolution_strategy
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConflictMetadata':
        """Create a ConflictMetadata from a dictionary."""
        return cls(
            table_name=data["table_name"],
            primary_key=tuple(data["primary_key"]),
            conflict_time=data["conflict_time"],
            client_id=data["client_id"],
            client_change=data["client_change"],
            server_record=data["server_record"],
            resolution=data["resolution"],
            resolution_strategy=data["resolution_strategy"]
        )


class ConflictAuditLog:
    """
    Logs and provides access to conflict resolution history for auditability.
    Uses common library threading and serialization.
    """
    def __init__(self, max_history_size: int = 1000):
        self.conflicts: List[ConflictMetadata] = []
        self.max_history_size = max_history_size
        # Use common library components
        self.conflict_cache = ThreadSafeCache(max_size=100)  # Cache recent conflicts
    
@atomic_operation
    def log_conflict(self, metadata: ConflictMetadata) -> None:
        """Log a conflict resolution with thread safety."""
        self.conflicts.append(metadata)
        self._prune_history()
        
        # Cache recent conflict for quick access
        cache_key = f"{metadata.table_name}:{metadata.primary_key}"
        self.conflict_cache.put(cache_key, metadata)
    
    def _prune_history(self) -> None:
        """Prune history if it exceeds max_history_size."""
        if len(self.conflicts) > self.max_history_size:
            self.conflicts = self.conflicts[-self.max_history_size:]
    
    def get_conflicts_for_table(self, table_name: str) -> List[ConflictMetadata]:
        """Get all conflicts for a table."""
        return [c for c in self.conflicts if c.table_name == table_name]
    
    def get_conflicts_for_record(self, 
                               table_name: str, 
                               primary_key: Tuple) -> List[ConflictMetadata]:
        """Get all conflicts for a specific record."""
        return [
            c for c in self.conflicts 
            if c.table_name == table_name and c.primary_key == primary_key
        ]
    
    def get_conflicts_for_client(self, client_id: str) -> List[ConflictMetadata]:
        """Get all conflicts involving a specific client."""
        return [c for c in self.conflicts if c.client_id == client_id]
    
    def export_to_json(self) -> str:
        """Export the conflict history to JSON using extended serialization."""
        data = [c.to_dict() for c in self.conflicts]
        return json.dumps(data, cls=ExtendedJSONEncoder)
    
    def import_from_json(self, json_str: str) -> None:
        """Import conflict history from JSON using extended serialization."""
        data = json.loads(json_str, cls=ExtendedJSONDecoder)
        self.conflicts = [ConflictMetadata.from_dict(c) for c in data]
        self._prune_history()


class LastWriteWinsResolver(ConflictResolver):
    """
    Resolves conflicts by choosing the most recent change.
    """
    def resolve(self, 
               table_name: str, 
               client_change: ChangeRecord, 
               server_record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolve a conflict using last-write-wins strategy.
        
        Args:
            table_name: Name of the table
            client_change: Change from the client
            server_record: Current record on the server
            
        Returns:
            Resolved record, or None to reject the client change
        """
        # If the server record doesn't exist, use the client change
        if server_record is None:
            return client_change.new_data
        
        # If the client is trying to delete but server has newer record, keep server record
        if client_change.operation == "delete":
            # In a real implementation, we would compare timestamps
            # For simplicity, we'll assume server always wins in this case
            return server_record
        
        # Compare timestamps
        # In a real implementation, we would use something like vector clocks
        # For simplicity, assume the client change is newer
        if client_change.timestamp > time.time() - 60:  # Within last minute
            return client_change.new_data
        else:
            return server_record


class ServerWinsResolver(ConflictResolver):
    """
    Resolves conflicts by always choosing the server version.
    """
    def resolve(self, 
               table_name: str, 
               client_change: ChangeRecord, 
               server_record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolve a conflict by always choosing the server version.
        
        Args:
            table_name: Name of the table
            client_change: Change from the client
            server_record: Current record on the server
            
        Returns:
            Resolved record, or None to reject the client change
        """
        # If the server record doesn't exist, use the client change
        if server_record is None:
            return client_change.new_data
        
        # Otherwise, server always wins
        return server_record


class ClientWinsResolver(ConflictResolver):
    """
    Resolves conflicts by always choosing the client version.
    """
    def resolve(self, 
               table_name: str, 
               client_change: ChangeRecord, 
               server_record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolve a conflict by always choosing the client version.
        
        Args:
            table_name: Name of the table
            client_change: Change from the client
            server_record: Current record on the server
            
        Returns:
            Resolved record, or None to reject the client change
        """
        # Choose the client change
        if client_change.operation == "delete":
            return None  # No record (delete)
        else:
            return client_change.new_data


class MergeFieldsResolver(ConflictResolver):
    """
    Resolves conflicts by merging fields from client and server.
    """
    def __init__(self, field_priorities: Dict[str, List[str]]):
        """
        Initialize with field priorities.
        
        Args:
            field_priorities: Dict mapping table names to lists of fields.
                             Fields earlier in the list are prioritized from client,
                             fields not in the list use server values.
        """
        self.field_priorities = field_priorities
    
    def resolve(self, 
               table_name: str, 
               client_change: ChangeRecord, 
               server_record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolve a conflict by merging fields based on priorities.
        
        Args:
            table_name: Name of the table
            client_change: Change from the client
            server_record: Current record on the server
            
        Returns:
            Resolved record, or None to reject the client change
        """
        # If the server record doesn't exist, use the client change
        if server_record is None:
            return client_change.new_data
        
        # If the client is trying to delete, delete wins
        if client_change.operation == "delete":
            return None
        
        # If the client has new data, merge it with the server record
        if client_change.new_data:
            # Start with a copy of the server record
            result = copy.deepcopy(server_record)
            
            # Get the priority fields for this table
            priority_fields = self.field_priorities.get(table_name, [])
            
            # Update fields based on priorities
            for field in priority_fields:
                if field in client_change.new_data:
                    result[field] = client_change.new_data[field]
            
            return result
        
        # If all else fails, use the server record
        return server_record


class CustomMergeResolver(ConflictResolver):
    """
    Resolves conflicts using custom merge functions for specific tables.
    """
    def __init__(self, merge_functions: Dict[str, Callable]):
        """
        Initialize with custom merge functions.
        
        Args:
            merge_functions: Dict mapping table names to merge functions.
                           Each function should take (client_change, server_record)
                           and return the resolved record.
        """
        self.merge_functions = merge_functions
    
    def resolve(self, 
               table_name: str, 
               client_change: ChangeRecord, 
               server_record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolve a conflict using a custom merge function.
        
        Args:
            table_name: Name of the table
            client_change: Change from the client
            server_record: Current record on the server
            
        Returns:
            Resolved record, or None to reject the client change
        """
        # Use the custom merge function for this table if available
        merge_func = self.merge_functions.get(table_name)
        if merge_func:
            return merge_func(client_change, server_record)
        
        # Fall back to last-write-wins
        return LastWriteWinsResolver().resolve(table_name, client_change, server_record)


class ConflictManager:
    """
    Manages conflict resolution and logging for the database.
    Uses common library components for thread safety.
    """
    def __init__(self, audit_log: Optional[ConflictAuditLog] = None):
        self.resolvers: Dict[str, ConflictResolver] = {}
        self.default_resolver = LastWriteWinsResolver()
        self.audit_log = audit_log or ConflictAuditLog()
        
        # Use common library components
        self.resolver_cache = ThreadSafeCache(max_size=50)  # Cache resolver instances
    
    def register_resolver(self, table_name: str, resolver: ConflictResolver) -> None:
        """Register a resolver for a specific table."""
        self.resolvers[table_name] = resolver
    
    def set_default_resolver(self, resolver: ConflictResolver) -> None:
        """Set the default resolver for tables without a specific resolver."""
        self.default_resolver = resolver
    
@atomic_operation
    def resolve_conflict(self, 
                        table_name: str, 
                        client_change: ChangeRecord, 
                        server_record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Resolve a conflict and log the resolution with thread safety.
        
        Args:
            table_name: Name of the table
            client_change: Change from the client
            server_record: Current record on the server
            
        Returns:
            Resolved record, or None to reject the client change
        """
        # Get the appropriate resolver with caching
        cache_key = f"resolver:{table_name}"
        resolver = self.resolver_cache.get(cache_key)
        if resolver is None:
            resolver = self.resolvers.get(table_name, self.default_resolver)
            self.resolver_cache.put(cache_key, resolver)
        
        resolver_name = resolver.__class__.__name__
        
        # Resolve the conflict
        try:
            resolution = resolver.resolve(table_name, client_change, server_record)
        except Exception as e:
            # Log the error but don't crash
            print(f"Error in conflict resolver {resolver_name}: {e}")
            # Fall back to default resolver
            resolution = self.default_resolver.resolve(table_name, client_change, server_record)
            resolver_name = f"{resolver_name}_fallback_to_default"
        
        # Log the conflict resolution
        metadata = ConflictMetadata(
            table_name=table_name,
            primary_key=client_change.primary_key,
            conflict_time=time.time(),
            client_id=client_change.client_id,
            client_change=client_change.to_dict(),
            server_record=server_record,
            resolution=resolution,
            resolution_strategy=resolver_name
        )
        self.audit_log.log_conflict(metadata)
        
        return resolution