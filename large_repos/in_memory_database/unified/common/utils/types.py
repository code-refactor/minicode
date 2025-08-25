"""Common type definitions and utilities for the unified library."""

from typing import (
    Any, Dict, List, Optional, Union, Callable, TypeVar, Generic, 
    Tuple, Set, Iterable, Mapping, Sequence, Protocol, runtime_checkable
)
from datetime import datetime, date, timezone
from decimal import Decimal
import json
import copy
from collections.abc import MutableMapping

# Type aliases for commonly used types
JSONSerializable = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
Record = Dict[str, Any]
Schema = Dict[str, Any]
Timestamp = Union[datetime, float, int]

# Type variables for generic functions
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary."""
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Serializable':
        """Create object from dictionary."""
        ...


@runtime_checkable
class Hashable(Protocol):
    """Protocol for hashable objects."""
    
    def __hash__(self) -> int:
        """Return hash value."""
        ...


class TypedDict(Generic[K, V]):
    """Type-safe dictionary wrapper."""
    
    def __init__(self, key_type: type, value_type: type, data: Optional[Dict[K, V]] = None):
        """Initialize typed dictionary.
        
        Args:
            key_type: Expected type for keys
            value_type: Expected type for values
            data: Initial data
        """
        self._key_type = key_type
        self._value_type = value_type
        self._data: Dict[K, V] = data or {}
        
        # Validate initial data
        for key, value in self._data.items():
            self._validate_key(key)
            self._validate_value(value)
    
    def _validate_key(self, key: K) -> None:
        """Validate key type."""
        if not isinstance(key, self._key_type):
            raise TypeError(f"Key must be {self._key_type.__name__}, got {type(key).__name__}")
    
    def _validate_value(self, value: V) -> None:
        """Validate value type."""
        if not isinstance(value, self._value_type):
            raise TypeError(f"Value must be {self._value_type.__name__}, got {type(value).__name__}")
    
    def __getitem__(self, key: K) -> V:
        """Get item by key."""
        self._validate_key(key)
        return self._data[key]
    
    def __setitem__(self, key: K, value: V) -> None:
        """Set item by key."""
        self._validate_key(key)
        self._validate_value(value)
        self._data[key] = value
    
    def __delitem__(self, key: K) -> None:
        """Delete item by key."""
        self._validate_key(key)
        del self._data[key]
    
    def __contains__(self, key: Any) -> bool:
        """Check if key exists."""
        return key in self._data
    
    def __iter__(self):
        """Iterate over keys."""
        return iter(self._data)
    
    def __len__(self) -> int:
        """Get number of items."""
        return len(self._data)
    
    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Get item with default."""
        try:
            return self[key]
        except (KeyError, TypeError):
            return default
    
    def keys(self):
        """Get keys."""
        return self._data.keys()
    
    def values(self):
        """Get values."""
        return self._data.values()
    
    def items(self):
        """Get items."""
        return self._data.items()
    
    def to_dict(self) -> Dict[K, V]:
        """Convert to regular dictionary."""
        return self._data.copy()


def ensure_list(value: Union[T, List[T]]) -> List[T]:
    """Ensure value is a list.
    
    Args:
        value: Value to convert to list
        
    Returns:
        List containing the value(s)
    """
    if isinstance(value, list):
        return value
    elif value is None:
        return []
    else:
        return [value]


def ensure_dict(value: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
    """Ensure value is a dictionary.
    
    Args:
        value: Value to convert to dictionary
        
    Returns:
        Dictionary representation of the value
    """
    if isinstance(value, dict):
        return value
    elif hasattr(value, 'to_dict') and callable(getattr(value, 'to_dict')):
        return value.to_dict()
    elif hasattr(value, '__dict__'):
        return value.__dict__
    elif value is None:
        return {}
    else:
        return {'value': value}


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any], 
               merge_lists: bool = False) -> Dict[str, Any]:
    """Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        merge_lists: Whether to merge lists or replace them
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = deep_merge(result[key], value, merge_lists)
            elif isinstance(result[key], list) and isinstance(value, list) and merge_lists:
                # Merge lists if enabled
                result[key] = result[key] + value
            else:
                # Replace value
                result[key] = value
        else:
            result[key] = value
    
    return result


def flatten_dict(data: Dict[str, Any], separator: str = '.', 
                prefix: str = '') -> Dict[str, Any]:
    """Flatten nested dictionary.
    
    Args:
        data: Dictionary to flatten
        separator: Separator for nested keys
        prefix: Prefix for keys
        
    Returns:
        Flattened dictionary
    """
    result = {}
    
    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            result.update(flatten_dict(value, separator, new_key))
        else:
            result[new_key] = value
    
    return result


def unflatten_dict(data: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """Unflatten dictionary with nested keys.
    
    Args:
        data: Flattened dictionary
        separator: Separator used in keys
        
    Returns:
        Nested dictionary
    """
    result = {}
    
    for key, value in data.items():
        parts = key.split(separator)
        current = result
        
        # Navigate to the correct nested level
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                # Handle conflict by converting to dict
                current[part] = {'_value': current[part]}
            current = current[part]
        
        # Set the final value
        final_key = parts[-1]
        if final_key in current and isinstance(current[final_key], dict):
            # Handle conflict by adding _value key
            current[final_key]['_value'] = value
        else:
            current[final_key] = value
    
    return result


def safe_cast(value: Any, target_type: type, default: Any = None) -> Any:
    """Safely cast value to target type.
    
    Args:
        value: Value to cast
        target_type: Target type
        default: Default value if cast fails
        
    Returns:
        Casted value or default
    """
    try:
        if value is None:
            return default
        
        if isinstance(value, target_type):
            return value
        
        # Special handling for common conversions
        if target_type == bool:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on', 'y')
            else:
                return bool(value)
        
        elif target_type == datetime:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value, tz=timezone.utc)
            elif isinstance(value, str):
                # Try common datetime formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d',
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                # If no format works, fall through to default casting
        
        elif target_type in (list, tuple):
            if isinstance(value, str):
                try:
                    # Try JSON parsing first
                    parsed = json.loads(value)
                    if isinstance(parsed, (list, tuple)):
                        return target_type(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
                # Split by comma as fallback
                return target_type(s.strip() for s in value.split(','))
            elif hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
                return target_type(value)
        
        elif target_type == dict:
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        return parsed
                except (json.JSONDecodeError, TypeError):
                    pass
            elif hasattr(value, 'to_dict') and callable(getattr(value, 'to_dict')):
                return value.to_dict()
            elif hasattr(value, '__dict__'):
                return value.__dict__
        
        # Default casting
        return target_type(value)
    
    except (ValueError, TypeError, AttributeError):
        return default


def is_serializable(value: Any) -> bool:
    """Check if value is JSON serializable.
    
    Args:
        value: Value to check
        
    Returns:
        True if value is JSON serializable
    """
    try:
        json.dumps(value, default=str)
        return True
    except (TypeError, ValueError):
        return False


def make_serializable(value: Any) -> JSONSerializable:
    """Convert value to JSON serializable form.
    
    Args:
        value: Value to make serializable
        
    Returns:
        JSON serializable representation
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    
    elif isinstance(value, Decimal):
        return float(value)
    
    elif isinstance(value, dict):
        return {str(k): make_serializable(v) for k, v in value.items()}
    
    elif isinstance(value, (list, tuple, set)):
        return [make_serializable(item) for item in value]
    
    elif hasattr(value, 'to_dict') and callable(getattr(value, 'to_dict')):
        return make_serializable(value.to_dict())
    
    elif hasattr(value, '__dict__'):
        return make_serializable(value.__dict__)
    
    else:
        # Fallback to string representation
        return str(value)


def deep_copy(value: T) -> T:
    """Create deep copy of value.
    
    Args:
        value: Value to copy
        
    Returns:
        Deep copy of the value
    """
    return copy.deepcopy(value)


def get_nested_value(data: Dict[str, Any], path: str, 
                    separator: str = '.', default: Any = None) -> Any:
    """Get value from nested dictionary using dot notation.
    
    Args:
        data: Dictionary to search
        path: Dot-separated path to value
        separator: Path separator
        default: Default value if path not found
        
    Returns:
        Value at path or default
    """
    try:
        current = data
        for key in path.split(separator):
            current = current[key]
        return current
    except (KeyError, TypeError, AttributeError):
        return default


def set_nested_value(data: Dict[str, Any], path: str, value: Any,
                    separator: str = '.', create_missing: bool = True) -> None:
    """Set value in nested dictionary using dot notation.
    
    Args:
        data: Dictionary to modify
        path: Dot-separated path to set
        value: Value to set
        separator: Path separator
        create_missing: Whether to create missing intermediate dictionaries
    """
    keys = path.split(separator)
    current = data
    
    # Navigate to parent of target key
    for key in keys[:-1]:
        if key not in current:
            if create_missing:
                current[key] = {}
            else:
                raise KeyError(f"Path '{path}' not found")
        elif not isinstance(current[key], dict):
            if create_missing:
                current[key] = {}
            else:
                raise TypeError(f"Cannot set nested value: '{key}' is not a dictionary")
        current = current[key]
    
    # Set the final value
    current[keys[-1]] = value


def delete_nested_value(data: Dict[str, Any], path: str, 
                       separator: str = '.') -> bool:
    """Delete value from nested dictionary using dot notation.
    
    Args:
        data: Dictionary to modify
        path: Dot-separated path to delete
        separator: Path separator
        
    Returns:
        True if value was deleted, False if path not found
    """
    try:
        keys = path.split(separator)
        current = data
        
        # Navigate to parent of target key
        for key in keys[:-1]:
            current = current[key]
        
        # Delete the final key
        if keys[-1] in current:
            del current[keys[-1]]
            return True
        else:
            return False
    except (KeyError, TypeError):
        return False


class LazyProperty:
    """Descriptor for lazy property evaluation."""
    
    def __init__(self, func: Callable[..., T]):
        """Initialize lazy property.
        
        Args:
            func: Function to compute property value
        """
        self.func = func
        self.name = func.__name__
        self.__doc__ = func.__doc__
    
    def __get__(self, instance, owner=None) -> T:
        """Get property value."""
        if instance is None:
            return self
        
        # Check if value is already computed
        cache_name = f'_lazy_{self.name}'
        if hasattr(instance, cache_name):
            return getattr(instance, cache_name)
        
        # Compute and cache value
        value = self.func(instance)
        setattr(instance, cache_name, value)
        return value
    
    def __set__(self, instance, value: T) -> None:
        """Set property value."""
        cache_name = f'_lazy_{self.name}'
        setattr(instance, cache_name, value)
    
    def __delete__(self, instance) -> None:
        """Delete cached property value."""
        cache_name = f'_lazy_{self.name}'
        if hasattr(instance, cache_name):
            delattr(instance, cache_name)


def cached_property(func: Callable[..., T]) -> LazyProperty:
    """Decorator for cached properties.
    
    Args:
        func: Function to decorate
        
    Returns:
        LazyProperty descriptor
    """
    return LazyProperty(func)


class Registry(Generic[T]):
    """Generic registry for managing named instances."""
    
    def __init__(self):
        """Initialize registry."""
        self._items: Dict[str, T] = {}
    
    def register(self, name: str, item: T) -> None:
        """Register an item.
        
        Args:
            name: Item name
            item: Item to register
        """
        if name in self._items:
            raise ValueError(f"Item '{name}' already registered")
        self._items[name] = item
    
    def unregister(self, name: str) -> bool:
        """Unregister an item.
        
        Args:
            name: Item name
            
        Returns:
            True if item was unregistered
        """
        return self._items.pop(name, None) is not None
    
    def get(self, name: str, default: Optional[T] = None) -> Optional[T]:
        """Get registered item.
        
        Args:
            name: Item name
            default: Default value if not found
            
        Returns:
            Registered item or default
        """
        return self._items.get(name, default)
    
    def list_names(self) -> List[str]:
        """List all registered names."""
        return list(self._items.keys())
    
    def list_items(self) -> List[T]:
        """List all registered items."""
        return list(self._items.values())
    
    def clear(self) -> None:
        """Clear all registered items."""
        self._items.clear()
    
    def __contains__(self, name: str) -> bool:
        """Check if name is registered."""
        return name in self._items
    
    def __len__(self) -> int:
        """Get number of registered items."""
        return len(self._items)


# Pre-configured registries for common use cases
type_registry: Registry[type] = Registry()
validator_registry: Registry[Callable] = Registry()
converter_registry: Registry[Callable] = Registry()


def register_type(name: str, type_class: type) -> None:
    """Register a type in the global type registry."""
    type_registry.register(name, type_class)


def register_validator(name: str, validator: Callable) -> None:
    """Register a validator in the global validator registry."""
    validator_registry.register(name, validator)


def register_converter(name: str, converter: Callable) -> None:
    """Register a converter in the global converter registry."""
    converter_registry.register(name, converter)