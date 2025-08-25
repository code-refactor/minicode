"""Service layer base classes and registry for the unified library."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from .models import ValidationError
from .storage import StorageInterface

T = TypeVar('T')


class BaseService(ABC, Generic[T]):
    """Abstract base service with common operations."""
    
    def __init__(self, storage: StorageInterface[T]):
        """Initialize service with storage backend."""
        self.storage = storage
        self.validators: List[Callable[[T], List[ValidationError]]] = []
        self._pre_create_hooks: List[Callable[[T], T]] = []
        self._post_create_hooks: List[Callable[[T], None]] = []
        self._pre_update_hooks: List[Callable[[T], T]] = []
        self._post_update_hooks: List[Callable[[T], None]] = []
        self._pre_delete_hooks: List[Callable[[str], bool]] = []
        self._post_delete_hooks: List[Callable[[str], None]] = []
    
    def add_validator(self, validator: Callable[[T], List[ValidationError]]) -> None:
        """Add a custom validator function."""
        self.validators.append(validator)
    
    def add_pre_create_hook(self, hook: Callable[[T], T]) -> None:
        """Add a hook to run before entity creation."""
        self._pre_create_hooks.append(hook)
    
    def add_post_create_hook(self, hook: Callable[[T], None]) -> None:
        """Add a hook to run after entity creation."""
        self._post_create_hooks.append(hook)
    
    def add_pre_update_hook(self, hook: Callable[[T], T]) -> None:
        """Add a hook to run before entity update."""
        self._pre_update_hooks.append(hook)
    
    def add_post_update_hook(self, hook: Callable[[T], None]) -> None:
        """Add a hook to run after entity update."""
        self._post_update_hooks.append(hook)
    
    def add_pre_delete_hook(self, hook: Callable[[str], bool]) -> None:
        """Add a hook to run before entity deletion."""
        self._pre_delete_hooks.append(hook)
    
    def add_post_delete_hook(self, hook: Callable[[str], None]) -> None:
        """Add a hook to run after entity deletion."""
        self._post_delete_hooks.append(hook)
    
    def validate(self, entity: T) -> List[ValidationError]:
        """Validate an entity using all registered validators."""
        errors = []
        
        # Run entity's own validation if available
        if hasattr(entity, 'validate_fields'):
            errors.extend(entity.validate_fields())
        
        # Run custom validators
        for validator in self.validators:
            validator_errors = validator(entity)
            if validator_errors:
                errors.extend(validator_errors)
        
        return errors
    
    def create_with_validation(self, entity: T) -> str:
        """Create entity with validation and hooks."""
        # Validate
        errors = self.validate(entity)
        if errors:
            error_messages = [str(e) for e in errors]
            raise ValueError(f"Validation failed: {'; '.join(error_messages)}")
        
        # Run pre-create hooks
        for hook in self._pre_create_hooks:
            entity = hook(entity)
        
        # Create entity
        entity_id = self.storage.create(entity)
        
        # Run post-create hooks
        for hook in self._post_create_hooks:
            hook(entity)
        
        return entity_id
    
    def update_with_validation(self, entity: T) -> Optional[T]:
        """Update entity with validation and hooks."""
        # Validate
        errors = self.validate(entity)
        if errors:
            error_messages = [str(e) for e in errors]
            raise ValueError(f"Validation failed: {'; '.join(error_messages)}")
        
        # Run pre-update hooks
        for hook in self._pre_update_hooks:
            entity = hook(entity)
        
        # Update entity
        updated = self.storage.update(entity)
        
        if updated:
            # Run post-update hooks
            for hook in self._post_update_hooks:
                hook(updated)
        
        return updated
    
    def delete_with_hooks(self, entity_id: str) -> bool:
        """Delete entity with hooks."""
        # Run pre-delete hooks
        for hook in self._pre_delete_hooks:
            if not hook(entity_id):
                return False  # Hook prevented deletion
        
        # Delete entity
        deleted = self.storage.delete(entity_id)
        
        if deleted:
            # Run post-delete hooks
            for hook in self._post_delete_hooks:
                hook(entity_id)
        
        return deleted
    
    def get(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        return self.storage.get(entity_id)
    
    def list(self,
             filters: Optional[Dict[str, Any]] = None,
             sort_by: Optional[str] = None,
             limit: Optional[int] = None,
             offset: int = 0) -> List[T]:
        """List entities with optional filtering and pagination."""
        return self.storage.list(filters, sort_by, limit, offset)
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities matching the filters."""
        return self.storage.count(filters)
    
    def exists(self, entity_id: str) -> bool:
        """Check if an entity exists."""
        return self.storage.exists(entity_id)
    
    def clear(self) -> None:
        """Clear all entities."""
        self.storage.clear()


class ServiceRegistry:
    """Central registry for service discovery."""
    
    _instance = None
    _services: Dict[str, BaseService] = {}
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._services = {}
        return cls._instance
    
    def register(self, name: str, service: BaseService) -> None:
        """Register a service with a name."""
        if name in self._services:
            raise ValueError(f"Service '{name}' is already registered")
        self._services[name] = service
    
    def unregister(self, name: str) -> bool:
        """Unregister a service."""
        if name not in self._services:
            return False
        del self._services[name]
        return True
    
    def get(self, name: str) -> Optional[BaseService]:
        """Get a service by name."""
        return self._services.get(name)
    
    def get_or_raise(self, name: str) -> BaseService:
        """Get a service by name or raise an error."""
        service = self._services.get(name)
        if not service:
            raise ValueError(f"Service '{name}' not found in registry")
        return service
    
    def list_services(self) -> List[str]:
        """List all registered service names."""
        return list(self._services.keys())
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
    
    def has_service(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services


class CrossReferenceValidator:
    """Helper class for cross-service reference validation."""
    
    def __init__(self, registry: ServiceRegistry):
        """Initialize with service registry."""
        self.registry = registry
    
    def validate_reference(self,
                          service_name: str,
                          entity_id: str,
                          field_name: str) -> Optional[ValidationError]:
        """Validate that a referenced entity exists in another service."""
        service = self.registry.get(service_name)
        
        if not service:
            return ValidationError(
                field=field_name,
                message=f"Service '{service_name}' not found",
                code="service_not_found"
            )
        
        if not service.exists(entity_id):
            return ValidationError(
                field=field_name,
                message=f"Referenced entity '{entity_id}' not found in {service_name}",
                code="reference_not_found"
            )
        
        return None
    
    def validate_references(self,
                          references: Dict[str, str]) -> List[ValidationError]:
        """Validate multiple references.
        
        Args:
            references: Dict mapping field_name to "service:entity_id"
        
        Returns:
            List of validation errors
        """
        errors = []
        
        for field_name, reference in references.items():
            if ':' not in reference:
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Invalid reference format: {reference}",
                    code="invalid_reference_format"
                ))
                continue
            
            service_name, entity_id = reference.split(':', 1)
            error = self.validate_reference(service_name, entity_id, field_name)
            if error:
                errors.append(error)
        
        return errors