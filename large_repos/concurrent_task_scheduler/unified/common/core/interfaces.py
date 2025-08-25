"""Core interfaces for the unified task scheduling library."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .models import BaseJob, BaseNode, JobDependency, Priority
from .result import Result


class SchedulerInterface(ABC):
    """Interface for job scheduling implementations."""
    
    @abstractmethod
    def schedule_jobs(self, jobs: List[BaseJob], nodes: List[BaseNode]) -> Dict[str, str]:
        """
        Schedule jobs to nodes.
        
        Args:
            jobs: List of jobs to schedule
            nodes: List of available nodes
            
        Returns:
            Mapping of job IDs to node IDs
        """
        pass
    
    @abstractmethod
    def update_priorities(self, jobs: List[BaseJob], current_time: datetime) -> List[BaseJob]:
        """
        Update job priorities based on current conditions.
        
        Args:
            jobs: Jobs to update priorities for
            current_time: Current timestamp for calculations
            
        Returns:
            Jobs with updated priorities
        """
        pass
    
    @abstractmethod
    def can_preempt(self, running_job: BaseJob, pending_job: BaseJob) -> bool:
        """
        Determine if a running job can be preempted for a pending job.
        
        Args:
            running_job: Currently running job
            pending_job: Job waiting to run
            
        Returns:
            True if preemption should occur
        """
        pass
    
    @abstractmethod
    def get_next_job(self, available_jobs: List[BaseJob], node: BaseNode) -> Optional[BaseJob]:
        """
        Get the next job to run on a specific node.
        
        Args:
            available_jobs: Jobs ready to run
            node: Node to assign job to
            
        Returns:
            Next job to run, or None if no suitable job
        """
        pass


class ResourceManagerInterface(ABC):
    """Interface for resource management implementations."""
    
    @abstractmethod
    def allocate_resources(self, job: BaseJob, nodes: List[BaseNode]) -> Result[str]:
        """
        Allocate resources for a job.
        
        Args:
            job: Job requiring resources
            nodes: Available nodes
            
        Returns:
            Result containing assigned node ID or error
        """
        pass
    
    @abstractmethod
    def release_resources(self, job: BaseJob, node: BaseNode) -> Result[None]:
        """
        Release resources allocated to a job.
        
        Args:
            job: Job releasing resources
            node: Node to release from
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    def get_resource_availability(self, nodes: List[BaseNode]) -> Dict[str, Dict[str, float]]:
        """
        Get current resource availability across nodes.
        
        Args:
            nodes: Nodes to check
            
        Returns:
            Mapping of node IDs to available resources
        """
        pass
    
    @abstractmethod
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
        pass


class MonitoringInterface(ABC):
    """Interface for monitoring and observability implementations."""
    
    @abstractmethod
    def log_event(self, event_type: str, description: str, **details) -> None:
        """
        Log a system event.
        
        Args:
            event_type: Type of event
            description: Event description
            **details: Additional event details
        """
        pass
    
    @abstractmethod
    def record_metric(self, metric_name: str, value: float, **tags) -> None:
        """
        Record a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            **tags: Additional tags/labels
        """
        pass
    
    @abstractmethod
    def get_job_history(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get audit history for a job.
        
        Args:
            job_id: Job to get history for
            
        Returns:
            List of historical events
        """
        pass
    
    @abstractmethod
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
        pass


class FailureHandlerInterface(ABC):
    """Interface for failure detection and recovery implementations."""
    
    @abstractmethod
    def detect_failures(self, jobs: List[BaseJob], nodes: List[BaseNode]) -> List[Dict[str, Any]]:
        """
        Detect failures in jobs and nodes.
        
        Args:
            jobs: Jobs to check
            nodes: Nodes to check
            
        Returns:
            List of detected failures
        """
        pass
    
    @abstractmethod
    def initiate_recovery(self, failure: Dict[str, Any]) -> Result[None]:
        """
        Initiate recovery for a detected failure.
        
        Args:
            failure: Failure details
            
        Returns:
            Result indicating recovery status
        """
        pass
    
    @abstractmethod
    def can_recover(self, failure: Dict[str, Any]) -> bool:
        """
        Determine if a failure is recoverable.
        
        Args:
            failure: Failure details
            
        Returns:
            True if recovery is possible
        """
        pass
    
    @abstractmethod
    def get_recovery_strategy(self, failure: Dict[str, Any]) -> str:
        """
        Determine the best recovery strategy for a failure.
        
        Args:
            failure: Failure details
            
        Returns:
            Name of recovery strategy to use
        """
        pass


class DependencyManagerInterface(ABC):
    """Interface for dependency management implementations."""
    
    @abstractmethod
    def add_dependency(self, dependency: JobDependency) -> Result[None]:
        """
        Add a dependency between jobs.
        
        Args:
            dependency: Dependency to add
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    def remove_dependency(self, from_job: str, to_job: str) -> Result[None]:
        """
        Remove a dependency between jobs.
        
        Args:
            from_job: Source job ID
            to_job: Target job ID
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    def get_ready_jobs(self, jobs: List[BaseJob], completed_jobs: List[str]) -> List[BaseJob]:
        """
        Get jobs that are ready to run based on satisfied dependencies.
        
        Args:
            jobs: All jobs
            completed_jobs: IDs of completed jobs
            
        Returns:
            Jobs with all dependencies satisfied
        """
        pass
    
    @abstractmethod
    def detect_circular_dependencies(self, jobs: List[BaseJob]) -> List[List[str]]:
        """
        Detect circular dependencies in job graph.
        
        Args:
            jobs: Jobs to check
            
        Returns:
            List of circular dependency chains
        """
        pass
    
    @abstractmethod
    def get_dependency_graph(self, jobs: List[BaseJob]) -> Dict[str, List[str]]:
        """
        Get the dependency graph for jobs.
        
        Args:
            jobs: Jobs to analyze
            
        Returns:
            Adjacency list representation of dependency graph
        """
        pass


class QueueManagerInterface(ABC):
    """Interface for job queue management."""
    
    @abstractmethod
    def enqueue(self, job: BaseJob) -> Result[None]:
        """
        Add a job to the queue.
        
        Args:
            job: Job to enqueue
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    def dequeue(self) -> Optional[BaseJob]:
        """
        Remove and return the next job from the queue.
        
        Returns:
            Next job or None if queue is empty
        """
        pass
    
    @abstractmethod
    def peek(self) -> Optional[BaseJob]:
        """
        Get the next job without removing it.
        
        Returns:
            Next job or None if queue is empty
        """
        pass
    
    @abstractmethod
    def reorder(self, priority_function) -> None:
        """
        Reorder queue based on a priority function.
        
        Args:
            priority_function: Function to calculate job priority
        """
        pass
    
    @abstractmethod
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the queue.
        
        Returns:
            Queue statistics including size, priorities, etc.
        """
        pass