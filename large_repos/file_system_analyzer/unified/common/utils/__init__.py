"""
Utility modules for the File System Analyzer unified library.

This package provides common utility functions for file operations, 
cryptography, caching, and parallel processing.
"""

from .file_utils import (
    get_file_stats,
    find_files,
    calculate_directory_size,
    get_disk_usage,
    estimate_file_growth_rate,
    is_binary_file,
    get_mime_type,
    get_file_category,
    hash_file,
    FileSystemWalker
)

from .crypto import (
    SimpleCryptoProvider,
    hash_data,
    generate_secure_id,
    create_signature,
    verify_signature
)

from .cache import (
    CacheManager,
    FileCacheBackend,
    MemoryCacheBackend,
    CacheEntry
)

from .parallel import (
    ParallelProcessor,
    parallel_map,
    parallel_filter,
    ThreadPoolManager,
    ProcessPoolManager
)

__all__ = [
    # File utilities
    'get_file_stats',
    'find_files', 
    'calculate_directory_size',
    'get_disk_usage',
    'estimate_file_growth_rate',
    'is_binary_file',
    'get_mime_type',
    'get_file_category',
    'FileSystemWalker',
    
    # Crypto utilities
    'SimpleCryptoProvider',
    'hash_file',
    'hash_data',
    'generate_secure_id',
    'create_signature',
    'verify_signature',
    
    # Cache utilities
    'CacheManager',
    'FileCacheBackend',
    'MemoryCacheBackend',
    'CacheEntry',
    
    # Parallel processing utilities
    'ParallelProcessor',
    'parallel_map',
    'parallel_filter',
    'ThreadPoolManager',
    'ProcessPoolManager',
]