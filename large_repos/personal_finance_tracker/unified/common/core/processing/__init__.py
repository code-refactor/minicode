"""
Processing utilities for financial data operations.

This package provides utilities for batch processing, caching, and performance
monitoring that both persona implementations can use to efficiently handle
large volumes of financial data.
"""

# Batch processing
from .batch import (
    BatchResult,
    BatchProcessor,
    TransactionBatchProcessor,
    ProgressTracker,
    create_transaction_validator,
    create_transaction_enrichment_functions,
)

# Caching utilities
from .caching import (
    CacheEntry,
    CacheStats,
    Cache,
    InMemoryCache,
    CacheManager,
    get_cache_manager,
    cached,
    cache_key_from_dict,
    MemoizedCalculation,
    memoized_calculation,
    setup_default_caches,
)

# Performance monitoring
from .performance import (
    PerformanceMetric,
    TimingResult,
    PerformanceTracker,
    SystemMonitor,
    PerformanceMonitor,
    timed,
    get_global_monitor,
    memory_profiling,
    time_financial_operation,
)

__all__ = [
    # Batch processing
    "BatchResult",
    "BatchProcessor",
    "TransactionBatchProcessor",
    "ProgressTracker",
    "create_transaction_validator",
    "create_transaction_enrichment_functions",
    
    # Caching utilities
    "CacheEntry",
    "CacheStats",
    "Cache",
    "InMemoryCache",
    "CacheManager",
    "get_cache_manager",
    "cached",
    "cache_key_from_dict",
    "MemoizedCalculation",
    "memoized_calculation",
    "setup_default_caches",
    
    # Performance monitoring
    "PerformanceMetric",
    "TimingResult",
    "PerformanceTracker",
    "SystemMonitor",
    "PerformanceMonitor",
    "timed",
    "get_global_monitor",
    "memory_profiling",
    "time_financial_operation",
]