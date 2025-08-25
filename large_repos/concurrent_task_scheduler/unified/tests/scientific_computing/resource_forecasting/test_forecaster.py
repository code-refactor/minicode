"""Tests for the resource forecasting module."""

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
)

# Mock simulation class that overrides total_progress
class MockSimulation(Simulation):
    def total_progress(self) -> float:
        # Always return 0.5 for testing
        return 0.5

from concurrent_task_scheduler.resource_forecasting.data_collector import (
    ResourceDataCollector,
    AggregationMethod,
    AggregationPeriod,
)
from concurrent_task_scheduler.resource_forecasting.forecaster import (
    ResourceForecaster,
    ForecastingMethod,
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
def simulation_with_history(resource_data_collector):
    """Create a simulation with resource usage history for testing."""
    # Create a simulation
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
        id="sim_forecast_test",
        name="Forecast Test Simulation",
        creation_time=datetime.now() - timedelta(days=7),
        status=SimulationStatus.RUNNING,
        priority=SimulationPriority.HIGH,
        stages=stages,
    )
    
    # Add resource usage history
    start_date = datetime.now() - timedelta(days=30)
    
    # Generate 30 days of hourly data with daily and weekly patterns
    for i in range(30 * 24):
        timestamp = start_date + timedelta(hours=i)
        
        # Hour of day effect (0-23)
        hour_effect = np.sin(timestamp.hour / 24 * 2 * np.pi) * 0.2
        
        # Day of week effect (0=Monday, 6=Sunday)
        day_of_week = timestamp.weekday()
        weekend_effect = 0.1 if day_of_week >= 5 else 0
        
        # Linear trend (slight increase over time)
        trend = i / (30 * 24) * 0.1
        
        # Combine effects for CPU
        cpu_usage = 0.5 + hour_effect + weekend_effect + trend
        cpu_usage = max(0.1, min(0.9, cpu_usage))  # Keep within bounds
        
        # Memory has different pattern - gradually increases
        memory_usage = 0.4 + (i / (30 * 24)) * 0.3 + np.random.normal(0, 0.05)
        memory_usage = max(0.1, min(0.9, memory_usage))
        
        # Storage steadily increases
        storage_usage = 0.3 + (i / (30 * 24)) * 0.4
        storage_usage = max(0.1, min(0.9, storage_usage))
        
        # Network has spiky pattern
        network_base = 0.3 + hour_effect * 2
        network_spikes = np.random.choice([0, 0, 0, 0.3], p=[0.9, 0.03, 0.03, 0.04])
        network_usage = network_base + network_spikes
        network_usage = max(0.1, min(0.9, network_usage))
        
        # Record data points
        resource_data_collector.record_data_point(
            resource_type=ResourceType.CPU,
            utilization=cpu_usage,
            capacity=1.0,
            timestamp=timestamp,
            simulation_id=simulation.id,
        )
        
        resource_data_collector.record_data_point(
            resource_type=ResourceType.MEMORY,
            utilization=memory_usage,
            capacity=1.0,
            timestamp=timestamp,
            simulation_id=simulation.id,
        )
        
        resource_data_collector.record_data_point(
            resource_type=ResourceType.STORAGE,
            utilization=storage_usage,
            capacity=1.0,
            timestamp=timestamp,
            simulation_id=simulation.id,
        )
        
        resource_data_collector.record_data_point(
            resource_type=ResourceType.NETWORK,
            utilization=network_usage,
            capacity=1.0,
            timestamp=timestamp,
            simulation_id=simulation.id,
        )
    
    return simulation


def test_forecaster_init(resource_forecaster):
    """Test initialization of resource forecaster."""
    assert hasattr(resource_forecaster, 'data_collector')
    assert isinstance(resource_forecaster.models, dict)
    assert isinstance(resource_forecaster.model_accuracy, dict)
    assert isinstance(resource_forecaster.recent_forecasts, dict)
    assert resource_forecaster.default_method == ForecastingMethod.LINEAR_REGRESSION


def test_extract_time_features(resource_forecaster):
    """Test extracting time features from timestamps."""
    # Create some test timestamps
    timestamps = [
        datetime(2023, 1, 1, 12, 0),  # Sunday noon
        datetime(2023, 1, 2, 8, 0),   # Monday morning
        datetime(2023, 1, 3, 18, 0),  # Tuesday evening
        datetime(2023, 1, 7, 23, 0),  # Saturday night
    ]
    
    features = resource_forecaster._extract_time_features(timestamps)
    
    # Check feature shape and basic properties
    assert features.shape == (4, 10)  # 4 timestamps, 10 features
    
    # Check values for the first timestamp (Sunday noon)
    assert features[0][0] == 12  # Hour
    assert features[0][1] == 1   # Day
    assert features[0][2] == 1   # Month
    assert features[0][3] == 6   # Day of week (0=Monday, 6=Sunday)
    assert features[0][8] in [1, True]  # Is weekend (Sunday) - could be bool or int
    assert features[0][9] in [1, 2]  # Time of day (noon = afternoon = 1 or 2)
    
    # Check values for the second timestamp (Monday morning)
    assert features[1][0] == 8   # Hour
    assert features[1][3] == 0   # Day of week (Monday)
    assert features[1][8] in [0, False]  # Is weekend (not weekend) - could be bool or int
    assert features[1][9] in [1, 2]  # Time of day (morning = 1 or 2)


def test_train_model(resource_forecaster, simulation_with_history):
    """Test training a forecasting model."""
    # Train a linear regression model
    result = resource_forecaster.train_model(
        resource_type=ResourceType.CPU,
        simulation_id=simulation_with_history.id,
        method=ForecastingMethod.LINEAR_REGRESSION,
        training_days=30,
    )
    
    assert result.success
    model_data = result.value
    
    # Check model data structure
    assert "model" in model_data
    assert "method" in model_data
    assert "scaler" in model_data
    assert "training_start" in model_data
    assert "training_end" in model_data
    assert "data_points" in model_data
    assert "last_updated" in model_data
    assert "resource_type" in model_data
    
    # Check model was stored correctly
    assert simulation_with_history.id in resource_forecaster.models
    assert ResourceType.CPU in resource_forecaster.models[simulation_with_history.id]
    
    # Test training with insufficient data
    result = resource_forecaster.train_model(
        resource_type=ResourceType.CPU,
        simulation_id="nonexistent",
        method=ForecastingMethod.LINEAR_REGRESSION,
    )
    
    assert not result.success
    assert "Insufficient data" in result.error
    
    # Test other forecasting methods
    for method in [
        ForecastingMethod.RANDOM_FOREST,
        ForecastingMethod.MOVING_AVERAGE,
        ForecastingMethod.EXPONENTIAL_SMOOTHING,
        ForecastingMethod.ENSEMBLE,
    ]:
        result = resource_forecaster.train_model(
            resource_type=ResourceType.CPU,
            simulation_id=simulation_with_history.id,
            method=method,
            training_days=30,
        )
        
        assert result.success
        assert result.value["method"] == method


def test_forecast_resource_usage(resource_forecaster, simulation_with_history):
    """Test forecasting resource usage."""
    # Forecast CPU usage
    start_date = datetime.now()
    end_date = start_date + timedelta(days=14)
    
    result = resource_forecaster.forecast_resource_usage(
        resource_type=ResourceType.CPU,
        start_date=start_date,
        end_date=end_date,
        simulation_id=simulation_with_history.id,
        method=ForecastingMethod.LINEAR_REGRESSION,
        period=ForecastPeriod.DAILY,
    )
    
    assert result.success
    forecast = result.value
    
    # Check forecast structure
    assert forecast.start_date == start_date
    assert forecast.end_date == end_date
    assert forecast.period == ForecastPeriod.DAILY
    assert forecast.resource_type == ResourceType.CPU
    assert len(forecast.forecasted_values) > 0
    assert len(forecast.confidence_intervals) > 0
    
    # Check forecast values
    for date_str, value in forecast.forecasted_values.items():
        assert 0.0 <= value <= 1.0  # Should be a utilization value between 0 and 1
    
    # Test forecasting with other methods
    for method in [
        ForecastingMethod.MOVING_AVERAGE,
        ForecastingMethod.EXPONENTIAL_SMOOTHING,
        ForecastingMethod.ENSEMBLE,
    ]:
        result = resource_forecaster.forecast_resource_usage(
            resource_type=ResourceType.CPU,
            start_date=start_date,
            end_date=start_date + timedelta(days=7),
            simulation_id=simulation_with_history.id,
            method=method,
            period=ForecastPeriod.DAILY,
        )
        
        assert result.success
        assert result.value.resource_type == ResourceType.CPU
    
    # Test forecasting with other resource types
    for resource_type in [ResourceType.MEMORY, ResourceType.STORAGE, ResourceType.NETWORK]:
        result = resource_forecaster.forecast_resource_usage(
            resource_type=resource_type,
            start_date=start_date,
            end_date=start_date + timedelta(days=7),
            simulation_id=simulation_with_history.id,
            period=ForecastPeriod.DAILY,
        )
        
        assert result.success
        assert result.value.resource_type == resource_type
    
    # Test forecasting with different periods
    for period in [ForecastPeriod.WEEKLY, ForecastPeriod.MONTHLY]:
        result = resource_forecaster.forecast_resource_usage(
            resource_type=ResourceType.CPU,
            start_date=start_date,
            end_date=start_date + timedelta(days=30),
            simulation_id=simulation_with_history.id,
            period=period,
        )
        
        assert result.success
        assert result.value.period == period


def test_update_forecast_with_actuals(resource_forecaster, simulation_with_history):
    """Test updating a forecast with actual values."""
    # Create a forecast
    start_date = datetime.now()
    end_date = start_date + timedelta(days=7)
    
    result = resource_forecaster.forecast_resource_usage(
        resource_type=ResourceType.CPU,
        start_date=start_date,
        end_date=end_date,
        simulation_id=simulation_with_history.id,
        period=ForecastPeriod.DAILY,
    )
    
    assert result.success
    forecast = result.value
    
    # Update with some actual values
    actual_values = {
        start_date.strftime('%Y-%m-%d'): 0.65,
        (start_date + timedelta(days=1)).strftime('%Y-%m-%d'): 0.70,
        (start_date + timedelta(days=2)).strftime('%Y-%m-%d'): 0.75,
    }
    
    updated_forecast = resource_forecaster.update_forecast_with_actuals(
        forecast=forecast,
        actual_values=actual_values,
    )
    
    # Check if actuals were added correctly
    assert len(updated_forecast.actual_values) == 3
    assert start_date.strftime('%Y-%m-%d') in updated_forecast.actual_values
    
    # Check if accuracy metrics were calculated
    assert updated_forecast.accuracy is not None
    assert hasattr(updated_forecast.accuracy, 'mean_absolute_error')
    assert hasattr(updated_forecast.accuracy, 'mean_percentage_error')
    assert hasattr(updated_forecast.accuracy, 'root_mean_squared_error')


def test_create_resource_projection(resource_forecaster, simulation_with_history):
    """Test creating a resource projection."""
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)
    
    # Create another simulation
    another_sim_id = "sim_another"
    # Add some resource usage history for the new simulation
    for i in range(24 * 7):  # 7 days of hourly data
        timestamp = datetime.now() - timedelta(hours=i)
        for resource_type in ResourceType:
            resource_forecaster.data_collector.record_data_point(
                resource_type=resource_type,
                utilization=0.4 + (i % 24) / 48.0,  # Simple pattern
                capacity=1.0,
                timestamp=timestamp,
                simulation_id=another_sim_id,
            )
    
    # Create resource projection for both simulations
    result = resource_forecaster.create_resource_projection(
        project_id="project001",
        project_name="Test Project",
        start_date=start_date,
        end_date=end_date,
        simulation_ids=[simulation_with_history.id, another_sim_id],
    )
    
    assert result.success
    projection = result.value
    
    # Check projection structure
    assert projection.project_id == "project001"
    assert projection.project_name == "Test Project"
    assert projection.start_date == start_date
    assert projection.end_date == end_date
    assert len(projection.resource_projections) > 0
    assert projection.total_cost_estimate is not None
    assert len(projection.cost_breakdown) > 0
    
    # Check resource projections for all resource types
    for resource_type in ResourceType:
        assert resource_type in projection.resource_projections
        resource_forecast = projection.resource_projections[resource_type]
        assert resource_forecast.resource_type == resource_type
        assert len(resource_forecast.forecasted_values) > 0


def test_detect_anomalies(resource_forecaster, simulation_with_history):
    """Test detecting anomalies in resource usage."""
    # Add some anomalous data points
    for i in range(3):
        timestamp = datetime.now() - timedelta(hours=i)
        resource_forecaster.data_collector.record_data_point(
            resource_type=ResourceType.CPU,
            utilization=0.95,  # Anomalously high
            capacity=1.0,
            timestamp=timestamp,
            simulation_id=simulation_with_history.id,
        )
    
    # Detect anomalies
    result = resource_forecaster.detect_anomalies(
        resource_type=ResourceType.CPU,
        simulation_id=simulation_with_history.id,
        threshold_stdevs=2.0,  # Lower threshold to detect our test anomalies
        window_days=7,
    )
    
    assert result.success
    anomalies = result.value
    
    # Should have detected at least one anomaly
    assert len(anomalies) > 0
    
    # Check anomaly structure
    for anomaly in anomalies:
        assert "timestamp" in anomaly
        assert "value" in anomaly
        assert "z_score" in anomaly
        assert "is_high" in anomaly
        
        # Our test anomalies should be high
        if anomaly["value"] >= 0.95:
            assert anomaly["is_high"] is True