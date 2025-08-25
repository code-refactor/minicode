"""
Caching framework for the File System Analyzer unified library.

This module provides flexible caching mechanisms with multiple backends
and automatic cleanup capabilities.
"""

import os
import json
import pickle
import hashlib
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass

from ..core.types import FilePath
from .crypto import hash_data, HashAlgorithm

logger = logging.getLogger(__name__)

T = TypeVar('T')
K = TypeVar('K')


@dataclass
class CacheEntry(Generic[T]):
    """Represents a cache entry with metadata."""
    key: str
    value: T
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.metadata is None:
            self.metadata = {}
            
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > (self.created_at + timedelta(seconds=self.ttl_seconds))
        
    @property
    def age_seconds(self) -> float:
        """Get the age of the cache entry in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
        
    def touch(self) -> None:
        """Update access time and increment access count."""
        self.accessed_at = datetime.now()
        self.access_count += 1


class CacheBackend(ABC, Generic[K, T]):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: K) -> Optional[CacheEntry[T]]:
        """Get a cache entry by key."""
        pass
        
    @abstractmethod
    def set(self, key: K, value: T, ttl_seconds: Optional[int] = None, 
           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set a cache entry."""
        pass
        
    @abstractmethod
    def delete(self, key: K) -> bool:
        """Delete a cache entry by key."""
        pass
        
    @abstractmethod
    def exists(self, key: K) -> bool:
        """Check if a key exists in the cache."""
        pass
        
    @abstractmethod
    def clear(self) -> int:
        """Clear all cache entries and return the number cleared."""
        pass
        
    @abstractmethod
    def keys(self) -> List[K]:
        """Get all cache keys."""
        pass
        
    @abstractmethod
    def size(self) -> int:
        """Get the number of cache entries."""
        pass
        
    @abstractmethod
    def cleanup_expired(self) -> int:
        """Remove expired entries and return the number removed."""
        pass


class MemoryCacheBackend(CacheBackend[str, T]):
    """In-memory cache backend with thread safety."""
    
    def __init__(self, max_size: Optional[int] = None):
        """
        Initialize the memory cache.
        
        Args:
            max_size: Maximum number of entries (None for unlimited)
        """
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[CacheEntry[T]]:
        """Get a cache entry by key."""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                if entry.is_expired:
                    del self._cache[key]
                    return None
                entry.touch()
            return entry
            
    def set(self, key: str, value: T, ttl_seconds: Optional[int] = None,
           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set a cache entry."""
        with self._lock:
            # If at max size, remove oldest entry
            if self.max_size and len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
                
            now = datetime.now()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                accessed_at=now,
                ttl_seconds=ttl_seconds,
                metadata=metadata or {}
            )
            self._cache[key] = entry
            return True
            
    def delete(self, key: str) -> bool:
        """Delete a cache entry by key."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
            
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry and entry.is_expired:
                del self._cache[key]
                return False
            return entry is not None
            
    def clear(self) -> int:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
            
    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())
            
    def size(self) -> int:
        """Get the number of cache entries."""
        with self._lock:
            return len(self._cache)
            
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
            
    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry."""
        if not self._cache:
            return
            
        # Find the oldest entry by creation time
        oldest_key = min(self._cache.keys(), 
                        key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_entries = len(self._cache)
            total_accesses = sum(entry.access_count for entry in self._cache.values())
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired)
            
            return {
                "total_entries": total_entries,
                "expired_entries": expired_count,
                "total_accesses": total_accesses,
                "max_size": self.max_size,
                "hit_rate": None  # Would need to track misses to calculate
            }


class FileCacheBackend(CacheBackend[str, T]):
    """File-based cache backend with persistence."""
    
    def __init__(self, cache_dir: FilePath, serializer: str = "json"):
        """
        Initialize the file cache.
        
        Args:
            cache_dir: Directory to store cache files
            serializer: Serialization method ('json' or 'pickle')
        """
        self.cache_dir = Path(cache_dir)
        self.serializer = serializer
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Use hash of key to avoid filesystem issues
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
        
    def _serialize(self, entry: CacheEntry[T]) -> bytes:
        """Serialize a cache entry."""
        data = {
            "key": entry.key,
            "value": entry.value,
            "created_at": entry.created_at.isoformat(),
            "accessed_at": entry.accessed_at.isoformat(),
            "access_count": entry.access_count,
            "ttl_seconds": entry.ttl_seconds,
            "metadata": entry.metadata
        }
        
        if self.serializer == "json":
            return json.dumps(data, default=str).encode()
        elif self.serializer == "pickle":
            return pickle.dumps(data)
        else:
            raise ValueError(f"Unknown serializer: {self.serializer}")
            
    def _deserialize(self, data: bytes) -> CacheEntry[T]:
        """Deserialize a cache entry."""
        if self.serializer == "json":
            obj = json.loads(data.decode())
        elif self.serializer == "pickle":
            obj = pickle.loads(data)
        else:
            raise ValueError(f"Unknown serializer: {self.serializer}")
            
        return CacheEntry(
            key=obj["key"],
            value=obj["value"],
            created_at=datetime.fromisoformat(obj["created_at"]),
            accessed_at=datetime.fromisoformat(obj["accessed_at"]),
            access_count=obj["access_count"],
            ttl_seconds=obj["ttl_seconds"],
            metadata=obj["metadata"]
        )
        
    def get(self, key: str) -> Optional[CacheEntry[T]]:
        """Get a cache entry by key."""
        cache_path = self._get_cache_path(key)
        
        with self._lock:
            if not cache_path.exists():
                return None
                
            try:
                with open(cache_path, 'rb') as f:
                    entry = self._deserialize(f.read())
                    
                if entry.is_expired:
                    cache_path.unlink()
                    return None
                    
                entry.touch()
                
                # Write back with updated access info
                with open(cache_path, 'wb') as f:
                    f.write(self._serialize(entry))
                    
                return entry
                
            except Exception as e:
                logger.error(f"Error reading cache entry {key}: {e}")
                # Remove corrupted cache file
                try:
                    cache_path.unlink()
                except Exception:
                    pass
                return None
                
    def set(self, key: str, value: T, ttl_seconds: Optional[int] = None,
           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set a cache entry."""
        cache_path = self._get_cache_path(key)
        
        with self._lock:
            try:
                now = datetime.now()
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=now,
                    accessed_at=now,
                    ttl_seconds=ttl_seconds,
                    metadata=metadata or {}
                )
                
                with open(cache_path, 'wb') as f:
                    f.write(self._serialize(entry))
                    
                return True
                
            except Exception as e:
                logger.error(f"Error writing cache entry {key}: {e}")
                return False
                
    def delete(self, key: str) -> bool:
        """Delete a cache entry by key."""
        cache_path = self._get_cache_path(key)
        
        with self._lock:
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    return True
                except Exception as e:
                    logger.error(f"Error deleting cache entry {key}: {e}")
                    return False
            return False
            
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        cache_path = self._get_cache_path(key)
        
        with self._lock:
            if not cache_path.exists():
                return False
                
            # Check if expired
            try:
                with open(cache_path, 'rb') as f:
                    entry = self._deserialize(f.read())
                    
                if entry.is_expired:
                    cache_path.unlink()
                    return False
                    
                return True
                
            except Exception:
                return False
                
    def clear(self) -> int:
        """Clear all cache entries."""
        with self._lock:
            count = 0
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                    count += 1
                except Exception:
                    pass
            return count
            
    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            keys = []
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        entry = self._deserialize(f.read())
                        if not entry.is_expired:
                            keys.append(entry.key)
                        else:
                            cache_file.unlink()  # Clean up expired entry
                except Exception:
                    pass
            return keys
            
    def size(self) -> int:
        """Get the number of cache entries."""
        return len(list(self.cache_dir.glob("*.cache")))
        
    def cleanup_expired(self) -> int:
        """Remove expired cache files."""
        with self._lock:
            count = 0
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        entry = self._deserialize(f.read())
                        
                    if entry.is_expired:
                        cache_file.unlink()
                        count += 1
                        
                except Exception:
                    # Remove corrupted cache files
                    try:
                        cache_file.unlink()
                        count += 1
                    except Exception:
                        pass
            return count


class CacheManager(Generic[T]):
    """High-level cache manager with multiple backends and policies."""
    
    def __init__(
        self,
        backend: CacheBackend[str, T],
        default_ttl: Optional[int] = 3600,
        auto_cleanup_interval: Optional[int] = 300,
        key_prefix: str = "",
        hash_keys: bool = False
    ):
        """
        Initialize the cache manager.
        
        Args:
            backend: Cache backend implementation
            default_ttl: Default TTL in seconds
            auto_cleanup_interval: Auto cleanup interval in seconds (None to disable)
            key_prefix: Prefix for all cache keys
            hash_keys: Whether to hash cache keys
        """
        self.backend = backend
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.hash_keys = hash_keys
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
        
        # Auto cleanup
        if auto_cleanup_interval:
            self._start_auto_cleanup(auto_cleanup_interval)
            
    def _normalize_key(self, key: str) -> str:
        """Normalize a cache key."""
        full_key = f"{self.key_prefix}{key}" if self.key_prefix else key
        
        if self.hash_keys:
            return hash_data(full_key.encode(), HashAlgorithm.SHA256)
        
        return full_key
        
    def get(self, key: str) -> Optional[T]:
        """Get a value from the cache."""
        normalized_key = self._normalize_key(key)
        entry = self.backend.get(normalized_key)
        
        if entry:
            self._stats["hits"] += 1
            return entry.value
        else:
            self._stats["misses"] += 1
            return None
            
    def set(self, key: str, value: T, ttl: Optional[int] = None,
           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set a value in the cache."""
        normalized_key = self._normalize_key(key)
        ttl = ttl if ttl is not None else self.default_ttl
        
        success = self.backend.set(normalized_key, value, ttl, metadata)
        if success:
            self._stats["sets"] += 1
        return success
        
    def get_or_set(self, key: str, factory: Callable[[], T], 
                  ttl: Optional[int] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> T:
        """
        Get a value from cache, or set it using the factory function.
        
        Args:
            key: Cache key
            factory: Function to generate value if not in cache
            ttl: TTL for the cached value
            metadata: Metadata for the cache entry
            
        Returns:
            The cached or newly generated value
        """
        value = self.get(key)
        if value is not None:
            return value
            
        value = factory()
        self.set(key, value, ttl, metadata)
        return value
        
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        normalized_key = self._normalize_key(key)
        success = self.backend.delete(normalized_key)
        if success:
            self._stats["deletes"] += 1
        return success
        
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        normalized_key = self._normalize_key(key)
        return self.backend.exists(normalized_key)
        
    def clear(self) -> int:
        """Clear all cache entries."""
        return self.backend.clear()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests) if total_requests > 0 else 0.0
        
        stats = self._stats.copy()
        stats.update({
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "cache_size": self.backend.size()
        })
        
        # Add backend-specific stats if available
        if hasattr(self.backend, "get_stats"):
            stats["backend_stats"] = self.backend.get_stats()
            
        return stats
        
    def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        return self.backend.cleanup_expired()
        
    def _start_auto_cleanup(self, interval: int) -> None:
        """Start automatic cleanup of expired entries."""
        import threading
        import time
        
        def cleanup_worker():
            while True:
                try:
                    time.sleep(interval)
                    cleaned = self.cleanup_expired()
                    if cleaned > 0:
                        logger.debug(f"Auto cleanup removed {cleaned} expired cache entries")
                except Exception as e:
                    logger.error(f"Error in auto cleanup: {e}")
                    
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()


def cached(
    cache_manager: CacheManager,
    key_func: Optional[Callable[..., str]] = None,
    ttl: Optional[int] = None
):
    """
    Decorator to cache function results.
    
    Args:
        cache_manager: Cache manager instance
        key_func: Function to generate cache key from arguments
        ttl: TTL for cached results
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                import pickle
                key_data = (func.__name__, args, tuple(sorted(kwargs.items())))
                cache_key = hash_data(pickle.dumps(key_data), HashAlgorithm.SHA256)
                
            # Try to get from cache
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
                
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
            
        wrapper._cache_manager = cache_manager
        return wrapper
    return decorator