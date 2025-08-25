"""Resource reservation system for the unified task scheduling library."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
import logging

from ..core.models import BaseJob, BaseNode, ResourceRequirement, ResourceType
from ..core.result import Result, ErrorCode


logger = logging.getLogger(__name__)


class ReservationStatus(str, Enum):
    """Status of a resource reservation."""
    PENDING = "pending"  # Reservation created but not yet active
    ACTIVE = "active"    # Reservation is currently active
    COMPLETED = "completed"  # Reservation completed successfully
    EXPIRED = "expired"   # Reservation expired without being used
    CANCELLED = "cancelled"  # Reservation was cancelled


class ReservationType(str, Enum):
    """Types of reservations."""
    IMMEDIATE = "immediate"  # Use resources immediately
    ADVANCE = "advance"     # Reserve for future use
    RECURRING = "recurring"  # Recurring reservation
    MAINTENANCE = "maintenance"  # Reserved for maintenance


@dataclass
class ResourceReservation:
    """A resource reservation."""
    reservation_id: str
    job_id: str
    node_id: str
    resource_requirements: List[ResourceRequirement]
    start_time: datetime
    end_time: datetime
    reservation_type: ReservationType = ReservationType.ADVANCE
    status: ReservationStatus = ReservationStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def duration(self) -> timedelta:
        """Get the duration of the reservation."""
        return self.end_time - self.start_time
    
    def is_active(self, current_time: Optional[datetime] = None) -> bool:
        """Check if reservation is currently active."""
        if current_time is None:
            current_time = datetime.now()
        return (self.status == ReservationStatus.ACTIVE and 
                self.start_time <= current_time <= self.end_time)
    
    def overlaps_with(self, other: 'ResourceReservation') -> bool:
        """Check if this reservation overlaps with another."""
        return (self.node_id == other.node_id and
                not (self.end_time <= other.start_time or other.end_time <= self.start_time))
    
    def conflicts_with(self, other: 'ResourceReservation') -> bool:
        """Check if this reservation conflicts with another (same node, overlapping time, conflicting resources)."""
        if not self.overlaps_with(other):
            return False
        
        # Check for resource conflicts
        my_resources = {req.resource_type: req.amount for req in self.resource_requirements}
        other_resources = {req.resource_type: req.amount for req in other.resource_requirements}
        
        for resource_type in my_resources:
            if resource_type in other_resources:
                # There's a potential conflict - would need to check node capacity
                return True
        
        return False


@dataclass
class ReservationRequest:
    """Request for a resource reservation."""
    job_id: str
    resource_requirements: List[ResourceRequirement]
    start_time: datetime
    duration: timedelta
    reservation_type: ReservationType = ReservationType.ADVANCE
    priority: int = 0
    preferred_nodes: Optional[List[str]] = None
    excluded_nodes: Optional[List[str]] = None
    constraints: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def end_time(self) -> datetime:
        """Calculate end time from start time and duration."""
        return self.start_time + self.duration


class ResourceReservationManager:
    """
    Manager for resource reservations in the unified task scheduling system.
    
    This class handles:
    - Creating and managing resource reservations
    - Checking for conflicts and availability
    - Reservation lifecycle management
    - Resource utilization tracking for reservations
    """
    
    def __init__(self, 
                 default_reservation_duration: timedelta = timedelta(hours=1),
                 max_advance_reservation_time: timedelta = timedelta(days=30),
                 cleanup_interval: timedelta = timedelta(hours=1)):
        """
        Initialize the reservation manager.
        
        Args:
            default_reservation_duration: Default duration for reservations
            max_advance_reservation_time: Maximum time in advance for reservations
            cleanup_interval: Interval for cleaning up expired reservations
        """
        self.default_reservation_duration = default_reservation_duration
        self.max_advance_reservation_time = max_advance_reservation_time
        self.cleanup_interval = cleanup_interval
        
        # Reservation storage
        self.reservations: Dict[str, ResourceReservation] = {}
        self.node_reservations: Dict[str, List[str]] = {}  # node_id -> reservation_ids
        self.job_reservations: Dict[str, List[str]] = {}   # job_id -> reservation_ids
        
        # Tracking
        self.reservation_history: List[ResourceReservation] = []
        self.last_cleanup: datetime = datetime.now()
        
        logger.info("ResourceReservationManager initialized")
    
    def create_reservation(self, request: ReservationRequest, 
                          nodes: List[BaseNode]) -> Result[ResourceReservation]:
        """
        Create a new resource reservation.
        
        Args:
            request: Reservation request
            nodes: Available nodes to consider
            
        Returns:
            Result containing the created reservation or error
        """
        # Validate request
        if request.start_time < datetime.now():
            return Result.err("Cannot create reservation in the past", ErrorCode.INVALID_PARAMETER)
        
        if request.start_time > datetime.now() + self.max_advance_reservation_time:
            return Result.err("Reservation too far in advance", ErrorCode.INVALID_PARAMETER)
        
        if request.duration <= timedelta(0):
            return Result.err("Reservation duration must be positive", ErrorCode.INVALID_PARAMETER)
        
        # Find suitable node
        suitable_node = self._find_suitable_node(request, nodes)
        if not suitable_node:
            return Result.err("No suitable node available for reservation", ErrorCode.RESOURCE_UNAVAILABLE)
        
        # Check for conflicts
        conflicts = self._check_conflicts(request, suitable_node.id)
        if conflicts:
            return Result.err(f"Reservation conflicts with existing reservations: {conflicts}", 
                            ErrorCode.RESOURCE_CONFLICT)
        
        # Create reservation
        reservation_id = f"res_{request.job_id}_{request.start_time.isoformat()}"
        reservation = ResourceReservation(
            reservation_id=reservation_id,
            job_id=request.job_id,
            node_id=suitable_node.id,
            resource_requirements=request.resource_requirements,
            start_time=request.start_time,
            end_time=request.end_time,
            reservation_type=request.reservation_type,
            priority=request.priority,
            metadata=request.metadata or {}
        )
        
        # Store reservation
        self.reservations[reservation_id] = reservation
        
        # Update indices
        if suitable_node.id not in self.node_reservations:
            self.node_reservations[suitable_node.id] = []
        self.node_reservations[suitable_node.id].append(reservation_id)
        
        if request.job_id not in self.job_reservations:
            self.job_reservations[request.job_id] = []
        self.job_reservations[request.job_id].append(reservation_id)
        
        logger.info(f"Created reservation {reservation_id} for job {request.job_id} "
                   f"on node {suitable_node.id} from {request.start_time} to {request.end_time}")
        
        return Result.ok(reservation)
    
    def cancel_reservation(self, reservation_id: str, reason: str = "User requested") -> Result[ResourceReservation]:
        """
        Cancel a resource reservation.
        
        Args:
            reservation_id: ID of reservation to cancel
            reason: Reason for cancellation
            
        Returns:
            Result containing the cancelled reservation or error
        """
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found", ErrorCode.NOT_FOUND)
        
        reservation = self.reservations[reservation_id]
        
        if reservation.status in [ReservationStatus.COMPLETED, ReservationStatus.EXPIRED]:
            return Result.err(f"Cannot cancel reservation with status {reservation.status.value}", 
                            ErrorCode.INVALID_STATE)
        
        # Update status
        reservation.status = ReservationStatus.CANCELLED
        reservation.metadata["cancellation_reason"] = reason
        reservation.metadata["cancelled_at"] = datetime.now().isoformat()
        
        # Move to history
        self.reservation_history.append(reservation)
        self._remove_reservation(reservation_id)
        
        logger.info(f"Cancelled reservation {reservation_id}: {reason}")
        return Result.ok(reservation)
    
    def activate_reservation(self, reservation_id: str) -> Result[ResourceReservation]:
        """
        Activate a reservation (mark as actively using resources).
        
        Args:
            reservation_id: ID of reservation to activate
            
        Returns:
            Result containing the activated reservation or error
        """
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found", ErrorCode.NOT_FOUND)
        
        reservation = self.reservations[reservation_id]
        current_time = datetime.now()
        
        # Check if reservation can be activated
        if reservation.status != ReservationStatus.PENDING:
            return Result.err(f"Reservation must be pending to activate (current: {reservation.status.value})", 
                            ErrorCode.INVALID_STATE)
        
        if current_time < reservation.start_time:
            return Result.err("Reservation cannot be activated before start time", ErrorCode.INVALID_OPERATION)
        
        if current_time > reservation.end_time:
            return Result.err("Reservation has expired", ErrorCode.INVALID_OPERATION)
        
        # Activate reservation
        reservation.status = ReservationStatus.ACTIVE
        reservation.metadata["activated_at"] = current_time.isoformat()
        
        logger.info(f"Activated reservation {reservation_id}")
        return Result.ok(reservation)
    
    def complete_reservation(self, reservation_id: str) -> Result[ResourceReservation]:
        """
        Mark a reservation as completed.
        
        Args:
            reservation_id: ID of reservation to complete
            
        Returns:
            Result containing the completed reservation or error
        """
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found", ErrorCode.NOT_FOUND)
        
        reservation = self.reservations[reservation_id]
        
        if reservation.status not in [ReservationStatus.ACTIVE, ReservationStatus.PENDING]:
            return Result.err(f"Cannot complete reservation with status {reservation.status.value}", 
                            ErrorCode.INVALID_STATE)
        
        # Complete reservation
        reservation.status = ReservationStatus.COMPLETED
        reservation.metadata["completed_at"] = datetime.now().isoformat()
        
        # Move to history
        self.reservation_history.append(reservation)
        self._remove_reservation(reservation_id)
        
        logger.info(f"Completed reservation {reservation_id}")
        return Result.ok(reservation)
    
    def get_reservations_for_node(self, node_id: str, 
                                 start_time: Optional[datetime] = None,
                                 end_time: Optional[datetime] = None) -> List[ResourceReservation]:
        """
        Get reservations for a specific node within a time range.
        
        Args:
            node_id: Node to get reservations for
            start_time: Start of time range (defaults to now)
            end_time: End of time range (defaults to far future)
            
        Returns:
            List of reservations for the node
        """
        if start_time is None:
            start_time = datetime.now()
        if end_time is None:
            end_time = datetime.now() + timedelta(days=365)  # One year from now
        
        reservation_ids = self.node_reservations.get(node_id, [])
        reservations = []
        
        for res_id in reservation_ids:
            if res_id in self.reservations:
                reservation = self.reservations[res_id]
                # Check if reservation overlaps with requested time range
                if not (reservation.end_time <= start_time or reservation.start_time >= end_time):
                    reservations.append(reservation)
        
        return sorted(reservations, key=lambda r: r.start_time)
    
    def get_reservations_for_job(self, job_id: str) -> List[ResourceReservation]:
        """Get all reservations for a specific job."""
        reservation_ids = self.job_reservations.get(job_id, [])
        reservations = []
        
        for res_id in reservation_ids:
            if res_id in self.reservations:
                reservations.append(self.reservations[res_id])
        
        return sorted(reservations, key=lambda r: r.start_time)
    
    def check_availability(self, node_id: str, start_time: datetime, 
                          end_time: datetime, 
                          resource_requirements: List[ResourceRequirement]) -> bool:
        """
        Check if resources are available on a node during a time period.
        
        Args:
            node_id: Node to check
            start_time: Start of time period
            end_time: End of time period
            resource_requirements: Resources needed
            
        Returns:
            True if resources are available
        """
        # Get existing reservations that overlap with the requested time
        overlapping_reservations = []
        reservation_ids = self.node_reservations.get(node_id, [])
        
        for res_id in reservation_ids:
            if res_id in self.reservations:
                reservation = self.reservations[res_id]
                if not (reservation.end_time <= start_time or reservation.start_time >= end_time):
                    overlapping_reservations.append(reservation)
        
        # Calculate resource usage during the time period
        # For simplicity, assume all overlapping reservations are active simultaneously
        used_resources = {}
        for resource_type in ResourceType:
            used_resources[resource_type] = 0
        
        for reservation in overlapping_reservations:
            for req in reservation.resource_requirements:
                used_resources[req.resource_type] += req.amount
        
        # Check if requested resources can be accommodated
        # This would need access to node capacity information
        # For now, assume simple conflict checking
        for req in resource_requirements:
            current_usage = used_resources.get(req.resource_type, 0)
            # Would need to compare against actual node capacity
            # This is a placeholder implementation
            if current_usage + req.amount > 100:  # Placeholder capacity
                return False
        
        return True
    
    def get_utilization_forecast(self, node_id: str, 
                               forecast_hours: int = 24) -> Dict[str, List[Tuple[datetime, float]]]:
        """
        Get resource utilization forecast for a node.
        
        Args:
            node_id: Node to forecast for
            forecast_hours: Hours to forecast
            
        Returns:
            Dictionary mapping resource types to time series of utilization
        """
        current_time = datetime.now()
        end_time = current_time + timedelta(hours=forecast_hours)
        
        # Get all reservations in the forecast period
        reservations = self.get_reservations_for_node(node_id, current_time, end_time)
        
        # Create timeline of utilization changes
        utilization_timeline = {}
        for resource_type in ResourceType:
            utilization_timeline[resource_type.value] = [(current_time, 0.0)]
        
        # Process each reservation
        for reservation in reservations:
            for req in reservation.resource_requirements:
                resource_type = req.resource_type.value
                
                # Add utilization at start time
                utilization_timeline[resource_type].append((reservation.start_time, req.amount))
                
                # Remove utilization at end time  
                utilization_timeline[resource_type].append((reservation.end_time, -req.amount))
        
        # Calculate cumulative utilization
        forecast = {}
        for resource_type, events in utilization_timeline.items():
            events.sort(key=lambda x: x[0])  # Sort by time
            
            cumulative_util = 0.0
            timeline = []
            
            for timestamp, change in events:
                cumulative_util += change
                timeline.append((timestamp, max(0.0, cumulative_util)))
            
            forecast[resource_type] = timeline
        
        return forecast
    
    def cleanup_expired_reservations(self) -> int:
        """
        Clean up expired reservations.
        
        Returns:
            Number of reservations cleaned up
        """
        current_time = datetime.now()
        
        if current_time - self.last_cleanup < self.cleanup_interval:
            return 0
        
        expired_reservations = []
        
        for res_id, reservation in list(self.reservations.items()):
            if (reservation.status == ReservationStatus.PENDING and 
                current_time > reservation.end_time):
                
                # Mark as expired
                reservation.status = ReservationStatus.EXPIRED
                reservation.metadata["expired_at"] = current_time.isoformat()
                
                expired_reservations.append(res_id)
        
        # Move expired reservations to history
        for res_id in expired_reservations:
            reservation = self.reservations[res_id]
            self.reservation_history.append(reservation)
            self._remove_reservation(res_id)
        
        self.last_cleanup = current_time
        
        if expired_reservations:
            logger.info(f"Cleaned up {len(expired_reservations)} expired reservations")
        
        return len(expired_reservations)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get reservation statistics."""
        current_time = datetime.now()
        
        stats = {
            "total_active_reservations": len(self.reservations),
            "reservations_by_status": {},
            "reservations_by_type": {},
            "total_historical_reservations": len(self.reservation_history),
            "nodes_with_reservations": len(self.node_reservations),
            "upcoming_reservations": 0,
            "active_reservations": 0
        }
        
        # Count by status and type
        for reservation in self.reservations.values():
            status = reservation.status.value
            res_type = reservation.reservation_type.value
            
            stats["reservations_by_status"][status] = stats["reservations_by_status"].get(status, 0) + 1
            stats["reservations_by_type"][res_type] = stats["reservations_by_type"].get(res_type, 0) + 1
            
            if reservation.start_time > current_time:
                stats["upcoming_reservations"] += 1
            elif reservation.is_active(current_time):
                stats["active_reservations"] += 1
        
        return stats
    
    def _find_suitable_node(self, request: ReservationRequest, 
                           nodes: List[BaseNode]) -> Optional[BaseNode]:
        """Find a suitable node for the reservation request."""
        suitable_nodes = []
        
        # Filter nodes based on preferences and constraints
        candidate_nodes = nodes
        
        if request.preferred_nodes:
            candidate_nodes = [n for n in candidate_nodes if n.id in request.preferred_nodes]
        
        if request.excluded_nodes:
            candidate_nodes = [n for n in candidate_nodes if n.id not in request.excluded_nodes]
        
        # Check resource availability
        for node in candidate_nodes:
            if self.check_availability(node.id, request.start_time, request.end_time, 
                                     request.resource_requirements):
                suitable_nodes.append(node)
        
        # Return best node (for now, just return first suitable)
        return suitable_nodes[0] if suitable_nodes else None
    
    def _check_conflicts(self, request: ReservationRequest, node_id: str) -> List[str]:
        """Check for conflicts with existing reservations."""
        conflicts = []
        reservation_ids = self.node_reservations.get(node_id, [])
        
        for res_id in reservation_ids:
            if res_id in self.reservations:
                existing = self.reservations[res_id]
                
                # Create a temporary reservation object to check conflicts
                temp_reservation = ResourceReservation(
                    reservation_id="temp",
                    job_id=request.job_id,
                    node_id=node_id,
                    resource_requirements=request.resource_requirements,
                    start_time=request.start_time,
                    end_time=request.end_time
                )
                
                if temp_reservation.conflicts_with(existing):
                    conflicts.append(res_id)
        
        return conflicts
    
    def _remove_reservation(self, reservation_id: str):
        """Remove a reservation from active tracking."""
        if reservation_id not in self.reservations:
            return
        
        reservation = self.reservations[reservation_id]
        
        # Remove from main storage
        del self.reservations[reservation_id]
        
        # Remove from node index
        if reservation.node_id in self.node_reservations:
            self.node_reservations[reservation.node_id].remove(reservation_id)
            if not self.node_reservations[reservation.node_id]:
                del self.node_reservations[reservation.node_id]
        
        # Remove from job index
        if reservation.job_id in self.job_reservations:
            self.job_reservations[reservation.job_id].remove(reservation_id)
            if not self.job_reservations[reservation.job_id]:
                del self.job_reservations[reservation.job_id]