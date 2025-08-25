"""
Batch processing utilities for financial data operations.

This module provides classes and functions for efficiently processing
large volumes of financial data in batches with error handling,
progress tracking, and resource management.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Callable, Iterator, Tuple, Union, Generic, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock
import logging

T = TypeVar('T')
R = TypeVar('R')

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of a batch processing operation."""
    batch_id: str
    success_count: int
    error_count: int
    total_items: int
    start_time: datetime
    end_time: datetime
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> float:
        """Get processing duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Get success rate as a percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.success_count / self.total_items) * 100
    
    @property
    def items_per_second(self) -> float:
        """Get processing rate in items per second."""
        if self.duration_seconds == 0:
            return 0.0
        return self.total_items / self.duration_seconds
    
    def add_error(self, item_index: int, error: Exception, item_data: Any = None) -> None:
        """Add an error to the batch result."""
        self.errors.append({
            "index": item_index,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "item_data": item_data,
            "timestamp": datetime.now().isoformat()
        })
        self.error_count += 1
    
    def add_warning(self, item_index: int, warning: str, item_data: Any = None) -> None:
        """Add a warning to the batch result."""
        self.warnings.append({
            "index": item_index,
            "warning": warning,
            "item_data": item_data,
            "timestamp": datetime.now().isoformat()
        })
    
    def merge(self, other: 'BatchResult') -> 'BatchResult':
        """Merge with another batch result."""
        merged = BatchResult(
            batch_id=f"{self.batch_id}+{other.batch_id}",
            success_count=self.success_count + other.success_count,
            error_count=self.error_count + other.error_count,
            total_items=self.total_items + other.total_items,
            start_time=min(self.start_time, other.start_time),
            end_time=max(self.end_time, other.end_time),
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            results=self.results + other.results,
            metadata={**self.metadata, **other.metadata}
        )
        return merged


class BatchProcessor(Generic[T, R], ABC):
    """
    Abstract base class for batch processing operations.
    
    Provides common functionality for processing items in batches with
    error handling, progress tracking, and configurable batch sizes.
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        max_workers: Optional[int] = None,
        use_threads: bool = True,
        continue_on_error: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of items to process in each batch
            max_workers: Maximum number of worker threads/processes
            use_threads: Whether to use threads (True) or processes (False)
            continue_on_error: Whether to continue processing if errors occur
            progress_callback: Optional callback for progress updates
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.use_threads = use_threads
        self.continue_on_error = continue_on_error
        self.progress_callback = progress_callback
        self._lock = Lock()
        self._processed_count = 0
    
    @abstractmethod
    def process_item(self, item: T) -> R:
        """
        Process a single item.
        
        Args:
            item: Item to process
            
        Returns:
            Processed result
            
        Raises:
            Exception: If processing fails
        """
        pass
    
    def validate_item(self, item: T) -> bool:
        """
        Validate an item before processing.
        
        Override this method to provide custom validation logic.
        
        Args:
            item: Item to validate
            
        Returns:
            True if item is valid, False otherwise
        """
        return True
    
    def process_batch(self, items: List[T], batch_id: str = None) -> BatchResult:
        """
        Process a batch of items sequentially.
        
        Args:
            items: List of items to process
            batch_id: Optional batch identifier
            
        Returns:
            BatchResult with processing results
        """
        if batch_id is None:
            batch_id = f"batch_{datetime.now().timestamp()}"
        
        start_time = datetime.now()
        result = BatchResult(
            batch_id=batch_id,
            success_count=0,
            error_count=0,
            total_items=len(items),
            start_time=start_time,
            end_time=start_time  # Will be updated at end
        )
        
        for i, item in enumerate(items):
            try:
                # Validate item first
                if not self.validate_item(item):
                    result.add_warning(i, "Item failed validation", item)
                    continue
                
                # Process item
                processed_result = self.process_item(item)
                result.results.append(processed_result)
                result.success_count += 1
                
                # Update progress
                self._update_progress(result.success_count + result.error_count, result.total_items)
                
            except Exception as e:
                result.add_error(i, e, item)
                logger.warning(f"Error processing item {i} in batch {batch_id}: {e}")
                
                if not self.continue_on_error:
                    break
        
        result.end_time = datetime.now()
        return result
    
    def process_parallel(self, items: List[T], batch_id: str = None) -> BatchResult:
        """
        Process items in parallel using threads or processes.
        
        Args:
            items: List of items to process
            batch_id: Optional batch identifier
            
        Returns:
            BatchResult with processing results
        """
        if batch_id is None:
            batch_id = f"parallel_batch_{datetime.now().timestamp()}"
        
        start_time = datetime.now()
        result = BatchResult(
            batch_id=batch_id,
            success_count=0,
            error_count=0,
            total_items=len(items),
            start_time=start_time,
            end_time=start_time
        )
        
        # Choose executor type
        executor_class = ThreadPoolExecutor if self.use_threads else ProcessPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {}
            for i, item in enumerate(items):
                if self.validate_item(item):
                    future = executor.submit(self._safe_process_item, i, item)
                    future_to_item[future] = (i, item)
                else:
                    result.add_warning(i, "Item failed validation", item)
            
            # Collect results
            for future in as_completed(future_to_item):
                i, item = future_to_item[future]
                try:
                    success, processed_result, error = future.result()
                    
                    if success:
                        result.results.append(processed_result)
                        result.success_count += 1
                    else:
                        result.add_error(i, error, item)
                    
                    # Update progress
                    completed = result.success_count + result.error_count
                    self._update_progress(completed, len(future_to_item))
                    
                except Exception as e:
                    result.add_error(i, e, item)
                    logger.error(f"Unexpected error with future for item {i}: {e}")
        
        result.end_time = datetime.now()
        return result
    
    def process_in_chunks(
        self,
        items: List[T],
        parallel_chunks: bool = False
    ) -> List[BatchResult]:
        """
        Process items in chunks of batch_size.
        
        Args:
            items: List of items to process
            parallel_chunks: Whether to process chunks in parallel
            
        Returns:
            List of BatchResult objects, one per chunk
        """
        chunks = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        results = []
        
        if parallel_chunks and self.use_threads:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_chunk = {
                    executor.submit(self.process_batch, chunk, f"chunk_{i}"): i
                    for i, chunk in enumerate(chunks)
                }
                
                for future in as_completed(future_to_chunk):
                    chunk_index = future_to_chunk[future]
                    try:
                        chunk_result = future.result()
                        results.append(chunk_result)
                    except Exception as e:
                        logger.error(f"Error processing chunk {chunk_index}: {e}")
        else:
            for i, chunk in enumerate(chunks):
                chunk_result = self.process_batch(chunk, f"chunk_{i}")
                results.append(chunk_result)
        
        return results
    
    def _safe_process_item(self, index: int, item: T) -> Tuple[bool, Optional[R], Optional[Exception]]:
        """
        Safely process an item, catching exceptions.
        
        Args:
            index: Item index
            item: Item to process
            
        Returns:
            Tuple of (success, result, error)
        """
        try:
            result = self.process_item(item)
            return True, result, None
        except Exception as e:
            return False, None, e
    
    def _update_progress(self, processed: int, total: int) -> None:
        """Update progress tracking."""
        with self._lock:
            self._processed_count = processed
            if self.progress_callback:
                self.progress_callback(processed, total)


class TransactionBatchProcessor(BatchProcessor[Dict[str, Any], Dict[str, Any]]):
    """
    Specialized batch processor for financial transactions.
    
    Processes transaction dictionaries with validation and enrichment.
    """
    
    def __init__(
        self,
        required_fields: List[str] = None,
        validation_rules: Dict[str, Callable[[Any], bool]] = None,
        enrichment_functions: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        **kwargs
    ):
        """
        Initialize transaction batch processor.
        
        Args:
            required_fields: List of required field names
            validation_rules: Dictionary of field_name -> validation_function
            enrichment_functions: List of functions to enrich transaction data
            **kwargs: Additional arguments for BatchProcessor
        """
        super().__init__(**kwargs)
        self.required_fields = required_fields or ["amount", "date", "description"]
        self.validation_rules = validation_rules or {}
        self.enrichment_functions = enrichment_functions or []
    
    def validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate a transaction dictionary."""
        # Check required fields
        for field in self.required_fields:
            if field not in item or item[field] is None:
                return False
        
        # Apply validation rules
        for field, validator in self.validation_rules.items():
            if field in item and not validator(item[field]):
                return False
        
        return True
    
    def process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transaction with validation and enrichment."""
        # Make a copy to avoid modifying original
        processed_item = item.copy()
        
        # Apply enrichment functions
        for enrichment_func in self.enrichment_functions:
            processed_item = enrichment_func(processed_item)
        
        # Add processing metadata
        processed_item['processed_at'] = datetime.now().isoformat()
        processed_item['processor'] = 'TransactionBatchProcessor'
        
        return processed_item


class ProgressTracker:
    """
    Utility class for tracking batch processing progress.
    """
    
    def __init__(self, total_items: int, update_interval: int = 100):
        """
        Initialize progress tracker.
        
        Args:
            total_items: Total number of items to process
            update_interval: How often to log progress updates
        """
        self.total_items = total_items
        self.update_interval = update_interval
        self.processed_items = 0
        self.start_time = datetime.now()
        self.last_update_time = self.start_time
        self._lock = Lock()
    
    def update(self, processed: int, total: int = None) -> None:
        """
        Update progress.
        
        Args:
            processed: Number of items processed so far
            total: Total number of items (optional update)
        """
        with self._lock:
            self.processed_items = processed
            if total is not None:
                self.total_items = total
            
            # Log progress at intervals
            if processed % self.update_interval == 0 or processed >= self.total_items:
                self._log_progress()
    
    def _log_progress(self) -> None:
        """Log current progress."""
        now = datetime.now()
        elapsed = (now - self.start_time).total_seconds()
        
        if elapsed > 0:
            rate = self.processed_items / elapsed
            percentage = (self.processed_items / self.total_items * 100) if self.total_items > 0 else 0
            
            logger.info(
                f"Progress: {self.processed_items}/{self.total_items} "
                f"({percentage:.1f}%) - {rate:.1f} items/sec"
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get progress summary."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "processed_items": self.processed_items,
            "total_items": self.total_items,
            "percentage_complete": (self.processed_items / self.total_items * 100) if self.total_items > 0 else 0,
            "elapsed_seconds": elapsed,
            "items_per_second": self.processed_items / elapsed if elapsed > 0 else 0,
            "estimated_remaining_seconds": ((self.total_items - self.processed_items) * elapsed / self.processed_items) if self.processed_items > 0 else None
        }


def create_transaction_validator() -> Dict[str, Callable[[Any], bool]]:
    """
    Create common validation rules for financial transactions.
    
    Returns:
        Dictionary of field validators
    """
    from decimal import Decimal
    from datetime import datetime, date
    
    def validate_amount(value: Any) -> bool:
        """Validate transaction amount."""
        try:
            amount = Decimal(str(value))
            return amount != 0  # Non-zero amounts only
        except:
            return False
    
    def validate_date(value: Any) -> bool:
        """Validate transaction date."""
        if isinstance(value, (date, datetime)):
            return True
        
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except:
                return False
        
        return False
    
    def validate_description(value: Any) -> bool:
        """Validate transaction description."""
        return isinstance(value, str) and len(value.strip()) > 0
    
    return {
        "amount": validate_amount,
        "date": validate_date,
        "description": validate_description
    }


def create_transaction_enrichment_functions() -> List[Callable[[Dict[str, Any]], Dict[str, Any]]]:
    """
    Create common enrichment functions for transactions.
    
    Returns:
        List of enrichment functions
    """
    def add_absolute_amount(transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Add absolute amount field."""
        if "amount" in transaction:
            try:
                from decimal import Decimal
                amount = Decimal(str(transaction["amount"]))
                transaction["absolute_amount"] = abs(amount)
            except:
                pass
        return transaction
    
    def categorize_by_amount(transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Add amount-based category."""
        if "amount" in transaction:
            try:
                from decimal import Decimal
                amount = Decimal(str(transaction["amount"]))
                
                if amount >= 1000:
                    transaction["amount_category"] = "large"
                elif amount >= 100:
                    transaction["amount_category"] = "medium"
                else:
                    transaction["amount_category"] = "small"
            except:
                transaction["amount_category"] = "unknown"
        
        return transaction
    
    def add_processed_timestamp(transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Add processing timestamp."""
        transaction["batch_processed_at"] = datetime.now().isoformat()
        return transaction
    
    return [
        add_absolute_amount,
        categorize_by_amount,
        add_processed_timestamp
    ]