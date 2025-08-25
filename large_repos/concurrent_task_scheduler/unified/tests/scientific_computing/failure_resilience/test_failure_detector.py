"""Tests for the failure detection system."""

from datetime import datetime, timedelta
import pytest

from concurrent_task_scheduler.failure_resilience.failure_detector import (
    FailureDetector,
    FailureRecoveryManager,
    FailureReport,
    FailureType,
    FailureSeverity,
    DetectionMethod,
    RecoveryStrategy,
    NodeHealthCheck,
)
from concurrent_task_scheduler.models import (
    ComputeNode,
    NodeStatus,
    NodeType,
    Result,
    Simulation,
    SimulationStage,
    SimulationStageStatus,
    SimulationPriority,
    SimulationStatus,
)


@pytest.fixture
def failure_detector():
    """Create a failure detector for testing."""
    return FailureDetector(heartbeat_interval=5, heartbeat_timeout=15)


@pytest.fixture
def sample_compute_node():
    """Create a sample compute node for testing."""
    return ComputeNode(
        id="node_001",
        name="Compute Node 1",
        node_type=NodeType.COMPUTE,
        status=NodeStatus.ONLINE,
        cpu_cores=32,
        memory_gb=128,
        gpu_count=4,
        storage_gb=2048,
        network_bandwidth_gbps=10,
        current_load={"cpu": 0.4, "memory": 0.3, "storage": 0.2},
        location="data_center_1",
    )


@pytest.fixture
def sample_simulation():
    """Create a sample simulation for testing."""
    # Create a simulation with stages
    stages = {}
    
    # Add a preprocessing stage
    preprocessing = SimulationStage(
        id="stage_preprocess",
        name="Data Preprocessing",
        progress=1.0,  # 100% complete
        status=SimulationStageStatus.COMPLETED,
        start_time=datetime.now() - timedelta(hours=2),
        end_time=datetime.now() - timedelta(hours=1),
        estimated_duration=timedelta(hours=1),
    )
    stages[preprocessing.id] = preprocessing
    
    # Add a main simulation stage
    main_stage = SimulationStage(
        id="stage_main",
        name="Main Simulation",
        progress=0.5,  # 50% complete
        status=SimulationStageStatus.RUNNING,
        start_time=datetime.now() - timedelta(hours=1),
        estimated_duration=timedelta(hours=2),
    )
    stages[main_stage.id] = main_stage
    
    # Add a postprocessing stage (not started yet)
    postprocessing = SimulationStage(
        id="stage_postprocess",
        name="Result Analysis",
        progress=0.0,  # Not started
        status=SimulationStageStatus.PENDING,
        estimated_duration=timedelta(minutes=30),
    )
    stages[postprocessing.id] = postprocessing
    
    # Create the simulation
    simulation = Simulation(
        id="sim_climate_test",
        name="Climate Model Test",
        creation_time=datetime.now() - timedelta(hours=3),
        status=SimulationStatus.RUNNING,
        priority=SimulationPriority.HIGH,
        stages=stages,
    )
    
    return simulation


@pytest.fixture
def recovery_manager(failure_detector):
    """Create a failure recovery manager for testing."""
    return FailureRecoveryManager(failure_detector)


def test_failure_detector_init(failure_detector):
    """Test the initialization of the failure detector."""
    assert failure_detector.heartbeat_interval == 5
    assert failure_detector.heartbeat_timeout == 15
    assert isinstance(failure_detector.last_heartbeat, dict)
    assert isinstance(failure_detector.node_health_history, dict)
    assert isinstance(failure_detector.simulation_health_history, dict)
    assert isinstance(failure_detector.failure_reports, dict)
    assert isinstance(failure_detector.thresholds, dict)


def test_record_heartbeat(failure_detector):
    """Test recording a heartbeat from a node."""
    node_id = "node_001"
    failure_detector.record_heartbeat(node_id)
    
    assert node_id in failure_detector.last_heartbeat
    assert isinstance(failure_detector.last_heartbeat[node_id], datetime)


def test_check_node_health(failure_detector, sample_compute_node):
    """Test checking the health of a node."""
    # First record a heartbeat so it's healthy
    failure_detector.record_heartbeat(sample_compute_node.id)
    
    # Check health
    health_check = failure_detector.check_node_health(sample_compute_node)
    
    assert isinstance(health_check, NodeHealthCheck)
    assert health_check.node_id == sample_compute_node.id
    assert health_check.status == sample_compute_node.status
    assert isinstance(health_check.metrics, dict)
    assert "cpu_load" in health_check.metrics
    assert "memory_usage" in health_check.metrics
    assert "disk_usage" in health_check.metrics
    assert health_check.is_healthy()
    
    # Should be tracked in health history
    assert sample_compute_node.id in failure_detector.node_health_history
    assert len(failure_detector.node_health_history[sample_compute_node.id]) == 1
    
    # Test heartbeat timeout
    # Set last heartbeat to exceed timeout
    failure_detector.last_heartbeat[sample_compute_node.id] = datetime.now() - timedelta(seconds=30)
    
    # Check health again
    health_check = failure_detector.check_node_health(sample_compute_node)
    
    assert not health_check.is_healthy()
    assert len(health_check.errors) > 0
    assert "Heartbeat timeout" in health_check.errors[0]


def test_check_simulation_health(failure_detector, sample_simulation):
    """Test checking the health of a simulation."""
    # Check health
    warnings = failure_detector.check_simulation_health(sample_simulation)
    
    assert isinstance(warnings, list)
    
    # Should initialize health history
    assert sample_simulation.id in failure_detector.simulation_health_history
    assert "last_health_check" in failure_detector.simulation_health_history[sample_simulation.id]
    
    # Test progress stall detection
    # Set last progress update to exceed threshold
    failure_detector.simulation_health_history[sample_simulation.id]["last_progress_update"] = datetime.now() - timedelta(minutes=120)
    
    # Check health again
    warnings = failure_detector.check_simulation_health(sample_simulation)
    
    assert len(warnings) > 0
    assert "progress stalled" in warnings[0]


def test_update_simulation_progress(failure_detector):
    """Test recording progress updates for simulations."""
    sim_id = "sim_001"
    
    # Should initialize if not exists
    failure_detector.update_simulation_progress(sim_id, 0.5)
    
    assert sim_id in failure_detector.simulation_health_history
    assert "last_progress_update" in failure_detector.simulation_health_history[sim_id]
    assert isinstance(failure_detector.simulation_health_history[sim_id]["last_progress_update"], datetime)


def test_update_simulation_status(failure_detector):
    """Test recording status changes for simulations."""
    sim_id = "sim_001"
    
    # Should initialize if not exists
    failure_detector.update_simulation_status(sim_id, "running")
    
    assert sim_id in failure_detector.simulation_health_history
    assert "last_status_change" in failure_detector.simulation_health_history[sim_id]
    assert isinstance(failure_detector.simulation_health_history[sim_id]["last_status_change"], datetime)


def test_detect_node_failures(failure_detector, sample_compute_node):
    """Test detecting failures in compute nodes."""
    # Make the node unhealthy
    sample_compute_node.current_load = {"cpu": 0.98, "memory": 0.99, "storage": 0.97}
    failure_detector.last_heartbeat[sample_compute_node.id] = datetime.now() - timedelta(seconds=60)
    
    # Detect failures
    failures = failure_detector.detect_node_failures({sample_compute_node.id: sample_compute_node})
    
    assert len(failures) > 0
    assert isinstance(failures[0], FailureReport)
    assert failures[0].node_id == sample_compute_node.id
    assert failures[0].id in failure_detector.failure_reports


def test_detect_simulation_failures(failure_detector, sample_simulation):
    """Test detecting failures in simulations."""
    # Create stalled progress situation
    failure_detector.simulation_health_history[sample_simulation.id] = {
        "last_progress_update": datetime.now() - timedelta(minutes=120),
        "last_status_change": datetime.now(),
        "last_health_check": datetime.now(),
    }
    
    # Detect failures
    failures = failure_detector.detect_simulation_failures({sample_simulation.id: sample_simulation})
    
    assert len(failures) > 0
    assert isinstance(failures[0], FailureReport)
    assert failures[0].simulation_id == sample_simulation.id
    assert failures[0].id in failure_detector.failure_reports
    
    # Should have incremented the failure count
    assert sample_simulation.id in failure_detector.simulation_failure_counts
    assert failure_detector.simulation_failure_counts[sample_simulation.id] > 0


def test_report_failure(failure_detector):
    """Test manually reporting a failure."""
    # Report a node failure
    failure = failure_detector.report_failure(
        failure_type=FailureType.NODE_OFFLINE,
        severity=FailureSeverity.HIGH,
        description="Node went offline unexpectedly",
        node_id="node_001",
    )
    
    assert isinstance(failure, FailureReport)
    assert failure.id in failure_detector.failure_reports
    assert failure.failure_type == FailureType.NODE_OFFLINE
    assert failure.severity == FailureSeverity.HIGH
    assert failure.node_id == "node_001"
    
    # Report a simulation failure
    failure = failure_detector.report_failure(
        failure_type=FailureType.PROCESS_CRASH,
        severity=FailureSeverity.MEDIUM,
        description="Simulation process crashed",
        simulation_id="sim_001",
        stage_id="stage_002",
    )
    
    assert isinstance(failure, FailureReport)
    assert failure.id in failure_detector.failure_reports
    assert failure.failure_type == FailureType.PROCESS_CRASH
    assert failure.severity == FailureSeverity.MEDIUM
    assert failure.simulation_id == "sim_001"
    assert failure.stage_id == "stage_002"
    
    # Increments failure counts
    assert "node_001" in failure_detector.node_failure_counts
    assert "sim_001" in failure_detector.simulation_failure_counts


def test_get_active_failures(failure_detector):
    """Test getting active failures."""
    # Create a few failures
    failure1 = failure_detector.report_failure(
        failure_type=FailureType.NODE_OFFLINE,
        severity=FailureSeverity.HIGH,
        description="Node went offline unexpectedly",
        node_id="node_001",
    )
    
    failure2 = failure_detector.report_failure(
        failure_type=FailureType.PROCESS_CRASH,
        severity=FailureSeverity.MEDIUM,
        description="Simulation process crashed",
        simulation_id="sim_001",
    )
    
    failure3 = failure_detector.report_failure(
        failure_type=FailureType.MEMORY_EXHAUSTION,
        severity=FailureSeverity.HIGH,
        description="Out of memory",
        node_id="node_002",
        simulation_id="sim_002",
    )
    
    # Mark one as resolved
    failure2.mark_resolved("manual intervention")
    
    # Get active failures
    active = failure_detector.get_active_failures()
    assert len(active) == 2
    assert failure1.id in [f.id for f in active]
    assert failure3.id in [f.id for f in active]
    assert failure2.id not in [f.id for f in active]
    
    # Get node-specific failures
    node_failures = failure_detector.get_active_failures(node_id="node_001")
    assert len(node_failures) == 1
    assert node_failures[0].id == failure1.id
    
    # Get simulation-specific failures
    sim_failures = failure_detector.get_active_failures(simulation_id="sim_002")
    assert len(sim_failures) == 1
    assert sim_failures[0].id == failure3.id


def test_resolve_failure(failure_detector):
    """Test resolving a failure."""
    # Create a failure
    failure = failure_detector.report_failure(
        failure_type=FailureType.NODE_OFFLINE,
        severity=FailureSeverity.HIGH,
        description="Node went offline unexpectedly",
        node_id="node_001",
    )
    
    # Resolve it
    result = failure_detector.resolve_failure(failure.id, "manual restart")
    
    assert result.success
    assert failure_detector.failure_reports[failure.id].resolved
    assert failure_detector.failure_reports[failure.id].resolution_time is not None
    assert failure_detector.failure_reports[failure.id].resolution_method == "manual restart"
    
    # Test with non-existent failure
    result = failure_detector.resolve_failure("nonexistent", "reboot")
    assert not result.success
    assert "not found" in result.error
    
    # Test with already resolved failure
    result = failure_detector.resolve_failure(failure.id, "another method")
    assert not result.success
    assert "already resolved" in result.error


def test_reliability_metrics(failure_detector, sample_compute_node):
    """Test reliability metrics calculation."""
    # Record some health checks
    node_id = sample_compute_node.id
    
    # Record healthy checks
    for _ in range(5):
        failure_detector.record_heartbeat(node_id)
        health_check = failure_detector.check_node_health(sample_compute_node)
        assert health_check.is_healthy()
    
    # Calculate reliability score
    score = failure_detector.get_node_reliability_score(node_id)
    assert score == 1.0  # All checks were healthy
    
    # Make unhealthy and record more checks
    sample_compute_node.current_load = {"cpu": 0.98, "memory": 0.99, "storage": 0.97}
    failure_detector.last_heartbeat[node_id] = datetime.now() - timedelta(seconds=60)
    
    for _ in range(5):
        health_check = failure_detector.check_node_health(sample_compute_node)
        assert not health_check.is_healthy()
    
    # Calculate reliability score
    score = failure_detector.get_node_reliability_score(node_id)
    assert 0.0 <= score <= 0.5  # Some checks were unhealthy


def test_failure_type_determination(failure_detector):
    """Test determining failure types from error messages."""
    assert failure_detector._determine_failure_type("Heartbeat timeout detected") == FailureType.NODE_OFFLINE
    assert failure_detector._determine_failure_type("High CPU load detected") == FailureType.RESOURCE_CONTENTION
    assert failure_detector._determine_failure_type("Memory usage at 95%") == FailureType.MEMORY_EXHAUSTION
    assert failure_detector._determine_failure_type("Disk space critical") == FailureType.DISK_FULL
    assert failure_detector._determine_failure_type("Network errors detected") == FailureType.NETWORK_FAILURE
    assert failure_detector._determine_failure_type("Process appears stalled") == FailureType.DEADLOCK
    assert failure_detector._determine_failure_type("Simulation exceeded time limit") == FailureType.TIMEOUT
    assert failure_detector._determine_failure_type("Storage system failure") == FailureType.STORAGE_FAILURE
    assert failure_detector._determine_failure_type("Unknown error") == FailureType.UNKNOWN


def test_recovery_manager_init(recovery_manager, failure_detector):
    """Test initialization of recovery manager."""
    assert recovery_manager.detector == failure_detector
    assert isinstance(recovery_manager.recovery_strategies, dict)
    assert len(recovery_manager.recovery_strategies) > 0
    assert isinstance(recovery_manager.recovery_in_progress, dict)
    assert isinstance(recovery_manager.recovery_history, dict)


def test_get_recovery_strategy(recovery_manager):
    """Test getting recovery strategies for failures."""
    # Create a failure report
    failure = FailureReport(
        id="failure_001",
        failure_type=FailureType.NODE_OFFLINE,
        severity=FailureSeverity.HIGH,
        detection_time=datetime.now(),
        detection_method=DetectionMethod.HEARTBEAT,
        node_id="node_001",
    )
    
    # Get strategy
    strategy = recovery_manager.get_recovery_strategy(failure)
    
    assert isinstance(strategy, RecoveryStrategy)
    assert strategy in recovery_manager.recovery_strategies[FailureType.NODE_OFFLINE]
    
    # Get strategy with previous attempts
    strategy2 = recovery_manager.get_recovery_strategy(
        failure, previous_attempts=[strategy]
    )
    
    # Should get a different strategy if available
    if len(recovery_manager.recovery_strategies[FailureType.NODE_OFFLINE]) > 1:
        assert strategy2 != strategy
    
    # Test with all strategies tried
    all_strategies = recovery_manager.recovery_strategies[FailureType.NODE_OFFLINE]
    strategy3 = recovery_manager.get_recovery_strategy(
        failure, previous_attempts=list(all_strategies)
    )
    
    # Should cycle back to first strategy
    assert strategy3 == all_strategies[0]


def test_initiate_recovery(recovery_manager, failure_detector):
    """Test initiating recovery for a failure."""
    # Create a failure
    failure = failure_detector.report_failure(
        failure_type=FailureType.NODE_OFFLINE,
        severity=FailureSeverity.HIGH,
        description="Node went offline unexpectedly",
        node_id="node_001",
    )
    
    # Initiate recovery
    result = recovery_manager.initiate_recovery(failure.id)
    
    assert result.success
    assert isinstance(result.value, RecoveryStrategy)
    assert failure.id in recovery_manager.recovery_in_progress
    assert len(failure.recovery_attempts) == 1
    assert failure.recovery_attempts[0]["method"] == result.value.value
    
    # Test with specified strategy
    failure2 = failure_detector.report_failure(
        failure_type=FailureType.PROCESS_CRASH,
        severity=FailureSeverity.MEDIUM,
        description="Simulation process crashed",
        simulation_id="sim_001",
    )
    
    result2 = recovery_manager.initiate_recovery(failure2.id, RecoveryStrategy.RESTORE_CHECKPOINT)
    
    assert result2.success
    assert result2.value == RecoveryStrategy.RESTORE_CHECKPOINT
    
    # Test with non-existent failure
    result3 = recovery_manager.initiate_recovery("nonexistent")
    assert not result3.success
    
    # Test with already in-progress recovery
    result4 = recovery_manager.initiate_recovery(failure.id)
    assert not result4.success
    assert "already in progress" in result4.error
    
    # Test with simulation recovery tracking
    assert "sim_001" in recovery_manager.recovery_history
    assert len(recovery_manager.recovery_history["sim_001"]) == 1


def test_complete_recovery(recovery_manager, failure_detector):
    """Test completing a recovery operation."""
    # Create a failure and initiate recovery
    failure = failure_detector.report_failure(
        failure_type=FailureType.NODE_OFFLINE,
        severity=FailureSeverity.HIGH,
        description="Node went offline unexpectedly",
        node_id="node_001",
        simulation_id="sim_003",
    )
    
    recovery_manager.initiate_recovery(failure.id)
    
    # Complete recovery as successful
    result = recovery_manager.complete_recovery(failure.id, True, {"action": "node restarted"})
    
    assert result.success
    assert failure.id not in recovery_manager.recovery_in_progress
    assert failure.recovery_attempts[0]["success"]
    assert "action" in failure.recovery_attempts[0]["details"]
    
    # Simulation history should be updated
    assert "sim_003" in recovery_manager.recovery_history
    assert len(recovery_manager.recovery_history["sim_003"]) == 1
    assert recovery_manager.recovery_history["sim_003"][0]["completed"]
    assert recovery_manager.recovery_history["sim_003"][0]["success"]
    
    # Test with non-existent failure
    result = recovery_manager.complete_recovery("nonexistent", True)
    assert not result.success
    
    # Test with no recovery in progress
    result = recovery_manager.complete_recovery(failure.id, True)
    assert not result.success
    assert "No recovery in progress" in result.error


def test_get_active_recoveries(recovery_manager, failure_detector):
    """Test getting active recovery operations."""
    # Create failures and initiate recoveries
    failure1 = failure_detector.report_failure(
        failure_type=FailureType.NODE_OFFLINE,
        severity=FailureSeverity.HIGH,
        description="Node went offline unexpectedly",
        node_id="node_001",
    )
    
    failure2 = failure_detector.report_failure(
        failure_type=FailureType.PROCESS_CRASH,
        severity=FailureSeverity.MEDIUM,
        description="Simulation process crashed",
        simulation_id="sim_001",
    )
    
    recovery_manager.initiate_recovery(failure1.id)
    recovery_manager.initiate_recovery(failure2.id)
    
    # Get active recoveries
    active = recovery_manager.get_active_recoveries()
    
    assert len(active) == 2
    assert failure1.id in active
    assert failure2.id in active
    assert isinstance(active[failure1.id], RecoveryStrategy)
    
    # Complete one recovery
    recovery_manager.complete_recovery(failure1.id, True)
    
    # Get active recoveries again
    active = recovery_manager.get_active_recoveries()
    
    assert len(active) == 1
    assert failure1.id not in active
    assert failure2.id in active


def test_cancel_recovery(recovery_manager, failure_detector):
    """Test canceling an in-progress recovery."""
    # Create a failure and initiate recovery
    failure = failure_detector.report_failure(
        failure_type=FailureType.NODE_OFFLINE,
        severity=FailureSeverity.HIGH,
        description="Node went offline unexpectedly",
        node_id="node_001",
        simulation_id="sim_005",
    )
    
    recovery_manager.initiate_recovery(failure.id)
    
    # Cancel recovery
    result = recovery_manager.cancel_recovery(failure.id)
    
    assert result.success
    assert failure.id not in recovery_manager.recovery_in_progress
    assert not failure.recovery_attempts[0]["success"]
    assert failure.recovery_attempts[0]["details"]["status"] == "cancelled"
    
    # Simulation history should be updated
    assert "sim_005" in recovery_manager.recovery_history
    assert len(recovery_manager.recovery_history["sim_005"]) == 1
    assert recovery_manager.recovery_history["sim_005"][0]["completed"]
    assert not recovery_manager.recovery_history["sim_005"][0]["success"]
    
    # Test with non-existent or no recovery in progress
    result = recovery_manager.cancel_recovery("nonexistent")
    assert not result.success
    
    result = recovery_manager.cancel_recovery(failure.id)
    assert not result.success


def test_process_failures(recovery_manager, failure_detector):
    """Test automatic processing of unresolved failures."""
    # Create some failures
    for i in range(10):
        failure_detector.report_failure(
            failure_type=FailureType.NODE_OFFLINE if i % 2 == 0 else FailureType.PROCESS_CRASH,
            severity=FailureSeverity.HIGH if i < 3 else 
                     FailureSeverity.MEDIUM if i < 6 else
                     FailureSeverity.LOW,
            description=f"Test failure {i}",
            node_id=f"node_{i}" if i % 2 == 0 else None,
            simulation_id=f"sim_{i}" if i % 2 == 1 else None,
        )
    
    # Process failures
    processed = recovery_manager.process_failures()
    
    # Should process up to 3 failures at once
    assert len(processed) <= 3
    
    # Priorities should be respected - critical/high severity first
    for failure_id in processed:
        failure = failure_detector.failure_reports[failure_id]
        assert failure.severity in [FailureSeverity.CRITICAL, FailureSeverity.HIGH]
        assert failure_id in recovery_manager.recovery_in_progress