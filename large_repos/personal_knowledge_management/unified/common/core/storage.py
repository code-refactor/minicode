"""Generic storage system for the unified library."""

import json
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Type, TypeVar, Union
from uuid import UUID

import yaml
from pydantic import BaseModel

from common.core.exceptions import (
    EntityNotFoundError,
    StorageError,
    ValidationError,
    ConcurrencyError
)
from common.core.models import BaseEntity
from common.core.utils import (
    convert_strings_to_uuids,
    convert_uuids_to_strings,
    normalize_text,
    sanitize_filename
)


T = TypeVar('T', bound=BaseEntity)
MAX_WORKERS = 8  # Maximum number of worker threads for parallel operations


class EntityStorage(Generic[T]):
    """Generic storage system that persists entities to the filesystem."""
    
    def __init__(self, base_path: Union[str, Path], entity_type: Type[T]):
        """Initialize the storage system.
        
        Args:
            base_path: The base directory for storing all data.
            entity_type: The type of entity this storage handles.
        """
        self.base_path = Path(base_path)
        self.entity_type = entity_type
        self._collection_name = self._get_collection_name()
        self._ensure_directories()
        self._locks: Dict[str, threading.RLock] = {}
        self._cache: Dict[str, T] = {}
        self._cache_lock = threading.RLock()
        self._indexes: Dict[str, Dict[str, Set[str]]] = {}  # field -> value -> entity_ids
        self._index_lock = threading.RLock()
        self._build_indexes()
    
    def _get_collection_name(self) -> str:
        """Get the collection name for this entity type."""
        type_name = self.entity_type.__name__.lower()
        
        # Handle special cases
        if type_name.endswith('y'):
            return type_name[:-1] + 'ies'
        elif type_name.endswith('s') or type_name.endswith('x') or type_name.endswith('ch'):
            return type_name + 'es'
        else:
            return type_name + 's'
    
    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self._collection_name,
            'backups',
            'indexes',
            'exports'
        ]
        
        for directory in directories:
            path = self.base_path / directory
            path.mkdir(parents=True, exist_ok=True)
    
    def _get_collection_path(self) -> Path:
        """Get the path for this collection."""
        return self.base_path / self._collection_name
    
    def _get_entity_path(self, entity_id: UUID) -> Path:
        """Get the file path for a specific entity."""
        return self._get_collection_path() / f"{entity_id}.yaml"
    
    def _get_lock(self, entity_id: UUID) -> threading.RLock:
        """Get a lock for a specific entity."""
        entity_id_str = str(entity_id)
        if entity_id_str not in self._locks:
            self._locks[entity_id_str] = threading.RLock()
        return self._locks[entity_id_str]
    
    def save(self, entity: T) -> None:
        """Save an entity to storage.
        
        Args:
            entity: The entity to save.
            
        Raises:
            StorageError: If save operation fails.
        """
        try:
            file_path = self._get_entity_path(entity.id)
            
            # Update timestamp
            entity.update()
            
            # Get lock for this entity
            with self._get_lock(entity.id):
                # Convert to dict and handle serialization
                data = entity.model_dump()
                data = convert_uuids_to_strings(data)
                
                # Write to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
                
                # Update cache
                self._update_cache(entity)
                
                # Update indexes
                self._update_indexes(entity)
                
        except Exception as e:
            raise StorageError(f"Failed to save entity {entity.id}: {str(e)}")
    
    def save_batch(self, entities: List[T]) -> None:
        """Save multiple entities in parallel.
        
        Args:
            entities: List of entities to save.
        """
        with ThreadPoolExecutor(max_workers=min(len(entities), MAX_WORKERS)) as executor:
            futures = [executor.submit(self.save, entity) for entity in entities]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions that occurred
    
    def get(self, entity_id: UUID) -> Optional[T]:
        """Retrieve an entity by ID.
        
        Args:
            entity_id: The ID of the entity to retrieve.
            
        Returns:
            The entity if found, None otherwise.
        """
        # Check cache first
        cached = self._get_from_cache(entity_id)
        if cached is not None:
            return cached
        
        file_path = self._get_entity_path(entity_id)
        
        if not file_path.exists():
            return None
        
        try:
            with self._get_lock(entity_id):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                # Convert string UUIDs back to UUID objects
                data = convert_strings_to_uuids(data)
                
                # Create entity instance
                entity = self.entity_type(**data)
                
                # Update cache
                self._update_cache(entity)
                
                return entity
                
        except Exception as e:
            raise StorageError(f"Failed to load entity {entity_id}: {str(e)}")
    
    def get_or_raise(self, entity_id: UUID) -> T:
        """Retrieve an entity by ID or raise an exception.
        
        Args:
            entity_id: The ID of the entity to retrieve.
            
        Returns:
            The entity.
            
        Raises:
            EntityNotFoundError: If entity is not found.
        """
        entity = self.get(entity_id)
        if entity is None:
            raise EntityNotFoundError(self.entity_type.__name__, entity_id)
        return entity
    
    def delete(self, entity_id: UUID) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: The ID of the entity to delete.
            
        Returns:
            True if deleted, False if not found.
        """
        file_path = self._get_entity_path(entity_id)
        
        if not file_path.exists():
            return False
        
        try:
            with self._get_lock(entity_id):
                # Remove from cache
                self._invalidate_cache(entity_id)
                
                # Remove from indexes
                entity = self.get(entity_id)
                if entity:
                    self._remove_from_indexes(entity)
                
                # Delete file
                file_path.unlink()
                
                return True
                
        except Exception as e:
            raise StorageError(f"Failed to delete entity {entity_id}: {str(e)}")
    
    def list_all(self) -> List[T]:
        """List all entities in the collection.
        
        Returns:
            List of all entities.
        """
        collection_path = self._get_collection_path()
        entities = []
        
        for file_path in collection_path.glob("*.yaml"):
            try:
                entity_id = UUID(file_path.stem)
                entity = self.get(entity_id)
                if entity:
                    entities.append(entity)
            except (ValueError, StorageError):
                continue  # Skip invalid files
        
        return entities
    
    def query(self, **filters) -> List[T]:
        """Query entities with filters.
        
        Args:
            **filters: Field-value pairs to filter by.
            
        Returns:
            List of matching entities.
        """
        all_entities = self.list_all()
        results = []
        
        for entity in all_entities:
            match = True
            for field, value in filters.items():
                if not hasattr(entity, field):
                    match = False
                    break
                
                entity_value = getattr(entity, field)
                
                # Handle different comparison types
                if isinstance(value, (list, set)):
                    if entity_value not in value:
                        match = False
                        break
                elif callable(value):
                    if not value(entity_value):
                        match = False
                        break
                else:
                    if entity_value != value:
                        match = False
                        break
            
            if match:
                results.append(entity)
        
        return results
    
    def search_text(self, query: str, fields: Optional[List[str]] = None) -> List[T]:
        """Search entities by text content.
        
        Args:
            query: Search query string.
            fields: Optional list of fields to search in.
            
        Returns:
            List of matching entities.
        """
        query_normalized = normalize_text(query)
        all_entities = self.list_all()
        results = []
        
        for entity in all_entities:
            # Determine which fields to search
            if fields:
                search_fields = fields
            else:
                # Search all string fields by default
                search_fields = [
                    field for field in entity.model_fields
                    if isinstance(getattr(entity, field, None), str)
                ]
            
            # Check each field
            for field in search_fields:
                if hasattr(entity, field):
                    value = getattr(entity, field)
                    if value and isinstance(value, str):
                        if query_normalized in normalize_text(value):
                            results.append(entity)
                            break
        
        return results
    
    def count(self, **filters) -> int:
        """Count entities matching filters.
        
        Args:
            **filters: Field-value pairs to filter by.
            
        Returns:
            Number of matching entities.
        """
        if not filters:
            # Fast path for total count
            collection_path = self._get_collection_path()
            return len(list(collection_path.glob("*.yaml")))
        
        return len(self.query(**filters))
    
    def exists(self, entity_id: UUID) -> bool:
        """Check if an entity exists.
        
        Args:
            entity_id: The ID of the entity to check.
            
        Returns:
            True if entity exists, False otherwise.
        """
        return self._get_entity_path(entity_id).exists()
    
    def update(self, entity_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update specific fields of an entity.
        
        Args:
            entity_id: The ID of the entity to update.
            updates: Dictionary of field updates.
            
        Returns:
            True if updated, False if not found.
        """
        entity = self.get(entity_id)
        if not entity:
            return False
        
        try:
            # Apply updates
            for field, value in updates.items():
                if hasattr(entity, field):
                    setattr(entity, field, value)
            
            # Save updated entity
            self.save(entity)
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to update entity {entity_id}: {str(e)}")
    
    def backup(self, backup_name: Optional[str] = None) -> Path:
        """Create a backup of all entities.
        
        Args:
            backup_name: Optional name for the backup.
            
        Returns:
            Path to the backup directory.
        """
        if backup_name is None:
            backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_dir = self.base_path / 'backups' / self._collection_name / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        collection_path = self._get_collection_path()
        
        # Copy all entity files
        for file_path in collection_path.glob("*.yaml"):
            shutil.copy2(file_path, backup_dir / file_path.name)
        
        # Save metadata
        metadata = {
            'entity_type': self.entity_type.__name__,
            'timestamp': datetime.now().isoformat(),
            'entity_count': self.count()
        }
        
        with open(backup_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return backup_dir
    
    def restore(self, backup_path: Union[str, Path]) -> None:
        """Restore entities from a backup.
        
        Args:
            backup_path: Path to the backup directory.
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise StorageError(f"Backup path does not exist: {backup_path}")
        
        # Clear current data
        collection_path = self._get_collection_path()
        for file_path in collection_path.glob("*.yaml"):
            file_path.unlink()
        
        # Clear cache and indexes
        self._invalidate_cache()
        self._clear_indexes()
        
        # Restore files
        for file_path in backup_path.glob("*.yaml"):
            if file_path.name != 'metadata.yaml':
                shutil.copy2(file_path, collection_path / file_path.name)
        
        # Rebuild indexes
        self._build_indexes()
    
    def _update_cache(self, entity: T) -> None:
        """Update the cache with an entity."""
        with self._cache_lock:
            self._cache[str(entity.id)] = entity
    
    def _get_from_cache(self, entity_id: UUID) -> Optional[T]:
        """Get an entity from the cache."""
        with self._cache_lock:
            return self._cache.get(str(entity_id))
    
    def _invalidate_cache(self, entity_id: Optional[UUID] = None) -> None:
        """Invalidate cache entries."""
        with self._cache_lock:
            if entity_id is None:
                self._cache.clear()
            else:
                self._cache.pop(str(entity_id), None)
    
    def _build_indexes(self) -> None:
        """Build indexes for faster queries."""
        with self._index_lock:
            self._indexes.clear()
            
            # Index common fields
            indexable_fields = ['tags', 'status', 'priority', 'created_at']
            
            for entity in self.list_all():
                for field in indexable_fields:
                    if hasattr(entity, field):
                        value = getattr(entity, field)
                        if value is not None:
                            self._add_to_index(field, value, str(entity.id))
    
    def _add_to_index(self, field: str, value: Any, entity_id: str) -> None:
        """Add an entity to an index."""
        with self._index_lock:
            if field not in self._indexes:
                self._indexes[field] = {}
            
            # Convert value to string for indexing
            if isinstance(value, (list, set)):
                for item in value:
                    key = str(item)
                    if key not in self._indexes[field]:
                        self._indexes[field][key] = set()
                    self._indexes[field][key].add(entity_id)
            else:
                key = str(value)
                if key not in self._indexes[field]:
                    self._indexes[field][key] = set()
                self._indexes[field][key].add(entity_id)
    
    def _update_indexes(self, entity: T) -> None:
        """Update indexes when an entity is saved."""
        # Remove old index entries
        self._remove_from_indexes(entity)
        
        # Add new index entries
        indexable_fields = ['tags', 'status', 'priority', 'created_at']
        for field in indexable_fields:
            if hasattr(entity, field):
                value = getattr(entity, field)
                if value is not None:
                    self._add_to_index(field, value, str(entity.id))
    
    def _remove_from_indexes(self, entity: T) -> None:
        """Remove an entity from all indexes."""
        with self._index_lock:
            entity_id_str = str(entity.id)
            for field_index in self._indexes.values():
                for entity_set in field_index.values():
                    entity_set.discard(entity_id_str)
    
    def _clear_indexes(self) -> None:
        """Clear all indexes."""
        with self._index_lock:
            self._indexes.clear()
    
    def query_by_index(self, field: str, value: Any) -> List[T]:
        """Query using indexes for better performance.
        
        Args:
            field: Field to query by.
            value: Value to match.
            
        Returns:
            List of matching entities.
        """
        with self._index_lock:
            if field not in self._indexes:
                # Fall back to regular query
                return self.query(**{field: value})
            
            key = str(value)
            entity_ids = self._indexes[field].get(key, set())
            
            entities = []
            for entity_id_str in entity_ids:
                entity = self.get(UUID(entity_id_str))
                if entity:
                    entities.append(entity)
            
            return entities