"""Storage interfaces and implementations for the unified library."""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Callable, Union
from datetime import datetime
from uuid import UUID
import threading

T = TypeVar('T')


class StorageInterface(ABC, Generic[T]):
    """Abstract interface for all storage implementations."""
    
    @abstractmethod
    def create(self, entity: T) -> str:
        """Create a new entity and return its ID."""
        pass
    
    @abstractmethod
    def get(self, entity_id: Union[str, UUID]) -> Optional[T]:
        """Retrieve an entity by ID."""
        pass
    
    @abstractmethod
    def update(self, entity: T) -> Optional[T]:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: Union[str, UUID]) -> bool:
        """Delete an entity by ID."""
        pass
    
    @abstractmethod
    def list(self, 
             filters: Optional[Dict[str, Any]] = None,
             sort_by: Optional[str] = None,
             limit: Optional[int] = None,
             offset: int = 0) -> List[T]:
        """List entities with optional filtering and pagination."""
        pass
    
    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching the filters."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all entities from storage."""
        pass
    
    @abstractmethod
    def exists(self, entity_id: Union[str, UUID]) -> bool:
        """Check if an entity exists."""
        pass


class InMemoryStorage(StorageInterface[T]):
    """Generic in-memory storage implementation."""
    
    def __init__(self, entity_class: Type[T]):
        """Initialize in-memory storage."""
        self._items: Dict[str, T] = {}
        self._entity_class = entity_class
        self._lock = threading.RLock()
    
    def create(self, entity: T) -> str:
        """Create a new entity and return its ID."""
        with self._lock:
            entity_id = getattr(entity, 'id', None)
            if not entity_id:
                raise ValueError("Entity must have an 'id' field")
            
            # Convert UUID to string for storage
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            
            if storage_id in self._items:
                raise ValueError(f"Entity with ID {storage_id} already exists")
            
            self._items[storage_id] = entity
            return storage_id
    
    def get(self, entity_id: Union[str, UUID]) -> Optional[T]:
        """Retrieve an entity by ID."""
        with self._lock:
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            return self._items.get(storage_id)
    
    def update(self, entity: T) -> Optional[T]:
        """Update an existing entity."""
        with self._lock:
            entity_id = getattr(entity, 'id', None)
            if not entity_id:
                raise ValueError("Entity must have an 'id' field")
            
            # Convert UUID to string for storage
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            
            if storage_id not in self._items:
                return None
            
            # Update the updated_at timestamp if the entity has one
            if hasattr(entity, 'updated_at'):
                setattr(entity, 'updated_at', datetime.now())
            
            self._items[storage_id] = entity
            return entity
    
    def delete(self, entity_id: Union[str, UUID]) -> bool:
        """Delete an entity by ID."""
        with self._lock:
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            if storage_id not in self._items:
                return False
            
            del self._items[storage_id]
            return True
    
    def list(self,
             filters: Optional[Dict[str, Any]] = None,
             sort_by: Optional[str] = None,
             limit: Optional[int] = None,
             offset: int = 0) -> List[T]:
        """List entities with optional filtering and pagination."""
        with self._lock:
            items = list(self._items.values())
            
            # Apply filters
            if filters:
                items = self._apply_filters(items, filters)
            
            # Apply sorting
            if sort_by:
                items = self._apply_sorting(items, sort_by)
            
            # Apply pagination
            if offset > 0:
                items = items[offset:]
            
            if limit is not None and limit > 0:
                items = items[:limit]
            
            return items
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching the filters."""
        with self._lock:
            if not filters:
                return len(self._items)
            
            items = list(self._items.values())
            filtered = self._apply_filters(items, filters)
            return len(filtered)
    
    def clear(self) -> None:
        """Clear all entities from storage."""
        with self._lock:
            self._items.clear()
    
    def exists(self, entity_id: Union[str, UUID]) -> bool:
        """Check if an entity exists."""
        with self._lock:
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            return storage_id in self._items
    
    def _apply_filters(self, items: List[T], filters: Dict[str, Any]) -> List[T]:
        """Apply filters to a list of items."""
        filtered = []
        
        for item in items:
            match = True
            
            for key, value in filters.items():
                # Handle nested field access (e.g., "metadata.key")
                field_value = self._get_nested_field(item, key)
                
                # Handle different filter types
                if isinstance(value, dict):
                    # Complex filter operations
                    if '$in' in value:
                        if field_value not in value['$in']:
                            match = False
                            break
                    elif '$contains' in value:
                        if value['$contains'] not in str(field_value):
                            match = False
                            break
                    elif '$gt' in value:
                        if field_value <= value['$gt']:
                            match = False
                            break
                    elif '$lt' in value:
                        if field_value >= value['$lt']:
                            match = False
                            break
                    elif '$gte' in value:
                        if field_value < value['$gte']:
                            match = False
                            break
                    elif '$lte' in value:
                        if field_value > value['$lte']:
                            match = False
                            break
                else:
                    # Handle set membership check
                    if isinstance(field_value, set):
                        # Check if value is in the set
                        if value not in field_value:
                            match = False
                            break
                    # Handle list membership check
                    elif isinstance(field_value, list):
                        # Check if value is in the list
                        if value not in field_value:
                            match = False
                            break
                    # Simple equality check for other types
                    elif field_value != value:
                        match = False
                        break
            
            if match:
                filtered.append(item)
        
        return filtered
    
    def _apply_sorting(self, items: List[T], sort_by: str) -> List[T]:
        """Apply sorting to a list of items."""
        reverse = False
        
        # Handle descending sort (e.g., "-created_at")
        if sort_by.startswith('-'):
            reverse = True
            sort_by = sort_by[1:]
        
        try:
            return sorted(
                items,
                key=lambda x: self._get_nested_field(x, sort_by),
                reverse=reverse
            )
        except (AttributeError, KeyError):
            # If sort field doesn't exist, return unsorted
            return items
    
    def _get_nested_field(self, obj: Any, field_path: str) -> Any:
        """Get a nested field value from an object."""
        parts = field_path.split('.')
        value = obj
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value


class FileStorage(StorageInterface[T]):
    """Generic file-based storage with JSON serialization."""
    
    def __init__(self, 
                 filepath: Path,
                 entity_class: Type[T],
                 serializer: Optional[Callable[[T], Dict]] = None,
                 deserializer: Optional[Callable[[Dict], T]] = None):
        """Initialize file-based storage."""
        self.filepath = Path(filepath)
        self._entity_class = entity_class
        self._lock = threading.RLock()
        
        # Use custom or default serialization
        self._serializer = serializer or self._default_serializer
        self._deserializer = deserializer or self._default_deserializer
        
        # Ensure directory exists
        self._ensure_directory()
    
    def _default_serializer(self, entity: T) -> Dict:
        """Default serialization method."""
        if hasattr(entity, 'to_dict'):
            return entity.to_dict()
        elif hasattr(entity, '__dict__'):
            return entity.__dict__.copy()
        else:
            raise ValueError(f"Cannot serialize entity of type {type(entity)}")
    
    def _default_deserializer(self, data: Dict) -> T:
        """Default deserialization method."""
        if hasattr(self._entity_class, 'from_dict'):
            return self._entity_class.from_dict(data)
        else:
            return self._entity_class(**data)
    
    def _ensure_directory(self) -> None:
        """Ensure the directory for the file exists."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self) -> Dict[str, T]:
        """Load all entities from file."""
        if not self.filepath.exists():
            return {}
        
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                return {
                    entity_id: self._deserializer(entity_data)
                    for entity_id, entity_data in data.items()
                }
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save(self, data: Dict[str, T]) -> None:
        """Save all entities to file."""
        serialized = {
            entity_id: self._serializer(entity)
            for entity_id, entity in data.items()
        }
        
        # Atomic write with temporary file
        temp_file = self.filepath.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(serialized, f, indent=2, default=str)
            temp_file.replace(self.filepath)
        except Exception:
            if temp_file.exists():
                temp_file.unlink()
            raise
    
    def create(self, entity: T) -> str:
        """Create a new entity and return its ID."""
        with self._lock:
            data = self._load()
            
            entity_id = getattr(entity, 'id', None)
            if not entity_id:
                raise ValueError("Entity must have an 'id' field")
            
            # Convert UUID to string for storage
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            
            if storage_id in data:
                raise ValueError(f"Entity with ID {storage_id} already exists")
            
            data[storage_id] = entity
            self._save(data)
            return storage_id
    
    def get(self, entity_id: Union[str, UUID]) -> Optional[T]:
        """Retrieve an entity by ID."""
        with self._lock:
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            data = self._load()
            return data.get(storage_id)
    
    def update(self, entity: T) -> Optional[T]:
        """Update an existing entity."""
        with self._lock:
            data = self._load()
            
            entity_id = getattr(entity, 'id', None)
            if not entity_id:
                raise ValueError("Entity must have an 'id' field")
            
            # Convert UUID to string for storage
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            
            if storage_id not in data:
                return None
            
            # Update the updated_at timestamp if the entity has one
            if hasattr(entity, 'updated_at'):
                setattr(entity, 'updated_at', datetime.now())
            
            data[storage_id] = entity
            self._save(data)
            return entity
    
    def delete(self, entity_id: Union[str, UUID]) -> bool:
        """Delete an entity by ID."""
        with self._lock:
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            data = self._load()
            
            if storage_id not in data:
                return False
            
            del data[storage_id]
            self._save(data)
            return True
    
    def list(self,
             filters: Optional[Dict[str, Any]] = None,
             sort_by: Optional[str] = None,
             limit: Optional[int] = None,
             offset: int = 0) -> List[T]:
        """List entities with optional filtering and pagination."""
        with self._lock:
            data = self._load()
            items = list(data.values())
            
            # Reuse in-memory filtering logic
            temp_storage = InMemoryStorage(self._entity_class)
            temp_storage._items = data
            return temp_storage.list(filters, sort_by, limit, offset)
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching the filters."""
        with self._lock:
            data = self._load()
            
            # Reuse in-memory filtering logic
            temp_storage = InMemoryStorage(self._entity_class)
            temp_storage._items = data
            return temp_storage.count(filters)
    
    def clear(self) -> None:
        """Clear all entities from storage."""
        with self._lock:
            self._save({})
    
    def exists(self, entity_id: Union[str, UUID]) -> bool:
        """Check if an entity exists."""
        with self._lock:
            storage_id = str(entity_id) if isinstance(entity_id, UUID) else entity_id
            data = self._load()
            return storage_id in data