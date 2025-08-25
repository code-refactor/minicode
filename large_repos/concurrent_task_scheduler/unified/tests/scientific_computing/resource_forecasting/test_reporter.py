"""Tests for the resource reporting module."""

from datetime import datetime, timedelta

import pytest
import json

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
    ResourceUsageAnalyzer,
)
from concurrent_task_scheduler.resource_forecasting.forecaster import (
    ResourceForecaster,
)
from concurrent_task_scheduler.resource_forecasting.optimizer import (
    ResourceOptimizer,
    OptimizationGoal,
    OptimizationTimeframe,
)
from concurrent_task_scheduler.resource_forecasting.reporter import (
    ResourceReporter,
    ReportType,
    ReportFormat,
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
def resource_reporter(resource_data_collector, resource_forecaster, resource_optimizer):
    """Create a resource reporter for testing."""
    return ResourceReporter(
        data_collector=resource_data_collector,
        forecaster=resource_forecaster,
        optimizer=resource_optimizer,
    )


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
        id="sim_reporter_test",
        name="Reporter Test Simulation",
        creation_time=datetime.now() - timedelta(hours=3),
        status=SimulationStatus.RUNNING,
        priority=SimulationPriority.HIGH,
        stages=stages,
    )
    
    return simulation


@pytest.fixture
def simulation_with_data(resource_data_collector, sample_simulation):
    """Create a simulation with resource data for testing."""
    simulation = sample_simulation
    
    # Add resource usage data
    start_date = datetime.now() - timedelta(days=7)
    
    for i in range(7 * 24):  # 7 days of hourly data
        timestamp = start_date + timedelta(hours=i)
        
        for resource_type in ResourceType:
            # Create different patterns for each resource type
            if resource_type == ResourceType.CPU:
                value = 0.5 + 0.2 * (i % 24) / 24.0  # Daily pattern
            elif resource_type == ResourceType.MEMORY:
                value = 0.4 + 0.3 * i / (7 * 24)  # Increasing trend
            elif resource_type == ResourceType.STORAGE:
                value = 0.3 + 0.5 * i / (7 * 24)  # Steeper increasing trend
            else:  # NETWORK
                value = 0.4 + 0.3 * ((i % 24) / 24.0) * ((i % 7) / 7.0)  # Complex pattern
            
            resource_data_collector.record_data_point(
                resource_type=resource_type,
                utilization=value,
                capacity=1.0,
                timestamp=timestamp,
                simulation_id=simulation.id,
            )
    
    return simulation


def test_reporter_init(resource_reporter):
    """Test initialization of resource reporter."""
    assert hasattr(resource_reporter, 'data_collector')
    assert hasattr(resource_reporter, 'forecaster')
    assert hasattr(resource_reporter, 'optimizer')
    assert hasattr(resource_reporter, 'analyzer')
    assert isinstance(resource_reporter.generated_reports, dict)


def test_generate_utilization_report(resource_reporter, simulation_with_data):
    """Test generating a utilization report."""
    # Test JSON format
    result = resource_reporter.generate_utilization_report(
        simulation_id=simulation_with_data.id,
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
        resource_types=[ResourceType.CPU, ResourceType.MEMORY],
        format=ReportFormat.JSON,
    )
    
    assert result.success
    report_json = result.value
    
    # Parse JSON and check structure
    report_data = json.loads(report_json)
    assert report_data["report_type"] == ReportType.UTILIZATION.value
    assert "generated_at" in report_data
    assert "period" in report_data
    assert "scope" in report_data
    assert "metrics" in report_data
    assert "data" in report_data
    assert "summary" in report_data
    
    assert report_data["scope"]["simulation_id"] == simulation_with_data.id
    assert "cpu" in report_data["metrics"]
    assert "memory" in report_data["metrics"]
    assert "cpu" in report_data["data"]
    assert "memory" in report_data["data"]
    
    # Test CSV format
    result = resource_reporter.generate_utilization_report(
        simulation_id=simulation_with_data.id,
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
        resource_types=[ResourceType.CPU],
        format=ReportFormat.CSV,
    )
    
    assert result.success
    report_csv = result.value
    assert "timestamp" in report_csv
    assert "cpu" in report_csv
    
    # Test Markdown format
    result = resource_reporter.generate_utilization_report(
        simulation_id=simulation_with_data.id,
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
        resource_types=[ResourceType.CPU, ResourceType.MEMORY],
        format=ReportFormat.MARKDOWN,
    )
    
    assert result.success
    report_md = result.value
    assert "# Resource Utilization Report" in report_md
    assert "| Resource | Average Utilization | Peak Utilization | Utilization Rate |" in report_md
    assert "| cpu " in report_md
    assert "| memory " in report_md
    
    # Test Text format
    result = resource_reporter.generate_utilization_report(
        simulation_id=simulation_with_data.id,
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
        resource_types=[ResourceType.CPU],
        format=ReportFormat.TEXT,
    )
    
    assert result.success
    report_text = result.value
    assert "Resource Utilization Report" in report_text
    assert "cpu:" in report_text
    assert "Average Utilization:" in report_text
    
    # Test with node_id instead of simulation_id
    node_id = "node001"
    for i in range(24):
        timestamp = datetime.now() - timedelta(hours=i)
        resource_reporter.data_collector.record_data_point(
            resource_type=ResourceType.CPU,
            utilization=0.5,
            capacity=1.0,
            timestamp=timestamp,
            node_id=node_id,
        )
    
    result = resource_reporter.generate_utilization_report(
        node_id=node_id,
        resource_types=[ResourceType.CPU],
        format=ReportFormat.JSON,
    )
    
    assert result.success
    report_data = json.loads(result.value)
    assert report_data["scope"]["node_id"] == node_id


def test_generate_forecast_report(resource_reporter, simulation_with_data):
    """Test generating a forecast report."""
    # Test JSON format
    result = resource_reporter.generate_forecast_report(
        simulation_id=simulation_with_data.id,
        resource_types=[ResourceType.CPU, ResourceType.MEMORY],
        forecast_days=14,
        format=ReportFormat.JSON,
    )
    
    assert result.success
    report_json = result.value
    
    # Parse JSON and check structure
    report_data = json.loads(report_json)
    assert report_data["report_type"] == ReportType.FORECAST.value
    assert "generated_at" in report_data
    assert "period" in report_data
    assert "scope" in report_data
    assert "forecasts" in report_data
    
    assert report_data["scope"]["simulation_id"] == simulation_with_data.id
    assert "cpu" in report_data["forecasts"]
    assert "memory" in report_data["forecasts"]
    
    # Check forecast structure
    cpu_forecast = report_data["forecasts"]["cpu"]
    assert "values" in cpu_forecast
    assert "confidence_intervals" in cpu_forecast
    assert "peak_forecast" in cpu_forecast
    assert "total_forecast" in cpu_forecast
    
    # Test recommendations
    if "recommendations" in report_data:
        for rec in report_data["recommendations"]:
            assert "resource_type" in rec
            assert "current_allocation" in rec
            assert "recommended_allocation" in rec
    
    # Test CSV format
    result = resource_reporter.generate_forecast_report(
        simulation_id=simulation_with_data.id,
        resource_types=[ResourceType.CPU],
        forecast_days=14,
        format=ReportFormat.CSV,
    )
    
    assert result.success
    report_csv = result.value
    assert "date" in report_csv
    assert "cpu_forecast" in report_csv
    
    # Test Markdown format
    result = resource_reporter.generate_forecast_report(
        simulation_id=simulation_with_data.id,
        resource_types=[ResourceType.CPU, ResourceType.MEMORY],
        forecast_days=14,
        format=ReportFormat.MARKDOWN,
    )
    
    assert result.success
    report_md = result.value
    assert "# Resource Forecast Report" in report_md
    assert "| Resource | Peak Forecast | Total Forecast | Forecast Accuracy |" in report_md
    
    # Test Text format
    result = resource_reporter.generate_forecast_report(
        simulation_id=simulation_with_data.id,
        resource_types=[ResourceType.CPU],
        forecast_days=14,
        format=ReportFormat.TEXT,
    )
    
    assert result.success
    report_text = result.value
    assert "Resource Forecast Report" in report_text
    assert "cpu:" in report_text
    assert "Peak Forecast:" in report_text


def test_generate_grant_report(resource_reporter, simulation_with_data):
    """Test generating a grant report."""
    # Create another simulation with data
    another_sim_id = "sim_another"
    start_date = datetime.now() - timedelta(days=7)
    
    for i in range(7 * 24):  # 7 days of hourly data
        timestamp = start_date + timedelta(hours=i)
        
        for resource_type in ResourceType:
            resource_reporter.data_collector.record_data_point(
                resource_type=resource_type,
                utilization=0.4 + 0.2 * i / (7 * 24),
                capacity=1.0,
                timestamp=timestamp,
                simulation_id=another_sim_id,
            )
    
    # Generate grant report with JSON format
    result = resource_reporter.generate_grant_report(
        project_id="project001",
        project_name="Test Project",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30),
        simulation_ids=[simulation_with_data.id, another_sim_id],
        format=ReportFormat.JSON,
    )
    
    assert result.success
    report_json = result.value
    
    # Parse JSON and check structure
    report_data = json.loads(report_json)
    assert report_data["report_type"] == ReportType.GRANT.value
    assert "generated_at" in report_data
    assert "project" in report_data
    assert "period" in report_data
    assert "simulations" in report_data
    assert "resource_projections" in report_data
    assert "cost_estimate" in report_data
    
    assert report_data["project"]["id"] == "project001"
    assert report_data["project"]["name"] == "Test Project"
    assert simulation_with_data.id in report_data["simulations"]
    assert another_sim_id in report_data["simulations"]
    
    # Check resource projections
    for resource_type in ResourceType:
        assert resource_type.value in report_data["resource_projections"]
    
    # Check cost estimate
    assert "total" in report_data["cost_estimate"]
    assert "breakdown" in report_data["cost_estimate"]
    
    # Test Markdown format
    result = resource_reporter.generate_grant_report(
        project_id="project001",
        project_name="Test Project",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30),
        simulation_ids=[simulation_with_data.id, another_sim_id],
        format=ReportFormat.MARKDOWN,
    )
    
    assert result.success
    report_md = result.value
    assert "# Resource Projection for Grant Report" in report_md
    assert "## Project: Test Project" in report_md
    assert "## Cost Estimate" in report_md
    assert "| Resource | Cost |" in report_md
    assert "## Resource Projections" in report_md
    
    # Test Text format
    result = resource_reporter.generate_grant_report(
        project_id="project001",
        project_name="Test Project",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30),
        simulation_ids=[simulation_with_data.id, another_sim_id],
        format=ReportFormat.TEXT,
    )
    
    assert result.success
    report_text = result.value
    assert "Resource Projection for Grant Report" in report_text
    assert "Project: Test Project" in report_text
    assert "Cost Estimate" in report_text
    assert "Resource Projections" in report_text


def test_generate_recommendation_report(resource_reporter, simulation_with_data):
    """Test generating a recommendation report."""
    # Test JSON format
    result = resource_reporter.generate_recommendation_report(
        simulation_id=simulation_with_data.id,
        goal=OptimizationGoal.BALANCE,
        timeframe=OptimizationTimeframe.SHORT_TERM,
        format=ReportFormat.JSON,
        simulation=simulation_with_data,
    )
    
    assert result.success
    report_json = result.value
    
    # Parse JSON and check structure
    report_data = json.loads(report_json)
    assert report_data["report_type"] == ReportType.RECOMMENDATION.value
    assert "generated_at" in report_data
    assert "simulation" in report_data
    assert "optimization" in report_data
    assert "recommendations" in report_data
    assert "summary" in report_data
    
    assert report_data["simulation"]["id"] == simulation_with_data.id
    assert report_data["simulation"]["name"] == simulation_with_data.name
    assert report_data["optimization"]["goal"] == OptimizationGoal.BALANCE.value
    assert report_data["optimization"]["timeframe"] == OptimizationTimeframe.SHORT_TERM.value
    
    # Test Markdown format
    result = resource_reporter.generate_recommendation_report(
        simulation_id=simulation_with_data.id,
        goal=OptimizationGoal.MINIMIZE_COST,
        timeframe=OptimizationTimeframe.MEDIUM_TERM,
        format=ReportFormat.MARKDOWN,
        simulation=simulation_with_data,
    )
    
    assert result.success
    report_md = result.value
    assert "# Resource Optimization Recommendations" in report_md
    assert simulation_with_data.name in report_md
    assert "Optimization Goal: minimize_cost" in report_md
    assert "Timeframe: medium_term" in report_md
    
    # Test Text format
    result = resource_reporter.generate_recommendation_report(
        simulation_id=simulation_with_data.id,
        goal=OptimizationGoal.MAXIMIZE_THROUGHPUT,
        timeframe=OptimizationTimeframe.SHORT_TERM,
        format=ReportFormat.TEXT,
        simulation=simulation_with_data,
    )
    
    assert result.success
    report_text = result.value
    assert "Resource Optimization Recommendations" in report_text
    assert simulation_with_data.name in report_text
    assert "Optimization Goal: maximize_throughput" in report_text
    assert "Timeframe: short_term" in report_text


def test_get_report(resource_reporter, simulation_with_data):
    """Test getting a previously generated report."""
    # Generate a report first
    result = resource_reporter.generate_utilization_report(
        simulation_id=simulation_with_data.id,
        resource_types=[ResourceType.CPU],
        format=ReportFormat.JSON,
    )
    
    assert result.success
    
    # There should be a report stored
    assert len(resource_reporter.generated_reports) == 1
    
    # Get the first report ID
    report_id = list(resource_reporter.generated_reports.keys())[0]
    
    # Get the report
    report = resource_reporter.get_report(report_id)
    
    assert report is not None
    assert report["report_type"] == ReportType.UTILIZATION.value
    assert report["scope"]["simulation_id"] == simulation_with_data.id
    
    # Test with non-existent report ID
    report = resource_reporter.get_report("nonexistent")
    assert report is None