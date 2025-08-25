"""File system utility functions for the Database Storage Optimization Analyzer."""

import os
import stat
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Iterator, Union
import platform
import psutil
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

# Import from common library
from common.utils.file_utils import get_file_stats as common_get_file_stats, find_files as common_find_files

logger = logging.getLogger(__name__)


def get_file_stats(file_path: Union[str, Path]) -> Dict[str, Union[int, datetime, bool]]:
    """
    Get detailed file statistics.

    Args:
        file_path: Path to the file

    Returns:
        Dict containing file statistics including size, modification times, etc.
    """
    # Use common file utils but extend with database-specific information
    result = common_get_file_stats(file_path)
    
    try:
        path = Path(file_path)
        stats = path.stat()
        
        # Add additional database-specific information
        result.update({
            "path": str(path.absolute()),
            "size_bytes": stats.st_size,
            "last_modified": datetime.fromtimestamp(stats.st_mtime),
            "creation_time": datetime.fromtimestamp(stats.st_ctime),
            "last_accessed": datetime.fromtimestamp(stats.st_atime),
            "exists": path.exists(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
        })
        
        # Add platform-specific information
        if platform.system() == "Windows":
            # Add Windows-specific attributes
            result["is_hidden"] = bool(stats.st_file_attributes & 0x2)  # type: ignore
            
        elif platform.system() in ["Linux", "Darwin"]:
            # Add Unix-specific attributes
            result["is_executable"] = bool(stats.st_mode & stat.S_IXUSR)
            result["permissions"] = oct(stats.st_mode)[-3:]
        
        return result
        
    except (PermissionError, OSError, FileNotFoundError) as e:
        logger.warning(f"Error getting stats for {file_path}: {e}")
        return {
            "path": str(Path(file_path).absolute()),
            "size_bytes": 0,
            "exists": False,
            "error": str(e)
        }


def find_files(
    root_path: Union[str, Path],
    extensions: Optional[Set[str]] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    modified_after: Optional[datetime] = None,
    modified_before: Optional[datetime] = None,
    max_depth: Optional[int] = None,
    follow_symlinks: bool = False,
    skip_hidden: bool = True,
    recursive: bool = True,
    max_files: Optional[int] = None,
) -> Iterator[Path]:
    """
    Find files matching specified criteria (delegates to common file utils).
    """
    # Delegate to common file utils with appropriate parameter mapping
    found_files = common_find_files(
        root_path=root_path,
        recursive=recursive,
        follow_symlinks=follow_symlinks,
        max_depth=max_depth
    )
    
    # Apply local filters
    file_count = 0
    for file_path in found_files:
        try:
            # Skip hidden files if requested
            if skip_hidden and file_path.name.startswith('.'):
                continue
                
            # Check extension filter
            if extensions is not None:
                if file_path.suffix.lower() not in {ext.lower() for ext in extensions}:
                    continue
                    
            # Check size filters
            if min_size is not None or max_size is not None:
                try:
                    file_size = file_path.stat().st_size
                    if min_size is not None and file_size < min_size:
                        continue
                    if max_size is not None and file_size > max_size:
                        continue
                except (OSError, IOError):
                    continue
                    
            # Check modification time filters
            if modified_after is not None or modified_before is not None:
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if modified_after is not None and mtime <= modified_after:
                        continue
                    if modified_before is not None and mtime >= modified_before:
                        continue
                except (OSError, IOError):
                    continue
                    
            # Check max files limit
            if max_files is not None and file_count >= max_files:
                break
                
            yield file_path
            file_count += 1
            
        except Exception:
            # Skip files that cause errors
            continue


def calculate_dir_size(
    dir_path: Union[str, Path], 
    follow_symlinks: bool = False,
    max_workers: int = 10
) -> int:
    """
    Calculate the total size of a directory and all its contents.

    Args:
        dir_path: Path to the directory
        follow_symlinks: Whether to follow symbolic links
        max_workers: Maximum number of worker threads for parallel processing

    Returns:
        Total size in bytes
    """
    path = Path(dir_path)
    
    if not path.exists() or not path.is_dir():
        return 0

    total_size = 0
    
    try:
        # For smaller directories, use single-threaded approach
        for root, dirs, files in os.walk(path, followlinks=follow_symlinks):
            for file in files:
                file_path = Path(root) / file
                try:
                    if file_path.exists() and file_path.is_file():
                        total_size += file_path.stat().st_size
                except (OSError, IOError):
                    continue
                    
    except Exception as e:
        logger.error(f"Error calculating directory size for {dir_path}: {e}")
        
    return total_size


def get_disk_usage(path: Union[str, Path]) -> Dict[str, Union[int, float]]:
    """
    Get disk usage statistics for a given path.

    Args:
        path: Path to check disk usage for

    Returns:
        Dict containing total, used, and free space in bytes, plus percentage used
    """
    try:
        usage = psutil.disk_usage(str(path))
        return {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "percent_used": (usage.used / usage.total) * 100 if usage.total > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting disk usage for {path}: {e}")
        return {
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "percent_used": 0,
            "error": str(e)
        }


def estimate_file_growth_rate(
    file_path: Optional[Union[str, Path]],
    file_sizes: List[Tuple[datetime, int]],
    time_window_days: int = 30
) -> float:
    """
    Estimate the growth rate of a file based on historical size data.

    Args:
        file_path: Optional path to the file (can be None for historical data only)
        file_sizes: List of (timestamp, size_bytes) tuples
        time_window_days: Time window in days for calculating growth rate

    Returns:
        Estimated growth rate in bytes per day
    """
    if len(file_sizes) < 2:
        return 0.0
    
    # Sort by timestamp
    sorted_sizes = sorted(file_sizes, key=lambda x: x[0])
    
    # Filter to time window
    now = datetime.now()
    window_start = now - timedelta(days=time_window_days)
    recent_sizes = [(ts, size) for ts, size in sorted_sizes if ts >= window_start]
    
    if len(recent_sizes) < 2:
        # Fall back to all available data
        recent_sizes = sorted_sizes
        
    if len(recent_sizes) < 2:
        return 0.0
    
    # Calculate growth rate using linear regression
    first_ts, first_size = recent_sizes[0]
    last_ts, last_size = recent_sizes[-1]
    
    time_diff_days = (last_ts - first_ts).total_seconds() / 86400  # Convert to days
    
    if time_diff_days <= 0:
        return 0.0
    
    growth_rate = (last_size - first_size) / time_diff_days
    return growth_rate


@lru_cache(maxsize=128)
def get_filesystem_info(path: Union[str, Path]) -> Dict[str, str]:
    """
    Get filesystem information for a given path.

    Args:
        path: Path to check filesystem for

    Returns:
        Dict containing filesystem type and mount point
    """
    try:
        path_obj = Path(path).resolve()
        
        # Find the mount point
        mount_point = path_obj
        while mount_point != mount_point.parent and not mount_point.is_mount():
            mount_point = mount_point.parent
        
        # Get filesystem type (platform-specific)
        if platform.system() == "Linux":
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3 and parts[1] == str(mount_point):
                        return {
                            "filesystem_type": parts[2],
                            "mount_point": str(mount_point)
                        }
        
        return {
            "filesystem_type": "unknown",
            "mount_point": str(mount_point)
        }
        
    except Exception as e:
        logger.error(f"Error getting filesystem info for {path}: {e}")
        return {
            "filesystem_type": "unknown",
            "mount_point": "unknown",
            "error": str(e)
        }


def safe_remove_file(file_path: Union[str, Path], backup_suffix: str = ".bak") -> bool:
    """
    Safely remove a file with optional backup.

    Args:
        file_path: Path to file to remove
        backup_suffix: Suffix for backup file (empty string to skip backup)

    Returns:
        True if file was successfully removed, False otherwise
    """
    path = Path(file_path)
    
    if not path.exists():
        return True  # File already doesn't exist
    
    try:
        # Create backup if requested
        if backup_suffix:
            backup_path = path.with_suffix(path.suffix + backup_suffix)
            path.rename(backup_path)
            logger.info(f"Created backup: {backup_path}")
        else:
            path.unlink()
            
        return True
        
    except Exception as e:
        logger.error(f"Error removing file {file_path}: {e}")
        return False


def batch_file_operation(
    file_paths: List[Path],
    operation: callable,
    max_workers: int = 10,
    ignore_errors: bool = True
) -> List[Tuple[Path, bool, Optional[str]]]:
    """
    Perform a batch operation on multiple files in parallel.

    Args:
        file_paths: List of file paths to process
        operation: Callable that takes a Path and returns a result
        max_workers: Maximum number of worker threads
        ignore_errors: Whether to continue on errors or raise them

    Returns:
        List of (path, success, error_message) tuples
    """
    results = []
    
    def process_file(path: Path) -> Tuple[Path, bool, Optional[str]]:
        try:
            operation(path)
            return (path, True, None)
        except Exception as e:
            error_msg = str(e)
            if not ignore_errors:
                raise
            return (path, False, error_msg)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(process_file, path): path for path in file_paths}
        
        for future in as_completed(future_to_path):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                path = future_to_path[future]
                results.append((path, False, str(e)))
                if not ignore_errors:
                    raise
    
    return results