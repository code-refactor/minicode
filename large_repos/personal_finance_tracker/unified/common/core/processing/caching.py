"""
Caching utilities for financial data processing.

This module provides caching mechanisms to improve performance
by storing frequently accessed data and computed results.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Union, List, Tuple
from dataclasses import dataclass, field
import datetime
from datetime import timedelta
import json
import pickle
import hashlib
import threading
import time
from functools import wraps
import logging

# Factory function for default datetime
def _now():
    return datetime.datetime.now()

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    key: str
    value: Any
    created_at: datetime.datetime
    expires_at: Optional[datetime.datetime] = None
    access_count: int = 0
    last_accessed: datetime.datetime = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.datetime.now() > self.expires_at
    
    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.datetime.now()
    
    def size_estimate(self) -> int:
        """Estimate memory size of the cache entry."""
        try:
            return len(pickle.dumps(self.value))
        except:
            return len(str(self.value))


class CacheStats:
    """Statistics for cache performance monitoring."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0
        self.start_time = datetime.datetime.now()
        self._lock = threading.Lock()
    
    def record_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self.hits += 1
    
    def record_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self.misses += 1
    
    def record_set(self) -> None:
        """Record a cache set operation."""
        with self._lock:
            self.sets += 1
    
    def record_delete(self) -> None:
        """Record a cache delete operation."""
        with self._lock:
            self.deletes += 1
    
    def record_eviction(self) -> None:
        """Record a cache eviction."""
        with self._lock:
            self.evictions += 1
    
    @property
    def total_requests(self) -> int:
        """Total cache requests."""
        return self.hits + self.misses
    
    @property
    def hit_rate(self) -> float:
        """Cache hit rate as percentage."""
        total = self.total_requests
        return (self.hits / total * 100) if total > 0 else 0.0
    
    @property
    def uptime(self) -> timedelta:
        """Cache uptime."""
        return datetime.datetime.now() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "total_requests": self.total_requests,
            "hit_rate_percent": self.hit_rate,
            "uptime_seconds": self.uptime.total_seconds()
        }


class Cache(ABC):
    """Abstract base class for cache implementations."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL in seconds."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache. Returns True if key existed."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    def keys(self) -> List[str]:
        """Get list of all keys in cache."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get number of entries in cache."""
        pass


class InMemoryCache(Cache):
    """
    In-memory cache implementation with TTL and LRU eviction.
    
    Thread-safe cache suitable for single-process applications.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[int] = None,
        cleanup_interval: int = 300  # 5 minutes
    ):
        """
        Initialize in-memory cache.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default TTL in seconds
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self._lock = threading.RLock()
        self._stats = CacheStats()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.record_miss()
                return None
            
            if entry.is_expired():
                self._remove_entry(key)
                self._stats.record_miss()
                return None
            
            # Update access statistics
            entry.touch()
            
            # Move to end of access order (most recently used)
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            self._stats.record_hit()
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        with self._lock:
            # Calculate expiration time
            expires_at = None
            if ttl is not None:
                expires_at = datetime.datetime.now() + timedelta(seconds=ttl)
            elif self.default_ttl is not None:
                expires_at = datetime.datetime.now() + timedelta(seconds=self.default_ttl)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.datetime.now(),
                expires_at=expires_at
            )
            
            # Check if we need to evict entries
            if key not in self._cache and len(self._cache) >= self.max_size:
                self._evict_lru()
            
            # Add/update entry
            self._cache[key] = entry
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            self._stats.record_set()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                self._stats.record_delete()
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            
            if entry.is_expired():
                self._remove_entry(key)
                return False
            
            return True
    
    def keys(self) -> List[str]:
        """Get list of all keys in cache."""
        with self._lock:
            # Remove expired keys first
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                self._remove_entry(key)
            
            return list(self._cache.keys())
    
    def size(self) -> int:
        """Get number of entries in cache."""
        with self._lock:
            return len(self._cache)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get estimated memory usage."""
        with self._lock:
            total_size = sum(entry.size_estimate() for entry in self._cache.values())
            return {
                "total_entries": len(self._cache),
                "estimated_bytes": total_size,
                "estimated_mb": total_size / (1024 * 1024),
                "average_entry_size": total_size / len(self._cache) if self._cache else 0
            }
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_order:
            return
        
        lru_key = self._access_order[0]
        self._remove_entry(lru_key)
        self._stats.record_eviction()
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry from cache and access order."""
        if key in self._cache:
            del self._cache[key]
        
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _cleanup_expired(self) -> None:
        """Background thread to clean up expired entries."""
        while True:
            time.sleep(self.cleanup_interval)
            
            with self._lock:
                expired_keys = [
                    key for key, entry in self._cache.items()
                    if entry.is_expired()
                ]
                
                for key in expired_keys:
                    self._remove_entry(key)
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


class CacheManager:
    """
    Manager for multiple named caches with different configurations.
    
    Provides a centralized way to manage different cache instances
    for different types of data or use cases.
    """
    
    def __init__(self):
        self._caches: Dict[str, Cache] = {}
        self._lock = threading.Lock()
    
    def create_cache(
        self,
        name: str,
        cache_type: str = "memory",
        **kwargs
    ) -> Cache:
        """
        Create a new named cache.
        
        Args:
            name: Cache name
            cache_type: Type of cache ("memory" is currently supported)
            **kwargs: Cache-specific configuration
            
        Returns:
            Cache instance
        """
        with self._lock:
            if name in self._caches:
                raise ValueError(f"Cache '{name}' already exists")
            
            if cache_type == "memory":
                cache = InMemoryCache(**kwargs)
            else:
                raise ValueError(f"Unsupported cache type: {cache_type}")
            
            self._caches[name] = cache
            return cache
    
    def get_cache(self, name: str) -> Optional[Cache]:
        """Get cache by name."""
        return self._caches.get(name)
    
    def delete_cache(self, name: str) -> bool:
        """Delete cache by name."""
        with self._lock:
            if name in self._caches:
                del self._caches[name]
                return True
            return False
    
    def list_caches(self) -> List[str]:
        """Get list of cache names."""
        return list(self._caches.keys())
    
    def clear_all(self) -> None:
        """Clear all caches."""
        for cache in self._caches.values():
            cache.clear()
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches."""
        stats = {}
        for name, cache in self._caches.items():
            if hasattr(cache, 'get_stats'):
                stats[name] = cache.get_stats().to_dict()
            else:
                stats[name] = {"size": cache.size()}
        return stats


# Global cache manager instance
_global_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    return _global_cache_manager


def cached(
    cache_name: str = "default",
    ttl: Optional[int] = None,
    key_func: Optional[Callable[..., str]] = None
) -> Callable:
    """
    Decorator for caching function results.
    
    Args:
        cache_name: Name of cache to use
        ttl: TTL for cached values in seconds
        key_func: Function to generate cache key from arguments
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        # Ensure cache exists
        cache_manager = get_cache_manager()
        cache = cache_manager.get_cache(cache_name)
        if cache is None:
            cache = cache_manager.create_cache(cache_name)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_key_from_dict(data: Dict[str, Any]) -> str:
    """
    Generate a cache key from a dictionary.
    
    Args:
        data: Dictionary to generate key from
        
    Returns:
        Cache key string
    """
    # Sort keys for consistent ordering
    sorted_items = sorted(data.items())
    key_string = json.dumps(sorted_items, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()


class MemoizedCalculation:
    """
    Utility class for memoizing expensive calculations.
    
    Useful for financial calculations that are expensive to compute
    but frequently accessed with the same parameters.
    """
    
    def __init__(self, cache_name: str = "calculations", ttl: int = 3600):
        """
        Initialize memoized calculation.
        
        Args:
            cache_name: Name of cache to use
            ttl: TTL for cached results in seconds
        """
        self.cache_name = cache_name
        self.ttl = ttl
        
        # Ensure cache exists
        cache_manager = get_cache_manager()
        self.cache = cache_manager.get_cache(cache_name)
        if self.cache is None:
            self.cache = cache_manager.create_cache(cache_name, max_size=10000)
    
    def memoize(self, func: Callable) -> Callable:
        """
        Decorator to memoize a function.
        
        Args:
            func: Function to memoize
            
        Returns:
            Memoized function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try cache first
            result = self.cache.get(cache_key)
            if result is not None:
                return result
            
            # Calculate and cache
            result = func(*args, **kwargs)
            self.cache.set(cache_key, result, self.ttl)
            
            return result
        
        return wrapper


# Pre-configured memoization decorators
calculation_cache = MemoizedCalculation("financial_calculations", ttl=3600)
memoized_calculation = calculation_cache.memoize

# Example usage functions
@memoized_calculation
def expensive_portfolio_calculation(
    holdings: List[Dict[str, Any]],
    market_data: Dict[str, float]
) -> Dict[str, Any]:
    """Example of an expensive portfolio calculation that benefits from caching."""
    # This would contain complex portfolio analysis logic
    # For now, just a placeholder
    time.sleep(0.1)  # Simulate expensive calculation
    
    total_value = sum(
        holding.get("quantity", 0) * market_data.get(holding.get("symbol", ""), 0)
        for holding in holdings
    )
    
    return {
        "total_value": total_value,
        "calculation_time": datetime.datetime.now().isoformat()
    }


def setup_default_caches() -> None:
    """Set up default caches for common use cases."""
    cache_manager = get_cache_manager()
    
    # Cache for financial calculations
    if not cache_manager.get_cache("calculations"):
        cache_manager.create_cache(
            "calculations",
            max_size=1000,
            default_ttl=3600  # 1 hour
        )
    
    # Cache for market data
    if not cache_manager.get_cache("market_data"):
        cache_manager.create_cache(
            "market_data",
            max_size=500,
            default_ttl=300  # 5 minutes
        )
    
    # Cache for user sessions
    if not cache_manager.get_cache("sessions"):
        cache_manager.create_cache(
            "sessions",
            max_size=100,
            default_ttl=1800  # 30 minutes
        )