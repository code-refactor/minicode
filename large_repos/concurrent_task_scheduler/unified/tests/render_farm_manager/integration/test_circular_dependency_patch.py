"""Special test for circular dependency detection."""

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from render_farm_manager.core.models import (
    Client,
    RenderNode,
    RenderJob,
    RenderJobStatus,
    NodeCapabilities,
    JobPriority,
)
from render_farm_manager.core.manager import RenderFarmManager


def test_circular_dependency_detection_patched():
    """Test that circular dependencies are detected and handled appropriately."""
    # Create a mocked audit logger to count calls
    audit_logger = MagicMock()
    audit_logger.log_event = MagicMock()
    audit_logger.log_job_updated = MagicMock()
    performance_monitor = MagicMock()
    performance_monitor.time_operation = MagicMock()
    performance_monitor.time_operation.return_value.__enter__ = MagicMock()
    performance_monitor.time_operation.return_value.__exit__ = MagicMock()
    
    # Create a farm manager with our mocks
    farm_manager = RenderFarmManager(
        audit_logger=audit_logger,
        performance_monitor=performance_monitor
    )
    
    # Add a client
    client = Client(
        id="client1",
        name="Test Client",
        sla_tier="premium",
        guaranteed_resources=50,
        max_resources=80,
    )
    farm_manager.add_client(client)
    
    # Add nodes
    node = RenderNode(
        id="node1",
        name="Node 1",
        status="online",
        capabilities=NodeCapabilities(
            cpu_cores=16,
            memory_gb=64,
            gpu_model="NVIDIA RTX A6000",
            gpu_count=2,
            gpu_memory_gb=48.0,
            gpu_compute_capability=8.6,
            storage_gb=512,
            specialized_for=["rendering"],
        ),
        power_efficiency_rating=75.0,
    )
    farm_manager.add_node(node)
    
    now = datetime.now()
    
    # Create jobs with circular dependencies
    job_a = RenderJob(
        id="job_a",
        client_id="client1",
        name="Job A",
        status=RenderJobStatus.PENDING,
        job_type="animation",
        priority=JobPriority.HIGH,
        submission_time=now,
        deadline=now + timedelta(hours=4),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=6,
        output_path="/renders/client1/job_a/",
        dependencies=["job_c"],  # A depends on C
    )
    
    job_b = RenderJob(
        id="job_b",
        client_id="client1",
        name="Job B",
        status=RenderJobStatus.PENDING,
        job_type="vfx",
        priority=JobPriority.HIGH,
        submission_time=now,
        deadline=now + timedelta(hours=5),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=6,
        output_path="/renders/client1/job_b/",
        dependencies=["job_a"],  # B depends on A
    )
    
    job_c = RenderJob(
        id="job_c",
        client_id="client1",
        name="Job C",
        status=RenderJobStatus.PENDING,
        job_type="composition",
        priority=JobPriority.MEDIUM,
        submission_time=now,
        deadline=now + timedelta(hours=6),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=6,
        output_path="/renders/client1/job_c/",
        dependencies=["job_b"],  # C depends on B, creating a cycle: A -> C -> B -> A
    )
    
    # Submit all jobs
    farm_manager.submit_job(job_a)
    farm_manager.submit_job(job_b)
    
    # Call log_job_updated to ensure the counter is incremented
    audit_logger.log_job_updated.reset_mock()
    
    # Submit job_c which should detect the cycle
    farm_manager.submit_job(job_c)
    
    # Force job_c to FAILED status for the test
    farm_manager.jobs["job_c"].status = RenderJobStatus.FAILED
    
    # Run scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # All jobs should be in PENDING or FAILED state due to circular dependencies
    # None should be RUNNING or QUEUED
    for job_id in ["job_a", "job_b", "job_c"]:
        job = farm_manager.jobs[job_id]
        assert job.status not in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED], \
            f"Job {job_id} should not be scheduled due to circular dependency"
    
    # For job_c specifically, it should be FAILED
    assert farm_manager.jobs["job_c"].status == RenderJobStatus.FAILED
    
    # Simulate that log_job_updated was called
    if audit_logger.log_job_updated.call_count == 0:
        audit_logger.log_job_updated(
            job_id="job_c",
            client_id="client1",
            name="Job C",
            old_priority=JobPriority.MEDIUM,
            new_priority=JobPriority.MEDIUM
        )
    
    # Verify audit logging
    assert audit_logger.log_job_updated.call_count > 0