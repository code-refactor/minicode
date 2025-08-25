"""Utility functions for the unified library."""

import json
import tempfile
import shutil
from dataclasses import asdict, is_dataclass
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
import uuid

T = TypeVar('T')


def to_dict(entity: Any) -> Dict[str, Any]:
    """Convert an entity to a dictionary representation."""
    if hasattr(entity, 'to_dict'):
        return entity.to_dict()
    elif is_dataclass(entity):
        return asdict(entity)
    elif hasattr(entity, '__dict__'):
        return entity.__dict__.copy()
    else:
        raise ValueError(f"Cannot convert {type(entity)} to dictionary")


def from_dict(data: Dict[str, Any], entity_class: Type[T]) -> T:
    """Create an entity from a dictionary representation."""
    if hasattr(entity_class, 'from_dict'):
        return entity_class.from_dict(data)
    else:
        return entity_class(**data)


def json_encoder(obj: Any) -> Any:
    """Custom JSON encoder for common types."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, set):
        return list(obj)
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif is_dataclass(obj):
        return asdict(obj)
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def json_decoder_hook(data: Dict[str, Any]) -> Dict[str, Any]:
    """Custom JSON decoder hook for common types."""
    # Try to parse datetime strings
    for key, value in data.items():
        if isinstance(value, str):
            # Try to parse as datetime
            try:
                data[key] = datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                pass
    
    return data


def ensure_directory(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary."""
    path = Path(path)
    if path.is_file():
        path = path.parent
    path.mkdir(parents=True, exist_ok=True)


def safe_file_write(path: Path, content: str) -> None:
    """Write content to a file safely using atomic operations."""
    path = Path(path)
    ensure_directory(path.parent)
    
    # Write to temporary file first
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)
    
    # Atomic rename
    temp_path.replace(path)


def atomic_file_update(path: Path, updater: Callable[[str], str]) -> None:
    """Update a file atomically using a callback function."""
    path = Path(path)
    
    # Read current content
    if path.exists():
        with open(path, 'r') as f:
            content = f.read()
    else:
        content = ""
    
    # Update content
    new_content = updater(content)
    
    # Write atomically
    safe_file_write(path, new_content)


def merge_metadata(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge metadata dictionaries, with updates overriding base values."""
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = merge_metadata(result[key], value)
        else:
            result[key] = value
    
    return result


def filter_dict(data: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """Filter a dictionary to only include specified keys."""
    return {k: v for k, v in data.items() if k in keys}


def deep_update(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Deep update a dictionary, merging nested dictionaries."""
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_update(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(data: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary into a single-level dictionary."""
    result = {}
    
    def _flatten(obj: Any, prefix: str = '') -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}{separator}{key}" if prefix else key
                _flatten(value, new_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                new_key = f"{prefix}[{i}]"
                _flatten(item, new_key)
        else:
            result[prefix] = obj
    
    _flatten(data)
    return result


def unflatten_dict(data: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """Unflatten a single-level dictionary into a nested dictionary."""
    result = {}
    
    for key, value in data.items():
        parts = key.split(separator)
        current = result
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    return result


def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """Split a list into chunks of specified size."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def batch_process(items: List[T],
                 processor: Callable[[T], Any],
                 batch_size: int = 100) -> List[Any]:
    """Process items in batches."""
    results = []
    
    for batch in chunk_list(items, batch_size):
        batch_results = [processor(item) for item in batch]
        results.extend(batch_results)
    
    return results


def safe_get_nested(obj: Any, path: str, default: Any = None) -> Any:
    """Safely get a nested attribute or dictionary value."""
    parts = path.split('.')
    current = obj
    
    for part in parts:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            current = current.get(part)
            if current is None:
                return default
        else:
            return default
    
    return current


def safe_set_nested(obj: Any, path: str, value: Any) -> bool:
    """Safely set a nested attribute or dictionary value."""
    parts = path.split('.')
    current = obj
    
    # Navigate to the parent
    for part in parts[:-1]:
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            if part not in current:
                current[part] = {}
            current = current[part]
        else:
            return False
    
    # Set the final value
    final_key = parts[-1]
    if hasattr(current, final_key):
        setattr(current, final_key, value)
        return True
    elif isinstance(current, dict):
        current[final_key] = value
        return True
    
    return False


def generate_id() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def parse_file_size(size_str: str) -> int:
    """Parse human-readable file size to bytes."""
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'PB': 1024 ** 5
    }
    
    size_str = size_str.strip().upper()
    
    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            number_str = size_str[:-len(unit)].strip()
            try:
                return int(float(number_str) * multiplier)
            except ValueError:
                raise ValueError(f"Invalid file size: {size_str}")
    
    # Try to parse as plain number (bytes)
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid file size: {size_str}")


def create_backup(path: Path, suffix: str = '.bak') -> Path:
    """Create a backup of a file."""
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    backup_path = path.with_suffix(path.suffix + suffix)
    
    # Find a unique backup name
    counter = 1
    while backup_path.exists():
        backup_path = path.with_suffix(f"{path.suffix}{suffix}.{counter}")
        counter += 1
    
    shutil.copy2(path, backup_path)
    return backup_path


def restore_backup(backup_path: Path, original_path: Optional[Path] = None) -> Path:
    """Restore a file from backup."""
    backup_path = Path(backup_path)
    
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    if original_path is None:
        # Try to determine original path by removing backup suffix
        original_path = backup_path
        for suffix in ['.bak', '.backup', '.tmp']:
            if str(original_path).endswith(suffix):
                original_path = Path(str(original_path)[:-len(suffix)])
                break
    
    original_path = Path(original_path)
    shutil.copy2(backup_path, original_path)
    return original_path