import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from render_farm_manager.core.models import (
    RenderClient,
    RenderNode,
    RenderJob,
    RenderJobStatus,
    ServiceTier,
    NodeType,
    EnergyMode,
    NodeCapabilities,
    JobPriority,
    NodeStatus,
)
from render_farm_manager.core.manager import RenderFarmManager


@pytest.fixture
def audit_logger():
    """Creates a mock audit logger with all necessary methods."""
    mock = MagicMock()
    # Add specific methods that might be called during testing
    mock.log_client_added = MagicMock()
    mock.log_node_added = MagicMock()
    mock.log_job_submitted = MagicMock()
    mock.log_job_scheduled = MagicMock()
    mock.log_job_updated = MagicMock()
    mock.log_job_completed = MagicMock()
    mock.log_energy_mode_changed = MagicMock()
    mock.log_scheduling_cycle = MagicMock()
    mock.log_event = MagicMock()
    return mock


@pytest.fixture
def performance_monitor():
    """Creates a mock performance monitor with all necessary methods."""
    mock = MagicMock()
    # Add specific methods that might be called during testing
    mock.update_scheduling_cycle_time = MagicMock()
    mock.update_job_turnaround_time = MagicMock()
    mock.update_node_utilization = MagicMock()
    mock.update_client_job_count = MagicMock()
    mock.update_energy_cost_saved = MagicMock()
    mock.time_operation = MagicMock()
    return mock


@pytest.fixture
def farm_manager(audit_logger, performance_monitor):
    """Creates a render farm manager with mocked audit logger and performance metrics."""
    return RenderFarmManager(
        audit_logger=audit_logger,
        performance_monitor=performance_monitor
    )


@pytest.fixture
def client():
    """Creates a test client."""
    return RenderClient(
        client_id="client1",
        name="Test Client",
        service_tier=ServiceTier.PREMIUM,
    )


def test_energy_mode_changes(farm_manager, client):
    """Test that energy modes can be changed and logged correctly."""
    # This is a simple test that just checks mode changes are accepted
    farm_manager.add_client(client)
    
    # Set energy mode to BALANCED (this should be the default)
    farm_manager.set_energy_mode(EnergyMode.BALANCED)
    assert farm_manager.energy_optimizer.current_energy_mode == EnergyMode.BALANCED
    
    # Set energy mode to EFFICIENCY
    farm_manager.set_energy_mode(EnergyMode.EFFICIENCY)
    assert farm_manager.energy_optimizer.current_energy_mode == EnergyMode.EFFICIENCY
    
    # Set energy mode to PERFORMANCE
    farm_manager.set_energy_mode(EnergyMode.PERFORMANCE)
    assert farm_manager.energy_optimizer.current_energy_mode == EnergyMode.PERFORMANCE
    
    # Set energy mode to NIGHT_SAVINGS
    farm_manager.set_energy_mode(EnergyMode.NIGHT_SAVINGS)
    assert farm_manager.energy_optimizer.current_energy_mode == EnergyMode.NIGHT_SAVINGS
    
    # Verify log calls were made for mode changes
    assert farm_manager.audit_logger.log_energy_mode_changed.call_count >= 1