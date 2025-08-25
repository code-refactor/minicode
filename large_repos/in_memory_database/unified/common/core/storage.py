"""Core storage abstractions for the unified library."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Callable
from threading import RLock
from datetime import datetime
import json


class BaseDataStore(ABC):
    """Abstract base class for all data storage implementations."""
    
    @abstractmethod
    def insert(self, key: Any, data: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Insert a new record into the store."""
        pass
    
    @abstractmethod
    def update(self, key: Any, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing record in the store."""
        pass
    
    @abstractmethod
    def delete(self, key: Any) -> bool:
        """Delete a record from the store."""
        pass
    
    @abstractmethod
    def get(self, key: Any) -> Optional[Any]:
        """Retrieve a record by key."""
        pass
    
    @abstractmethod
    def query(self, conditions: Optional[Dict[str, Any]] = None, 
              limit: Optional[int] = None) -> List[Any]:
        """Query records based on conditions."""
        pass
    
    @abstractmethod
    def batch_operation(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple operations in batch."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all records from the store."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Return the number of records in the store."""
        pass


class InMemoryStore(BaseDataStore):
    """Thread-safe in-memory implementation of BaseDataStore."""
    
    def __init__(self):
        """Initialize the in-memory store."""
        self._data: Dict[Any, Any] = {}
        self._metadata: Dict[Any, Dict[str, Any]] = {}
        self._lock = RLock()
        self._created_at: Dict[Any, datetime] = {}
        self._updated_at: Dict[Any, datetime] = {}
    
    def insert(self, key: Any, data: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Insert a new record into the store."""
        with self._lock:
            if key in self._data:
                raise KeyError(f"Key {key} already exists")
            
            self._data[key] = data
            self._metadata[key] = metadata or {}
            now = datetime.now()
            self._created_at[key] = now
            self._updated_at[key] = now
            
            return str(key)
    
    def update(self, key: Any, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing record in the store."""
        with self._lock:
            if key not in self._data:
                return False
            
            self._data[key] = data
            if metadata is not None:
                self._metadata[key] = metadata
            self._updated_at[key] = datetime.now()
            
            return True
    
    def delete(self, key: Any) -> bool:
        """Delete a record from the store."""
        with self._lock:
            if key not in self._data:
                return False
            
            del self._data[key]
            self._metadata.pop(key, None)
            self._created_at.pop(key, None)
            self._updated_at.pop(key, None)
            
            return True
    
    def get(self, key: Any) -> Optional[Any]:
        """Retrieve a record by key."""
        with self._lock:
            return self._data.get(key)
    
    def query(self, conditions: Optional[Dict[str, Any]] = None, 
              limit: Optional[int] = None) -> List[Any]:
        """Query records based on conditions."""
        with self._lock:
            results = []
            
            for key, value in self._data.items():
                if self._matches_conditions(key, value, conditions):
                    results.append(value)
                    
                    if limit and len(results) >= limit:
                        break
            
            return results
    
    def batch_operation(self, operations: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple operations in batch."""
        results = []
        
        with self._lock:
            for op in operations:
                op_type = op.get('type')
                
                if op_type == 'insert':
                    try:
                        result = self.insert(op['key'], op['data'], op.get('metadata'))
                        results.append({'success': True, 'result': result})
                    except Exception as e:
                        results.append({'success': False, 'error': str(e)})
                
                elif op_type == 'update':
                    result = self.update(op['key'], op['data'], op.get('metadata'))
                    results.append({'success': result})
                
                elif op_type == 'delete':
                    result = self.delete(op['key'])
                    results.append({'success': result})
                
                elif op_type == 'get':
                    result = self.get(op['key'])
                    results.append({'success': result is not None, 'result': result})
                
                else:
                    results.append({'success': False, 'error': f'Unknown operation type: {op_type}'})
        
        return results
    
    def clear(self) -> None:
        """Clear all records from the store."""
        with self._lock:
            self._data.clear()
            self._metadata.clear()
            self._created_at.clear()
            self._updated_at.clear()
    
    def size(self) -> int:
        """Return the number of records in the store."""
        with self._lock:
            return len(self._data)
    
    def get_metadata(self, key: Any) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific key."""
        with self._lock:
            return self._metadata.get(key)
    
    def get_timestamps(self, key: Any) -> Optional[Dict[str, datetime]]:
        """Get creation and update timestamps for a key."""
        with self._lock:
            if key not in self._data:
                return None
            
            return {
                'created_at': self._created_at.get(key),
                'updated_at': self._updated_at.get(key)
            }
    
    def _matches_conditions(self, key: Any, value: Any, 
                          conditions: Optional[Dict[str, Any]]) -> bool:
        """Check if a record matches the given conditions."""
        if not conditions:
            return True
        
        for field, expected in conditions.items():
            if field == '_key' and key != expected:
                return False
            
            if hasattr(value, '__dict__'):
                if not hasattr(value, field) or getattr(value, field) != expected:
                    return False
            elif isinstance(value, dict):
                if field not in value or value[field] != expected:
                    return False
            else:
                return False
        
        return True


class TableStore(InMemoryStore):
    """Table-based storage extending InMemoryStore."""
    
    def __init__(self, name: str, primary_key: Optional[List[str]] = None):
        """Initialize table store with name and optional primary key."""
        super().__init__()
        self.name = name
        self.primary_key = primary_key or []
        self._indexes: Dict[str, Dict[Any, List[Any]]] = {}
    
    def create_index(self, field: str) -> None:
        """Create an index on a field for faster queries."""
        with self._lock:
            if field not in self._indexes:
                self._indexes[field] = {}
                
                # Build index for existing data
                for key, value in self._data.items():
                    self._update_index(field, key, value, 'add')
    
    def drop_index(self, field: str) -> None:
        """Drop an index on a field."""
        with self._lock:
            self._indexes.pop(field, None)
    
    def insert(self, key: Any, data: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Insert with index updates."""
        result = super().insert(key, data, metadata)
        
        # Update indexes
        for field in self._indexes:
            self._update_index(field, key, data, 'add')
        
        return result
    
    def update(self, key: Any, data: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update with index updates."""
        with self._lock:
            old_data = self._data.get(key)
            result = super().update(key, data, metadata)
            
            if result:
                # Update indexes
                for field in self._indexes:
                    self._update_index(field, key, old_data, 'remove')
                    self._update_index(field, key, data, 'add')
            
            return result
    
    def delete(self, key: Any) -> bool:
        """Delete with index updates."""
        with self._lock:
            data = self._data.get(key)
            result = super().delete(key)
            
            if result:
                # Update indexes
                for field in self._indexes:
                    self._update_index(field, key, data, 'remove')
            
            return result
    
    def _update_index(self, field: str, key: Any, data: Any, 
                     operation: str) -> None:
        """Update index for a field."""
        if field not in self._indexes:
            return
        
        # Extract field value
        if isinstance(data, dict):
            field_value = data.get(field)
        elif hasattr(data, field):
            field_value = getattr(data, field)
        else:
            return
        
        if operation == 'add':
            if field_value not in self._indexes[field]:
                self._indexes[field][field_value] = []
            if key not in self._indexes[field][field_value]:
                self._indexes[field][field_value].append(key)
        
        elif operation == 'remove':
            if field_value in self._indexes[field]:
                try:
                    self._indexes[field][field_value].remove(key)
                    if not self._indexes[field][field_value]:
                        del self._indexes[field][field_value]
                except ValueError:
                    pass