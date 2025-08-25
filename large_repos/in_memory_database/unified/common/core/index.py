"""Indexing abstractions for the unified library."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
import bisect
import hashlib


@dataclass
class IndexEntry:
    """Entry in an index."""
    key: Any
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class Index(ABC):
    """Abstract base class for indexes."""
    
    @abstractmethod
    def add(self, key: Any, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add an entry to the index."""
        pass
    
    @abstractmethod
    def remove(self, key: Any) -> bool:
        """Remove an entry from the index."""
        pass
    
    @abstractmethod
    def search(self, query: Any, limit: Optional[int] = None,
              filter_fn: Optional[Callable] = None) -> List[Tuple[float, Any]]:
        """Search the index.
        
        Returns list of (score, value) tuples.
        """
        pass
    
    @abstractmethod
    def get_metadata(self, key: Any) -> Optional[Dict[str, Any]]:
        """Get metadata for a key."""
        pass
    
    @abstractmethod
    def rebuild(self) -> None:
        """Rebuild the index from scratch."""
        pass
    
    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from the index."""
        pass


class HashIndex(Index):
    """Hash-based index for exact matches."""
    
    def __init__(self, name: str = "hash_index"):
        """Initialize hash index."""
        self.name = name
        self._index: Dict[Any, IndexEntry] = {}
        self._lock = RLock()
        self._stats = {
            'adds': 0,
            'removes': 0,
            'searches': 0,
            'hits': 0,
            'misses': 0
        }
    
    def add(self, key: Any, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add an entry to the index."""
        with self._lock:
            entry = IndexEntry(key=key, value=value, metadata=metadata or {})
            self._index[key] = entry
            self._stats['adds'] += 1
    
    def remove(self, key: Any) -> bool:
        """Remove an entry from the index."""
        with self._lock:
            if key in self._index:
                del self._index[key]
                self._stats['removes'] += 1
                return True
            return False
    
    def search(self, query: Any, limit: Optional[int] = None,
              filter_fn: Optional[Callable] = None) -> List[Tuple[float, Any]]:
        """Search for exact match."""
        with self._lock:
            self._stats['searches'] += 1
            
            if query in self._index:
                entry = self._index[query]
                
                # Apply filter if provided
                if filter_fn and not filter_fn(entry.value, entry.metadata):
                    self._stats['misses'] += 1
                    return []
                
                self._stats['hits'] += 1
                return [(1.0, entry.value)]  # Perfect match score
            
            self._stats['misses'] += 1
            return []
    
    def get(self, key: Any) -> Optional[Any]:
        """Get value by key."""
        with self._lock:
            entry = self._index.get(key)
            return entry.value if entry else None
    
    def get_metadata(self, key: Any) -> Optional[Dict[str, Any]]:
        """Get metadata for a key."""
        with self._lock:
            entry = self._index.get(key)
            return entry.metadata if entry else None
    
    def rebuild(self) -> None:
        """No-op for hash index."""
        pass
    
    def stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self._lock:
            return {
                **self._stats,
                'size': len(self._index),
                'hit_rate': self._stats['hits'] / max(1, self._stats['searches'])
            }
    
    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._index.clear()
            self._stats = {
                'adds': 0,
                'removes': 0,
                'searches': 0,
                'hits': 0,
                'misses': 0
            }
    
    def keys(self) -> List[Any]:
        """Get all keys in the index."""
        with self._lock:
            return list(self._index.keys())
    
    def values(self) -> List[Any]:
        """Get all values in the index."""
        with self._lock:
            return [entry.value for entry in self._index.values()]


class BTreeIndex(Index):
    """B-tree based index for range queries."""
    
    def __init__(self, name: str = "btree_index", order: int = 100):
        """Initialize B-tree index.
        
        Args:
            name: Name of the index
            order: Maximum number of keys in a node
        """
        self.name = name
        self.order = order
        self._keys: List[Any] = []
        self._entries: Dict[Any, IndexEntry] = {}
        self._lock = RLock()
        self._stats = {
            'adds': 0,
            'removes': 0,
            'searches': 0,
            'range_queries': 0
        }
    
    def add(self, key: Any, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add an entry to the index."""
        with self._lock:
            entry = IndexEntry(key=key, value=value, metadata=metadata or {})
            
            # Remove old key if exists
            if key in self._entries:
                self._keys.remove(key)
            
            # Insert key in sorted position
            bisect.insort(self._keys, key)
            self._entries[key] = entry
            self._stats['adds'] += 1
    
    def remove(self, key: Any) -> bool:
        """Remove an entry from the index."""
        with self._lock:
            if key in self._entries:
                self._keys.remove(key)
                del self._entries[key]
                self._stats['removes'] += 1
                return True
            return False
    
    def search(self, query: Any, limit: Optional[int] = None,
              filter_fn: Optional[Callable] = None) -> List[Tuple[float, Any]]:
        """Search for exact match or use as starting point for range query."""
        with self._lock:
            self._stats['searches'] += 1
            
            if query in self._entries:
                entry = self._entries[query]
                
                if filter_fn and not filter_fn(entry.value, entry.metadata):
                    return []
                
                return [(1.0, entry.value)]
            
            return []
    
    def range_search(self, min_key: Optional[Any] = None, max_key: Optional[Any] = None,
                    limit: Optional[int] = None,
                    filter_fn: Optional[Callable] = None) -> List[Tuple[Any, Any]]:
        """Perform range search.
        
        Returns list of (key, value) tuples.
        """
        with self._lock:
            self._stats['range_queries'] += 1
            
            # Find range boundaries
            if min_key is None:
                start_idx = 0
            else:
                start_idx = bisect.bisect_left(self._keys, min_key)
            
            if max_key is None:
                end_idx = len(self._keys)
            else:
                end_idx = bisect.bisect_right(self._keys, max_key)
            
            # Collect results
            results = []
            for i in range(start_idx, end_idx):
                key = self._keys[i]
                entry = self._entries[key]
                
                if filter_fn and not filter_fn(entry.value, entry.metadata):
                    continue
                
                results.append((key, entry.value))
                
                if limit and len(results) >= limit:
                    break
            
            return results
    
    def get_metadata(self, key: Any) -> Optional[Dict[str, Any]]:
        """Get metadata for a key."""
        with self._lock:
            entry = self._entries.get(key)
            return entry.metadata if entry else None
    
    def rebuild(self) -> None:
        """Rebuild the sorted key list."""
        with self._lock:
            self._keys.sort()
    
    def stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self._lock:
            return {
                **self._stats,
                'size': len(self._entries),
                'depth': self._estimate_depth()
            }
    
    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._keys.clear()
            self._entries.clear()
            self._stats = {
                'adds': 0,
                'removes': 0,
                'searches': 0,
                'range_queries': 0
            }
    
    def _estimate_depth(self) -> int:
        """Estimate B-tree depth based on number of keys."""
        if not self._keys:
            return 0
        
        import math
        # Rough estimate: log_order(n)
        return max(1, int(math.log(len(self._keys), max(2, self.order // 2))))


class CompositeIndex(Index):
    """Composite index combining multiple fields."""
    
    def __init__(self, name: str = "composite_index", fields: List[str] = None):
        """Initialize composite index.
        
        Args:
            name: Name of the index
            fields: List of field names to index
        """
        self.name = name
        self.fields = fields or []
        self._index: Dict[Tuple, List[IndexEntry]] = {}
        self._lock = RLock()
    
    def add(self, key: Any, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add an entry to the index."""
        with self._lock:
            # Extract composite key from value
            composite_key = self._extract_composite_key(value)
            
            if composite_key not in self._index:
                self._index[composite_key] = []
            
            entry = IndexEntry(key=key, value=value, metadata=metadata or {})
            self._index[composite_key].append(entry)
    
    def remove(self, key: Any) -> bool:
        """Remove entries with the given primary key."""
        with self._lock:
            removed = False
            
            # Need to search all composite keys
            for comp_key in list(self._index.keys()):
                entries = self._index[comp_key]
                filtered = [e for e in entries if e.key != key]
                
                if len(filtered) < len(entries):
                    removed = True
                    
                    if filtered:
                        self._index[comp_key] = filtered
                    else:
                        del self._index[comp_key]
            
            return removed
    
    def search(self, query: Any, limit: Optional[int] = None,
              filter_fn: Optional[Callable] = None) -> List[Tuple[float, Any]]:
        """Search by composite key."""
        with self._lock:
            composite_key = self._extract_composite_key(query)
            
            if composite_key not in self._index:
                return []
            
            results = []
            for entry in self._index[composite_key]:
                if filter_fn and not filter_fn(entry.value, entry.metadata):
                    continue
                
                results.append((1.0, entry.value))
                
                if limit and len(results) >= limit:
                    break
            
            return results
    
    def get_metadata(self, key: Any) -> Optional[Dict[str, Any]]:
        """Get metadata for a key."""
        with self._lock:
            for entries in self._index.values():
                for entry in entries:
                    if entry.key == key:
                        return entry.metadata
            return None
    
    def rebuild(self) -> None:
        """No-op for composite index."""
        pass
    
    def stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self._lock:
            total_entries = sum(len(entries) for entries in self._index.values())
            return {
                'composite_keys': len(self._index),
                'total_entries': total_entries,
                'fields': self.fields
            }
    
    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._index.clear()
    
    def _extract_composite_key(self, value: Any) -> Tuple:
        """Extract composite key from value."""
        if not self.fields:
            return (value,)
        
        key_parts = []
        for field in self.fields:
            if isinstance(value, dict):
                key_parts.append(value.get(field))
            elif hasattr(value, field):
                key_parts.append(getattr(value, field))
            else:
                key_parts.append(None)
        
        return tuple(key_parts)