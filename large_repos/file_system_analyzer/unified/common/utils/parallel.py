"""
Parallel processing utilities for the File System Analyzer unified library.

This module provides utilities for parallel execution using both thread pools
and process pools, with proper error handling and resource management.
"""

import os
import threading
import multiprocessing
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed, Future
from typing import Any, Callable, Dict, List, Optional, Union, Iterator, TypeVar, Generic, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

from ..core.types import DEFAULT_THREAD_POOL_SIZE

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class TaskResult(Generic[R]):
    """Result of a parallel task execution."""
    success: bool
    result: Optional[R] = None
    error: Optional[Exception] = None
    task_id: Optional[str] = None
    execution_time: Optional[float] = None
    
    @property
    def is_success(self) -> bool:
        """Check if the task was successful."""
        return self.success and self.error is None


@dataclass
class ParallelExecutionStats:
    """Statistics for parallel execution."""
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_execution_time: float
    average_task_time: float
    max_workers: int
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate."""
        return self.successful_tasks / self.total_tasks if self.total_tasks > 0 else 0.0


class PoolManager(ABC):
    """Abstract base class for pool managers."""
    
    @abstractmethod
    def submit(self, func: Callable, *args, **kwargs) -> Future:
        """Submit a task to the pool."""
        pass
        
    @abstractmethod
    def map(self, func: Callable[[T], R], items: List[T]) -> Iterator[R]:
        """Map a function over a list of items."""
        pass
        
    @abstractmethod
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the pool."""
        pass
        
    @abstractmethod
    def __enter__(self):
        """Context manager entry."""
        pass
        
    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


class ThreadPoolManager(PoolManager):
    """Thread pool manager for I/O-bound tasks."""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the thread pool manager.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers or DEFAULT_THREAD_POOL_SIZE
        self.executor: Optional[ThreadPoolExecutor] = None
        self._lock = threading.Lock()
        
    def _ensure_executor(self) -> ThreadPoolExecutor:
        """Ensure the executor is created."""
        if self.executor is None:
            with self._lock:
                if self.executor is None:
                    self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self.executor
        
    def submit(self, func: Callable, *args, **kwargs) -> Future:
        """Submit a task to the thread pool."""
        executor = self._ensure_executor()
        return executor.submit(func, *args, **kwargs)
        
    def map(self, func: Callable[[T], R], items: List[T], 
           timeout: Optional[float] = None) -> Iterator[R]:
        """Map a function over a list of items using the thread pool."""
        executor = self._ensure_executor()
        return executor.map(func, items, timeout=timeout)
        
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the thread pool."""
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


class ProcessPoolManager(PoolManager):
    """Process pool manager for CPU-bound tasks."""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the process pool manager.
        
        Args:
            max_workers: Maximum number of worker processes
        """
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.executor: Optional[ProcessPoolExecutor] = None
        self._lock = threading.Lock()
        
    def _ensure_executor(self) -> ProcessPoolExecutor:
        """Ensure the executor is created."""
        if self.executor is None:
            with self._lock:
                if self.executor is None:
                    self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self.executor
        
    def submit(self, func: Callable, *args, **kwargs) -> Future:
        """Submit a task to the process pool."""
        executor = self._ensure_executor()
        return executor.submit(func, *args, **kwargs)
        
    def map(self, func: Callable[[T], R], items: List[T], 
           timeout: Optional[float] = None, chunksize: int = 1) -> Iterator[R]:
        """Map a function over a list of items using the process pool."""
        executor = self._ensure_executor()
        return executor.map(func, items, timeout=timeout, chunksize=chunksize)
        
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the process pool."""
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()


class ParallelProcessor(Generic[T, R]):
    """High-level parallel processor with error handling and progress tracking."""
    
    def __init__(
        self,
        pool_manager: PoolManager,
        error_handler: Optional[Callable[[Exception, T], Optional[R]]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize the parallel processor.
        
        Args:
            pool_manager: Pool manager for execution
            error_handler: Function to handle errors (returns fallback result or None)
            progress_callback: Function called with (completed, total) progress updates
        """
        self.pool_manager = pool_manager
        self.error_handler = error_handler
        self.progress_callback = progress_callback
        
    def process_batch(
        self,
        func: Callable[[T], R],
        items: List[T],
        batch_size: Optional[int] = None,
        timeout: Optional[float] = None
    ) -> Tuple[List[TaskResult[R]], ParallelExecutionStats]:
        """
        Process a batch of items in parallel.
        
        Args:
            func: Function to apply to each item
            items: List of items to process
            batch_size: Size of batches for processing
            timeout: Timeout per task in seconds
            
        Returns:
            Tuple of (results, statistics)
        """
        import time
        
        start_time = time.time()
        results = []
        successful_count = 0
        failed_count = 0
        task_times = []
        
        # Process in batches if specified
        if batch_size and len(items) > batch_size:
            batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        else:
            batches = [items]
            
        total_items = len(items)
        completed = 0
        
        for batch in batches:
            # Submit batch to pool
            futures = {}
            for i, item in enumerate(batch):
                task_id = f"task_{completed + i}"
                future = self.pool_manager.submit(self._safe_execute, func, item, task_id)
                futures[future] = (item, task_id)
                
            # Collect results
            for future in as_completed(futures, timeout=timeout):
                item, task_id = futures[future]
                
                try:
                    task_result = future.result()
                    results.append(task_result)
                    
                    if task_result.is_success:
                        successful_count += 1
                    else:
                        failed_count += 1
                        
                    if task_result.execution_time:
                        task_times.append(task_result.execution_time)
                        
                except Exception as e:
                    # Future itself failed
                    error_result = TaskResult(
                        success=False,
                        error=e,
                        task_id=task_id
                    )
                    results.append(error_result)
                    failed_count += 1
                    
                completed += 1
                
                # Update progress
                if self.progress_callback:
                    self.progress_callback(completed, total_items)
                    
        end_time = time.time()
        total_execution_time = end_time - start_time
        average_task_time = sum(task_times) / len(task_times) if task_times else 0.0
        
        stats = ParallelExecutionStats(
            total_tasks=total_items,
            successful_tasks=successful_count,
            failed_tasks=failed_count,
            total_execution_time=total_execution_time,
            average_task_time=average_task_time,
            max_workers=getattr(self.pool_manager, 'max_workers', 1)
        )
        
        return results, stats
        
    def _safe_execute(self, func: Callable[[T], R], item: T, task_id: str) -> TaskResult[R]:
        """Safely execute a function with error handling."""
        import time
        
        start_time = time.time()
        
        try:
            result = func(item)
            execution_time = time.time() - start_time
            
            return TaskResult(
                success=True,
                result=result,
                task_id=task_id,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Try error handler if available
            fallback_result = None
            if self.error_handler:
                try:
                    fallback_result = self.error_handler(e, item)
                except Exception:
                    pass  # Error handler failed, continue with original error
                    
            return TaskResult(
                success=fallback_result is not None,
                result=fallback_result,
                error=e,
                task_id=task_id,
                execution_time=execution_time
            )


def parallel_map(
    func: Callable[[T], R],
    items: List[T],
    max_workers: Optional[int] = None,
    use_processes: bool = False,
    timeout: Optional[float] = None,
    error_handler: Optional[Callable[[Exception, T], Optional[R]]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[TaskResult[R]]:
    """
    Apply a function to a list of items in parallel.
    
    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of workers
        use_processes: Whether to use processes instead of threads
        timeout: Timeout per task in seconds
        error_handler: Function to handle errors
        progress_callback: Progress callback function
        
    Returns:
        List of task results
    """
    # Choose appropriate pool manager
    if use_processes:
        pool_manager = ProcessPoolManager(max_workers)
    else:
        pool_manager = ThreadPoolManager(max_workers)
        
    processor = ParallelProcessor(
        pool_manager=pool_manager,
        error_handler=error_handler,
        progress_callback=progress_callback
    )
    
    try:
        results, _ = processor.process_batch(func, items, timeout=timeout)
        return results
    finally:
        pool_manager.shutdown()


def parallel_filter(
    predicate: Callable[[T], bool],
    items: List[T],
    max_workers: Optional[int] = None,
    use_processes: bool = False
) -> List[T]:
    """
    Filter a list of items in parallel.
    
    Args:
        predicate: Function that returns True for items to keep
        items: List of items to filter
        max_workers: Maximum number of workers
        use_processes: Whether to use processes instead of threads
        
    Returns:
        Filtered list of items
    """
    results = parallel_map(predicate, items, max_workers, use_processes)
    
    filtered_items = []
    for i, result in enumerate(results):
        if result.is_success and result.result:
            filtered_items.append(items[i])
            
    return filtered_items


@contextmanager
def managed_thread_pool(max_workers: Optional[int] = None):
    """
    Context manager for thread pool execution.
    
    Args:
        max_workers: Maximum number of worker threads
        
    Yields:
        ThreadPoolManager instance
    """
    pool_manager = ThreadPoolManager(max_workers)
    try:
        yield pool_manager
    finally:
        pool_manager.shutdown()


@contextmanager
def managed_process_pool(max_workers: Optional[int] = None):
    """
    Context manager for process pool execution.
    
    Args:
        max_workers: Maximum number of worker processes
        
    Yields:
        ProcessPoolManager instance
    """
    pool_manager = ProcessPoolManager(max_workers)
    try:
        yield pool_manager
    finally:
        pool_manager.shutdown()


class BatchProcessor(Generic[T, R]):
    """Batch processor with configurable batching and parallel execution."""
    
    def __init__(
        self,
        batch_size: int = 100,
        max_workers: Optional[int] = None,
        use_processes: bool = False,
        preserve_order: bool = True
    ):
        """
        Initialize the batch processor.
        
        Args:
            batch_size: Number of items to process in each batch
            max_workers: Maximum number of workers
            use_processes: Whether to use processes instead of threads
            preserve_order: Whether to preserve the order of results
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.use_processes = use_processes
        self.preserve_order = preserve_order
        
    def process(
        self,
        func: Callable[[T], R],
        items: List[T],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[R]:
        """
        Process items in batches.
        
        Args:
            func: Function to apply to each item
            items: List of items to process
            progress_callback: Progress callback function
            
        Returns:
            List of processed results
        """
        if not items:
            return []
            
        # Split into batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        all_results = []
        completed_items = 0
        total_items = len(items)
        
        for batch_idx, batch in enumerate(batches):
            # Process batch in parallel
            batch_results = parallel_map(
                func=func,
                items=batch,
                max_workers=self.max_workers,
                use_processes=self.use_processes
            )
            
            # Extract successful results
            batch_processed = []
            for result in batch_results:
                if result.is_success:
                    batch_processed.append(result.result)
                else:
                    # Handle failed items - could log error or use default value
                    logger.warning(f"Failed to process item: {result.error}")
                    batch_processed.append(None)  # or some default
                    
            if self.preserve_order:
                all_results.extend(batch_processed)
            else:
                # Filter out failed items if order doesn't matter
                all_results.extend([r for r in batch_processed if r is not None])
                
            completed_items += len(batch)
            
            # Update progress
            if progress_callback:
                progress_callback(completed_items, total_items)
                
        return all_results


class WorkerPool:
    """Generic worker pool for executing tasks."""
    
    def __init__(self, worker_count: int = None, use_processes: bool = False):
        """
        Initialize the worker pool.
        
        Args:
            worker_count: Number of workers (None for auto-detect)
            use_processes: Whether to use processes instead of threads
        """
        self.worker_count = worker_count or (
            os.cpu_count() if use_processes else DEFAULT_THREAD_POOL_SIZE
        )
        self.use_processes = use_processes
        self._pool = None
        
    def start(self):
        """Start the worker pool."""
        if self.use_processes:
            self._pool = ProcessPoolExecutor(max_workers=self.worker_count)
        else:
            self._pool = ThreadPoolExecutor(max_workers=self.worker_count)
            
    def stop(self):
        """Stop the worker pool."""
        if self._pool:
            self._pool.shutdown(wait=True)
            self._pool = None
            
    def submit_task(self, func: Callable, *args, **kwargs) -> Future:
        """Submit a task to the pool."""
        if not self._pool:
            self.start()
        return self._pool.submit(func, *args, **kwargs)
        
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()