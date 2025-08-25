"""Core data models for the unified task scheduling library."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field


class Priority(str, Enum):
    """Task priority levels."""
    BACKGROUND = "background"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    def __lt__(self, other):
        """Compare priorities for sorting."""
        if not isinstance(other, Priority):
            return NotImplemented
        order = [Priority.BACKGROUND, Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
        return order.index(self) < order.index(other)
    
    def __le__(self, other):
        """Compare priorities for sorting."""
        return self == other or self < other
    
    def __gt__(self, other):
        """Compare priorities for sorting."""
        if not isinstance(other, Priority):
            return NotImplemented
        return not self <= other
    
    def __ge__(self, other):
        """Compare priorities for sorting."""
        return self == other or self > other


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class NodeStatus(str, Enum):
    """Compute node status."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    BUSY = "busy"
    IDLE = "idle"


class ResourceType(str, Enum):
    """Types of computational resources."""
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"


class DependencyType(str, Enum):
    """Types of job dependencies."""
    COMPLETION = "completion"  # Job must complete successfully
    START = "start"  # Job must start
    DATA = "data"  # Data dependency
    RESOURCE = "resource"  # Resource availability


@dataclass
class ResourceRequirement:
    """Resource requirement specification."""
    resource_type: ResourceType
    amount: float
    unit: str = ""
    
    def __hash__(self):
        return hash((self.resource_type, self.amount, self.unit))


@dataclass
class NodeCapabilities:
    """Node hardware and software capabilities."""
    cpu_cores: int = 0
    gpu_count: int = 0
    memory_gb: float = 0.0
    storage_gb: float = 0.0
    network_bandwidth_gbps: float = 0.0
    specialized_hardware: List[str] = field(default_factory=list)
    software_capabilities: List[str] = field(default_factory=list)
    
    def has_capability(self, capability: str) -> bool:
        """Check if node has a specific capability."""
        return (capability in self.specialized_hardware or 
                capability in self.software_capabilities)
    
    def can_satisfy(self, requirements: List[ResourceRequirement]) -> bool:
        """Check if node can satisfy resource requirements."""
        for req in requirements:
            if req.resource_type == ResourceType.CPU and req.amount > self.cpu_cores:
                return False
            elif req.resource_type == ResourceType.GPU and req.amount > self.gpu_count:
                return False
            elif req.resource_type == ResourceType.MEMORY and req.amount > self.memory_gb:
                return False
            elif req.resource_type == ResourceType.STORAGE and req.amount > self.storage_gb:
                return False
            elif req.resource_type == ResourceType.NETWORK and req.amount > self.network_bandwidth_gbps:
                return False
        return True


@dataclass
class BaseJob:
    """Base job model for all task types."""
    id: str
    name: str
    status: JobStatus = JobStatus.PENDING
    priority: Priority = Priority.MEDIUM
    submission_time: datetime = field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    estimated_duration: timedelta = timedelta(hours=1)
    actual_duration: Optional[timedelta] = None
    progress: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    resource_requirements: List[ResourceRequirement] = field(default_factory=list)
    assigned_node: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __hash__(self):
        return hash(self.id)
    
    def is_ready(self, completed_jobs: Set[str]) -> bool:
        """Check if job is ready to run based on dependencies."""
        return all(dep in completed_jobs for dep in self.dependencies)
    
    def is_complete(self) -> bool:
        """Check if job has completed (successfully or not)."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    def is_active(self) -> bool:
        """Check if job is currently active."""
        return self.status in [JobStatus.RUNNING, JobStatus.QUEUED]
    
    def can_retry(self) -> bool:
        """Check if job can be retried after failure."""
        return self.status == JobStatus.FAILED and self.retry_count < self.max_retries
    
    def calculate_priority_score(self, current_time: datetime) -> float:
        """Calculate dynamic priority score."""
        base_score = {
            Priority.BACKGROUND: 0.0,
            Priority.LOW: 0.25,
            Priority.MEDIUM: 0.5,
            Priority.HIGH: 0.75,
            Priority.CRITICAL: 1.0
        }[self.priority]
        
        # Add waiting time factor
        wait_time = (current_time - self.submission_time).total_seconds() / 3600
        wait_factor = min(wait_time / 24, 0.5)  # Max 0.5 bonus for 24+ hours wait
        
        return base_score + wait_factor


@dataclass
class BaseNode:
    """Base compute node model."""
    id: str
    name: str
    status: NodeStatus = NodeStatus.IDLE
    capabilities: NodeCapabilities = field(default_factory=NodeCapabilities)
    current_load: Dict[ResourceType, float] = field(default_factory=dict)
    assigned_jobs: List[str] = field(default_factory=list)
    reliability_score: float = 1.0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)
    
    def is_available(self) -> bool:
        """Check if node is available for job assignment."""
        return self.status in [NodeStatus.ONLINE, NodeStatus.IDLE]
    
    def get_available_resources(self) -> Dict[ResourceType, float]:
        """Get currently available resources."""
        available = {}
        available[ResourceType.CPU] = self.capabilities.cpu_cores - self.current_load.get(ResourceType.CPU, 0)
        available[ResourceType.GPU] = self.capabilities.gpu_count - self.current_load.get(ResourceType.GPU, 0)
        available[ResourceType.MEMORY] = self.capabilities.memory_gb - self.current_load.get(ResourceType.MEMORY, 0)
        available[ResourceType.STORAGE] = self.capabilities.storage_gb - self.current_load.get(ResourceType.STORAGE, 0)
        available[ResourceType.NETWORK] = self.capabilities.network_bandwidth_gbps - self.current_load.get(ResourceType.NETWORK, 0)
        return available
    
    def can_accommodate(self, job: BaseJob) -> bool:
        """Check if node can accommodate a job's requirements."""
        if not self.is_available():
            return False
        
        available = self.get_available_resources()
        for req in job.resource_requirements:
            if req.amount > available.get(req.resource_type, 0):
                return False
        return True
    
    def allocate_resources(self, job: BaseJob) -> bool:
        """Allocate resources for a job."""
        if not self.can_accommodate(job):
            return False
        
        for req in job.resource_requirements:
            self.current_load[req.resource_type] = self.current_load.get(req.resource_type, 0) + req.amount
        
        self.assigned_jobs.append(job.id)
        if self.status == NodeStatus.IDLE:
            self.status = NodeStatus.BUSY
        return True
    
    def release_resources(self, job: BaseJob) -> None:
        """Release resources allocated to a job."""
        for req in job.resource_requirements:
            self.current_load[req.resource_type] = max(0, self.current_load.get(req.resource_type, 0) - req.amount)
        
        if job.id in self.assigned_jobs:
            self.assigned_jobs.remove(job.id)
        
        if not self.assigned_jobs and self.status == NodeStatus.BUSY:
            self.status = NodeStatus.IDLE


@dataclass
class JobDependency:
    """Represents a dependency between jobs."""
    from_job: str
    to_job: str
    dependency_type: DependencyType = DependencyType.COMPLETION
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.from_job, self.to_job, self.dependency_type))