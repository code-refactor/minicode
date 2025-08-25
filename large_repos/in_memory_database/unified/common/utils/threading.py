"""Thread-safe utilities and context managers for the unified library."""

import threading
import time
import weakref
from typing import Any, Dict, Optional, Callable, TypeVar, Generic, Set, List
from contextlib import contextmanager, AbstractContextManager
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ThreadSafeCache(Generic[T]):
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 256, ttl: Optional[float] = None):
        """Initialize thread-safe cache.
        
        Args:
            max_size: Maximum number of items to cache
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self._cache: Dict[Any, tuple] = {}  # key -> (value, timestamp, access_order)
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.RLock()
        self._access_counter = 0
    
    def get(self, key: Any, default: T = None) -> T:
        """Get item from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        with self._lock:
            if key not in self._cache:
                return default
            
            value, timestamp, _ = self._cache[key]
            
            # Check TTL expiration
            if self._ttl is not None and time.time() - timestamp > self._ttl:
                del self._cache[key]
                return default
            
            # Update access order
            self._access_counter += 1
            self._cache[key] = (value, timestamp, self._access_counter)
            
            return value
    
    def put(self, key: Any, value: T) -> None:
        """Put item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            current_time = time.time()
            self._access_counter += 1
            
            self._cache[key] = (value, current_time, self._access_counter)
            
            # Evict oldest items if cache is full
            if len(self._cache) > self._max_size:
                self._evict_lru()
    
    def remove(self, key: Any) -> bool:
        """Remove item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if item was removed, False if not found
        """
        with self._lock:
            return self._cache.pop(key, None) is not None
    
    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()
            self._access_counter = 0
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def _evict_lru(self) -> None:
        """Evict least recently used items."""
        # Sort by access order and remove oldest
        items_by_access = sorted(
            self._cache.items(),
            key=lambda item: item[1][2]  # access_order
        )
        
        # Remove oldest 25% of items
        num_to_remove = max(1, len(items_by_access) // 4)
        for i in range(num_to_remove):
            key = items_by_access[i][0]
            del self._cache[key]


class RWLock:
    """Reader-Writer lock implementation."""
    
    def __init__(self):
        """Initialize the RW lock."""
        self._readers = 0
        self._writers = 0
        self._read_ready = threading.Condition(threading.RLock())
        self._write_ready = threading.Condition(threading.RLock())
    
    @contextmanager
    def read_lock(self):
        """Acquire read lock."""
        self._acquire_read()
        try:
            yield
        finally:
            self._release_read()
    
    @contextmanager
    def write_lock(self):
        """Acquire write lock."""
        self._acquire_write()
        try:
            yield
        finally:
            self._release_write()
    
    def _acquire_read(self):
        """Acquire read access."""
        with self._read_ready:
            while self._writers > 0:
                self._read_ready.wait()
            self._readers += 1
    
    def _release_read(self):
        """Release read access."""
        with self._read_ready:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()
    
    def _acquire_write(self):
        """Acquire write access."""
        with self._write_ready:
            while self._writers > 0 or self._readers > 0:
                self._write_ready.wait()
            self._writers += 1
    
    def _release_write(self):
        """Release write access."""
        with self._write_ready:
            self._writers -= 1
            self._write_ready.notify_all()
        with self._read_ready:
            self._read_ready.notify_all()


class ThreadPoolManager:
    """Manages thread pools with different configurations."""
    
    def __init__(self):
        """Initialize the thread pool manager."""
        self._pools: Dict[str, ThreadPoolExecutor] = {}
        self._pool_configs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_pool(self, name: str, max_workers: int = 4, 
                   thread_name_prefix: Optional[str] = None) -> ThreadPoolExecutor:
        """Create a named thread pool.
        
        Args:
            name: Pool name
            max_workers: Maximum number of worker threads
            thread_name_prefix: Prefix for thread names
            
        Returns:
            ThreadPoolExecutor instance
        """
        with self._lock:
            if name in self._pools:
                raise ValueError(f"Pool '{name}' already exists")
            
            config = {
                'max_workers': max_workers,
                'thread_name_prefix': thread_name_prefix or f"{name}_worker"
            }
            
            pool = ThreadPoolExecutor(**config)
            self._pools[name] = pool
            self._pool_configs[name] = config
            
            logger.info(f"Created thread pool '{name}' with {max_workers} workers")
            return pool
    
    def get_pool(self, name: str) -> Optional[ThreadPoolExecutor]:
        """Get a thread pool by name.
        
        Args:
            name: Pool name
            
        Returns:
            ThreadPoolExecutor instance or None if not found
        """
        with self._lock:
            return self._pools.get(name)
    
    def submit_to_pool(self, pool_name: str, fn: Callable, *args, **kwargs) -> Optional[Future]:
        """Submit task to named pool.
        
        Args:
            pool_name: Name of the pool
            fn: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Future object or None if pool not found
        """
        pool = self.get_pool(pool_name)
        if pool:
            return pool.submit(fn, *args, **kwargs)
        return None
    
    def map_to_pool(self, pool_name: str, fn: Callable, iterable, timeout: Optional[float] = None):
        """Map function over iterable using named pool.
        
        Args:
            pool_name: Name of the pool
            fn: Function to apply
            iterable: Iterable to process
            timeout: Timeout for each task
            
        Yields:
            Results from function application
        """
        pool = self.get_pool(pool_name)
        if pool:
            yield from pool.map(fn, iterable, timeout=timeout)
    
    def shutdown_pool(self, name: str, wait: bool = True) -> bool:
        """Shutdown a named pool.
        
        Args:
            name: Pool name
            wait: Whether to wait for pending tasks
            
        Returns:
            True if pool was shutdown, False if not found
        """
        with self._lock:
            pool = self._pools.pop(name, None)
            if pool:
                pool.shutdown(wait=wait)
                self._pool_configs.pop(name, None)
                logger.info(f"Shutdown thread pool '{name}'")
                return True
            return False
    
    def shutdown_all(self, wait: bool = True) -> None:
        """Shutdown all pools.
        
        Args:
            wait: Whether to wait for pending tasks
        """
        with self._lock:
            pool_names = list(self._pools.keys())
            for name in pool_names:
                self.shutdown_pool(name, wait=wait)
    
    def get_pool_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status information for a pool.
        
        Args:
            name: Pool name
            
        Returns:
            Dictionary with pool status or None if not found
        """
        with self._lock:
            if name not in self._pools:
                return None
            
            pool = self._pools[name]
            config = self._pool_configs[name]
            
            return {
                'name': name,
                'max_workers': config['max_workers'],
                'thread_name_prefix': config['thread_name_prefix'],
                # Note: ThreadPoolExecutor doesn't expose internal state
                # In a real implementation, you might track submitted/completed tasks
            }
    
    def list_pools(self) -> List[str]:
        """List all pool names.
        
        Returns:
            List of pool names
        """
        with self._lock:
            return list(self._pools.keys())


class AtomicCounter:
    """Thread-safe atomic counter."""
    
    def __init__(self, initial: int = 0):
        """Initialize counter.
        
        Args:
            initial: Initial counter value
        """
        self._value = initial
        self._lock = threading.Lock()
    
    def increment(self, delta: int = 1) -> int:
        """Increment counter and return new value.
        
        Args:
            delta: Amount to increment
            
        Returns:
            New counter value
        """
        with self._lock:
            self._value += delta
            return self._value
    
    def decrement(self, delta: int = 1) -> int:
        """Decrement counter and return new value.
        
        Args:
            delta: Amount to decrement
            
        Returns:
            New counter value
        """
        with self._lock:
            self._value -= delta
            return self._value
    
    def get(self) -> int:
        """Get current counter value.
        
        Returns:
            Current value
        """
        with self._lock:
            return self._value
    
    def set(self, value: int) -> int:
        """Set counter value.
        
        Args:
            value: New value
            
        Returns:
            Previous value
        """
        with self._lock:
            old_value = self._value
            self._value = value
            return old_value
    
    def compare_and_swap(self, expected: int, new_value: int) -> bool:
        """Atomically compare and swap values.
        
        Args:
            expected: Expected current value
            new_value: New value to set if current equals expected
            
        Returns:
            True if swap was performed
        """
        with self._lock:
            if self._value == expected:
                self._value = new_value
                return True
            return False


class ThreadLocalStorage:
    """Enhanced thread-local storage with cleanup support."""
    
    def __init__(self):
        """Initialize thread-local storage."""
        self._storage = threading.local()
        self._cleanup_callbacks: Set[Callable] = set()
        self._lock = threading.Lock()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from thread-local storage.
        
        Args:
            key: Storage key
            default: Default value if key not found
            
        Returns:
            Stored value or default
        """
        return getattr(self._storage, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set value in thread-local storage.
        
        Args:
            key: Storage key
            value: Value to store
        """
        setattr(self._storage, key, value)
    
    def delete(self, key: str) -> bool:
        """Delete value from thread-local storage.
        
        Args:
            key: Storage key
            
        Returns:
            True if key was deleted, False if not found
        """
        try:
            delattr(self._storage, key)
            return True
        except AttributeError:
            return False
    
    def clear(self) -> None:
        """Clear all thread-local storage for current thread."""
        # Get all attributes and delete them
        attrs = [attr for attr in dir(self._storage) if not attr.startswith('_')]
        for attr in attrs:
            try:
                delattr(self._storage, attr)
            except AttributeError:
                pass
    
    def register_cleanup(self, callback: Callable) -> None:
        """Register a cleanup callback for thread termination.
        
        Args:
            callback: Function to call on thread cleanup
        """
        with self._lock:
            self._cleanup_callbacks.add(callback)
    
    def unregister_cleanup(self, callback: Callable) -> bool:
        """Unregister a cleanup callback.
        
        Args:
            callback: Callback to remove
            
        Returns:
            True if callback was removed
        """
        with self._lock:
            try:
                self._cleanup_callbacks.remove(callback)
                return True
            except KeyError:
                return False


# Global instances
_thread_pool_manager = ThreadPoolManager()
_thread_local_storage = ThreadLocalStorage()


def get_thread_pool_manager() -> ThreadPoolManager:
    """Get global thread pool manager instance."""
    return _thread_pool_manager


def get_thread_local_storage() -> ThreadLocalStorage:
    """Get global thread-local storage instance."""
    return _thread_local_storage


@contextmanager
def atomic_operation(lock: Optional[threading.Lock] = None):
    """Context manager for atomic operations.
    
    Args:
        lock: Lock to use (creates new one if None)
    """
    if lock is None:
        lock = threading.Lock()
    
    with lock:
        yield


def synchronized(lock_attr: str = '_lock'):
    """Decorator to synchronize method access.
    
    Args:
        lock_attr: Name of the lock attribute on the instance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, lock_attr, None)
            if lock is None:
                # Create lock if it doesn't exist
                lock = threading.RLock()
                setattr(self, lock_attr, lock)
            
            with lock:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator


def thread_safe_singleton(cls):
    """Decorator to make a class a thread-safe singleton.
    
    Args:
        cls: Class to make singleton
    """
    instances = {}
    lock = threading.Lock()
    
    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance


class BackgroundTaskManager:
    """Manager for background tasks with lifecycle management."""
    
    def __init__(self, max_workers: int = 2):
        """Initialize background task manager.
        
        Args:
            max_workers: Maximum number of background worker threads
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="bg_task")
        self._tasks: Dict[str, Future] = {}
        self._periodic_tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._shutdown = threading.Event()
    
    def submit_task(self, name: str, fn: Callable, *args, **kwargs) -> Future:
        """Submit a background task.
        
        Args:
            name: Task name
            fn: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Future object for the task
        """
        with self._lock:
            if name in self._tasks and not self._tasks[name].done():
                raise ValueError(f"Task '{name}' is already running")
            
            future = self._executor.submit(fn, *args, **kwargs)
            self._tasks[name] = future
            
            logger.info(f"Submitted background task '{name}'")
            return future
    
    def schedule_periodic(self, name: str, fn: Callable, interval: float, *args, **kwargs) -> None:
        """Schedule a periodic background task.
        
        Args:
            name: Task name
            fn: Function to execute
            interval: Interval in seconds between executions
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        with self._lock:
            if name in self._periodic_tasks:
                raise ValueError(f"Periodic task '{name}' already exists")
            
            self._periodic_tasks[name] = {
                'fn': fn,
                'interval': interval,
                'args': args,
                'kwargs': kwargs,
                'next_run': time.time() + interval,
                'enabled': True
            }
            
            logger.info(f"Scheduled periodic task '{name}' with {interval}s interval")
    
    def cancel_task(self, name: str) -> bool:
        """Cancel a task.
        
        Args:
            name: Task name
            
        Returns:
            True if task was cancelled
        """
        with self._lock:
            # Cancel one-time task
            if name in self._tasks:
                future = self._tasks[name]
                if not future.done():
                    cancelled = future.cancel()
                    logger.info(f"{'Cancelled' if cancelled else 'Could not cancel'} task '{name}'")
                    return cancelled
            
            # Disable periodic task
            if name in self._periodic_tasks:
                self._periodic_tasks[name]['enabled'] = False
                logger.info(f"Disabled periodic task '{name}'")
                return True
            
            return False
    
    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get task status.
        
        Args:
            name: Task name
            
        Returns:
            Dictionary with task status or None if not found
        """
        with self._lock:
            # Check one-time tasks
            if name in self._tasks:
                future = self._tasks[name]
                return {
                    'name': name,
                    'type': 'one-time',
                    'done': future.done(),
                    'cancelled': future.cancelled(),
                    'running': future.running()
                }
            
            # Check periodic tasks
            if name in self._periodic_tasks:
                task = self._periodic_tasks[name]
                return {
                    'name': name,
                    'type': 'periodic',
                    'enabled': task['enabled'],
                    'interval': task['interval'],
                    'next_run': task['next_run']
                }
            
            return None
    
    def list_tasks(self) -> List[str]:
        """List all task names.
        
        Returns:
            List of task names
        """
        with self._lock:
            return list(self._tasks.keys()) + list(self._periodic_tasks.keys())
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the task manager.
        
        Args:
            wait: Whether to wait for running tasks to complete
        """
        self._shutdown.set()
        self._executor.shutdown(wait=wait)
        logger.info("Background task manager shutdown")
    
    def start_periodic_scheduler(self) -> None:
        """Start the periodic task scheduler (runs in background thread)."""
        def scheduler_loop():
            while not self._shutdown.is_set():
                current_time = time.time()
                
                with self._lock:
                    tasks_to_run = []
                    for name, task in self._periodic_tasks.items():
                        if task['enabled'] and current_time >= task['next_run']:
                            tasks_to_run.append((name, task))
                            # Schedule next run
                            task['next_run'] = current_time + task['interval']
                
                # Execute tasks outside the lock
                for name, task in tasks_to_run:
                    try:
                        self._executor.submit(task['fn'], *task['args'], **task['kwargs'])
                    except Exception as e:
                        logger.error(f"Error submitting periodic task '{name}': {e}")
                
                # Sleep for a short interval
                time.sleep(0.1)
        
        scheduler_thread = threading.Thread(target=scheduler_loop, name="periodic_scheduler", daemon=True)
        scheduler_thread.start()
        logger.info("Started periodic task scheduler")