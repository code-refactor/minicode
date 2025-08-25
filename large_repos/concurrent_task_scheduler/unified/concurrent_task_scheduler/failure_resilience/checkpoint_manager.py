"""Checkpoint management for simulation state preservation."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from concurrent_task_scheduler.models import (
    Checkpoint,
    CheckpointCompression,
    CheckpointManager as CheckpointManagerModel,
    CheckpointMetadata,
    CheckpointPolicy,
    CheckpointStatus,
    CheckpointStorageType,
    CheckpointType,
    Result,
    Simulation,
    SimulationStage,
    SimulationStageStatus,
)
from concurrent_task_scheduler.models.utils import DateTimeEncoder, generate_id

logger = logging.getLogger(__name__)


class ValidationResult(str, Enum):
    """Result of checkpoint validation."""
    
    VALID = "valid"
    CORRUPTED = "corrupted"
    INCOMPLETE = "incomplete"
    MISSING = "missing"


class CheckpointCreationStrategy(str, Enum):
    """Strategies for creating checkpoints."""
    
    PERIODIC = "periodic"  # Regular intervals
    PROGRESS_BASED = "progress_based"  # Based on progress
    EVENT_BASED = "event_based"  # Based on events (e.g., stage completion)
    HYBRID = "hybrid"  # Combination of strategies


class CheckpointManager:
    """Manager for checkpoint creation, validation, and restoration."""
    
    def __init__(
        self,
        base_storage_path: str = None,
        max_concurrent_operations: int = 4,
        checkpoint_base_path: str = None,
    ):
        # For backward compatibility
        self.base_storage_path = base_storage_path or checkpoint_base_path or "/tmp/checkpoints"
        self.max_concurrent_operations = max_concurrent_operations
        self.policies: Dict[str, CheckpointPolicy] = {}
        self.checkpoints: Dict[str, Dict[str, Checkpoint]] = {}  # sim_id -> checkpoint_id -> Checkpoint
        self.simulation_managers: Dict[str, CheckpointManagerModel] = {}
        self.active_operations: Dict[str, datetime] = {}  # operation_id -> start_time
        # ValidationResult is defined in this file, so it's accessible here
        self.validation_cache: Dict[str, Tuple[ValidationResult, datetime]] = {}  # checkpoint_id -> (result, time)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_operations)
        
        # Store checkpoint policies for simulations
        self.checkpoint_policies: Dict[str, CheckpointPolicy] = {}
        
        # Ensure storage path exists
        os.makedirs(self.base_storage_path, exist_ok=True)
    
    def register_policy(self, policy: CheckpointPolicy) -> str:
        """Register a checkpoint policy."""
        policy_id = policy.name.lower().replace(" ", "_")
        self.policies[policy_id] = policy
        return policy_id
    
    def get_default_policy(self) -> CheckpointPolicy:
        """Get or create a default checkpoint policy."""
        if "default" not in self.policies:
            default_policy = CheckpointPolicy(
                name="Default",
                description="Default checkpoint policy",
                checkpoint_type=CheckpointType.FULL,
                storage_type=CheckpointStorageType.PARALLEL_FS,
                compression=CheckpointCompression.ZSTD,
                frequency_minutes=60,
                min_progress_delta=0.05,
            )
            self.register_policy(default_policy)
        
        return self.policies["default"]
    
    def set_checkpoint_policy(
        self,
        simulation_id: str,
        policy: CheckpointPolicy,
    ) -> Result[bool]:
        """Set the checkpoint policy for a simulation."""
        self.checkpoint_policies[simulation_id] = policy
        return Result.ok(True)
    
    def get_checkpoint_policy(self, simulation_id: str) -> CheckpointPolicy:
        """Get the checkpoint policy for a simulation."""
        # Return the policy if it exists, otherwise a default policy
        return self.checkpoint_policies.get(
            simulation_id,
            CheckpointPolicy(
                name="Default",
                description="Default checkpoint policy",
                checkpoint_type=CheckpointType.FULL,
                storage_type=CheckpointStorageType.PARALLEL_FS,
                compression=CheckpointCompression.ZSTD,
                frequency_minutes=60,  # Default to hourly checkpoints
                min_progress_delta=0.05,    # Default to 5% progress
                interval_minutes=60,         # For backward compatibility
                max_checkpoints=5,           # For backward compatibility
                priority="medium"            # For backward compatibility
            )
        )
    
    def create_manager_for_simulation(
        self,
        simulation_id: str,
        policy_id: Optional[str] = None,
    ) -> Result[CheckpointManagerModel]:
        """Create a checkpoint manager for a simulation."""
        if simulation_id in self.simulation_managers:
            return Result.err(f"Checkpoint manager already exists for simulation {simulation_id}")
        
        # Get policy
        if policy_id and policy_id in self.policies:
            policy = self.policies[policy_id]
        else:
            policy = self.get_default_policy()
        
        # Create storage directory
        simulation_storage_path = os.path.join(self.base_storage_path, simulation_id)
        os.makedirs(simulation_storage_path, exist_ok=True)
        
        # Create manager
        manager = CheckpointManagerModel(
            simulation_id=simulation_id,
            checkpoint_policy=policy,
            base_storage_path=simulation_storage_path,
        )
        
        self.simulation_managers[simulation_id] = manager
        self.checkpoints[simulation_id] = {}
        
        return Result.ok(manager)
    
    def update_policy(
        self,
        simulation_id: str,
        policy_id: str,
    ) -> Result[bool]:
        """Update the checkpoint policy for a simulation."""
        if simulation_id not in self.simulation_managers:
            return Result.err(f"No checkpoint manager found for simulation {simulation_id}")
        
        if policy_id not in self.policies:
            return Result.err(f"Policy {policy_id} not found")
        
        # Update policy
        manager = self.simulation_managers[simulation_id]
        manager.checkpoint_policy = self.policies[policy_id]
        
        return Result.ok(True)
    
    def should_create_checkpoint(
        self,
        simulation: Simulation,
        stage_id: Optional[str] = None,
    ) -> bool:
        """Determine if a checkpoint should be created."""
        if simulation.id not in self.simulation_managers:
            # Create manager if it doesn't exist
            result = self.create_manager_for_simulation(simulation.id)
            if not result.success:
                logger.error(f"Failed to create checkpoint manager: {result.error}")
                return False
        
        manager = self.simulation_managers[simulation.id]
        
        # Get progress
        current_progress = simulation.total_progress()
        
        # Check if checkpoint should be created
        return manager.should_create_checkpoint(datetime.now(), current_progress)
    
    def register_checkpoint(self, checkpoint: Checkpoint) -> Result[bool]:
        """Register an existing checkpoint."""
        if checkpoint.metadata.simulation_id not in self.checkpoints:
            self.checkpoints[checkpoint.metadata.simulation_id] = {}
            
        # Store the checkpoint
        self.checkpoints[checkpoint.metadata.simulation_id][checkpoint.id] = checkpoint
        
        # Update simulation manager
        if checkpoint.metadata.simulation_id not in self.simulation_managers:
            # Create a new manager if needed
            simulation_storage_path = os.path.join(self.base_storage_path, checkpoint.metadata.simulation_id)
            os.makedirs(simulation_storage_path, exist_ok=True)
            
            manager = CheckpointManagerModel(
                simulation_id=checkpoint.metadata.simulation_id,
                checkpoint_policy=self.get_default_policy(),
                base_storage_path=simulation_storage_path,
            )
            
            self.simulation_managers[checkpoint.metadata.simulation_id] = manager
            self.checkpoints[checkpoint.metadata.simulation_id] = {}
            
        # Add to manager
        manager = self.simulation_managers[checkpoint.metadata.simulation_id]
        if checkpoint not in manager.checkpoints:
            manager.checkpoints.append(checkpoint)
        
        # Update latest checkpoint ID if this is newer
        if (manager.latest_checkpoint_id is None or
            (checkpoint.metadata.checkpoint_time > 
             self.checkpoints[checkpoint.metadata.simulation_id][manager.latest_checkpoint_id].metadata.checkpoint_time)):
            manager.latest_checkpoint_id = checkpoint.id
            
        return Result.ok(True)
            
    def create_checkpoint(
        self,
        simulation: Simulation,
        stage_id: Optional[str] = None,
        checkpoint_type: Optional[CheckpointType] = None,
        description: Optional[str] = None,
    ) -> Result[Checkpoint]:
        """Create a checkpoint for a simulation or stage."""
        if simulation.id not in self.simulation_managers:
            # Create manager if it doesn't exist
            result = self.create_manager_for_simulation(simulation.id)
            if not result.success:
                return Result.err(f"Failed to create checkpoint manager: {result.error}")
        
        manager = self.simulation_managers[simulation.id]
        
        # Use specified type or default from policy
        cp_type = checkpoint_type or manager.checkpoint_policy.checkpoint_type
        
        # Generate checkpoint path
        checkpoint_path = manager.generate_checkpoint_path(stage_id)
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        
        # Create metadata
        progress = simulation.total_progress()
        if stage_id and stage_id in simulation.stages:
            stage = simulation.stages[stage_id]
            stage_name = stage.name
            progress = stage.progress
        else:
            stage_name = None
        
        metadata = CheckpointMetadata(
            simulation_id=simulation.id,
            simulation_name=simulation.name,
            stage_id=stage_id,
            stage_name=stage_name,
            checkpoint_type=cp_type,
            storage_type=manager.checkpoint_policy.storage_type,
            compression=manager.checkpoint_policy.compression,
            progress_at_checkpoint=progress,
        )
        
        # Create checkpoint
        checkpoint_id = f"cp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        checkpoint = Checkpoint(
            id=checkpoint_id,
            metadata=metadata,
            status=CheckpointStatus.CREATING,
            path=checkpoint_path,
        )
        
        # Track checkpoint
        self.checkpoints.setdefault(simulation.id, {})[checkpoint_id] = checkpoint
        manager.checkpoints.append(checkpoint)
        manager.latest_checkpoint_id = checkpoint_id
        
        # Start checkpoint creation process
        operation_id = generate_id("cp_op")
        self.active_operations[operation_id] = datetime.now()
        
        # In a real implementation, this would actually save the simulation state
        # Here we'll just simulate the process with a delay and creating empty files
        try:
            self._create_checkpoint_files(checkpoint, simulation, stage_id)
            
            # Update checkpoint status
            checkpoint.status = CheckpointStatus.COMPLETE
            
            # Update metadata
            metadata.size_bytes = self._get_checkpoint_size(checkpoint)
            metadata.creation_duration_seconds = (datetime.now() - self.active_operations[operation_id]).total_seconds()
            
            # Generate validation hash
            checkpoint.validation_hash = self._calculate_validation_hash(checkpoint)
            
            # Remove from active operations
            del self.active_operations[operation_id]
            
            # Apply retention policy
            self._apply_retention_policy(simulation.id)
            
            return Result.ok(checkpoint)
        
        except Exception as e:
            # Update checkpoint status
            checkpoint.status = CheckpointStatus.FAILED
            
            # Remove from active operations
            if operation_id in self.active_operations:
                del self.active_operations[operation_id]
            
            logger.error(f"Failed to create checkpoint: {e}")
            return Result.err(f"Failed to create checkpoint: {e}")
    
    def _create_checkpoint_files(
        self,
        checkpoint: Checkpoint,
        simulation: Simulation,
        stage_id: Optional[str] = None,
    ) -> None:
        """Create files for a checkpoint."""
        # Create checkpoint directory
        os.makedirs(checkpoint.path, exist_ok=True)
        
        # In a real implementation, this would save actual simulation state
        # Here we'll just create some empty files with metadata
        
        # Save metadata
        metadata_path = os.path.join(checkpoint.path, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(checkpoint.metadata.model_dump(), f, cls=DateTimeEncoder, indent=2)
        
        # Save simulation data (mock)
        simulation_path = os.path.join(checkpoint.path, "simulation.json")
        with open(simulation_path, "w") as f:
            # In a real implementation, this would be the actual simulation state
            # Here we'll just save some basic info
            sim_data = {
                "id": simulation.id,
                "name": simulation.name,
                "timestamp": datetime.now().isoformat(),
                "progress": simulation.total_progress(),
                "status": simulation.status.value,
            }
            json.dump(sim_data, f, cls=DateTimeEncoder, indent=2)
        
        # If stage specific, save stage data
        if stage_id and stage_id in simulation.stages:
            stage = simulation.stages[stage_id]
            stage_path = os.path.join(checkpoint.path, f"stage_{stage_id}.json")
            with open(stage_path, "w") as f:
                stage_data = {
                    "id": stage.id,
                    "name": stage.name,
                    "progress": stage.progress,
                    "status": stage.status.value,
                }
                json.dump(stage_data, f, cls=DateTimeEncoder, indent=2)
        
        # Create a mock data file
        data_path = os.path.join(checkpoint.path, "data.bin")
        with open(data_path, "wb") as f:
            # Just write some random bytes for mock data
            f.write(os.urandom(1024 * 1024))  # 1MB of random data
    
    def _get_checkpoint_size(self, checkpoint: Checkpoint) -> int:
        """Get the size of a checkpoint in bytes."""
        total_size = 0
        for root, _, files in os.walk(checkpoint.path):
            for f in files:
                file_path = os.path.join(root, f)
                total_size += os.path.getsize(file_path)
        return total_size
    
    def _calculate_validation_hash(self, checkpoint: Checkpoint) -> str:
        """Calculate a validation hash for a checkpoint."""
        hasher = hashlib.sha256()
        
        # Hash all files in the checkpoint
        for root, _, files in os.walk(checkpoint.path):
            for file_name in sorted(files):  # Sort for deterministic order
                file_path = os.path.join(root, file_name)
                with open(file_path, "rb") as f:
                    # Read and hash file in chunks
                    chunk = f.read(8192)
                    while chunk:
                        hasher.update(chunk)
                        chunk = f.read(8192)
        
        return hasher.hexdigest()
    
    def validate_checkpoint(self, checkpoint_id: str, simulation_id: str) -> ValidationResult:
        """Validate a checkpoint."""
        # Check if in cache
        cache_key = f"{simulation_id}:{checkpoint_id}"
        if cache_key in self.validation_cache:
            result, timestamp = self.validation_cache[cache_key]
            
            # Use cache if less than 1 hour old
            if datetime.now() - timestamp < timedelta(hours=1):
                return result
        
        # Get checkpoint
        if simulation_id not in self.checkpoints or checkpoint_id not in self.checkpoints[simulation_id]:
            logger.error(f"Checkpoint {checkpoint_id} not found for simulation {simulation_id}")
            result = ValidationResult.MISSING
            self.validation_cache[cache_key] = (result, datetime.now())
            return result
        
        checkpoint = self.checkpoints[simulation_id][checkpoint_id]
        
        # Check if checkpoint exists
        if not os.path.exists(checkpoint.path):
            logger.error(f"Checkpoint directory not found: {checkpoint.path}")
            result = ValidationResult.MISSING
            self.validation_cache[cache_key] = (result, datetime.now())
            return result
        
        # Check if checkpoint is complete
        metadata_path = os.path.join(checkpoint.path, "metadata.json")
        simulation_path = os.path.join(checkpoint.path, "simulation.json")
        data_path = os.path.join(checkpoint.path, "data.bin")
        
        if not all(os.path.exists(p) for p in [metadata_path, simulation_path, data_path]):
            logger.error(f"Checkpoint incomplete: {checkpoint.path}")
            result = ValidationResult.INCOMPLETE
            self.validation_cache[cache_key] = (result, datetime.now())
            return result
        
        # Validate hash if available
        if checkpoint.validation_hash:
            current_hash = self._calculate_validation_hash(checkpoint)
            if current_hash != checkpoint.validation_hash:
                logger.error(f"Checkpoint hash mismatch: {checkpoint.path}")
                result = ValidationResult.CORRUPTED
                self.validation_cache[cache_key] = (result, datetime.now())
                return result
        
        # Checkpoint is valid
        result = ValidationResult.VALID
        self.validation_cache[cache_key] = (result, datetime.now())
        return result
    
    def get_latest_checkpoint(
        self,
        simulation_id: str,
        stage_id: Optional[str] = None,
    ) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a simulation or stage."""
        if simulation_id not in self.simulation_managers:
            logger.error(f"No checkpoint manager found for simulation {simulation_id}")
            return None
        
        manager = self.simulation_managers[simulation_id]
        
        # Get latest checkpoint
        latest = manager.get_latest_checkpoint()
        
        # If stage specific, find latest for that stage
        if stage_id and latest and latest.metadata.stage_id != stage_id:
            # Find all checkpoints for this stage
            stage_checkpoints = [
                cp for cp in manager.checkpoints
                if cp.metadata.stage_id == stage_id and cp.status == CheckpointStatus.COMPLETE
            ]
            
            if not stage_checkpoints:
                return None
            
            # Sort by timestamp and return latest
            latest = sorted(
                stage_checkpoints,
                key=lambda cp: cp.metadata.checkpoint_time,
                reverse=True
            )[0]
        
        return latest
    
    def get_all_checkpoints(
        self,
        simulation_id: str,
        stage_id: Optional[str] = None,
    ) -> List[Checkpoint]:
        """Get all checkpoints for a simulation or stage."""
        if simulation_id not in self.simulation_managers:
            logger.error(f"No checkpoint manager found for simulation {simulation_id}")
            return []
        
        manager = self.simulation_managers[simulation_id]
        
        # Filter by stage if specified
        if stage_id:
            return [
                cp for cp in manager.checkpoints
                if cp.metadata.stage_id == stage_id
            ]
        
        return manager.checkpoints.copy()
        
    def get_checkpoints_for_simulation(self, simulation_id: str) -> List[Checkpoint]:
        """Get all checkpoints for a simulation. Alias for get_all_checkpoints."""
        return self.get_all_checkpoints(simulation_id)
    
    def restore_from_checkpoint(
        self,
        checkpoint_id: str,
        simulation_id: str,
    ) -> Result[bool]:
        """Restore a simulation from a checkpoint."""
        # Get checkpoint
        if simulation_id not in self.checkpoints or checkpoint_id not in self.checkpoints[simulation_id]:
            return Result.err(f"Checkpoint {checkpoint_id} not found for simulation {simulation_id}")
        
        checkpoint = self.checkpoints[simulation_id][checkpoint_id]
        
        # Validate checkpoint
        validation_result = self.validate_checkpoint(checkpoint_id, simulation_id)
        if validation_result != ValidationResult.VALID:
            return Result.err(f"Cannot restore from invalid checkpoint: {validation_result}")
        
        # In a real implementation, this would restore the simulation state
        # Here we'll just update the checkpoint's restore count
        
        checkpoint.restore_count += 1
        checkpoint.last_restore_time = datetime.now()
        
        return Result.ok(True)
    
    def _apply_retention_policy(self, simulation_id: str) -> None:
        """Apply retention policy to checkpoints."""
        if simulation_id not in self.simulation_managers:
            return
        
        manager = self.simulation_managers[simulation_id]
        
        # Get checkpoints to delete
        to_delete = manager.apply_retention_policy()
        
        # Delete checkpoints
        for checkpoint_id in to_delete:
            checkpoint = self.checkpoints[simulation_id].get(checkpoint_id)
            if checkpoint:
                # Remove checkpoint files
                if os.path.exists(checkpoint.path):
                    shutil.rmtree(checkpoint.path)
                
                # Remove from tracking
                del self.checkpoints[simulation_id][checkpoint_id]
                manager.checkpoints = [
                    cp for cp in manager.checkpoints if cp.id != checkpoint_id
                ]
                
                # Update latest checkpoint if needed
                if manager.latest_checkpoint_id == checkpoint_id:
                    remaining = [
                        cp for cp in manager.checkpoints
                        if cp.status == CheckpointStatus.COMPLETE
                    ]
                    if remaining:
                        latest = sorted(
                            remaining,
                            key=lambda cp: cp.metadata.checkpoint_time,
                            reverse=True
                        )[0]
                        manager.latest_checkpoint_id = latest.id
                    else:
                        manager.latest_checkpoint_id = None
    
    def archive_checkpoint(
        self,
        checkpoint_id: str,
        simulation_id: str,
        archive_path: Optional[str] = None,
    ) -> Result[str]:
        """Archive a checkpoint to long-term storage."""
        # Get checkpoint
        if simulation_id not in self.checkpoints or checkpoint_id not in self.checkpoints[simulation_id]:
            return Result.err(f"Checkpoint {checkpoint_id} not found for simulation {simulation_id}")
        
        checkpoint = self.checkpoints[simulation_id][checkpoint_id]
        
        # Validate checkpoint
        validation_result = self.validate_checkpoint(checkpoint_id, simulation_id)
        if validation_result != ValidationResult.VALID:
            return Result.err(f"Cannot archive invalid checkpoint: {validation_result}")
        
        # If archive path not specified, use default
        if not archive_path:
            archive_path = os.path.join(
                self.base_storage_path,
                "archives",
                simulation_id,
                f"{checkpoint_id}.tar.gz"
            )
        
        # Create parent directory
        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
        
        # In a real implementation, this would compress and archive the checkpoint
        # Here we'll just update the checkpoint's status
        
        checkpoint.status = CheckpointStatus.ARCHIVED
        
        return Result.ok(archive_path)
    
    def cleanup(self) -> None:
        """Clean up resources used by the checkpoint manager."""
        # Shutdown executor
        self.executor.shutdown(wait=True)


class CheckpointCoordinator:
    """Coordinates checkpoint creation across simulations."""
    
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        max_concurrent_checkpoints: int = 5,
    ):
        self.checkpoint_manager = checkpoint_manager
        self.max_concurrent_checkpoints = max_concurrent_checkpoints
        self.scheduled_checkpoints: Dict[str, datetime] = {}  # simulation_id -> scheduled_time
        self.last_checkpoint_time: Dict[str, datetime] = {}  # simulation_id -> last_checkpoint_time
        self.checkpoint_failures: Dict[str, int] = {}  # simulation_id -> failure_count
    
    def schedule_checkpoint(
        self,
        simulation_id: str,
        scheduled_time: Optional[datetime] = None,
    ) -> None:
        """Schedule a checkpoint for a simulation."""
        if scheduled_time is None:
            scheduled_time = datetime.now()
        
        self.scheduled_checkpoints[simulation_id] = scheduled_time
    
    def process_scheduled_checkpoints(self, simulations: Dict[str, Simulation]) -> List[str]:
        """Process scheduled checkpoints."""
        # Get checkpoints due for creation
        now = datetime.now()
        due_checkpoints = [
            sim_id for sim_id, scheduled_time in self.scheduled_checkpoints.items()
            if scheduled_time <= now and sim_id in simulations
        ]
        
        # Limit to max concurrent
        active_checkpoints = len(self.checkpoint_manager.active_operations)
        available_slots = max(0, self.max_concurrent_checkpoints - active_checkpoints)
        
        if available_slots <= 0:
            return []
        
        # Sort by priority (e.g., time since last checkpoint)
        def checkpoint_priority(sim_id: str) -> float:
            # Higher value = higher priority
            
            # Factor 1: Time since last checkpoint
            last_time = self.last_checkpoint_time.get(sim_id)
            time_factor = 0.0
            if last_time:
                hours_since_last = (now - last_time).total_seconds() / 3600
                time_factor = min(24, hours_since_last) / 24  # Normalize to 0-1 range
            else:
                time_factor = 1.0  # Max priority if never checkpointed
            
            # Factor 2: Simulation priority
            sim = simulations[sim_id]
            priority_values = {
                "critical": 1.0,
                "high": 0.8,
                "medium": 0.6,
                "low": 0.4,
                "background": 0.2,
            }
            priority_factor = priority_values.get(sim.priority.value, 0.5)
            
            # Factor 3: Progress since last checkpoint
            progress_factor = 0.0
            if last_time:
                # In a real implementation, we'd track progress at last checkpoint
                # Here we'll just use a random value
                import random
                progress_factor = random.random()
            else:
                progress_factor = 1.0  # Max priority if never checkpointed
            
            # Combine factors
            return (time_factor * 0.5) + (priority_factor * 0.3) + (progress_factor * 0.2)
        
        # Sort by priority
        due_checkpoints.sort(key=checkpoint_priority, reverse=True)
        
        # Take top N
        to_process = due_checkpoints[:available_slots]
        
        # Create checkpoints
        created = []
        
        for sim_id in to_process:
            # Remove from scheduled
            del self.scheduled_checkpoints[sim_id]
            
            # Create checkpoint
            result = self.checkpoint_manager.create_checkpoint(simulations[sim_id])
            
            if result.success:
                # Update last checkpoint time
                self.last_checkpoint_time[sim_id] = now
                created.append(sim_id)
                
                # Reset failure count
                self.checkpoint_failures[sim_id] = 0
            else:
                # Increment failure count
                failures = self.checkpoint_failures.get(sim_id, 0) + 1
                self.checkpoint_failures[sim_id] = failures
                
                # Reschedule with backoff
                backoff_minutes = min(60, 5 * (2 ** min(5, failures - 1)))
                self.schedule_checkpoint(
                    sim_id,
                    now + timedelta(minutes=backoff_minutes)
                )
        
        return created
    
    def should_checkpoint_simulation(self, simulation: Simulation) -> bool:
        """Determine if a simulation should be checkpointed."""
        # If already scheduled, don't re-check
        if simulation.id in self.scheduled_checkpoints:
            return False
        
        return self.checkpoint_manager.should_create_checkpoint(simulation)