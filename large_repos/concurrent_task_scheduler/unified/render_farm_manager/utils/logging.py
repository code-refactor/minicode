"""Logging and monitoring utilities for the Render Farm Manager."""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Import common monitoring interfaces
from common.core.interfaces import MonitoringInterface
from render_farm_manager.core.interfaces import AuditInterface
from render_farm_manager.core.models import AuditLogEntry


class AuditLogger(AuditInterface, MonitoringInterface):
    """Implementation of the audit logger for tracking render farm activity."""
    
    def __init__(self):
        """Initialize the audit logger."""
        self.logs: List[AuditLogEntry] = []
        self.logger = logging.getLogger("render_farm.audit")
        
    def log_event(self, event_type: str, description: str, **details) -> AuditLogEntry:
        """
        Log an event in the audit trail.
        
        Args:
            event_type: Type of event
            description: Human-readable description of the event
            **details: Additional details about the event
            
        Returns:
            The created audit log entry
        """
        # Get the log level from details, defaulting to INFO
        log_level = details.get("log_level", "info")
        
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            event_type=event_type,
            description=description,
            details=details,
            job_id=details.get("job_id"),
            node_id=details.get("node_id"),
            client_id=details.get("client_id"),
        )
        
        self.logs.append(entry)
        
        # Log at the appropriate level
        if log_level == "error":
            self.logger.error(
                f"{entry.timestamp} - {event_type}: {description} "
                f"(job_id={entry.job_id}, node_id={entry.node_id}, client_id={entry.client_id})"
            )
        elif log_level == "warning":
            self.logger.warning(
                f"{entry.timestamp} - {event_type}: {description} "
                f"(job_id={entry.job_id}, node_id={entry.node_id}, client_id={entry.client_id})"
            )
        else:  # default to info
            self.logger.info(
                f"{entry.timestamp} - {event_type}: {description} "
                f"(job_id={entry.job_id}, node_id={entry.node_id}, client_id={entry.client_id})"
            )
        
        return entry
        
    def log_error(self, message: str, source: str, severity: str) -> AuditLogEntry:
        """
        Log an error event.
        
        Args:
            message: Error message
            source: Source of the error
            severity: Severity level
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "error",
            message,
            source=source,
            log_level="error",
            severity=severity
        )
        
    def log_client_added(self, client_id: str, name: str, service_tier: str) -> AuditLogEntry:
        """
        Log a client added event.
        
        Args:
            client_id: ID of the client
            name: Name of the client
            service_tier: Service tier of the client
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "client_added",
            f"Client {client_id} ({name}) added to the render farm",
            client_id=client_id,
            client_name=name,
            service_tier=service_tier
        )
    
    def log_client_updated(self, client_id: str, name: str, old_tier: str, new_tier: str) -> AuditLogEntry:
        """
        Log a client updated event.
        
        Args:
            client_id: ID of the client
            name: Name of the client
            old_tier: Previous service tier
            new_tier: New service tier
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "client_updated",
            f"Client {client_id} ({name}) service tier updated from {old_tier} to {new_tier}",
            client_id=client_id,
            client_name=name,
            old_tier=old_tier,
            new_tier=new_tier
        )
    
    def log_node_added(self, node_id: str, name: str, status: str, capabilities: dict) -> AuditLogEntry:
        """
        Log a node added event.
        
        Args:
            node_id: ID of the node
            name: Name of the node
            status: Status of the node
            capabilities: Capabilities of the node
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "node_added",
            f"Node {node_id} ({name}) added to the render farm",
            node_id=node_id,
            node_name=name,
            node_status=status,
            node_capabilities=capabilities
        )
    
    def log_node_updated(self, node_id: str, name: str, old_status: str, new_status: str) -> AuditLogEntry:
        """
        Log a node updated event.
        
        Args:
            node_id: ID of the node
            name: Name of the node
            old_status: Previous status
            new_status: New status
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "node_updated",
            f"Node {node_id} ({name}) status updated from {old_status} to {new_status}",
            node_id=node_id,
            node_name=name,
            old_status=old_status,
            new_status=new_status
        )
        
    def log_node_failure(self, node_id: str) -> AuditLogEntry:
        """
        Log a node failure event.
        
        Args:
            node_id: ID of the failed node
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "node_failure",
            f"Node {node_id} has failed",
            node_id=node_id,
            log_level="warning"
        )
    
    def log_job_submitted(self, job_id: str, client_id: str, name: str, priority: str) -> AuditLogEntry:
        """
        Log a job submitted event.
        
        Args:
            job_id: ID of the job
            client_id: ID of the client
            name: Name of the job
            priority: Priority of the job
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "job_submitted",
            f"Job {job_id} ({name}) submitted by client {client_id}",
            job_id=job_id,
            job_name=name,
            client_id=client_id,
            priority=priority
        )
    
    def log_job_scheduled(self, job_id: str, node_id: str, client_id: str, priority: str) -> AuditLogEntry:
        """
        Log a job scheduled event.
        
        Args:
            job_id: ID of the job
            node_id: ID of the node
            client_id: ID of the client
            priority: Priority of the job
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "job_scheduled",
            f"Job {job_id} scheduled on node {node_id}",
            job_id=job_id,
            node_id=node_id,
            client_id=client_id,
            priority=priority
        )
    
    def log_job_updated(self, job_id: str, client_id: str, name: str, old_priority: str, new_priority: str) -> AuditLogEntry:
        """
        Log a job updated event.
        
        Args:
            job_id: ID of the job
            client_id: ID of the client
            name: Name of the job
            old_priority: Previous priority
            new_priority: New priority
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "job_updated",
            f"Job {job_id} ({name}) priority updated from {old_priority} to {new_priority}",
            job_id=job_id,
            job_name=name,
            client_id=client_id,
            old_priority=old_priority,
            new_priority=new_priority
        )
    
    def log_job_completed(self, job_id: str, client_id: str, name: str, completion_time: str) -> AuditLogEntry:
        """
        Log a job completed event.
        
        Args:
            job_id: ID of the job
            client_id: ID of the client
            name: Name of the job
            completion_time: Time of completion
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "job_completed",
            f"Job {job_id} ({name}) completed",
            job_id=job_id,
            job_name=name,
            client_id=client_id,
            completion_time=completion_time
        )
    
    def log_energy_mode_changed(self, old_mode: str, new_mode: str) -> AuditLogEntry:
        """
        Log an energy mode changed event.
        
        Args:
            old_mode: Previous energy mode
            new_mode: New energy mode
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "energy_mode_changed",
            f"Energy mode changed from {old_mode} to {new_mode}",
            old_mode=old_mode,
            new_mode=new_mode
        )
    
    def log_scheduling_cycle(self, jobs_scheduled: int, utilization_percentage: float, energy_optimized_jobs: int, progressive_outputs: int) -> AuditLogEntry:
        """
        Log a scheduling cycle event.
        
        Args:
            jobs_scheduled: Number of jobs scheduled in this cycle
            utilization_percentage: Percentage of cluster utilization
            energy_optimized_jobs: Number of jobs optimized for energy usage
            progressive_outputs: Number of progressive outputs generated
            
        Returns:
            The created audit log entry
        """
        return self.log_event(
            "scheduling_cycle_completed",
            f"Scheduling cycle completed: {jobs_scheduled} jobs scheduled, {utilization_percentage:.1f}% utilization",
            jobs_scheduled=jobs_scheduled,
            utilization_percentage=utilization_percentage,
            energy_optimized_jobs=energy_optimized_jobs,
            progressive_outputs=progressive_outputs
        )
    
    def get_job_history(self, job_id: str) -> List[AuditLogEntry]:
        """
        Get the audit history for a specific job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            List of audit log entries related to the job
        """
        return [entry for entry in self.logs if entry.job_id == job_id]
    
    def get_node_history(self, node_id: str) -> List[AuditLogEntry]:
        """
        Get the audit history for a specific node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            List of audit log entries related to the node
        """
        return [entry for entry in self.logs if entry.node_id == node_id]
    
    def get_client_history(self, client_id: str) -> List[AuditLogEntry]:
        """
        Get the audit history for a specific client.
        
        Args:
            client_id: ID of the client
            
        Returns:
            List of audit log entries related to the client
        """
        return [entry for entry in self.logs if entry.client_id == client_id]
    
    def get_logs_by_time_range(self, start_time: datetime, end_time: datetime) -> List[AuditLogEntry]:
        """
        Get logs within a specific time range.
        
        Args:
            start_time: Start of the time range
            end_time: End of the time range
            
        Returns:
            List of audit log entries within the time range
        """
        return [
            entry for entry in self.logs 
            if start_time <= entry.timestamp <= end_time
        ]
    
    def get_logs_by_event_type(self, event_type: str) -> List[AuditLogEntry]:
        """
        Get logs of a specific event type.
        
        Args:
            event_type: The event type to filter by
            
        Returns:
            List of audit log entries with the specified event type
        """
        return [entry for entry in self.logs if entry.event_type == event_type]
    
    # MonitoringInterface methods
    def record_metric(self, metric_name: str, value: float, **tags) -> None:
        """
        Record a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            **tags: Additional tags/labels
        """
        # Log as an event for now - in a real system this would go to a metrics store
        self.log_event(
            "metric_recorded",
            f"{metric_name}: {value}",
            metric_name=metric_name,
            metric_value=value,
            **tags
        )
    
    def get_job_history(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get audit history for a job.
        
        Args:
            job_id: Job to get history for
            
        Returns:
            List of historical events
        """
        return [{
            "timestamp": entry.timestamp,
            "event_type": entry.event_type,
            "description": entry.description,
            "details": entry.details
        } for entry in self.logs if entry.job_id == job_id]
    
    def get_node_metrics(self, node_id: str, start_time: datetime, end_time: datetime) -> Dict[str, List[Tuple[datetime, float]]]:
        """
        Get performance metrics for a node.
        
        Args:
            node_id: Node to get metrics for
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Mapping of metric names to time series data
        """
        metrics = {}
        
        for entry in self.logs:
            if (entry.node_id == node_id and 
                start_time <= entry.timestamp <= end_time and
                entry.event_type == "metric_recorded"):
                
                metric_name = entry.details.get("metric_name")
                metric_value = entry.details.get("metric_value")
                
                if metric_name and metric_value is not None:
                    if metric_name not in metrics:
                        metrics[metric_name] = []
                    metrics[metric_name].append((entry.timestamp, metric_value))
        
        return metrics


class PerformanceMonitor:
    """Monitor and track performance metrics for the render farm."""
    
    def __init__(self, audit_logger: AuditLogger):
        """
        Initialize the performance monitor.
        
        Args:
            audit_logger: The audit logger to record performance events
        """
        self.audit_logger = audit_logger
        self.operation_times: Dict[str, List[float]] = {}
        self.client_metrics: Dict[str, Dict[str, float]] = {}
        self.node_metrics: Dict[str, Dict[str, float]] = {}
        self.job_metrics: Dict[str, Dict[str, float]] = {}
        self.failure_count: int = 0
        
    def time_operation(self, operation_name: str) -> 'TimedOperation':
        """
        Create a context manager to time an operation.
        
        Args:
            operation_name: Name of the operation to time
            
        Returns:
            A context manager for timing the operation
        """
        return TimedOperation(self, operation_name)
    
    def record_operation_time(self, operation_name: str, duration_ms: float) -> None:
        """
        Record the time taken for an operation.
        
        Args:
            operation_name: Name of the operation
            duration_ms: Duration of the operation in milliseconds
        """
        if operation_name not in self.operation_times:
            self.operation_times[operation_name] = []
        
        self.operation_times[operation_name].append(duration_ms)
        
        self.audit_logger.log_event(
            "performance_metric",
            f"Operation '{operation_name}' completed in {duration_ms:.2f}ms",
            operation_name=operation_name,
            duration_ms=duration_ms,
        )
    
    def update_client_resource_metrics(self, client_id: str, allocated_percentage: float, 
                                      borrowed_percentage: float = 0.0, lent_percentage: float = 0.0) -> None:
        """
        Update resource metrics for a client.
        
        Args:
            client_id: ID of the client
            allocated_percentage: Percentage of resources allocated to the client
            borrowed_percentage: Percentage of resources borrowed from other clients
            lent_percentage: Percentage of resources lent to other clients
        """
        if client_id not in self.client_metrics:
            self.client_metrics[client_id] = {}
            
        self.client_metrics[client_id].update({
            "allocated_percentage": allocated_percentage,
            "borrowed_percentage": borrowed_percentage,
            "lent_percentage": lent_percentage,
        })
        
        self.audit_logger.log_event(
            "client_resource_metrics_updated",
            f"Client {client_id} resource metrics updated: allocated={allocated_percentage:.2f}%, "
            f"borrowed={borrowed_percentage:.2f}%, lent={lent_percentage:.2f}%",
            client_id=client_id,
            allocated_percentage=allocated_percentage,
            borrowed_percentage=borrowed_percentage,
            lent_percentage=lent_percentage,
        )
    
    def update_energy_cost_saved(self, amount: float, mode: str) -> None:
        """
        Update the amount of energy cost saved.
        
        Args:
            amount: Amount of cost saved
            mode: Energy mode that enabled the savings
        """
        self.audit_logger.log_event(
            "energy_cost_savings",
            f"Energy cost savings recorded: {amount:.2f} in {mode} mode",
            amount=amount,
            mode=mode,
        )
    
    def update_scheduling_cycle_time(self, duration_ms: float, jobs_scheduled: int) -> None:
        """
        Update the time taken for a scheduling cycle.
        
        Args:
            duration_ms: Duration of the scheduling cycle in milliseconds
            jobs_scheduled: Number of jobs scheduled in this cycle
        """
        self.record_operation_time("scheduling_cycle", duration_ms)
        
        self.audit_logger.log_event(
            "scheduling_cycle_metrics",
            f"Scheduling cycle completed in {duration_ms:.2f}ms with {jobs_scheduled} jobs scheduled",
            duration_ms=duration_ms,
            jobs_scheduled=jobs_scheduled,
        )
    
    def update_job_turnaround_time(self, job_id: str, turnaround_hours: float, client_id: str) -> None:
        """
        Update the turnaround time for a completed job.
        
        Args:
            job_id: ID of the job
            turnaround_hours: Time from submission to completion in hours
            client_id: ID of the client that submitted the job
        """
        if job_id not in self.job_metrics:
            self.job_metrics[job_id] = {}
            
        self.job_metrics[job_id]["turnaround_hours"] = turnaround_hours
        
        self.audit_logger.log_event(
            "job_turnaround_time",
            f"Job {job_id} completed with turnaround time of {turnaround_hours:.2f} hours",
            job_id=job_id,
            turnaround_hours=turnaround_hours,
            client_id=client_id,
        )
    
    def update_node_utilization(self, node_id: str, utilization_percentage: float) -> None:
        """
        Update the utilization percentage for a node.
        
        Args:
            node_id: ID of the node
            utilization_percentage: Percentage of time the node is utilized
        """
        if node_id not in self.node_metrics:
            self.node_metrics[node_id] = {}
            
        self.node_metrics[node_id]["utilization_percentage"] = utilization_percentage
        
        self.audit_logger.log_event(
            "node_utilization",
            f"Node {node_id} utilization updated to {utilization_percentage:.2f}%",
            node_id=node_id,
            utilization_percentage=utilization_percentage,
        )
    
    def update_client_job_count(self, client_id: str, job_count: int) -> None:
        """
        Update the number of jobs for a client.
        
        Args:
            client_id: ID of the client
            job_count: Current number of jobs for the client
        """
        if client_id not in self.client_metrics:
            self.client_metrics[client_id] = {}
            
        self.client_metrics[client_id]["job_count"] = job_count
        
        self.audit_logger.log_event(
            "client_job_count",
            f"Client {client_id} job count updated to {job_count}",
            client_id=client_id,
            job_count=job_count,
        )
    
    def update_node_failure_count(self, node_id: str = None) -> None:
        """
        Increment the node failure count.
        
        Args:
            node_id: Optional ID of the node that failed
        """
        self.failure_count += 1
        
        log_details = {"failure_count": self.failure_count}
        if node_id:
            log_details["node_id"] = node_id
            
        self.audit_logger.log_event(
            "node_failure_count",
            f"Node failure count incremented to {self.failure_count}" + 
            (f" (node: {node_id})" if node_id else ""),
            **log_details,
            log_level="warning",
        )
    
    def get_average_operation_time(self, operation_name: str) -> Optional[float]:
        """
        Get the average time for an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Average time in milliseconds, or None if no data is available
        """
        if operation_name not in self.operation_times or not self.operation_times[operation_name]:
            return None
        
        return sum(self.operation_times[operation_name]) / len(self.operation_times[operation_name])
    
    def get_max_operation_time(self, operation_name: str) -> Optional[float]:
        """
        Get the maximum time for an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Maximum time in milliseconds, or None if no data is available
        """
        if operation_name not in self.operation_times or not self.operation_times[operation_name]:
            return None
        
        return max(self.operation_times[operation_name])
    
    def get_min_operation_time(self, operation_name: str) -> Optional[float]:
        """
        Get the minimum time for an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Minimum time in milliseconds, or None if no data is available
        """
        if operation_name not in self.operation_times or not self.operation_times[operation_name]:
            return None
        
        return min(self.operation_times[operation_name])
    
    def get_client_metrics(self, client_id: str) -> Dict[str, float]:
        """
        Get resource metrics for a client.
        
        Args:
            client_id: ID of the client
            
        Returns:
            Dictionary of resource metrics for the client
        """
        return self.client_metrics.get(client_id, {})
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self.operation_times = {}
        self.client_metrics = {}


class TimedOperation:
    """Context manager for timing operations."""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str):
        """
        Initialize the timed operation.
        
        Args:
            monitor: The performance monitor
            operation_name: Name of the operation to time
        """
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = 0.0
        
    def __enter__(self) -> 'TimedOperation':
        """Start timing the operation."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Stop timing the operation and record the duration.
        
        Args:
            exc_type: Exception type, if an exception was raised
            exc_val: Exception value, if an exception was raised
            exc_tb: Exception traceback, if an exception was raised
        """
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        self.monitor.record_operation_time(self.operation_name, duration_ms)