"""
Manager pattern implementations for financial applications.

This module provides base manager classes and common patterns that both
persona implementations can use for organizing business logic and data access.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar, Callable
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
import logging
from contextlib import contextmanager

# Import from our core modules
from ..core.validation import ValidationResult, ValidationError
from ..core.models import BaseTransaction, Money, Period

# Type variables for generic managers
T = TypeVar('T')
K = TypeVar('K')  # Key type
V = TypeVar('V')  # Value type

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ManagerResult:
    """Result from manager operations."""
    success: bool
    data: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_result(cls, data: Any = None, metadata: Dict[str, Any] = None) -> 'ManagerResult':
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            metadata=metadata or {}
        )
    
    @classmethod
    def error_result(cls, errors: Union[str, List[str]], data: Any = None) -> 'ManagerResult':
        """Create an error result."""
        if isinstance(errors, str):
            errors = [errors]
        
        return cls(
            success=False,
            data=data,
            errors=errors
        )
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def merge(self, other: 'ManagerResult') -> 'ManagerResult':
        """Merge with another result."""
        merged = ManagerResult(
            success=self.success and other.success,
            data=self.data if self.data is not None else other.data,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            metadata={**self.metadata, **other.metadata}
        )
        return merged


class BaseManager(ABC, Generic[T]):
    """
    Abstract base class for business logic managers.
    
    Provides common patterns for validation, error handling,
    and operation lifecycle management.
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize base manager.
        
        Args:
            name: Optional name for the manager
        """
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._hooks: Dict[str, List[Callable]] = {}
    
    def register_hook(self, event: str, callback: Callable) -> None:
        """
        Register a hook for a specific event.
        
        Args:
            event: Event name (e.g., 'before_create', 'after_update')
            callback: Callback function to execute
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    def execute_hooks(self, event: str, *args, **kwargs) -> None:
        """Execute all hooks for a given event."""
        for callback in self._hooks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"Hook callback failed for event {event}: {e}")
    
    @abstractmethod
    def validate(self, item: T) -> ValidationResult:
        """
        Validate an item before processing.
        
        Args:
            item: Item to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        pass
    
    @contextmanager
    def operation_context(self, operation_name: str, **metadata):
        """
        Context manager for tracking operations.
        
        Provides hook execution and error handling for operations.
        
        Args:
            operation_name: Name of the operation
            **metadata: Additional metadata for the operation
        """
        self.logger.debug(f"Starting operation: {operation_name}")
        
        # Execute before hooks
        self.execute_hooks(f"before_{operation_name}", **metadata)
        
        start_time = datetime.now()
        success = False
        error = None
        
        try:
            yield
            success = True
        except Exception as e:
            error = e
            self.logger.error(f"Operation {operation_name} failed: {e}")
            raise
        finally:
            # Calculate duration
            duration = datetime.now() - start_time
            
            # Execute after hooks
            hook_metadata = {
                **metadata,
                'success': success,
                'duration': duration,
                'error': error
            }
            self.execute_hooks(f"after_{operation_name}", **hook_metadata)
            
            self.logger.debug(
                f"Completed operation {operation_name}: "
                f"success={success}, duration={duration.total_seconds():.3f}s"
            )
    
    def handle_validation_result(self, validation_result: ValidationResult) -> ManagerResult:
        """
        Convert validation result to manager result.
        
        Args:
            validation_result: Validation result to convert
            
        Returns:
            ManagerResult based on validation
        """
        if validation_result.is_valid:
            result = ManagerResult.success_result()
            result.warnings = validation_result.warnings
            return result
        else:
            return ManagerResult.error_result(validation_result.errors)


class CRUDManager(BaseManager[T]):
    """
    Base manager for CRUD (Create, Read, Update, Delete) operations.
    
    Provides standard patterns for managing collections of objects
    with validation, hooks, and error handling.
    """
    
    def __init__(self, name: Optional[str] = None):
        super().__init__(name)
        self._storage: Dict[str, T] = {}
        self._id_counter = 0
    
    def _generate_id(self) -> str:
        """Generate a unique ID for new items."""
        self._id_counter += 1
        return f"{self.name}_{self._id_counter}_{datetime.now().timestamp()}"
    
    def create(self, item: T, item_id: Optional[str] = None) -> ManagerResult:
        """
        Create a new item.
        
        Args:
            item: Item to create
            item_id: Optional ID for the item (auto-generated if None)
            
        Returns:
            ManagerResult with creation status
        """
        with self.operation_context("create", item=item, item_id=item_id):
            # Validate item
            validation_result = self.validate(item)
            if not validation_result.is_valid:
                return self.handle_validation_result(validation_result)
            
            # Generate ID if needed
            if item_id is None:
                item_id = self._generate_id()
            
            # Check if ID already exists
            if item_id in self._storage:
                return ManagerResult.error_result(f"Item with ID {item_id} already exists")
            
            # Store item
            self._storage[item_id] = item
            
            result = ManagerResult.success_result(
                data={"id": item_id, "item": item},
                metadata={"operation": "create", "id": item_id}
            )
            result.warnings = validation_result.warnings
            
            self.logger.info(f"Created item with ID: {item_id}")
            return result
    
    def read(self, item_id: str) -> ManagerResult:
        """
        Read an item by ID.
        
        Args:
            item_id: ID of item to read
            
        Returns:
            ManagerResult with the item or error
        """
        with self.operation_context("read", item_id=item_id):
            if item_id not in self._storage:
                return ManagerResult.error_result(f"Item with ID {item_id} not found")
            
            item = self._storage[item_id]
            return ManagerResult.success_result(
                data={"id": item_id, "item": item},
                metadata={"operation": "read", "id": item_id}
            )
    
    def update(self, item_id: str, item: T) -> ManagerResult:
        """
        Update an existing item.
        
        Args:
            item_id: ID of item to update
            item: New item data
            
        Returns:
            ManagerResult with update status
        """
        with self.operation_context("update", item_id=item_id, item=item):
            if item_id not in self._storage:
                return ManagerResult.error_result(f"Item with ID {item_id} not found")
            
            # Validate new item
            validation_result = self.validate(item)
            if not validation_result.is_valid:
                return self.handle_validation_result(validation_result)
            
            # Store old item for hooks
            old_item = self._storage[item_id]
            
            # Update item
            self._storage[item_id] = item
            
            result = ManagerResult.success_result(
                data={"id": item_id, "item": item, "old_item": old_item},
                metadata={"operation": "update", "id": item_id}
            )
            result.warnings = validation_result.warnings
            
            self.logger.info(f"Updated item with ID: {item_id}")
            return result
    
    def delete(self, item_id: str) -> ManagerResult:
        """
        Delete an item by ID.
        
        Args:
            item_id: ID of item to delete
            
        Returns:
            ManagerResult with deletion status
        """
        with self.operation_context("delete", item_id=item_id):
            if item_id not in self._storage:
                return ManagerResult.error_result(f"Item with ID {item_id} not found")
            
            # Get item for hooks
            item = self._storage[item_id]
            
            # Delete item
            del self._storage[item_id]
            
            result = ManagerResult.success_result(
                data={"id": item_id, "deleted_item": item},
                metadata={"operation": "delete", "id": item_id}
            )
            
            self.logger.info(f"Deleted item with ID: {item_id}")
            return result
    
    def list_all(self, filter_func: Optional[Callable[[T], bool]] = None) -> ManagerResult:
        """
        List all items, optionally filtered.
        
        Args:
            filter_func: Optional function to filter items
            
        Returns:
            ManagerResult with list of items
        """
        with self.operation_context("list_all", filter_func=filter_func):
            items = []
            
            for item_id, item in self._storage.items():
                if filter_func is None or filter_func(item):
                    items.append({"id": item_id, "item": item})
            
            return ManagerResult.success_result(
                data=items,
                metadata={"operation": "list_all", "count": len(items)}
            )
    
    def count(self, filter_func: Optional[Callable[[T], bool]] = None) -> ManagerResult:
        """
        Count items, optionally filtered.
        
        Args:
            filter_func: Optional function to filter items
            
        Returns:
            ManagerResult with count
        """
        with self.operation_context("count", filter_func=filter_func):
            if filter_func is None:
                count = len(self._storage)
            else:
                count = sum(1 for item in self._storage.values() if filter_func(item))
            
            return ManagerResult.success_result(
                data=count,
                metadata={"operation": "count"}
            )
    
    def exists(self, item_id: str) -> bool:
        """Check if an item exists."""
        return item_id in self._storage
    
    def clear(self) -> ManagerResult:
        """
        Clear all items.
        
        Returns:
            ManagerResult with clear status
        """
        with self.operation_context("clear"):
            count = len(self._storage)
            self._storage.clear()
            
            self.logger.info(f"Cleared {count} items")
            
            return ManagerResult.success_result(
                data={"cleared_count": count},
                metadata={"operation": "clear"}
            )


class TransactionManager(CRUDManager[BaseTransaction]):
    """
    Specialized manager for financial transactions.
    
    Extends CRUDManager with transaction-specific functionality
    like categorization, period filtering, and balance calculations.
    """
    
    def __init__(self):
        super().__init__("TransactionManager")
    
    def validate(self, transaction: BaseTransaction) -> ValidationResult:
        """Validate a transaction."""
        result = ValidationResult(True)
        
        try:
            # Use the transaction's own validation
            transaction.validate()
        except ValidationError as e:
            result.add_error(str(e))
        
        # Additional business rules
        if transaction.amount == 0:
            result.add_error("Transaction amount cannot be zero")
        
        # Check date is not too far in the future
        if transaction.date.date() > date.today().replace(year=date.today().year + 1):
            result.add_warning("Transaction date is more than a year in the future")
        
        return result
    
    def get_transactions_by_period(self, period: Period) -> ManagerResult:
        """
        Get transactions within a specific period.
        
        Args:
            period: Period to filter transactions
            
        Returns:
            ManagerResult with filtered transactions
        """
        def period_filter(transaction: BaseTransaction) -> bool:
            return period.contains_date(transaction.date)
        
        return self.list_all(filter_func=period_filter)
    
    def get_transactions_by_category(self, category: str) -> ManagerResult:
        """
        Get transactions by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            ManagerResult with filtered transactions
        """
        def category_filter(transaction: BaseTransaction) -> bool:
            return transaction.category == category
        
        return self.list_all(filter_func=category_filter)
    
    def calculate_balance(self, up_to_date: Optional[date] = None) -> ManagerResult:
        """
        Calculate balance from all transactions.
        
        Args:
            up_to_date: Optional date to calculate balance up to
            
        Returns:
            ManagerResult with balance calculation
        """
        with self.operation_context("calculate_balance", up_to_date=up_to_date):
            balance = Decimal('0')
            transaction_count = 0
            
            for transaction in self._storage.values():
                # Filter by date if specified
                if up_to_date and transaction.date.date() > up_to_date:
                    continue
                
                balance += transaction.amount
                transaction_count += 1
            
            return ManagerResult.success_result(
                data={
                    "balance": balance,
                    "transaction_count": transaction_count,
                    "up_to_date": up_to_date
                },
                metadata={
                    "operation": "calculate_balance",
                    "up_to_date": up_to_date.isoformat() if up_to_date else None
                }
            )
    
    def get_categories(self) -> ManagerResult:
        """
        Get all unique categories from transactions.
        
        Returns:
            ManagerResult with list of categories
        """
        with self.operation_context("get_categories"):
            categories = set()
            
            for transaction in self._storage.values():
                if transaction.category:
                    categories.add(transaction.category)
            
            return ManagerResult.success_result(
                data=sorted(categories),
                metadata={"operation": "get_categories", "count": len(categories)}
            )


class CacheableManager(BaseManager[T]):
    """
    Manager with caching capabilities.
    
    Provides automatic caching of expensive operations
    with configurable cache policies.
    """
    
    def __init__(self, name: Optional[str] = None, cache_ttl: int = 3600):
        super().__init__(name)
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation and parameters."""
        import hashlib
        import json
        
        # Create a deterministic string from operation and kwargs
        key_data = {"operation": operation, "params": kwargs}
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = datetime.now() - self._cache_timestamps[cache_key]
        return age.total_seconds() < self.cache_ttl
    
    def cached_operation(self, operation_name: str, operation_func: Callable, **kwargs) -> Any:
        """
        Execute operation with caching.
        
        Args:
            operation_name: Name of the operation for cache key
            operation_func: Function to execute if not cached
            **kwargs: Parameters for the operation
            
        Returns:
            Operation result (from cache or fresh execution)
        """
        cache_key = self._get_cache_key(operation_name, **kwargs)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            self.logger.debug(f"Cache hit for operation: {operation_name}")
            return self._cache[cache_key]
        
        # Execute operation
        self.logger.debug(f"Cache miss for operation: {operation_name}")
        result = operation_func(**kwargs)
        
        # Cache result
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
        
        return result
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """
        Invalidate cache entries.
        
        Args:
            pattern: Optional pattern to match keys (clears all if None)
        """
        if pattern is None:
            # Clear all cache
            self._cache.clear()
            self._cache_timestamps.clear()
            self.logger.info("Cleared all cache entries")
        else:
            # Clear matching keys
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            
            for key in keys_to_remove:
                del self._cache[key]
                del self._cache_timestamps[key]
            
            self.logger.info(f"Cleared {len(keys_to_remove)} cache entries matching pattern: {pattern}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now()
        
        valid_entries = sum(
            1 for timestamp in self._cache_timestamps.values()
            if (now - timestamp).total_seconds() < self.cache_ttl
        )
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "cache_ttl": self.cache_ttl,
            "oldest_entry": min(self._cache_timestamps.values()) if self._cache_timestamps else None,
            "newest_entry": max(self._cache_timestamps.values()) if self._cache_timestamps else None
        }


class ConfigurableManager(BaseManager[T]):
    """
    Manager with configurable behavior.
    
    Allows runtime configuration of manager behavior
    through configuration parameters.
    """
    
    def __init__(self, name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(name)
        self.config = config or {}
        self._default_config = self._get_default_config()
    
    @abstractmethod
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for this manager."""
        pass
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, self._default_config.get(key, default))
    
    def set_config(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
        self.logger.debug(f"Set configuration: {key} = {value}")
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Update multiple configuration values.
        
        Args:
            config: Dictionary of configuration updates
        """
        self.config.update(config)
        self.logger.debug(f"Updated configuration with {len(config)} values")
    
    def reset_config(self) -> None:
        """Reset configuration to defaults."""
        self.config = self._default_config.copy()
        self.logger.info("Reset configuration to defaults")
    
    def validate_config(self) -> ValidationResult:
        """
        Validate current configuration.
        
        Returns:
            ValidationResult with configuration validation status
        """
        # Override in subclasses for specific validation rules
        return ValidationResult(True)