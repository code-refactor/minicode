"""Utility functions for the unified library."""

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID


def convert_uuids_to_strings(data: Any) -> Any:
    """Recursively convert UUID objects to strings in a data structure.
    
    Args:
        data: The data structure to convert.
        
    Returns:
        The data structure with UUIDs converted to strings.
    """
    if isinstance(data, UUID):
        return str(data)
    elif isinstance(data, dict):
        return {key: convert_uuids_to_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_uuids_to_strings(item) for item in data]
    elif isinstance(data, set):
        return {convert_uuids_to_strings(item) for item in data}
    elif isinstance(data, tuple):
        return tuple(convert_uuids_to_strings(item) for item in data)
    else:
        return data


def convert_strings_to_uuids(data: Any) -> Any:
    """Recursively convert UUID strings to UUID objects in a data structure.
    
    Args:
        data: The data structure to convert.
        
    Returns:
        The data structure with UUID strings converted to UUID objects.
    """
    if isinstance(data, str):
        try:
            return UUID(data)
        except (ValueError, AttributeError):
            return data
    elif isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Special handling for fields that should be UUIDs
            if key in ['id', 'parent_id', 'source', 'source_id'] or key.endswith('_id') or key.endswith('_ids'):
                result[key] = convert_strings_to_uuids(value)
            else:
                result[key] = value
        return result
    elif isinstance(data, list):
        return [convert_strings_to_uuids(item) for item in data]
    elif isinstance(data, set):
        return {convert_strings_to_uuids(item) for item in data}
    else:
        return data


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize a filename to be safe for filesystem operations.
    
    Args:
        filename: The filename to sanitize.
        max_length: Maximum length for the filename.
        
    Returns:
        A sanitized filename.
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    
    # Truncate if too long
    if len(filename) > max_length:
        # Keep extension if present
        parts = filename.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) <= 10:  # Reasonable extension length
            name, ext = parts
            max_name_length = max_length - len(ext) - 1
            filename = name[:max_name_length] + '.' + ext
        else:
            filename = filename[:max_length]
    
    # Default name if empty
    if not filename:
        filename = 'unnamed'
    
    return filename


def calculate_hash(content: Union[str, bytes]) -> str:
    """Calculate SHA-256 hash of content.
    
    Args:
        content: The content to hash.
        
    Returns:
        Hexadecimal hash string.
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def merge_dicts(dict1: Dict[Any, Any], dict2: Dict[Any, Any], deep: bool = True) -> Dict[Any, Any]:
    """Merge two dictionaries.
    
    Args:
        dict1: First dictionary.
        dict2: Second dictionary (values take precedence).
        deep: Whether to perform deep merge for nested dicts.
        
    Returns:
        Merged dictionary.
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if deep and key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, deep=True)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict[Any, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten.
        parent_key: Parent key for recursion.
        sep: Separator for nested keys.
        
    Returns:
        Flattened dictionary.
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def parse_date_range(start: Union[str, datetime], end: Union[str, datetime]) -> tuple[datetime, datetime]:
    """Parse and validate a date range.
    
    Args:
        start: Start date (string or datetime).
        end: End date (string or datetime).
        
    Returns:
        Tuple of (start_datetime, end_datetime).
        
    Raises:
        ValueError: If dates are invalid or end is before start.
    """
    if isinstance(start, str):
        start = datetime.fromisoformat(start)
    if isinstance(end, str):
        end = datetime.fromisoformat(end)
    
    if end < start:
        raise ValueError(f"End date {end} is before start date {start}")
    
    return start, end


def format_timedelta(td: timedelta) -> str:
    """Format a timedelta into a human-readable string.
    
    Args:
        td: Timedelta to format.
        
    Returns:
        Human-readable string.
    """
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return ', '.join(parts)


def truncate_string(s: str, max_length: int, suffix: str = '...') -> str:
    """Truncate a string to a maximum length.
    
    Args:
        s: String to truncate.
        max_length: Maximum length.
        suffix: Suffix to append if truncated.
        
    Returns:
        Truncated string.
    """
    if len(s) <= max_length:
        return s
    
    if max_length <= len(suffix):
        return suffix[:max_length]
    
    return s[:max_length - len(suffix)] + suffix


def normalize_text(text: str) -> str:
    """Normalize text for comparison or searching.
    
    Args:
        text: Text to normalize.
        
    Returns:
        Normalized text.
    """
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove punctuation for searching
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Remove extra whitespace again
    text = ' '.join(text.split())
    
    return text.strip()


def extract_keywords(text: str, min_length: int = 3) -> Set[str]:
    """Extract keywords from text.
    
    Args:
        text: Text to extract keywords from.
        min_length: Minimum keyword length.
        
    Returns:
        Set of keywords.
    """
    # Normalize text
    normalized = normalize_text(text)
    
    # Split into words
    words = normalized.split()
    
    # Filter by length and remove common stop words
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'with', 'was', 'were',
        'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should',
        'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
        'from', 'into', 'over', 'under', 'between', 'through', 'during',
        'before', 'after', 'above', 'below', 'when', 'where', 'what', 'which',
        'who', 'whom', 'whose', 'why', 'how', 'all', 'each', 'every', 'some',
        'any', 'few', 'more', 'most', 'other', 'another', 'such', 'only',
        'own', 'same', 'than', 'too', 'very', 'just', 'now'
    }
    
    keywords = {
        word for word in words
        if len(word) >= min_length and word not in stop_words
    }
    
    return keywords


def paginate_list(items: List[Any], page: int = 1, page_size: int = 10) -> Dict[str, Any]:
    """Paginate a list of items.
    
    Args:
        items: List of items to paginate.
        page: Page number (1-indexed).
        page_size: Number of items per page.
        
    Returns:
        Dictionary with pagination info and items.
    """
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size
    
    # Validate page number
    page = max(1, min(page, total_pages or 1))
    
    start_index = (page - 1) * page_size
    end_index = min(start_index + page_size, total_items)
    
    return {
        'items': items[start_index:end_index],
        'page': page,
        'page_size': page_size,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_previous': page > 1,
        'has_next': page < total_pages,
        'start_index': start_index + 1 if total_items > 0 else 0,
        'end_index': end_index
    }


def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safely load JSON data with a default fallback.
    
    Args:
        data: JSON string to parse.
        default: Default value if parsing fails.
        
    Returns:
        Parsed JSON or default value.
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def ensure_list(value: Union[Any, List[Any]]) -> List[Any]:
    """Ensure a value is a list.
    
    Args:
        value: Value to ensure is a list.
        
    Returns:
        Value as a list.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (set, tuple)):
        return list(value)
    return [value]


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk.
        chunk_size: Size of each chunk.
        
    Returns:
        List of chunks.
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]