"""Common exceptions for the unified library."""

from typing import Optional, Any
from uuid import UUID


class UnifiedLibraryError(Exception):
    """Base exception for all unified library errors."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.details = details or {}


class StorageError(UnifiedLibraryError):
    """Exception raised for storage-related errors."""
    pass


class EntityNotFoundError(UnifiedLibraryError):
    """Exception raised when an entity is not found."""
    
    def __init__(self, entity_type: str, entity_id: UUID, message: Optional[str] = None):
        self.entity_type = entity_type
        self.entity_id = entity_id
        if message is None:
            message = f"{entity_type} with ID {entity_id} not found"
        super().__init__(message, {"entity_type": entity_type, "entity_id": str(entity_id)})


class ValidationError(UnifiedLibraryError):
    """Exception raised for validation errors."""
    
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        super().__init__(message, {"field": field, "value": value})


class DuplicateEntityError(UnifiedLibraryError):
    """Exception raised when attempting to create a duplicate entity."""
    
    def __init__(self, entity_type: str, identifier: Any, message: Optional[str] = None):
        self.entity_type = entity_type
        self.identifier = identifier
        if message is None:
            message = f"Duplicate {entity_type} with identifier {identifier}"
        super().__init__(message, {"entity_type": entity_type, "identifier": str(identifier)})


class PermissionError(UnifiedLibraryError):
    """Exception raised for permission-related errors."""
    pass


class ImportError(UnifiedLibraryError):
    """Exception raised during import operations."""
    pass


class ExportError(UnifiedLibraryError):
    """Exception raised during export operations."""
    pass


class SearchError(UnifiedLibraryError):
    """Exception raised during search operations."""
    pass


class AnalysisError(UnifiedLibraryError):
    """Exception raised during analysis operations."""
    pass


class ConfigurationError(UnifiedLibraryError):
    """Exception raised for configuration-related errors."""
    pass


class NetworkError(UnifiedLibraryError):
    """Exception raised for network-related errors."""
    pass


class ConcurrencyError(UnifiedLibraryError):
    """Exception raised for concurrency-related errors."""
    pass


class DataIntegrityError(UnifiedLibraryError):
    """Exception raised when data integrity is compromised."""
    pass