"""Tests for file utility functions."""

import os
import pytest
from pathlib import Path
from datetime import datetime, timedelta

from file_system_analyzer_db_admin.utils.file_utils import (
    get_file_stats,
    find_files,
    calculate_dir_size,
    get_disk_usage,
    estimate_file_growth_rate,
)


def test_get_file_stats(mock_data_dir):
    """Test getting file statistics."""
    # Test existing file
    mysql_config = mock_data_dir / "mysql" / "config" / "my.cnf"
    stats = get_file_stats(mysql_config)
    
    assert stats["path"] == str(mysql_config.absolute())
    assert stats["size_bytes"] > 0
    assert stats["exists"] is True
    assert stats["is_file"] is True
    assert stats["is_dir"] is False
    assert "last_modified" in stats
    assert "creation_time" in stats
    assert "last_accessed" in stats
    
    # Test directory
    dir_stats = get_file_stats(mock_data_dir)
    assert dir_stats["exists"] is True
    assert dir_stats["is_file"] is False
    assert dir_stats["is_dir"] is True
    
    # Test nonexistent file
    nonexistent_stats = get_file_stats(mock_data_dir / "nonexistent.txt")
    assert nonexistent_stats["exists"] is False
    assert "error" in nonexistent_stats


def test_find_files(mock_data_dir):
    """Test finding files with various filters."""
    # Find all files in mysql directory
    mysql_dir = mock_data_dir / "mysql"
    all_mysql_files = list(find_files(mysql_dir))
    assert len(all_mysql_files) > 0
    
    # Test extension filter (config files)
    config_files = list(find_files(mysql_dir, extensions={".cnf"}))
    assert len(config_files) > 0
    assert all(f.suffix == ".cnf" for f in config_files)
    
    # Test maximum depth
    shallow_files = list(find_files(mock_data_dir, max_depth=1))
    deep_files = list(find_files(mock_data_dir, max_depth=3))
    assert len(deep_files) >= len(shallow_files)
    
    # Test non-recursive
    non_recursive = list(find_files(mock_data_dir, recursive=False))
    recursive = list(find_files(mock_data_dir))
    assert len(recursive) >= len(non_recursive)
    
    # Test max_files limit
    limited_files = list(find_files(mock_data_dir, max_files=3))
    assert len(limited_files) <= 3


def test_calculate_dir_size(mock_data_dir):
    """Test calculating directory size."""
    # Calculate size of mysql directory
    mysql_dir = mock_data_dir / "mysql"
    size = calculate_dir_size(mysql_dir)
    assert size > 0
    
    # Calculate size of a specific subdirectory
    logs_dir = mysql_dir / "logs"
    logs_size = calculate_dir_size(logs_dir)
    assert logs_size > 0
    
    # Test nonexistent directory
    nonexistent_size = calculate_dir_size(mock_data_dir / "nonexistent")
    assert nonexistent_size == 0


def test_get_disk_usage(mock_data_dir):
    """Test getting disk usage information."""
    usage = get_disk_usage(mock_data_dir)
    
    assert "total_bytes" in usage
    assert usage["total_bytes"] > 0
    
    assert "used_bytes" in usage
    assert usage["used_bytes"] > 0
    
    assert "free_bytes" in usage
    assert usage["free_bytes"] > 0
    
    assert "percent_used" in usage
    assert 0 <= usage["percent_used"] <= 100


def test_estimate_file_growth_rate():
    """Test estimating file growth rate from historical data."""
    now = datetime.now()
    
    # Linear growth (1MB per day)
    linear_history = [
        (now - timedelta(days=5), 1 * 1024 * 1024),
        (now - timedelta(days=4), 2 * 1024 * 1024),
        (now - timedelta(days=3), 3 * 1024 * 1024),
        (now - timedelta(days=2), 4 * 1024 * 1024),
        (now - timedelta(days=1), 5 * 1024 * 1024),
    ]
    linear_rate = estimate_file_growth_rate(None, linear_history)
    assert linear_rate > 0
    assert abs(linear_rate - 1024 * 1024) < 100000  # Should be close to 1MB/day
    
    # Exponential growth (doubling every day)
    exponential_history = [
        (now - timedelta(days=5), 1 * 1024 * 1024),
        (now - timedelta(days=4), 2 * 1024 * 1024),
        (now - timedelta(days=3), 4 * 1024 * 1024),
        (now - timedelta(days=2), 8 * 1024 * 1024),
        (now - timedelta(days=1), 16 * 1024 * 1024),
    ]
    exponential_rate = estimate_file_growth_rate(None, exponential_history)
    assert exponential_rate > linear_rate  # Exponential should grow faster
    
    # No growth
    stable_history = [
        (now - timedelta(days=5), 1 * 1024 * 1024),
        (now - timedelta(days=4), 1 * 1024 * 1024),
        (now - timedelta(days=3), 1 * 1024 * 1024),
        (now - timedelta(days=2), 1 * 1024 * 1024),
        (now - timedelta(days=1), 1 * 1024 * 1024),
    ]
    stable_rate = estimate_file_growth_rate(None, stable_history)
    assert stable_rate == 0
    
    # Empty or small history
    empty_history = []
    assert estimate_file_growth_rate(None, empty_history) == 0
    
    single_point = [(now, 1024)]
    assert estimate_file_growth_rate(None, single_point) == 0