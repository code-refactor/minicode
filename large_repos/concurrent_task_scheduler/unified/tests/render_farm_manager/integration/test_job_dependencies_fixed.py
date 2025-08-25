"""Integration tests for job dependency functionality."""

import pytest
from datetime import datetime, timedelta

from render_farm_manager.core.models import (
    Client,
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
def farm_manager():
    return RenderFarmManager()


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
            id="node1",
            name="Render Node 1",
            status=NodeStatus.ONLINE,
            capabilities=NodeCapabilities(
                cpu_cores=16,
                memory_gb=64,
                gpu_model="NVIDIA RTX A6000",
                gpu_count=2,
                gpu_memory_gb=48.0,
                gpu_compute_capability=8.6,
                storage_gb=512,
                specialized_for=["gpu_rendering"],
            ),
            power_efficiency_rating=75.0,
        ),
        RenderNode(
            id="node2",
            name="Render Node 2",
            status=NodeStatus.ONLINE,
            capabilities=NodeCapabilities(
                cpu_cores=16,
                memory_gb=64,
                gpu_model="NVIDIA RTX A6000",
                gpu_count=2,
                gpu_memory_gb=48.0,
                gpu_compute_capability=8.6,
                storage_gb=512,
                specialized_for=["gpu_rendering"],
            ),
            power_efficiency_rating=75.0,
        ),
    ]


def test_simple_dependency(farm_manager):
    """Test that a job with dependencies is only scheduled after dependencies complete."""
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
    node1 = RenderNode(
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
            specialized_for=["gpu_rendering"],
        ),
        power_efficiency_rating=85.0,
    )
    node2 = RenderNode(
        id="node2",
        name="Node 2",
        status="online",
        capabilities=NodeCapabilities(
            cpu_cores=16,
            memory_gb=64,
            gpu_model="NVIDIA RTX A6000",
            gpu_count=2,
            gpu_memory_gb=48.0,
            gpu_compute_capability=8.6,
            storage_gb=512,
            specialized_for=["gpu_rendering"],
        ),
        power_efficiency_rating=85.0,
    )
    farm_manager.add_node(node1)
    farm_manager.add_node(node2)
    
    now = datetime.now()
    
    # Create jobs with dependencies
    job_parent = RenderJob(
        id="job_parent",
        client_id="client1",
        name="Parent Job",
        status=RenderJobStatus.PENDING,
        job_type="animation",
        priority=JobPriority.HIGH,
        submission_time=now,
        deadline=now + timedelta(hours=5),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=6,
        dependencies=[],  # No dependencies
        output_path="/renders/client1/job_parent/",
    )
    
    job_child = RenderJob(
        id="job_child",
        client_id="client1",
        name="Child Job",
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
        dependencies=["job_parent"],  # Depends on parent job
        output_path="/renders/client1/job_child/",
    )
    
    # Submit jobs
    farm_manager.submit_job(job_parent)
    farm_manager.submit_job(job_child)
    
    # Only parent job should be scheduled since child job depends on it
    farm_manager.run_scheduling_cycle()
    
    # Verify parent is running and child is still pending
    assert farm_manager.jobs["job_parent"].status == RenderJobStatus.RUNNING
    assert farm_manager.jobs["job_child"].status == RenderJobStatus.PENDING
    
    # Complete parent job
    farm_manager.complete_job("job_parent")
    
    # Run another scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Now child job should be scheduled
    assert farm_manager.jobs["job_child"].status == RenderJobStatus.RUNNING


def test_circular_dependency_detection(farm_manager):
    """Test that circular dependencies are detected and handled appropriately."""
    # Add a client using standard Client model
    client = Client(
        id="client1",
        name="Test Client",
        sla_tier="premium",
        guaranteed_resources=50,
        max_resources=80,
    )
    farm_manager.add_client(client)
    
    # Add a node
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
            specialized_for=["gpu_rendering"],
        ),
        power_efficiency_rating=85.0,
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
    
    # Submit jobs in sequence to test cycle detection
    farm_manager.submit_job(job_a)  # This should be fine
    assert farm_manager.jobs["job_a"].status == RenderJobStatus.PENDING
    
    farm_manager.submit_job(job_b)  # This should be fine
    assert farm_manager.jobs["job_b"].status == RenderJobStatus.PENDING
    
    # This creates a cycle - it should be marked as FAILED
    farm_manager.submit_job(job_c)  
    assert farm_manager.jobs["job_c"].status == RenderJobStatus.FAILED, \
        "Job C should be marked as FAILED due to circular dependency"
        
    # Check the audit log for the circular dependency error
    # In a complete implementation, we would verify this in the audit log
    
    # Run scheduling cycle - none of the jobs should be scheduled
    # because they all have dependencies affected by the cycle
    farm_manager.run_scheduling_cycle()
    
    # After running the cycle, all jobs in the dependency chain
    # should be marked as FAILED due to circular dependency
    assert farm_manager.jobs["job_a"].status == RenderJobStatus.FAILED
    assert farm_manager.jobs["job_b"].status == RenderJobStatus.FAILED
    assert farm_manager.jobs["job_c"].status == RenderJobStatus.FAILED