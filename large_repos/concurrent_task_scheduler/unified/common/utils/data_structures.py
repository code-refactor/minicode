"""Data structures for the unified task scheduling library."""

from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Generic
import threading
from collections import deque, defaultdict
import heapq
from datetime import datetime


T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class ThreadSafeDict(Generic[K, V]):
    """Thread-safe dictionary wrapper."""
    
    def __init__(self):
        self._dict: Dict[K, V] = {}
        self._lock = threading.RLock()
    
    def __getitem__(self, key: K) -> V:
        with self._lock:
            return self._dict[key]
    
    def __setitem__(self, key: K, value: V):
        with self._lock:
            self._dict[key] = value
    
    def __delitem__(self, key: K):
        with self._lock:
            del self._dict[key]
    
    def __contains__(self, key: K) -> bool:
        with self._lock:
            return key in self._dict
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._dict)
    
    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        with self._lock:
            return self._dict.get(key, default)
    
    def setdefault(self, key: K, default: V) -> V:
        with self._lock:
            return self._dict.setdefault(key, default)
    
    def pop(self, key: K, default: Optional[V] = None) -> Optional[V]:
        with self._lock:
            return self._dict.pop(key, default)
    
    def keys(self):
        with self._lock:
            return list(self._dict.keys())
    
    def values(self):
        with self._lock:
            return list(self._dict.values())
    
    def items(self):
        with self._lock:
            return list(self._dict.items())
    
    def clear(self):
        with self._lock:
            self._dict.clear()
    
    def copy(self) -> Dict[K, V]:
        with self._lock:
            return self._dict.copy()


class ThreadSafeSet(Generic[T]):
    """Thread-safe set wrapper."""
    
    def __init__(self, initial: Optional[Set[T]] = None):
        self._set: Set[T] = set(initial or [])
        self._lock = threading.RLock()
    
    def add(self, item: T):
        with self._lock:
            self._set.add(item)
    
    def remove(self, item: T):
        with self._lock:
            self._set.remove(item)
    
    def discard(self, item: T):
        with self._lock:
            self._set.discard(item)
    
    def __contains__(self, item: T) -> bool:
        with self._lock:
            return item in self._set
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._set)
    
    def copy(self) -> Set[T]:
        with self._lock:
            return self._set.copy()
    
    def clear(self):
        with self._lock:
            self._set.clear()


class LRUCache(Generic[K, V]):
    """Thread-safe LRU cache implementation."""
    
    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._cache: Dict[K, V] = {}
        self._access_order: deque = deque()
        self._lock = threading.RLock()
    
    def get(self, key: K) -> Optional[V]:
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            return None
    
    def put(self, key: K, value: V):
        with self._lock:
            if key in self._cache:
                # Update existing
                self._cache[key] = value
                self._access_order.remove(key)
                self._access_order.append(key)
            else:
                # Add new
                if len(self._cache) >= self.max_size:
                    # Remove least recently used
                    oldest = self._access_order.popleft()
                    del self._cache[oldest]
                
                self._cache[key] = value
                self._access_order.append(key)
    
    def __contains__(self, key: K) -> bool:
        with self._lock:
            return key in self._cache
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)
    
    def clear(self):
        with self._lock:
            self._cache.clear()
            self._access_order.clear()


class PriorityQueue(Generic[T]):
    """Thread-safe priority queue."""
    
    def __init__(self):
        self._heap: List[Tuple[float, int, T]] = []
        self._counter = 0  # For stable sorting
        self._lock = threading.RLock()
    
    def put(self, item: T, priority: float):
        with self._lock:
            # Use negative priority for max heap behavior
            heapq.heappush(self._heap, (-priority, self._counter, item))
            self._counter += 1
    
    def get(self) -> Optional[T]:
        with self._lock:
            if self._heap:
                _, _, item = heapq.heappop(self._heap)
                return item
            return None
    
    def peek(self) -> Optional[T]:
        with self._lock:
            if self._heap:
                return self._heap[0][2]
            return None
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)
    
    def empty(self) -> bool:
        with self._lock:
            return len(self._heap) == 0


class CircularBuffer(Generic[T]):
    """Thread-safe circular buffer with fixed capacity."""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._buffer: List[Optional[T]] = [None] * capacity
        self._head = 0
        self._size = 0
        self._lock = threading.RLock()
    
    def append(self, item: T):
        with self._lock:
            self._buffer[self._head] = item
            self._head = (self._head + 1) % self.capacity
            if self._size < self.capacity:
                self._size += 1
    
    def get_all(self) -> List[T]:
        with self._lock:
            if self._size == 0:
                return []
            
            result = []
            start = (self._head - self._size) % self.capacity
            
            for i in range(self._size):
                idx = (start + i) % self.capacity
                if self._buffer[idx] is not None:
                    result.append(self._buffer[idx])
            
            return result
    
    def __len__(self) -> int:
        with self._lock:
            return self._size
    
    def is_full(self) -> bool:
        with self._lock:
            return self._size == self.capacity


class TimeSeriesBuffer:
    """Buffer for storing time series data with automatic cleanup."""
    
    def __init__(self, max_age_seconds: float = 3600, max_size: int = 10000):
        self.max_age_seconds = max_age_seconds
        self.max_size = max_size
        self._data: List[Tuple[datetime, Any]] = []
        self._lock = threading.RLock()
    
    def add(self, value: Any, timestamp: Optional[datetime] = None):
        if timestamp is None:
            timestamp = datetime.now()
        
        with self._lock:
            self._data.append((timestamp, value))
            self._cleanup()
    
    def get_recent(self, seconds: Optional[float] = None) -> List[Tuple[datetime, Any]]:
        if seconds is None:
            seconds = self.max_age_seconds
        
        cutoff = datetime.now().timestamp() - seconds
        
        with self._lock:
            return [(ts, val) for ts, val in self._data 
                   if ts.timestamp() >= cutoff]
    
    def get_all(self) -> List[Tuple[datetime, Any]]:
        with self._lock:
            return self._data.copy()
    
    def _cleanup(self):
        """Remove old data points."""
        now = datetime.now()
        cutoff_time = now.timestamp() - self.max_age_seconds
        
        # Remove old entries
        self._data = [(ts, val) for ts, val in self._data 
                     if ts.timestamp() >= cutoff_time]
        
        # Enforce size limit
        if len(self._data) > self.max_size:
            self._data = self._data[-self.max_size:]


class BloomFilter:
    """Simple Bloom filter for fast membership testing."""
    
    def __init__(self, capacity: int = 1000, error_rate: float = 0.1):
        import math
        
        self.capacity = capacity
        self.error_rate = error_rate
        
        # Calculate optimal bit array size and number of hash functions
        self.bit_size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        self.hash_count = int(self.bit_size * math.log(2) / capacity)
        
        self.bit_array = [False] * self.bit_size
        self._lock = threading.RLock()
    
    def _hash(self, item: str, seed: int) -> int:
        """Simple hash function."""
        hash_value = seed
        for char in item:
            hash_value = ((hash_value * 31) + ord(char)) % self.bit_size
        return hash_value
    
    def add(self, item: str):
        with self._lock:
            for i in range(self.hash_count):
                index = self._hash(item, i)
                self.bit_array[index] = True
    
    def __contains__(self, item: str) -> bool:
        with self._lock:
            for i in range(self.hash_count):
                index = self._hash(item, i)
                if not self.bit_array[index]:
                    return False
            return True


class Trie:
    """Trie data structure for efficient string prefix matching."""
    
    class TrieNode:
        def __init__(self):
            self.children: Dict[str, 'Trie.TrieNode'] = {}
            self.is_end_of_word = False
            self.value: Optional[Any] = None
    
    def __init__(self):
        self.root = self.TrieNode()
        self._lock = threading.RLock()
    
    def insert(self, key: str, value: Any = None):
        with self._lock:
            node = self.root
            for char in key:
                if char not in node.children:
                    node.children[char] = self.TrieNode()
                node = node.children[char]
            
            node.is_end_of_word = True
            node.value = value
    
    def search(self, key: str) -> Optional[Any]:
        with self._lock:
            node = self._find_node(key)
            if node and node.is_end_of_word:
                return node.value
            return None
    
    def starts_with(self, prefix: str) -> List[Tuple[str, Any]]:
        with self._lock:
            node = self._find_node(prefix)
            if not node:
                return []
            
            results = []
            self._collect_words(node, prefix, results)
            return results
    
    def _find_node(self, key: str) -> Optional[TrieNode]:
        node = self.root
        for char in key:
            if char not in node.children:
                return None
            node = node.children[char]
        return node
    
    def _collect_words(self, node: TrieNode, prefix: str, results: List[Tuple[str, Any]]):
        if node.is_end_of_word:
            results.append((prefix, node.value))
        
        for char, child_node in node.children.items():
            self._collect_words(child_node, prefix + char, results)


class CountingDict(defaultdict):
    """Dictionary that automatically counts occurrences."""
    
    def __init__(self):
        super().__init__(int)
        self._lock = threading.RLock()
    
    def increment(self, key: Any, amount: int = 1):
        with self._lock:
            self[key] += amount
    
    def decrement(self, key: Any, amount: int = 1):
        with self._lock:
            self[key] = max(0, self[key] - amount)
    
    def most_common(self, n: Optional[int] = None) -> List[Tuple[Any, int]]:
        with self._lock:
            sorted_items = sorted(self.items(), key=lambda x: x[1], reverse=True)
            return sorted_items[:n] if n else sorted_items