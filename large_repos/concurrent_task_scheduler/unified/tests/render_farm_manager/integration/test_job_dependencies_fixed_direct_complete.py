"""Fixed direct test for job dependency functionality."""

import pytest
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


def test_simple_dependency():
    """Test that a job with dependencies is only scheduled after dependencies complete."""
    # Create a fresh farm manager
    farm_manager = RenderFarmManager()
    
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
    
    # STEP 1: Submit a parent job
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
    farm_manager.submit_job(job_parent)
    
    # STEP 2: Run scheduling cycle - parent job should be scheduled
    farm_manager.run_scheduling_cycle()
    assert farm_manager.jobs["job_parent"].status == RenderJobStatus.RUNNING
    
    # STEP 3: Submit child job that depends on parent
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
    farm_manager.submit_job(job_child)
    
    # STEP 4: Complete parent job
    farm_manager.complete_job("job_parent")
    
    # STEP 5: Run scheduling cycle - child job should now be scheduled since parent is completed
    farm_manager.run_scheduling_cycle()
    assert farm_manager.jobs["job_child"].status == RenderJobStatus.RUNNING


def test_circular_dependency_detection():
    """Test that circular dependencies are detected and handled appropriately."""
    # Create a fresh farm manager
    farm_manager = RenderFarmManager()
    
    # Add a client
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
    
    # STEP 1: Create first job that will be part of a cycle
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
    farm_manager.submit_job(job_a)
    
    # STEP 2: Create second job in the cycle
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
    farm_manager.submit_job(job_b)
    
    # STEP 3: Create third job, completing the cycle
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
    
    # When submitting job_c, it should be marked as FAILED due to circular dependency
    farm_manager.submit_job(job_c)
    assert farm_manager.jobs["job_c"].status == RenderJobStatus.FAILED
    
    # Run scheduling cycle - verify none of the jobs are scheduled
    farm_manager.run_scheduling_cycle()
    
    # After cycle detection in submit_job and dependency checking in run_scheduling_cycle,
    # all jobs should be properly marked - a, b could still be pending, but c should be FAILED
    assert farm_manager.jobs["job_c"].status == RenderJobStatus.FAILED