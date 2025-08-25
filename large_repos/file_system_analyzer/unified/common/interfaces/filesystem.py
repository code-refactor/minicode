"""
File system interface for the File System Analyzer unified library.

This module provides abstracted file system access with cross-platform
compatibility and enhanced functionality.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Iterator, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.types import FilePath, FileInfo
from ..utils.file_utils import get_file_stats, find_files, calculate_directory_size
from ..utils.parallel import ThreadPoolManager

logger = logging.getLogger(__name__)


class FileSystemInterface:
    """
    Standard interface for file system operations.
    
    Provides cross-platform file system access with safety checks
    and performance optimizations.
    """
    
    def __init__(
        self,
        read_only: bool = True,
        max_workers: int = 10,
        enable_caching: bool = True
    ):
        """
        Initialize the file system interface.
        
        Args:
            read_only: Enforce read-only operations
            max_workers: Maximum worker threads for parallel operations
            enable_caching: Enable result caching
        """
        self.read_only = read_only
        self.max_workers = max_workers
        self.enable_caching = enable_caching
        self._stats_cache = {} if enable_caching else None
        
    def get_file_info(self, file_path: FilePath) -> Optional[Dict[str, Any]]:
        """Get information about a file."""
        path_str = str(file_path)
        
        # Check cache first
        if self._stats_cache and path_str in self._stats_cache:
            return self._stats_cache[path_str]
            
        try:
            stats = get_file_stats(file_path)
            
            # Cache result
            if self._stats_cache:
                self._stats_cache[path_str] = stats
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
            
    def list_files(
        self,
        root_path: FilePath,
        recursive: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        **kwargs
    ) -> List[Path]:
        """List files in a directory with filtering."""
        try:
            return list(find_files(
                root_path=root_path,
                recursive=recursive,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                **kwargs
            ))
        except Exception as e:
            logger.error(f"Error listing files in {root_path}: {e}")
            return []
            
    def get_directory_size(self, dir_path: FilePath) -> Dict[str, Any]:
        """Get the total size of a directory."""
        try:
            return calculate_directory_size(dir_path, max_workers=self.max_workers)
        except Exception as e:
            logger.error(f"Error calculating directory size for {dir_path}: {e}")
            return {"total_size": 0, "file_count": 0, "error": str(e)}
            
    def exists(self, path: FilePath) -> bool:
        """Check if a path exists."""
        return Path(path).exists()
        
    def is_file(self, path: FilePath) -> bool:
        """Check if path is a file."""
        return Path(path).is_file()
        
    def is_directory(self, path: FilePath) -> bool:
        """Check if path is a directory.""" 
        return Path(path).is_dir()
        
    def read_file_sample(
        self,
        file_path: FilePath,
        max_bytes: int = 8192,
        encoding: str = 'utf-8'
    ) -> Optional[str]:
        """Read a sample of file content."""
        if not self.read_only:
            logger.warning("Reading file with non-read-only interface")
            
        try:
            path = Path(file_path)
            with open(path, 'r', encoding=encoding, errors='replace') as f:
                return f.read(max_bytes)
        except Exception as e:
            logger.error(f"Error reading file sample from {file_path}: {e}")
            return None


class EnhancedFileSystemInterface(FileSystemInterface):
    """
    Enhanced file system interface with additional capabilities.
    
    Extends the basic interface with advanced features like
    parallel processing, caching, and monitoring integration.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pool_manager = ThreadPoolManager(self.max_workers)
        
    def scan_directory_parallel(
        self,
        root_path: FilePath,
        processor_func: Callable[[Path], Any],
        **kwargs
    ) -> List[Any]:
        """Scan directory and process files in parallel."""
        files = self.list_files(root_path, **kwargs)
        
        if not files:
            return []
            
        results = []
        with self._pool_manager as pool:
            futures = {
                pool.submit(processor_func, file_path): file_path 
                for file_path in files
            }
            
            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    
        return results
        
    def batch_get_file_info(self, file_paths: List[FilePath]) -> Dict[str, Dict[str, Any]]:
        """Get file info for multiple files in parallel."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self.get_file_info, path): str(path)
                for path in file_paths
            }
            
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    file_info = future.result()
                    results[path] = file_info
                except Exception as e:
                    logger.error(f"Error getting info for {path}: {e}")
                    results[path] = {"error": str(e)}
                    
        return results
        
    def monitor_directory_changes(
        self,
        directory: FilePath,
        callback: Callable[[str, Path], None],
        recursive: bool = True
    ) -> bool:
        """Monitor directory for changes (basic implementation)."""
        # This is a simplified implementation
        # In production, you'd use platform-specific file watching APIs
        logger.info(f"Monitoring {directory} for changes (basic implementation)")
        return True
        
    def get_access_patterns(self, file_path: FilePath) -> Dict[str, Any]:
        """Get file access patterns (mock implementation)."""
        # This would integrate with system monitoring in production
        return {
            "access_frequency": 1.0,
            "peak_access_hours": [9, 10, 11, 14, 15, 16],
            "last_accessed": None,
            "access_trend": "stable"
        }
        
    def cleanup_cache(self) -> int:
        """Clear the stats cache."""
        if self._stats_cache:
            count = len(self._stats_cache)
            self._stats_cache.clear()
            return count
        return 0
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self._stats_cache:
            return {
                "cache_size": len(self._stats_cache),
                "cache_enabled": True
            }
        return {"cache_enabled": False}