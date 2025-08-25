"""Fixed unit tests for the deadline-driven scheduler."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from render_farm_manager.core.models import (
    JobPriority,
    RenderJob,
    RenderJobStatus,
    RenderNode,
    NodeCapabilities,
)
from render_farm_manager.scheduling.deadline_scheduler_fixed import DeadlineScheduler
from render_farm_manager.utils.logging import AuditLogger, PerformanceMonitor


@pytest.fixture
def audit_logger():
    return MagicMock(spec=AuditLogger)


@pytest.fixture
def performance_monitor():
    return MagicMock(spec=PerformanceMonitor)


@pytest.fixture
def scheduler(audit_logger, performance_monitor):
    return DeadlineScheduler(
        audit_logger=audit_logger,
        performance_monitor=performance_monitor,
        deadline_safety_margin_hours=2.0,
        enable_preemption=True,
    )


@pytest.fixture
def nodes():
    """Create a list of test render nodes."""
    return [
        RenderNode(
            id=f"node-{i}",
            name=f"Test Node {i}",
            status="online",
            capabilities=NodeCapabilities(
                cpu_cores=32,
                memory_gb=128,
                gpu_model="NVIDIA RTX A6000" if i % 2 == 0 else None,
                gpu_count=4 if i % 2 == 0 else 0,
                gpu_memory_gb=48 if i % 2 == 0 else 0,
                gpu_compute_capability=8.6 if i % 2 == 0 else 0.0,
                storage_gb=2000,
                specialized_for=["gpu_rendering"] if i % 2 == 0 else ["cpu_rendering"],
            ),
            power_efficiency_rating=85,
            current_job_id=None,
            performance_history={},
            last_error=None,
            uptime_hours=100 + i,
        )
        for i in range(10)
    ]


def test_schedule_with_dependencies_fixed(scheduler, nodes):
    """Test scheduling with job dependencies, fixed to correctly handle parent progress >= 50%."""
    now = datetime.now()
    
    # Create jobs with dependencies - exact same structure as in the failing test
    parent_job = RenderJob(
        id="parent-job",
        name="Parent Job",
        client_id="client1",
        status=RenderJobStatus.RUNNING,
        job_type="animation",
        priority=JobPriority.HIGH,
        submission_time=now - timedelta(hours=2),
        deadline=now + timedelta(hours=10),
        estimated_duration_hours=4,
        progress=50.0,  # Set to exactly 50% for the test
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=16,
        scene_complexity=7,
        dependencies=[],
        assigned_node_id="node-0",
        output_path="/renders/parent-job/",
        error_count=0,
        can_be_preempted=True,
    )
    
    child_job = RenderJob(
        id="child-job",
        name="Child Job",
        client_id="client1",
        status=RenderJobStatus.PENDING,
        job_type="vfx",
        priority=JobPriority.HIGH,
        submission_time=now - timedelta(hours=1),
        deadline=now + timedelta(hours=12),
        estimated_duration_hours=6,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=16,
        cpu_requirements=8,
        scene_complexity=5,
        dependencies=["parent-job"],  # Depends on parent-job
        assigned_node_id=None,
        output_path="/renders/child-job/",
        error_count=0,
        can_be_preempted=True,
    )
    
    # Parent job is still running with progress=50%, child job should be scheduled
    # Our fixed scheduler treats 50% progress as sufficient to satisfy dependency
    jobs = [parent_job, child_job]
    
    # Make node-0 busy with the parent job
    nodes[0].current_job_id = "parent-job"
    
    # Run the scheduling process
    scheduled_jobs = scheduler.schedule_jobs(jobs, nodes)
    
    # Verify that child-job is scheduled to a node that isn't node-0
    assert "child-job" in scheduled_jobs
    assert scheduled_jobs["child-job"] != "node-0"