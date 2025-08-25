"""Core models for the Render Farm Manager."""

from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field

# Import common models
from common.core.models import (
    BaseJob, BaseNode, JobStatus, NodeStatus as CommonNodeStatus,
    Priority, ResourceRequirement, ResourceType, NodeCapabilities as CommonNodeCapabilities
)


class JobPriority(str, Enum):
    """Priority levels for render jobs."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    # Mapping to common Priority enum
    def to_common_priority(self) -> Priority:
        """Convert to common Priority enum."""
        mapping = {
            JobPriority.LOW: Priority.LOW,
            JobPriority.MEDIUM: Priority.MEDIUM,
            JobPriority.HIGH: Priority.HIGH,
            JobPriority.CRITICAL: Priority.CRITICAL
        }
        return mapping.get(self, Priority.MEDIUM)
    
    @classmethod
    def from_common_priority(cls, priority: Priority) -> 'JobPriority':
        """Convert from common Priority enum."""
        mapping = {
            Priority.LOW: JobPriority.LOW,
            Priority.MEDIUM: JobPriority.MEDIUM,
            Priority.HIGH: JobPriority.HIGH,
            Priority.CRITICAL: JobPriority.CRITICAL
        }
        return mapping.get(priority, JobPriority.MEDIUM)


class ServiceTier(str, Enum):
    """Service tiers for clients."""
    
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class NodeType(str, Enum):
    """Types of render nodes."""
    
    CPU = "cpu"
    GPU = "gpu"
    HYBRID = "hybrid"
    SPECIALIZED = "specialized"


class LogLevel(str, Enum):
    """Log levels for the audit logger."""
    
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RenderJobStatus(str, Enum):
    """Status values for render jobs."""
    
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    # Mapping to common JobStatus enum
    def to_common_status(self) -> JobStatus:
        """Convert to common JobStatus enum."""
        mapping = {
            RenderJobStatus.PENDING: JobStatus.PENDING,
            RenderJobStatus.QUEUED: JobStatus.QUEUED,
            RenderJobStatus.RUNNING: JobStatus.RUNNING,
            RenderJobStatus.PAUSED: JobStatus.PAUSED,
            RenderJobStatus.COMPLETED: JobStatus.COMPLETED,
            RenderJobStatus.FAILED: JobStatus.FAILED,
            RenderJobStatus.CANCELLED: JobStatus.CANCELLED
        }
        return mapping.get(self, JobStatus.PENDING)
    
    @classmethod
    def from_common_status(cls, status: JobStatus) -> 'RenderJobStatus':
        """Convert from common JobStatus enum."""
        mapping = {
            JobStatus.PENDING: RenderJobStatus.PENDING,
            JobStatus.QUEUED: RenderJobStatus.QUEUED,
            JobStatus.RUNNING: RenderJobStatus.RUNNING,
            JobStatus.PAUSED: RenderJobStatus.PAUSED,
            JobStatus.COMPLETED: RenderJobStatus.COMPLETED,
            JobStatus.FAILED: RenderJobStatus.FAILED,
            JobStatus.CANCELLED: RenderJobStatus.CANCELLED
        }
        return mapping.get(status, RenderJobStatus.PENDING)


class NodeStatus(str, Enum):
    """Status values for render nodes."""
    
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    STARTING = "starting"
    STOPPING = "stopping"
    
    # Mapping to common NodeStatus enum
    def to_common_status(self) -> CommonNodeStatus:
        """Convert to common NodeStatus enum."""
        mapping = {
            NodeStatus.ONLINE: CommonNodeStatus.ONLINE,
            NodeStatus.OFFLINE: CommonNodeStatus.OFFLINE,
            NodeStatus.MAINTENANCE: CommonNodeStatus.MAINTENANCE,
            NodeStatus.ERROR: CommonNodeStatus.OFFLINE,  # Map ERROR to OFFLINE
            NodeStatus.STARTING: CommonNodeStatus.IDLE,  # Map STARTING to IDLE
            NodeStatus.STOPPING: CommonNodeStatus.OFFLINE  # Map STOPPING to OFFLINE
        }
        return mapping.get(self, CommonNodeStatus.OFFLINE)
    
    @classmethod
    def from_common_status(cls, status: CommonNodeStatus) -> 'NodeStatus':
        """Convert from common NodeStatus enum."""
        mapping = {
            CommonNodeStatus.ONLINE: NodeStatus.ONLINE,
            CommonNodeStatus.OFFLINE: NodeStatus.OFFLINE,
            CommonNodeStatus.MAINTENANCE: NodeStatus.MAINTENANCE,
            CommonNodeStatus.IDLE: NodeStatus.ONLINE,  # Map IDLE to ONLINE
            CommonNodeStatus.BUSY: NodeStatus.ONLINE   # Map BUSY to ONLINE
        }
        return mapping.get(status, NodeStatus.OFFLINE)


class EnergyMode(str, Enum):
    """Energy usage modes for the render farm."""
    
    PERFORMANCE = "performance"  # Maximum performance, disregard energy usage
    BALANCED = "balanced"  # Balance between performance and energy efficiency
    EFFICIENCY = "efficiency"  # Optimize for energy efficiency, may impact performance
    NIGHT_SAVINGS = "night_savings"  # Special mode for overnight operations


class NodeCapabilities(BaseModel):
    """Capabilities and specifications of a render node."""
    
    cpu_cores: int = Field(..., gt=0)
    memory_gb: int = Field(..., gt=0)
    gpu_model: Optional[str] = None
    gpu_count: int = Field(default=0, ge=0)
    gpu_memory_gb: float = Field(default=0, ge=0)
    gpu_compute_capability: float = Field(default=0, ge=0)
    storage_gb: int = Field(..., gt=0)
    specialized_for: List[str] = Field(default_factory=list)
    
    def to_common_capabilities(self) -> CommonNodeCapabilities:
        """Convert to common NodeCapabilities."""
        return CommonNodeCapabilities(
            cpu_cores=self.cpu_cores,
            gpu_count=self.gpu_count,
            memory_gb=float(self.memory_gb),
            storage_gb=float(self.storage_gb),
            network_bandwidth_gbps=1.0,  # Default network bandwidth
            specialized_hardware=[self.gpu_model] if self.gpu_model else [],
            software_capabilities=self.specialized_for
        )
    
    @classmethod
    def from_common_capabilities(cls, capabilities: CommonNodeCapabilities) -> 'NodeCapabilities':
        """Convert from common NodeCapabilities."""
        return cls(
            cpu_cores=capabilities.cpu_cores,
            memory_gb=int(capabilities.memory_gb),
            gpu_count=capabilities.gpu_count,
            gpu_model=capabilities.specialized_hardware[0] if capabilities.specialized_hardware else None,
            storage_gb=int(capabilities.storage_gb),
            specialized_for=capabilities.software_capabilities
        )


class RenderNode(BaseModel):
    """A node in the render farm capable of executing render jobs."""
    
    id: str
    name: str
    status: str
    capabilities: NodeCapabilities
    power_efficiency_rating: float = Field(..., ge=0, le=100)
    current_job_id: Optional[str] = None
    performance_history: Dict[str, float] = Field(default_factory=dict)
    last_error: Optional[str] = None
    uptime_hours: float = Field(default=0, ge=0)
    
    def to_common_node(self) -> BaseNode:
        """Convert to common BaseNode."""
        # Map render status to common status
        render_status = NodeStatus(self.status)
        common_status = render_status.to_common_status()
        
        node = BaseNode(
            id=self.id,
            name=self.name,
            status=common_status,
            capabilities=self.capabilities.to_common_capabilities(),
            assigned_jobs=[self.current_job_id] if self.current_job_id else [],
            reliability_score=self.power_efficiency_rating / 100.0,
            metadata={
                "power_efficiency_rating": self.power_efficiency_rating,
                "performance_history": self.performance_history,
                "last_error": self.last_error,
                "uptime_hours": self.uptime_hours
            }
        )
        return node
    
    @classmethod
    def from_common_node(cls, node: BaseNode, power_efficiency_rating: float = 80.0) -> 'RenderNode':
        """Convert from common BaseNode."""
        # Convert capabilities
        capabilities = NodeCapabilities.from_common_capabilities(node.capabilities)
        
        # Get metadata values
        metadata = node.metadata or {}
        
        return cls(
            id=node.id,
            name=node.name,
            status=NodeStatus.from_common_status(node.status).value,
            capabilities=capabilities,
            power_efficiency_rating=metadata.get("power_efficiency_rating", power_efficiency_rating),
            current_job_id=node.assigned_jobs[0] if node.assigned_jobs else None,
            performance_history=metadata.get("performance_history", {}),
            last_error=metadata.get("last_error"),
            uptime_hours=metadata.get("uptime_hours", 0.0)
        )
    
    def model_copy(self, **kwargs):
        """Create a copy of the model."""
        return self.__class__(**{**self.model_dump(), **kwargs})
    
    def copy(self, **kwargs):
        """Deprecated copy method."""
        return self.model_copy(**kwargs)


class RenderJob(BaseModel):
    """A rendering job submitted to the farm."""
    
    id: str
    name: str
    client_id: str
    status: RenderJobStatus = RenderJobStatus.PENDING
    job_type: str
    priority: JobPriority
    submission_time: datetime
    deadline: datetime
    estimated_duration_hours: float = Field(..., gt=0)
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    requires_gpu: bool = False
    memory_requirements_gb: int = Field(..., gt=0)
    cpu_requirements: int = Field(..., gt=0)
    scene_complexity: int = Field(..., ge=1, le=10)
    dependencies: List[str] = Field(default_factory=list)
    assigned_node_id: Optional[str] = None
    output_path: str
    error_count: int = Field(default=0, ge=0)
    can_be_preempted: bool = True
    supports_progressive_output: bool = False
    supports_checkpoint: bool = False
    last_checkpoint_time: Optional[datetime] = None
    last_progressive_output_time: Optional[datetime] = None
    energy_intensive: bool = False
    
    def to_common_job(self) -> BaseJob:
        """Convert to common BaseJob."""
        # Create resource requirements
        resource_requirements = []
        if self.cpu_requirements > 0:
            resource_requirements.append(
                ResourceRequirement(ResourceType.CPU, float(self.cpu_requirements), "cores")
            )
        if self.memory_requirements_gb > 0:
            resource_requirements.append(
                ResourceRequirement(ResourceType.MEMORY, float(self.memory_requirements_gb), "GB")
            )
        if self.requires_gpu:
            resource_requirements.append(
                ResourceRequirement(ResourceType.GPU, 1.0, "count")
            )
        
        # Convert duration to timedelta
        from datetime import timedelta
        estimated_duration = timedelta(hours=self.estimated_duration_hours)
        
        job = BaseJob(
            id=self.id,
            name=self.name,
            status=self.status.to_common_status(),
            priority=self.priority.to_common_priority(),
            submission_time=self.submission_time,
            estimated_duration=estimated_duration,
            progress=self.progress,
            dependencies=self.dependencies,
            resource_requirements=resource_requirements,
            assigned_node=self.assigned_node_id,
            retry_count=self.error_count,
            metadata={
                "client_id": self.client_id,
                "job_type": self.job_type,
                "deadline": self.deadline,
                "scene_complexity": self.scene_complexity,
                "output_path": self.output_path,
                "can_be_preempted": self.can_be_preempted,
                "supports_progressive_output": self.supports_progressive_output,
                "supports_checkpoint": self.supports_checkpoint,
                "last_checkpoint_time": self.last_checkpoint_time,
                "last_progressive_output_time": self.last_progressive_output_time,
                "energy_intensive": self.energy_intensive
            }
        )
        return job
    
    @classmethod
    def from_common_job(cls, job: BaseJob, client_id: str = "default", 
                       job_type: str = "render", deadline: Optional[datetime] = None) -> 'RenderJob':
        """Convert from common BaseJob."""
        # Extract resource requirements
        cpu_requirements = 1
        memory_requirements_gb = 1
        requires_gpu = False
        
        for req in job.resource_requirements:
            if req.resource_type == ResourceType.CPU:
                cpu_requirements = int(req.amount)
            elif req.resource_type == ResourceType.MEMORY:
                memory_requirements_gb = int(req.amount)
            elif req.resource_type == ResourceType.GPU:
                requires_gpu = req.amount > 0
        
        # Get metadata values
        metadata = job.metadata or {}
        
        # Set deadline
        if deadline is None:
            deadline = metadata.get("deadline")
            if deadline is None:
                from datetime import timedelta
                deadline = job.submission_time + timedelta(days=1)  # Default 1 day
        
        return cls(
            id=job.id,
            name=job.name,
            client_id=metadata.get("client_id", client_id),
            status=RenderJobStatus.from_common_status(job.status),
            job_type=metadata.get("job_type", job_type),
            priority=JobPriority.from_common_priority(job.priority),
            submission_time=job.submission_time,
            deadline=deadline,
            estimated_duration_hours=job.estimated_duration.total_seconds() / 3600,
            progress=job.progress,
            requires_gpu=requires_gpu,
            memory_requirements_gb=memory_requirements_gb,
            cpu_requirements=cpu_requirements,
            scene_complexity=metadata.get("scene_complexity", 5),
            dependencies=job.dependencies,
            assigned_node_id=job.assigned_node,
            output_path=metadata.get("output_path", "/tmp/output"),
            error_count=job.retry_count,
            can_be_preempted=metadata.get("can_be_preempted", True),
            supports_progressive_output=metadata.get("supports_progressive_output", False),
            supports_checkpoint=metadata.get("supports_checkpoint", False),
            last_checkpoint_time=metadata.get("last_checkpoint_time"),
            last_progressive_output_time=metadata.get("last_progressive_output_time"),
            energy_intensive=metadata.get("energy_intensive", False)
        )
    
    def model_copy(self, **kwargs):
        """Create a copy of the model."""
        return self.__class__(**{**self.model_dump(), **kwargs})
    
    def copy(self, **kwargs):
        """Deprecated copy method."""
        return self.model_copy(**kwargs)


class Client(BaseModel):
    """A client organization that submits render jobs to the farm."""
    
    id: str
    name: str
    sla_tier: str  # premium, standard, basic
    guaranteed_resources: int = Field(..., ge=0)  # Percentage of resources guaranteed
    max_resources: int = Field(..., ge=0)  # Maximum percentage of resources allowed


class RenderClient(BaseModel):
    """A client organization that submits render jobs to the farm."""
    
    client_id: str
    name: str
    service_tier: ServiceTier
    guaranteed_resources: int = Field(default=0, ge=0)  # Percentage of resources guaranteed
    max_resources: int = Field(default=100, ge=0)  # Maximum percentage of resources allowed
    
    @property
    def id(self) -> str:
        """Get the client ID (alias for client_id for compatibility)."""
        return self.client_id
    
    @property
    def sla_tier(self) -> str:
        """Get the SLA tier (alias for service_tier for compatibility)."""
        return self.service_tier
    
    def model_copy(self, **kwargs):
        """Create a copy of the model."""
        return self.__class__(**{**self.model_dump(), **kwargs})
    
    def copy(self, **kwargs):
        """Deprecated copy method."""
        return self.model_copy(**kwargs)


class ProgressiveOutputConfig(BaseModel):
    """Configuration for progressive result generation."""
    
    enabled: bool = True
    interval_minutes: int = Field(default=30, gt=0)
    quality_levels: List[int] = Field(default_factory=lambda: [25, 50, 75])
    max_overhead_percentage: float = Field(default=5.0, ge=0.0, le=100.0)


class ResourceAllocation(BaseModel):
    """Resource allocation for a specific client."""
    
    client_id: str
    allocated_percentage: float = Field(..., ge=0, le=100)
    allocated_nodes: List[str] = Field(default_factory=list)
    borrowed_percentage: float = Field(default=0, ge=0)
    borrowed_from: Dict[str, float] = Field(default_factory=dict)
    lent_percentage: float = Field(default=0, ge=0)
    lent_to: Dict[str, float] = Field(default_factory=dict)


class PerformanceMetrics(BaseModel):
    """Performance metrics for the render farm."""
    
    total_jobs_completed: int = 0
    jobs_completed_on_time: int = 0
    average_utilization_percentage: float = 0.0
    average_node_idle_percentage: float = 0.0
    energy_usage_kwh: float = 0.0
    average_job_turnaround_hours: float = 0.0
    preemptions_count: int = 0
    node_failures_count: int = 0
    optimization_improvement_percentage: float = 0.0


class AuditLogEntry(BaseModel):
    """Entry in the audit log for the render farm."""
    
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str
    job_id: Optional[str] = None
    node_id: Optional[str] = None
    client_id: Optional[str] = None
    description: str
    details: Dict = Field(default_factory=dict)