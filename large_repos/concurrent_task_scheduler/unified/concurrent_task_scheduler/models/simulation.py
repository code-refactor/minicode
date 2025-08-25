"""Core simulation models and definitions."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field
from dataclasses import dataclass, field

# Import from common library
from common.core.models import (
    BaseJob, BaseNode, Priority, JobStatus, NodeStatus, NodeCapabilities,
    ResourceType, ResourceRequirement as CommonResourceRequirement
)


# Extend common ResourceRequirement for simulation-specific needs
class ResourceRequirement(CommonResourceRequirement):
    """Extended resource requirements for simulation components."""
    unit: str = ""  # Make unit optional with default


class SimulationStageStatus(str, Enum):
    """Status of a simulation stage."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationStage(BaseModel):
    """A single stage in a multi-stage simulation workflow."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    estimated_duration: timedelta
    resource_requirements: List[ResourceRequirement] = Field(default_factory=list)
    dependencies: Set[str] = Field(default_factory=set)
    status: SimulationStageStatus = SimulationStageStatus.PENDING
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    checkpoint_frequency: timedelta = Field(default=timedelta(hours=1))
    last_checkpoint_time: Optional[datetime] = None
    checkpoint_path: Optional[str] = None
    error_message: Optional[str] = None


# Use Priority from common library for consistency
SimulationPriority = Priority


class SimulationStatus(str, Enum):
    """Status of a simulation."""

    DEFINED = "defined"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Simulation(BaseModel):
    """A complete simulation with multiple stages."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    stages: Dict[str, SimulationStage]
    priority: Priority = Priority.MEDIUM
    status: SimulationStatus = SimulationStatus.DEFINED
    creation_time: datetime = Field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    owner: str = "default_owner"
    project: str = "default_project"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    result_path: Optional[str] = None
    scientific_promise: float = 0.5  # Scale of 0-1 for prioritization
    estimated_total_duration: timedelta = Field(default=timedelta(days=1))
    
    @property
    def progress(self) -> float:
        """Get the simulation progress. Alias for total_progress."""
        # For compatibility with tests that expect a progress property
        # Access metadata if it's there, otherwise calculate from stages
        if "progress" in self.metadata:
            return float(self.metadata["progress"])
        return self.total_progress()

    def total_progress(self) -> float:
        """Calculate the total progress of the simulation."""
        if not self.stages:
            return 0.0
        
        total_progress = sum(stage.progress for stage in self.stages.values())
        return total_progress / len(self.stages)
    
    def estimated_completion_time(self) -> Optional[datetime]:
        """Estimate the completion time based on progress and elapsed time."""
        if self.status not in [SimulationStatus.RUNNING, SimulationStatus.PAUSED]:
            return None
        
        if self.start_time is None:
            return None
        
        progress = self.total_progress()
        if progress <= 0:
            return None
        
        elapsed_time = datetime.now() - self.start_time
        total_estimated_time = elapsed_time / progress
        remaining_time = total_estimated_time - elapsed_time
        
        return datetime.now() + remaining_time
    
    def get_active_stage_ids(self) -> List[str]:
        """Get the IDs of all currently active stages."""
        return [
            stage_id for stage_id, stage in self.stages.items()
            if stage.status == SimulationStageStatus.RUNNING
        ]
    
    def get_pending_stage_ids(self) -> List[str]:
        """Get the IDs of all pending stages."""
        return [
            stage_id for stage_id, stage in self.stages.items()
            if stage.status == SimulationStageStatus.PENDING
        ]
    
    def get_next_stages(self) -> List[str]:
        """Get the IDs of stages that are ready to run based on dependencies."""
        result = []
        for stage_id, stage in self.stages.items():
            if stage.status != SimulationStageStatus.PENDING:
                continue
            
            dependencies_met = True
            for dep_id in stage.dependencies:
                if dep_id not in self.stages:
                    dependencies_met = False
                    break
                
                dep_stage = self.stages[dep_id]
                if dep_stage.status != SimulationStageStatus.COMPLETED:
                    dependencies_met = False
                    break
            
            if dependencies_met:
                result.append(stage_id)
        
        return result
    
    def update_status(self) -> None:
        """Update the overall simulation status based on stage statuses."""
        if all(stage.status == SimulationStageStatus.COMPLETED for stage in self.stages.values()):
            self.status = SimulationStatus.COMPLETED
            if self.end_time is None:
                self.end_time = datetime.now()
        elif any(stage.status == SimulationStageStatus.FAILED for stage in self.stages.values()):
            self.status = SimulationStatus.FAILED
        elif any(stage.status == SimulationStageStatus.RUNNING for stage in self.stages.values()):
            self.status = SimulationStatus.RUNNING
            if self.start_time is None:
                self.start_time = datetime.now()
        elif any(stage.status == SimulationStageStatus.PAUSED for stage in self.stages.values()):
            self.status = SimulationStatus.PAUSED
        elif all(stage.status in [SimulationStageStatus.PENDING, SimulationStageStatus.QUEUED]
                 for stage in self.stages.values()):
            self.status = SimulationStatus.SCHEDULED


# Add simulation-specific node statuses by extending the base enum
class ExtendedNodeStatus(str, Enum):
    """Extended node status for simulation-specific needs."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    BUSY = "busy"
    IDLE = "idle"
    RESERVED = "reserved"  # Simulation-specific status


class NodeType(str, Enum):
    """Type of compute node."""

    COMPUTE = "compute"
    GPU = "gpu"
    MEMORY = "memory"
    STORAGE = "storage"


@dataclass
class ComputeNode(BaseNode):
    """Representation of a compute node in the cluster, extending BaseNode."""

    # Extend BaseNode with simulation-specific fields
    node_type: NodeType = NodeType.COMPUTE
    assigned_simulations: List[str] = field(default_factory=list)
    last_failure_time: Optional[datetime] = None
    maintenance_window: Optional[Dict[str, datetime]] = None
    location: str = "unknown"
    
    def __init__(self, **data):
        # Handle legacy field mappings for backward compatibility
        if 'cpu_cores' in data:
            if 'capabilities' not in data:
                data['capabilities'] = NodeCapabilities()
            data['capabilities'].cpu_cores = data.pop('cpu_cores')
        if 'memory_gb' in data:
            if 'capabilities' not in data:
                data['capabilities'] = NodeCapabilities()
            data['capabilities'].memory_gb = data.pop('memory_gb')
        if 'gpu_count' in data:
            if 'capabilities' not in data:
                data['capabilities'] = NodeCapabilities()
            data['capabilities'].gpu_count = data.pop('gpu_count')
        if 'storage_gb' in data:
            if 'capabilities' not in data:
                data['capabilities'] = NodeCapabilities()
            data['capabilities'].storage_gb = data.pop('storage_gb')
        if 'network_bandwidth_gbps' in data:
            if 'capabilities' not in data:
                data['capabilities'] = NodeCapabilities()
            data['capabilities'].network_bandwidth_gbps = data.pop('network_bandwidth_gbps')
        
        # Extract ComputeNode-specific fields
        compute_node_fields = {
            'node_type': data.pop('node_type', NodeType.COMPUTE),
            'assigned_simulations': data.pop('assigned_simulations', []),
            'last_failure_time': data.pop('last_failure_time', None),
            'maintenance_window': data.pop('maintenance_window', None),
            'location': data.pop('location', 'unknown')
        }
        
        # Initialize BaseNode with remaining data
        super().__init__(**data)
        
        # Set ComputeNode-specific fields
        for field_name, field_value in compute_node_fields.items():
            setattr(self, field_name, field_value)
    
    # Backward compatibility properties
    @property
    def cpu_cores(self) -> int:
        return self.capabilities.cpu_cores
    
    @property
    def memory_gb(self) -> float:
        return self.capabilities.memory_gb
    
    @property
    def gpu_count(self) -> int:
        return self.capabilities.gpu_count
    
    @property
    def storage_gb(self) -> float:
        return self.capabilities.storage_gb
    
    @property
    def network_bandwidth_gbps(self) -> float:
        return self.capabilities.network_bandwidth_gbps
    
    def is_available(self) -> bool:
        """Check if the node is available for new simulations."""
        # Use parent method and add simulation-specific logic
        return (super().is_available() and 
                len(self.assigned_simulations) < self.capabilities.cpu_cores)
    
    def get_available_resources(self) -> Dict[ResourceType, float]:
        """Get the available resources on this node."""
        # Use parent method
        return super().get_available_resources()
    
    def can_accommodate(self, requirements: List[ResourceRequirement]) -> bool:
        """Check if this node can accommodate the given resource requirements."""
        # Convert to common ResourceRequirement format for parent method
        common_reqs = [
            CommonResourceRequirement(resource_type=req.resource_type, amount=req.amount, unit=req.unit)
            for req in requirements
        ]
        return self.capabilities.can_satisfy(common_reqs)


class ClusterStatus(BaseModel):
    """Overall status of the compute cluster."""

    total_nodes: int
    available_nodes: int
    reserved_nodes: int
    maintenance_nodes: int
    offline_nodes: int
    total_resource_usage: Dict[ResourceType, float]
    available_resources: Dict[ResourceType, float]
    running_simulations: int
    queued_simulations: int
    last_updated: datetime = Field(default_factory=datetime.now)