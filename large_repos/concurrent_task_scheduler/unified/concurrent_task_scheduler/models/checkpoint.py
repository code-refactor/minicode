"""Checkpoint models for simulation state preservation."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class CheckpointType(str, Enum):
    """Types of checkpoints that can be created."""

    FULL = "full"  # Complete simulation state
    INCREMENTAL = "incremental"  # Changes since last checkpoint
    METADATA_ONLY = "metadata_only"  # Only simulation metadata, no results
    CRITICAL_STATE = "critical_state"  # Only the most critical state information


class CheckpointStatus(str, Enum):
    """Status of a checkpoint."""

    CREATING = "creating"
    COMPLETE = "complete"
    FAILED = "failed"
    CORRUPTED = "corrupted"
    ARCHIVED = "archived"


class CheckpointStorageType(str, Enum):
    """Types of storage for checkpoints."""

    LOCAL = "local"  # Local filesystem
    PARALLEL_FS = "parallel_fs"  # Parallel distributed filesystem
    OBJECT_STORE = "object_store"  # Object storage
    ARCHIVE = "archive"  # Long-term archive storage


class CheckpointCompression(str, Enum):
    """Compression types for checkpoints."""

    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"
    LZ4 = "lz4"


class CheckpointMetadata(BaseModel):
    """Metadata for a checkpoint."""

    simulation_id: str
    simulation_name: str
    stage_id: Optional[str] = None
    stage_name: Optional[str] = None
    checkpoint_time: datetime = Field(default_factory=datetime.now)
    checkpoint_type: CheckpointType
    storage_type: CheckpointStorageType
    compression: CheckpointCompression = CheckpointCompression.ZSTD
    size_bytes: int = 0
    creation_duration_seconds: float = 0.0
    node_ids: List[str] = Field(default_factory=list)
    progress_at_checkpoint: float
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_json(self) -> str:
        """Convert metadata to JSON string."""
        return json.dumps(self.model_dump(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> CheckpointMetadata:
        """Create metadata from JSON string."""
        data = json.loads(json_str)
        
        # Convert string timestamps to datetime objects
        if "checkpoint_time" in data and isinstance(data["checkpoint_time"], str):
            data["checkpoint_time"] = datetime.fromisoformat(data["checkpoint_time"].replace("Z", "+00:00"))
        
        return cls(**data)


class Checkpoint(BaseModel):
    """Representation of a simulation checkpoint."""

    id: str = Field(default_factory=lambda: f"cp_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    metadata: CheckpointMetadata
    status: CheckpointStatus = CheckpointStatus.CREATING
    path: str
    validation_hash: Optional[str] = None
    restore_count: int = 0
    last_restore_time: Optional[datetime] = None
    retention_policy: str = "standard"  # Determines how long to keep the checkpoint
    
    def get_path(self) -> Path:
        """Get the checkpoint path as a Path object."""
        return Path(self.path)
    
    def validate(self) -> bool:
        """Validate the checkpoint integrity."""
        # This is a placeholder for actual validation logic
        return self.status == CheckpointStatus.COMPLETE
    
    def mark_as_restored(self) -> None:
        """Mark this checkpoint as having been restored."""
        self.restore_count += 1
        self.last_restore_time = datetime.now()


class CheckpointPolicy(BaseModel):
    """Policy for checkpoint creation and management."""

    name: str
    description: Optional[str] = None
    checkpoint_type: CheckpointType = CheckpointType.FULL
    storage_type: CheckpointStorageType = CheckpointStorageType.PARALLEL_FS
    compression: CheckpointCompression = CheckpointCompression.ZSTD
    frequency_minutes: int = 60  # How often to create checkpoints
    min_progress_delta: float = 0.05  # Minimum progress change to trigger checkpoint
    retention_periods: Dict[str, int] = Field(
        default_factory=lambda: {
            "recent": 24,  # hours to keep recent checkpoints
            "daily": 7,    # days to keep daily checkpoints
            "weekly": 4,   # weeks to keep weekly checkpoints
            "monthly": 6,  # months to keep monthly checkpoints
        }
    )
    max_checkpoint_size_gb: Optional[float] = None  # Max size for a checkpoint
    priority_level: int = 3  # 1 (highest) to 5 (lowest)
    enabled: bool = True
    
    @property
    def interval_minutes(self) -> int:
        """Alias for frequency_minutes for backward compatibility."""
        return self.frequency_minutes
        
    @property
    def priority(self):
        """Legacy property for SimulationPriority compatibility."""
        from concurrent_task_scheduler.models.simulation import Priority as SimulationPriority
        # Convert priority_level to SimulationPriority
        # 1 (highest) to 5 (lowest)
        if self.priority_level <= 1:
            return SimulationPriority.HIGH
        elif self.priority_level <= 3:
            return SimulationPriority.MEDIUM
        else:
            return SimulationPriority.LOW
    
    def should_create_checkpoint(
        self,
        last_checkpoint_time: Optional[datetime],
        current_time: datetime,
        last_progress: float,
        current_progress: float
    ) -> bool:
        """Determine if a checkpoint should be created based on this policy."""
        # Always create first checkpoint
        if last_checkpoint_time is None:
            return True
        
        # Check time-based frequency
        time_diff = (current_time - last_checkpoint_time).total_seconds() / 60
        if time_diff >= self.frequency_minutes:
            return True
        
        # Check progress-based frequency
        progress_diff = current_progress - last_progress
        if progress_diff >= self.min_progress_delta:
            return True
        
        return False


class CheckpointManager(BaseModel):
    """Manager for simulation checkpoints."""

    simulation_id: str
    checkpoint_policy: CheckpointPolicy
    checkpoints: List[Checkpoint] = Field(default_factory=list)
    latest_checkpoint_id: Optional[str] = None
    base_storage_path: str
    total_storage_used_bytes: int = 0
    
    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Get the latest successful checkpoint."""
        if not self.latest_checkpoint_id:
            return None
        
        for checkpoint in reversed(self.checkpoints):
            if (checkpoint.id == self.latest_checkpoint_id and 
                checkpoint.status == CheckpointStatus.COMPLETE):
                return checkpoint
        
        return None
    
    def get_checkpoint_by_id(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a specific checkpoint by ID."""
        for checkpoint in self.checkpoints:
            if checkpoint.id == checkpoint_id:
                return checkpoint
        
        return None
    
    def should_create_checkpoint(
        self,
        current_time: datetime,
        current_progress: float
    ) -> bool:
        """Determine if a new checkpoint should be created."""
        latest = self.get_latest_checkpoint()
        
        last_checkpoint_time = None
        last_progress = 0.0
        
        if latest:
            last_checkpoint_time = latest.metadata.checkpoint_time
            last_progress = latest.metadata.progress_at_checkpoint
        
        return self.checkpoint_policy.should_create_checkpoint(
            last_checkpoint_time, current_time, last_progress, current_progress
        )
    
    def generate_checkpoint_path(self, stage_id: Optional[str] = None) -> str:
        """Generate a path for a new checkpoint."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stage_suffix = f"_stage_{stage_id}" if stage_id else ""
        checkpoint_id = f"cp_{timestamp}{stage_suffix}"
        
        return f"{self.base_storage_path}/{self.simulation_id}/{checkpoint_id}"
    
    def apply_retention_policy(self) -> List[str]:
        """Apply retention policy and return IDs of checkpoints to delete."""
        # This is a simplified implementation
        checkpoints_to_delete = []
        current_time = datetime.now()
        
        # Keep only a certain number of recent checkpoints
        if len(self.checkpoints) > 10:  # Arbitrary limit for example
            older_checkpoints = sorted(
                [cp for cp in self.checkpoints if cp.status == CheckpointStatus.COMPLETE],
                key=lambda cp: cp.metadata.checkpoint_time
            )[:-10]  # Keep the 10 most recent
            
            for checkpoint in older_checkpoints:
                age_days = (current_time - checkpoint.metadata.checkpoint_time).days
                
                # Always keep monthly checkpoints
                if age_days % 30 < 2 and age_days >= 30:
                    continue
                
                # Keep weekly checkpoints for a few months
                if age_days % 7 < 2 and age_days < 90:
                    continue
                
                checkpoints_to_delete.append(checkpoint.id)
        
        return checkpoints_to_delete