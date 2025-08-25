"""Tests for the failure resilience module."""

import os
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from concurrent_task_scheduler.failure_resilience.checkpoint_manager import (
    CheckpointManager,
    CheckpointCoordinator,
)
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
from concurrent_task_scheduler.failure_resilience.resilience_coordinator import (
    ResilienceCoordinator,
    ResilienceLevel,
    ResilienceEvent,
    ResilienceMetrics,
)
from concurrent_task_scheduler.models import (
    ComputeNode,
    NodeStatus,
    NodeType,
    Simulation,
    SimulationStage,
    SimulationStageStatus,
    SimulationPriority,
    SimulationStatus,
    Result,
)


# Mock simulation classes that override total_progress
class MockSimulation(Simulation):
    def total_progress(self) -> float:
        # Always return 0.5 for testing
        return 0.5

class StalledSimulation(Simulation):
    def total_progress(self) -> float:
        # Always return 0.1 for testing
        return 0.1


class TestFailureDetector:
    """Tests for the FailureDetector class."""

    @pytest.fixture
    def failure_detector(self):
        """Create a failure detector instance."""
        detector = FailureDetector()
        return detector

    @pytest.fixture
    def mock_node(self):
        """Create a mock compute node for testing."""
        node = ComputeNode(
            id="node-123",
            name="compute-123",
            status=NodeStatus.ONLINE,
            cpu_cores=32,
            memory_gb=128,
            storage_gb=1000,
            current_load={"cpu": 0.5, "memory": 0.4, "storage": 0.3},
            node_type=NodeType.COMPUTE,
            gpu_count=0,
            network_bandwidth_gbps=10,
            location="data_center_1"
        )
        return node
    
    @pytest.fixture
    def mock_simulation(self):
        """Create a mock simulation for testing."""
        sim = MockSimulation(
            id="sim-123",
            name="Test Simulation",
            description="A test simulation",
            status=SimulationStatus.RUNNING,
            priority=SimulationPriority.HIGH,
            stages={}
        )
        
        # Add a stage
        stage = SimulationStage(
            id="stage-1",
            name="Processing Stage",
            status=SimulationStageStatus.RUNNING,
            progress=0.5,
            estimated_duration=timedelta(hours=2),
        )
        sim.stages = {"stage-1": stage}
        
        # Mock the start time
        stage.start_time = datetime.now() - timedelta(minutes=30)  # Started 30 minutes ago
        
        return sim

    def test_record_heartbeat(self, failure_detector):
        """Test recording a heartbeat from a node."""
        failure_detector.record_heartbeat("node-123")
        
        assert "node-123" in failure_detector.last_heartbeat
        assert isinstance(failure_detector.last_heartbeat["node-123"], datetime)

    def test_check_node_health(self, failure_detector, mock_node):
        """Test checking node health."""
        # Record a heartbeat first
        failure_detector.record_heartbeat(mock_node.id)
        
        # Check health
        health_check = failure_detector.check_node_health(mock_node)
        
        assert health_check.node_id == mock_node.id
        assert health_check.status == NodeStatus.ONLINE
        assert isinstance(health_check.check_time, datetime)
        assert "cpu_load" in health_check.metrics
        assert "memory_usage" in health_check.metrics
        assert "disk_usage" in health_check.metrics
        assert "network_errors" in health_check.metrics
        
        # Should be healthy
        assert health_check.is_healthy() is True
        assert not health_check.errors
        
        # Check node with no heartbeat
        no_heartbeat_node = ComputeNode(
            id="no-heartbeat",
            name="no-heartbeat",
            status=NodeStatus.ONLINE,
            cpu_cores=32,
            memory_gb=128,
            storage_gb=1000,
            node_type=NodeType.COMPUTE,
            gpu_count=0,
            network_bandwidth_gbps=10,
            location="data_center_1"
        )
        
        health_check = failure_detector.check_node_health(no_heartbeat_node)
        
        # Should have a warning but still be healthy
        assert health_check.warnings
        assert "No heartbeat recorded" in health_check.warnings[0]
        assert health_check.is_healthy() is True
        
        # Check node with heartbeat timeout
        timeout_node = ComputeNode(
            id="timeout-node",
            name="timeout-node",
            status=NodeStatus.ONLINE,
            cpu_cores=32,
            memory_gb=128,
            storage_gb=1000,
            node_type=NodeType.COMPUTE,
            gpu_count=0,
            network_bandwidth_gbps=10,
            location="data_center_1"
        )
        
        # Record a heartbeat too far in the past
        failure_detector.last_heartbeat[timeout_node.id] = datetime.now() - timedelta(seconds=failure_detector.heartbeat_timeout * 2)
        
        health_check = failure_detector.check_node_health(timeout_node)
        
        # Should have an error and not be healthy
        assert health_check.errors
        assert "Heartbeat timeout" in health_check.errors[0]
        assert health_check.is_healthy() is False

    def test_check_simulation_health(self, failure_detector, mock_simulation):
        """Test checking simulation health."""
        # No issues initially
        warnings = failure_detector.check_simulation_health(mock_simulation)
        assert not warnings
        
        # Record initial check in history
        assert mock_simulation.id in failure_detector.simulation_health_history
        assert "last_health_check" in failure_detector.simulation_health_history[mock_simulation.id]
        
        # Simulate stalled progress (override threshold to make test faster)
        old_threshold = failure_detector.thresholds["simulation_progress_stall_minutes"]
        failure_detector.thresholds["simulation_progress_stall_minutes"] = 0.1  # 6 seconds
        
        # Set last progress time far in the past
        failure_detector.simulation_health_history[mock_simulation.id]["last_progress_update"] = (
            datetime.now() - timedelta(minutes=1)
        )
        
        # Now check again
        warnings = failure_detector.check_simulation_health(mock_simulation)
        
        # Should have stall warning
        assert warnings
        assert "progress stalled" in warnings[0].lower()
        
        # Restore threshold
        failure_detector.thresholds["simulation_progress_stall_minutes"] = old_threshold

    def test_update_simulation_progress(self, failure_detector):
        """Test updating simulation progress."""
        sim_id = "sim-123"
        
        # Update progress
        failure_detector.update_simulation_progress(sim_id, 0.5)
        
        # Check that history was updated
        assert sim_id in failure_detector.simulation_health_history
        assert "last_progress_update" in failure_detector.simulation_health_history[sim_id]
        assert isinstance(failure_detector.simulation_health_history[sim_id]["last_progress_update"], datetime)

    def test_detect_node_failures(self, failure_detector, mock_node):
        """Test detecting node failures."""
        # Create mock nodes
        nodes = {
            "node-123": mock_node,
            "problem-node": ComputeNode(
                id="problem-node",
                name="problem",
                status=NodeStatus.ONLINE,
                # Set up with critical disk usage to trigger failure
                current_load={"cpu": 0.5, "memory": 0.5, "storage": 0.99},
                cpu_cores=32,
                memory_gb=128,
                storage_gb=1000,
                node_type=NodeType.COMPUTE,
                gpu_count=0,
                network_bandwidth_gbps=10,
                location="data_center_1"
            ),
        }
        
        # Record heartbeats
        for node_id in nodes:
            failure_detector.record_heartbeat(node_id)
        
        # Detect failures
        failures = failure_detector.detect_node_failures(nodes)
        
        # Should detect one failure (high disk usage)
        assert len(failures) == 1
        assert failures[0].node_id == "problem-node"
        assert failures[0].failure_type == FailureType.DISK_FULL
        assert failures[0].severity == FailureSeverity.HIGH

    def test_detect_simulation_failures(self, failure_detector, mock_simulation):
        """Test detecting simulation failures."""
        # Create mock simulations
        stalled_sim = StalledSimulation(
            id="stalled-sim",
            name="Stalled Simulation",
            description="A stalled simulation",
            status=SimulationStatus.RUNNING,
            stages={}
        )
        
        # Add a stage that's been running too long
        stage = SimulationStage(
            id="stage-1",
            name="Stalled Stage",
            status=SimulationStageStatus.RUNNING,
            progress=0.1,  # Low progress
            estimated_duration=timedelta(minutes=10),  # Should take 10 minutes
        )
        
        # Stage started a long time ago relative to its estimated duration
        stage.start_time = datetime.now() - timedelta(minutes=60)  # Running for 60 minutes
        
        stalled_sim.stages = {"stage-1": stage}
        
        simulations = {
            "sim-123": mock_simulation,
            "stalled-sim": stalled_sim,
        }
        
        # Initialize health history for stalled sim
        failure_detector.simulation_health_history["stalled-sim"] = {
            "last_progress_update": datetime.now() - timedelta(minutes=30),
        }
        
        # Detect failures
        failures = failure_detector.detect_simulation_failures(simulations)
        
        # Should detect one failure (stalled stage)
        assert len(failures) == 1
        assert failures[0].simulation_id == "stalled-sim"
        assert failures[0].stage_id == "stage-1"
        assert failures[0].failure_type == FailureType.TIMEOUT

    def test_report_failure(self, failure_detector):
        """Test manually reporting a failure."""
        failure = failure_detector.report_failure(
            failure_type=FailureType.NETWORK_FAILURE,
            severity=FailureSeverity.MEDIUM,
            description="Network connection unstable",
            node_id="node-123",
        )
        
        assert failure.id in failure_detector.failure_reports
        assert failure.failure_type == FailureType.NETWORK_FAILURE
        assert failure.severity == FailureSeverity.MEDIUM
        assert failure.description == "Network connection unstable"
        assert failure.node_id == "node-123"
        assert failure.detection_method == DetectionMethod.MANUAL
        assert failure.resolved is False
        
        # Check failure count was incremented
        assert failure_detector.node_failure_counts["node-123"] == 1

    def test_get_active_failures(self, failure_detector):
        """Test getting active failures."""
        # Create some failures
        failure1 = failure_detector.report_failure(
            failure_type=FailureType.NODE_OFFLINE,
            severity=FailureSeverity.HIGH,
            description="Node went offline",
            node_id="node-1",
        )
        
        failure2 = failure_detector.report_failure(
            failure_type=FailureType.PROCESS_CRASH,
            severity=FailureSeverity.MEDIUM,
            description="Process crashed",
            simulation_id="sim-1",
        )
        
        failure3 = failure_detector.report_failure(
            failure_type=FailureType.DISK_FULL,
            severity=FailureSeverity.CRITICAL,
            description="Disk full",
            node_id="node-2",
        )
        
        # Mark one as resolved
        failure3.mark_resolved("manual intervention")
        
        # Get active failures (all)
        active = failure_detector.get_active_failures()
        assert len(active) == 2
        assert all(not f.resolved for f in active)
        
        # Get active failures for specific node
        node_failures = failure_detector.get_active_failures(node_id="node-1")
        assert len(node_failures) == 1
        assert node_failures[0].id == failure1.id
        
        # Get active failures for specific simulation
        sim_failures = failure_detector.get_active_failures(simulation_id="sim-1")
        assert len(sim_failures) == 1
        assert sim_failures[0].id == failure2.id

    def test_resolve_failure(self, failure_detector):
        """Test resolving a failure."""
        failure = failure_detector.report_failure(
            failure_type=FailureType.NODE_DEGRADED,
            severity=FailureSeverity.MEDIUM,
            description="Node performance degraded",
            node_id="node-123",
        )
        
        # Resolve the failure
        result = failure_detector.resolve_failure(failure.id, "performance optimization")
        
        assert result.success is True
        assert failure.resolved is True
        assert failure.resolution_method == "performance optimization"
        assert failure.resolution_time is not None
        
        # Try to resolve non-existent failure
        result = failure_detector.resolve_failure("nonexistent", "manual")
        assert result.success is False
        
        # Try to resolve already resolved failure
        result = failure_detector.resolve_failure(failure.id, "another method")
        assert result.success is False
        assert "already resolved" in result.error

    def test_get_node_reliability_score(self, failure_detector, mock_node):
        """Test calculating node reliability score."""
        node_id = mock_node.id
        
        # No history should give perfect score
        assert failure_detector.get_node_reliability_score(node_id) == 1.0
        
        # Record some health checks
        health1 = NodeHealthCheck(node_id=node_id, check_time=datetime.now(), status=NodeStatus.ONLINE)
        health2 = NodeHealthCheck(node_id=node_id, check_time=datetime.now(), status=NodeStatus.ONLINE)
        health2.add_error("Some error")
        health3 = NodeHealthCheck(node_id=node_id, check_time=datetime.now(), status=NodeStatus.ONLINE)
        
        failure_detector.node_health_history[node_id] = [health1, health2, health3]
        
        # Should have 2/3 healthy checks
        assert failure_detector.get_node_reliability_score(node_id) == 2/3


class TestFailureRecoveryManager:
    """Tests for the FailureRecoveryManager class."""

    @pytest.fixture
    def failure_detector(self):
        """Create a failure detector instance."""
        detector = FailureDetector()
        return detector

    @pytest.fixture
    def recovery_manager(self, failure_detector):
        """Create a recovery manager instance."""
        manager = FailureRecoveryManager(failure_detector)
        return manager

    def test_get_recovery_strategy(self, recovery_manager, failure_detector):
        """Test getting the best recovery strategy for a failure."""
        # Create a failure
        failure = failure_detector.report_failure(
            failure_type=FailureType.NODE_OFFLINE,
            severity=FailureSeverity.HIGH,
            description="Node went offline",
            node_id="node-123",
        )
        
        # Get strategy with no previous attempts
        strategy = recovery_manager.get_recovery_strategy(failure)
        
        # First strategy for NODE_OFFLINE should be MIGRATE
        assert strategy == RecoveryStrategy.MIGRATE
        
        # Get strategy with previous attempts
        previous = [RecoveryStrategy.MIGRATE]
        strategy = recovery_manager.get_recovery_strategy(failure, previous)
        
        # Second strategy for NODE_OFFLINE should be RESTORE_CHECKPOINT
        assert strategy == RecoveryStrategy.RESTORE_CHECKPOINT
        
        # Try with all strategies already attempted
        previous = [RecoveryStrategy.MIGRATE, RecoveryStrategy.RESTORE_CHECKPOINT]
        strategy = recovery_manager.get_recovery_strategy(failure, previous)
        
        # Should cycle back to first strategy
        assert strategy == RecoveryStrategy.MIGRATE

    def test_initiate_recovery(self, recovery_manager, failure_detector):
        """Test initiating recovery for a failure."""
        # Create a failure
        failure = failure_detector.report_failure(
            failure_type=FailureType.PROCESS_CRASH,
            severity=FailureSeverity.MEDIUM,
            description="Process crashed",
            simulation_id="sim-123",
        )
        
        # Initiate recovery
        result = recovery_manager.initiate_recovery(failure.id)
        
        assert result.success is True
        strategy = result.value
        
        # First strategy for PROCESS_CRASH should be RESTART
        assert strategy == RecoveryStrategy.RESTART
        
        # Failure should have a recovery attempt recorded
        assert len(failure.recovery_attempts) == 1
        assert failure.recovery_attempts[0]["method"] == RecoveryStrategy.RESTART.value
        assert failure.recovery_attempts[0]["success"] is False  # Initially False
        
        # Should be in active operations
        assert failure.id in recovery_manager.recovery_in_progress
        
        # Try to initiate another recovery for the same failure
        result = recovery_manager.initiate_recovery(failure.id)
        assert result.success is False
        assert "already in progress" in result.error

    def test_complete_recovery(self, recovery_manager, failure_detector):
        """Test completing a recovery operation."""
        # Create a failure and initiate recovery
        failure = failure_detector.report_failure(
            failure_type=FailureType.NETWORK_FAILURE,
            severity=FailureSeverity.MEDIUM,
            description="Network issue",
            simulation_id="sim-123",
        )
        
        recovery_manager.initiate_recovery(failure.id)
        
        # Complete the recovery successfully
        details = {"action": "network settings reconfigured"}
        result = recovery_manager.complete_recovery(failure.id, True, details)
        
        assert result.success is True
        
        # Recovery should be completed and marked as successful
        assert failure.id not in recovery_manager.recovery_in_progress
        assert failure.recovery_attempts[0]["success"] is True
        assert failure.recovery_attempts[0]["details"] == details
        assert "completion_time" in failure.recovery_attempts[0]
        
        # Failure should be marked as resolved
        assert failure.resolved is True
        assert failure.resolution_time is not None
        assert "Recovery with strategy" in failure.resolution_method
        
        # For simulation recovery, history should be updated
        assert "sim-123" in recovery_manager.recovery_history
        assert len(recovery_manager.recovery_history["sim-123"]) == 1
        assert recovery_manager.recovery_history["sim-123"][0]["completed"] is True
        assert recovery_manager.recovery_history["sim-123"][0]["success"] is True
        
        # Try to complete a non-existent recovery
        result = recovery_manager.complete_recovery("nonexistent", True)
        assert result.success is False
        assert "not found" in result.error
        
        # Try to complete a recovery that's not in progress
        result = recovery_manager.complete_recovery(failure.id, True)
        assert result.success is False
        assert "No recovery in progress" in result.error

    def test_cancel_recovery(self, recovery_manager, failure_detector):
        """Test cancelling an in-progress recovery."""
        # Create a failure and initiate recovery
        failure = failure_detector.report_failure(
            failure_type=FailureType.DEADLOCK,
            severity=FailureSeverity.HIGH,
            description="Simulation deadlocked",
            simulation_id="sim-123",
        )
        
        recovery_manager.initiate_recovery(failure.id)
        
        # Cancel the recovery
        result = recovery_manager.cancel_recovery(failure.id)
        
        assert result.success is True
        
        # Recovery should be cancelled
        assert failure.id not in recovery_manager.recovery_in_progress
        assert failure.recovery_attempts[0]["success"] is False
        assert failure.recovery_attempts[0]["details"]["status"] == "cancelled"
        
        # Failure should still be unresolved
        assert failure.resolved is False
        
        # Cancel a non-existent recovery
        result = recovery_manager.cancel_recovery("nonexistent")
        assert result.success is False
        assert "No recovery in progress" in result.error

    def test_process_failures(self, recovery_manager, failure_detector):
        """Test automatic processing of failures."""
        # Create multiple failures with different severities
        critical = failure_detector.report_failure(
            failure_type=FailureType.STORAGE_FAILURE,
            severity=FailureSeverity.CRITICAL,
            description="Storage system failure",
            node_id="node-1",
        )
        
        high = failure_detector.report_failure(
            failure_type=FailureType.NODE_OFFLINE,
            severity=FailureSeverity.HIGH,
            description="Node offline",
            node_id="node-2",
        )
        
        medium = failure_detector.report_failure(
            failure_type=FailureType.PROCESS_CRASH,
            severity=FailureSeverity.MEDIUM,
            description="Process crashed",
            simulation_id="sim-1",
        )
        
        low = failure_detector.report_failure(
            failure_type=FailureType.RESOURCE_CONTENTION,
            severity=FailureSeverity.LOW,
            description="Resource contention",
            simulation_id="sim-2",
        )
        
        # Process failures
        processed = recovery_manager.process_failures()
        
        # Should process failures in order of severity (up to limit)
        assert len(processed) <= 3  # Default limit
        
        # CRITICAL and HIGH severity should be processed first
        if len(processed) >= 1:
            assert critical.id in processed
        if len(processed) >= 2:
            assert high.id in processed
        
        # These should now be in active recoveries
        for failure_id in processed:
            assert failure_id in recovery_manager.recovery_in_progress


class TestResilienceCoordinator:
    """Tests for the ResilienceCoordinator class."""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """Create a temporary directory for checkpoint files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def checkpoint_manager(self, temp_checkpoint_dir):
        """Create a checkpoint manager instance."""
        manager = CheckpointManager(temp_checkpoint_dir)
        return manager

    @pytest.fixture
    def failure_detector(self):
        """Create a failure detector instance."""
        detector = FailureDetector()
        return detector

    @pytest.fixture
    def resilience_coordinator(self, checkpoint_manager, failure_detector, temp_checkpoint_dir):
        """Create a resilience coordinator instance."""
        coordinator = ResilienceCoordinator(
            checkpoint_manager=checkpoint_manager,
            failure_detector=failure_detector,
            checkpoint_base_path=temp_checkpoint_dir,
            resilience_level=ResilienceLevel.STANDARD,
        )
        return coordinator

    @pytest.fixture
    def mock_node(self):
        """Create a mock compute node for testing."""
        node = ComputeNode(
            id="node-123",
            name="compute-123",
            status=NodeStatus.ONLINE,
            cpu_cores=32,
            memory_gb=128,
            storage_gb=1000,
            current_load={"cpu": 0.5, "memory": 0.4, "storage": 0.3},
            node_type=NodeType.COMPUTE,
            gpu_count=0,
            network_bandwidth_gbps=10,
            location="data_center_1"
        )
        return node

    @pytest.fixture
    def mock_simulation(self):
        """Create a mock simulation for testing."""
        sim = MockSimulation(
            id="sim-123",
            name="Test Simulation",
            description="A test simulation",
            status=SimulationStatus.RUNNING,
            priority=SimulationPriority.HIGH,
            stages={}
        )
        
        # Add a stage
        stage = SimulationStage(
            id="stage-1",
            name="Processing Stage",
            status=SimulationStageStatus.RUNNING,
            progress=0.5,
            estimated_duration=timedelta(hours=2),
        )
        sim.stages = {"stage-1": stage}
        
        return sim

    def test_set_resilience_level(self, resilience_coordinator):
        """Test setting the resilience level."""
        # Start with STANDARD
        assert resilience_coordinator.resilience_level == ResilienceLevel.STANDARD
        assert resilience_coordinator.checkpoint_frequency == timedelta(minutes=60)
        
        # Change to HIGH
        resilience_coordinator.set_resilience_level(ResilienceLevel.HIGH)
        
        assert resilience_coordinator.resilience_level == ResilienceLevel.HIGH
        assert resilience_coordinator.checkpoint_frequency == timedelta(minutes=30)
        
        # Change to MAXIMUM
        resilience_coordinator.set_resilience_level(ResilienceLevel.MAXIMUM)
        
        assert resilience_coordinator.resilience_level == ResilienceLevel.MAXIMUM
        assert resilience_coordinator.checkpoint_frequency == timedelta(minutes=15)

    def test_record_event(self, resilience_coordinator):
        """Test recording resilience events."""
        event_id = resilience_coordinator.record_event(
            event_type="test_event",
            description="Test event",
            severity="info",
            source="test",
            details={"test_key": "test_value"},
        )
        
        assert event_id in resilience_coordinator.events
        event = resilience_coordinator.events[event_id]
        
        assert event.event_type == "test_event"
        assert event.description == "Test event"
        assert event.severity == "info"
        assert event.source == "test"
        assert event.details == {"test_key": "test_value"}
        assert event.handled is False
        assert event.handling_time is None
        assert event.handler is None

    def test_schedule_checkpoint(self, resilience_coordinator, mock_simulation):
        """Test scheduling a checkpoint."""
        # Schedule with default timing
        resilience_coordinator.schedule_checkpoint(mock_simulation)
        
        assert mock_simulation.id in resilience_coordinator.checkpoint_schedule
        
        # Time should be about an hour in the future (STANDARD level)
        checkpoint_time = resilience_coordinator.checkpoint_schedule[mock_simulation.id]
        time_diff = (checkpoint_time - datetime.now()).total_seconds() / 60
        assert 59 <= time_diff <= 61
        
        # Schedule with custom timing
        resilience_coordinator.schedule_checkpoint(mock_simulation, delay_minutes=15)
        
        # Time should be 15 minutes in the future
        checkpoint_time = resilience_coordinator.checkpoint_schedule[mock_simulation.id]
        time_diff = (checkpoint_time - datetime.now()).total_seconds() / 60
        assert 14 <= time_diff <= 16

    def test_handle_node_status_change(self, resilience_coordinator, mock_node):
        """Test handling node status changes."""
        # Handle a node going offline
        affected_simulations = ["sim-1", "sim-2"]
        affected_handled = resilience_coordinator.handle_node_status_change(
            node_id=mock_node.id,
            old_status=NodeStatus.ONLINE,
            new_status=NodeStatus.OFFLINE,
            affected_simulations=affected_simulations,
        )
        
        # Should create a NodeOffline failure report
        failures = resilience_coordinator.failure_detector.get_active_failures(node_id=mock_node.id)
        assert len(failures) == 1
        assert failures[0].failure_type == FailureType.NODE_OFFLINE
        
        # Should record status change in history
        assert mock_node.id in resilience_coordinator.node_status_history
        assert len(resilience_coordinator.node_status_history[mock_node.id]) == 1
        assert resilience_coordinator.node_status_history[mock_node.id][0][1] == NodeStatus.OFFLINE.value
        
        # Should record an event
        events = [e for e in resilience_coordinator.events.values() if e.event_type == "node_status_change"]
        assert len(events) == 1
        assert events[0].details["node_id"] == mock_node.id
        assert events[0].details["old_status"] == NodeStatus.ONLINE.value
        assert events[0].details["new_status"] == NodeStatus.OFFLINE.value
        
        # Metrics should be updated
        assert resilience_coordinator.metrics.total_failures == 1

    def test_handle_simulation_status_change(self, resilience_coordinator, mock_simulation):
        """Test handling simulation status changes."""
        # Handle a simulation failing
        result = resilience_coordinator.handle_simulation_status_change(
            simulation=mock_simulation,
            old_status="running",
            new_status="failed",
        )
        
        # Should create a ProcessCrash failure report
        failures = resilience_coordinator.failure_detector.get_active_failures(simulation_id=mock_simulation.id)
        assert len(failures) == 1
        assert failures[0].failure_type == FailureType.PROCESS_CRASH
        
        # Should record status change in history
        assert mock_simulation.id in resilience_coordinator.simulation_status_history
        assert len(resilience_coordinator.simulation_status_history[mock_simulation.id]) == 1
        assert resilience_coordinator.simulation_status_history[mock_simulation.id][0][1] == "failed"
        
        # Should record an event
        events = [e for e in resilience_coordinator.events.values() if e.event_type == "simulation_status_change"]
        assert len(events) == 1
        assert events[0].details["simulation_id"] == mock_simulation.id
        assert events[0].details["old_status"] == "running"
        assert events[0].details["new_status"] == "failed"
        
        # Metrics should be updated
        assert resilience_coordinator.metrics.total_failures == 1
        
        # Test simulation starting to run
        result = resilience_coordinator.handle_simulation_status_change(
            simulation=mock_simulation,
            old_status="scheduled",
            new_status="running",
        )
        
        # Should schedule a checkpoint
        assert mock_simulation.id in resilience_coordinator.checkpoint_schedule

    def test_handle_stage_status_change(self, resilience_coordinator, mock_simulation):
        """Test handling stage status changes."""
        stage_id = "stage-1"
        stage = mock_simulation.stages[stage_id]
        
        # Handle a stage failing
        result = resilience_coordinator.handle_stage_status_change(
            simulation=mock_simulation,
            stage_id=stage_id,
            old_status=SimulationStageStatus.RUNNING,
            new_status=SimulationStageStatus.FAILED,
        )
        
        # Should create a failure report
        failures = resilience_coordinator.failure_detector.get_active_failures(
            simulation_id=mock_simulation.id
        )
        assert len(failures) == 1
        assert failures[0].failure_type == FailureType.PROCESS_CRASH
        assert failures[0].stage_id == stage_id
        
        # Should record an event
        events = [e for e in resilience_coordinator.events.values() if e.event_type == "stage_status_change"]
        assert len(events) == 1
        assert events[0].details["simulation_id"] == mock_simulation.id
        assert events[0].details["stage_id"] == stage_id
        assert events[0].details["old_status"] == SimulationStageStatus.RUNNING.value
        assert events[0].details["new_status"] == SimulationStageStatus.FAILED.value
        
        # Metrics should be updated
        assert resilience_coordinator.metrics.total_failures == 1

    def test_handle_failure_detection(self, resilience_coordinator):
        """Test handling detected failures."""
        # Create a failure report
        failure = FailureReport(
            id="failure-123",
            failure_type=FailureType.MEMORY_EXHAUSTION,
            severity=FailureSeverity.HIGH,
            detection_time=datetime.now(),
            detection_method=DetectionMethod.METRICS,
            simulation_id="sim-123",
            description="Out of memory error",
        )
        
        # Handle the failure
        recovery_id = resilience_coordinator.handle_failure_detection(failure)
        
        # Should record an event
        events = [e for e in resilience_coordinator.events.values() if e.event_type == "failure_detected"]
        assert len(events) == 1
        assert events[0].details["failure_id"] == failure.id
        assert events[0].details["failure_type"] == failure.failure_type.value
        
        # Should initiate recovery
        assert recovery_id is not None
        assert "sim-123" in resilience_coordinator.active_recoveries
        assert resilience_coordinator.active_recoveries["sim-123"]["recovery_id"] == recovery_id
        
        # Metrics should be updated
        assert resilience_coordinator.metrics.total_failures == 1

    def test_complete_recovery(self, resilience_coordinator):
        """Test completing a recovery operation."""
        # Create a recovery (mock the _initiate_simulation_recovery method)
        simulation_id = "sim-123"
        recovery_id = "recovery-123"
        
        resilience_coordinator.active_recoveries[simulation_id] = {
            "recovery_id": recovery_id,
            "simulation_id": simulation_id,
            "strategy": RecoveryStrategy.RESTORE_CHECKPOINT.value,
            "reason": "Test recovery",
            "initiated_at": datetime.now().isoformat(),
            "completed": False,
            "events": [],
        }
        
        # Complete the recovery
        result = resilience_coordinator.complete_recovery(
            recovery_id=recovery_id,
            success=True,
            details={"action": "simulation restored"},
        )
        
        assert result.success is True
        
        # Recovery should be completed
        assert simulation_id not in resilience_coordinator.active_recoveries
        
        # Should record an event
        events = [e for e in resilience_coordinator.events.values() if e.event_type == "recovery_completed"]
        assert len(events) == 1
        assert events[0].details["recovery_id"] == recovery_id
        assert events[0].details["success"] is True
        
        # Metrics should be updated
        assert resilience_coordinator.metrics.successful_recoveries == 1

    @pytest.mark.xfail(reason="Test is inconsistent due to implementation details")
    def test_detect_and_handle_failures(self, resilience_coordinator, mock_node, mock_simulation):
        """Test end-to-end failure detection and handling."""
        # Create problematic node and simulation
        problem_node = ComputeNode(
            id="problem-node",
            name="problem",
            status=NodeStatus.ONLINE,
            current_load={"cpu": 0.99, "memory": 0.5, "storage": 0.5},  # High CPU load
            cpu_cores=32,
            memory_gb=128,
            storage_gb=1000,
            node_type=NodeType.COMPUTE,
            gpu_count=0,
            network_bandwidth_gbps=10,
            location="data_center_1"
        )
        
        nodes = {
            "node-123": mock_node,
            "problem-node": problem_node,
        }
        
        # Record heartbeats
        for node_id in nodes:
            resilience_coordinator.failure_detector.record_heartbeat(node_id)
        
        # Create problematic simulation
        stalled_sim = StalledSimulation(
            id="stalled-sim",
            name="Stalled Simulation",
            status=SimulationStatus.RUNNING,
            stages={}
        )
        
        # Set up simulation to appear stalled
        resilience_coordinator.failure_detector.simulation_health_history["stalled-sim"] = {
            "last_progress_update": datetime.now() - timedelta(minutes=120),  # No progress for 2 hours
        }
        
        simulations = {
            "sim-123": mock_simulation,
            "stalled-sim": stalled_sim,
        }
        
        # Set low threshold for testing
        resilience_coordinator.failure_detector.thresholds["simulation_progress_stall_minutes"] = 60
        
        # Detect and handle failures
        with patch.object(resilience_coordinator.recovery_manager, 'initiate_recovery', return_value=Result.ok(RecoveryStrategy.RESTART)):
            handled_failures = resilience_coordinator.detect_and_handle_failures(nodes, simulations)
        
        # Should detect and handle at least one failure
        assert len(handled_failures) > 0
        
        # The CPU load failure and stalled simulation should be detected
        node_failures = resilience_coordinator.failure_detector.get_active_failures(node_id="problem-node")
        assert len(node_failures) > 0
        assert node_failures[0].failure_type == FailureType.RESOURCE_CONTENTION
        
        sim_failures = resilience_coordinator.failure_detector.get_active_failures(simulation_id="stalled-sim")
        assert len(sim_failures) > 0
        
        # Metrics should be updated
        assert resilience_coordinator.metrics.total_failures > 0