"""
File system utility functions for the File System Analyzer unified library.

This module provides comprehensive file operations including metadata extraction,
file type detection, directory traversal, and size calculations with cross-platform
compatibility and performance optimizations.
"""

import os
import stat
import mimetypes
import platform
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Iterator, Union, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import subprocess

from ..core.types import (
    FileInfo, HashAlgorithm, FileCategory, FilePath,
    DEFAULT_MAX_FILE_SIZE, FILE_EXTENSIONS
)

logger = logging.getLogger(__name__)


def get_file_stats(file_path: FilePath, calculate_hash: bool = False, 
                  hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> Dict[str, Any]:
    """
    Get comprehensive file statistics and metadata.
    
    Args:
        file_path: Path to the file
        calculate_hash: Whether to calculate file hash
        hash_algorithm: Hash algorithm to use
        
    Returns:
        Dictionary containing detailed file statistics
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {"path": str(path), "exists": False, "error": "File not found"}
            
        stats = path.stat()
        
        # Basic file information
        result = {
            "path": str(path.absolute()),
            "name": path.name,
            "size_bytes": stats.st_size,
            "last_modified": datetime.fromtimestamp(stats.st_mtime),
            "creation_time": datetime.fromtimestamp(stats.st_ctime),
            "last_accessed": datetime.fromtimestamp(stats.st_atime),
            "exists": True,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
        }
        
        # File type detection
        if path.is_file():
            result["mime_type"] = get_mime_type(path)
            result["file_category"] = get_file_category(path)
            result["is_binary"] = is_binary_file(path)
            result["extension"] = path.suffix.lower()
            
        # Platform-specific attributes
        if platform.system() == "Windows":
            # Windows file attributes
            result["is_hidden"] = bool(stats.st_file_attributes & 0x2) if hasattr(stats, 'st_file_attributes') else False
            result["is_system"] = bool(stats.st_file_attributes & 0x4) if hasattr(stats, 'st_file_attributes') else False
            
        elif platform.system() in ["Linux", "Darwin"]:
            # Unix-specific attributes
            result["permissions"] = oct(stats.st_mode & 0o777)
            result["is_executable"] = bool(stats.st_mode & stat.S_IXUSR)
            result["uid"] = stats.st_uid
            result["gid"] = stats.st_gid
            
            # Try to get owner/group names
            try:
                import pwd
                import grp
                result["owner"] = pwd.getpwuid(stats.st_uid).pw_name
                result["group"] = grp.getgrgid(stats.st_gid).gr_name
            except (ImportError, KeyError, OSError):
                result["owner"] = str(stats.st_uid)
                result["group"] = str(stats.st_gid)
                
        # Calculate hash if requested
        if calculate_hash and path.is_file() and stats.st_size > 0:
            try:
                result["hash"] = hash_file(path, hash_algorithm)
                result["hash_algorithm"] = hash_algorithm.value
            except Exception as e:
                logger.warning(f"Failed to calculate hash for {path}: {e}")
                result["hash_error"] = str(e)
                
        return result
        
    except Exception as e:
        logger.error(f"Error getting stats for {file_path}: {e}")
        return {
            "path": str(file_path),
            "exists": False,
            "error": str(e)
        }


def find_files(
    root_path: FilePath,
    extensions: Optional[Set[str]] = None,
    categories: Optional[Set[FileCategory]] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    modified_after: Optional[datetime] = None,
    modified_before: Optional[datetime] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    max_depth: Optional[int] = None,
    follow_symlinks: bool = False,
    skip_hidden: bool = True,
    skip_system: bool = True,
    recursive: bool = True,
    max_files: Optional[int] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    filter_func: Optional[Callable[[Path], bool]] = None,
) -> Iterator[Path]:
    """
    Find files matching specified criteria with comprehensive filtering options.
    
    Args:
        root_path: Starting directory for search
        extensions: File extensions to include (e.g., {'.py', '.txt'})
        categories: File categories to include
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        modified_after: Only include files modified after this datetime
        modified_before: Only include files modified before this datetime
        created_after: Only include files created after this datetime
        created_before: Only include files created before this datetime
        max_depth: Maximum directory depth to search
        follow_symlinks: Whether to follow symbolic links
        skip_hidden: Whether to skip hidden files and directories
        skip_system: Whether to skip system files
        recursive: Whether to search recursively
        max_files: Maximum number of files to return
        include_patterns: Glob patterns for files to include
        exclude_patterns: Glob patterns for files to exclude
        filter_func: Custom filter function
        
    Yields:
        Path objects for matching files
    """
    root = Path(root_path)
    if not root.exists() or not root.is_dir():
        logger.warning(f"Root path {root_path} does not exist or is not a directory")
        return
        
    # Compile patterns if provided
    import re
    compiled_include = [re.compile(p) for p in (include_patterns or [])]
    compiled_exclude = [re.compile(p) for p in (exclude_patterns or [])]
    
    # Create category extension mapping
    category_extensions = set()
    if categories:
        for category in categories:
            category_extensions.update(FILE_EXTENSIONS.get(category, set()))
            
    count = 0
    current_depth = 0
    
    try:
        for current_root, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
            current_path = Path(current_root)
            
            # Calculate current depth
            try:
                current_depth = len(current_path.relative_to(root).parts)
            except ValueError:
                current_depth = 0
                
            # Skip if exceeding max depth
            if max_depth is not None and current_depth > max_depth:
                dirnames.clear()  # Don't descend further
                continue
                
            # Filter directories
            if skip_hidden:
                dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                
            # Stop recursion if not recursive and not at root
            if not recursive and current_path != root:
                dirnames.clear()
                continue
                
            # Process files in current directory
            for filename in filenames:
                file_path = current_path / filename
                
                try:
                    # Skip hidden files if requested
                    if skip_hidden and filename.startswith('.'):
                        continue
                        
                    # Skip system files on Windows
                    if skip_system and platform.system() == "Windows":
                        try:
                            attrs = os.stat(file_path).st_file_attributes
                            if attrs & 0x4:  # FILE_ATTRIBUTE_SYSTEM
                                continue
                        except (AttributeError, OSError):
                            pass
                            
                    # Skip symlinks if not following them
                    if not follow_symlinks and file_path.is_symlink():
                        continue
                        
                    # Extension filter
                    if extensions and file_path.suffix.lower() not in extensions:
                        continue
                        
                    # Category filter
                    if categories and file_path.suffix.lower() not in category_extensions:
                        continue
                        
                    # Pattern filters
                    if compiled_include:
                        if not any(pattern.search(str(file_path)) for pattern in compiled_include):
                            continue
                            
                    if compiled_exclude:
                        if any(pattern.search(str(file_path)) for pattern in compiled_exclude):
                            continue
                            
                    # Get file stats for further filtering
                    try:
                        stats = file_path.stat()
                    except (OSError, IOError):
                        continue
                        
                    # Size filters
                    if min_size is not None and stats.st_size < min_size:
                        continue
                    if max_size is not None and stats.st_size > max_size:
                        continue
                        
                    # Date filters
                    mod_time = datetime.fromtimestamp(stats.st_mtime)
                    if modified_after is not None and mod_time < modified_after:
                        continue
                    if modified_before is not None and mod_time > modified_before:
                        continue
                        
                    create_time = datetime.fromtimestamp(stats.st_ctime)
                    if created_after is not None and create_time < created_after:
                        continue
                    if created_before is not None and create_time > created_before:
                        continue
                        
                    # Custom filter function
                    if filter_func and not filter_func(file_path):
                        continue
                        
                    # Yield the matching file
                    yield file_path
                    
                    # Check max files limit
                    count += 1
                    if max_files is not None and count >= max_files:
                        return
                        
                except (PermissionError, OSError) as e:
                    logger.debug(f"Error accessing {file_path}: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Error walking directory {root_path}: {e}")


def calculate_directory_size(
    dir_path: FilePath,
    follow_symlinks: bool = False,
    max_workers: int = 10,
    include_subdirs: bool = True
) -> Dict[str, int]:
    """
    Calculate the total size of a directory and optionally subdirectories.
    
    Args:
        dir_path: Path to the directory
        follow_symlinks: Whether to follow symbolic links
        max_workers: Maximum number of worker threads
        include_subdirs: Whether to include subdirectory breakdown
        
    Returns:
        Dictionary with size information
    """
    path = Path(dir_path)
    if not path.exists() or not path.is_dir():
        return {"total_size": 0, "file_count": 0, "error": "Directory not found"}
        
    try:
        total_size = 0
        file_count = 0
        subdir_sizes = {}
        
        # Get all files
        all_files = list(find_files(
            path, 
            recursive=True, 
            follow_symlinks=follow_symlinks
        ))
        
        if len(all_files) < 1000:
            # Simple approach for small directories
            for file_path in all_files:
                try:
                    size = file_path.stat().st_size
                    total_size += size
                    file_count += 1
                    
                    if include_subdirs:
                        # Track size by immediate subdirectory
                        try:
                            rel_path = file_path.relative_to(path)
                            if len(rel_path.parts) > 1:
                                subdir = rel_path.parts[0]
                                subdir_sizes[subdir] = subdir_sizes.get(subdir, 0) + size
                        except ValueError:
                            pass
                            
                except (OSError, IOError):
                    continue
        else:
            # Parallel approach for larger directories
            def get_file_size(file_path: Path) -> Tuple[int, Optional[str]]:
                try:
                    size = file_path.stat().st_size
                    subdir = None
                    if include_subdirs:
                        try:
                            rel_path = file_path.relative_to(path)
                            if len(rel_path.parts) > 1:
                                subdir = rel_path.parts[0]
                        except ValueError:
                            pass
                    return size, subdir
                except (OSError, IOError):
                    return 0, None
                    
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(get_file_size, file_path) for file_path in all_files]
                
                for future in as_completed(futures):
                    try:
                        size, subdir = future.result()
                        total_size += size
                        if size > 0:
                            file_count += 1
                            if subdir and include_subdirs:
                                subdir_sizes[subdir] = subdir_sizes.get(subdir, 0) + size
                    except Exception:
                        continue
                        
        result = {
            "total_size": total_size,
            "file_count": file_count,
            "path": str(path.absolute())
        }
        
        if include_subdirs and subdir_sizes:
            result["subdirectory_sizes"] = subdir_sizes
            
        return result
        
    except Exception as e:
        logger.error(f"Error calculating size of {dir_path}: {e}")
        return {"total_size": 0, "file_count": 0, "error": str(e)}


@lru_cache(maxsize=128)
def get_disk_usage(path: FilePath) -> Dict[str, Union[int, float]]:
    """
    Get disk usage statistics for the partition containing the path.
    
    Args:
        path: Path to check
        
    Returns:
        Dictionary with disk usage information
    """
    try:
        import shutil
        usage = shutil.disk_usage(str(path))
        
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "percent_used": (usage.used / usage.total) * 100 if usage.total > 0 else 0,
            "path": str(path)
        }
    except Exception as e:
        logger.error(f"Error getting disk usage for {path}: {e}")
        return {"error": str(e), "path": str(path)}


def estimate_file_growth_rate(
    file_path: FilePath,
    historical_sizes: List[Tuple[datetime, int]],
    method: str = "linear"
) -> Dict[str, float]:
    """
    Estimate the growth rate of a file based on historical size measurements.
    
    Args:
        file_path: Path to the file
        historical_sizes: List of (datetime, size_bytes) tuples
        method: Estimation method ('linear', 'exponential', 'average')
        
    Returns:
        Dictionary with growth rate estimates
    """
    if not historical_sizes or len(historical_sizes) < 2:
        return {"bytes_per_day": 0.0, "method": method, "confidence": 0.0}
        
    # Sort by datetime
    sorted_sizes = sorted(historical_sizes, key=lambda x: x[0])
    
    if method == "linear":
        # Simple linear regression
        timestamps = [(dt - sorted_sizes[0][0]).total_seconds() / 86400 for dt, _ in sorted_sizes]
        sizes = [size for _, size in sorted_sizes]
        
        n = len(timestamps)
        sum_x = sum(timestamps)
        sum_y = sum(sizes)
        sum_xy = sum(x * y for x, y in zip(timestamps, sizes))
        sum_x2 = sum(x * x for x in timestamps)
        
        # Calculate slope (bytes per day)
        if n * sum_x2 - sum_x * sum_x != 0:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        else:
            slope = 0.0
            
        # Calculate confidence (R-squared)
        if n > 2:
            mean_y = sum_y / n
            ss_tot = sum((y - mean_y) ** 2 for y in sizes)
            ss_res = sum((sizes[i] - (slope * timestamps[i] + (sum_y - slope * sum_x) / n)) ** 2 
                        for i in range(n))
            confidence = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        else:
            confidence = 0.5
            
        return {
            "bytes_per_day": slope,
            "method": "linear",
            "confidence": max(0.0, min(1.0, confidence))
        }
        
    elif method == "average":
        # Simple average of deltas
        deltas = []
        for i in range(1, len(sorted_sizes)):
            time_diff = (sorted_sizes[i][0] - sorted_sizes[i-1][0]).total_seconds() / 86400
            if time_diff > 0:
                size_diff = sorted_sizes[i][1] - sorted_sizes[i-1][1]
                deltas.append(size_diff / time_diff)
                
        if deltas:
            avg_growth = sum(deltas) / len(deltas)
            # Confidence based on consistency of deltas
            if len(deltas) > 1:
                variance = sum((d - avg_growth) ** 2 for d in deltas) / len(deltas)
                std_dev = variance ** 0.5
                confidence = max(0.0, 1.0 - (std_dev / abs(avg_growth)) if avg_growth != 0 else 0.0)
            else:
                confidence = 0.5
        else:
            avg_growth = 0.0
            confidence = 0.0
            
        return {
            "bytes_per_day": avg_growth,
            "method": "average",
            "confidence": confidence
        }
        
    else:
        # Default to simple delta between first and last
        time_diff = (sorted_sizes[-1][0] - sorted_sizes[0][0]).total_seconds() / 86400
        if time_diff > 0:
            size_diff = sorted_sizes[-1][1] - sorted_sizes[0][1]
            growth_rate = size_diff / time_diff
        else:
            growth_rate = 0.0
            
        return {
            "bytes_per_day": growth_rate,
            "method": "simple",
            "confidence": 0.5
        }


def is_binary_file(file_path: FilePath, chunk_size: int = 8192) -> bool:
    """
    Determine if a file is binary by checking for null bytes.
    
    Args:
        file_path: Path to the file
        chunk_size: Size of chunk to read for testing
        
    Returns:
        True if the file appears to be binary, False otherwise
    """
    try:
        path = Path(file_path)
        if not path.is_file():
            return False
            
        with open(path, 'rb') as f:
            chunk = f.read(chunk_size)
            return b'\0' in chunk
            
    except Exception:
        # If we can't read the file, assume it's binary
        return True


def get_mime_type(file_path: FilePath) -> str:
    """
    Get the MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string
    """
    try:
        # Try python-magic first if available
        try:
            import magic
            return magic.from_file(str(file_path), mime=True)
        except ImportError:
            pass
            
        # Fall back to built-in mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"
        
    except Exception:
        return "application/octet-stream"


def get_file_category(file_path: FilePath) -> FileCategory:
    """
    Determine the category of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        FileCategory enum value
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    
    for category, extensions in FILE_EXTENSIONS.items():
        if extension in extensions:
            return category
            
    return FileCategory.OTHER


def hash_file(file_path: FilePath, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use
        
    Returns:
        Hex string of the hash
    """
    path = Path(file_path)
    
    # Select hash algorithm
    if algorithm == HashAlgorithm.MD5:
        hasher = hashlib.md5()
    elif algorithm == HashAlgorithm.SHA1:
        hasher = hashlib.sha1()
    elif algorithm == HashAlgorithm.SHA256:
        hasher = hashlib.sha256()
    elif algorithm == HashAlgorithm.SHA512:
        hasher = hashlib.sha512()
    else:
        hasher = hashlib.sha256()
        
    try:
        with open(path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
        
    except Exception as e:
        logger.error(f"Error hashing file {file_path}: {e}")
        raise


class FileSystemWalker:
    """
    Advanced file system walker with filtering and progress tracking.
    """
    
    def __init__(self, root_path: FilePath):
        """Initialize the walker with a root path."""
        self.root_path = Path(root_path)
        self.files_processed = 0
        self.directories_processed = 0
        self.errors_encountered = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    def walk(
        self,
        filter_func: Optional[Callable[[Path], bool]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> Iterator[Path]:
        """
        Walk the file system with advanced filtering and progress tracking.
        
        Args:
            filter_func: Custom filter function
            progress_callback: Function to call with progress updates
            **kwargs: Arguments passed to find_files
            
        Yields:
            Path objects for matching files
        """
        self.start_time = datetime.now()
        self.files_processed = 0
        self.directories_processed = 0
        self.errors_encountered = 0
        
        try:
            for file_path in find_files(self.root_path, filter_func=filter_func, **kwargs):
                self.files_processed += 1
                
                if progress_callback and self.files_processed % 100 == 0:
                    progress_callback(self.files_processed, self.directories_processed)
                    
                yield file_path
                
        except Exception as e:
            self.errors_encountered += 1
            logger.error(f"Error in file system walk: {e}")
            
        finally:
            self.end_time = datetime.now()
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the walk operation."""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            
        return {
            "files_processed": self.files_processed,
            "directories_processed": self.directories_processed,
            "errors_encountered": self.errors_encountered,
            "duration_seconds": duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }