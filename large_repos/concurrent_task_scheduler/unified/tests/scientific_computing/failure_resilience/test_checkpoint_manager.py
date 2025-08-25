"""Tests for the checkpoint management module."""

import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from concurrent_task_scheduler.failure_resilience.checkpoint_manager import (
    CheckpointManager,
    CheckpointCoordinator,
    ValidationResult,
    CheckpointCreationStrategy,
)
from concurrent_task_scheduler.models import (
    Checkpoint,
    CheckpointCompression,
    CheckpointPolicy,
    SimulationStatus,
    CheckpointStatus,
    CheckpointStorageType,
    CheckpointType,
    Simulation,
    SimulationStage,
    SimulationPriority,
    SimulationStageStatus,
)


@pytest.fixture
def checkpoint_base_path():
    """Provide a temporary directory for checkpoint testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def checkpoint_manager(checkpoint_base_path):
    """Create a checkpoint manager for testing."""
    manager = CheckpointManager(base_storage_path=checkpoint_base_path, max_concurrent_operations=2)
    yield manager
    manager.cleanup()


@pytest.fixture
def checkpoint_coordinator(checkpoint_manager):
    """Create a checkpoint coordinator for testing."""
    return CheckpointCoordinator(checkpoint_manager=checkpoint_manager)


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


def test_checkpoint_manager_init(checkpoint_manager, checkpoint_base_path):
    """Test the initialization of the checkpoint manager."""
    assert checkpoint_manager.base_storage_path == checkpoint_base_path
    assert checkpoint_manager.max_concurrent_operations == 2
    assert isinstance(checkpoint_manager.policies, dict)
    assert len(checkpoint_manager.policies) == 0
    assert isinstance(checkpoint_manager.checkpoints, dict)
    assert len(checkpoint_manager.checkpoints) == 0


def test_register_policy(checkpoint_manager):
    """Test registering a checkpoint policy."""
    policy = CheckpointPolicy(
        name="Test Policy",
        description="Policy for testing",
        checkpoint_type=CheckpointType.FULL,
        storage_type=CheckpointStorageType.PARALLEL_FS,
        compression=CheckpointCompression.ZSTD,
        frequency_minutes=30,
        min_progress_delta=0.1,
    )
    
    policy_id = checkpoint_manager.register_policy(policy)
    assert policy_id == "test_policy"
    assert policy_id in checkpoint_manager.policies
    assert checkpoint_manager.policies[policy_id] == policy


def test_get_default_policy(checkpoint_manager):
    """Test getting (and creating if needed) the default policy."""
    # Should create a default policy if none exists
    default_policy = checkpoint_manager.get_default_policy()
    
    assert default_policy is not None
    assert default_policy.name == "Default"
    assert default_policy.checkpoint_type == CheckpointType.FULL
    assert "default" in checkpoint_manager.policies
    
    # Should return the same policy on subsequent calls
    default_policy2 = checkpoint_manager.get_default_policy()
    assert default_policy == default_policy2


def test_create_manager_for_simulation(checkpoint_manager, sample_simulation):
    """Test creating a checkpoint manager for a simulation."""
    result = checkpoint_manager.create_manager_for_simulation(sample_simulation.id)
    
    assert result.success
    manager = result.value
    
    assert manager.simulation_id == sample_simulation.id
    assert manager.checkpoint_policy is not None
    assert sample_simulation.id in checkpoint_manager.simulation_managers
    assert sample_simulation.id in checkpoint_manager.checkpoints
    
    # Test creating a manager with a specific policy
    custom_policy = CheckpointPolicy(
        name="Custom Policy",
        description="Custom policy for testing",
        checkpoint_type=CheckpointType.INCREMENTAL,
        storage_type=CheckpointStorageType.LOCAL,
        compression=CheckpointCompression.NONE,
        frequency_minutes=15,
        min_progress_delta=0.05,
    )
    
    policy_id = checkpoint_manager.register_policy(custom_policy)
    
    result2 = checkpoint_manager.create_manager_for_simulation("sim_another", policy_id)
    assert result2.success
    manager2 = result2.value
    
    assert manager2.simulation_id == "sim_another"
    assert manager2.checkpoint_policy.name == "Custom Policy"
    assert manager2.checkpoint_policy.checkpoint_type == CheckpointType.INCREMENTAL


def test_update_policy(checkpoint_manager, sample_simulation):
    """Test updating the checkpoint policy for a simulation."""
    # Create manager first
    checkpoint_manager.create_manager_for_simulation(sample_simulation.id)
    
    # Register a new policy
    new_policy = CheckpointPolicy(
        name="New Policy",
        description="New policy for testing",
        checkpoint_type=CheckpointType.METADATA_ONLY,
        storage_type=CheckpointStorageType.OBJECT_STORE,
        compression=CheckpointCompression.GZIP,
        frequency_minutes=20,
        min_progress_delta=0.2,
    )
    
    policy_id = checkpoint_manager.register_policy(new_policy)
    
    # Update policy
    result = checkpoint_manager.update_policy(sample_simulation.id, policy_id)
    
    assert result.success
    assert checkpoint_manager.simulation_managers[sample_simulation.id].checkpoint_policy == new_policy
    
    # Test with non-existent simulation
    result = checkpoint_manager.update_policy("sim_nonexistent", policy_id)
    assert not result.success
    assert "No checkpoint manager found" in result.error
    
    # Test with non-existent policy
    result = checkpoint_manager.update_policy(sample_simulation.id, "nonexistent_policy")
    assert not result.success
    assert "Policy nonexistent_policy not found" in result.error


def test_should_create_checkpoint(checkpoint_manager, sample_simulation):
    """Test determining if a checkpoint should be created."""
    # Should create manager if it doesn't exist
    result = checkpoint_manager.should_create_checkpoint(sample_simulation)
    
    # Result depends on the policy, for default policy it checks time since last checkpoint
    assert isinstance(result, bool)
    
    # Register a progress-based policy and update
    progress_policy = CheckpointPolicy(
        name="Progress Policy",
        description="Progress-based policy",
        checkpoint_type=CheckpointType.FULL,
        storage_type=CheckpointStorageType.PARALLEL_FS,
        compression=CheckpointCompression.ZSTD,
        frequency_minutes=120,  # Long time - shouldn't trigger
        min_progress_delta=0.01,  # Small delta - should trigger easily
    )
    
    policy_id = checkpoint_manager.register_policy(progress_policy)
    checkpoint_manager.update_policy(sample_simulation.id, policy_id)
    
    # Should now base on progress
    result = checkpoint_manager.should_create_checkpoint(sample_simulation)
    assert isinstance(result, bool)


def test_create_checkpoint(checkpoint_manager, sample_simulation):
    """Test creating a checkpoint for a simulation."""
    # Create checkpoint
    result = checkpoint_manager.create_checkpoint(sample_simulation)
    
    assert result.success
    checkpoint = result.value
    
    assert checkpoint.status == CheckpointStatus.COMPLETE
    assert checkpoint.metadata.simulation_id == sample_simulation.id
    assert checkpoint.metadata.simulation_name == sample_simulation.name
    assert checkpoint.metadata.stage_id is None  # Whole simulation checkpoint
    assert checkpoint.validation_hash is not None
    
    # Check if files were created
    assert os.path.exists(checkpoint.path)
    assert os.path.exists(os.path.join(checkpoint.path, "metadata.json"))
    assert os.path.exists(os.path.join(checkpoint.path, "simulation.json"))
    assert os.path.exists(os.path.join(checkpoint.path, "data.bin"))
    
    # Check if checkpoint is tracked
    assert sample_simulation.id in checkpoint_manager.checkpoints
    assert checkpoint.id in checkpoint_manager.checkpoints[sample_simulation.id]
    
    # Create stage-specific checkpoint
    stage_id = "stage_main"
    result = checkpoint_manager.create_checkpoint(sample_simulation, stage_id=stage_id)
    
    assert result.success
    checkpoint = result.value
    
    assert checkpoint.status == CheckpointStatus.COMPLETE
    assert checkpoint.metadata.simulation_id == sample_simulation.id
    assert checkpoint.metadata.stage_id == stage_id
    assert checkpoint.metadata.stage_name == sample_simulation.stages[stage_id].name
    
    # Check if stage file was created
    assert os.path.exists(os.path.join(checkpoint.path, f"stage_{stage_id}.json"))


@pytest.mark.xfail(reason="Checkpoint validation not fully implemented yet")
def test_validate_checkpoint(checkpoint_manager, sample_simulation):
    """Test validating a checkpoint."""
    # Create checkpoint first
    result = checkpoint_manager.create_checkpoint(sample_simulation)
    assert result.success
    checkpoint = result.value
    
    # Validate checkpoint
    validation_result = checkpoint_manager.validate_checkpoint(checkpoint.id, sample_simulation.id)
    assert validation_result == ValidationResult.VALID
    
    # Test validation caching
    # This call should use the cached result
    validation_result = checkpoint_manager.validate_checkpoint(checkpoint.id, sample_simulation.id)
    assert validation_result == ValidationResult.VALID
    
    # Test with non-existent checkpoint
    validation_result = checkpoint_manager.validate_checkpoint("nonexistent", sample_simulation.id)
    assert validation_result == ValidationResult.MISSING
    
    # Test with incomplete checkpoint
    # Create a checkpoint, then delete one of the required files
    result = checkpoint_manager.create_checkpoint(sample_simulation, description="Incomplete test")
    assert result.success
    checkpoint2 = result.value
    
    # Delete the data file
    os.remove(os.path.join(checkpoint2.path, "data.bin"))
    
    validation_result = checkpoint_manager.validate_checkpoint(checkpoint2.id, sample_simulation.id)
    assert validation_result == ValidationResult.INCOMPLETE
    
    # Test with corrupted checkpoint
    # Create a checkpoint, then modify the validation hash
    result = checkpoint_manager.create_checkpoint(sample_simulation, description="Corrupted test")
    assert result.success
    checkpoint3 = result.value
    
    original_hash = checkpoint3.validation_hash
    checkpoint3.validation_hash = "corrupted_hash"
    
    validation_result = checkpoint_manager.validate_checkpoint(checkpoint3.id, sample_simulation.id)
    assert validation_result == ValidationResult.CORRUPTED


def test_get_latest_checkpoint(checkpoint_manager, sample_simulation):
    """Test getting the latest checkpoint for a simulation."""
    # Create checkpoint first
    result1 = checkpoint_manager.create_checkpoint(sample_simulation)
    assert result1.success
    checkpoint1 = result1.value
    
    # Create a second checkpoint
    result2 = checkpoint_manager.create_checkpoint(sample_simulation)
    assert result2.success
    checkpoint2 = result2.value
    
    # Get latest
    latest = checkpoint_manager.get_latest_checkpoint(sample_simulation.id)
    assert latest.id == checkpoint2.id
    
    # Create stage-specific checkpoints
    stage_id = "stage_main"
    result3 = checkpoint_manager.create_checkpoint(sample_simulation, stage_id=stage_id)
    assert result3.success
    
    # Get latest for stage
    latest_stage = checkpoint_manager.get_latest_checkpoint(sample_simulation.id, stage_id=stage_id)
    assert latest_stage.id == result3.value.id
    
    # Still returns latest overall checkpoint
    latest = checkpoint_manager.get_latest_checkpoint(sample_simulation.id)
    assert latest.id == result3.value.id


def test_get_all_checkpoints(checkpoint_manager, sample_simulation):
    """Test getting all checkpoints for a simulation."""
    # Create multiple checkpoints
    result1 = checkpoint_manager.create_checkpoint(sample_simulation)
    assert result1.success
    
    result2 = checkpoint_manager.create_checkpoint(sample_simulation)
    assert result2.success
    
    stage_id = "stage_main"
    result3 = checkpoint_manager.create_checkpoint(sample_simulation, stage_id=stage_id)
    assert result3.success
    
    # Get all checkpoints
    all_checkpoints = checkpoint_manager.get_all_checkpoints(sample_simulation.id)
    assert len(all_checkpoints) == 3
    
    # Get stage-specific checkpoints
    stage_checkpoints = checkpoint_manager.get_all_checkpoints(sample_simulation.id, stage_id=stage_id)
    assert len(stage_checkpoints) == 1
    assert stage_checkpoints[0].id == result3.value.id


@pytest.mark.xfail(reason="Checkpoint validation and restoration not fully implemented yet")
def test_restore_from_checkpoint(checkpoint_manager, sample_simulation):
    """Test restoring a simulation from a checkpoint."""
    # Create checkpoint first
    result = checkpoint_manager.create_checkpoint(sample_simulation)
    assert result.success
    checkpoint = result.value
    
    # Restore
    restore_result = checkpoint_manager.restore_from_checkpoint(checkpoint.id, sample_simulation.id)
    assert restore_result.success
    
    # Verify restore count was incremented
    checkpoint = checkpoint_manager.checkpoints[sample_simulation.id][checkpoint.id]
    assert checkpoint.restore_count == 1
    assert checkpoint.last_restore_time is not None
    
    # Test with non-existent checkpoint
    restore_result = checkpoint_manager.restore_from_checkpoint("nonexistent", sample_simulation.id)
    assert not restore_result.success
    
    # Test with invalid checkpoint
    # Create a checkpoint, then delete one of the required files
    result = checkpoint_manager.create_checkpoint(sample_simulation)
    assert result.success
    checkpoint2 = result.value
    
    # Delete the data file
    os.remove(os.path.join(checkpoint2.path, "data.bin"))
    
    restore_result = checkpoint_manager.restore_from_checkpoint(checkpoint2.id, sample_simulation.id)
    assert not restore_result.success
    assert "Cannot restore from invalid checkpoint" in restore_result.error


def test_checkpoint_coordinator(checkpoint_coordinator, checkpoint_manager, sample_simulation):
    """Test the checkpoint coordinator functionality."""
    # Schedule a checkpoint
    checkpoint_coordinator.schedule_checkpoint(sample_simulation.id)
    
    # Check if scheduled
    assert sample_simulation.id in checkpoint_coordinator.scheduled_checkpoints
    
    # Create a dictionary of simulations
    simulations = {sample_simulation.id: sample_simulation}
    
    # Process scheduled checkpoints
    created = checkpoint_coordinator.process_scheduled_checkpoints(simulations)
    
    # If simulation was due for checkpoint, it should be in the created list
    if sample_simulation.id in created:
        assert sample_simulation.id not in checkpoint_coordinator.scheduled_checkpoints
    
    # Schedule with specific time
    future_time = datetime.now() + timedelta(minutes=10)
    checkpoint_coordinator.schedule_checkpoint(sample_simulation.id, future_time)
    
    # Should not be processed yet
    created = checkpoint_coordinator.process_scheduled_checkpoints(simulations)
    assert len(created) == 0
    assert sample_simulation.id in checkpoint_coordinator.scheduled_checkpoints
    
    # Test checkpoint prioritization
    checkpoint_coordinator.last_checkpoint_time[sample_simulation.id] = datetime.now() - timedelta(hours=23)
    
    # Should prioritize based on time since last checkpoint
    should_checkpoint = checkpoint_coordinator.should_checkpoint_simulation(sample_simulation)
    assert isinstance(should_checkpoint, bool)