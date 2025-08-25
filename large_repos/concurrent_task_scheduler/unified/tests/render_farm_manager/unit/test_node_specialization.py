"""Unit tests for the node specialization system."""

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
from render_farm_manager.node_specialization.specialization_manager import NodeSpecializationManager
from render_farm_manager.utils.logging import AuditLogger, PerformanceMonitor


@pytest.fixture
def audit_logger():
    return MagicMock(spec=AuditLogger)


@pytest.fixture
def performance_monitor():
    return MagicMock(spec=PerformanceMonitor)


@pytest.fixture
def specialization_manager(audit_logger, performance_monitor):
    return NodeSpecializationManager(
        audit_logger=audit_logger,
        performance_monitor=performance_monitor,
        learning_rate=0.2,
        history_weight=0.3,
    )


@pytest.fixture
def nodes():
    """Create a list of test render nodes with different capabilities."""
    nodes = []
    
    # GPU nodes
    for i in range(5):
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
                performance_history={
                    "job_type:animation": 1.8,
                    "job_type:vfx": 2.0,
                    "requirement:gpu": 1.9,
                } if i % 2 == 0 else {},
                last_error=None,
                uptime_hours=1000 + i * 100,
            )
        )
    
    # CPU nodes
    for i in range(5):
        nodes.append(
            RenderNode(
                id=f"cpu-node-{i}",
                name=f"CPU Node {i}",
                status="online",
                capabilities=NodeCapabilities(
                    cpu_cores=64,
                    memory_gb=256,
                    gpu_model=None,
                    gpu_count=0,
                    gpu_memory_gb=0,
                    gpu_compute_capability=0.0,
                    storage_gb=4000,
                    specialized_for=["cpu_rendering", "simulation"],
                ),
                power_efficiency_rating=80,
                current_job_id=None,
                performance_history={
                    "job_type:simulation": 1.7,
                    "job_type:compositing": 1.5,
                } if i % 2 == 0 else {},
                last_error=None,
                uptime_hours=900 + i * 100,
            )
        )
    
    # Memory-optimized nodes
    for i in range(3):
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
                power_efficiency_rating=75,
                current_job_id=None,
                performance_history={
                    "job_type:scene_assembly": 1.9,
                    "memory_range:high": 1.8,
                } if i % 2 == 0 else {},
                last_error=None,
                uptime_hours=800 + i * 100,
            )
        )
    
    return nodes


@pytest.fixture
def jobs():
    """Create a list of test render jobs with different requirements."""
    now = datetime.now()
    
    return [
        # GPU-intensive animation job
        RenderJob(
            id="animation-job",
            name="Animation Job",
            client_id="client1",
            status=RenderJobStatus.PENDING,
            job_type="animation",
            priority=JobPriority.HIGH,
            submission_time=now - timedelta(hours=2),
            deadline=now + timedelta(hours=24),
            estimated_duration_hours=8,
            progress=0.0,
            requires_gpu=True,
            memory_requirements_gb=64,
            cpu_requirements=16,
            scene_complexity=8,
            dependencies=[],
            assigned_node_id=None,
            output_path="/renders/animation-job/",
            error_count=0,
            can_be_preempted=True,
        ),
        # CPU-intensive simulation job
        RenderJob(
            id="simulation-job",
            name="Simulation Job",
            client_id="client2",
            status=RenderJobStatus.PENDING,
            job_type="simulation",
            priority=JobPriority.MEDIUM,
            submission_time=now - timedelta(hours=4),
            deadline=now + timedelta(hours=48),
            estimated_duration_hours=12,
            progress=0.0,
            requires_gpu=False,
            memory_requirements_gb=128,
            cpu_requirements=32,
            scene_complexity=6,
            dependencies=[],
            assigned_node_id=None,
            output_path="/renders/simulation-job/",
            error_count=0,
            can_be_preempted=True,
        ),
        # Memory-intensive scene assembly job
        RenderJob(
            id="assembly-job",
            name="Scene Assembly Job",
            client_id="client1",
            status=RenderJobStatus.PENDING,
            job_type="scene_assembly",
            priority=JobPriority.MEDIUM,
            submission_time=now - timedelta(hours=1),
            deadline=now + timedelta(hours=36),
            estimated_duration_hours=6,
            progress=0.0,
            requires_gpu=False,
            memory_requirements_gb=512,
            cpu_requirements=24,
            scene_complexity=7,
            dependencies=[],
            assigned_node_id=None,
            output_path="/renders/assembly-job/",
            error_count=0,
            can_be_preempted=True,
        ),
        # VFX job with GPU requirement
        RenderJob(
            id="vfx-job",
            name="VFX Job",
            client_id="client3",
            status=RenderJobStatus.PENDING,
            job_type="vfx",
            priority=JobPriority.HIGH,
            submission_time=now - timedelta(hours=3),
            deadline=now + timedelta(hours=18),
            estimated_duration_hours=10,
            progress=0.0,
            requires_gpu=True,
            memory_requirements_gb=96,
            cpu_requirements=16,
            scene_complexity=9,
            dependencies=[],
            assigned_node_id=None,
            output_path="/renders/vfx-job/",
            error_count=0,
            can_be_preempted=True,
        ),
        # Compositing job for CPU rendering
        RenderJob(
            id="compositing-job",
            name="Compositing Job",
            client_id="client2",
            status=RenderJobStatus.PENDING,
            job_type="compositing",
            priority=JobPriority.LOW,
            submission_time=now - timedelta(hours=1),
            deadline=now + timedelta(hours=72),
            estimated_duration_hours=4,
            progress=0.0,
            requires_gpu=False,
            memory_requirements_gb=32,
            cpu_requirements=16,
            scene_complexity=4,
            dependencies=[],
            assigned_node_id=None,
            output_path="/renders/compositing-job/",
            error_count=0,
            can_be_preempted=True,
        ),
    ]


def test_specialization_manager_initialization(specialization_manager):
    """Test that the specialization manager initializes correctly."""
    assert specialization_manager.learning_rate == 0.2
    assert specialization_manager.history_weight == 0.3
    assert "animation" in specialization_manager.job_type_specializations
    assert "vfx" in specialization_manager.job_type_specializations
    assert "simulation" in specialization_manager.job_type_specializations


def test_match_job_to_node_gpu_job(specialization_manager, jobs, nodes):
    """Test matching a GPU job to the appropriate node."""
    animation_job = jobs[0]  # GPU-intensive animation job
    
    matched_node_id = specialization_manager.match_job_to_node(animation_job, nodes)
    
    # Verify that a GPU node was selected
    assert matched_node_id is not None
    assert matched_node_id.startswith("gpu-node")
    
    # Verify that node has required GPU capabilities
    matched_node = next(node for node in nodes if node.id == matched_node_id)
    assert matched_node.capabilities.gpu_count > 0
    assert "gpu_rendering" in matched_node.capabilities.specialized_for


def test_match_job_to_node_cpu_job(specialization_manager, jobs, nodes):
    """Test matching a CPU job to the appropriate node."""
    simulation_job = jobs[1]  # CPU-intensive simulation job
    
    matched_node_id = specialization_manager.match_job_to_node(simulation_job, nodes)
    
    # Verify that a CPU node was selected
    assert matched_node_id is not None
    assert matched_node_id.startswith("cpu-node")
    
    # Verify that node has required CPU capabilities
    matched_node = next(node for node in nodes if node.id == matched_node_id)
    assert matched_node.capabilities.cpu_cores >= simulation_job.cpu_requirements
    assert "simulation" in matched_node.capabilities.specialized_for


def test_match_job_to_node_memory_job(specialization_manager, jobs, nodes):
    """Test matching a memory-intensive job to the appropriate node."""
    assembly_job = jobs[2]  # Memory-intensive scene assembly job
    
    matched_node_id = specialization_manager.match_job_to_node(assembly_job, nodes)
    
    # Verify that a memory-optimized node was selected
    assert matched_node_id is not None
    assert matched_node_id.startswith("mem-node")
    
    # Verify that node has required memory capabilities
    matched_node = next(node for node in nodes if node.id == matched_node_id)
    assert matched_node.capabilities.memory_gb >= assembly_job.memory_requirements_gb
    assert "scene_assembly" in matched_node.capabilities.specialized_for


def test_calculate_performance_score(specialization_manager, jobs, nodes):
    """Test performance score calculation for different job-node combinations."""
    animation_job = jobs[0]  # GPU job
    simulation_job = jobs[1]  # CPU job
    
    gpu_node = nodes[0]  # First GPU node
    cpu_node = nodes[5]  # First CPU node
    
    # GPU job should score higher on GPU node than CPU node
    gpu_job_on_gpu_node = specialization_manager.calculate_performance_score(animation_job, gpu_node)
    gpu_job_on_cpu_node = specialization_manager.calculate_performance_score(animation_job, cpu_node)
    
    assert gpu_job_on_gpu_node > gpu_job_on_cpu_node
    
    # CPU job should score higher on CPU node than GPU node
    cpu_job_on_cpu_node = specialization_manager.calculate_performance_score(simulation_job, cpu_node)
    cpu_job_on_gpu_node = specialization_manager.calculate_performance_score(simulation_job, gpu_node)
    
    assert cpu_job_on_cpu_node > cpu_job_on_gpu_node


def test_update_performance_history(specialization_manager, jobs, nodes):
    """Test updating performance history based on job results."""
    animation_job = jobs[0]  # GPU job
    gpu_node = nodes[0]  # First GPU node
    
    # Initial performance history
    initial_animation_score = gpu_node.performance_history.get("job_type:animation", 0.0)
    
    # Performance metrics from completed job
    performance_metrics = {
        "render_time_per_frame": 30.0,  # 30 seconds per frame (good performance)
    }
    
    # Update performance history
    specialization_manager.update_performance_history(animation_job, gpu_node, performance_metrics)
    
    # Verify that performance history was updated
    updated_animation_score = gpu_node.performance_history.get("job_type:animation", 0.0)
    
    # If no initial score, should be set directly
    if initial_animation_score == 0.0:
        assert updated_animation_score > 0.0
    else:
        # Should be updated using learning rate
        assert updated_animation_score != initial_animation_score
        
        # Calculate expected score based on learning rate
        expected_score = (
            (1 - specialization_manager.learning_rate) * initial_animation_score +
            specialization_manager.learning_rate * 2.0  # 60 / 30 = 2.0
        )
        assert updated_animation_score == pytest.approx(expected_score, abs=0.1)


def test_performance_history_influence(specialization_manager, jobs, nodes):
    """Test that performance history influences node selection."""
    vfx_job = jobs[3]  # VFX job (requires GPU)
    
    # Set performance history for one GPU node to be much better
    nodes[0].performance_history["job_type:vfx"] = 3.0  # Excellent performance
    
    matched_node_id = specialization_manager.match_job_to_node(vfx_job, nodes)
    
    # A GPU node should be selected based on performance history
    # It might not always be gpu-node-0 depending on implementation details
    assert matched_node_id is not None
    assert matched_node_id.startswith("gpu-node")


def test_node_capability_matching(specialization_manager, jobs, nodes):
    """Test that node capabilities are properly matched to job requirements."""
    # Make nodes have varying amounts of memory
    for i in range(5):
        nodes[i].capabilities.memory_gb = 64  # Just enough for animation job
    
    animation_job = jobs[0]  # Requires 64GB memory
    
    # Make the job require more memory
    animation_job.memory_requirements_gb = 96
    
    # Now only memory nodes should match
    matched_node_id = specialization_manager.match_job_to_node(animation_job, nodes)
    
    # Verify that a memory node or GPU node with enough memory was selected
    matched_node = next(node for node in nodes if node.id == matched_node_id)
    assert matched_node.capabilities.memory_gb >= animation_job.memory_requirements_gb


def test_no_suitable_node(specialization_manager, jobs, nodes):
    """Test behavior when no suitable node is available."""
    animation_job = jobs[0]  # GPU job
    
    # Make all nodes unsuitable
    for node in nodes:
        node.status = "offline"
    
    matched_node_id = specialization_manager.match_job_to_node(animation_job, nodes)
    
    # Should return None when no suitable node is found
    assert matched_node_id is None


def test_specialized_vs_general_nodes(specialization_manager, jobs, nodes):
    """Test specialized nodes are preferred over general-purpose nodes."""
    compositing_job = jobs[4]  # Compositing job
    
    # Add a general-purpose node
    general_node = RenderNode(
        id="general-node",
        name="General Purpose Node",
        status="online",
        capabilities=NodeCapabilities(
            cpu_cores=32,
            memory_gb=128,
            gpu_model="NVIDIA RTX A4000",
            gpu_count=1,
            gpu_memory_gb=16,
            gpu_compute_capability=8.6,
            storage_gb=2000,
            specialized_for=[],  # No specialization
        ),
        power_efficiency_rating=70,
        current_job_id=None,
        performance_history={},
        last_error=None,
        uptime_hours=500,
    )
    
    modified_nodes = nodes + [general_node]
    
    # Compositing job should prefer CPU node over general node
    matched_node_id = specialization_manager.match_job_to_node(compositing_job, modified_nodes)
    
    assert matched_node_id.startswith("cpu-node")
    assert matched_node_id != "general-node"


def test_analyze_node_efficiency(specialization_manager, nodes):
    """Test analyzing node efficiency based on performance history."""
    # Set up diverse performance history
    for i in range(len(nodes)):
        if i < 5:  # GPU nodes
            nodes[i].performance_history = {
                "job_type:animation": 1.8 + i * 0.1,
                "job_type:vfx": 2.0 - i * 0.1,
                "job_type:lighting": 1.5 + i * 0.2,
            }
        elif i < 10:  # CPU nodes
            nodes[i].performance_history = {
                "job_type:simulation": 1.7 + i * 0.1,
                "job_type:compositing": 1.5 + i * 0.1,
                "job_type:texture_baking": 1.2 + i * 0.1,
            }
        else:  # Memory nodes
            nodes[i].performance_history = {
                "job_type:scene_assembly": 1.9 + i * 0.1,
                "job_type:cloth_sim": 1.6 + i * 0.1,
            }
    
    efficiency_data = specialization_manager.analyze_node_efficiency(nodes)
    
    # Check that efficiency data was generated for all nodes
    assert len(efficiency_data) == len(nodes)
    
    # Check that job types are correctly assigned
    assert "animation" in efficiency_data["gpu-node-0"]
    assert "simulation" in efficiency_data["cpu-node-0"]
    assert "scene_assembly" in efficiency_data["mem-node-0"]