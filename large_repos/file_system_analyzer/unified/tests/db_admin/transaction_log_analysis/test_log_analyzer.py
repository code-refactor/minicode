"""Tests for the transaction log analyzer."""

import pytest
from datetime import datetime, timedelta

from file_system_analyzer_db_admin.transaction_log_analysis.log_analyzer import (
    TransactionLogAnalyzer,
    LogGrowthPattern,
    LogGrowthCorrelation,
    LogRetentionStrategy,
)
from file_system_analyzer_db_admin.utils.types import DatabaseEngine, FileCategory, ScanStatus


def test_analyzer_initialization():
    """Test log analyzer initialization."""
    analyzer = TransactionLogAnalyzer()
    assert analyzer is not None
    assert analyzer.min_history_days > 0
    assert 0 < analyzer.correlation_confidence_threshold <= 1.0


def test_analyze_log_files(mock_database_files):
    """Test analysis of log files."""
    analyzer = TransactionLogAnalyzer()
    
    # Filter log files
    log_files = [f for f in mock_database_files if f.category == FileCategory.LOG]
    assert len(log_files) > 0
    
    # Analyze log files
    log_stats = analyzer.analyze_log_files(log_files)
    assert len(log_stats) == len(log_files)
    
    for stat in log_stats:
        assert "path" in stat
        assert "engine" in stat
        assert "size_bytes" in stat
        assert stat["size_bytes"] > 0


def test_detect_growth_pattern():
    """Test detection of log growth patterns."""
    analyzer = TransactionLogAnalyzer(growth_pattern_detection_min_samples=3)
    now = datetime.now()
    
    # Linear growth
    linear_history = [
        (now - timedelta(days=5), 100),
        (now - timedelta(days=4), 200),
        (now - timedelta(days=3), 300),
        (now - timedelta(days=2), 400),
        (now - timedelta(days=1), 500),
    ]
    pattern, confidence = analyzer.detect_growth_pattern(linear_history)
    assert pattern == LogGrowthPattern.LINEAR
    assert confidence > 0.9
    
    # Exponential growth
    exponential_history = [
        (now - timedelta(days=5), 100),
        (now - timedelta(days=4), 200),
        (now - timedelta(days=3), 400),
        (now - timedelta(days=2), 800),
        (now - timedelta(days=1), 1600),
    ]
    pattern, confidence = analyzer.detect_growth_pattern(exponential_history)
    assert pattern == LogGrowthPattern.EXPONENTIAL
    assert confidence > 0.8
    
    # Stable pattern
    stable_history = [
        (now - timedelta(days=5), 100),
        (now - timedelta(days=4), 100),
        (now - timedelta(days=3), 100),
        (now - timedelta(days=2), 100),
        (now - timedelta(days=1), 100),
    ]
    pattern, confidence = analyzer.detect_growth_pattern(stable_history)
    assert pattern == LogGrowthPattern.STABLE
    assert confidence > 0.9
    
    # Too few samples
    few_samples = [
        (now - timedelta(days=2), 100),
        (now - timedelta(days=1), 200),
    ]
    pattern, confidence = analyzer.detect_growth_pattern(few_samples)
    assert pattern == LogGrowthPattern.UNKNOWN
    assert confidence == 0.0


def test_correlate_with_operations():
    """Test correlation of log growth with operations."""
    analyzer = TransactionLogAnalyzer()
    
    # Sample log growth rates
    log_growth_rates = [10, 20, 30, 40, 50]
    
    # Sample operation frequencies that correlate well
    high_correlation_ops = {
        "INSERT": [100, 200, 300, 400, 500],  # Perfect correlation
        "UPDATE": [90, 180, 270, 360, 450],   # Strong correlation
    }
    
    # Sample operation frequencies with weak correlation
    weak_correlation_ops = {
        "DELETE": [10, 20, 10, 20, 10],       # Weak correlation
        "BACKUP": [500, 100, 300, 200, 400],  # Negative correlation
    }
    
    # Test correlations
    high_corr_result = analyzer.correlate_with_operations(
        DatabaseEngine.MYSQL,
        log_growth_rates,
        high_correlation_ops
    )
    
    weak_corr_result = analyzer.correlate_with_operations(
        DatabaseEngine.MYSQL,
        log_growth_rates,
        weak_correlation_ops
    )
    
    # Check results
    assert "INSERT" in high_corr_result
    assert high_corr_result["INSERT"] == LogGrowthCorrelation.HIGH
    
    assert "UPDATE" in high_corr_result
    assert high_corr_result["UPDATE"] == LogGrowthCorrelation.HIGH
    
    assert "DELETE" in weak_corr_result
    assert weak_corr_result["DELETE"] in [LogGrowthCorrelation.LOW, LogGrowthCorrelation.MEDIUM]
    
    # Test with empty inputs
    empty_result = analyzer.correlate_with_operations(
        DatabaseEngine.MYSQL,
        [],
        {}
    )
    assert empty_result == {}


def test_generate_retention_recommendations():
    """Test generation of retention policy recommendations."""
    analyzer = TransactionLogAnalyzer()
    
    # High growth rate, exponential pattern
    high_growth_recommendations = analyzer.generate_retention_recommendations(
        engine=DatabaseEngine.MYSQL,
        growth_pattern=LogGrowthPattern.EXPONENTIAL,
        growth_rate_bytes_per_day=2_000_000_000,  # 2GB/day
        total_log_size_bytes=10_000_000_000,  # 10GB
    )
    
    assert len(high_growth_recommendations) > 0
    assert any(r.priority.value == "high" for r in high_growth_recommendations)
    
    # Low growth rate, stable pattern
    low_growth_recommendations = analyzer.generate_retention_recommendations(
        engine=DatabaseEngine.POSTGRESQL,
        growth_pattern=LogGrowthPattern.STABLE,
        growth_rate_bytes_per_day=10_000_000,  # 10MB/day
        total_log_size_bytes=1_000_000_000,  # 1GB
    )
    
    assert len(low_growth_recommendations) > 0
    assert all(r.priority.value != "high" for r in low_growth_recommendations)


def test_analyze_logs(mock_database_files):
    """Test full log analysis workflow."""
    analyzer = TransactionLogAnalyzer()
    
    # Filter log files
    log_files = [f for f in mock_database_files if f.category == FileCategory.LOG]
    assert len(log_files) > 0
    
    # Create sample historical sizes
    now = datetime.now()
    historical_sizes = {}
    
    for log_file in log_files:
        # Assume linear growth for test
        historical_sizes[log_file.path] = [
            (now - timedelta(days=5), int(log_file.size_bytes * 0.5)),
            (now - timedelta(days=4), int(log_file.size_bytes * 0.6)),
            (now - timedelta(days=3), int(log_file.size_bytes * 0.7)),
            (now - timedelta(days=2), int(log_file.size_bytes * 0.8)),
            (now - timedelta(days=1), int(log_file.size_bytes * 0.9)),
            (now, log_file.size_bytes),
        ]
    
    # Sample operation frequencies
    operation_frequencies = {
        "mysql": {
            "INSERT": [1000, 1200, 1400, 1600, 1800, 2000],
            "UPDATE": [500, 600, 700, 800, 900, 1000],
        },
        "postgresql": {
            "INSERT": [800, 1000, 1200, 1400, 1600, 1800],
            "UPDATE": [400, 500, 600, 700, 800, 900],
        }
    }
    
    # Run analysis
    analysis_result = analyzer.analyze_logs(
        log_files=log_files,
        historical_sizes=historical_sizes,
        operation_frequencies=operation_frequencies
    )
    
    # Check result
    assert analysis_result.scan_status == ScanStatus.COMPLETED
    assert analysis_result.total_log_size_bytes > 0
    assert analysis_result.growth_rate_bytes_per_day > 0
    assert analysis_result.dominant_growth_pattern is not None
    assert 0 <= analysis_result.growth_pattern_confidence <= 1.0
    assert len(analysis_result.log_files) == len(log_files)
    assert len(analysis_result.recommendations) > 0