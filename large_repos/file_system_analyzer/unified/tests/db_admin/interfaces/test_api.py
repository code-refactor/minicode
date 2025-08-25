"""Tests for the Storage Optimizer API."""

import os
import pytest
from datetime import datetime
from pathlib import Path

from file_system_analyzer_db_admin.interfaces.api import StorageOptimizerAPI
from file_system_analyzer_db_admin.utils.types import (
    DatabaseEngine,
    FileCategory,
    DatabaseFile,
)


def test_api_initialization(temp_output_dir):
    """Test API initialization."""
    api = StorageOptimizerAPI(output_dir=temp_output_dir)
    assert api is not None
    assert api.fs_interface is not None
    assert api.export_interface is not None
    assert api.notification_interface is not None
    assert api.file_detector is not None
    assert api.log_analyzer is not None
    assert api.index_analyzer is not None
    assert api.fragmentation_analyzer is not None
    assert api.backup_analyzer is not None
    assert api.read_only is True
    assert api.cache_results is True


def test_analyze_database_files(mock_data_dir, temp_output_dir):
    """Test database file analysis through API."""
    api = StorageOptimizerAPI(output_dir=temp_output_dir)
    
    # Analyze MySQL directory
    mysql_dir = mock_data_dir / "mysql"
    mysql_result = api.analyze_database_files(
        root_path=mysql_dir,
        recursive=True,
        export_format="json",
        export_filename="mysql_analysis.json",
    )
    
    # Check results
    assert mysql_result is not None
    assert mysql_result.get("scan_status") == "completed"
    assert mysql_result.get("total_files_scanned", 0) > 0
    assert len(mysql_result.get("detected_files", [])) > 0
    
    # Check that export file was created
    export_file = Path(temp_output_dir) / "mysql_analysis.json"
    assert export_file.exists()
    
    # Test caching
    cached_result = api.analyze_database_files(
        root_path=mysql_dir,
        recursive=True,
    )
    assert cached_result is not None
    assert cached_result == mysql_result
    
    # Clear cache and reanalyze
    api.clear_cache()
    reanalyzed_result = api.analyze_database_files(
        root_path=mysql_dir,
        recursive=True,
    )
    assert reanalyzed_result is not None
    assert reanalyzed_result != {}  # Should not be empty
    
    # Check for cached keys
    cached_keys = api.get_cached_analysis_keys()
    assert len(cached_keys) > 0


def test_analyze_transaction_logs(mock_database_files, temp_output_dir):
    """Test transaction log analysis through API."""
    api = StorageOptimizerAPI(output_dir=temp_output_dir)
    
    # Filter log files
    log_files = [f.dict() for f in mock_database_files if f.category == FileCategory.LOG]
    assert len(log_files) > 0
    
    # Create sample historical sizes
    now = datetime.now()
    
    # Analyze logs
    log_result = api.analyze_transaction_logs(
        log_files=log_files,
        export_format="json",
        export_filename="log_analysis.json",
    )
    
    # Check results
    assert log_result is not None
    assert log_result.get("scan_status") == "completed"
    assert log_result.get("total_log_size_bytes", 0) > 0
    assert len(log_result.get("log_files", [])) > 0
    
    # Check that export file was created
    export_file = Path(temp_output_dir) / "log_analysis.json"
    assert export_file.exists()


def test_analyze_index_efficiency(mock_indexes, temp_output_dir):
    """Test index efficiency analysis through API."""
    api = StorageOptimizerAPI(output_dir=temp_output_dir)
    
    # Convert indexes to dictionaries
    indexes = [idx.dict() for idx in mock_indexes]
    assert len(indexes) > 0
    
    # Sample table sizes
    table_sizes = {"users": 1073741824, "products": 536870912}  # 1GB, 512MB
    
    # Analyze indexes
    index_result = api.analyze_index_efficiency(
        indexes=indexes,
        tables_sizes=table_sizes,
        export_format="json",
        export_filename="index_analysis.json",
    )
    
    # Check results
    assert index_result is not None
    assert index_result.get("scan_status") == "completed"
    assert index_result.get("total_indexes", 0) > 0
    assert index_result.get("total_index_size_bytes", 0) > 0
    assert len(index_result.get("redundant_indexes", [])) > 0
    assert len(index_result.get("unused_indexes", [])) > 0
    
    # Check that export file was created
    export_file = Path(temp_output_dir) / "index_analysis.json"
    assert export_file.exists()


def test_analyze_tablespace_fragmentation(mock_tablespaces, fragmentation_data, temp_output_dir):
    """Test tablespace fragmentation analysis through API."""
    api = StorageOptimizerAPI(output_dir=temp_output_dir)
    
    # Convert tablespaces to dictionaries
    tablespaces = [ts.dict() for ts in mock_tablespaces]
    assert len(tablespaces) > 0
    
    # Analyze tablespaces
    tablespace_result = api.analyze_tablespace_fragmentation(
        tablespaces=tablespaces,
        fragmentation_data=fragmentation_data,
        export_format="json",
        export_filename="tablespace_analysis.json",
    )
    
    # Check results
    assert tablespace_result is not None
    assert tablespace_result.get("scan_status") == "completed"
    assert tablespace_result.get("total_tablespaces", 0) > 0
    assert tablespace_result.get("total_size_bytes", 0) > 0
    assert tablespace_result.get("free_space_bytes", 0) > 0
    assert len(tablespace_result.get("fragmented_tablespaces", [])) > 0
    assert len(tablespace_result.get("visualization_data", {})) > 0
    
    # Check that export file was created
    export_file = Path(temp_output_dir) / "tablespace_analysis.json"
    assert export_file.exists()


def test_analyze_backup_compression(mock_backup_files, temp_output_dir):
    """Test backup compression analysis through API."""
    api = StorageOptimizerAPI(output_dir=temp_output_dir)
    
    # Analyze backups
    backup_result = api.analyze_backup_compression(
        backups=mock_backup_files,
        export_format="json",
        export_filename="backup_analysis.json",
    )
    
    # Check results
    assert backup_result is not None
    assert backup_result.get("scan_status") == "completed"
    assert backup_result.get("total_backups", 0) > 0
    assert backup_result.get("total_backup_size_bytes", 0) > 0
    assert backup_result.get("total_original_size_bytes", 0) > 0
    assert backup_result.get("overall_compression_ratio", 0) > 0
    assert len(backup_result.get("backups_by_algorithm", {})) > 0
    assert len(backup_result.get("backups_by_strategy", {})) > 0
    
    # Check that export file was created
    export_file = Path(temp_output_dir) / "backup_analysis.json"
    assert export_file.exists()


def test_comprehensive_analysis(mock_data_dir, temp_output_dir):
    """Test comprehensive analysis through API."""
    api = StorageOptimizerAPI(output_dir=temp_output_dir)
    
    # Run comprehensive analysis
    comprehensive_result = api.comprehensive_analysis(
        root_path=mock_data_dir,
        recursive=True,
        export_format="json",
        export_filename="comprehensive_analysis.json",
    )
    
    # Check results
    assert comprehensive_result is not None
    assert "file_analysis" in comprehensive_result
    assert comprehensive_result["file_analysis"].get("scan_status") == "completed"
    assert comprehensive_result["file_analysis"].get("total_files_scanned", 0) > 0
    
    # The following may be present or empty depending on whether log and backup files were found
    assert "log_analysis" in comprehensive_result
    assert "backup_analysis" in comprehensive_result
    
    # Check that export file was created
    export_file = Path(temp_output_dir) / "comprehensive_analysis.json"
    assert export_file.exists()