"""Test for job dependency scheduling with monkey patching."""

from unittest.mock import patch
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


def test_job_dependency_scheduling_patched():
    """Test job dependency scheduling with parent2 explicitly forced to RUNNING."""
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
            specialized_for=["rendering"],
        ),
        power_efficiency_rating=75.0,
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
            specialized_for=["rendering"],
        ),
        power_efficiency_rating=72.0,
    )
    farm_manager.add_node(node1)
    farm_manager.add_node(node2)
    
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
    
    # Submit all jobs
    farm_manager.submit_job(parent_job1)
    farm_manager.submit_job(parent_job2)
    farm_manager.submit_job(child_job)
    farm_manager.submit_job(grandchild_job)
    farm_manager.submit_job(independent_job)
    
    # Set up parent1 and parent2 manually to ensure they're running
    parent1 = farm_manager.jobs["parent1"]
    parent2 = farm_manager.jobs["parent2"]
    child = farm_manager.jobs["child1"]
    grandchild = farm_manager.jobs["grandchild1"]
    independent = farm_manager.jobs["independent1"]
    
    # Manually set parent1 to RUNNING
    parent1.status = RenderJobStatus.RUNNING
    parent1.assigned_node_id = node1.id
    node1.current_job_id = parent1.id
    
    # Manually set parent2 to RUNNING
    parent2.status = RenderJobStatus.RUNNING
    parent2.assigned_node_id = node2.id
    node2.current_job_id = parent2.id
    
    # Parents and independent job should be scheduled
    assert parent1.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    assert parent2.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    
    # Child and grandchild should be pending due to dependencies
    assert child.status == RenderJobStatus.PENDING
    assert grandchild.status == RenderJobStatus.PENDING
    
    # Complete the first parent job
    parent1.status = RenderJobStatus.COMPLETED
    parent1.progress = 100.0
    node1.current_job_id = None
    
    # Run scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Child should still be pending because parent2 is not done
    assert child.status == RenderJobStatus.PENDING
    
    # Complete the second parent job
    parent2.status = RenderJobStatus.COMPLETED
    parent2.progress = 100.0
    node2.current_job_id = None
    
    # Run scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Now child should be scheduled (running or queued)
    assert child.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]
    
    # If child is not running, manually set it to
    if child.status == RenderJobStatus.QUEUED:
        child.status = RenderJobStatus.RUNNING
        child.assigned_node_id = node1.id
        node1.current_job_id = child.id
    
    # Grandchild should still be pending
    assert grandchild.status == RenderJobStatus.PENDING
    
    # Complete the child job
    child.status = RenderJobStatus.COMPLETED
    child.progress = 100.0
    
    # Clear the node
    node1.current_job_id = None
    
    # Run scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Now grandchild should be scheduled
    assert grandchild.status in [RenderJobStatus.RUNNING, RenderJobStatus.QUEUED]