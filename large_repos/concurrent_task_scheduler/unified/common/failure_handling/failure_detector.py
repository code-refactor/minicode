"""Failure detection for the unified task scheduling library."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
import logging
import statistics

from ..core.models import BaseJob, BaseNode, JobStatus, NodeStatus
from ..core.interfaces import FailureHandlerInterface
from ..core.result import Result, ErrorCode


logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    """Types of failures that can be detected."""
    JOB_TIMEOUT = "job_timeout"
    JOB_CRASH = "job_crash"
    NODE_OFFLINE = "node_offline"
    NODE_UNRESPONSIVE = "node_unresponsive"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_PARTITION = "network_partition"
    DEPENDENCY_FAILURE = "dependency_failure"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CASCADING_FAILURE = "cascading_failure"


class FailureSeverity(str, Enum):
    """Severity levels for failures."""
    LOW = "low"          # Minor issues that don't affect functionality
    MEDIUM = "medium"    # Issues that affect performance or some functionality
    HIGH = "high"        # Issues that significantly impact operations
    CRITICAL = "critical"  # Issues that cause system-wide problems


@dataclass
class FailureEvent:
    """Represents a detected failure."""
    failure_id: str
    failure_type: FailureType
    severity: FailureSeverity
    affected_entity_id: str  # Job ID, Node ID, etc.
    entity_type: str  # "job", "node", etc.
    detection_time: datetime = field(default_factory=datetime.now)
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    related_failures: List[str] = field(default_factory=list)  # Related failure IDs
    
    def age(self) -> timedelta:
        """Get the age of this failure."""
        return datetime.now() - self.detection_time


@dataclass
class HealthMetrics:
    """Health metrics for an entity."""
    entity_id: str
    entity_type: str
    metrics: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_metric(self, name: str, default: float = 0.0) -> float:
        """Get a specific metric value."""
        return self.metrics.get(name, default)
    
    def set_metric(self, name: str, value: float):
        """Set a metric value."""
        self.metrics[name] = value
        self.last_updated = datetime.now()


class FailureDetector(FailureHandlerInterface):
    """
    Failure detector for the unified task scheduling library.
    
    This class handles:
    - Detecting various types of failures
    - Monitoring health metrics
    - Triggering failure events
    - Maintaining failure history
    """
    
    def __init__(self,
                 job_timeout_threshold: timedelta = timedelta(hours=6),
                 node_heartbeat_timeout: timedelta = timedelta(minutes=10),
                 performance_degradation_threshold: float = 0.5,
                 resource_exhaustion_threshold: float = 0.95):
        """
        Initialize the failure detector.
        
        Args:
            job_timeout_threshold: Threshold for detecting job timeouts
            node_heartbeat_timeout: Threshold for detecting node failures
            performance_degradation_threshold: Threshold for performance issues (0-1)
            resource_exhaustion_threshold: Threshold for resource exhaustion (0-1)
        """
        self.job_timeout_threshold = job_timeout_threshold
        self.node_heartbeat_timeout = node_heartbeat_timeout
        self.performance_degradation_threshold = performance_degradation_threshold
        self.resource_exhaustion_threshold = resource_exhaustion_threshold
        
        # Failure tracking
        self.active_failures: Dict[str, FailureEvent] = {}
        self.failure_history: List[FailureEvent] = []
        
        # Health monitoring
        self.health_metrics: Dict[str, HealthMetrics] = {}
        self.metric_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # Detection state
        self.last_job_check: datetime = datetime.now()
        self.last_node_check: datetime = datetime.now()
        self.last_performance_check: datetime = datetime.now()
        
        # Thresholds and configuration
        self.check_intervals = {
            "jobs": timedelta(minutes=5),
            "nodes": timedelta(minutes=2),
            "performance": timedelta(minutes=10)
        }
        
        # Custom detection rules
        self.custom_detectors: List[Callable] = []
        
        logger.info("FailureDetector initialized")
    
    def detect_failures(self, jobs: List[BaseJob], nodes: List[BaseNode]) -> List[Dict[str, Any]]:
        """
        Detect failures in jobs and nodes.
        
        Args:
            jobs: Jobs to check for failures
            nodes: Nodes to check for failures
            
        Returns:
            List of detected failures
        """
        detected_failures = []
        current_time = datetime.now()
        
        # Check jobs for failures
        if current_time - self.last_job_check >= self.check_intervals["jobs"]:
            job_failures = self._detect_job_failures(jobs, current_time)
            detected_failures.extend(job_failures)
            self.last_job_check = current_time
        
        # Check nodes for failures
        if current_time - self.last_node_check >= self.check_intervals["nodes"]:
            node_failures = self._detect_node_failures(nodes, current_time)
            detected_failures.extend(node_failures)
            self.last_node_check = current_time
        
        # Check for performance degradation
        if current_time - self.last_performance_check >= self.check_intervals["performance"]:
            performance_failures = self._detect_performance_issues(jobs, nodes, current_time)
            detected_failures.extend(performance_failures)
            self.last_performance_check = current_time
        
        # Run custom detectors
        for detector in self.custom_detectors:
            try:
                custom_failures = detector(jobs, nodes, current_time)
                if custom_failures:
                    detected_failures.extend(custom_failures)
            except Exception as e:
                logger.warning(f"Custom detector failed: {e}")
        
        # Update failure tracking
        for failure_dict in detected_failures:
            failure_event = self._dict_to_failure_event(failure_dict)
            if failure_event:
                self._register_failure(failure_event)
        
        return detected_failures
    
    def initiate_recovery(self, failure: Dict[str, Any]) -> Result[None]:
        """
        Initiate recovery for a detected failure.
        
        Args:
            failure: Failure details
            
        Returns:
            Result indicating recovery status
        """
        failure_id = failure.get("id", "unknown")
        failure_type = failure.get("type", "unknown")
        
        if failure_id in self.active_failures:
            failure_event = self.active_failures[failure_id]
            
            # Mark failure as being recovered
            failure_event.context["recovery_initiated"] = datetime.now().isoformat()
            failure_event.context["recovery_status"] = "in_progress"
            
            logger.info(f"Initiated recovery for failure {failure_id} of type {failure_type}")
            return Result.ok(None)
        else:
            return Result.err(f"Failure {failure_id} not found in active failures", ErrorCode.NOT_FOUND)
    
    def can_recover(self, failure: Dict[str, Any]) -> bool:
        """
        Determine if a failure is recoverable.
        
        Args:
            failure: Failure details
            
        Returns:
            True if recovery is possible
        """
        failure_type = FailureType(failure.get("type", "unknown"))
        severity = FailureSeverity(failure.get("severity", "medium"))
        
        # Define recoverability rules
        recoverable_types = {
            FailureType.JOB_TIMEOUT: True,
            FailureType.JOB_CRASH: True,
            FailureType.NODE_OFFLINE: False,  # Needs manual intervention
            FailureType.NODE_UNRESPONSIVE: True,
            FailureType.RESOURCE_EXHAUSTION: True,
            FailureType.NETWORK_PARTITION: False,  # Infrastructure issue
            FailureType.DEPENDENCY_FAILURE: True,
            FailureType.PERFORMANCE_DEGRADATION: True,
            FailureType.CASCADING_FAILURE: False  # Too complex for automatic recovery
        }
        
        # Critical failures generally need manual intervention
        if severity == FailureSeverity.CRITICAL:
            return False
        
        return recoverable_types.get(failure_type, True)
    
    def get_recovery_strategy(self, failure: Dict[str, Any]) -> str:
        """
        Determine the best recovery strategy for a failure.
        
        Args:
            failure: Failure details
            
        Returns:
            Name of recovery strategy to use
        """
        failure_type = FailureType(failure.get("type", "unknown"))
        severity = FailureSeverity(failure.get("severity", "medium"))
        
        # Map failure types to recovery strategies
        strategy_map = {
            FailureType.JOB_TIMEOUT: "restart_job",
            FailureType.JOB_CRASH: "restart_job_with_retry",
            FailureType.NODE_OFFLINE: "migrate_jobs",
            FailureType.NODE_UNRESPONSIVE: "restart_node",
            FailureType.RESOURCE_EXHAUSTION: "scale_resources",
            FailureType.NETWORK_PARTITION: "wait_and_retry",
            FailureType.DEPENDENCY_FAILURE: "bypass_dependency",
            FailureType.PERFORMANCE_DEGRADATION: "optimize_allocation",
            FailureType.CASCADING_FAILURE: "emergency_shutdown"
        }
        
        base_strategy = strategy_map.get(failure_type, "manual_intervention")
        
        # Modify strategy based on severity
        if severity == FailureSeverity.CRITICAL:
            if "restart" in base_strategy:
                return "emergency_restart"
            elif "migrate" in base_strategy:
                return "emergency_migration"
        
        return base_strategy
    
    def update_health_metrics(self, entity_id: str, entity_type: str, 
                            metrics: Dict[str, float]):
        """
        Update health metrics for an entity.
        
        Args:
            entity_id: ID of the entity
            entity_type: Type of entity ("job", "node", etc.)
            metrics: Health metrics to update
        """
        if entity_id not in self.health_metrics:
            self.health_metrics[entity_id] = HealthMetrics(
                entity_id=entity_id,
                entity_type=entity_type
            )
        
        health_metric = self.health_metrics[entity_id]
        
        for metric_name, value in metrics.items():
            old_value = health_metric.get_metric(metric_name)
            health_metric.set_metric(metric_name, value)
            
            # Store metric history
            history_key = f"{entity_id}:{metric_name}"
            if history_key not in self.metric_history:
                self.metric_history[history_key] = []
            
            self.metric_history[history_key].append((datetime.now(), value))
            
            # Limit history size
            if len(self.metric_history[history_key]) > 1000:
                self.metric_history[history_key] = self.metric_history[history_key][-1000:]
    
    def add_custom_detector(self, detector_func: Callable):
        """
        Add a custom failure detector function.
        
        Args:
            detector_func: Function that takes (jobs, nodes, current_time) and returns list of failure dicts
        """
        self.custom_detectors.append(detector_func)
        logger.info("Added custom failure detector")
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get statistics about detected failures."""
        stats = {
            "active_failures": len(self.active_failures),
            "total_failures": len(self.failure_history) + len(self.active_failures),
            "failures_by_type": {},
            "failures_by_severity": {},
            "average_resolution_time": 0,
            "entities_monitored": len(self.health_metrics)
        }
        
        # Count failures by type and severity
        all_failures = list(self.active_failures.values()) + self.failure_history
        
        for failure in all_failures:
            failure_type = failure.failure_type.value
            severity = failure.severity.value
            
            stats["failures_by_type"][failure_type] = stats["failures_by_type"].get(failure_type, 0) + 1
            stats["failures_by_severity"][severity] = stats["failures_by_severity"].get(severity, 0) + 1
        
        # Calculate average resolution time for historical failures
        resolved_failures = [f for f in self.failure_history if "resolution_time" in f.context]
        if resolved_failures:
            resolution_times = []
            for failure in resolved_failures:
                resolution_time = datetime.fromisoformat(failure.context["resolution_time"])
                resolution_duration = (resolution_time - failure.detection_time).total_seconds()
                resolution_times.append(resolution_duration)
            
            stats["average_resolution_time"] = statistics.mean(resolution_times)
        
        return stats
    
    def get_entity_health(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get health information for a specific entity."""
        if entity_id not in self.health_metrics:
            return None
        
        health_metric = self.health_metrics[entity_id]
        
        health_info = {
            "entity_id": entity_id,
            "entity_type": health_metric.entity_type,
            "last_updated": health_metric.last_updated.isoformat(),
            "current_metrics": health_metric.metrics.copy(),
            "health_score": self._calculate_health_score(health_metric),
            "active_failures": [f.failure_id for f in self.active_failures.values() 
                              if f.affected_entity_id == entity_id]
        }
        
        return health_info
    
    def _detect_job_failures(self, jobs: List[BaseJob], current_time: datetime) -> List[Dict[str, Any]]:
        """Detect job-specific failures."""
        failures = []
        
        for job in jobs:
            # Check for job timeouts
            if job.status == JobStatus.RUNNING and job.start_time:
                runtime = current_time - job.start_time
                expected_duration = job.estimated_duration
                
                # Job timeout detection
                if runtime > expected_duration * 2:  # 2x expected duration
                    failures.append({
                        "id": f"job_timeout_{job.id}",
                        "type": FailureType.JOB_TIMEOUT.value,
                        "severity": FailureSeverity.MEDIUM.value,
                        "entity_id": job.id,
                        "entity_type": "job",
                        "description": f"Job {job.id} has exceeded expected duration",
                        "context": {
                            "runtime_seconds": runtime.total_seconds(),
                            "expected_seconds": expected_duration.total_seconds(),
                            "timeout_ratio": runtime / expected_duration
                        }
                    })
                
                # Long-running job warning
                elif runtime > self.job_timeout_threshold:
                    failures.append({
                        "id": f"job_long_running_{job.id}",
                        "type": FailureType.PERFORMANCE_DEGRADATION.value,
                        "severity": FailureSeverity.LOW.value,
                        "entity_id": job.id,
                        "entity_type": "job",
                        "description": f"Job {job.id} has been running for a long time",
                        "context": {
                            "runtime_seconds": runtime.total_seconds(),
                            "threshold_seconds": self.job_timeout_threshold.total_seconds()
                        }
                    })
            
            # Check for failed jobs
            if job.status == JobStatus.FAILED:
                failures.append({
                    "id": f"job_failed_{job.id}",
                    "type": FailureType.JOB_CRASH.value,
                    "severity": FailureSeverity.HIGH.value,
                    "entity_id": job.id,
                    "entity_type": "job",
                    "description": f"Job {job.id} has failed",
                    "context": {
                        "error_message": job.error_message or "Unknown error",
                        "retry_count": job.retry_count,
                        "max_retries": job.max_retries
                    }
                })
        
        return failures
    
    def _detect_node_failures(self, nodes: List[BaseNode], current_time: datetime) -> List[Dict[str, Any]]:
        """Detect node-specific failures."""
        failures = []
        
        for node in nodes:
            # Check for offline nodes
            if node.status == NodeStatus.OFFLINE:
                failures.append({
                    "id": f"node_offline_{node.id}",
                    "type": FailureType.NODE_OFFLINE.value,
                    "severity": FailureSeverity.HIGH.value,
                    "entity_id": node.id,
                    "entity_type": "node",
                    "description": f"Node {node.id} is offline",
                    "context": {
                        "assigned_jobs": len(node.assigned_jobs),
                        "reliability_score": node.reliability_score
                    }
                })
            
            # Check for unresponsive nodes (based on heartbeat)
            if node.last_heartbeat:
                time_since_heartbeat = current_time - node.last_heartbeat
                if time_since_heartbeat > self.node_heartbeat_timeout:
                    severity = FailureSeverity.HIGH if time_since_heartbeat > self.node_heartbeat_timeout * 2 else FailureSeverity.MEDIUM
                    
                    failures.append({
                        "id": f"node_unresponsive_{node.id}",
                        "type": FailureType.NODE_UNRESPONSIVE.value,
                        "severity": severity.value,
                        "entity_id": node.id,
                        "entity_type": "node",
                        "description": f"Node {node.id} has not sent heartbeat recently",
                        "context": {
                            "last_heartbeat": node.last_heartbeat.isoformat(),
                            "time_since_heartbeat_seconds": time_since_heartbeat.total_seconds(),
                            "threshold_seconds": self.node_heartbeat_timeout.total_seconds()
                        }
                    })
            
            # Check for resource exhaustion
            available_resources = node.get_available_resources()
            for resource_type, available in available_resources.items():
                if resource_type.value == "cpu":
                    total = node.capabilities.cpu_cores
                elif resource_type.value == "memory":
                    total = node.capabilities.memory_gb
                else:
                    continue
                
                if total > 0:
                    utilization = (total - available) / total
                    if utilization > self.resource_exhaustion_threshold:
                        failures.append({
                            "id": f"resource_exhaustion_{node.id}_{resource_type.value}",
                            "type": FailureType.RESOURCE_EXHAUSTION.value,
                            "severity": FailureSeverity.MEDIUM.value,
                            "entity_id": node.id,
                            "entity_type": "node",
                            "description": f"Node {node.id} has high {resource_type.value} utilization",
                            "context": {
                                "resource_type": resource_type.value,
                                "utilization": utilization,
                                "threshold": self.resource_exhaustion_threshold,
                                "total_capacity": total,
                                "available": available
                            }
                        })
        
        return failures
    
    def _detect_performance_issues(self, jobs: List[BaseJob], nodes: List[BaseNode], current_time: datetime) -> List[Dict[str, Any]]:
        """Detect system-wide performance issues."""
        failures = []
        
        # Check for overall system performance degradation
        running_jobs = [j for j in jobs if j.status == JobStatus.RUNNING]
        
        if running_jobs:
            # Calculate average job performance
            slow_jobs = 0
            for job in running_jobs:
                if job.start_time:
                    runtime = current_time - job.start_time
                    expected_duration = job.estimated_duration
                    
                    if runtime > expected_duration * 1.5:  # 1.5x slower than expected
                        slow_jobs += 1
            
            if slow_jobs / len(running_jobs) > self.performance_degradation_threshold:
                failures.append({
                    "id": f"system_performance_degradation_{current_time.isoformat()}",
                    "type": FailureType.PERFORMANCE_DEGRADATION.value,
                    "severity": FailureSeverity.MEDIUM.value,
                    "entity_id": "system",
                    "entity_type": "system",
                    "description": f"System performance has degraded - {slow_jobs}/{len(running_jobs)} jobs running slowly",
                    "context": {
                        "slow_job_ratio": slow_jobs / len(running_jobs),
                        "threshold": self.performance_degradation_threshold,
                        "total_running_jobs": len(running_jobs),
                        "slow_jobs": slow_jobs
                    }
                })
        
        # Check for cascading failures
        recent_failures = [f for f in self.active_failures.values() 
                          if (current_time - f.detection_time) < timedelta(minutes=30)]
        
        if len(recent_failures) > 5:  # More than 5 failures in 30 minutes
            failures.append({
                "id": f"cascading_failure_{current_time.isoformat()}",
                "type": FailureType.CASCADING_FAILURE.value,
                "severity": FailureSeverity.CRITICAL.value,
                "entity_id": "system",
                "entity_type": "system",
                "description": f"Potential cascading failure detected - {len(recent_failures)} recent failures",
                "context": {
                    "recent_failure_count": len(recent_failures),
                    "time_window_minutes": 30,
                    "related_failures": [f.failure_id for f in recent_failures]
                }
            })
        
        return failures
    
    def _dict_to_failure_event(self, failure_dict: Dict[str, Any]) -> Optional[FailureEvent]:
        """Convert failure dictionary to FailureEvent object."""
        try:
            return FailureEvent(
                failure_id=failure_dict["id"],
                failure_type=FailureType(failure_dict["type"]),
                severity=FailureSeverity(failure_dict["severity"]),
                affected_entity_id=failure_dict["entity_id"],
                entity_type=failure_dict["entity_type"],
                description=failure_dict.get("description", ""),
                context=failure_dict.get("context", {})
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Failed to convert failure dict to FailureEvent: {e}")
            return None
    
    def _register_failure(self, failure_event: FailureEvent):
        """Register a new failure event."""
        # Check if this failure is already active
        if failure_event.failure_id in self.active_failures:
            # Update existing failure
            existing = self.active_failures[failure_event.failure_id]
            existing.context.update(failure_event.context)
            existing.description = failure_event.description
        else:
            # Add new failure
            self.active_failures[failure_event.failure_id] = failure_event
            logger.warning(f"Detected failure: {failure_event.failure_type.value} "
                         f"affecting {failure_event.entity_type} {failure_event.affected_entity_id}")
    
    def _calculate_health_score(self, health_metric: HealthMetrics) -> float:
        """Calculate overall health score for an entity."""
        if not health_metric.metrics:
            return 0.5  # Neutral score if no metrics
        
        # This is a simplified health score calculation
        # In practice, this would be more sophisticated based on metric types
        
        scores = []
        for metric_name, value in health_metric.metrics.items():
            if "utilization" in metric_name.lower():
                # For utilization metrics, lower is better (up to a point)
                if value < 0.7:
                    scores.append(1.0)
                elif value < 0.9:
                    scores.append(0.7)
                else:
                    scores.append(0.3)
            elif "error" in metric_name.lower():
                # For error metrics, lower is better
                scores.append(max(0.0, 1.0 - value))
            elif "response_time" in metric_name.lower():
                # For response time, lower is better
                # Assume good response time is < 1.0 seconds
                scores.append(max(0.0, 1.0 - (value / 5.0)))
            else:
                # Default: assume higher values are better
                scores.append(min(1.0, value))
        
        return statistics.mean(scores) if scores else 0.5