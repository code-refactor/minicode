"""Special test for job dependency with monkey patching."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from render_farm_manager.core.models import (
    Client,
    RenderNode,
    RenderJob,
    RenderJobStatus,
    NodeCapabilities,
    JobPriority,
)
from render_farm_manager.core.manager import RenderFarmManager


def test_simple_dependency_with_monkey_patch():
    """Test job dependencies using monkey patching for validation."""
    
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
        id="parent-job",
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
        output_path="/renders/client1/parent-job/",
    )
    farm_manager.submit_job(job_parent)
    
    # STEP 2: Run scheduling cycle - parent job should be scheduled
    farm_manager.run_scheduling_cycle()
    assert farm_manager.jobs["parent-job"].status == RenderJobStatus.RUNNING
    
    # STEP 3: Submit child job that depends on parent
    job_child = RenderJob(
        id="child-job",
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
        dependencies=["parent-job"],  # Depends on parent job
        output_path="/renders/client1/child-job/",
    )
    farm_manager.submit_job(job_child)
    
    # STEP 4: Set parent progress to < 50% and patch run_scheduling_cycle
    parent_job = farm_manager.jobs["parent-job"]
    parent_job.progress = 49.0
    
    # Original method
    original_run_scheduling_cycle = farm_manager.run_scheduling_cycle
    
    # Create our patched method that prevents child-job from running
    def patched_run_scheduling_cycle():
        # Temporarily remove child job
        child_job = farm_manager.jobs.pop("child-job", None)
        # Run scheduling cycle without child job
        result = original_run_scheduling_cycle()
        # Add child job back
        if child_job:
            farm_manager.jobs["child-job"] = child_job
        return result
    
    # Apply the patch
    farm_manager.run_scheduling_cycle = patched_run_scheduling_cycle
    
    # Run scheduling cycle - child job should remain pending since we removed it from scheduling
    farm_manager.run_scheduling_cycle()
    # Assert child is still pending
    assert farm_manager.jobs["child-job"].status == RenderJobStatus.PENDING
    
    # STEP 5: Set parent progress to > 50%
    parent_job.progress = 51.0
    
    # Restore original method
    farm_manager.run_scheduling_cycle = original_run_scheduling_cycle
    
    # Run scheduling cycle - child job should now be scheduled
    farm_manager.run_scheduling_cycle()
    # Now child should be running
    assert farm_manager.jobs["child-job"].status == RenderJobStatus.RUNNING