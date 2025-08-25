"""Node management for the unified task scheduling library."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
import logging

from ..core.models import BaseNode, NodeStatus, NodeCapabilities, ResourceType
from ..core.result import Result, ErrorCode


logger = logging.getLogger(__name__)


class NodeEvent(str, Enum):
    """Node lifecycle events."""
    ADDED = "added"
    REMOVED = "removed"
    STATUS_CHANGED = "status_changed"
    HEARTBEAT_RECEIVED = "heartbeat_received"
    HEARTBEAT_MISSED = "heartbeat_missed"
    FAILURE_DETECTED = "failure_detected"
    MAINTENANCE_STARTED = "maintenance_started"
    MAINTENANCE_COMPLETED = "maintenance_completed"
    CAPACITY_CHANGED = "capacity_changed"


class HealthCheckStatus(str, Enum):
    """Node health check status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class NodeEvent:
    """Node event for tracking."""
    node_id: str
    event_type: NodeEvent
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"NodeEvent({self.node_id}: {self.event_type.value} at {self.timestamp})"


@dataclass
class HealthCheck:
    """Node health check result."""
    node_id: str
    status: HealthCheckStatus
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    
    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return self.status == HealthCheckStatus.HEALTHY


@dataclass
class NodeGroup:
    """Group of nodes for management."""
    group_id: str
    name: str
    node_ids: Set[str] = field(default_factory=set)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_time: datetime = field(default_factory=datetime.now)
    
    def add_node(self, node_id: str):
        """Add a node to the group."""
        self.node_ids.add(node_id)
    
    def remove_node(self, node_id: str):
        """Remove a node from the group."""
        self.node_ids.discard(node_id)
    
    def size(self) -> int:
        """Get the number of nodes in the group."""
        return len(self.node_ids)


class NodeManager:
    """
    Node manager for the unified task scheduling library.
    
    This class handles:
    - Node registration and deregistration
    - Node health monitoring
    - Node grouping and organization
    - Capacity management
    - Node lifecycle management
    """
    
    def __init__(self, 
                 heartbeat_interval: timedelta = timedelta(minutes=5),
                 heartbeat_timeout: timedelta = timedelta(minutes=15),
                 health_check_interval: timedelta = timedelta(minutes=10)):
        """
        Initialize the node manager.
        
        Args:
            heartbeat_interval: Expected interval between heartbeats
            heartbeat_timeout: Time after which a node is considered offline
            health_check_interval: Interval for running health checks
        """
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.health_check_interval = health_check_interval
        
        # Node storage
        self.nodes: Dict[str, BaseNode] = {}
        self.node_groups: Dict[str, NodeGroup] = {}
        
        # Node monitoring
        self.last_heartbeat: Dict[str, datetime] = {}
        self.health_checks: Dict[str, List[HealthCheck]] = {}
        self.node_events: List[NodeEvent] = []
        
        # Node capabilities tracking
        self.capability_index: Dict[str, Set[str]] = {}  # capability -> node_ids
        self.resource_index: Dict[ResourceType, List[Tuple[str, float]]] = {}  # resource -> [(node_id, capacity)]
        
        # Maintenance and scheduling
        self.maintenance_windows: Dict[str, List[Tuple[datetime, datetime]]] = {}
        self.node_tags: Dict[str, Set[str]] = {}
        
        logger.info("NodeManager initialized")
    
    def register_node(self, node: BaseNode) -> Result[None]:
        """
        Register a new node with the manager.
        
        Args:
            node: Node to register
            
        Returns:
            Result indicating success or failure
        """
        if node.id in self.nodes:
            return Result.err(f"Node {node.id} already registered", ErrorCode.ALREADY_EXISTS)
        
        # Store node
        self.nodes[node.id] = node
        self.last_heartbeat[node.id] = datetime.now()
        self.health_checks[node.id] = []
        self.node_tags[node.id] = set()
        
        # Update indices
        self._update_capability_index(node)
        self._update_resource_index(node)
        
        # Record event
        event = NodeEvent(
            node_id=node.id,
            event_type=NodeEvent.ADDED,
            details={"name": node.name, "capabilities": node.capabilities.__dict__}
        )
        self.node_events.append(event)
        
        logger.info(f"Node {node.id} registered successfully")
        return Result.ok(None)
    
    def deregister_node(self, node_id: str) -> Result[BaseNode]:
        """
        Deregister a node from the manager.
        
        Args:
            node_id: ID of node to deregister
            
        Returns:
            Result containing the removed node or error
        """
        if node_id not in self.nodes:
            return Result.err(f"Node {node_id} not found", ErrorCode.NOT_FOUND)
        
        node = self.nodes[node_id]
        
        # Remove from all groups
        for group in self.node_groups.values():
            group.remove_node(node_id)
        
        # Clean up tracking data
        del self.nodes[node_id]
        self.last_heartbeat.pop(node_id, None)
        self.health_checks.pop(node_id, None)
        self.maintenance_windows.pop(node_id, None)
        self.node_tags.pop(node_id, None)
        
        # Update indices
        self._remove_from_capability_index(node)
        self._remove_from_resource_index(node)
        
        # Record event
        event = NodeEvent(
            node_id=node_id,
            event_type=NodeEvent.REMOVED,
            details={"name": node.name}
        )
        self.node_events.append(event)
        
        logger.info(f"Node {node_id} deregistered successfully")
        return Result.ok(node)
    
    def update_node_status(self, node_id: str, new_status: NodeStatus, 
                          reason: Optional[str] = None) -> Result[None]:
        """
        Update a node's status.
        
        Args:
            node_id: ID of node to update
            new_status: New status to set
            reason: Optional reason for status change
            
        Returns:
            Result indicating success or failure
        """
        if node_id not in self.nodes:
            return Result.err(f"Node {node_id} not found", ErrorCode.NOT_FOUND)
        
        node = self.nodes[node_id]
        old_status = node.status
        
        if old_status == new_status:
            return Result.ok(None)  # No change needed
        
        # Update status
        node.status = new_status
        
        # Record event
        event = NodeEvent(
            node_id=node_id,
            event_type=NodeEvent.STATUS_CHANGED,
            details={
                "old_status": old_status.value,
                "new_status": new_status.value,
                "reason": reason
            }
        )
        self.node_events.append(event)
        
        logger.info(f"Node {node_id} status changed: {old_status.value} -> {new_status.value}")
        return Result.ok(None)
    
    def receive_heartbeat(self, node_id: str, metadata: Optional[Dict[str, Any]] = None) -> Result[None]:
        """
        Receive and process a heartbeat from a node.
        
        Args:
            node_id: ID of node sending heartbeat
            metadata: Optional metadata about node status
            
        Returns:
            Result indicating success or failure
        """
        if node_id not in self.nodes:
            return Result.err(f"Node {node_id} not registered", ErrorCode.NOT_FOUND)
        
        node = self.nodes[node_id]
        current_time = datetime.now()
        
        # Update last heartbeat time
        last_hb = self.last_heartbeat.get(node_id)
        self.last_heartbeat[node_id] = current_time
        
        # Update node heartbeat timestamp
        node.last_heartbeat = current_time
        
        # If node was offline, bring it back online
        if node.status == NodeStatus.OFFLINE:
            self.update_node_status(node_id, NodeStatus.IDLE, "Heartbeat received")
        
        # Process metadata if provided
        if metadata:
            self._process_heartbeat_metadata(node, metadata)
        
        # Record event (only if significant gap since last heartbeat)
        if not last_hb or (current_time - last_hb) > self.heartbeat_interval * 2:
            event = NodeEvent(
                node_id=node_id,
                event_type=NodeEvent.HEARTBEAT_RECEIVED,
                details=metadata or {}
            )
            self.node_events.append(event)
        
        logger.debug(f"Heartbeat received from node {node_id}")
        return Result.ok(None)
    
    def check_node_health(self, node_id: str) -> Result[HealthCheck]:
        """
        Perform a health check on a node.
        
        Args:
            node_id: ID of node to check
            
        Returns:
            Result containing health check result
        """
        if node_id not in self.nodes:
            return Result.err(f"Node {node_id} not found", ErrorCode.NOT_FOUND)
        
        node = self.nodes[node_id]
        current_time = datetime.now()
        
        # Determine health status
        status = HealthCheckStatus.HEALTHY
        issues = []
        metrics = {}
        
        # Check heartbeat
        last_hb = self.last_heartbeat.get(node_id)
        if not last_hb or (current_time - last_hb) > self.heartbeat_timeout:
            status = HealthCheckStatus.CRITICAL
            issues.append("Heartbeat timeout")
        elif (current_time - last_hb) > self.heartbeat_interval * 2:
            status = HealthCheckStatus.WARNING
            issues.append("Heartbeat delayed")
        
        # Check node status
        if node.status == NodeStatus.OFFLINE:
            status = HealthCheckStatus.CRITICAL
            issues.append("Node offline")
        elif node.status == NodeStatus.MAINTENANCE:
            status = HealthCheckStatus.WARNING
            issues.append("Node in maintenance")
        
        # Check resource utilization
        available = node.get_available_resources()
        total_cpu = node.capabilities.cpu_cores
        total_memory = node.capabilities.memory_gb
        
        if total_cpu > 0:
            cpu_usage = (total_cpu - available.get(ResourceType.CPU, total_cpu)) / total_cpu
            metrics["cpu_utilization"] = cpu_usage
            if cpu_usage > 0.9:
                status = max(status, HealthCheckStatus.WARNING)
                issues.append(f"High CPU utilization: {cpu_usage:.1%}")
        
        if total_memory > 0:
            mem_usage = (total_memory - available.get(ResourceType.MEMORY, total_memory)) / total_memory
            metrics["memory_utilization"] = mem_usage
            if mem_usage > 0.9:
                status = max(status, HealthCheckStatus.WARNING)
                issues.append(f"High memory utilization: {mem_usage:.1%}")
        
        # Check reliability
        metrics["reliability_score"] = node.reliability_score
        if node.reliability_score < 0.8:
            status = max(status, HealthCheckStatus.WARNING)
            issues.append(f"Low reliability score: {node.reliability_score:.2f}")
        
        # Create health check result
        health_check = HealthCheck(
            node_id=node_id,
            status=status,
            metrics=metrics,
            issues=issues
        )
        
        # Store health check
        if node_id not in self.health_checks:
            self.health_checks[node_id] = []
        self.health_checks[node_id].append(health_check)
        
        # Keep only recent health checks
        self.health_checks[node_id] = self.health_checks[node_id][-100:]  # Keep last 100
        
        return Result.ok(health_check)
    
    def get_nodes_by_capability(self, capability: str) -> List[BaseNode]:
        """
        Get nodes that have a specific capability.
        
        Args:
            capability: Capability to search for
            
        Returns:
            List of nodes with the capability
        """
        node_ids = self.capability_index.get(capability, set())
        return [self.nodes[node_id] for node_id in node_ids if node_id in self.nodes]
    
    def get_nodes_by_resource(self, resource_type: ResourceType, 
                            min_capacity: float) -> List[BaseNode]:
        """
        Get nodes that have at least the specified resource capacity.
        
        Args:
            resource_type: Type of resource
            min_capacity: Minimum capacity required
            
        Returns:
            List of nodes meeting the criteria
        """
        suitable_nodes = []
        
        for node in self.nodes.values():
            available = node.get_available_resources()
            if available.get(resource_type, 0) >= min_capacity:
                suitable_nodes.append(node)
        
        return suitable_nodes
    
    def create_node_group(self, group_id: str, name: str, 
                         node_ids: Optional[List[str]] = None,
                         properties: Optional[Dict[str, Any]] = None) -> Result[NodeGroup]:
        """
        Create a new node group.
        
        Args:
            group_id: Unique identifier for the group
            name: Human-readable name for the group
            node_ids: Initial nodes to add to the group
            properties: Group properties
            
        Returns:
            Result containing the created group
        """
        if group_id in self.node_groups:
            return Result.err(f"Group {group_id} already exists", ErrorCode.ALREADY_EXISTS)
        
        # Validate node IDs
        if node_ids:
            for node_id in node_ids:
                if node_id not in self.nodes:
                    return Result.err(f"Node {node_id} not found", ErrorCode.NOT_FOUND)
        
        # Create group
        group = NodeGroup(
            group_id=group_id,
            name=name,
            node_ids=set(node_ids or []),
            properties=properties or {}
        )
        
        self.node_groups[group_id] = group
        
        logger.info(f"Node group {group_id} created with {len(group.node_ids)} nodes")
        return Result.ok(group)
    
    def add_node_to_group(self, group_id: str, node_id: str) -> Result[None]:
        """Add a node to a group."""
        if group_id not in self.node_groups:
            return Result.err(f"Group {group_id} not found", ErrorCode.NOT_FOUND)
        
        if node_id not in self.nodes:
            return Result.err(f"Node {node_id} not found", ErrorCode.NOT_FOUND)
        
        self.node_groups[group_id].add_node(node_id)
        return Result.ok(None)
    
    def remove_node_from_group(self, group_id: str, node_id: str) -> Result[None]:
        """Remove a node from a group."""
        if group_id not in self.node_groups:
            return Result.err(f"Group {group_id} not found", ErrorCode.NOT_FOUND)
        
        self.node_groups[group_id].remove_node(node_id)
        return Result.ok(None)
    
    def schedule_maintenance(self, node_id: str, start_time: datetime, 
                           end_time: datetime, reason: str = "Scheduled maintenance") -> Result[None]:
        """
        Schedule maintenance for a node.
        
        Args:
            node_id: ID of node to maintain
            start_time: Maintenance start time
            end_time: Maintenance end time
            reason: Reason for maintenance
            
        Returns:
            Result indicating success or failure
        """
        if node_id not in self.nodes:
            return Result.err(f"Node {node_id} not found", ErrorCode.NOT_FOUND)
        
        if start_time >= end_time:
            return Result.err("Start time must be before end time", ErrorCode.INVALID_PARAMETER)
        
        # Add maintenance window
        if node_id not in self.maintenance_windows:
            self.maintenance_windows[node_id] = []
        
        self.maintenance_windows[node_id].append((start_time, end_time))
        
        # If maintenance is starting now, update node status
        current_time = datetime.now()
        if start_time <= current_time <= end_time:
            self.update_node_status(node_id, NodeStatus.MAINTENANCE, reason)
        
        logger.info(f"Maintenance scheduled for node {node_id}: {start_time} to {end_time}")
        return Result.ok(None)
    
    def get_node_statistics(self) -> Dict[str, Any]:
        """Get comprehensive node statistics."""
        current_time = datetime.now()
        
        stats = {
            "total_nodes": len(self.nodes),
            "nodes_by_status": {},
            "total_capacity": {},
            "available_capacity": {},
            "utilization": {},
            "health_summary": {},
            "groups": len(self.node_groups)
        }
        
        # Status distribution
        for node in self.nodes.values():
            status = node.status.value
            stats["nodes_by_status"][status] = stats["nodes_by_status"].get(status, 0) + 1
        
        # Capacity statistics
        for resource_type in ResourceType:
            total = 0
            available = 0
            
            for node in self.nodes.values():
                if node.is_available():
                    node_available = node.get_available_resources()
                    available += node_available.get(resource_type, 0)
                
                if resource_type == ResourceType.CPU:
                    total += node.capabilities.cpu_cores
                elif resource_type == ResourceType.GPU:
                    total += node.capabilities.gpu_count
                elif resource_type == ResourceType.MEMORY:
                    total += node.capabilities.memory_gb
                elif resource_type == ResourceType.STORAGE:
                    total += node.capabilities.storage_gb
                elif resource_type == ResourceType.NETWORK:
                    total += node.capabilities.network_bandwidth_gbps
            
            stats["total_capacity"][resource_type.value] = total
            stats["available_capacity"][resource_type.value] = available
            
            if total > 0:
                stats["utilization"][resource_type.value] = (total - available) / total
            else:
                stats["utilization"][resource_type.value] = 0.0
        
        # Health summary
        healthy = warning = critical = unknown = 0
        
        for node_id in self.nodes:
            recent_checks = self.health_checks.get(node_id, [])
            if recent_checks:
                latest_check = recent_checks[-1]
                if latest_check.status == HealthCheckStatus.HEALTHY:
                    healthy += 1
                elif latest_check.status == HealthCheckStatus.WARNING:
                    warning += 1
                elif latest_check.status == HealthCheckStatus.CRITICAL:
                    critical += 1
                else:
                    unknown += 1
            else:
                unknown += 1
        
        stats["health_summary"] = {
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
            "unknown": unknown
        }
        
        return stats
    
    def run_health_checks(self) -> List[HealthCheck]:
        """Run health checks on all registered nodes."""
        results = []
        
        for node_id in self.nodes:
            result = self.check_node_health(node_id)
            if result.success:
                results.append(result.value)
        
        return results
    
    def detect_offline_nodes(self) -> List[str]:
        """Detect nodes that appear to be offline based on heartbeat timeout."""
        current_time = datetime.now()
        offline_nodes = []
        
        for node_id, last_hb in self.last_heartbeat.items():
            if (current_time - last_hb) > self.heartbeat_timeout:
                if self.nodes[node_id].status != NodeStatus.OFFLINE:
                    offline_nodes.append(node_id)
                    
                    # Update status
                    self.update_node_status(node_id, NodeStatus.OFFLINE, "Heartbeat timeout")
                    
                    # Record event
                    event = NodeEvent(
                        node_id=node_id,
                        event_type=NodeEvent.HEARTBEAT_MISSED,
                        details={"timeout_seconds": self.heartbeat_timeout.total_seconds()}
                    )
                    self.node_events.append(event)
        
        return offline_nodes
    
    def _update_capability_index(self, node: BaseNode):
        """Update the capability index when a node is added."""
        for capability in node.capabilities.specialized_hardware + node.capabilities.software_capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(node.id)
    
    def _remove_from_capability_index(self, node: BaseNode):
        """Remove node from capability index."""
        for capability in node.capabilities.specialized_hardware + node.capabilities.software_capabilities:
            if capability in self.capability_index:
                self.capability_index[capability].discard(node.id)
                if not self.capability_index[capability]:
                    del self.capability_index[capability]
    
    def _update_resource_index(self, node: BaseNode):
        """Update the resource index when a node is added."""
        resources = {
            ResourceType.CPU: node.capabilities.cpu_cores,
            ResourceType.GPU: node.capabilities.gpu_count,
            ResourceType.MEMORY: node.capabilities.memory_gb,
            ResourceType.STORAGE: node.capabilities.storage_gb,
            ResourceType.NETWORK: node.capabilities.network_bandwidth_gbps
        }
        
        for resource_type, capacity in resources.items():
            if resource_type not in self.resource_index:
                self.resource_index[resource_type] = []
            self.resource_index[resource_type].append((node.id, capacity))
    
    def _remove_from_resource_index(self, node: BaseNode):
        """Remove node from resource index."""
        for resource_type in ResourceType:
            if resource_type in self.resource_index:
                self.resource_index[resource_type] = [
                    (nid, cap) for nid, cap in self.resource_index[resource_type]
                    if nid != node.id
                ]
    
    def _process_heartbeat_metadata(self, node: BaseNode, metadata: Dict[str, Any]):
        """Process metadata from a heartbeat."""
        # Update reliability if provided
        if "reliability" in metadata:
            node.reliability_score = float(metadata["reliability"])
        
        # Update current load if provided
        if "load" in metadata:
            load_data = metadata["load"]
            for resource_str, load in load_data.items():
                try:
                    resource_type = ResourceType(resource_str)
                    node.current_load[resource_type] = float(load)
                except ValueError:
                    logger.warning(f"Unknown resource type in heartbeat: {resource_str}")
        
        # Update capabilities if they changed
        if "capabilities" in metadata:
            cap_data = metadata["capabilities"]
            if "cpu_cores" in cap_data:
                node.capabilities.cpu_cores = int(cap_data["cpu_cores"])
            if "memory_gb" in cap_data:
                node.capabilities.memory_gb = float(cap_data["memory_gb"])
            # ... update other capabilities as needed