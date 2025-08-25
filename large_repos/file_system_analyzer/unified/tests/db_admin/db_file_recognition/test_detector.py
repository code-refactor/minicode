"""Tests for the database file detector."""

import os
from pathlib import Path
import pytest
from datetime import datetime

from file_system_analyzer_db_admin.db_file_recognition.detector import DatabaseFileDetector
from file_system_analyzer_db_admin.utils.types import DatabaseEngine, FileCategory, ScanStatus


def test_detector_initialization():
    """Test detector initialization."""
    detector = DatabaseFileDetector()
    assert detector is not None
    assert detector.ignore_extensions is not None
    assert '.exe' in detector.ignore_extensions


def test_detect_engine_from_path():
    """Test engine detection from file path."""
    detector = DatabaseFileDetector()
    
    # MySQL paths
    assert detector.detect_engine_from_path(Path("/var/lib/mysql/data/users.ibd")) == DatabaseEngine.MYSQL
    assert detector.detect_engine_from_path(Path("/var/lib/mysql/mysql-bin.000001")) == DatabaseEngine.MYSQL
    
    # PostgreSQL paths
    assert detector.detect_engine_from_path(Path("/var/lib/postgresql/data/base/16384/16385")) == DatabaseEngine.POSTGRESQL
    assert detector.detect_engine_from_path(Path("/var/lib/postgresql/pg_wal/000000010000000000000001")) == DatabaseEngine.POSTGRESQL
    
    # MongoDB paths
    assert detector.detect_engine_from_path(Path("/var/lib/mongodb/collection-0-1234567890123456789012.wt")) == DatabaseEngine.MONGODB
    assert detector.detect_engine_from_path(Path("/var/lib/mongodb/WiredTiger.wt")) == DatabaseEngine.MONGODB
    
    # Unknown path
    assert detector.detect_engine_from_path(Path("/tmp/unknown_file.txt")) is None


def test_detect_category_from_path():
    """Test category detection from file path."""
    detector = DatabaseFileDetector()
    
    # MySQL files
    assert detector.detect_category_from_path(Path("/var/lib/mysql/data/users.ibd"), DatabaseEngine.MYSQL) == FileCategory.DATA
    assert detector.detect_category_from_path(Path("/var/lib/mysql/mysql-bin.000001"), DatabaseEngine.MYSQL) == FileCategory.LOG
    assert detector.detect_category_from_path(Path("/var/lib/mysql/backup.sql"), DatabaseEngine.MYSQL) == FileCategory.BACKUP
    assert detector.detect_category_from_path(Path("/var/lib/mysql/my.cnf"), DatabaseEngine.MYSQL) == FileCategory.CONFIG
    
    # PostgreSQL files
    assert detector.detect_category_from_path(Path("/var/lib/postgresql/data/base/16384/16385"), DatabaseEngine.POSTGRESQL) == FileCategory.DATA
    assert detector.detect_category_from_path(Path("/var/lib/postgresql/pg_wal/000000010000000000000001"), DatabaseEngine.POSTGRESQL) == FileCategory.LOG
    
    # MongoDB files
    assert detector.detect_category_from_path(Path("/var/lib/mongodb/collection-0-1234567890123456789012.wt"), DatabaseEngine.MONGODB) == FileCategory.DATA
    assert detector.detect_category_from_path(Path("/var/lib/mongodb/index-1-1234567890123456789012.wt"), DatabaseEngine.MONGODB) == FileCategory.INDEX
    
    # Unknown file
    assert detector.detect_category_from_path(Path("/tmp/unknown_file.txt")) == FileCategory.UNKNOWN


def test_analyze_file(mock_data_dir):
    """Test analyzing a single file."""
    detector = DatabaseFileDetector()
    
    # MySQL data file
    mysql_data_file = mock_data_dir / "mysql" / "data" / "users.ibd"
    result = detector.analyze_file(mysql_data_file)
    assert result is not None
    assert result.engine == DatabaseEngine.MYSQL
    assert result.category == FileCategory.DATA
    
    # MySQL log file
    mysql_log_file = mock_data_dir / "mysql" / "logs" / "mysql-bin.000001"
    result = detector.analyze_file(mysql_log_file)
    assert result is not None
    assert result.engine == DatabaseEngine.MYSQL
    assert result.category == FileCategory.LOG
    
    # PostgreSQL data file
    pg_data_file = mock_data_dir / "postgresql" / "data" / "base" / "16384" / "16385"
    result = detector.analyze_file(pg_data_file)
    assert result is not None
    assert result.engine == DatabaseEngine.POSTGRESQL
    assert result.category == FileCategory.DATA


def test_scan_directory(mock_data_dir):
    """Test scanning a directory for database files."""
    detector = DatabaseFileDetector()
    
    # Scan MySQL directory
    mysql_dir = mock_data_dir / "mysql"
    mysql_result = detector.scan_directory(mysql_dir)
    assert mysql_result.scan_status == ScanStatus.COMPLETED
    assert mysql_result.total_files_scanned > 0
    assert len(mysql_result.detected_files) > 0
    assert DatabaseEngine.MYSQL in mysql_result.files_by_engine
    
    # Scan PostgreSQL directory
    pg_dir = mock_data_dir / "postgresql"
    pg_result = detector.scan_directory(pg_dir)
    assert pg_result.scan_status == ScanStatus.COMPLETED
    assert pg_result.total_files_scanned > 0
    assert len(pg_result.detected_files) > 0
    assert DatabaseEngine.POSTGRESQL in pg_result.files_by_engine
    
    # Scan MongoDB directory
    mongo_dir = mock_data_dir / "mongodb"
    mongo_result = detector.scan_directory(mongo_dir)
    assert mongo_result.scan_status == ScanStatus.COMPLETED
    assert mongo_result.total_files_scanned > 0
    assert len(mongo_result.detected_files) > 0
    assert DatabaseEngine.MONGODB in mongo_result.files_by_engine
    
    # Scan all directories recursively
    all_result = detector.scan_directory(mock_data_dir)
    assert all_result.scan_status == ScanStatus.COMPLETED
    assert all_result.total_files_scanned > 0
    assert len(all_result.detected_files) > 0
    assert DatabaseEngine.MYSQL in all_result.files_by_engine
    assert DatabaseEngine.POSTGRESQL in all_result.files_by_engine
    assert DatabaseEngine.MONGODB in all_result.files_by_engine


def test_invalid_directory():
    """Test scanning an invalid directory."""
    detector = DatabaseFileDetector()
    result = detector.scan_directory("/nonexistent/path")
    assert result.scan_status == ScanStatus.FAILED
    assert "does not exist" in result.error_message
    assert result.total_files_scanned == 0
    assert len(result.detected_files) == 0