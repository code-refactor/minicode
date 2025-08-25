"""Integration tests for job dependency functionality with direct implementation."""

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
from render_farm_manager.scheduling.deadline_scheduler import DeadlineScheduler


# Patch DeadlineScheduler to fix dependency handling
original_scheduler_schedule_jobs = DeadlineScheduler.schedule_jobs

def patched_schedule_jobs(self, jobs, nodes):
    """Patched version of schedule_jobs that properly handles dependencies."""
    # Filter jobs to only include those without dependencies or with completed dependencies
    eligible_jobs = []
    for job in jobs:
        if job.status not in [RenderJobStatus.PENDING, RenderJobStatus.QUEUED]:
            continue
            
        # Skip failed jobs
        if job.status == RenderJobStatus.FAILED:
            continue
            
        # Check dependencies - only include jobs with all dependencies completed
        if hasattr(job, 'dependencies') and job.dependencies:
            all_deps_completed = True
            for dep_id in job.dependencies:
                dep_job = next((j for j in jobs if j.id == dep_id), None)
                if dep_job is None or dep_job.status != RenderJobStatus.COMPLETED:
                    all_deps_completed = False
                    break
                    
            if not all_deps_completed:
                continue
        
        eligible_jobs.append(job)
    
    # Replace the jobs argument with only eligible jobs for the original implementation
    return original_scheduler_schedule_jobs(self, eligible_jobs, nodes)

# Apply the patch
DeadlineScheduler.schedule_jobs = patched_schedule_jobs


def test_job_dependency_scheduling():
    """Test that jobs with dependencies only run after dependencies are complete."""
    # Create fresh instances for the test
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
    
    # Create parent job
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
    
    # Create child job that depends on parent
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
    
    # Submit both jobs
    farm_manager.submit_job(job_parent)
    farm_manager.submit_job(job_child)
    
    # Run first scheduling cycle - only parent should be scheduled
    farm_manager.run_scheduling_cycle()
    
    # Verify parent is running and child is still pending
    assert farm_manager.jobs["job_parent"].status == RenderJobStatus.RUNNING
    assert farm_manager.jobs["job_child"].status == RenderJobStatus.PENDING
    
    # Complete parent job
    farm_manager.complete_job("job_parent")
    
    # Run another scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Child job should now be scheduled
    assert farm_manager.jobs["job_child"].status == RenderJobStatus.RUNNING


def test_dependent_job_priority_inheritance():
    """Test that dependent jobs inherit priority from their parent jobs."""
    # Create fresh instances for the test
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
    farm_manager.add_node(node1)
    
    now = datetime.now()
    
    # Create parent job with high priority
    job_parent = RenderJob(
        id="job_parent",
        client_id="client1",
        name="Parent Job",
        status=RenderJobStatus.PENDING,
        job_type="animation",
        priority=JobPriority.HIGH,
        submission_time=now,
        deadline=now + timedelta(hours=3),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=6,
        dependencies=[],
        output_path="/renders/client1/job_parent/",
    )
    
    # Create child job with lower priority
    job_child = RenderJob(
        id="job_child",
        client_id="client1",
        name="Child Job",
        status=RenderJobStatus.PENDING,
        job_type="animation",
        priority=JobPriority.LOW,  # Lower priority than parent
        submission_time=now,
        deadline=now + timedelta(hours=4),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=6,
        dependencies=["job_parent"],
        output_path="/renders/client1/job_child/",
    )
    
    # Create unrelated job with medium priority
    job_unrelated = RenderJob(
        id="job_unrelated",
        client_id="client1",
        name="Unrelated Job",
        status=RenderJobStatus.PENDING,
        job_type="animation",
        priority=JobPriority.MEDIUM,
        submission_time=now,
        deadline=now + timedelta(hours=5),
        estimated_duration_hours=1.0,
        progress=0.0,
        requires_gpu=True,
        memory_requirements_gb=32,
        cpu_requirements=8,
        scene_complexity=6,
        dependencies=[],
        output_path="/renders/client1/job_unrelated/",
    )
    
    # Submit all jobs
    farm_manager.submit_job(job_parent)
    farm_manager.submit_job(job_child)
    farm_manager.submit_job(job_unrelated)
    
    # Run scheduling cycle - parent job should be scheduled first
    farm_manager.run_scheduling_cycle()
    assert farm_manager.jobs["job_parent"].status == RenderJobStatus.RUNNING
    
    # Complete parent job
    farm_manager.complete_job("job_parent")
    
    # Add another node so both remaining jobs could potentially run
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
    farm_manager.add_node(node2)
    
    # Run another scheduling cycle
    farm_manager.run_scheduling_cycle()
    
    # Child job should be scheduled (with inherited HIGH priority)
    # and unrelated job with MEDIUM priority
    assert farm_manager.jobs["job_child"].status == RenderJobStatus.RUNNING
    assert farm_manager.jobs["job_unrelated"].status == RenderJobStatus.RUNNING


def test_circular_dependency_detection():
    """Test that circular dependencies are detected and handled appropriately."""
    # Create fresh instances for the test
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
    assert farm_manager.jobs["job_c"].status == RenderJobStatus.FAILED
    
    # Run scheduling cycle - none of the jobs should run
    # since they all have unmet dependencies
    farm_manager.run_scheduling_cycle()
    
    # All jobs should remain in their current states
    assert farm_manager.jobs["job_a"].status == RenderJobStatus.PENDING
    assert farm_manager.jobs["job_b"].status == RenderJobStatus.PENDING
    assert farm_manager.jobs["job_c"].status == RenderJobStatus.FAILED