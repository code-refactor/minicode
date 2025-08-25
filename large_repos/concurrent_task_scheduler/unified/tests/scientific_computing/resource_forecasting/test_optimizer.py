"""Tests for the resource optimization module."""

from datetime import datetime, timedelta

import pytest
import numpy as np

from concurrent_task_scheduler.models import (
    ResourceType,
    Simulation,
    SimulationStage,
    SimulationStageStatus,
    SimulationPriority,
    SimulationStatus,
    ForecastPeriod,
    ResourceForecast,
    ResourceProjection,
)

# Mock simulation class that overrides total_progress
class MockSimulation(Simulation):
    def total_progress(self) -> float:
        # Always return 0.5 for testing
        return 0.5

from concurrent_task_scheduler.resource_forecasting.data_collector import (
    ResourceDataCollector,
)
from concurrent_task_scheduler.resource_forecasting.forecaster import (
    ResourceForecaster,
)
from concurrent_task_scheduler.resource_forecasting.optimizer import (
    ResourceOptimizer,
    OptimizationGoal,
    OptimizationTimeframe,
    ResourceAllocationRecommendation,
    CapacityPlanningRecommendation,
)


@pytest.fixture
def resource_data_collector():
    """Create a resource data collector for testing."""
    return ResourceDataCollector(storage_capacity=1000)


@pytest.fixture
def resource_forecaster(resource_data_collector):
    """Create a resource forecaster for testing."""
    return ResourceForecaster(resource_data_collector)


@pytest.fixture
def resource_optimizer(resource_forecaster):
    """Create a resource optimizer for testing."""
    return ResourceOptimizer(resource_forecaster)


@pytest.fixture
def sample_simulation():
    """Create a sample simulation for testing."""
    # Create a simulation with stages
    stages = {}
    
    # Add a preprocessing stage
    preprocessing = SimulationStage(
        id="stage_preprocess",
        name="Data Preprocessing",
        progress=1.0,  # 100% complete
        status=SimulationStageStatus.COMPLETED,
        start_time=datetime.now() - timedelta(hours=2),
        end_time=datetime.now() - timedelta(hours=1),
        estimated_duration=timedelta(hours=1),
    )
    stages[preprocessing.id] = preprocessing
    
    # Add a main simulation stage
    main_stage = SimulationStage(
        id="stage_main",
        name="Main Simulation",
        progress=0.5,  # 50% complete
        status=SimulationStageStatus.RUNNING,
        start_time=datetime.now() - timedelta(hours=1),
        estimated_duration=timedelta(hours=2),
    )
    stages[main_stage.id] = main_stage
    
    # Create the simulation
    simulation = MockSimulation(
        id="sim_optimizer_test",
        name="Optimizer Test Simulation",
        creation_time=datetime.now() - timedelta(hours=3),
        status=SimulationStatus.RUNNING,
        priority=SimulationPriority.HIGH,
        stages=stages,
    )
    
    return simulation


@pytest.fixture
def sample_resource_projection():
    """Create a sample resource projection for testing."""
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    # Create forecasts for each resource type
    resource_projections = {}
    
    for resource_type in ResourceType:
        # Create a simple forecast with increasing values
        forecasted_values = {}
        confidence_intervals = {}
        
        for i in range(30):
            date_str = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            value = 0.5 + (i / 60.0)  # Gradual increase
            forecasted_values[date_str] = value
            confidence_intervals[date_str] = (value * 0.9, value * 1.1)
        
        forecast = ResourceForecast(
            start_date=start_date,
            end_date=end_date,
            period=ForecastPeriod.DAILY,
            resource_type=resource_type,
            forecasted_values=forecasted_values,
            confidence_intervals=confidence_intervals,
        )
        
        resource_projections[resource_type] = forecast
    
    # Create the projection
    projection = ResourceProjection(
        project_id="project001",
        project_name="Test Project",
        start_date=start_date,
        end_date=end_date,
        resource_projections=resource_projections,
        total_cost_estimate=5000.0,
        cost_breakdown={
            "cpu": 2000.0,
            "memory": 1500.0,
            "storage": 1000.0,
            "network": 500.0,
        },
        narrative="Resource projection for testing",
    )
    
    return projection


def test_optimizer_init(resource_optimizer):
    """Test initialization of resource optimizer."""
    assert hasattr(resource_optimizer, 'forecaster')
    assert isinstance(resource_optimizer.allocation_recommendations, dict)
    assert isinstance(resource_optimizer.capacity_recommendations, dict)
    assert isinstance(resource_optimizer.utilization_targets, dict)
    assert isinstance(resource_optimizer.buffer_factors, dict)
    
    # Check if utilization targets are set for all resource types
    for resource_type in ResourceType:
        assert resource_type in resource_optimizer.utilization_targets
    
    # Check if buffer factors are set for all timeframes
    for timeframe in OptimizationTimeframe:
        assert timeframe in resource_optimizer.buffer_factors


def test_optimize_simulation_resources(resource_optimizer, sample_simulation, resource_forecaster):
    """Test optimizing resources for a simulation."""
    # Add some historical data for forecasting
    start_date = datetime.now() - timedelta(days=30)
    for i in range(30 * 24):
        timestamp = start_date + timedelta(hours=i)
        for resource_type in ResourceType:
            # Create patterns specific to each resource type
            if resource_type == ResourceType.CPU:
                value = 0.5 + (i / (30 * 24)) * 0.2  # Gradual increase
            elif resource_type == ResourceType.MEMORY:
                value = 0.7 - (i / (30 * 24)) * 0.1  # Gradual decrease
            elif resource_type == ResourceType.STORAGE:
                value = 0.6  # Constant
            else:  # NETWORK
                value = 0.4 + np.sin(i / 24 * np.pi) * 0.2  # Sinusoidal
            
            # Add some noise
            value += np.random.normal(0, 0.05)
            value = max(0.1, min(0.9, value))
            
            resource_forecaster.data_collector.record_data_point(
                resource_type=resource_type,
                utilization=value,
                capacity=1.0,
                timestamp=timestamp,
                simulation_id=sample_simulation.id,
            )
    
    # Test optimization with different goals
    for goal in OptimizationGoal:
        result = resource_optimizer.optimize_simulation_resources(
            simulation=sample_simulation,
            goal=goal,
            timeframe=OptimizationTimeframe.SHORT_TERM,
        )
        
        assert result.success
        recommendations = result.value
        
        # Recommendations might be empty if no significant changes are needed
        if recommendations:
            for rec in recommendations:
                assert isinstance(rec, ResourceAllocationRecommendation)
                assert rec.simulation_id == sample_simulation.id
                assert rec.resource_type in ResourceType
                assert rec.current_allocation > 0
                assert rec.recommended_allocation > 0
                assert 0.0 <= rec.confidence <= 1.0
                assert rec.justification
                assert rec.impact_estimate
                assert rec.timeframe == OptimizationTimeframe.SHORT_TERM
    
    # Test with different timeframes
    for timeframe in OptimizationTimeframe:
        result = resource_optimizer.optimize_simulation_resources(
            simulation=sample_simulation,
            goal=OptimizationGoal.BALANCE,
            timeframe=timeframe,
        )
        
        assert result.success


def test_generate_capacity_plan(resource_optimizer, sample_resource_projection):
    """Test generating capacity planning recommendations."""
    result = resource_optimizer.generate_capacity_plan(
        resource_projection=sample_resource_projection,
        timeframe=OptimizationTimeframe.MEDIUM_TERM,
    )
    
    assert result.success
    recommendations = result.value
    
    # Should have recommendations for most resource types
    assert len(recommendations) > 0
    
    for rec in recommendations:
        assert isinstance(rec, CapacityPlanningRecommendation)
        assert rec.resource_type in ResourceType
        assert rec.current_capacity > 0
        assert rec.recommended_capacity > 0
        assert rec.recommended_buffer > 1.0  # Buffer should be > 100%
        assert 0.0 <= rec.confidence <= 1.0
        assert rec.justification
        assert isinstance(rec.cost_impact, float)
        assert rec.timeframe == OptimizationTimeframe.MEDIUM_TERM
        assert not rec.implemented  # Should start as not implemented
    
    # Test with different timeframes
    for timeframe in OptimizationTimeframe:
        result = resource_optimizer.generate_capacity_plan(
            resource_projection=sample_resource_projection,
            timeframe=timeframe,
        )
        
        assert result.success


def test_resource_allocation_recommendation():
    """Test the ResourceAllocationRecommendation class."""
    # Create a recommendation
    rec = ResourceAllocationRecommendation(
        simulation_id="sim001",
        resource_type=ResourceType.CPU,
        current_allocation=32.0,
        recommended_allocation=40.0,
        confidence=0.8,
        justification="Increased resource needs based on forecast",
        impact_estimate="20% performance improvement expected",
        timeframe=OptimizationTimeframe.SHORT_TERM,
    )
    
    # Check attributes
    assert rec.simulation_id == "sim001"
    assert rec.resource_type == ResourceType.CPU
    assert rec.current_allocation == 32.0
    assert rec.recommended_allocation == 40.0
    assert rec.confidence == 0.8
    assert rec.justification == "Increased resource needs based on forecast"
    assert rec.impact_estimate == "20% performance improvement expected"
    assert rec.timeframe == OptimizationTimeframe.SHORT_TERM
    assert not rec.implemented
    assert rec.implementation_time is None
    assert rec.actual_impact is None
    
    # Test mark_implemented
    rec.mark_implemented("15% performance improvement observed")
    
    assert rec.implemented
    assert rec.implementation_time is not None
    assert rec.actual_impact == "15% performance improvement observed"
    
    # Test to_dict
    rec_dict = rec.to_dict()
    
    assert rec_dict["simulation_id"] == "sim001"
    assert rec_dict["resource_type"] == "cpu"
    assert rec_dict["current_allocation"] == 32.0
    assert rec_dict["recommended_allocation"] == 40.0
    assert rec_dict["percent_change"] == 25.0  # (40-32)/32 * 100
    assert rec_dict["confidence"] == 0.8
    assert rec_dict["justification"] == "Increased resource needs based on forecast"
    assert rec_dict["impact_estimate"] == "20% performance improvement expected"
    assert rec_dict["timeframe"] == "short_term"
    assert rec_dict["implemented"]
    assert "implementation_time" in rec_dict
    assert rec_dict["actual_impact"] == "15% performance improvement observed"


def test_capacity_planning_recommendation():
    """Test the CapacityPlanningRecommendation class."""
    # Create a recommendation
    rec = CapacityPlanningRecommendation(
        resource_type=ResourceType.MEMORY,
        current_capacity=1024.0,
        forecasted_need=1200.0,
        recommended_capacity=1500.0,
        recommended_buffer=1.25,
        confidence=0.85,
        justification="Memory capacity increase needed based on forecast",
        cost_impact=2000.0,
        timeframe=OptimizationTimeframe.MEDIUM_TERM,
    )
    
    # Check attributes
    assert rec.resource_type == ResourceType.MEMORY
    assert rec.current_capacity == 1024.0
    assert rec.forecasted_need == 1200.0
    assert rec.recommended_capacity == 1500.0
    assert rec.recommended_buffer == 1.25
    assert rec.confidence == 0.85
    assert rec.justification == "Memory capacity increase needed based on forecast"
    assert rec.cost_impact == 2000.0
    assert rec.timeframe == OptimizationTimeframe.MEDIUM_TERM
    assert not rec.implemented
    assert rec.implementation_time is None
    
    # Test mark_implemented
    rec.mark_implemented()
    
    assert rec.implemented
    assert rec.implementation_time is not None
    
    # Test to_dict
    rec_dict = rec.to_dict()
    
    assert rec_dict["resource_type"] == "memory"
    assert rec_dict["current_capacity"] == 1024.0
    assert rec_dict["forecasted_need"] == 1200.0
    assert rec_dict["recommended_capacity"] == 1500.0
    assert rec_dict["recommended_buffer"] == 1.25
    assert rec_dict["confidence"] == 0.85
    assert rec_dict["justification"] == "Memory capacity increase needed based on forecast"
    assert rec_dict["cost_impact"] == 2000.0
    assert rec_dict["timeframe"] == "medium_term"
    assert rec_dict["implemented"]
    assert "implementation_time" in rec_dict


def test_resource_cost(resource_optimizer):
    """Test getting resource costs."""
    for resource_type in ResourceType:
        cost = resource_optimizer._get_resource_cost(resource_type)
        assert cost > 0


def test_mock_allocation_and_capacity(resource_optimizer, sample_simulation):
    """Test getting mock allocations and capacities."""
    # Test getting current allocation
    for resource_type in ResourceType:
        allocation = resource_optimizer._get_current_allocation(
            simulation=sample_simulation,
            resource_type=resource_type,
        )
        assert allocation is not None
        assert allocation > 0
    
    # Test getting current capacity
    for resource_type in ResourceType:
        capacity = resource_optimizer._get_current_capacity(resource_type)
        assert capacity is not None
        assert capacity > 0
    
    # Current capacity should be greater than allocation
    for resource_type in ResourceType:
        allocation = resource_optimizer._get_current_allocation(
            simulation=sample_simulation,
            resource_type=resource_type,
        )
        capacity = resource_optimizer._get_current_capacity(resource_type)
        assert capacity > allocation


def test_justification_generation(resource_optimizer):
    """Test generating justifications for recommendations."""
    # Test allocation justification
    for resource_type in ResourceType:
        for goal in OptimizationGoal:
            for timeframe in OptimizationTimeframe:
                # Test with increase
                justification = resource_optimizer._generate_justification(
                    resource_type=resource_type,
                    current=100.0,
                    recommended=120.0,
                    forecasted=110.0,
                    goal=goal,
                    timeframe=timeframe,
                )
                
                assert "increase" in justification.lower()
                assert resource_type.value in justification.lower()
                assert "20.0%" in justification  # (120-100)/100 * 100
                
                # Test with decrease
                justification = resource_optimizer._generate_justification(
                    resource_type=resource_type,
                    current=100.0,
                    recommended=80.0,
                    forecasted=70.0,
                    goal=goal,
                    timeframe=timeframe,
                )
                
                assert "decrease" in justification.lower()
                assert resource_type.value in justification.lower()
                assert "20.0%" in justification  # (100-80)/100 * 100
    
    # Test capacity justification
    for resource_type in ResourceType:
        for timeframe in OptimizationTimeframe:
            # Test with increase
            justification = resource_optimizer._generate_capacity_justification(
                resource_type=resource_type,
                current=500.0,
                recommended=600.0,
                forecasted=550.0,
                timeframe=timeframe,
            )
            
            assert "increase" in justification.lower()
            assert resource_type.value in justification.lower()
            assert "20.0%" in justification  # (600-500)/500 * 100
            
            # Test with decrease
            justification = resource_optimizer._generate_capacity_justification(
                resource_type=resource_type,
                current=500.0,
                recommended=400.0,
                forecasted=350.0,
                timeframe=timeframe,
            )
            
            assert "decrease" in justification.lower()
            assert resource_type.value in justification.lower()
            assert "20.0%" in justification  # (500-400)/500 * 100