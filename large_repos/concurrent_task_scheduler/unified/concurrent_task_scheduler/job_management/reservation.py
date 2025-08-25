"""Resource reservation system for long-running simulations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from concurrent_task_scheduler.models import (
    ComputeNode,
    NodeStatus,
    ResourceType,
    Result,
    Simulation,
    Priority as SimulationPriority,  # Import Priority as SimulationPriority for compatibility
    TimeRange,
)
from concurrent_task_scheduler.models.utils import generate_id

logger = logging.getLogger(__name__)


class ReservationType(str, Enum):
    """Types of resource reservations."""

    EXCLUSIVE = "exclusive"  # Exclusive access to nodes
    SHARED = "shared"  # Shared access to nodes
    PARTIAL = "partial"  # Partial node allocation
    DYNAMIC = "dynamic"  # Dynamically adjusted allocation


class ConflictResolution(str, Enum):
    """Strategies for resolving reservation conflicts."""

    FIRST_COME_FIRST_SERVED = "first_come_first_served"
    PRIORITY_BASED = "priority_based"
    PREEMPTION = "preemption"
    NEGOTIATION = "negotiation"
    ADMIN_DECISION = "admin_decision"


class ReservationStatus(str, Enum):
    """Status of a resource reservation."""

    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PREEMPTED = "preempted"


class ResourceAllocation:
    """Resource allocation for a reservation."""

    def __init__(
        self,
        node_id: str,
        resources: Dict[ResourceType, float],
        exclusive: bool = False,
    ):
        self.node_id = node_id
        self.resources = resources.copy()
        self.exclusive = exclusive
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def total_resources(self) -> Dict[ResourceType, float]:
        """Get the total resources allocated."""
        return self.resources.copy()
    
    def is_active(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this allocation is currently active."""
        if current_time is None:
            current_time = datetime.now()
        
        if self.start_time is None or self.end_time is None:
            return False
        
        return self.start_time <= current_time <= self.end_time


class Reservation(TimeRange):
    """A reservation for computational resources."""

    def __init__(
        self,
        reservation_id: str,
        simulation_id: str,
        start_time: datetime,
        end_time: datetime,
        reservation_type: ReservationType = ReservationType.EXCLUSIVE,
        status: ReservationStatus = ReservationStatus.REQUESTED,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.id = reservation_id
        self.simulation_id = simulation_id
        self.reservation_type = reservation_type
        self.status = status
        self.allocations: List[ResourceAllocation] = []
        self.priority: SimulationPriority = SimulationPriority.MEDIUM
        self.preemptible: bool = True
        self.request_time = datetime.now()
        self.last_modified = datetime.now()
        self.confirmation_time: Optional[datetime] = None
        self.activation_time: Optional[datetime] = None
        self.completion_time: Optional[datetime] = None
        self.cancellation_time: Optional[datetime] = None
        self.cancellation_reason: Optional[str] = None
        self.user_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self.metadata: Dict[str, str] = {}
    
    def add_allocation(self, allocation: ResourceAllocation) -> None:
        """Add a resource allocation to this reservation."""
        allocation.start_time = self.start_time
        allocation.end_time = self.end_time
        self.allocations.append(allocation)
        self.last_modified = datetime.now()
    
    def is_active(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this reservation is currently active."""
        if current_time is None:
            current_time = datetime.now()
        
        return (self.status == ReservationStatus.ACTIVE and 
                self.contains(current_time))
    
    def confirm(self) -> None:
        """Confirm this reservation."""
        if self.status == ReservationStatus.REQUESTED:
            self.status = ReservationStatus.CONFIRMED
            self.confirmation_time = datetime.now()
            self.last_modified = datetime.now()
    
    def activate(self) -> None:
        """Activate this reservation."""
        if self.status == ReservationStatus.CONFIRMED:
            self.status = ReservationStatus.ACTIVE
            self.activation_time = datetime.now()
            self.last_modified = datetime.now()
    
    def complete(self) -> None:
        """Mark this reservation as completed."""
        if self.status == ReservationStatus.ACTIVE:
            self.status = ReservationStatus.COMPLETED
            self.completion_time = datetime.now()
            self.last_modified = datetime.now()
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel this reservation."""
        if self.status not in [ReservationStatus.COMPLETED, ReservationStatus.CANCELLED]:
            self.status = ReservationStatus.CANCELLED
            self.cancellation_time = datetime.now()
            self.cancellation_reason = reason
            self.last_modified = datetime.now()
    
    def preempt(self, reason: str) -> None:
        """Preempt this reservation."""
        if self.status == ReservationStatus.ACTIVE:
            self.status = ReservationStatus.PREEMPTED
            self.cancellation_time = datetime.now()
            self.cancellation_reason = f"Preempted: {reason}"
            self.last_modified = datetime.now()
    
    def total_resources(self) -> Dict[ResourceType, float]:
        """Get the total resources allocated across all nodes."""
        totals: Dict[ResourceType, float] = {}
        
        for allocation in self.allocations:
            for resource_type, amount in allocation.resources.items():
                if resource_type in totals:
                    totals[resource_type] += amount
                else:
                    totals[resource_type] = amount
        
        return totals
    
    def allocated_nodes(self) -> List[str]:
        """Get the IDs of all allocated nodes."""
        return [allocation.node_id for allocation in self.allocations]
    
    def extended_duration(self) -> timedelta:
        """Get the total duration including any extensions."""
        return self.end_time - self.start_time
    
    def can_be_preempted(self) -> bool:
        """Check if this reservation can be preempted."""
        return self.preemptible


class MaintenanceWindow(TimeRange):
    """A maintenance window for the compute cluster."""

    def __init__(
        self,
        window_id: str,
        start_time: datetime,
        end_time: datetime,
        description: str,
        affected_nodes: List[str],
        severity: str = "major",
        cancellable: bool = False,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.id = window_id
        self.description = description
        self.affected_nodes = affected_nodes.copy()
        self.severity = severity  # critical, major, minor
        self.cancellable = cancellable
        self.creation_time = datetime.now()
        self.last_modified = datetime.now()
        self.cancelled = False
        self.cancellation_time: Optional[datetime] = None
        self.cancellation_reason: Optional[str] = None
        self.notifications_sent: List[datetime] = []
    
    def affects_node(self, node_id: str) -> bool:
        """Check if this maintenance window affects the specified node."""
        return node_id in self.affected_nodes
    
    def is_pending(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this maintenance window is pending (not started yet)."""
        if current_time is None:
            current_time = datetime.now()
        
        return not self.cancelled and current_time < self.start_time
    
    def is_active(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this maintenance window is currently active."""
        if current_time is None:
            current_time = datetime.now()
        
        return not self.cancelled and self.contains(current_time)
    
    def is_completed(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this maintenance window is completed."""
        if current_time is None:
            current_time = datetime.now()
        
        return not self.cancelled and current_time > self.end_time
    
    def cancel(self, reason: str) -> bool:
        """Attempt to cancel this maintenance window."""
        if not self.cancellable:
            return False
        
        if self.is_active():
            return False  # Can't cancel active maintenance
        
        self.cancelled = True
        self.cancellation_time = datetime.now()
        self.cancellation_reason = reason
        self.last_modified = datetime.now()
        
        return True
    
    def send_notification(self) -> None:
        """Record that a notification was sent for this maintenance window."""
        self.notifications_sent.append(datetime.now())
        self.last_modified = datetime.now()


class ReservationConflict:
    """A conflict between reservations or with maintenance."""

    def __init__(
        self,
        conflict_id: str,
        reservation_a_id: str,
        reservation_b_id: Optional[str] = None,
        maintenance_id: Optional[str] = None,
        conflict_type: str = "reservation_overlap",
    ):
        self.id = conflict_id
        self.reservation_a_id = reservation_a_id
        self.reservation_b_id = reservation_b_id
        self.maintenance_id = maintenance_id
        self.conflict_type = conflict_type
        self.detection_time = datetime.now()
        self.resolution_strategy: Optional[ConflictResolution] = None
        self.resolution_time: Optional[datetime] = None
        self.resolved = False
        self.resolution_details: Optional[str] = None
    
    def resolve(self, strategy: ConflictResolution, details: str) -> None:
        """Mark this conflict as resolved."""
        self.resolution_strategy = strategy
        self.resolution_time = datetime.now()
        self.resolved = True
        self.resolution_details = details


class ReservationSystem:
    """System for managing resource reservations."""

    def __init__(self, conflict_strategy: ConflictResolution = ConflictResolution.PRIORITY_BASED):
        self.reservations: Dict[str, Reservation] = {}
        self.maintenance_windows: Dict[str, MaintenanceWindow] = {}
        self.conflicts: Dict[str, ReservationConflict] = {}
        self.conflict_strategy = conflict_strategy
    
    def create_reservation(
        self,
        simulation_id: str,
        start_time: datetime,
        end_time: datetime,
        reservation_type: ReservationType = ReservationType.EXCLUSIVE,
        priority: SimulationPriority = SimulationPriority.MEDIUM,
        preemptible: bool = True,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Result[Reservation]:
        """Create a new reservation."""
        # Validate time range
        if start_time >= end_time:
            return Result.err("Start time must be before end time")
        
        if start_time < datetime.now():
            return Result.err("Cannot create reservation in the past")
        
        # Create reservation
        reservation_id = generate_id("rsv")
        reservation = Reservation(
            reservation_id=reservation_id,
            simulation_id=simulation_id,
            start_time=start_time,
            end_time=end_time,
            reservation_type=reservation_type,
            status=ReservationStatus.REQUESTED,
        )
        
        reservation.priority = priority
        reservation.preemptible = preemptible
        reservation.user_id = user_id
        reservation.project_id = project_id
        
        if metadata:
            reservation.metadata = metadata.copy()
        
        # Add to system
        self.reservations[reservation_id] = reservation
        
        # Check for conflicts
        conflicts = self._detect_conflicts(reservation)
        if conflicts:
            # Process conflicts based on strategy
            resolved = self._resolve_conflicts(conflicts)
            if not resolved:
                # If conflicts couldn't be resolved, cancel the reservation
                del self.reservations[reservation_id]
                return Result.err("Could not resolve reservation conflicts")
        
        return Result.ok(reservation)
    
    def add_allocation(
        self,
        reservation_id: str,
        node_id: str,
        resources: Dict[ResourceType, float],
        exclusive: bool = False,
    ) -> Result[bool]:
        """Add a resource allocation to a reservation."""
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found")
        
        reservation = self.reservations[reservation_id]
        
        if reservation.status not in [ReservationStatus.REQUESTED, ReservationStatus.CONFIRMED]:
            return Result.err(f"Cannot add allocation to {reservation.status} reservation")
        
        # Create and add allocation
        allocation = ResourceAllocation(
            node_id=node_id,
            resources=resources,
            exclusive=exclusive,
        )
        
        reservation.add_allocation(allocation)
        return Result.ok(True)
    
    def confirm_reservation(self, reservation_id: str) -> Result[bool]:
        """Confirm a requested reservation."""
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found")
        
        reservation = self.reservations[reservation_id]
        
        if reservation.status != ReservationStatus.REQUESTED:
            return Result.err(f"Cannot confirm {reservation.status} reservation")
        
        # Check if reservation has allocations
        if not reservation.allocations:
            return Result.err("Cannot confirm reservation without allocations")
        
        # Confirm reservation
        reservation.confirm()
        return Result.ok(True)
    
    def activate_reservation(self, reservation_id: str) -> Result[bool]:
        """Activate a confirmed reservation."""
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found")
        
        reservation = self.reservations[reservation_id]
        
        if reservation.status != ReservationStatus.CONFIRMED:
            return Result.err(f"Cannot activate {reservation.status} reservation")
        
        # Check if we're within the time window
        now = datetime.now()
        if now < reservation.start_time:
            return Result.err(
                f"Cannot activate reservation before start time "
                f"(current: {now}, start: {reservation.start_time})"
            )
        
        if now > reservation.end_time:
            return Result.err(
                f"Cannot activate expired reservation "
                f"(current: {now}, end: {reservation.end_time})"
            )
        
        # Activate reservation
        reservation.activate()
        return Result.ok(True)
    
    def complete_reservation(self, reservation_id: str) -> Result[bool]:
        """Mark a reservation as completed."""
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found")
        
        reservation = self.reservations[reservation_id]
        
        if reservation.status != ReservationStatus.ACTIVE:
            return Result.err(f"Cannot complete {reservation.status} reservation")
        
        reservation.complete()
        return Result.ok(True)
    
    def cancel_reservation(
        self,
        reservation_id: str,
        reason: Optional[str] = None,
    ) -> Result[bool]:
        """Cancel a reservation."""
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found")
        
        reservation = self.reservations[reservation_id]
        
        if reservation.status in [ReservationStatus.COMPLETED, ReservationStatus.CANCELLED]:
            return Result.err(f"Cannot cancel {reservation.status} reservation")
        
        reservation.cancel(reason)
        return Result.ok(True)
    
    def preempt_reservation(
        self,
        reservation_id: str,
        reason: str,
    ) -> Result[bool]:
        """Preempt an active reservation."""
        if reservation_id not in self.reservations:
            return Result.err(f"Reservation {reservation_id} not found")
        
        reservation = self.reservations[reservation_id]
        
        if reservation.status != ReservationStatus.ACTIVE:
            return Result.err(f"Cannot preempt {reservation.status} reservation")
        
        if not reservation.preemptible:
            return Result.err("Cannot preempt non-preemptible reservation")
        
        reservation.preempt(reason)
        return Result.ok(True)
    
    def add_maintenance_window(
        self,
        start_time: datetime,
        end_time: datetime,
        description: str,
        affected_nodes: List[str],
        severity: str = "major",
        cancellable: bool = False,
    ) -> Result[MaintenanceWindow]:
        """Add a maintenance window to the system."""
        # Validate time range
        if start_time >= end_time:
            return Result.err("Start time must be before end time")
        
        # Create maintenance window
        window_id = generate_id("maint")
        window = MaintenanceWindow(
            window_id=window_id,
            start_time=start_time,
            end_time=end_time,
            description=description,
            affected_nodes=affected_nodes,
            severity=severity,
            cancellable=cancellable,
        )
        
        # Add to system
        self.maintenance_windows[window_id] = window
        
        # Check for conflicts with existing reservations
        conflicts = []
        
        for reservation in self.reservations.values():
            if reservation.status in [
                ReservationStatus.REQUESTED,
                ReservationStatus.CONFIRMED,
                ReservationStatus.ACTIVE,
            ]:
                # Check for time and node overlap
                if window.overlaps(reservation) and any(
                    window.affects_node(node_id)
                    for node_id in reservation.allocated_nodes()
                ):
                    # Create conflict
                    conflict_id = generate_id("conflict")
                    conflict = ReservationConflict(
                        conflict_id=conflict_id,
                        reservation_a_id=reservation.id,
                        maintenance_id=window_id,
                        conflict_type="maintenance_overlap",
                    )
                    
                    self.conflicts[conflict_id] = conflict
                    conflicts.append(conflict)
        
        # Process conflicts based on strategy
        if conflicts:
            resolved = self._resolve_conflicts(conflicts)
            if not resolved and severity == "critical":
                # For critical maintenance, force resolution
                self._force_resolve_conflicts(conflicts, "Critical maintenance takes precedence")
        
        return Result.ok(window)
    
    def cancel_maintenance(
        self,
        window_id: str,
        reason: str,
    ) -> Result[bool]:
        """Cancel a maintenance window."""
        if window_id not in self.maintenance_windows:
            return Result.err(f"Maintenance window {window_id} not found")
        
        window = self.maintenance_windows[window_id]
        
        if not window.cancellable:
            return Result.err("Maintenance window is not cancellable")
        
        if window.is_active():
            return Result.err("Cannot cancel active maintenance window")
        
        if window.cancel(reason):
            return Result.ok(True)
        
        return Result.err("Failed to cancel maintenance window")
    
    def get_active_reservations(self) -> List[Reservation]:
        """Get all currently active reservations."""
        now = datetime.now()
        return [
            r for r in self.reservations.values()
            if r.is_active(now)
        ]
    
    def get_active_maintenance(self) -> List[MaintenanceWindow]:
        """Get all currently active maintenance windows."""
        now = datetime.now()
        return [
            w for w in self.maintenance_windows.values()
            if w.is_active(now)
        ]
    
    def get_pending_maintenance(self) -> List[MaintenanceWindow]:
        """Get all pending maintenance windows."""
        now = datetime.now()
        return [
            w for w in self.maintenance_windows.values()
            if w.is_pending(now)
        ]
    
    def get_conflicts(self, resolved: Optional[bool] = None) -> List[ReservationConflict]:
        """Get conflicts, optionally filtered by resolution status."""
        if resolved is None:
            return list(self.conflicts.values())
        
        return [
            c for c in self.conflicts.values()
            if c.resolved == resolved
        ]
    
    def _detect_conflicts(self, reservation: Reservation) -> List[ReservationConflict]:
        """Detect conflicts for a reservation."""
        conflicts = []
        
        # Check conflicts with other reservations
        for other in self.reservations.values():
            if other.id == reservation.id:
                continue
            
            if other.status not in [
                ReservationStatus.REQUESTED,
                ReservationStatus.CONFIRMED,
                ReservationStatus.ACTIVE,
            ]:
                continue
            
            # Check for time overlap
            if not reservation.overlaps(other):
                continue
            
            # For now, just check if they share any nodes
            reservation_nodes = set(reservation.allocated_nodes())
            other_nodes = set(other.allocated_nodes())
            
            if reservation_nodes.intersection(other_nodes):
                conflict_id = generate_id("conflict")
                conflict = ReservationConflict(
                    conflict_id=conflict_id,
                    reservation_a_id=reservation.id,
                    reservation_b_id=other.id,
                    conflict_type="reservation_overlap",
                )
                
                self.conflicts[conflict_id] = conflict
                conflicts.append(conflict)
        
        # Check conflicts with maintenance windows
        for window in self.maintenance_windows.values():
            if window.cancelled:
                continue
            
            # Check for time overlap
            if not reservation.overlaps(window):
                continue
            
            # Check for node overlap
            reservation_nodes = set(reservation.allocated_nodes())
            if any(window.affects_node(node_id) for node_id in reservation_nodes):
                conflict_id = generate_id("conflict")
                conflict = ReservationConflict(
                    conflict_id=conflict_id,
                    reservation_a_id=reservation.id,
                    maintenance_id=window.id,
                    conflict_type="maintenance_overlap",
                )
                
                self.conflicts[conflict_id] = conflict
                conflicts.append(conflict)
        
        return conflicts
    
    def _resolve_conflicts(self, conflicts: List[ReservationConflict]) -> bool:
        """Attempt to resolve conflicts using the current strategy."""
        if not conflicts:
            return True
        
        if self.conflict_strategy == ConflictResolution.FIRST_COME_FIRST_SERVED:
            return self._resolve_fcfs(conflicts)
        elif self.conflict_strategy == ConflictResolution.PRIORITY_BASED:
            return self._resolve_priority_based(conflicts)
        elif self.conflict_strategy == ConflictResolution.PREEMPTION:
            return self._resolve_preemption(conflicts)
        
        # Default to unresolved
        return False
    
    def _resolve_fcfs(self, conflicts: List[ReservationConflict]) -> bool:
        """Resolve conflicts using first-come-first-served strategy."""
        all_resolved = True
        
        for conflict in conflicts:
            if conflict.resolved:
                continue
            
            if conflict.conflict_type == "reservation_overlap":
                # Get the two reservations
                reservation_a = self.reservations.get(conflict.reservation_a_id)
                reservation_b = self.reservations.get(conflict.reservation_b_id)
                
                if not reservation_a or not reservation_b:
                    continue
                
                # The earlier reservation wins
                if reservation_a.request_time <= reservation_b.request_time:
                    # Cancel the newer reservation
                    if reservation_b.status != ReservationStatus.CANCELLED:
                        reservation_b.cancel("Conflict with earlier reservation")
                        conflict.resolve(
                            ConflictResolution.FIRST_COME_FIRST_SERVED,
                            f"Cancelled newer reservation {reservation_b.id}"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.FIRST_COME_FIRST_SERVED,
                            f"Reservation {reservation_b.id} was already cancelled"
                        )
                else:
                    # Cancel the newer reservation (A)
                    if reservation_a.status != ReservationStatus.CANCELLED:
                        reservation_a.cancel("Conflict with earlier reservation")
                        conflict.resolve(
                            ConflictResolution.FIRST_COME_FIRST_SERVED,
                            f"Cancelled newer reservation {reservation_a.id}"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.FIRST_COME_FIRST_SERVED,
                            f"Reservation {reservation_a.id} was already cancelled"
                        )
            
            elif conflict.conflict_type == "maintenance_overlap":
                # Maintenance always wins in FCFS
                reservation = self.reservations.get(conflict.reservation_a_id)
                maintenance = self.maintenance_windows.get(conflict.maintenance_id)
                
                if not reservation or not maintenance:
                    continue
                
                if maintenance.severity == "critical" or not maintenance.cancellable:
                    # Cancel the reservation
                    if reservation.status != ReservationStatus.CANCELLED:
                        reservation.cancel(f"Conflict with maintenance window {maintenance.id}")
                        conflict.resolve(
                            ConflictResolution.FIRST_COME_FIRST_SERVED,
                            f"Cancelled reservation {reservation.id} due to critical maintenance"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.FIRST_COME_FIRST_SERVED,
                            f"Reservation {reservation.id} was already cancelled"
                        )
                else:
                    # For non-critical maintenance, check timing
                    if maintenance.creation_time <= reservation.request_time:
                        # Maintenance was scheduled first
                        if reservation.status != ReservationStatus.CANCELLED:
                            reservation.cancel(f"Conflict with earlier maintenance window {maintenance.id}")
                            conflict.resolve(
                                ConflictResolution.FIRST_COME_FIRST_SERVED,
                                f"Cancelled reservation {reservation.id} due to earlier maintenance"
                            )
                        else:
                            conflict.resolve(
                                ConflictResolution.FIRST_COME_FIRST_SERVED,
                                f"Reservation {reservation.id} was already cancelled"
                            )
                    else:
                        # Reservation was scheduled first
                        if not maintenance.cancelled:
                            # Try to cancel maintenance
                            if maintenance.cancel(f"Conflict with earlier reservation {reservation.id}"):
                                conflict.resolve(
                                    ConflictResolution.FIRST_COME_FIRST_SERVED,
                                    f"Cancelled maintenance window {maintenance.id}"
                                )
                            else:
                                # Couldn't cancel maintenance
                                if reservation.status != ReservationStatus.CANCELLED:
                                    reservation.cancel(
                                        f"Conflict with non-cancellable maintenance window {maintenance.id}"
                                    )
                                    conflict.resolve(
                                        ConflictResolution.FIRST_COME_FIRST_SERVED,
                                        f"Cancelled reservation {reservation.id} due to non-cancellable maintenance"
                                    )
                                else:
                                    conflict.resolve(
                                        ConflictResolution.FIRST_COME_FIRST_SERVED,
                                        f"Reservation {reservation.id} was already cancelled"
                                    )
                        else:
                            conflict.resolve(
                                ConflictResolution.FIRST_COME_FIRST_SERVED,
                                f"Maintenance window {maintenance.id} was already cancelled"
                            )
            
            # Update all_resolved flag
            all_resolved = all_resolved and conflict.resolved
        
        return all_resolved
    
    def _resolve_priority_based(self, conflicts: List[ReservationConflict]) -> bool:
        """Resolve conflicts using priority-based strategy."""
        all_resolved = True
        
        for conflict in conflicts:
            if conflict.resolved:
                continue
            
            if conflict.conflict_type == "reservation_overlap":
                # Get the two reservations
                reservation_a = self.reservations.get(conflict.reservation_a_id)
                reservation_b = self.reservations.get(conflict.reservation_b_id)
                
                if not reservation_a or not reservation_b:
                    continue
                
                # Higher priority reservation wins
                if reservation_a.priority.value < reservation_b.priority.value:
                    # A has higher priority (lower value)
                    if reservation_b.status != ReservationStatus.CANCELLED:
                        reservation_b.cancel(f"Conflict with higher priority reservation {reservation_a.id}")
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Cancelled lower priority reservation {reservation_b.id}"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Reservation {reservation_b.id} was already cancelled"
                        )
                elif reservation_b.priority.value < reservation_a.priority.value:
                    # B has higher priority
                    if reservation_a.status != ReservationStatus.CANCELLED:
                        reservation_a.cancel(f"Conflict with higher priority reservation {reservation_b.id}")
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Cancelled lower priority reservation {reservation_a.id}"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Reservation {reservation_a.id} was already cancelled"
                        )
                else:
                    # Equal priority, fall back to FCFS
                    if reservation_a.request_time <= reservation_b.request_time:
                        if reservation_b.status != ReservationStatus.CANCELLED:
                            reservation_b.cancel(f"Conflict with earlier reservation {reservation_a.id}")
                            conflict.resolve(
                                ConflictResolution.PRIORITY_BASED,
                                f"Equal priority, cancelled newer reservation {reservation_b.id}"
                            )
                        else:
                            conflict.resolve(
                                ConflictResolution.PRIORITY_BASED,
                                f"Reservation {reservation_b.id} was already cancelled"
                            )
                    else:
                        if reservation_a.status != ReservationStatus.CANCELLED:
                            reservation_a.cancel(f"Conflict with earlier reservation {reservation_b.id}")
                            conflict.resolve(
                                ConflictResolution.PRIORITY_BASED,
                                f"Equal priority, cancelled newer reservation {reservation_a.id}"
                            )
                        else:
                            conflict.resolve(
                                ConflictResolution.PRIORITY_BASED,
                                f"Reservation {reservation_a.id} was already cancelled"
                            )
            
            elif conflict.conflict_type == "maintenance_overlap":
                # Get the reservation and maintenance window
                reservation = self.reservations.get(conflict.reservation_a_id)
                maintenance = self.maintenance_windows.get(conflict.maintenance_id)
                
                if not reservation or not maintenance:
                    continue
                
                # Critical maintenance always wins
                if maintenance.severity == "critical":
                    if reservation.status != ReservationStatus.CANCELLED:
                        reservation.cancel(f"Conflict with critical maintenance window {maintenance.id}")
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Cancelled reservation {reservation.id} due to critical maintenance"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Reservation {reservation.id} was already cancelled"
                        )
                elif reservation.priority == SimulationPriority.CRITICAL:
                    # Critical reservation wins over non-critical maintenance
                    if not maintenance.cancelled:
                        if maintenance.cancel(f"Conflict with critical reservation {reservation.id}"):
                            conflict.resolve(
                                ConflictResolution.PRIORITY_BASED,
                                f"Cancelled maintenance window {maintenance.id} due to critical reservation"
                            )
                        else:
                            # Couldn't cancel maintenance
                            all_resolved = False
                    else:
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Maintenance window {maintenance.id} was already cancelled"
                        )
                else:
                    # For other priorities, maintenance usually wins
                    if reservation.status != ReservationStatus.CANCELLED:
                        reservation.cancel(f"Conflict with maintenance window {maintenance.id}")
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Cancelled reservation {reservation.id} due to maintenance"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.PRIORITY_BASED,
                            f"Reservation {reservation.id} was already cancelled"
                        )
            
            # Update all_resolved flag
            all_resolved = all_resolved and conflict.resolved
        
        return all_resolved
    
    def _resolve_preemption(self, conflicts: List[ReservationConflict]) -> bool:
        """Resolve conflicts using preemption strategy."""
        all_resolved = True
        
        for conflict in conflicts:
            if conflict.resolved:
                continue
            
            if conflict.conflict_type == "reservation_overlap":
                # Get the two reservations
                reservation_a = self.reservations.get(conflict.reservation_a_id)
                reservation_b = self.reservations.get(conflict.reservation_b_id)
                
                if not reservation_a or not reservation_b:
                    continue
                
                # Try to preempt based on priority and preemptibility
                if (reservation_a.priority.value < reservation_b.priority.value and 
                    reservation_b.preemptible):
                    # A has higher priority, preempt B if active
                    if reservation_b.status == ReservationStatus.ACTIVE:
                        reservation_b.preempt(f"Preempted by higher priority reservation {reservation_a.id}")
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Preempted lower priority reservation {reservation_b.id}"
                        )
                    elif reservation_b.status != ReservationStatus.CANCELLED:
                        reservation_b.cancel(f"Conflict with higher priority reservation {reservation_a.id}")
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Cancelled lower priority reservation {reservation_b.id}"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Reservation {reservation_b.id} was already cancelled"
                        )
                
                elif (reservation_b.priority.value < reservation_a.priority.value and 
                      reservation_a.preemptible):
                    # B has higher priority, preempt A if active
                    if reservation_a.status == ReservationStatus.ACTIVE:
                        reservation_a.preempt(f"Preempted by higher priority reservation {reservation_b.id}")
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Preempted lower priority reservation {reservation_a.id}"
                        )
                    elif reservation_a.status != ReservationStatus.CANCELLED:
                        reservation_a.cancel(f"Conflict with higher priority reservation {reservation_b.id}")
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Cancelled lower priority reservation {reservation_a.id}"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Reservation {reservation_a.id} was already cancelled"
                        )
                
                else:
                    # Can't preempt, fall back to priority-based
                    resolved = self._resolve_priority_based([conflict])
                    all_resolved = all_resolved and resolved
                    continue
            
            elif conflict.conflict_type == "maintenance_overlap":
                # Get the reservation and maintenance window
                reservation = self.reservations.get(conflict.reservation_a_id)
                maintenance = self.maintenance_windows.get(conflict.maintenance_id)
                
                if not reservation or not maintenance:
                    continue
                
                # Critical maintenance always wins
                if maintenance.severity == "critical":
                    if reservation.status == ReservationStatus.ACTIVE:
                        reservation.preempt(f"Preempted by critical maintenance window {maintenance.id}")
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Preempted reservation {reservation.id} due to critical maintenance"
                        )
                    elif reservation.status != ReservationStatus.CANCELLED:
                        reservation.cancel(f"Conflict with critical maintenance window {maintenance.id}")
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Cancelled reservation {reservation.id} due to critical maintenance"
                        )
                    else:
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Reservation {reservation.id} was already cancelled"
                        )
                elif reservation.priority == SimulationPriority.CRITICAL:
                    # Critical reservation wins over non-critical maintenance
                    if not maintenance.cancelled:
                        if maintenance.cancel(f"Conflict with critical reservation {reservation.id}"):
                            conflict.resolve(
                                ConflictResolution.PREEMPTION,
                                f"Cancelled maintenance window {maintenance.id} due to critical reservation"
                            )
                        else:
                            # Couldn't cancel maintenance
                            all_resolved = False
                    else:
                        conflict.resolve(
                            ConflictResolution.PREEMPTION,
                            f"Maintenance window {maintenance.id} was already cancelled"
                        )
                else:
                    # For other priorities, check if reservation can be preempted
                    if reservation.preemptible:
                        if reservation.status == ReservationStatus.ACTIVE:
                            reservation.preempt(f"Preempted by maintenance window {maintenance.id}")
                            conflict.resolve(
                                ConflictResolution.PREEMPTION,
                                f"Preempted reservation {reservation.id} due to maintenance"
                            )
                        elif reservation.status != ReservationStatus.CANCELLED:
                            reservation.cancel(f"Conflict with maintenance window {maintenance.id}")
                            conflict.resolve(
                                ConflictResolution.PREEMPTION,
                                f"Cancelled reservation {reservation.id} due to maintenance"
                            )
                        else:
                            conflict.resolve(
                                ConflictResolution.PREEMPTION,
                                f"Reservation {reservation.id} was already cancelled"
                            )
                    else:
                        # Can't preempt, try to cancel maintenance if possible
                        if not maintenance.cancelled and maintenance.cancellable:
                            if maintenance.cancel(f"Conflict with non-preemptible reservation {reservation.id}"):
                                conflict.resolve(
                                    ConflictResolution.PREEMPTION,
                                    f"Cancelled maintenance window {maintenance.id} due to non-preemptible reservation"
                                )
                            else:
                                all_resolved = False
                        else:
                            all_resolved = False
            
            # Update all_resolved flag
            all_resolved = all_resolved and conflict.resolved
        
        return all_resolved
    
    def _force_resolve_conflicts(self, conflicts: List[ReservationConflict], reason: str) -> None:
        """Force resolution of conflicts by cancelling reservations."""
        for conflict in conflicts:
            if conflict.resolved:
                continue
            
            if conflict.conflict_type == "reservation_overlap":
                # Cancel both reservations in the worst case
                reservation_a = self.reservations.get(conflict.reservation_a_id)
                reservation_b = self.reservations.get(conflict.reservation_b_id)
                
                if reservation_a and reservation_a.status != ReservationStatus.CANCELLED:
                    reservation_a.cancel(f"Forced conflict resolution: {reason}")
                
                if reservation_b and reservation_b.status != ReservationStatus.CANCELLED:
                    reservation_b.cancel(f"Forced conflict resolution: {reason}")
                
                conflict.resolve(
                    ConflictResolution.ADMIN_DECISION,
                    f"Forced resolution by cancelling reservations: {reason}"
                )
            
            elif conflict.conflict_type == "maintenance_overlap":
                # Cancel the reservation, preserve maintenance
                reservation = self.reservations.get(conflict.reservation_a_id)
                
                if reservation and reservation.status != ReservationStatus.CANCELLED:
                    reservation.cancel(f"Forced conflict resolution: {reason}")
                
                conflict.resolve(
                    ConflictResolution.ADMIN_DECISION,
                    f"Forced resolution by cancelling reservation: {reason}"
                )