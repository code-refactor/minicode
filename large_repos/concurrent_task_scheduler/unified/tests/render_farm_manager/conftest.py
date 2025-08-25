"""Test configuration and fixtures for the Render Farm Manager."""

import datetime
import random
from typing import Dict, List
import pytest

from render_farm_manager.core.models import (
    RenderNode,
    RenderJob,
    Client,
    NodeCapabilities,
    RenderJobStatus,
    JobPriority,
)


@pytest.fixture
def clients() -> List[Client]:
    """Create a list of test clients with different SLA tiers."""
    return [
        Client(
            id="client1",
            name="Premium Studio",
            sla_tier="premium",
            guaranteed_resources=30,
            max_resources=50,
        ),
        Client(
            id="client2",
            name="Standard Studio",
            sla_tier="standard",
            guaranteed_resources=20,
            max_resources=40,
        ),
        Client(
            id="client3",
            name="Basic Studio",
            sla_tier="basic",
            guaranteed_resources=10,
            max_resources=20,
        ),
    ]


@pytest.fixture
def render_nodes() -> List[RenderNode]:
    """Create a list of test render nodes with different capabilities."""
    nodes = []
    
    # Create 10 GPU-optimized nodes
    for i in range(10):
        nodes.append(
            RenderNode(
                id=f"gpu-node-{i}",
                name=f"GPU Node {i}",
                status="online",
                capabilities=NodeCapabilities(
                    cpu_cores=32,
                    memory_gb=128,
                    gpu_model="NVIDIA RTX A6000",
                    gpu_count=4,
                    gpu_memory_gb=48,
                    gpu_compute_capability=8.6,
                    storage_gb=2000,
                    specialized_for=["gpu_rendering"],
                ),
                power_efficiency_rating=85,
                current_job_id=None,
                performance_history={},
                last_error=None,
                uptime_hours=random.randint(100, 5000),
            )
        )
    
    # Create 10 CPU-optimized nodes
    for i in range(10):
        nodes.append(
            RenderNode(
                id=f"cpu-node-{i}",
                name=f"CPU Node {i}",
                status="online",
                capabilities=NodeCapabilities(
                    cpu_cores=96,
                    memory_gb=512,
                    gpu_model=None,
                    gpu_count=0,
                    gpu_memory_gb=0,
                    gpu_compute_capability=0.0,
                    storage_gb=4000,
                    specialized_for=["cpu_rendering", "simulation"],
                ),
                power_efficiency_rating=75,
                current_job_id=None,
                performance_history={},
                last_error=None,
                uptime_hours=random.randint(100, 5000),
            )
        )
    
    # Create 5 memory-optimized nodes
    for i in range(5):
        nodes.append(
            RenderNode(
                id=f"mem-node-{i}",
                name=f"Memory Node {i}",
                status="online",
                capabilities=NodeCapabilities(
                    cpu_cores=48,
                    memory_gb=1024,
                    gpu_model="NVIDIA RTX A5000",
                    gpu_count=2,
                    gpu_memory_gb=24,
                    gpu_compute_capability=8.6,
                    storage_gb=8000,
                    specialized_for=["memory_intensive", "scene_assembly"],
                ),
                power_efficiency_rating=70,
                current_job_id=None,
                performance_history={},
                last_error=None,
                uptime_hours=random.randint(100, 5000),
            )
        )
    
    return nodes


@pytest.fixture
def render_jobs(clients) -> List[RenderJob]:
    """Create a list of test render jobs with different priorities and deadlines."""
    now = datetime.datetime.now()
    
    jobs = []
    for i in range(20):
        # Determine job type
        job_type = random.choice(["animation", "vfx", "simulation", "lighting", "compositing"])
        
        # Set resource requirements based on job type
        if job_type == "animation":
            requires_gpu = random.choice([True, False])
            memory_requirements = random.randint(16, 64)
        elif job_type == "vfx":
            requires_gpu = True
            memory_requirements = random.randint(32, 128)
        elif job_type == "simulation":
            requires_gpu = random.choice([True, False])
            memory_requirements = random.randint(64, 256)
        elif job_type == "lighting":
            requires_gpu = True
            memory_requirements = random.randint(16, 64)
        else:  # compositing
            requires_gpu = False
            memory_requirements = random.randint(16, 32)
        
        # Set deadline based on priority
        priority = random.choice([JobPriority.LOW, JobPriority.MEDIUM, JobPriority.HIGH, JobPriority.CRITICAL])
        if priority == JobPriority.CRITICAL:
            deadline = now + datetime.timedelta(hours=random.randint(1, 12))
        elif priority == JobPriority.HIGH:
            deadline = now + datetime.timedelta(days=random.randint(1, 2))
        elif priority == JobPriority.MEDIUM:
            deadline = now + datetime.timedelta(days=random.randint(3, 7))
        else:
            deadline = now + datetime.timedelta(days=random.randint(7, 14))
        
        # Select a client
        client = random.choice(clients)
        
        jobs.append(
            RenderJob(
                id=f"job-{i}",
                name=f"Render Job {i}",
                client_id=client.id,
                status=RenderJobStatus.PENDING,
                job_type=job_type,
                priority=priority,
                submission_time=now - datetime.timedelta(hours=random.randint(1, 48)),
                deadline=deadline,
                estimated_duration_hours=random.randint(1, 48),
                progress=0.0,
                requires_gpu=requires_gpu,
                memory_requirements_gb=memory_requirements,
                cpu_requirements=random.randint(4, 32),
                scene_complexity=random.randint(1, 10),
                dependencies=[],
                assigned_node_id=None,
                output_path=f"/renders/job-{i}/",
                error_count=0,
                can_be_preempted=priority != JobPriority.CRITICAL,
                supports_progressive_output=random.choice([True, False]),
            )
        )
    
    return jobs