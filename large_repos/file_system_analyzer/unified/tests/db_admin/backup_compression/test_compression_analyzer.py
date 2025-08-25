"""Tests for the backup compression analyzer."""

import pytest
from datetime import datetime, timedelta

from file_system_analyzer_db_admin.backup_compression.compression_analyzer import (
    BackupCompressionAnalyzer,
    CompressionAlgorithm,
    BackupStrategy,
)
from file_system_analyzer_db_admin.utils.types import ScanStatus


def test_analyzer_initialization():
    """Test backup compression analyzer initialization."""
    analyzer = BackupCompressionAnalyzer()
    assert analyzer is not None
    assert analyzer.speed_weight + analyzer.space_weight + analyzer.recovery_weight == 1.0
    assert analyzer.min_backups_for_trend > 0
    assert analyzer.retention_policy_days > 0


def test_calculate_compression_metrics(mock_backup_files):
    """Test calculation of compression metrics."""
    analyzer = BackupCompressionAnalyzer()
    
    from file_system_analyzer_db_admin.backup_compression.compression_analyzer import BackupInfo
    
    # Create backup objects from mock data
    backup_objects = []
    for backup_data in mock_backup_files:
        backup_objects.append(BackupInfo(**backup_data))
        
    # Calculate metrics for each backup
    for backup in backup_objects:
        metrics = analyzer.calculate_compression_metrics(backup)
        
        # Check metrics
        assert metrics.compression_ratio > 0
        assert metrics.space_savings_bytes >= 0
        assert 0 <= metrics.space_savings_percent <= 100
        assert metrics.efficiency_score >= 0
        
        # Additional checks for backups with duration data
        if backup.backup_duration_seconds is not None:
            assert metrics.compression_speed_mbps is not None
            assert metrics.compression_speed_mbps > 0
            
        if backup.restore_duration_seconds is not None:
            assert metrics.decompression_speed_mbps is not None
            assert metrics.decompression_speed_mbps > 0


def test_compare_algorithms(mock_backup_files):
    """Test comparison of compression algorithms."""
    analyzer = BackupCompressionAnalyzer()
    
    from file_system_analyzer_db_admin.backup_compression.compression_analyzer import BackupInfo
    
    # Create backup objects from mock data
    backup_objects = []
    for backup_data in mock_backup_files:
        backup_objects.append(BackupInfo(**backup_data))
        
    # Compare all algorithms
    overall_comparison = analyzer.compare_algorithms(backup_objects)
    
    # Check comparison results
    assert len(overall_comparison.algorithms) > 0
    assert len(overall_comparison.compression_ratios) > 0
    assert len(overall_comparison.space_savings) > 0
    assert overall_comparison.best_space_efficiency is not None
    assert overall_comparison.best_speed_efficiency is not None
    assert overall_comparison.best_overall is not None
    
    # Compare filtered by engine
    mysql_comparison = analyzer.compare_algorithms(
        backup_objects, 
        filter_engine="mysql"
    )
    
    # Should only include MySQL backups
    assert all(alg in [b.compression_algorithm for b in backup_objects if b.engine == "mysql"] 
              for alg in mysql_comparison.algorithms)


def test_analyze_retention_efficiency(mock_backup_files):
    """Test analysis of backup retention efficiency."""
    analyzer = BackupCompressionAnalyzer()
    
    from file_system_analyzer_db_admin.backup_compression.compression_analyzer import BackupInfo
    
    # Create backup objects from mock data
    backup_objects = []
    for backup_data in mock_backup_files:
        backup_objects.append(BackupInfo(**backup_data))
        
    # Analyze retention
    retention_analysis = analyzer.analyze_retention_efficiency(backup_objects)
    
    # Check retention analysis
    assert "retention_periods" in retention_analysis
    assert "optimal_strategy" in retention_analysis
    
    # Check retention periods
    retention_periods = retention_analysis["retention_periods"]
    assert "7" in retention_periods  # Should have 7-day retention data
    assert "30" in retention_periods  # Should have 30-day retention data
    assert "90" in retention_periods  # Should have 90-day retention data
    
    # Check optimal strategy
    optimal_strategy = retention_analysis["optimal_strategy"]
    assert "recommended_full_retention_days" in optimal_strategy or "recommended_retention_days" in optimal_strategy
    assert "estimated_storage_bytes" in optimal_strategy


def test_generate_recommendations(mock_backup_files):
    """Test generation of backup optimization recommendations."""
    analyzer = BackupCompressionAnalyzer()
    
    from file_system_analyzer_db_admin.backup_compression.compression_analyzer import BackupInfo
    
    # Create backup objects from mock data
    backup_objects = []
    for backup_data in mock_backup_files:
        backup_objects.append(BackupInfo(**backup_data))
        
    # Compare algorithms
    comparisons = {
        "mysql": analyzer.compare_algorithms(backup_objects, filter_engine="mysql"),
        "postgresql": analyzer.compare_algorithms(backup_objects, filter_engine="postgresql"),
        "mongodb": analyzer.compare_algorithms(backup_objects, filter_engine="mongodb"),
    }
    
    # Generate recommendations
    recommendations = analyzer.generate_recommendations(backup_objects, comparisons)
    
    # Check recommendations
    assert len(recommendations) > 0
    
    # Check for algorithm recommendation
    has_algorithm_rec = False
    for rec in recommendations:
        if "compression algorithm" in rec.title.lower():
            has_algorithm_rec = True
            break
            
    assert has_algorithm_rec, "Expected recommendation for compression algorithm"
    
    # Check for incremental backup recommendation
    # Find if there are only full backups for any engine
    only_full_backups = False
    backup_strategies = {}
    for backup in backup_objects:
        if backup.engine not in backup_strategies:
            backup_strategies[backup.engine] = set()
        backup_strategies[backup.engine].add(backup.backup_strategy)
        
    for engine, strategies in backup_strategies.items():
        if len(strategies) == 1 and BackupStrategy.FULL in strategies:
            only_full_backups = True
            break
            
    if only_full_backups:
        has_incremental_rec = False
        for rec in recommendations:
            if "incremental backup" in rec.title.lower() or "incremental backup" in rec.description.lower():
                has_incremental_rec = True
                break
                
        assert has_incremental_rec, "Expected recommendation for incremental backups"


def test_analyze_backup_compression(mock_backup_files):
    """Test full backup compression analysis workflow."""
    analyzer = BackupCompressionAnalyzer()
    
    from file_system_analyzer_db_admin.backup_compression.compression_analyzer import BackupInfo
    
    # Create backup objects from mock data
    backup_objects = []
    for backup_data in mock_backup_files:
        backup_objects.append(BackupInfo(**backup_data))
        
    # Run analysis
    analysis_result = analyzer.analyze_backup_compression(backup_objects)
    
    # Check result
    assert analysis_result.scan_status == ScanStatus.COMPLETED
    assert analysis_result.total_backups == len(backup_objects)
    assert analysis_result.total_backup_size_bytes > 0
    assert analysis_result.total_original_size_bytes > 0
    assert analysis_result.overall_compression_ratio > 0
    assert analysis_result.overall_space_savings_bytes > 0
    assert len(analysis_result.backups_by_algorithm) > 0
    assert len(analysis_result.backups_by_strategy) > 0
    assert len(analysis_result.algorithm_metrics) > 0
    assert len(analysis_result.strategy_metrics) > 0
    assert len(analysis_result.best_algorithms) > 0
    assert len(analysis_result.efficiency_by_database_type) > 0
    assert len(analysis_result.recommendations) > 0
    
    # Check that each algorithm has metrics
    for algorithm in set(b.compression_algorithm for b in backup_objects):
        assert algorithm.value in analysis_result.algorithm_metrics
        
    # Check that each strategy has metrics
    for strategy in set(b.backup_strategy for b in backup_objects):
        assert strategy.value in analysis_result.strategy_metrics