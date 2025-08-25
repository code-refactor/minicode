"""Resource partitioning system for the Render Farm Manager."""

import logging
import math
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any

# Import common resource management components
from common.resource_management.partitioner import ResourcePartitioner as CommonResourcePartitioner
from common.core.models import BaseJob, BaseNode, ResourceType
from common.core.result import Result, ErrorCode
from render_farm_manager.core.interfaces import ResourceManagerInterface
from render_farm_manager.core.models import (
    Client,
    RenderJob,
    RenderJobStatus,
    RenderNode,
    ResourceAllocation,
)
from render_farm_manager.utils.logging import AuditLogger, PerformanceMonitor


class ResourcePartitioner(CommonResourcePartitioner, ResourceManagerInterface):
    """
    Resource partitioning system that manages resource allocation among clients.
    
    This system ensures that clients receive their guaranteed minimum resources
    while allowing flexible overflow usage when capacity is available.
    """
    
    def __init__(
        self,
        audit_logger: AuditLogger,
        performance_monitor: PerformanceMonitor,
        allow_borrowing: bool = True,
        borrowing_limit_percentage: float = 50.0,
    ):
        """
        Initialize the resource partitioner.
        
        Args:
            audit_logger: Logger for audit trail events
            performance_monitor: Monitor for tracking partitioner performance
            allow_borrowing: Whether to allow resource borrowing between clients
            borrowing_limit_percentage: Maximum percentage of guaranteed resources
                that can be borrowed from a client
        """
        # Initialize common resource partitioner with dynamic strategy
        from common.resource_management.partitioner import PartitionStrategy
        from datetime import timedelta
        super().__init__(
            strategy=PartitionStrategy.DYNAMIC,
            rebalance_interval=timedelta(minutes=30),
            oversubscription_factor=1.1
        )
        
        self.audit_logger = audit_logger
        self.performance_monitor = performance_monitor
        self.allow_borrowing = allow_borrowing
        self.borrowing_limit_percentage = borrowing_limit_percentage
        self.logger = logging.getLogger("render_farm.resource_partitioner")
        
        # Added to maintain state for tests
        # Render-specific state tracking
        self.client_resource_history: Dict[str, List[float]] = {}
        self.borrowing_transactions: List[Dict[str, Any]] = []
        self.clients: Dict[str, Client] = {}
        self.nodes: Dict[str, RenderNode] = {}
        self.client_demand: Dict[str, float] = {}
        self.current_allocations: Dict[str, ResourceAllocation] = {}
    
    def add_client(self, client: Client) -> None:
        """
        Add a client to the resource partitioner.
        
        Args:
            client: The client to add
        """
        self.clients[client.id] = client
        self.client_demand[client.id] = 0.0
        
        self.audit_logger.log_event(
            "client_added_to_partitioner",
            f"Client {client.id} ({client.name}) added to resource partitioner",
            client_id=client.id,
            client_name=client.name,
            sla_tier=client.sla_tier,
            guaranteed_resources=client.guaranteed_resources,
            max_resources=client.max_resources,
        )
    
    def add_node(self, node: RenderNode) -> None:
        """
        Add a node to the resource partitioner.
        
        Args:
            node: The node to add
        """
        self.nodes[node.id] = node
        
        self.audit_logger.log_event(
            "node_added_to_partitioner",
            f"Node {node.id} ({node.name}) added to resource partitioner",
            node_id=node.id,
            node_name=node.name,
            node_status=node.status,
        )
    
    def update_client_demand(self, client_id: str, demand_percentage: float) -> None:
        """
        Update the demand percentage for a client.
        
        Args:
            client_id: ID of the client
            demand_percentage: The new demand percentage (0-100)
        """
        if client_id in self.client_demand:
            # When the demand changes, we need to reset the resource allocations
            self.current_allocations = {}
            
            # Update the demand
            self.client_demand[client_id] = max(0.0, min(100.0, demand_percentage))
            
            self.audit_logger.log_event(
                "client_demand_updated",
                f"Client {client_id} demand updated to {self.client_demand[client_id]:.2f}%",
                client_id=client_id,
                demand_percentage=self.client_demand[client_id],
            )
    
    def get_borrowed_percentage(self, client_id: str) -> float:
        """
        Get the percentage of resources borrowed by a client.
        
        Args:
            client_id: ID of the client
            
        Returns:
            Percentage of resources borrowed
        """
        if client_id in self.current_allocations:
            return self.current_allocations[client_id].borrowed_percentage
        return 0.0
    
    def get_lent_percentage(self, client_id: str) -> float:
        """
        Get the percentage of resources lent by a client.
        
        Args:
            client_id: ID of the client
            
        Returns:
            Percentage of resources lent
        """
        if client_id in self.current_allocations:
            return self.current_allocations[client_id].lent_percentage
        return 0.0
    
    def get_borrowed_from(self, client_id: str) -> Dict[str, float]:
        """
        Get the clients that this client is borrowing resources from.
        
        Args:
            client_id: ID of the client
            
        Returns:
            Dictionary mapping client IDs to borrowed percentages
        """
        if client_id in self.current_allocations:
            return self.current_allocations[client_id].borrowed_from
        return {}
    
    def get_lent_to(self, client_id: str) -> Dict[str, float]:
        """
        Get the clients that this client is lending resources to.
        
        Args:
            client_id: ID of the client
            
        Returns:
            Dictionary mapping client IDs to lent percentages
        """
        if client_id in self.current_allocations:
            return self.current_allocations[client_id].lent_to
        return {}
    
    def allocate_client_resources(self, clients: Optional[List[Client]] = None, nodes: Optional[List[RenderNode]] = None) -> Dict[str, ResourceAllocation]:
        """
        Allocate resources to clients based on SLAs and current demands.
        
        Args:
            clients: List of clients (if None, use stored clients)
            nodes: List of available render nodes (if None, use stored nodes)
            
        Returns:
            Dictionary mapping client IDs to their resource allocations
        """
        with self.performance_monitor.time_operation("allocate_resources"):
            # Use provided clients/nodes or fall back to stored ones
            clients_list = clients if clients is not None else list(self.clients.values())
            nodes_list = nodes if nodes is not None else list(self.nodes.values())
            
            # Calculate total available resources (number of nodes)
            total_nodes = len(nodes_list)
            
            # Calculate guaranteed resources for each client
            guaranteed_allocations: Dict[str, int] = {}
            for client in clients_list:
                # Calculate how many nodes the client is guaranteed
                guaranteed_nodes = math.floor(total_nodes * client.guaranteed_resources / 100)
                guaranteed_allocations[client.id] = guaranteed_nodes
            
            # Check if total guaranteed resources exceed total available resources
            total_guaranteed = sum(guaranteed_allocations.values())
            if total_guaranteed > total_nodes:
                # Scale down guaranteed allocations proportionally
                scale_factor = total_nodes / total_guaranteed
                for client_id in guaranteed_allocations:
                    guaranteed_allocations[client_id] = math.floor(
                        guaranteed_allocations[client_id] * scale_factor
                    )
                
                self.audit_logger.log_event(
                    "resource_allocation_scaled",
                    f"Guaranteed allocations scaled down due to resource constraints (factor: {scale_factor:.2f})",
                    scale_factor=scale_factor,
                    original_total_guaranteed=total_guaranteed,
                    scaled_total_guaranteed=sum(guaranteed_allocations.values()),
                )
            
            # Calculate unallocated nodes
            allocated_nodes = sum(guaranteed_allocations.values())
            unallocated_nodes = total_nodes - allocated_nodes
            
            # Prepare resource allocations
            allocations: Dict[str, ResourceAllocation] = {}
            for client in clients_list:
                allocations[client.id] = ResourceAllocation(
                    client_id=client.id,
                    allocated_percentage=(guaranteed_allocations[client.id] / total_nodes) * 100 if total_nodes > 0 else 0,
                    allocated_nodes=[],
                    borrowed_percentage=0.0,
                    borrowed_from={},
                    lent_percentage=0.0,
                    lent_to={},
                )
            
            # Allocate guaranteed nodes to clients
            available_nodes = list(nodes_list)  # Make a copy to track available nodes
            
            for client in clients_list:
                # Get nodes for this client's guaranteed allocation
                client_nodes = self._select_nodes_for_client(
                    client, 
                    available_nodes, 
                    guaranteed_allocations[client.id]
                )
                
                allocations[client.id].allocated_nodes = [node.id for node in client_nodes]
                
                # Remove allocated nodes from available nodes
                available_nodes = [
                    node for node in available_nodes 
                    if node.id not in allocations[client.id].allocated_nodes
                ]
            
            # If resource borrowing is enabled, handle overflow allocation
            if self.allow_borrowing and unallocated_nodes > 0:
                # Calculate demand for each client (based on pending jobs)
                client_demand = self.client_demand
                if not client_demand:
                    client_demand = self._calculate_client_demand(clients_list, nodes_list, allocations)
                
                # Allocate overflow resources based on demand and max allocation limits
                overflow_allocations = self._allocate_overflow_resources(
                    clients_list, available_nodes, client_demand
                )
                
                # Update allocations with overflow
                for client_id, overflow_nodes in overflow_allocations.items():
                    # Calculate borrowed percentage
                    borrowed_percentage = (len(overflow_nodes) / total_nodes) * 100
                    
                    # Make sure borrowed percentage doesn't exceed the limit for borrowing client
                    client_obj = next((c for c in clients_list if c.id == client_id), None)
                    if client_obj and self.borrowing_limit_percentage > 0:
                        # Calculate maximum borrowable percentage based on client's guaranteed resources
                        max_borrowable = self.borrowing_limit_percentage
                        if borrowed_percentage > max_borrowable:
                            # Adjust overflow nodes to respect the limit
                            nodes_to_use = math.floor((max_borrowable / 100.0) * total_nodes)
                            # Make sure we always get at least one node if there are any
                            nodes_to_use = max(1, nodes_to_use) if overflow_nodes else 0
                            overflow_nodes = overflow_nodes[:nodes_to_use]
                            borrowed_percentage = (len(overflow_nodes) / total_nodes) * 100
                    
                    # Add overflow nodes to allocation
                    allocations[client_id].allocated_nodes.extend(overflow_nodes)
                    allocations[client_id].allocated_percentage += borrowed_percentage
                    allocations[client_id].borrowed_percentage = borrowed_percentage
                    
                    # Track which clients the resources were borrowed from
                    # (simplified - in a real system, you would track specific borrowing relationships)
                    borrowed_from = {}
                    for other_client in clients_list:
                        if other_client.id != client_id:
                            borrowed_from[other_client.id] = borrowed_percentage / (len(clients_list) - 1)
                    
                    allocations[client_id].borrowed_from = borrowed_from
                    
                    # Update lent_to for other clients
                    for other_client_id in borrowed_from:
                        if other_client_id in allocations:
                            if client_id not in allocations[other_client_id].lent_to:
                                allocations[other_client_id].lent_to[client_id] = 0.0
                            
                            allocations[other_client_id].lent_to[client_id] += borrowed_from[other_client_id]
                            allocations[other_client_id].lent_percentage += borrowed_from[other_client_id]
            
            # Log allocations
            for client_id, allocation in allocations.items():
                self.audit_logger.log_event(
                    "resources_allocated",
                    f"Resources allocated to client {client_id}: "
                    f"{allocation.allocated_percentage:.2f}% "
                    f"({len(allocation.allocated_nodes)} nodes)",
                    client_id=client_id,
                    allocated_percentage=allocation.allocated_percentage,
                    allocated_node_count=len(allocation.allocated_nodes),
                    borrowed_percentage=allocation.borrowed_percentage,
                    lent_percentage=allocation.lent_percentage,
                    total_nodes=total_nodes,
                )
            
            # Update our internal state
            self.current_allocations = allocations
            
            # Update performance metrics
            for client_id, allocation in allocations.items():
                self.performance_monitor.update_client_resource_metrics(
                    client_id=client_id,
                    allocated_percentage=allocation.allocated_percentage,
                    borrowed_percentage=allocation.borrowed_percentage,
                    lent_percentage=allocation.lent_percentage,
                )
            
            return allocations
    
    def can_borrow_resources(self, from_client: Client, to_client: Client, amount: float) -> bool:
        """
        Determine if resources can be borrowed from one client to another.
        
        Args:
            from_client: The client lending resources
            to_client: The client borrowing resources
            amount: The percentage of resources to borrow
            
        Returns:
            True if resources can be borrowed, False otherwise
        """
        # Cannot borrow if borrowing is disabled
        if not self.allow_borrowing:
            return False
        
        # Calculate the maximum amount that can be borrowed from this client
        max_borrowable = from_client.guaranteed_resources * (self.borrowing_limit_percentage / 100)
        
        # Check if the requested amount exceeds the limit
        if amount > max_borrowable:
            return False
        
        # Check if the borrowing client would exceed their maximum allocation
        if to_client.guaranteed_resources + amount > to_client.max_resources:
            return False
        
        return True
    
    def calculate_resource_usage(self, client_id: str, jobs: List[RenderJob], nodes: List[RenderNode]) -> float:
        """
        Calculate the current resource usage for a client.
        
        Args:
            client_id: ID of the client
            jobs: List of render jobs
            nodes: List of render nodes
            
        Returns:
            Percentage of resources currently used by the client
        """
        # Count nodes currently used by this client
        client_nodes = 0
        total_nodes = len(nodes)
        
        for node in nodes:
            if node.current_job_id:
                job = next((j for j in jobs if j.id == node.current_job_id), None)
                if job and job.client_id == client_id:
                    client_nodes += 1
        
        # Calculate percentage
        if total_nodes == 0:
            return 0.0
        
        return (client_nodes / total_nodes) * 100
    
    def _select_nodes_for_client(
        self, client: Client, available_nodes: List[RenderNode], node_count: int
    ) -> List[RenderNode]:
        """
        Select appropriate nodes for a client based on their requirements.
        
        Args:
            client: The client to select nodes for
            available_nodes: List of available nodes
            node_count: Number of nodes to select
            
        Returns:
            List of selected nodes
        """
        if node_count <= 0 or not available_nodes:
            return []
        
        # In a real implementation, this would consider the client's typical workload
        # For simplicity, we'll just select the first N available nodes
        return available_nodes[:node_count]
    
    def _calculate_client_demand(
        self, 
        clients: List[Client], 
        nodes: List[RenderNode],
        allocations: Dict[str, ResourceAllocation],
    ) -> Dict[str, float]:
        """
        Calculate resource demand for each client based on pending jobs.
        
        Args:
            clients: List of clients
            nodes: List of nodes
            allocations: Current resource allocations
            
        Returns:
            Dictionary mapping client IDs to their demand (percentage of total resources)
        """
        # This is a simplified implementation - a real system would analyze job requirements
        # and estimate the actual resource needs based on job characteristics
        
        client_demand: Dict[str, float] = {}
        total_nodes = len(nodes)
        
        for client in clients:
            # Check if client is already at their maximum allocation
            if client.max_resources <= 0:
                client_demand[client.id] = 0.0
                continue
            
            current_allocation = allocations[client.id].allocated_percentage
            
            if current_allocation >= client.max_resources:
                client_demand[client.id] = 0.0
            else:
                # Client can use more resources up to their maximum
                client_demand[client.id] = min(
                    client.max_resources - current_allocation,
                    client.guaranteed_resources * 0.5,  # Simplified demand estimation
                )
        
        return client_demand
    
    def _allocate_overflow_resources(
        self,
        clients: List[Client],
        available_nodes: List[RenderNode],
        client_demand: Dict[str, float],
    ) -> Dict[str, List[str]]:
        """
        Allocate overflow resources based on client demand.
        
        Args:
            clients: List of clients
            available_nodes: List of available nodes
            client_demand: Dictionary mapping client IDs to their demand
            
        Returns:
            Dictionary mapping client IDs to lists of allocated overflow node IDs
        """
        overflow_allocations: Dict[str, List[str]] = defaultdict(list)
        
        # Calculate total demand
        total_demand = sum(client_demand.values())
        
        if total_demand <= 0:
            return overflow_allocations
        
        # Sort clients by demand (highest first)
        sorted_clients = sorted(
            [(client_id, demand) for client_id, demand in client_demand.items()],
            key=lambda x: x[1],
            reverse=True,
        )
        
        # Allocate overflow nodes proportionally to demand
        nodes_remaining = len(available_nodes)
        
        for client_id, demand in sorted_clients:
            if demand <= 0 or nodes_remaining <= 0:
                continue
            
            # Calculate share of overflow based on demand
            demand_share = demand / total_demand
            node_share = min(math.floor(demand_share * len(available_nodes)), nodes_remaining)
            
            # Get the nodes for this client
            client_nodes = available_nodes[:node_share]
            overflow_allocations[client_id] = [node.id for node in client_nodes]
            
            # Update remaining nodes
            available_nodes = available_nodes[node_share:]
            nodes_remaining -= node_share
        
        # If there are still nodes available, allocate them to clients that can use them
        while available_nodes and sorted_clients:
            client_id, demand = sorted_clients[0]
            
            if demand > 0:
                overflow_allocations[client_id].append(available_nodes[0].id)
                available_nodes = available_nodes[1:]
            
            # Move this client to the end of the list for round-robin allocation
            sorted_clients = sorted_clients[1:] + [sorted_clients[0]]
        
        return overflow_allocations
    
    # Abstract methods from common ResourceManagerInterface  
    # Note: These methods handle common BaseJob/BaseNode objects
    def allocate_resources(self, job: BaseJob, nodes: List[BaseNode]) -> Result[str]:
        """
        Allocate resources for a job.
        
        Args:
            job: Job requiring resources
            nodes: Available nodes
            
        Returns:
            Result containing assigned node ID or error
        """
        # Convert common models to render models for compatibility
        from render_farm_manager.core.models import RenderJob, RenderNode
        
        # Find the best node for this job
        for node in nodes:
            if node.can_accommodate(job):
                # Allocate resources on this node
                if node.allocate_resources(job):
                    self.audit_logger.log_event(
                        "resource_allocated",
                        f"Allocated resources for job {job.id} on node {node.id}",
                        job_id=job.id,
                        node_id=node.id
                    )
                    return Result.ok(node.id)
        
        return Result.fail("No suitable node found", ErrorCode.RESOURCE_UNAVAILABLE)
    
    def release_resources(self, job: BaseJob, node: BaseNode) -> Result[None]:
        """
        Release resources allocated to a job.
        
        Args:
            job: Job releasing resources
            node: Node to release from
            
        Returns:
            Result indicating success or failure
        """
        try:
            node.release_resources(job)
            self.audit_logger.log_event(
                "resource_released",
                f"Released resources for job {job.id} from node {node.id}",
                job_id=job.id,
                node_id=node.id
            )
            return Result.ok(None)
        except Exception as e:
            return Result.fail(f"Failed to release resources: {str(e)}", "OPERATION_FAILED")
    
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
            availability[node.id] = node.get_available_resources()
        return availability
    
    def reserve_resources(self, job: BaseJob, node: BaseNode, start_time: datetime, duration: float) -> Result[str]:
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
        # Generate a unique reservation ID
        import uuid
        reservation_id = str(uuid.uuid4())
        
        # In a real implementation, this would create a reservation record
        # For now, we'll just log the event
        self.audit_logger.log_event(
            "resource_reserved",
            f"Reserved resources for job {job.id} on node {node.id}",
            job_id=job.id,
            node_id=node.id,
            start_time=start_time.isoformat(),
            duration_hours=duration,
            reservation_id=reservation_id
        )
        
        return Result.ok(reservation_id)