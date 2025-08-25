"""Tests for the tablespace fragmentation analyzer."""

import pytest
from datetime import datetime

from file_system_analyzer_db_admin.tablespace_fragmentation.fragmentation_analyzer import (
    TablespaceFragmentationAnalyzer,
    FragmentationType,
    FragmentationSeverity,
    SpaceDistributionType,
    TablespaceInfo,
)
from file_system_analyzer_db_admin.utils.types import ScanStatus


def test_analyzer_initialization():
    """Test fragmentation analyzer initialization."""
    analyzer = TablespaceFragmentationAnalyzer()
    assert analyzer is not None
    assert analyzer.critical_fragmentation_threshold > analyzer.high_fragmentation_threshold
    assert analyzer.high_fragmentation_threshold > analyzer.moderate_fragmentation_threshold
    assert analyzer.visualization_resolution > 0


def test_detect_fragmentation_severity():
    """Test detection of fragmentation severity."""
    analyzer = TablespaceFragmentationAnalyzer(
        critical_fragmentation_threshold=40.0,
        high_fragmentation_threshold=25.0,
        moderate_fragmentation_threshold=15.0,
    )
    
    # Test different levels
    assert analyzer.detect_fragmentation_severity(50.0) == FragmentationSeverity.CRITICAL
    assert analyzer.detect_fragmentation_severity(30.0) == FragmentationSeverity.HIGH
    assert analyzer.detect_fragmentation_severity(20.0) == FragmentationSeverity.MODERATE
    assert analyzer.detect_fragmentation_severity(10.0) == FragmentationSeverity.LOW
    assert analyzer.detect_fragmentation_severity(3.0) == FragmentationSeverity.NEGLIGIBLE


def test_analyze_free_space_distribution():
    """Test analysis of free space distribution patterns."""
    analyzer = TablespaceFragmentationAnalyzer()
    
    # Uniform distribution (one large chunk)
    uniform_chunks = [1073741824]  # One 1GB chunk
    assert analyzer.analyze_free_space_distribution(uniform_chunks, 1073741824) == SpaceDistributionType.UNIFORM
    
    # Clustered distribution (a few large chunks)
    clustered_chunks = [805306368, 268435456]  # 768MB and 256MB chunks
    assert analyzer.analyze_free_space_distribution(clustered_chunks, 1073741824) == SpaceDistributionType.CLUSTERED
    
    # Scattered distribution (many small chunks)
    scattered_chunks = [1048576] * 100  # 100 chunks of 1MB each
    assert analyzer.analyze_free_space_distribution(scattered_chunks, 104857600) == SpaceDistributionType.SCATTERED
    
    # Depleted (almost no free space)
    depleted_chunks = [102400, 51200]  # Two tiny chunks (100KB, 50KB)
    assert analyzer.analyze_free_space_distribution(depleted_chunks, 153600) == SpaceDistributionType.DEPLETED
    
    # Empty list
    assert analyzer.analyze_free_space_distribution([], 0) == SpaceDistributionType.DEPLETED


def test_estimate_reorganization_benefit():
    """Test estimation of reorganization benefit."""
    analyzer = TablespaceFragmentationAnalyzer()
    
    # High internal fragmentation with scattered free space
    high_internal_scattered = analyzer.estimate_reorganization_benefit(
        fragmentation_percent=30.0,
        fragmentation_type=FragmentationType.INTERNAL,
        free_space_distribution=SpaceDistributionType.SCATTERED,
    )
    
    # Moderate external fragmentation with clustered free space
    moderate_external_clustered = analyzer.estimate_reorganization_benefit(
        fragmentation_percent=15.0,
        fragmentation_type=FragmentationType.EXTERNAL,
        free_space_distribution=SpaceDistributionType.CLUSTERED,
    )
    
    # Low mixed fragmentation with uniform free space
    low_mixed_uniform = analyzer.estimate_reorganization_benefit(
        fragmentation_percent=5.0,
        fragmentation_type=FragmentationType.MIXED,
        free_space_distribution=SpaceDistributionType.UNIFORM,
    )
    
    # Check relative values
    assert high_internal_scattered > moderate_external_clustered
    assert moderate_external_clustered > low_mixed_uniform
    assert 0 <= high_internal_scattered <= 80.0
    assert 0 <= moderate_external_clustered <= 80.0
    assert 0 <= low_mixed_uniform <= 80.0


def test_calculate_optimal_fill_factor():
    """Test calculation of optimal fill factor."""
    analyzer = TablespaceFragmentationAnalyzer()
    
    # High fragmentation, fast growth
    high_frag_fast_growth = analyzer.calculate_optimal_fill_factor(
        current_fragmentation=35.0,
        growth_rate_bytes_per_day=10485760,  # 10MB/day
        total_size_bytes=1073741824,  # 1GB
        free_space_bytes=268435456,  # 256MB
    )
    
    # Low fragmentation, slow growth
    low_frag_slow_growth = analyzer.calculate_optimal_fill_factor(
        current_fragmentation=5.0,
        growth_rate_bytes_per_day=1048576,  # 1MB/day
        total_size_bytes=1073741824,  # 1GB
        free_space_bytes=268435456,  # 256MB
    )
    
    # Check values
    assert 50.0 <= high_frag_fast_growth <= 95.0
    assert 50.0 <= low_frag_slow_growth <= 95.0
    assert high_frag_fast_growth < low_frag_slow_growth  # High fragmentation should lead to lower fill factor


def test_generate_visualization_data(mock_tablespaces, fragmentation_data):
    """Test generation of visualization data."""
    analyzer = TablespaceFragmentationAnalyzer()
    
    # Get a tablespace and its fragmentation data
    tablespace = mock_tablespaces[0]  # USERS_TS
    ts_frag_data = fragmentation_data[tablespace.name]
    
    # Generate visualization
    vis_data = analyzer.generate_visualization_data(tablespace, ts_frag_data)
    
    # Check visualization data
    assert len(vis_data.x) > 0
    assert len(vis_data.y) > 0
    assert len(vis_data.width) > 0
    assert len(vis_data.height) > 0
    assert len(vis_data.type) > 0
    assert len(vis_data.size_bytes) > 0
    assert len(vis_data.x) == len(vis_data.y) == len(vis_data.width) == len(vis_data.height) == len(vis_data.type) == len(vis_data.size_bytes)
    
    # Check data types
    assert all(0 <= x <= 1 for x in vis_data.x)  # Normalized positions
    assert all(0 <= w <= 1 for w in vis_data.width)  # Normalized widths
    assert all(t in ["data", "free"] for t in vis_data.type)


def test_generate_recommendations(mock_tablespaces, fragmentation_data):
    """Test generation of optimization recommendations."""
    analyzer = TablespaceFragmentationAnalyzer()
    
    # Create metrics for tablespaces
    metrics_list = []
    
    for tablespace in mock_tablespaces:
        ts_data = fragmentation_data.get(tablespace.name, {})
        
        # Use data from fragmentation_data fixture
        fragmentation_percent = ts_data.get("fragmentation_percent", 0.0)
        frag_type_str = ts_data.get("fragmentation_type", "mixed")
        fragmentation_type = getattr(FragmentationType, frag_type_str.upper(), FragmentationType.MIXED)
        
        free_chunks = ts_data.get("free_chunks_sizes", [])
        free_space_distribution = analyzer.analyze_free_space_distribution(
            free_chunks, tablespace.free_size_bytes
        )
        
        severity = analyzer.detect_fragmentation_severity(fragmentation_percent)
        growth_trend = ts_data.get("growth_bytes_per_day")
        
        days_until_full = None
        if growth_trend and growth_trend > 0 and tablespace.free_size_bytes > 0:
            days_until_full = int(tablespace.free_size_bytes / growth_trend)
            
        optimal_fill_factor = analyzer.calculate_optimal_fill_factor(
            fragmentation_percent, growth_trend,
            tablespace.total_size_bytes, tablespace.free_size_bytes
        )
        
        reorganization_benefit = analyzer.estimate_reorganization_benefit(
            fragmentation_percent, fragmentation_type, free_space_distribution
        )
        
        # Create metric object
        from file_system_analyzer_db_admin.tablespace_fragmentation.fragmentation_analyzer import FragmentationMetrics
        metrics = FragmentationMetrics(
            tablespace=tablespace,
            fragmentation_percent=fragmentation_percent,
            fragmentation_type=fragmentation_type,
            severity=severity,
            free_space_distribution=free_space_distribution,
            largest_contiguous_free_chunk_bytes=max(free_chunks) if free_chunks else 0,
            free_chunks_count=len(free_chunks),
            avg_free_chunk_size_bytes=sum(free_chunks) / len(free_chunks) if free_chunks else 0,
            growth_trend_bytes_per_day=growth_trend,
            days_until_full=days_until_full,
            optimal_fill_factor=optimal_fill_factor,
            estimated_reorganization_benefit_percent=reorganization_benefit,
        )
        
        metrics_list.append(metrics)
    
    # Generate recommendations
    recommendations = analyzer.generate_recommendations(metrics_list)
    
    # There should be recommendations for highly fragmented tablespaces
    assert len(recommendations) > 0
    
    # ORDERS_TS has critical fragmentation (45%) and should have high priority recommendation
    has_critical_rec = False
    for rec in recommendations:
        if "ORDERS_TS" in rec.description and rec.priority.value == "high":
            has_critical_rec = True
            break
            
    assert has_critical_rec, "Expected high priority recommendation for ORDERS_TS"


def test_analyze_tablespace_fragmentation(mock_tablespaces, fragmentation_data):
    """Test full tablespace fragmentation analysis workflow."""
    analyzer = TablespaceFragmentationAnalyzer()
    
    analysis_result = analyzer.analyze_tablespace_fragmentation(
        tablespaces=mock_tablespaces,
        fragmentation_data=fragmentation_data,
    )
    
    # Check result
    assert analysis_result.scan_status == ScanStatus.COMPLETED
    assert analysis_result.total_tablespaces == len(mock_tablespaces)
    assert analysis_result.total_size_bytes > 0
    assert analysis_result.free_space_bytes > 0
    assert len(analysis_result.fragmented_tablespaces) == len(mock_tablespaces)
    assert len(analysis_result.tablespaces_by_severity) > 0
    assert analysis_result.total_reorganization_benefit_bytes >= 0
    assert len(analysis_result.visualization_data) == len(mock_tablespaces)
    assert analysis_result.estimated_recovery_time_hours > 0
    assert len(analysis_result.recommendations) > 0