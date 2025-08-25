"""Tests for the index efficiency analyzer."""

import pytest
from datetime import datetime

from file_system_analyzer_db_admin.index_efficiency.index_analyzer import (
    IndexEfficiencyAnalyzer,
    IndexValueCategory,
)
from file_system_analyzer_db_admin.utils.types import ScanStatus


def test_analyzer_initialization():
    """Test index analyzer initialization."""
    analyzer = IndexEfficiencyAnalyzer()
    assert analyzer is not None
    assert 0 <= analyzer.redundancy_threshold <= 1.0
    assert 0 <= analyzer.space_performance_weight_ratio <= 1.0


def test_detect_redundant_indexes(mock_indexes):
    """Test detection of redundant indexes."""
    analyzer = IndexEfficiencyAnalyzer()
    
    # Detect redundant indexes
    redundant_map = analyzer.detect_redundant_indexes(mock_indexes)
    
    # The "products_redundant_idx" should be identified as redundant with "products_name_idx"
    redundant_name = "products_redundant_idx"
    duplicate_of = "products_name_idx"
    
    redundant_found = False
    for idx_name, redundant_with in redundant_map.items():
        if idx_name == redundant_name and duplicate_of in redundant_with:
            redundant_found = True
            break
    
    assert redundant_found, f"Expected {redundant_name} to be redundant with {duplicate_of}"


def test_calculate_space_performance_ratio(mock_indexes):
    """Test calculation of space to performance ratio."""
    analyzer = IndexEfficiencyAnalyzer()
    table_sizes = {"users": 1073741824}  # 1GB
    
    # Test with performance data
    for idx in mock_indexes:
        if idx.avg_query_time_ms is not None and idx.usage_count is not None:
            ratio = analyzer.calculate_space_performance_ratio(idx, table_sizes.get(idx.table_name))
            assert ratio is not None
            assert ratio > 0
    
    # Test without performance data
    idx_without_perf = mock_indexes[0].copy()
    idx_without_perf.avg_query_time_ms = None
    idx_without_perf.usage_count = None
    
    ratio = analyzer.calculate_space_performance_ratio(idx_without_perf, table_sizes.get(idx_without_perf.table_name))
    assert ratio is not None
    assert ratio > 0


def test_detect_unused_indexes(mock_indexes):
    """Test detection of unused or rarely used indexes."""
    analyzer = IndexEfficiencyAnalyzer(min_usage_threshold=10)
    
    unused_indexes = analyzer.detect_unused_indexes(mock_indexes)
    assert len(unused_indexes) > 0
    
    # "users_unused_idx" should be in the unused list
    assert "users_unused_idx" in unused_indexes
    
    # "products_redundant_idx" should be in the unused list
    assert "products_redundant_idx" in unused_indexes
    
    # Primary keys should not be in the unused list
    assert "users_pk" not in unused_indexes
    assert "products_pk" not in unused_indexes


def test_calculate_index_metrics(mock_indexes):
    """Test calculation of index metrics."""
    analyzer = IndexEfficiencyAnalyzer()
    table_sizes = {"users": 1073741824, "products": 536870912}  # 1GB, 512MB
    
    metrics = analyzer.calculate_index_metrics(mock_indexes, table_sizes)
    assert len(metrics) == len(mock_indexes)
    
    # Check that each index has metrics
    for idx in mock_indexes:
        assert idx.name in metrics
        metric = metrics[idx.name]
        
        assert metric.space_to_performance_ratio is not None
        assert 0 <= metric.redundancy_score <= 1.0
        assert 0 <= metric.optimization_potential <= 1.0
        
        # Check that the redundant index has high redundancy score
        if idx.name == "products_redundant_idx":
            assert metric.redundancy_score > 0.5
            assert len(metric.duplicate_indexes) > 0
            
        # Check that rarely used indexes have high unused score
        if idx.name == "users_unused_idx":
            assert metric.unused_score > 0.8


def test_categorize_indexes(mock_indexes):
    """Test categorization of indexes by value."""
    analyzer = IndexEfficiencyAnalyzer()
    table_sizes = {"users": 1073741824, "products": 536870912}  # 1GB, 512MB
    
    metrics = analyzer.calculate_index_metrics(mock_indexes, table_sizes)
    categories = analyzer.categorize_indexes(metrics)
    
    # Check that all categories exist
    for category in IndexValueCategory:
        assert category in categories
    
    # Check that primary keys are in HIGH_VALUE
    assert "users_pk" in categories[IndexValueCategory.HIGH_VALUE]
    assert "products_pk" in categories[IndexValueCategory.HIGH_VALUE]
    
    # Check that redundant index is in REDUNDANT
    assert "products_redundant_idx" in categories[IndexValueCategory.REDUNDANT]
    
    # Check that unused index is in UNUSED
    assert "users_unused_idx" in categories[IndexValueCategory.UNUSED]


def test_generate_recommendations(mock_indexes):
    """Test generation of optimization recommendations."""
    analyzer = IndexEfficiencyAnalyzer()
    table_sizes = {"users": 1073741824, "products": 536870912}  # 1GB, 512MB
    
    metrics = analyzer.calculate_index_metrics(mock_indexes, table_sizes)
    categories = analyzer.categorize_indexes(metrics)
    
    recommendations = analyzer.generate_recommendations(metrics, categories)
    assert len(recommendations) > 0
    
    # Check for duplicate index recommendation
    has_duplicate_rec = False
    for rec in recommendations:
        if "duplicate" in rec.title.lower() and "products" in rec.title:
            has_duplicate_rec = True
            break
    
    assert has_duplicate_rec, "Expected recommendation for duplicate products indexes"
    
    # Check for unused index recommendation
    has_unused_rec = False
    for rec in recommendations:
        if "unused" in rec.title.lower():
            has_unused_rec = True
            break
    
    assert has_unused_rec, "Expected recommendation for unused indexes"


def test_analyze_indexes(mock_indexes):
    """Test full index analysis workflow."""
    analyzer = IndexEfficiencyAnalyzer()
    table_sizes = {"users": 1073741824, "products": 536870912}  # 1GB, 512MB
    
    analysis_result = analyzer.analyze_indexes(mock_indexes, table_sizes)
    
    # Check result
    assert analysis_result.scan_status == ScanStatus.COMPLETED
    assert analysis_result.total_indexes == len(mock_indexes)
    assert analysis_result.total_index_size_bytes > 0
    assert len(analysis_result.indexes_by_table) == 2  # users and products
    assert len(analysis_result.redundant_indexes) > 0
    assert len(analysis_result.unused_indexes) > 0
    assert len(analysis_result.high_value_indexes) > 0
    assert len(analysis_result.indexes_by_size) == len(mock_indexes)
    assert analysis_result.average_space_to_performance_ratio is not None
    assert analysis_result.total_potential_savings_bytes >= 0
    assert len(analysis_result.recommendations) > 0