"""Unified task scheduling library - Common components."""

# Core components
from .core import *

# Scheduling components
from .scheduling import (
    PriorityManager, BaseQueueManager, FairShareQueueManager, BaseScheduler
)

# Resource management components  
from .resource_management import (
    ResourceAllocator, NodeManager, ResourceReservationManager, ResourcePartitioner
)

# Dependency tracking components
from .dependency_tracking import (
    DependencyGraph, DependencyResolver
)

# Failure handling components
from .failure_handling import (
    FailureDetector
)

# Utility components
from .utils import (
    Timer, generate_uuid, generate_job_id, generate_node_id, 
    format_duration, now
)

__version__ = "1.0.0"

__all__ = [
    # Core
    'BaseJob', 'BaseNode', 'Priority', 'JobStatus', 'NodeStatus',
    'ResourceType', 'DependencyType', 'Result', 'ErrorCode',
    
    # Scheduling
    'PriorityManager', 'BaseQueueManager', 'FairShareQueueManager', 'BaseScheduler',
    
    # Resource Management
    'ResourceAllocator', 'NodeManager', 'ResourceReservationManager', 'ResourcePartitioner',
    
    # Dependency Tracking
    'DependencyGraph', 'DependencyResolver',
    
    # Failure Handling
    'FailureDetector',
    
    # Utilities
    'Timer', 'generate_uuid', 'generate_job_id', 'generate_node_id',
    'format_duration', 'now'
]
