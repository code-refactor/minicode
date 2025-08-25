"""Storage system for the ResearchBrain knowledge management system."""

import json
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union
from uuid import UUID

import pandas as pd
import yaml
from pydantic import BaseModel

from common.core import EntityStorage, StorageError as CommonStorageError
from researchbrain.core.models import KnowledgeNode


T = TypeVar('T', bound=KnowledgeNode)
MAX_WORKERS = 8  # Maximum number of worker threads for parallel operations


class StorageError(Exception):
    """Exception raised for errors in the storage system."""
    pass


class LocalStorage:
    """Storage system that persists data to the local filesystem in plain text formats.
    
    This is a wrapper around the common EntityStorage with ResearchBrain-specific functionality.
    """

    def __init__(self, base_path: Union[str, Path]):
        """Initialize the storage system.

        Args:
            base_path: The base directory for storing all data.
        """
        self.base_path = Path(base_path)
        self._storages = {}  # Dictionary to store EntityStorage instances by model type
        self._ensure_directories()
        self._locks = {}  # Dictionary to store locks for file access
        self._cache = {}  # Simple in-memory cache for frequently accessed items
        self._cache_lock = threading.RLock()  # Lock for cache access

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            'notes',
            'citations',
            'research_questions',
            'experiments',
            'grants',
            'collaborators',
            'annotations',
            'attachments',
            'backups',
            'indexes',  # For search indexes
            'templates',  # For experiment templates
        ]

        for directory in directories:
            path = self.base_path / directory
            path.mkdir(parents=True, exist_ok=True)

    def _get_collection_path(self, model_type: Type[T]) -> Path:
        """Get the path for a specific collection based on model type.

        Args:
            model_type: The type of model to determine the collection.

        Returns:
            Path to the collection directory.
        """
        type_name = model_type.__name__.lower()
        if type_name.endswith('s'):
            collection_name = type_name
        else:
            collection_name = f"{type_name}s"

        if model_type.__name__ == 'ResearchQuestion':
            collection_name = 'research_questions'
        elif model_type.__name__ == 'GrantProposal':
            collection_name = 'grants'

        return self.base_path / collection_name

    def _get_lock(self, file_path: Union[str, Path]) -> threading.RLock:
        """Get a lock for a specific file path, creating one if it doesn't exist.

        Args:
            file_path: The file path to get a lock for.

        Returns:
            A reentrant lock for the file path.
        """
        file_path_str = str(file_path)
        if file_path_str not in self._locks:
            self._locks[file_path_str] = threading.RLock()
        return self._locks[file_path_str]
    
    def _get_storage(self, model_type: Type[T]) -> EntityStorage[T]:
        """Get or create an EntityStorage instance for a specific model type.
        
        Args:
            model_type: The type of model to get storage for.
            
        Returns:
            EntityStorage instance for the model type.
        """
        type_name = model_type.__name__
        if type_name not in self._storages:
            self._storages[type_name] = EntityStorage(self.base_path, model_type)
        return self._storages[type_name]

    def save(self, item: T) -> None:
        """Save an item to storage.

        Args:
            item: The item to save.
        """
        try:
            storage = self._get_storage(type(item))
            storage.save(item)
            # Also update local cache for backward compatibility
            self._update_cache(item)
        except CommonStorageError as e:
            raise StorageError(str(e)) from e

    def _update_cache(self, item: T) -> None:
        """Update the in-memory cache with the latest version of an item.

        Args:
            item: The item to cache.
        """
        with self._cache_lock:
            type_name = type(item).__name__
            if type_name not in self._cache:
                self._cache[type_name] = {}
            self._cache[type_name][str(item.id)] = item

    def _get_from_cache(self, model_type: Type[T], item_id: UUID) -> Optional[T]:
        """Try to get an item from the cache.

        Args:
            model_type: The type of the item to retrieve.
            item_id: The UUID of the item.

        Returns:
            The cached item if found, None otherwise.
        """
        with self._cache_lock:
            type_name = model_type.__name__
            if type_name in self._cache and str(item_id) in self._cache[type_name]:
                return self._cache[type_name][str(item_id)]
        return None

    def _invalidate_cache(self, model_type: Optional[Type[T]] = None, item_id: Optional[UUID] = None) -> None:
        """Invalidate the cache for a specific item or type.

        Args:
            model_type: Optional type to invalidate cache for.
            item_id: Optional item ID to invalidate cache for.
        """
        with self._cache_lock:
            if model_type is None:
                self._cache = {}  # Clear the entire cache
            elif item_id is None:
                type_name = model_type.__name__
                if type_name in self._cache:
                    del self._cache[type_name]  # Clear cache for this type
            else:
                type_name = model_type.__name__
                if type_name in self._cache and str(item_id) in self._cache[type_name]:
                    del self._cache[type_name][str(item_id)]  # Clear cache for this item

    def _convert_uuids_to_strings(self, data):
        """Convert UUID objects to strings in a data structure.

        Args:
            data: The data structure to convert, modified in place.
        """
        if isinstance(data, dict):
            for key, value in list(data.items()):
                if isinstance(value, UUID):
                    data[key] = str(value)
                elif isinstance(value, list):
                    self._convert_uuids_to_strings(value)
                elif isinstance(value, dict):
                    self._convert_uuids_to_strings(value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, UUID):
                    data[i] = str(item)
                elif isinstance(item, dict):
                    self._convert_uuids_to_strings(item)
                elif isinstance(item, list):
                    self._convert_uuids_to_strings(item)

    def _convert_enums_to_strings(self, data):
        """Convert Enum objects to strings in a data structure.

        Args:
            data: The data structure to convert, modified in place.
        """
        from enum import Enum

        if isinstance(data, dict):
            for key, value in list(data.items()):
                if isinstance(value, Enum):
                    data[key] = value.value
                elif isinstance(value, list):
                    self._convert_enums_to_strings(value)
                elif isinstance(value, dict):
                    self._convert_enums_to_strings(value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, Enum):
                    data[i] = item.value
                elif isinstance(item, dict):
                    self._convert_enums_to_strings(item)
                elif isinstance(item, list):
                    self._convert_enums_to_strings(item)

    def _convert_string_to_uuid(self, data):
        """Convert string UUIDs back to UUID objects.

        Args:
            data: The data structure to convert, modified in place.
        """
        if isinstance(data, dict):
            # Convert 'id' fields to UUID
            if 'id' in data and isinstance(data['id'], str):
                try:
                    data['id'] = UUID(data['id'])
                except ValueError:
                    pass

            # Process source field in Notes
            if 'source' in data and isinstance(data['source'], str) and data['source'] != 'null':
                try:
                    data['source'] = UUID(data['source'])
                except ValueError:
                    pass

            # Convert lists of UUIDs
            uuid_list_fields = [
                'citations', 'notes', 'experiments', 'research_questions',
                'collaborators', 'replies', 'related_questions', 'grants'
            ]

            for key in uuid_list_fields:
                if key in data and isinstance(data[key], list):
                    for i, item in enumerate(data[key]):
                        if isinstance(item, str):
                            try:
                                data[key][i] = UUID(item)
                            except ValueError:
                                pass

            # Process specific UUID fields
            uuid_fields = ['resolved_by', 'parent_id', 'collaborator_id', 'node_id', 'research_question_id']
            for field in uuid_fields:
                if field in data and isinstance(data[field], str) and data[field] != 'null':
                    try:
                        data[field] = UUID(data[field])
                    except ValueError:
                        pass

            # Process nested structures
            for key, value in data.items():
                if isinstance(value, dict):
                    self._convert_string_to_uuid(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._convert_string_to_uuid(item)

    def _convert_strings_to_enums(self, data, model_type: Type[T]):
        """Convert string values back to Enum objects based on the model type.

        Args:
            data: The data structure to convert, modified in place.
            model_type: The model type to use for enum conversion.
        """
        # Import enum types based on model_type
        from researchbrain.core.models import (
            CitationType, CitationFormat, EvidenceType, EvidenceStrength,
            ExperimentStatus, GrantStatus, CollaboratorRole
        )

        # Map of field names to enum types
        enum_map = {
            'citation_type': CitationType,
            'format': CitationFormat,
            'evidence_type': EvidenceType,
            'strength': EvidenceStrength,
            'status': None,  # Special case - multiple models use 'status'
            'role': None,    # Special case for Collaborator
        }

        # Special handling for status field based on model type
        if model_type.__name__ == 'Experiment':
            enum_map['status'] = ExperimentStatus
        elif model_type.__name__ == 'GrantProposal':
            enum_map['status'] = GrantStatus
        elif model_type.__name__ == 'Collaborator':
            enum_map['role'] = CollaboratorRole

        if isinstance(data, dict):
            for key, value in data.items():
                if key in enum_map and enum_map[key] is not None and isinstance(value, str):
                    try:
                        data[key] = enum_map[key](value)
                    except ValueError:
                        pass  # Keep as string if conversion fails
                elif isinstance(value, dict):
                    self._convert_strings_to_enums(value, model_type)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            # For Evidence objects within a list
                            if key == 'evidence' and 'evidence_type' in item and 'strength' in item:
                                if isinstance(item['evidence_type'], str):
                                    try:
                                        item['evidence_type'] = EvidenceType(item['evidence_type'])
                                    except ValueError:
                                        pass
                                if isinstance(item['strength'], str):
                                    try:
                                        item['strength'] = EvidenceStrength(item['strength'])
                                    except ValueError:
                                        pass
                            self._convert_strings_to_enums(item, model_type)

    def get(self, model_type: Type[T], item_id: UUID) -> Optional[T]:
        """Retrieve an item by ID.

        Args:
            model_type: The type of the item to retrieve.
            item_id: The UUID of the item.

        Returns:
            The requested item or None if not found.
        """
        # Try to get from cache first
        cached_item = self._get_from_cache(model_type, item_id)
        if cached_item is not None:
            return cached_item

        try:
            storage = self._get_storage(model_type)
            item = storage.get(item_id)
            if item:
                self._update_cache(item)
            return item
        except CommonStorageError as e:
            raise StorageError(str(e)) from e

    def delete(self, model_type: Type[T], item_id: UUID) -> bool:
        """Delete an item by ID.

        Args:
            model_type: The type of the item to delete.
            item_id: The UUID of the item.

        Returns:
            True if the item was deleted, False if it wasn't found.
        """
        try:
            storage = self._get_storage(model_type)
            result = storage.delete(item_id)
            if result:
                # Invalidate both our local cache and the EntityStorage cache
                self._invalidate_cache(model_type, item_id)
                storage._invalidate_cache(item_id)
            return result
        except CommonStorageError as e:
            raise StorageError(str(e)) from e

    def list_all(self, model_type: Type[T]) -> List[T]:
        """List all items of a specific type.

        Args:
            model_type: The type of items to list.

        Returns:
            A list of all items of the specified type.
        """
        try:
            storage = self._get_storage(model_type)
            items = storage.list_all()
            # Update cache with all loaded items
            for item in items:
                self._update_cache(item)
            return items
        except CommonStorageError as e:
            raise StorageError(str(e)) from e

    def _load_item_from_file(self, file_path: Path, model_type: Type[T]) -> Optional[T]:
        """Load an item from a file.

        Args:
            file_path: The path to the file.
            model_type: The type of the item to load.

        Returns:
            The loaded item or None if loading failed.
        """
        # Extract the UUID from the filename
        try:
            item_id = UUID(file_path.stem)

            # Check cache first
            cached_item = self._get_from_cache(model_type, item_id)
            if cached_item is not None:
                return cached_item

            # Use a lock to prevent reading while the file is being written
            with self._get_lock(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                # Convert string UUIDs back to UUID objects
                self._convert_string_to_uuid(data)

                # Convert string values back to Enum objects
                self._convert_strings_to_enums(data, model_type)

                item = model_type(**data)

                # Update the cache
                self._update_cache(item)

                return item
        except Exception as e:
            # Print error for debugging but don't raise
            print(f"Error loading {file_path}: {e}")
            return None

    def query(self, model_type: Type[T], **filters) -> List[T]:
        """Query items of a specific type with filters.

        Args:
            model_type: The type of items to query.
            **filters: Field-value pairs to filter on.

        Returns:
            A list of items that match the filters.
        """
        try:
            storage = self._get_storage(model_type)
            return storage.query(**filters)
        except CommonStorageError as e:
            raise StorageError(str(e)) from e

    def save_attachment(self, file_path: Union[str, Path], target_filename: Optional[str] = None) -> Path:
        """Save an attachment file to the storage system.

        Args:
            file_path: Path to the file to save.
            target_filename: Optional custom filename to use.

        Returns:
            The path where the attachment was saved.
        """
        source_path = Path(file_path)

        if not source_path.exists():
            raise StorageError(f"Attachment file not found: {file_path}")

        if target_filename is None:
            target_filename = source_path.name

        attachments_dir = self.base_path / 'attachments'
        target_path = attachments_dir / target_filename

        # Use a lock to prevent concurrent writes
        with self._get_lock(target_path):
            # Copy the file
            shutil.copy2(source_path, target_path)

        return target_path

    def get_attachment(self, filename: str) -> Optional[Path]:
        """Get the path to an attachment file.

        Args:
            filename: Name of the attachment file.

        Returns:
            The path to the attachment or None if not found.
        """
        attachments_dir = self.base_path / 'attachments'
        file_path = attachments_dir / filename

        if file_path.exists():
            return file_path
        return None

    def export_to_dataframe(self, model_type: Type[T]) -> pd.DataFrame:
        """Export all items of a specific type to a pandas DataFrame.

        Args:
            model_type: The type of items to export.

        Returns:
            A DataFrame containing all items of the specified type.
        """
        items = self.list_all(model_type)
        if not items:
            return pd.DataFrame()

        # Convert to dict and normalize
        data = [item.model_dump() for item in items]

        # Convert UUIDs to strings for pandas compatibility
        for item_data in data:
            self._convert_uuids_to_strings(item_data)

        return pd.json_normalize(data)

    def backup(self, backup_dir: Union[str, Path]) -> Path:
        """Create a backup of all data.

        Args:
            backup_dir: Directory to store the backup.

        Returns:
            Path to the created backup directory.
        """
        backup_path = Path(backup_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_dir = backup_path / f"researchbrain_backup_{timestamp}"

        target_dir.mkdir(parents=True, exist_ok=True)

        # Create the data directory
        (target_dir / 'data').mkdir(parents=True, exist_ok=True)

        # Ensure all directories exist in the backup
        for dir_name in ['notes', 'citations', 'research_questions', 'experiments',
                        'grants', 'collaborators', 'annotations', 'attachments',
                        'templates', 'indexes']:
            (target_dir / 'data' / dir_name).mkdir(parents=True, exist_ok=True)

        # Debug info
        print(f"Creating backup at: {target_dir}")

        # Use a thread pool for parallel copying
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []

            # Copy files selectively to avoid recursively copying previous backups
            for item in sorted(self.base_path.glob('*')):
                # Skip previous backups
                if item.name == 'backups':
                    continue

                if item.is_dir():
                    # Create the directory in the target
                    (target_dir / 'data' / item.name).mkdir(parents=True, exist_ok=True)

                    # Copy all files in the directory
                    for file_path in item.glob('*'):
                        if file_path.is_file():
                            dest_path = target_dir / 'data' / item.name / file_path.name
                            futures.append(executor.submit(shutil.copy2, file_path, dest_path))
                elif item.is_file():
                    # Copy the file
                    dest_path = target_dir / 'data' / item.name
                    futures.append(executor.submit(shutil.copy2, item, dest_path))

            # Wait for all copy operations to complete
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Error during backup: {e}")

        # Create a metadata file with backup information
        metadata = {
            "backup_time": timestamp,
            "version": "1.0",
            "directories": list(str(path) for path in (target_dir / 'data').glob('*')),
        }

        with open(target_dir / 'backup_metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        print(f"Backup completed: {target_dir}")

        return target_dir

    def restore(self, backup_path: Union[str, Path]) -> None:
        """Restore data from a backup.

        Args:
            backup_path: Path to the backup directory.
        """
        source_path = Path(backup_path) / 'data'

        if not source_path.exists():
            raise StorageError(f"Backup data not found at {source_path}")

        # Clear the cache
        self._invalidate_cache()

        # Clear existing data, but skip the backups directory
        for item in self.base_path.glob('*'):
            if item.name == 'backups':
                continue

            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # Debug info
        print(f"Source path: {source_path}, exists: {source_path.exists()}")
        print(f"Files in source path: {list(source_path.glob('*'))}")

        # Make sure all necessary directories exist in the target
        self._ensure_directories()

        # Use a thread pool for parallel copying
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []

            # Copy from backup
            for item in source_path.glob('*'):
                print(f"Restoring: {item}")
                if item.is_dir():
                    # Create the directory in the target
                    target_dir = self.base_path / item.name
                    target_dir.mkdir(parents=True, exist_ok=True)
                    print(f"  Created dir: {target_dir}")

                    # Copy all files in the directory
                    for file_path in item.glob('*'):
                        if file_path.is_file():
                            dest_path = target_dir / file_path.name
                            futures.append(executor.submit(shutil.copy2, file_path, dest_path))
                elif item.is_file():
                    # Copy the file
                    dest_path = self.base_path / item.name
                    futures.append(executor.submit(shutil.copy2, item, dest_path))

            # Wait for all copy operations to complete
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"Error during restore: {e}")

        print("Restore completed")

    def build_search_index(self, model_type: Type[T], fields: List[str]) -> None:
        """Build a search index for a specific model type and fields.

        Args:
            model_type: The type of items to index.
            fields: The fields to index.
        """
        items = self.list_all(model_type)
        if not items:
            return

        # Create a simplified index structure for each field
        indexes = {}
        for field in fields:
            indexes[field] = {}

        # Build the index
        for item in items:
            item_dict = item.model_dump()
            item_id = str(item.id)

            for field in fields:
                if field in item_dict and isinstance(item_dict[field], str):
                    # Tokenize the field content
                    tokens = item_dict[field].lower().split()
                    # Add item ID to the index for each token
                    for token in tokens:
                        if token not in indexes[field]:
                            indexes[field][token] = set()
                        indexes[field][token].add(item_id)

        # Save the index
        index_path = self.base_path / 'indexes' / f"{model_type.__name__.lower()}_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            # Convert sets to lists for JSON serialization
            for field in indexes:
                for token in indexes[field]:
                    indexes[field][token] = list(indexes[field][token])
            json.dump(indexes, f, indent=2)

    def search_index(self, model_type: Type[T], search_text: str, fields: List[str]) -> List[UUID]:
        """Search the index for items matching the search text.

        Args:
            model_type: The type of items to search.
            search_text: The text to search for.
            fields: The fields to search in.

        Returns:
            A list of UUIDs of matching items.
        """
        index_path = self.base_path / 'indexes' / f"{model_type.__name__.lower()}_index.json"
        if not index_path.exists():
            # If index doesn't exist, build it
            self.build_search_index(model_type, fields)

            # If it still doesn't exist, fall back to text search
            if not index_path.exists():
                items = self.search_text(model_type, search_text, fields)
                return [item.id for item in items]

        # Load the index
        with open(index_path, 'r', encoding='utf-8') as f:
            indexes = json.load(f)

        # Tokenize the search text
        tokens = search_text.lower().split()

        # Find matching items
        matching_ids = set()
        first_match = True

        for token in tokens:
            token_matches = set()

            for field in fields:
                if field in indexes:
                    for indexed_token, item_ids in indexes[field].items():
                        if token in indexed_token:
                            token_matches.update(item_ids)

            # Intersect with previous matches
            if first_match:
                matching_ids = token_matches
                first_match = False
            else:
                matching_ids &= token_matches

        # Convert matching IDs to UUID objects
        return [UUID(item_id) for item_id in matching_ids]

    def search_text(self, model_type: Type[T], search_text: str, fields: List[str]) -> List[T]:
        """Search for items containing specific text in certain fields.

        Args:
            model_type: The type of items to search.
            search_text: The text to search for.
            fields: The fields to search in.

        Returns:
            A list of matching items.
        """
        try:
            storage = self._get_storage(model_type)
            return storage.search_text(search_text, fields)
        except CommonStorageError as e:
            raise StorageError(str(e)) from e

    def transaction(self, func=None, *args, **kwargs):
        """Execute a function within a transaction or act as a context manager.

        Args:
            func: The function to execute (optional for context manager mode).
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function or self as a context manager.

        Raises:
            Any exception raised by the function.
        """
        # If no function is provided, return self as a context manager
        if func is None:
            return self._TransactionContext(self)

        # Create a backup of the current state
        temp_backup_dir = self.base_path / 'backups' / f"transaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup(temp_backup_dir)

        try:
            # Execute the function
            result = func(*args, **kwargs)

            # If the function completed successfully, clean up the backup
            shutil.rmtree(backup_path)

            return result
        except Exception as e:
            # If the function failed, restore from the backup
            self.restore(backup_path)

            # Clean up the backup
            shutil.rmtree(backup_path)

            # Re-raise the exception
            raise e

    class _TransactionContext:
        """Context manager for transactions."""

        def __init__(self, storage):
            """Initialize with the storage instance.

            Args:
                storage: The storage instance.
            """
            self.storage = storage
            self.backup_path = None

        def __enter__(self):
            """Enter the context, creating a backup.

            Returns:
                The storage instance.
            """
            # Create a backup of the current state
            temp_backup_dir = self.storage.base_path / 'backups' / f"transaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.backup_path = self.storage.backup(temp_backup_dir)
            return self.storage

        def __exit__(self, exc_type, exc_val, exc_tb):
            """Exit the context, cleaning up or restoring as needed.

            Args:
                exc_type: Exception type if an exception occurred.
                exc_val: Exception value if an exception occurred.
                exc_tb: Exception traceback if an exception occurred.

            Returns:
                False to propagate exceptions.
            """
            if exc_type is not None:
                # An exception occurred, restore from the backup
                self.storage.restore(self.backup_path)

            # Clean up the backup
            if self.backup_path and os.path.exists(self.backup_path):
                shutil.rmtree(self.backup_path)

            # Don't suppress exceptions
            return False