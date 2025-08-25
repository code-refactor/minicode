import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from render_farm_manager.core.models import (
    RenderClient,
    RenderNode,
    RenderJob,
    RenderJobStatus,
    ServiceTier,
    NodeCapabilities,
    JobPriority,
    NodeStatus,
)
from render_farm_manager.core.manager import RenderFarmManager


@pytest.fixture
def audit_logger():
    mock = MagicMock()
    mock.log_event = MagicMock()
    mock.log_node_failure = MagicMock()
    return mock


@pytest.fixture
def performance_monitor():
    mock = MagicMock()
    mock.update_node_failure_count = MagicMock()
    mock.time_operation = MagicMock()
    return mock


@pytest.fixture
def farm_manager(audit_logger, performance_monitor):
    return RenderFarmManager(
        audit_logger=audit_logger,
        performance_monitor=performance_monitor
    )


@pytest.fixture
def client():
    return RenderClient(
        client_id="client1",
        name="Test Client",
        service_tier=ServiceTier.PREMIUM,
    )


@pytest.fixture
def render_nodes():
    return [
        RenderNode(
            id="gpu1",
            name="GPU Node 1",
            status=NodeStatus.ONLINE,
            capabilities=NodeCapabilities(
                cpu_cores=16,
                memory_gb=64,
                gpu_model="NVIDIA RTX A6000",
                gpu_count=2,
                gpu_memory_gb=48.0,
                gpu_compute_capability=8.6,
                storage_gb=2000,
                specialized_for=["gpu_rendering"],
            ),
            power_efficiency_rating=72.0,
        ),
        RenderNode(
            id="gpu2",
            name="GPU Node 2",
            status=NodeStatus.ONLINE,
            capabilities=NodeCapabilities(
                cpu_cores=32,
                memory_gb=128,
                gpu_model="NVIDIA RTX A6000",
                gpu_count=4,
                gpu_memory_gb=48.0,
                gpu_compute_capability=8.6,
                storage_gb=4000,
                specialized_for=["gpu_rendering"],
            ),
            power_efficiency_rating=65.0,
        ),
    ]


@pytest.fixture
def checkpointable_job():
    now = datetime.now()
    return RenderJob(
        id="job1",
        name="Test Checkpoint Job",
        client_id="client1",
        status=RenderJobStatus.PENDING,
        job_type="animation",
        priority=JobPriority.HIGH,
        submission_time=now - timedelta(hours=1),
        deadline=now + timedelta(hours=5),
        estimated_duration_hours=3.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=7,
        dependencies=[],
        assigned_node_id=None,
        output_path="/renders/client1/job1/",
        error_count=0,
        can_be_preempted=True,
        supports_progressive_output=False,
        supports_checkpoint=True,
    )


def test_error_recovery_checkpoint_simple(farm_manager, client, render_nodes, checkpointable_job):
    """Simple test to ensure node failure handling works with checkpoints."""
    # Setup
    farm_manager.add_client(client)
    for node in render_nodes:
        farm_manager.add_node(node)
    farm_manager.submit_job(checkpointable_job)
    
    # Run scheduling
    farm_manager.run_scheduling_cycle()
    
    # Check job is assigned
    job = farm_manager.jobs[checkpointable_job.id]
    assert job.status == RenderJobStatus.RUNNING
    assert job.assigned_node_id is not None
    
    # Simulate node failure
    node_id = job.assigned_node_id
    farm_manager.handle_node_failure(node_id, "Test failure")
    
    # Verify job is queued and not assigned to a node
    assert job.status == RenderJobStatus.QUEUED
    assert job.assigned_node_id is None
    assert job.error_count == 1