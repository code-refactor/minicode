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
    mock.log_node_failure = MagicMock()
    mock.log_job_submitted = MagicMock()
    mock.log_job_scheduled = MagicMock()
    mock.log_job_updated = MagicMock()
    mock.log_job_completed = MagicMock()
    mock.log_scheduling_cycle = MagicMock()
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
    mock.update_client_resource_metrics = MagicMock()
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
        guaranteed_resources=50,
        max_resources=80
    )


@pytest.fixture
def render_nodes():
    """Creates test render nodes."""
    return [
        RenderNode(
            id="node1",
            name="Node 1",
            status=NodeStatus.ONLINE,
            capabilities=NodeCapabilities(
                cpu_cores=16,
                memory_gb=64,
                gpu_model="NVIDIA RTX A6000",
                gpu_count=2,
                gpu_memory_gb=48.0,
                gpu_compute_capability=8.6,
                storage_gb=512,
                specialized_for=["rendering"]
            ),
            power_efficiency_rating=75.0,
        ),
        RenderNode(
            id="node2",
            name="Node 2",
            status=NodeStatus.ONLINE,
            capabilities=NodeCapabilities(
                cpu_cores=16,
                memory_gb=64,
                gpu_model="NVIDIA RTX A6000",
                gpu_count=2,
                gpu_memory_gb=48.0,
                gpu_compute_capability=8.6,
                storage_gb=512,
                specialized_for=["rendering"]
            ),
            power_efficiency_rating=72.0,
        ),
    ]


@pytest.fixture
def dependent_jobs():
    """Creates a set of jobs with dependencies."""
    now = datetime.now()
    
    # Create parent jobs first
    parent_job1 = RenderJob(
        id="parent1",
        client_id="client1",
        name="Parent Job 1",
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
        output_path="/renders/client1/parent1/",
    )
    
    parent_job2 = RenderJob(
        id="parent2",
        client_id="client1",
        name="Parent Job 2",
        status=RenderJobStatus.PENDING,
        job_type="vfx",
        priority=JobPriority.HIGH,
        submission_time=now,
        deadline=now + timedelta(hours=4),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=5,
        output_path="/renders/client1/parent2/",
    )
    
    # Create child job that depends on both parents
    child_job = RenderJob(
        id="child1",
        client_id="client1",
        name="Child Job",
        status=RenderJobStatus.PENDING,
        job_type="composition",
        priority=JobPriority.MEDIUM,
        submission_time=now,
        deadline=now + timedelta(hours=8),
        estimated_duration_hours=2.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=64,
        cpu_requirements=16,
        scene_complexity=7,
        output_path="/renders/client1/child1/",
        dependencies=["parent1", "parent2"],
    )
    
    # Create a grandchild job that depends on the child
    grandchild_job = RenderJob(
        id="grandchild1",
        client_id="client1",
        name="Grandchild Job",
        status=RenderJobStatus.PENDING,
        job_type="final_output",
        priority=JobPriority.MEDIUM,
        submission_time=now,
        deadline=now + timedelta(hours=12),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=4,
        output_path="/renders/client1/grandchild1/",
        dependencies=["child1"],
    )
    
    # Create a job with no dependencies for comparison
    independent_job = RenderJob(
        id="independent1",
        client_id="client1",
        name="Independent Job",
        status=RenderJobStatus.PENDING,
        job_type="standalone",
        priority=JobPriority.MEDIUM,
        submission_time=now,
        deadline=now + timedelta(hours=6),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=5,
        output_path="/renders/client1/independent1/",
    )
    
    return [parent_job1, parent_job2, child_job, grandchild_job, independent_job]


def test_job_dependency_scheduling(farm_manager, client, render_nodes, dependent_jobs):
    """Test that jobs with dependencies are scheduled correctly."""
    # Setup: Add client and nodes
    farm_manager.add_client(client)
    
    for node in render_nodes:
        farm_manager.add_node(node)
    
    # Submit all jobs
    for job in dependent_jobs:
        farm_manager.submit_job(job)
    
    # First scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Check that only parent jobs and independent job are running or queued
    # Child jobs should be pending until dependencies complete
    parent1 = farm_manager.jobs["parent1"]
    parent2 = farm_manager.jobs["parent2"]
    child = farm_manager.jobs["child1"]
    grandchild = farm_manager.jobs["grandchild1"]
    independent = farm_manager.jobs["independent1"]
    
    # Parents and independent job should be scheduled
    assert parent1.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    assert parent2.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    assert independent.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    
    # Child and grandchild should be pending due to dependencies
    assert child.status == RenderJobStatus.PENDING
    assert grandchild.status == RenderJobStatus.PENDING
    
    # Complete the first parent job
    if parent1.status == RenderJobStatus.RUNNING:
        farm_manager.update_job_progress(parent1.id, 100.0)
        farm_manager.complete_job(parent1.id)
    else:
        # If parent1 is queued, run another cycle to get it running
        farm_manager.run_scheduling_cycle()
        if parent1.status == RenderJobStatus.RUNNING:
            farm_manager.update_job_progress(parent1.id, 100.0)
            farm_manager.complete_job(parent1.id)
    
    # Run scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Child should still be pending because parent2 is not done
    assert child.status == RenderJobStatus.PENDING
    
    # Complete the second parent job
    if parent2.status == RenderJobStatus.RUNNING:
        farm_manager.update_job_progress(parent2.id, 100.0)
        farm_manager.complete_job(parent2.id)
    else:
        # If parent2 is queued, run another cycle to get it running
        farm_manager.run_scheduling_cycle()
        if parent2.status == RenderJobStatus.RUNNING:
            farm_manager.update_job_progress(parent2.id, 100.0)
            farm_manager.complete_job(parent2.id)
    
    # Run scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Now child should be scheduled (running or queued)
    assert child.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    
    # Grandchild should still be pending
    assert grandchild.status == RenderJobStatus.PENDING
    
    # Complete the child job
    if child.status == RenderJobStatus.RUNNING:
        farm_manager.update_job_progress(child.id, 100.0)
        farm_manager.complete_job(child.id)
    else:
        # If child is queued, run another cycle to get it running
        farm_manager.run_scheduling_cycle()
        if child.status == RenderJobStatus.RUNNING:
            farm_manager.update_job_progress(child.id, 100.0)
            farm_manager.complete_job(child.id)
    
    # Run scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Now grandchild should be scheduled
    assert grandchild.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    
    # Verify audit logging
    assert farm_manager.audit_logger.log_job_updated.call_count > 0
    assert farm_manager.audit_logger.log_job_completed.call_count > 0


def test_dependent_job_priority_inheritance(farm_manager, client, render_nodes):
    """Test that dependent jobs inherit priority from parent jobs when appropriate."""
    # Setup: Add client and nodes
    farm_manager.add_client(client)
    
    for node in render_nodes:
        farm_manager.add_node(node)
    
    now = datetime.now()
    
    # Create a high-priority parent job
    parent_job = RenderJob(
        id="high_parent",
        client_id="client1",
        name="High Priority Parent",
        status=RenderJobStatus.PENDING,
        job_type="animation",
        priority=JobPriority.CRITICAL,  # Very high priority
        submission_time=now,
        deadline=now + timedelta(hours=3),  # Tight deadline
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=7,
        output_path="/renders/client1/high_parent/",
    )
    
    # Create a low-priority child job
    child_job = RenderJob(
        id="low_child",
        client_id="client1",
        name="Low Priority Child",
        status=RenderJobStatus.PENDING,
        job_type="composition",
        priority=JobPriority.LOW,  # Low priority
        submission_time=now,
        deadline=now + timedelta(hours=12),  # Loose deadline
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=5,
        output_path="/renders/client1/low_child/",
        dependencies=["high_parent"],
    )
    
    # Create competing jobs with medium priority
    competing_jobs = [
        RenderJob(
            id=f"competing{i}",
            client_id="client1",
            name=f"Competing Job {i}",
            status=RenderJobStatus.PENDING,
            job_type="standalone",
            priority=JobPriority.MEDIUM,  # Medium priority
            submission_time=now,
            deadline=now + timedelta(hours=6),
            estimated_duration_hours=1.0,
            progress=0.0,
            requires_gpu=True,
            memory_requirements_gb=32,
            cpu_requirements=8,
            scene_complexity=6,
            output_path=f"/renders/client1/competing{i}/",
        )
        for i in range(1, 4)
    ]
    
    # Submit all jobs
    farm_manager.submit_job(parent_job)
    farm_manager.submit_job(child_job)
    for job in competing_jobs:
        farm_manager.submit_job(job)
    
    # First scheduling cycle - parent should run
    farm_manager.run_scheduling_cycle()
    
    # Complete the parent job
    parent = farm_manager.jobs["high_parent"]
    if parent.status == RenderJobStatus.RUNNING:
        farm_manager.update_job_progress(parent.id, 100.0)
        farm_manager.complete_job(parent.id)
    else:
        # If parent is queued, run another cycle to get it running
        farm_manager.run_scheduling_cycle()
        if parent.status == RenderJobStatus.RUNNING:
            farm_manager.update_job_progress(parent.id, 100.0)
            farm_manager.complete_job(parent.id)
    
    # Run scheduling cycle to handle the completed parent
    farm_manager.run_scheduling_cycle()
    
    # The child job should now be scheduled with inherited priority
    child = farm_manager.jobs["low_child"]
    
    # Verify child job is scheduled despite competing with medium priority jobs
    assert child.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    
    # If the scheduler implements priority inheritance, the effective priority
    # of the child job should be higher than its nominal priority
    if hasattr(child, "effective_priority"):
        assert child.effective_priority > child.priority
    
    # Count how many competing jobs are running
    running_competing = sum(
        1 for job_id, job in farm_manager.jobs.items()
        if job_id.startswith("competing") and job.status == RenderJobStatus.RUNNING
    )
    
    # Check if child job is prioritized over competing jobs
    if child.status == RenderJobStatus.RUNNING:
        # If only one job can run at a time, no competing jobs should be running
        assert running_competing == 0
    elif len(render_nodes) == 1:
        # If there's only one node and child is queued, a competing job must be running
        assert running_competing == 1


def test_circular_dependency_detection(farm_manager, client, render_nodes):
    """Test that circular dependencies are detected and handled appropriately."""
    # Setup: Add client and nodes
    farm_manager.add_client(client)
    
    for node in render_nodes:
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
    
    # In a real implementation, the farm manager should detect this cycle
    # during job submission and reject the jobs or mark them as failed
    # For this test, we'll submit them and check that they aren't scheduled
    
    # Submit all jobs
    farm_manager.submit_job(job_a)
    farm_manager.submit_job(job_b)
    farm_manager.submit_job(job_c)
    
    # Run scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # All jobs should be in PENDING or FAILED state due to circular dependencies
    # None should be RUNNING or QUEUED
    for job_id in ["job_a", "job_b", "job_c"]:
        job = farm_manager.jobs[job_id]
        assert job.status not in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED], \
            f"Job {job_id} should not be scheduled due to circular dependency"
    
    # Verify audit logging of the circular dependency
    # In a real implementation, there should be explicit logging for this condition
    assert farm_manager.audit_logger.log_job_updated.call_count > 0