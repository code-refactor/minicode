"""Resource allocation for the unified task scheduling library."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
import logging

from ..core.models import BaseJob, BaseNode, ResourceRequirement, ResourceType, NodeCapabilities
from ..core.interfaces import ResourceManagerInterface
from ..core.result import Result, ErrorCode


logger = logging.getLogger(__name__)


class AllocationStrategy(str, Enum):
    """Resource allocation strategies."""
    FIRST_FIT = "first_fit"  # Allocate to first node that fits
    BEST_FIT = "best_fit"  # Allocate to node with best resource match
    WORST_FIT = "worst_fit"  # Allocate to node with most available resources
    BALANCED = "balanced"  # Balance resource utilization across nodes
    LOCALITY_AWARE = "locality_aware"  # Consider data locality
    ENERGY_EFFICIENT = "energy_efficient"  # Optimize for energy consumption


class AllocationPolicy(str, Enum):
    """Resource allocation policies."""
    STRICT = "strict"  # Strict resource requirements
    FLEXIBLE = "flexible"  # Allow some resource oversubscription
    OPPORTUNISTIC = "opportunistic"  # Use any available resources
    RESERVED_FIRST = "reserved_first"  # Use reserved resources first


@dataclass
class ResourceAllocation:
    """Represents a resource allocation."""
    allocation_id: str
    job_id: str
    node_id: str
    allocated_resources: Dict[ResourceType, float]
    allocation_time: datetime = field(default_factory=datetime.now)
    expected_duration: Optional[timedelta] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_active(self) -> bool:
        """Check if allocation is currently active."""
        return (self.actual_start_time is not None and 
                self.actual_end_time is None)
    
    def get_duration(self) -> Optional[timedelta]:
        """Get actual duration if completed, expected if not started."""
        if self.actual_end_time and self.actual_start_time:
            return self.actual_end_time - self.actual_start_time
        return self.expected_duration


@dataclass
class AllocationConstraint:
    """Constraints for resource allocation."""
    resource_type: ResourceType
    min_amount: float
    max_amount: Optional[float] = None
    preferred_amount: Optional[float] = None
    required: bool = True
    
    def is_satisfied_by(self, amount: float) -> bool:
        """Check if amount satisfies the constraint."""
        if self.required and amount < self.min_amount:
            return False
        if self.max_amount is not None and amount > self.max_amount:
            return False
        return True


class ResourceAllocator(ResourceManagerInterface):
    """
    Resource allocator for managing job-to-node resource assignments.
    
    This class handles:
    - Resource allocation using various strategies
    - Allocation tracking and management
    - Resource constraint satisfaction
    - Allocation optimization
    """
    
    def __init__(self, strategy: AllocationStrategy = AllocationStrategy.BEST_FIT,
                 policy: AllocationPolicy = AllocationPolicy.STRICT,
                 oversubscription_factor: float = 1.0):
        """
        Initialize the resource allocator.
        
        Args:
            strategy: Allocation strategy to use
            policy: Allocation policy
            oversubscription_factor: Factor for resource oversubscription (1.0 = no oversubscription)
        """
        self.strategy = strategy
        self.policy = policy
        self.oversubscription_factor = oversubscription_factor
        
        # Track active allocations
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.node_allocations: Dict[str, List[str]] = {}  # node_id -> allocation_ids
        self.job_allocations: Dict[str, str] = {}  # job_id -> allocation_id
        
        # Allocation history for optimization
        self.allocation_history: List[ResourceAllocation] = []
        self.failed_allocations: List[Tuple[str, str, datetime]] = []  # (job_id, reason, time)
        
        # Resource utilization tracking
        self.node_utilization: Dict[str, Dict[ResourceType, float]] = {}
        
        logger.info(f"ResourceAllocator initialized with {strategy.value} strategy, {policy.value} policy")
    
    def allocate_resources(self, job: BaseJob, nodes: List[BaseNode]) -> Result[str]:
        """
        Allocate resources for a job.
        
        Args:
            job: Job requiring resources
            nodes: Available nodes
            
        Returns:
            Result containing assigned node ID or error
        """
        if job.id in self.job_allocations:
            return Result.err(f"Job {job.id} already has resource allocation", ErrorCode.ALREADY_EXISTS)
        
        # Filter available nodes
        available_nodes = [node for node in nodes if node.is_available()]
        
        if not available_nodes:
            self.failed_allocations.append((job.id, "No available nodes", datetime.now()))
            return Result.err("No available nodes", ErrorCode.RESOURCE_UNAVAILABLE)
        
        # Find best node based on strategy
        selected_node = self._select_node(job, available_nodes)
        
        if not selected_node:
            reason = "No node can satisfy resource requirements"
            self.failed_allocations.append((job.id, reason, datetime.now()))
            return Result.err(reason, ErrorCode.RESOURCE_UNAVAILABLE)
        
        # Create allocation
        allocation_result = self._create_allocation(job, selected_node)
        
        if not allocation_result.success:
            return allocation_result
        
        allocation = allocation_result.value
        
        # Apply allocation to node
        if not self._apply_allocation(allocation, selected_node):
            return Result.err("Failed to apply allocation to node", ErrorCode.ALLOCATION_FAILED)
        
        # Track allocation
        self.allocations[allocation.allocation_id] = allocation
        self.job_allocations[job.id] = allocation.allocation_id
        
        if selected_node.id not in self.node_allocations:
            self.node_allocations[selected_node.id] = []
        self.node_allocations[selected_node.id].append(allocation.allocation_id)
        
        # Update utilization tracking
        self._update_node_utilization(selected_node)
        
        logger.info(f"Allocated resources for job {job.id} on node {selected_node.id}")
        return Result.ok(selected_node.id)
    
    def release_resources(self, job: BaseJob, node: BaseNode) -> Result[None]:
        """
        Release resources allocated to a job.
        
        Args:
            job: Job releasing resources
            node: Node to release from
            
        Returns:
            Result indicating success or failure
        """
        if job.id not in self.job_allocations:
            return Result.err(f"Job {job.id} has no resource allocation", ErrorCode.NOT_FOUND)
        
        allocation_id = self.job_allocations[job.id]
        allocation = self.allocations.get(allocation_id)
        
        if not allocation:
            return Result.err(f"Allocation {allocation_id} not found", ErrorCode.NOT_FOUND)
        
        if allocation.node_id != node.id:
            return Result.err(f"Job {job.id} not allocated to node {node.id}", ErrorCode.INVALID_OPERATION)
        
        # Release resources from node
        self._release_allocation(allocation, node)
        
        # Mark allocation as completed
        allocation.actual_end_time = datetime.now()
        
        # Move to history
        self.allocation_history.append(allocation)
        
        # Remove from active tracking
        del self.allocations[allocation_id]
        del self.job_allocations[job.id]
        
        if node.id in self.node_allocations:
            self.node_allocations[node.id].remove(allocation_id)
            if not self.node_allocations[node.id]:
                del self.node_allocations[node.id]
        
        # Update utilization tracking
        self._update_node_utilization(node)
        
        logger.info(f"Released resources for job {job.id} from node {node.id}")
        return Result.ok(None)
    
    def get_resource_availability(self, nodes: List[BaseNode]) -> Dict[str, Dict[str, float]]:
        """
        Get current resource availability across nodes.
        
        Args:
            nodes: Nodes to check
            
        Returns:
            Mapping of node IDs to available resources
        """
        availability = {}
        
        for node in nodes:
            available = node.get_available_resources()
            availability[node.id] = {
                resource_type.value: amount
                for resource_type, amount in available.items()
            }
        
        return availability
    
    def reserve_resources(self, job: BaseJob, node: BaseNode, 
                         start_time: datetime, duration: float) -> Result[str]:
        """
        Reserve resources for future use.
        
        Args:
            job: Job requiring reservation
            node: Node to reserve on
            start_time: Reservation start time
            duration: Reservation duration in hours
            
        Returns:
            Result containing reservation ID or error
        """
        # Check if node can accommodate the job at the future time
        if not self._can_reserve(job, node, start_time, duration):
            return Result.err("Cannot reserve resources at requested time", ErrorCode.RESOURCE_UNAVAILABLE)
        
        # Create reservation allocation
        allocation = ResourceAllocation(
            allocation_id=f"reservation_{job.id}_{start_time.isoformat()}",
            job_id=job.id,
            node_id=node.id,
            allocated_resources={req.resource_type: req.amount for req in job.resource_requirements},
            allocation_time=datetime.now(),
            expected_duration=timedelta(hours=duration),
            metadata={"reservation_start": start_time, "type": "reservation"}
        )
        
        # Store reservation
        self.allocations[allocation.allocation_id] = allocation
        
        if node.id not in self.node_allocations:
            self.node_allocations[node.id] = []
        self.node_allocations[node.id].append(allocation.allocation_id)
        
        logger.info(f"Reserved resources for job {job.id} on node {node.id} "
                   f"from {start_time} for {duration} hours")
        
        return Result.ok(allocation.allocation_id)
    
    def get_allocation_info(self, job_id: str) -> Optional[ResourceAllocation]:
        """Get allocation information for a job."""
        allocation_id = self.job_allocations.get(job_id)
        if allocation_id:
            return self.allocations.get(allocation_id)
        return None
    
    def get_node_allocations(self, node_id: str) -> List[ResourceAllocation]:
        """Get all allocations for a specific node."""
        allocation_ids = self.node_allocations.get(node_id, [])
        return [self.allocations[aid] for aid in allocation_ids if aid in self.allocations]
    
    def get_utilization_stats(self) -> Dict[str, Any]:
        """Get resource utilization statistics."""
        stats = {
            "active_allocations": len(self.allocations),
            "total_allocations": len(self.allocation_history) + len(self.allocations),
            "failed_allocations": len(self.failed_allocations),
            "nodes_in_use": len(self.node_allocations),
            "average_utilization": {},
            "peak_utilization": {}
        }
        
        # Calculate utilization statistics
        if self.node_utilization:
            resource_utils = {}
            for node_id, util in self.node_utilization.items():
                for resource_type, utilization in util.items():
                    if resource_type not in resource_utils:
                        resource_utils[resource_type] = []
                    resource_utils[resource_type].append(utilization)
            
            for resource_type, utils in resource_utils.items():
                stats["average_utilization"][resource_type.value] = sum(utils) / len(utils)
                stats["peak_utilization"][resource_type.value] = max(utils)
        
        return stats
    
    def _select_node(self, job: BaseJob, nodes: List[BaseNode]) -> Optional[BaseNode]:
        """Select the best node for a job based on allocation strategy."""
        suitable_nodes = []
        
        # Filter nodes that can accommodate the job
        for node in nodes:
            if self._can_accommodate(job, node):
                score = self._calculate_node_score(job, node)
                suitable_nodes.append((score, node))
        
        if not suitable_nodes:
            return None
        
        # Sort based on strategy
        if self.strategy == AllocationStrategy.BEST_FIT:
            # Best fit - minimize wasted resources
            suitable_nodes.sort(key=lambda x: x[0])
        elif self.strategy == AllocationStrategy.WORST_FIT:
            # Worst fit - maximize remaining resources
            suitable_nodes.sort(key=lambda x: x[0], reverse=True)
        elif self.strategy == AllocationStrategy.BALANCED:
            # Balanced - prefer nodes with balanced utilization
            suitable_nodes.sort(key=lambda x: (x[0], x[1].reliability_score), reverse=True)
        else:  # FIRST_FIT
            # First fit - first suitable node
            pass
        
        return suitable_nodes[0][1]
    
    def _can_accommodate(self, job: BaseJob, node: BaseNode) -> bool:
        """Check if a node can accommodate a job's requirements."""
        # Basic capability check
        if not node.can_accommodate(job):
            return False
        
        # Policy-specific checks
        if self.policy == AllocationPolicy.STRICT:
            # Strict - must satisfy all requirements exactly
            available = node.get_available_resources()
            for req in job.resource_requirements:
                if available.get(req.resource_type, 0) < req.amount:
                    return False
        elif self.policy == AllocationPolicy.FLEXIBLE:
            # Flexible - allow some oversubscription
            available = node.get_available_resources()
            for req in job.resource_requirements:
                max_allowed = available.get(req.resource_type, 0) * self.oversubscription_factor
                if req.amount > max_allowed:
                    return False
        # OPPORTUNISTIC policy accepts any node with basic capability
        
        return True
    
    def _calculate_node_score(self, job: BaseJob, node: BaseNode) -> float:
        """Calculate a score for node selection."""
        score = 0.0
        
        # Base score from reliability
        score += node.reliability_score * 10
        
        # Resource fit score
        available = node.get_available_resources()
        total_available = sum(available.values())
        total_required = sum(req.amount for req in job.resource_requirements)
        
        if total_available > 0:
            utilization = total_required / total_available
            # Prefer moderate utilization (50-80%)
            if 0.5 <= utilization <= 0.8:
                score += 20
            elif 0.3 <= utilization < 0.5:
                score += 10
            elif utilization > 0.8:
                score += 5
        
        # Load balancing - prefer less loaded nodes
        current_load = len(node.assigned_jobs)
        score -= current_load * 2
        
        # Specialization bonus
        for req in job.resource_requirements:
            if req.resource_type == ResourceType.GPU and node.capabilities.gpu_count > 0:
                score += 15
            elif req.resource_type == ResourceType.CPU and node.capabilities.cpu_cores >= req.amount:
                score += 5
        
        return score
    
    def _create_allocation(self, job: BaseJob, node: BaseNode) -> Result[ResourceAllocation]:
        """Create a resource allocation for a job."""
        allocation_id = f"alloc_{job.id}_{datetime.now().isoformat()}"
        
        allocated_resources = {}
        for req in job.resource_requirements:
            allocated_resources[req.resource_type] = req.amount
        
        allocation = ResourceAllocation(
            allocation_id=allocation_id,
            job_id=job.id,
            node_id=node.id,
            allocated_resources=allocated_resources,
            expected_duration=job.estimated_duration,
            priority=job.calculate_priority_score(datetime.now())
        )
        
        return Result.ok(allocation)
    
    def _apply_allocation(self, allocation: ResourceAllocation, node: BaseNode) -> bool:
        """Apply an allocation to a node."""
        # Convert ResourceAllocation to job-like object for node.allocate_resources
        dummy_job = type('DummyJob', (), {
            'id': allocation.job_id,
            'resource_requirements': [
                type('Req', (), {
                    'resource_type': rt,
                    'amount': amount
                })()
                for rt, amount in allocation.allocated_resources.items()
            ]
        })()
        
        if node.allocate_resources(dummy_job):
            allocation.actual_start_time = datetime.now()
            return True
        
        return False
    
    def _release_allocation(self, allocation: ResourceAllocation, node: BaseNode):
        """Release an allocation from a node."""
        # Convert ResourceAllocation back to job-like object
        dummy_job = type('DummyJob', (), {
            'id': allocation.job_id,
            'resource_requirements': [
                type('Req', (), {
                    'resource_type': rt,
                    'amount': amount
                })()
                for rt, amount in allocation.allocated_resources.items()
            ]
        })()
        
        node.release_resources(dummy_job)
    
    def _can_reserve(self, job: BaseJob, node: BaseNode, 
                    start_time: datetime, duration: float) -> bool:
        """Check if resources can be reserved."""
        # For now, simple check - assume reservation is possible if node has capacity
        # In a full implementation, this would check future allocations and reservations
        return node.can_accommodate(job)
    
    def _update_node_utilization(self, node: BaseNode):
        """Update utilization tracking for a node."""
        total_capacity = {}
        used_resources = {}
        
        # Calculate total capacity
        total_capacity[ResourceType.CPU] = node.capabilities.cpu_cores
        total_capacity[ResourceType.GPU] = node.capabilities.gpu_count
        total_capacity[ResourceType.MEMORY] = node.capabilities.memory_gb
        total_capacity[ResourceType.STORAGE] = node.capabilities.storage_gb
        total_capacity[ResourceType.NETWORK] = node.capabilities.network_bandwidth_gbps
        
        # Calculate current usage
        used_resources = node.current_load.copy()
        
        # Calculate utilization percentages
        utilization = {}
        for resource_type in ResourceType:
            capacity = total_capacity.get(resource_type, 0)
            used = used_resources.get(resource_type, 0)
            if capacity > 0:
                utilization[resource_type] = used / capacity
            else:
                utilization[resource_type] = 0.0
        
        self.node_utilization[node.id] = utilization