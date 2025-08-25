"""Core interfaces for the Render Farm Manager."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Union

from render_farm_manager.core.models import (
    AuditLogEntry,
    Client,
    JobPriority,
    PerformanceMetrics,
    ProgressiveOutputConfig,
    RenderJob,
    RenderJobStatus,
    RenderNode,
    ResourceAllocation,
)


class SchedulerInterface(ABC):
    """Interface for the job scheduling component."""
    
    @abstractmethod
    def schedule_jobs(self, jobs: List[RenderJob], nodes: List[RenderNode]) -> Dict[str, str]:
        """
        Schedule jobs to render nodes based on priority, deadlines, and resource requirements.
        
        Args:
            jobs: List of render jobs to schedule
            nodes: List of available render nodes
            
        Returns:
            Dictionary mapping job IDs to node IDs
        """
        pass
    
    @abstractmethod
    def update_priorities(self, jobs: List[RenderJob]) -> List[RenderJob]:
        """
        Update job priorities based on deadlines and completion status.
        
        Args:
            jobs: List of render jobs
            
        Returns:
            List of updated render jobs with adjusted priorities
        """
        pass
    
    @abstractmethod
    def can_meet_deadline(self, job: RenderJob, available_nodes: List[RenderNode]) -> bool:
        """
        Determine if a job's deadline can be met with available resources.
        
        Args:
            job: The render job to evaluate
            available_nodes: List of available render nodes
            
        Returns:
            True if the deadline can be met, False otherwise
        """
        pass
    
    @abstractmethod
    def should_preempt(self, running_job: RenderJob, pending_job: RenderJob) -> bool:
        """
        Determine if a running job should be preempted for a pending job.
        
        Args:
            running_job: The currently running job
            pending_job: The job that might preempt the running job
            
        Returns:
            True if the running job should be preempted, False otherwise
        """
        pass


class ResourceManagerInterface(ABC):
    """Interface for the resource management component."""
    
    @abstractmethod
    def allocate_resources(self, clients: List[Client], nodes: List[RenderNode]) -> Dict[str, ResourceAllocation]:
        """
        Allocate resources to clients based on SLAs and current demands.
        
        Args:
            clients: List of clients
            nodes: List of available render nodes
            
        Returns:
            Dictionary mapping client IDs to their resource allocations
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass


class NodeSpecializationInterface(ABC):
    """Interface for the node specialization component."""
    
    @abstractmethod
    def match_job_to_node(self, job: RenderJob, nodes: List[RenderNode]) -> Optional[str]:
        """
        Match a job to the most appropriate node based on job requirements and node capabilities.
        
        Args:
            job: The render job to match
            nodes: List of available render nodes
            
        Returns:
            ID of the matched node, or None if no suitable node is found
        """
        pass
    
    @abstractmethod
    def calculate_performance_score(self, job: RenderJob, node: RenderNode) -> float:
        """
        Calculate a performance score for a job on a specific node.
        
        Args:
            job: The render job to evaluate
            node: The render node to evaluate
            
        Returns:
            Performance score (higher is better)
        """
        pass
    
    @abstractmethod
    def update_performance_history(self, job: RenderJob, node: RenderNode, performance_metrics: Dict[str, float]) -> None:
        """
        Update performance history for a node based on completed job metrics.
        
        Args:
            job: The completed render job
            node: The render node that executed the job
            performance_metrics: Metrics about the job's performance
        """
        pass


class ProgressiveResultInterface(ABC):
    """Interface for the progressive result generation component."""
    
    @abstractmethod
    def schedule_progressive_output(
        self, job: RenderJob, config: ProgressiveOutputConfig
    ) -> List[datetime]:
        """
        Schedule progressive output generation for a job.
        
        Args:
            job: The render job
            config: Configuration for progressive output generation
            
        Returns:
            List of scheduled times for progressive output generation
        """
        pass
    
    @abstractmethod
    def generate_progressive_output(self, job: RenderJob, quality_level: int) -> str:
        """
        Generate a progressive output for a job at a specific quality level.
        
        Args:
            job: The render job
            quality_level: Quality level for the progressive output
            
        Returns:
            Path to the generated progressive output
        """
        pass
    
    @abstractmethod
    def estimate_overhead(self, job: RenderJob, config: ProgressiveOutputConfig) -> float:
        """
        Estimate the overhead of progressive output generation for a job.
        
        Args:
            job: The render job
            config: Configuration for progressive output generation
            
        Returns:
            Estimated overhead as a percentage of total rendering time
        """
        pass


class EnergyOptimizationInterface(ABC):
    """Interface for the energy optimization component."""
    
    @abstractmethod
    def optimize_energy_usage(self, jobs: List[RenderJob], nodes: List[RenderNode]) -> Dict[str, str]:
        """
        Optimize energy usage by scheduling jobs to energy-efficient nodes.
        
        Args:
            jobs: List of render jobs
            nodes: List of render nodes
            
        Returns:
            Dictionary mapping job IDs to node IDs based on energy optimization
        """
        pass
    
    @abstractmethod
    def calculate_energy_cost(self, job: RenderJob, node: RenderNode, start_time: datetime) -> float:
        """
        Calculate the energy cost for a job on a specific node.
        
        Args:
            job: The render job
            node: The render node
            start_time: The scheduled start time for the job
            
        Returns:
            Estimated energy cost in currency units
        """
        pass
    
    @abstractmethod
    def get_time_of_day_energy_price(self, time: datetime) -> float:
        """
        Get the energy price for a specific time of day.
        
        Args:
            time: The time to check
            
        Returns:
            Energy price in currency units per kWh
        """
        pass


class AuditInterface(ABC):
    """Interface for the audit trail component."""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_job_history(self, job_id: str) -> List[AuditLogEntry]:
        """
        Get the audit history for a specific job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            List of audit log entries related to the job
        """
        pass
    
    @abstractmethod
    def get_node_history(self, node_id: str) -> List[AuditLogEntry]:
        """
        Get the audit history for a specific node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            List of audit log entries related to the node
        """
        pass