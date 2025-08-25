"""Failure detection system for compute nodes and simulations."""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Dict, List, Optional, Set, Tuple, Union

# Import from common library
from common.failure_handling.failure_detector import FailureDetector as CommonFailureDetector
from common.core.models import BaseJob, BaseNode, NodeStatus

# Import simulation-specific models
from concurrent_task_scheduler.models import (
    ComputeNode,
    ExtendedNodeStatus,
    Result,
    Simulation,
    SimulationStage,
    SimulationStageStatus,
    SystemEvent,
)
from concurrent_task_scheduler.models.utils import generate_id

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    """Types of failures that can be detected."""

    NODE_OFFLINE = "node_offline"  # Node is completely offline
    NODE_DEGRADED = "node_degraded"  # Node is degraded but still functioning
    PROCESS_CRASH = "process_crash"  # Simulation process crashed
    MEMORY_EXHAUSTION = "memory_exhaustion"  # Out of memory
    DISK_FULL = "disk_full"  # Disk space exhaustion
    NETWORK_FAILURE = "network_failure"  # Network connectivity issue
    RESOURCE_CONTENTION = "resource_contention"  # Resource contention with other jobs
    DEADLOCK = "deadlock"  # Simulation is deadlocked
    TIMEOUT = "timeout"  # Simulation exceeded time limit
    STORAGE_FAILURE = "storage_failure"  # Storage system failure
    UNKNOWN = "unknown"  # Unknown failure


class FailureSeverity(str, Enum):
    """Severity levels for failures."""

    CRITICAL = "critical"  # Critical failure requiring immediate attention
    HIGH = "high"  # High severity failure
    MEDIUM = "medium"  # Medium severity failure
    LOW = "low"  # Low severity failure
    INFO = "info"  # Informational, not a true failure


class DetectionMethod(str, Enum):
    """Methods used to detect failures."""

    HEARTBEAT = "heartbeat"  # Heartbeat monitoring
    METRICS = "metrics"  # Metrics-based detection
    LOG_ANALYSIS = "log_analysis"  # Log analysis
    SYSTEM_REPORT = "system_report"  # System-reported failure
    MANUAL = "manual"  # Manually reported
    PREDICTION = "prediction"  # Predictive detection


class FailureReport:
    """Report of a detected failure."""

    def __init__(
        self,
        id: str,
        failure_type: FailureType,
        severity: FailureSeverity,
        detection_time: datetime,
        detection_method: DetectionMethod,
        node_id: Optional[str] = None,
        simulation_id: Optional[str] = None,
        stage_id: Optional[str] = None,
        description: Optional[str] = None,
        details: Optional[Dict[str, str]] = None,
    ):
        self.id = id
        self.failure_type = failure_type
        self.severity = severity
        self.detection_time = detection_time
        self.detection_method = detection_method
        self.node_id = node_id
        self.simulation_id = simulation_id
        self.stage_id = stage_id
        self.description = description or self._generate_description()
        self.details = details or {}
        self.recovery_attempts: List[Dict] = []
        self.resolved = False
        self.resolution_time: Optional[datetime] = None
        self.resolution_method: Optional[str] = None
        
        # Automatically populate description if not provided
        if not description:
            self.description = self._generate_description()
    
    def _generate_description(self) -> str:
        """Generate a description based on the failure type and affected resources."""
        parts = []
        
        # Add failure type
        if self.failure_type == FailureType.NODE_OFFLINE:
            parts.append("Node went offline")
        elif self.failure_type == FailureType.NODE_DEGRADED:
            parts.append("Node experiencing degraded performance")
        elif self.failure_type == FailureType.PROCESS_CRASH:
            parts.append("Simulation process crashed")
        elif self.failure_type == FailureType.MEMORY_EXHAUSTION:
            parts.append("Memory exhaustion")
        elif self.failure_type == FailureType.DISK_FULL:
            parts.append("Disk space exhaustion")
        elif self.failure_type == FailureType.NETWORK_FAILURE:
            parts.append("Network connectivity issue")
        elif self.failure_type == FailureType.RESOURCE_CONTENTION:
            parts.append("Resource contention detected")
        elif self.failure_type == FailureType.DEADLOCK:
            parts.append("Simulation deadlock detected")
        elif self.failure_type == FailureType.TIMEOUT:
            parts.append("Simulation exceeded time limit")
        elif self.failure_type == FailureType.STORAGE_FAILURE:
            parts.append("Storage system failure")
        else:
            parts.append("Unknown failure")
        
        # Add affected resources
        if self.node_id:
            parts.append(f"on node {self.node_id}")
        
        if self.simulation_id:
            parts.append(f"affecting simulation {self.simulation_id}")
            
            if self.stage_id:
                parts.append(f"stage {self.stage_id}")
        
        return " ".join(parts)
    
    def add_recovery_attempt(
        self,
        method: str,
        time: datetime,
        success: bool,
        details: Optional[Dict] = None,
    ) -> None:
        """Record a recovery attempt."""
        self.recovery_attempts.append({
            "method": method,
            "time": time,
            "success": success,
            "details": details or {},
        })
    
    def mark_resolved(self, method: str) -> None:
        """Mark the failure as resolved."""
        self.resolved = True
        self.resolution_time = datetime.now()
        self.resolution_method = method
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "failure_type": self.failure_type.value,
            "severity": self.severity.value,
            "detection_time": self.detection_time.isoformat(),
            "detection_method": self.detection_method.value,
            "node_id": self.node_id,
            "simulation_id": self.simulation_id,
            "stage_id": self.stage_id,
            "description": self.description,
            "details": self.details,
            "recovery_attempts": self.recovery_attempts,
            "resolved": self.resolved,
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None,
            "resolution_method": self.resolution_method,
        }


class NodeHealthCheck:
    """Health check for a compute node."""

    def __init__(
        self,
        node_id: str,
        check_time: datetime,
        status: NodeStatus,
        metrics: Optional[Dict[str, float]] = None,
    ):
        self.node_id = node_id
        self.check_time = check_time
        self.status = status
        self.metrics = metrics or {}
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the health check."""
        self.warnings.append(warning)
    
    def add_error(self, error: str) -> None:
        """Add an error to the health check."""
        self.errors.append(error)
    
    def is_healthy(self) -> bool:
        """Check if the node is healthy."""
        return self.status == NodeStatus.ONLINE and not self.errors


class FailureDetector:
    """System for detecting node and simulation failures."""

    def __init__(
        self,
        heartbeat_interval: int = 30,  # seconds
        heartbeat_timeout: int = 90,  # seconds
    ):
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.last_heartbeat: Dict[str, datetime] = {}  # node_id -> last_heartbeat_time
        self.node_health_history: Dict[str, List[NodeHealthCheck]] = {}  # node_id -> [health_checks]
        self.simulation_health_history: Dict[str, Dict[str, datetime]] = {}  # sim_id -> {status_update_type -> time}
        self.failure_reports: Dict[str, FailureReport] = {}  # failure_id -> report
        self.node_failure_counts: Dict[str, int] = {}  # node_id -> count
        self.simulation_failure_counts: Dict[str, int] = {}  # sim_id -> count
        
        # Thresholds for failure detection
        self.thresholds = {
            "cpu_load": 0.95,  # 95% CPU usage
            "memory_usage": 0.95,  # 95% memory usage
            "disk_usage": 0.95,  # 95% disk usage
            "network_errors": 10,  # 10 errors per minute
            "process_restart_attempts": 3,  # 3 restart attempts
            "simulation_progress_stall_minutes": 60,  # 60 minutes without progress
        }
    
    def record_heartbeat(self, node_id: str) -> None:
        """Record a heartbeat from a node."""
        self.last_heartbeat[node_id] = datetime.now()
    
    def check_node_health(self, node: ComputeNode) -> NodeHealthCheck:
        """Check the health of a node."""
        now = datetime.now()
        health_check = NodeHealthCheck(
            node_id=node.id,
            check_time=now,
            status=node.status,
        )
        
        # Check heartbeat
        last_hb = self.last_heartbeat.get(node.id)
        if not last_hb:
            health_check.add_warning(f"No heartbeat recorded for node {node.id}")
        elif (now - last_hb).total_seconds() > self.heartbeat_timeout:
            health_check.add_error(
                f"Heartbeat timeout: last heartbeat was {(now - last_hb).total_seconds():.1f}s ago"
            )
        
        # Check metrics (simulated)
        cpu_load = node.current_load.get(
            "cpu",
            random.uniform(0.1, 0.9)  # Simulated value
        )
        memory_usage = node.current_load.get(
            "memory",
            random.uniform(0.1, 0.9)  # Simulated value
        )
        disk_usage = node.current_load.get(
            "storage",
            random.uniform(0.1, 0.9)  # Simulated value
        )
        
        health_check.metrics = {
            "cpu_load": cpu_load,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "network_errors": random.randint(0, 5),  # Simulated value
        }
        
        # Check thresholds
        if cpu_load > self.thresholds["cpu_load"]:
            health_check.add_warning(f"High CPU load: {cpu_load:.1%}")
        
        if memory_usage > self.thresholds["memory_usage"]:
            health_check.add_warning(f"High memory usage: {memory_usage:.1%}")
        
        if disk_usage > self.thresholds["disk_usage"]:
            health_check.add_error(f"High disk usage: {disk_usage:.1%}")
        
        network_errors = health_check.metrics.get("network_errors", 0)
        if network_errors > self.thresholds["network_errors"]:
            health_check.add_error(f"High network errors: {network_errors}")
        
        # Store health check
        if node.id not in self.node_health_history:
            self.node_health_history[node.id] = []
        
        self.node_health_history[node.id].append(health_check)
        
        # Limit history size
        if len(self.node_health_history[node.id]) > 100:
            self.node_health_history[node.id] = self.node_health_history[node.id][-100:]
        
        return health_check
    
    def check_simulation_health(
        self,
        simulation: Simulation,
        progress_window_minutes: int = 60,
    ) -> List[str]:
        """
        Check the health of a simulation.
        
        Returns a list of warnings/errors.
        """
        now = datetime.now()
        warnings = []
        
        # Initialize history if not exists
        if simulation.id not in self.simulation_health_history:
            self.simulation_health_history[simulation.id] = {
                "last_progress_update": now,
                "last_status_change": now,
                "last_health_check": now,
            }
        
        history = self.simulation_health_history[simulation.id]
        
        # Check for progress stalls
        last_progress = history.get("last_progress_update", now)
        minutes_since_progress = (now - last_progress).total_seconds() / 60
        
        if minutes_since_progress > self.thresholds["simulation_progress_stall_minutes"]:
            warnings.append(
                f"Simulation progress stalled for {minutes_since_progress:.1f} minutes"
            )
        
        # Update last health check
        history["last_health_check"] = now
        
        return warnings
    
    def update_simulation_progress(self, simulation_id: str, progress: float) -> None:
        """Record a progress update for a simulation."""
        now = datetime.now()
        
        # Initialize history if not exists
        if simulation_id not in self.simulation_health_history:
            self.simulation_health_history[simulation_id] = {}
        
        # Update last progress update time
        self.simulation_health_history[simulation_id]["last_progress_update"] = now
    
    def update_simulation_status(self, simulation_id: str, status: str) -> None:
        """Record a status change for a simulation."""
        now = datetime.now()
        
        # Initialize history if not exists
        if simulation_id not in self.simulation_health_history:
            self.simulation_health_history[simulation_id] = {}
        
        # Update last status change time
        self.simulation_health_history[simulation_id]["last_status_change"] = now
    
    def detect_node_failures(
        self,
        nodes: Dict[str, ComputeNode],
    ) -> List[FailureReport]:
        """Detect failures in compute nodes."""
        failures = []
        
        for node_id, node in nodes.items():
            # Check node health
            health_check = self.check_node_health(node)
            
            # Generate failure reports for errors
            for error in health_check.errors:
                failure_type = self._determine_failure_type(error)
                
                failure = FailureReport(
                    id=generate_id("failure"),
                    failure_type=failure_type,
                    severity=FailureSeverity.HIGH,
                    detection_time=datetime.now(),
                    detection_method=DetectionMethod.METRICS,
                    node_id=node_id,
                    description=error,
                )
                
                failures.append(failure)
                self.failure_reports[failure.id] = failure
                
                # Update node failure count
                count = self.node_failure_counts.get(node_id, 0) + 1
                self.node_failure_counts[node_id] = count
        
        return failures
    
    def detect_simulation_failures(
        self,
        simulations: Dict[str, Simulation],
    ) -> List[FailureReport]:
        """Detect failures in simulations."""
        failures = []
        
        for sim_id, simulation in simulations.items():
            # Skip non-running simulations
            if simulation.status not in ["running", "paused"]:
                continue
            
            # Check simulation health
            health_warnings = self.check_simulation_health(simulation)
            
            # Generate failure reports for warnings
            for warning in health_warnings:
                failure_type = self._determine_failure_type(warning)
                
                failure = FailureReport(
                    id=generate_id("failure"),
                    failure_type=failure_type,
                    severity=FailureSeverity.MEDIUM,
                    detection_time=datetime.now(),
                    detection_method=DetectionMethod.METRICS,
                    simulation_id=sim_id,
                    description=warning,
                )
                
                failures.append(failure)
                self.failure_reports[failure.id] = failure
                
                # Update simulation failure count
                count = self.simulation_failure_counts.get(sim_id, 0) + 1
                self.simulation_failure_counts[sim_id] = count
            
            # Check stages for stalls
            for stage_id, stage in simulation.stages.items():
                if stage.status == SimulationStageStatus.RUNNING:
                    # Check if stage is making progress
                    if stage.start_time:
                        time_running = (datetime.now() - stage.start_time).total_seconds() / 60
                        estimated_time = stage.estimated_duration.total_seconds() / 60
                        
                        # If running for 2x the estimated time with < 50% progress, consider it stalled
                        if time_running > 2 * estimated_time and stage.progress < 0.5:
                            failure = FailureReport(
                                id=generate_id("failure"),
                                failure_type=FailureType.TIMEOUT,
                                severity=FailureSeverity.MEDIUM,
                                detection_time=datetime.now(),
                                detection_method=DetectionMethod.METRICS,
                                simulation_id=sim_id,
                                stage_id=stage_id,
                                description=f"Stage {stage_id} appears stalled: running for {time_running:.1f} minutes with only {stage.progress:.1%} progress",
                            )
                            
                            failures.append(failure)
                            self.failure_reports[failure.id] = failure
        
        return failures
    
    def record_failure(self, failure: FailureReport) -> None:
        """Record an existing failure report."""
        self.failure_reports[failure.id] = failure
        
        # Update failure counts
        if failure.node_id:
            count = self.node_failure_counts.get(failure.node_id, 0) + 1
            self.node_failure_counts[failure.node_id] = count
        
        if failure.simulation_id:
            count = self.simulation_failure_counts.get(failure.simulation_id, 0) + 1
            self.simulation_failure_counts[failure.simulation_id] = count
    
    def report_failure(
        self,
        failure_type: FailureType,
        severity: FailureSeverity,
        description: str,
        node_id: Optional[str] = None,
        simulation_id: Optional[str] = None,
        stage_id: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> FailureReport:
        """Manually report a failure."""
        failure = FailureReport(
            id=generate_id("failure"),
            failure_type=failure_type,
            severity=severity,
            detection_time=datetime.now(),
            detection_method=DetectionMethod.MANUAL,
            node_id=node_id,
            simulation_id=simulation_id,
            stage_id=stage_id,
            description=description,
            details=details,
        )
        
        self.failure_reports[failure.id] = failure
        
        # Update failure counts
        if node_id:
            count = self.node_failure_counts.get(node_id, 0) + 1
            self.node_failure_counts[node_id] = count
        
        if simulation_id:
            count = self.simulation_failure_counts.get(simulation_id, 0) + 1
            self.simulation_failure_counts[simulation_id] = count
        
        return failure
    
    def get_active_failures(
        self,
        node_id: Optional[str] = None,
        simulation_id: Optional[str] = None,
    ) -> List[FailureReport]:
        """Get all active (unresolved) failures."""
        failures = [
            f for f in self.failure_reports.values()
            if not f.resolved
        ]
        
        # Filter by node_id if specified
        if node_id:
            failures = [f for f in failures if f.node_id == node_id]
        
        # Filter by simulation_id if specified
        if simulation_id:
            failures = [f for f in failures if f.simulation_id == simulation_id]
        
        return failures
    
    def resolve_failure(
        self,
        failure_id: str,
        resolution_method: str,
    ) -> Result[bool]:
        """Mark a failure as resolved."""
        if failure_id not in self.failure_reports:
            return Result.err(f"Failure {failure_id} not found")
        
        failure = self.failure_reports[failure_id]
        
        if failure.resolved:
            return Result.err(f"Failure {failure_id} is already resolved")
        
        failure.mark_resolved(resolution_method)
        return Result.ok(True)
    
    def get_node_reliability_score(self, node_id: str) -> float:
        """Calculate a reliability score for a node (0-1)."""
        if node_id not in self.node_health_history:
            return 1.0  # No history, assume reliable
        
        # Get recent health checks
        recent_checks = self.node_health_history[node_id][-10:]
        
        if not recent_checks:
            return 1.0
        
        # Count healthy checks
        healthy_count = sum(1 for check in recent_checks if check.is_healthy())
        return healthy_count / len(recent_checks)
    
    def get_simulation_failure_rate(self, simulation_id: str) -> float:
        """Calculate failure rate for a simulation (failures per hour)."""
        if simulation_id not in self.simulation_health_history:
            return 0.0  # No history, assume no failures
        
        history = self.simulation_health_history[simulation_id]
        start_time = min(history.values())
        hours_running = (datetime.now() - start_time).total_seconds() / 3600
        
        if hours_running < 0.1:  # Less than 6 minutes
            return 0.0
        
        failure_count = self.simulation_failure_counts.get(simulation_id, 0)
        return failure_count / hours_running
    
    def _determine_failure_type(self, error_message: str) -> FailureType:
        """Determine the type of failure from an error message."""
        # Simple pattern matching
        error_lower = error_message.lower()
        
        if "heartbeat timeout" in error_lower:
            return FailureType.NODE_OFFLINE
        elif "cpu load" in error_lower:
            return FailureType.RESOURCE_CONTENTION
        elif "memory" in error_lower:
            return FailureType.MEMORY_EXHAUSTION
        elif "disk" in error_lower:
            return FailureType.DISK_FULL
        elif "network" in error_lower:
            return FailureType.NETWORK_FAILURE
        elif "stalled" in error_lower:
            return FailureType.DEADLOCK
        elif "timeout" in error_lower or "exceeded" in error_lower:
            return FailureType.TIMEOUT
        elif "storage" in error_lower:
            return FailureType.STORAGE_FAILURE
        elif "crash" in error_lower:
            return FailureType.PROCESS_CRASH
        
        return FailureType.UNKNOWN


class RecoveryStrategy(str, Enum):
    """Strategies for recovering from failures."""

    RESTART = "restart"  # Restart the simulation or node
    RESTORE_CHECKPOINT = "restore_checkpoint"  # Restore from checkpoint
    MIGRATE = "migrate"  # Migrate to different nodes
    PARTIAL_RESTART = "partial_restart"  # Restart only failed components
    RECONFIGURE = "reconfigure"  # Reconfigure and restart
    ROLLBACK = "rollback"  # Rollback to previous state
    IGNORE = "ignore"  # Ignore the failure and continue


class FailureRecoveryManager:
    """Manager for recovering from failures."""

    def __init__(self, detector: FailureDetector):
        self.detector = detector
        self.recovery_strategies: Dict[FailureType, List[RecoveryStrategy]] = {
            FailureType.NODE_OFFLINE: [
                RecoveryStrategy.MIGRATE,
                RecoveryStrategy.RESTORE_CHECKPOINT,
            ],
            FailureType.NODE_DEGRADED: [
                RecoveryStrategy.MIGRATE,
                RecoveryStrategy.RECONFIGURE,
            ],
            FailureType.PROCESS_CRASH: [
                RecoveryStrategy.RESTART,
                RecoveryStrategy.RESTORE_CHECKPOINT,
            ],
            FailureType.MEMORY_EXHAUSTION: [
                RecoveryStrategy.RECONFIGURE,
                RecoveryStrategy.RESTART,
            ],
            FailureType.DISK_FULL: [
                RecoveryStrategy.IGNORE,  # Need manual intervention
            ],
            FailureType.NETWORK_FAILURE: [
                RecoveryStrategy.RESTART,
                RecoveryStrategy.MIGRATE,
            ],
            FailureType.RESOURCE_CONTENTION: [
                RecoveryStrategy.RECONFIGURE,
                RecoveryStrategy.MIGRATE,
            ],
            FailureType.DEADLOCK: [
                RecoveryStrategy.RESTART,
                RecoveryStrategy.RESTORE_CHECKPOINT,
            ],
            FailureType.TIMEOUT: [
                RecoveryStrategy.RESTART,
                RecoveryStrategy.RECONFIGURE,
            ],
            FailureType.STORAGE_FAILURE: [
                RecoveryStrategy.MIGRATE,
                RecoveryStrategy.RESTORE_CHECKPOINT,
            ],
            FailureType.UNKNOWN: [
                RecoveryStrategy.RESTORE_CHECKPOINT,
                RecoveryStrategy.RESTART,
            ],
        }
        self.max_recovery_attempts = 3
        self.recovery_backoff_minutes = 5
        self.recovery_in_progress: Dict[str, RecoveryStrategy] = {}  # failure_id -> strategy
        self.recovery_history: Dict[str, List[Dict]] = {}  # simulation_id -> [{recovery_info}]
    
    def get_recovery_strategy(
        self,
        failure: FailureReport,
        previous_attempts: List[RecoveryStrategy] = None,
    ) -> Optional[RecoveryStrategy]:
        """Get the best recovery strategy for a failure."""
        if not previous_attempts:
            previous_attempts = []
        
        # Get available strategies for this failure type
        available_strategies = self.recovery_strategies.get(
            failure.failure_type,
            [RecoveryStrategy.RESTART]
        )
        
        # Filter out previously tried strategies
        untried_strategies = [
            s for s in available_strategies
            if s not in previous_attempts
        ]
        
        if not untried_strategies:
            # If all strategies tried, retry the first one
            return available_strategies[0] if available_strategies else None
        
        # Return first untried strategy
        return untried_strategies[0]
    
    def initiate_recovery(
        self,
        failure_id: str,
        strategy: Optional[RecoveryStrategy] = None,
    ) -> Result[RecoveryStrategy]:
        """Initiate recovery for a failure."""
        # Get failure report
        if failure_id not in self.detector.failure_reports:
            return Result.err(f"Failure {failure_id} not found")
        
        failure = self.detector.failure_reports[failure_id]
        
        # Check if already resolved
        if failure.resolved:
            return Result.err(f"Failure {failure_id} is already resolved")
        
        # Check if recovery is already in progress
        if failure_id in self.recovery_in_progress:
            return Result.err(
                f"Recovery already in progress for failure {failure_id} "
                f"using strategy {self.recovery_in_progress[failure_id]}"
            )
        
        # Check if max attempts reached
        if len(failure.recovery_attempts) >= self.max_recovery_attempts:
            return Result.err(
                f"Maximum recovery attempts ({self.max_recovery_attempts}) "
                f"reached for failure {failure_id}"
            )
        
        # Get recovery strategy if not specified
        if not strategy:
            previous_strategies = [
                RecoveryStrategy(attempt["method"])
                for attempt in failure.recovery_attempts
            ]
            strategy = self.get_recovery_strategy(failure, previous_strategies)
            
            if not strategy:
                return Result.err(f"No recovery strategy available for failure {failure_id}")
        
        # Record recovery attempt
        failure.add_recovery_attempt(
            method=strategy.value,
            time=datetime.now(),
            success=False,  # Will be updated when complete
            details={"status": "initiated"},
        )
        
        # Add to in-progress recoveries
        self.recovery_in_progress[failure_id] = strategy
        
        # Add to recovery history
        if failure.simulation_id:
            if failure.simulation_id not in self.recovery_history:
                self.recovery_history[failure.simulation_id] = []
            
            self.recovery_history[failure.simulation_id].append({
                "failure_id": failure_id,
                "strategy": strategy.value,
                "initiated_at": datetime.now().isoformat(),
                "completed": False,
            })
        
        return Result.ok(strategy)
    
    def complete_recovery(
        self,
        failure_id: str,
        success: bool,
        details: Optional[Dict] = None,
    ) -> Result[bool]:
        """Mark a recovery attempt as complete."""
        # Get failure report
        if failure_id not in self.detector.failure_reports:
            return Result.err(f"Failure {failure_id} not found")
        
        failure = self.detector.failure_reports[failure_id]
        
        # Check if recovery is in progress
        if failure_id not in self.recovery_in_progress:
            return Result.err(f"No recovery in progress for failure {failure_id}")
        
        strategy = self.recovery_in_progress[failure_id]
        
        # Remove from in-progress
        del self.recovery_in_progress[failure_id]
        
        # Update recovery attempt
        if failure.recovery_attempts:
            attempt = failure.recovery_attempts[-1]
            attempt["success"] = success
            attempt["details"] = details or {}
            attempt["completion_time"] = datetime.now().isoformat()
        
        # If successful, mark failure as resolved
        if success:
            failure.mark_resolved(f"Recovery with strategy {strategy}")
        
        # Update recovery history
        if failure.simulation_id and failure.simulation_id in self.recovery_history:
            for entry in self.recovery_history[failure.simulation_id]:
                if entry.get("failure_id") == failure_id and not entry.get("completed"):
                    entry["completed"] = True
                    entry["success"] = success
                    entry["completed_at"] = datetime.now().isoformat()
                    if details:
                        entry["details"] = details
        
        return Result.ok(success)
    
    def get_active_recoveries(self) -> Dict[str, RecoveryStrategy]:
        """Get all active recovery operations."""
        return self.recovery_in_progress.copy()
    
    def cancel_recovery(self, failure_id: str) -> Result[bool]:
        """Cancel an in-progress recovery."""
        # Check if recovery is in progress
        if failure_id not in self.recovery_in_progress:
            return Result.err(f"No recovery in progress for failure {failure_id}")
        
        # Get failure report
        failure = self.detector.failure_reports.get(failure_id)
        
        # Remove from in-progress
        del self.recovery_in_progress[failure_id]
        
        # Update recovery attempt if failure exists
        if failure and failure.recovery_attempts:
            attempt = failure.recovery_attempts[-1]
            attempt["success"] = False
            attempt["details"] = {"status": "cancelled"}
            attempt["completion_time"] = datetime.now().isoformat()
        
        # Update recovery history
        if failure and failure.simulation_id and failure.simulation_id in self.recovery_history:
            for entry in self.recovery_history[failure.simulation_id]:
                if entry.get("failure_id") == failure_id and not entry.get("completed"):
                    entry["completed"] = True
                    entry["success"] = False
                    entry["completed_at"] = datetime.now().isoformat()
                    entry["details"] = {"status": "cancelled"}
        
        return Result.ok(True)
    
    def process_failures(self) -> List[str]:
        """Process all unresolved failures and initiate recovery if needed."""
        # Get all unresolved failures
        unresolved = [
            f for f in self.detector.failure_reports.values()
            if not f.resolved and f.id not in self.recovery_in_progress
        ]
        
        # Sort by severity (critical first)
        severity_priority = {
            FailureSeverity.CRITICAL: 0,
            FailureSeverity.HIGH: 1,
            FailureSeverity.MEDIUM: 2,
            FailureSeverity.LOW: 3,
            FailureSeverity.INFO: 4,
        }
        
        unresolved.sort(
            key=lambda f: (
                severity_priority.get(f.severity, 999),
                -(datetime.now() - f.detection_time).total_seconds()
            )
        )
        
        # Process up to 5 failures at a time
        processed = []
        
        for failure in unresolved[:5]:
            # Check if already in progress
            if failure.id in self.recovery_in_progress:
                continue
            
            # Check if enough time has passed since last attempt
            if failure.recovery_attempts:
                last_attempt = failure.recovery_attempts[-1]
                last_time = datetime.fromisoformat(
                    last_attempt.get("completion_time", last_attempt["time"].isoformat())
                )
                
                backoff = self.recovery_backoff_minutes * (2 ** (len(failure.recovery_attempts) - 1))
                if (datetime.now() - last_time).total_seconds() < backoff * 60:
                    continue
            
            # Initiate recovery
            result = self.initiate_recovery(failure.id)
            
            if result.success:
                processed.append(failure.id)
            
            # Limit to 3 new recoveries at once
            if len(processed) >= 3:
                break
        
        return processed