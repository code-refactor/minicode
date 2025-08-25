"""Resource partitioning for the unified task scheduling library."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
import logging

from ..core.models import BaseNode, ResourceType, NodeCapabilities
from ..core.result import Result, ErrorCode


logger = logging.getLogger(__name__)


class PartitionStrategy(str, Enum):
    """Resource partitioning strategies."""
    FIXED = "fixed"  # Fixed resource allocation per partition
    DYNAMIC = "dynamic"  # Dynamic allocation based on demand
    PROPORTIONAL = "proportional"  # Proportional to partition weights
    PRIORITY_BASED = "priority_based"  # Based on partition priorities
    WORKLOAD_AWARE = "workload_aware"  # Adaptive to workload characteristics


class PartitionType(str, Enum):
    """Types of resource partitions."""
    SHARED = "shared"  # Resources can be shared between jobs
    EXCLUSIVE = "exclusive"  # Exclusive resource allocation
    PREEMPTIBLE = "preemptible"  # Can be preempted by higher priority partitions
    GUARANTEED = "guaranteed"  # Guaranteed minimum resources


@dataclass
class ResourcePartition:
    """A resource partition definition."""
    partition_id: str
    name: str
    partition_type: PartitionType
    resource_allocation: Dict[ResourceType, float]  # Maximum resources per type
    guaranteed_allocation: Dict[ResourceType, float]  # Minimum guaranteed resources
    node_ids: Set[str] = field(default_factory=set)  # Nodes belonging to this partition
    priority: int = 0  # Partition priority (higher = more important)
    weight: float = 1.0  # Weight for proportional allocation
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_time: datetime = field(default_factory=datetime.now)
    
    def get_total_resources(self, resource_type: ResourceType) -> float:
        """Get total allocated resources of a specific type."""
        return self.resource_allocation.get(resource_type, 0.0)
    
    def get_guaranteed_resources(self, resource_type: ResourceType) -> float:
        """Get guaranteed resources of a specific type."""
        return self.guaranteed_allocation.get(resource_type, 0.0)
    
    def can_accommodate_resources(self, required_resources: Dict[ResourceType, float]) -> bool:
        """Check if partition can accommodate the required resources."""
        for resource_type, amount in required_resources.items():
            if amount > self.resource_allocation.get(resource_type, 0.0):
                return False
        return True


@dataclass
class PartitionUsage:
    """Current usage of a resource partition."""
    partition_id: str
    used_resources: Dict[ResourceType, float] = field(default_factory=dict)
    active_jobs: Set[str] = field(default_factory=set)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_usage_ratio(self, partition: ResourcePartition, resource_type: ResourceType) -> float:
        """Get usage ratio for a specific resource type."""
        allocated = partition.get_total_resources(resource_type)
        used = self.used_resources.get(resource_type, 0.0)
        return used / allocated if allocated > 0 else 0.0
    
    def get_available_resources(self, partition: ResourcePartition, 
                               resource_type: ResourceType) -> float:
        """Get available resources of a specific type."""
        allocated = partition.get_total_resources(resource_type)
        used = self.used_resources.get(resource_type, 0.0)
        return max(0.0, allocated - used)


class ResourcePartitioner:
    """
    Resource partitioner for managing resource allocation across different partitions.
    
    This class handles:
    - Creating and managing resource partitions
    - Dynamic resource allocation between partitions
    - Resource usage tracking and optimization
    - Partition-aware scheduling decisions
    """
    
    def __init__(self, strategy: PartitionStrategy = PartitionStrategy.PROPORTIONAL,
                 rebalance_interval: timedelta = timedelta(minutes=30),
                 oversubscription_factor: float = 1.1):
        """
        Initialize the resource partitioner.
        
        Args:
            strategy: Partitioning strategy to use
            rebalance_interval: Interval for rebalancing partitions
            oversubscription_factor: Factor for allowing resource oversubscription
        """
        self.strategy = strategy
        self.rebalance_interval = rebalance_interval
        self.oversubscription_factor = oversubscription_factor
        
        # Partition management
        self.partitions: Dict[str, ResourcePartition] = {}
        self.partition_usage: Dict[str, PartitionUsage] = {}
        
        # Node assignment
        self.node_to_partition: Dict[str, str] = {}  # node_id -> partition_id
        self.partition_to_nodes: Dict[str, Set[str]] = {}  # partition_id -> set of node_ids
        
        # Resource tracking
        self.total_resources: Dict[ResourceType, float] = {}
        self.last_rebalance: datetime = datetime.now()
        self.rebalance_history: List[Dict[str, Any]] = []
        
        logger.info(f"ResourcePartitioner initialized with {strategy.value} strategy")
    
    def create_partition(self, partition_id: str, name: str, 
                        partition_type: PartitionType,
                        resource_allocation: Dict[ResourceType, float],
                        guaranteed_allocation: Optional[Dict[ResourceType, float]] = None,
                        priority: int = 0, weight: float = 1.0,
                        constraints: Optional[Dict[str, Any]] = None) -> Result[ResourcePartition]:
        """
        Create a new resource partition.
        
        Args:
            partition_id: Unique identifier for the partition
            name: Human-readable name
            partition_type: Type of partition
            resource_allocation: Maximum resource allocation
            guaranteed_allocation: Minimum guaranteed resources
            priority: Partition priority
            weight: Weight for proportional allocation
            constraints: Additional constraints
            
        Returns:
            Result containing the created partition or error
        """
        if partition_id in self.partitions:
            return Result.err(f"Partition {partition_id} already exists", ErrorCode.ALREADY_EXISTS)
        
        # Validate resource allocation
        for resource_type, amount in resource_allocation.items():
            if amount < 0:
                return Result.err(f"Resource allocation cannot be negative: {resource_type.value}={amount}", 
                                ErrorCode.INVALID_PARAMETER)
        
        # Set default guaranteed allocation
        if guaranteed_allocation is None:
            guaranteed_allocation = {rt: amount * 0.5 for rt, amount in resource_allocation.items()}
        
        # Validate guaranteed allocation
        for resource_type, guaranteed in guaranteed_allocation.items():
            allocated = resource_allocation.get(resource_type, 0.0)
            if guaranteed > allocated:
                return Result.err(f"Guaranteed allocation cannot exceed total allocation for {resource_type.value}", 
                                ErrorCode.INVALID_PARAMETER)
        
        # Create partition
        partition = ResourcePartition(
            partition_id=partition_id,
            name=name,
            partition_type=partition_type,
            resource_allocation=resource_allocation.copy(),
            guaranteed_allocation=guaranteed_allocation.copy(),
            priority=priority,
            weight=weight,
            constraints=constraints or {}
        )
        
        # Store partition
        self.partitions[partition_id] = partition
        self.partition_usage[partition_id] = PartitionUsage(partition_id=partition_id)
        self.partition_to_nodes[partition_id] = set()
        
        logger.info(f"Created partition {partition_id} ({name}) with type {partition_type.value}")
        return Result.ok(partition)
    
    def delete_partition(self, partition_id: str, force: bool = False) -> Result[ResourcePartition]:
        """
        Delete a resource partition.
        
        Args:
            partition_id: ID of partition to delete
            force: Force deletion even if partition has active jobs
            
        Returns:
            Result containing the deleted partition or error
        """
        if partition_id not in self.partitions:
            return Result.err(f"Partition {partition_id} not found", ErrorCode.NOT_FOUND)
        
        partition = self.partitions[partition_id]
        usage = self.partition_usage[partition_id]
        
        # Check if partition has active jobs
        if usage.active_jobs and not force:
            return Result.err(f"Partition has {len(usage.active_jobs)} active jobs", 
                            ErrorCode.INVALID_OPERATION)
        
        # Remove nodes from partition
        for node_id in partition.node_ids.copy():
            self.remove_node_from_partition(partition_id, node_id)
        
        # Clean up
        del self.partitions[partition_id]
        del self.partition_usage[partition_id]
        del self.partition_to_nodes[partition_id]
        
        logger.info(f"Deleted partition {partition_id}")
        return Result.ok(partition)
    
    def assign_node_to_partition(self, node_id: str, partition_id: str) -> Result[None]:
        """
        Assign a node to a specific partition.
        
        Args:
            node_id: ID of node to assign
            partition_id: ID of target partition
            
        Returns:
            Result indicating success or failure
        """
        if partition_id not in self.partitions:
            return Result.err(f"Partition {partition_id} not found", ErrorCode.NOT_FOUND)
        
        # Remove from current partition if assigned
        current_partition = self.node_to_partition.get(node_id)
        if current_partition:
            self.remove_node_from_partition(current_partition, node_id)
        
        # Assign to new partition
        self.partitions[partition_id].node_ids.add(node_id)
        self.node_to_partition[node_id] = partition_id
        self.partition_to_nodes[partition_id].add(node_id)
        
        logger.info(f"Assigned node {node_id} to partition {partition_id}")
        return Result.ok(None)
    
    def remove_node_from_partition(self, partition_id: str, node_id: str) -> Result[None]:
        """
        Remove a node from a partition.
        
        Args:
            partition_id: ID of partition
            node_id: ID of node to remove
            
        Returns:
            Result indicating success or failure
        """
        if partition_id not in self.partitions:
            return Result.err(f"Partition {partition_id} not found", ErrorCode.NOT_FOUND)
        
        partition = self.partitions[partition_id]
        
        if node_id not in partition.node_ids:
            return Result.err(f"Node {node_id} not in partition {partition_id}", ErrorCode.NOT_FOUND)
        
        # Remove from partition
        partition.node_ids.discard(node_id)
        self.partition_to_nodes[partition_id].discard(node_id)
        
        # Remove from node mapping
        if self.node_to_partition.get(node_id) == partition_id:
            del self.node_to_partition[node_id]
        
        logger.info(f"Removed node {node_id} from partition {partition_id}")
        return Result.ok(None)
    
    def get_partition_for_node(self, node_id: str) -> Optional[str]:
        """Get the partition ID for a specific node."""
        return self.node_to_partition.get(node_id)
    
    def get_nodes_in_partition(self, partition_id: str) -> Set[str]:
        """Get all nodes in a specific partition."""
        return self.partition_to_nodes.get(partition_id, set()).copy()
    
    def allocate_job_to_partition(self, job_id: str, partition_id: str,
                                 resource_requirements: Dict[ResourceType, float]) -> Result[None]:
        """
        Allocate a job's resources to a partition.
        
        Args:
            job_id: ID of job to allocate
            partition_id: Target partition
            resource_requirements: Required resources
            
        Returns:
            Result indicating success or failure
        """
        if partition_id not in self.partitions:
            return Result.err(f"Partition {partition_id} not found", ErrorCode.NOT_FOUND)
        
        partition = self.partitions[partition_id]
        usage = self.partition_usage[partition_id]
        
        # Check if partition can accommodate the job
        if not partition.can_accommodate_resources(resource_requirements):
            return Result.err(f"Partition cannot accommodate required resources", 
                            ErrorCode.RESOURCE_UNAVAILABLE)
        
        # Check current usage
        for resource_type, required in resource_requirements.items():
            available = usage.get_available_resources(partition, resource_type)
            if required > available * self.oversubscription_factor:
                return Result.err(f"Insufficient {resource_type.value} resources in partition", 
                                ErrorCode.RESOURCE_UNAVAILABLE)
        
        # Allocate resources
        for resource_type, amount in resource_requirements.items():
            current_usage = usage.used_resources.get(resource_type, 0.0)
            usage.used_resources[resource_type] = current_usage + amount
        
        # Track job
        usage.active_jobs.add(job_id)
        usage.last_updated = datetime.now()
        
        logger.info(f"Allocated job {job_id} to partition {partition_id}")
        return Result.ok(None)
    
    def deallocate_job_from_partition(self, job_id: str, partition_id: str,
                                     resource_requirements: Dict[ResourceType, float]) -> Result[None]:
        """
        Deallocate a job's resources from a partition.
        
        Args:
            job_id: ID of job to deallocate
            partition_id: Source partition
            resource_requirements: Resources to release
            
        Returns:
            Result indicating success or failure
        """
        if partition_id not in self.partitions:
            return Result.err(f"Partition {partition_id} not found", ErrorCode.NOT_FOUND)
        
        usage = self.partition_usage[partition_id]
        
        if job_id not in usage.active_jobs:
            return Result.err(f"Job {job_id} not allocated to partition {partition_id}", 
                            ErrorCode.NOT_FOUND)
        
        # Deallocate resources
        for resource_type, amount in resource_requirements.items():
            current_usage = usage.used_resources.get(resource_type, 0.0)
            usage.used_resources[resource_type] = max(0.0, current_usage - amount)
        
        # Remove job tracking
        usage.active_jobs.discard(job_id)
        usage.last_updated = datetime.now()
        
        logger.info(f"Deallocated job {job_id} from partition {partition_id}")
        return Result.ok(None)
    
    def rebalance_partitions(self, nodes: List[BaseNode]) -> Result[Dict[str, Any]]:
        """
        Rebalance resource allocations across partitions.
        
        Args:
            nodes: Current node list for calculating total resources
            
        Returns:
            Result containing rebalancing information
        """
        current_time = datetime.now()
        
        if current_time - self.last_rebalance < self.rebalance_interval:
            return Result.ok({"message": "Rebalancing not needed yet"})
        
        # Calculate total available resources
        self._update_total_resources(nodes)
        
        # Apply rebalancing based on strategy
        if self.strategy == PartitionStrategy.DYNAMIC:
            result = self._dynamic_rebalance()
        elif self.strategy == PartitionStrategy.PROPORTIONAL:
            result = self._proportional_rebalance()
        elif self.strategy == PartitionStrategy.PRIORITY_BASED:
            result = self._priority_based_rebalance()
        elif self.strategy == PartitionStrategy.WORKLOAD_AWARE:
            result = self._workload_aware_rebalance()
        else:  # FIXED - no rebalancing
            result = {"message": "Fixed allocation strategy - no rebalancing"}
        
        self.last_rebalance = current_time
        self.rebalance_history.append({
            "timestamp": current_time,
            "strategy": self.strategy.value,
            "result": result
        })
        
        logger.info(f"Rebalanced partitions using {self.strategy.value} strategy")
        return Result.ok(result)
    
    def get_partition_statistics(self) -> Dict[str, Any]:
        """Get comprehensive partition statistics."""
        stats = {
            "total_partitions": len(self.partitions),
            "partitions": {},
            "total_resources": dict(self.total_resources),
            "strategy": self.strategy.value,
            "last_rebalance": self.last_rebalance.isoformat()
        }
        
        for partition_id, partition in self.partitions.items():
            usage = self.partition_usage[partition_id]
            
            partition_stats = {
                "name": partition.name,
                "type": partition.partition_type.value,
                "priority": partition.priority,
                "weight": partition.weight,
                "node_count": len(partition.node_ids),
                "active_jobs": len(usage.active_jobs),
                "resource_allocation": {rt.value: amount for rt, amount in partition.resource_allocation.items()},
                "resource_usage": {rt.value: amount for rt, amount in usage.used_resources.items()},
                "utilization": {}
            }
            
            # Calculate utilization ratios
            for resource_type in ResourceType:
                allocated = partition.get_total_resources(resource_type)
                used = usage.used_resources.get(resource_type, 0.0)
                partition_stats["utilization"][resource_type.value] = used / allocated if allocated > 0 else 0.0
            
            stats["partitions"][partition_id] = partition_stats
        
        return stats
    
    def suggest_partition_for_job(self, resource_requirements: Dict[ResourceType, float],
                                 priority: int = 0) -> Optional[str]:
        """
        Suggest the best partition for a job based on requirements.
        
        Args:
            resource_requirements: Job's resource requirements
            priority: Job priority
            
        Returns:
            Partition ID or None if no suitable partition
        """
        suitable_partitions = []
        
        for partition_id, partition in self.partitions.items():
            usage = self.partition_usage[partition_id]
            
            # Check if partition can accommodate the job
            can_fit = True
            for resource_type, required in resource_requirements.items():
                available = usage.get_available_resources(partition, resource_type)
                if required > available * self.oversubscription_factor:
                    can_fit = False
                    break
            
            if can_fit:
                # Calculate suitability score
                score = self._calculate_partition_score(partition, usage, resource_requirements, priority)
                suitable_partitions.append((score, partition_id))
        
        if suitable_partitions:
            # Return partition with highest score
            suitable_partitions.sort(key=lambda x: x[0], reverse=True)
            return suitable_partitions[0][1]
        
        return None
    
    def _update_total_resources(self, nodes: List[BaseNode]):
        """Update total resource tracking."""
        total = {}
        for resource_type in ResourceType:
            total[resource_type] = 0.0
        
        for node in nodes:
            total[ResourceType.CPU] += node.capabilities.cpu_cores
            total[ResourceType.GPU] += node.capabilities.gpu_count
            total[ResourceType.MEMORY] += node.capabilities.memory_gb
            total[ResourceType.STORAGE] += node.capabilities.storage_gb
            total[ResourceType.NETWORK] += node.capabilities.network_bandwidth_gbps
        
        self.total_resources = total
    
    def _dynamic_rebalance(self) -> Dict[str, Any]:
        """Perform dynamic rebalancing based on current usage."""
        changes = {}
        
        for partition_id, partition in self.partitions.items():
            usage = self.partition_usage[partition_id]
            
            # Calculate new allocation based on usage patterns
            for resource_type in ResourceType:
                current_allocation = partition.resource_allocation.get(resource_type, 0.0)
                current_usage = usage.used_resources.get(resource_type, 0.0)
                utilization = current_usage / current_allocation if current_allocation > 0 else 0.0
                
                # Adjust allocation based on utilization
                if utilization > 0.8:  # High utilization - increase allocation
                    new_allocation = current_allocation * 1.2
                elif utilization < 0.3:  # Low utilization - decrease allocation
                    new_allocation = current_allocation * 0.9
                else:
                    new_allocation = current_allocation
                
                # Ensure minimum guaranteed allocation
                guaranteed = partition.guaranteed_allocation.get(resource_type, 0.0)
                new_allocation = max(new_allocation, guaranteed)
                
                if abs(new_allocation - current_allocation) > 0.01:  # Significant change
                    changes[f"{partition_id}_{resource_type.value}"] = {
                        "old": current_allocation,
                        "new": new_allocation
                    }
                    partition.resource_allocation[resource_type] = new_allocation
        
        return {"changes": changes, "rebalance_type": "dynamic"}
    
    def _proportional_rebalance(self) -> Dict[str, Any]:
        """Perform proportional rebalancing based on partition weights."""
        changes = {}
        total_weight = sum(p.weight for p in self.partitions.values())
        
        for resource_type in ResourceType:
            total_available = self.total_resources.get(resource_type, 0.0)
            
            for partition_id, partition in self.partitions.items():
                proportion = partition.weight / total_weight if total_weight > 0 else 0.0
                new_allocation = total_available * proportion
                
                # Ensure minimum guaranteed allocation
                guaranteed = partition.guaranteed_allocation.get(resource_type, 0.0)
                new_allocation = max(new_allocation, guaranteed)
                
                old_allocation = partition.resource_allocation.get(resource_type, 0.0)
                if abs(new_allocation - old_allocation) > 0.01:
                    changes[f"{partition_id}_{resource_type.value}"] = {
                        "old": old_allocation,
                        "new": new_allocation
                    }
                    partition.resource_allocation[resource_type] = new_allocation
        
        return {"changes": changes, "rebalance_type": "proportional"}
    
    def _priority_based_rebalance(self) -> Dict[str, Any]:
        """Perform priority-based rebalancing."""
        changes = {}
        
        # Sort partitions by priority
        sorted_partitions = sorted(self.partitions.values(), key=lambda p: p.priority, reverse=True)
        
        for resource_type in ResourceType:
            remaining_resources = self.total_resources.get(resource_type, 0.0)
            
            # First, allocate guaranteed resources
            for partition in sorted_partitions:
                guaranteed = partition.guaranteed_allocation.get(resource_type, 0.0)
                remaining_resources -= guaranteed
            
            # Then, allocate remaining resources by priority
            for partition in sorted_partitions:
                usage = self.partition_usage[partition.partition_id]
                current_usage = usage.used_resources.get(resource_type, 0.0)
                
                # Higher priority partitions get more resources
                priority_factor = partition.priority / max(1, sum(p.priority for p in sorted_partitions))
                additional_allocation = remaining_resources * priority_factor
                
                guaranteed = partition.guaranteed_allocation.get(resource_type, 0.0)
                new_allocation = guaranteed + additional_allocation
                
                old_allocation = partition.resource_allocation.get(resource_type, 0.0)
                if abs(new_allocation - old_allocation) > 0.01:
                    changes[f"{partition.partition_id}_{resource_type.value}"] = {
                        "old": old_allocation,
                        "new": new_allocation
                    }
                    partition.resource_allocation[resource_type] = new_allocation
        
        return {"changes": changes, "rebalance_type": "priority_based"}
    
    def _workload_aware_rebalance(self) -> Dict[str, Any]:
        """Perform workload-aware rebalancing."""
        # This is a simplified implementation
        # In practice, this would analyze job patterns, resource demands, etc.
        changes = {}
        
        for partition_id, partition in self.partitions.items():
            usage = self.partition_usage[partition_id]
            
            # Analyze workload characteristics
            job_count = len(usage.active_jobs)
            
            for resource_type in ResourceType:
                current_allocation = partition.resource_allocation.get(resource_type, 0.0)
                current_usage = usage.used_resources.get(resource_type, 0.0)
                
                # Adjust based on job density and usage patterns
                if job_count > 0:
                    usage_per_job = current_usage / job_count
                    # More jobs might need more resources
                    adjustment_factor = 1.0 + (job_count * 0.1)  # 10% per job
                else:
                    adjustment_factor = 0.8  # Reduce allocation if no jobs
                
                new_allocation = current_allocation * adjustment_factor
                
                # Ensure minimum guaranteed allocation
                guaranteed = partition.guaranteed_allocation.get(resource_type, 0.0)
                new_allocation = max(new_allocation, guaranteed)
                
                if abs(new_allocation - current_allocation) > 0.01:
                    changes[f"{partition_id}_{resource_type.value}"] = {
                        "old": current_allocation,
                        "new": new_allocation
                    }
                    partition.resource_allocation[resource_type] = new_allocation
        
        return {"changes": changes, "rebalance_type": "workload_aware"}
    
    def _calculate_partition_score(self, partition: ResourcePartition, usage: PartitionUsage,
                                  resource_requirements: Dict[ResourceType, float],
                                  job_priority: int) -> float:
        """Calculate suitability score for a partition."""
        score = 0.0
        
        # Priority match bonus
        if job_priority >= partition.priority:
            score += 10
        
        # Resource efficiency score
        total_required = sum(resource_requirements.values())
        total_available = sum(usage.get_available_resources(partition, rt) 
                             for rt in ResourceType)
        
        if total_available > 0:
            efficiency = total_required / total_available
            if 0.5 <= efficiency <= 0.8:  # Sweet spot
                score += 20
            elif 0.3 <= efficiency < 0.5:
                score += 10
            elif efficiency > 0.8:
                score += 5
        
        # Load balancing - prefer less utilized partitions
        avg_utilization = sum(usage.get_usage_ratio(partition, rt) for rt in ResourceType) / len(ResourceType)
        score += (1.0 - avg_utilization) * 10
        
        # Partition type bonus
        if partition.partition_type == PartitionType.SHARED:
            score += 5  # Prefer shared partitions for general workloads
        
        return score