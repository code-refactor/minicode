"""Base scheduler implementation for the unified task scheduling library."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import logging

from ..core.interfaces import SchedulerInterface
from ..core.models import BaseJob, BaseNode, JobStatus, Priority
from ..core.result import Result, ErrorCode


class BaseScheduler(SchedulerInterface, ABC):
    """
    Base scheduler implementation with common scheduling logic.
    
    This class provides default implementations for common scheduling
    operations while allowing subclasses to customize specific behaviors.
    """
    
    def __init__(self, 
                 preemption_enabled: bool = True,
                 max_preemptions_per_job: int = 3,
                 min_job_runtime: timedelta = timedelta(minutes=5)):
        """
        Initialize the base scheduler.
        
        Args:
            preemption_enabled: Whether job preemption is allowed
            max_preemptions_per_job: Maximum times a job can be preempted
            min_job_runtime: Minimum time a job must run before preemption
        """
        self.preemption_enabled = preemption_enabled
        self.max_preemptions_per_job = max_preemptions_per_job
        self.min_job_runtime = min_job_runtime
        self.logger = logging.getLogger(self.__class__.__name__)
        self._preemption_history: Dict[str, int] = {}
    
    def schedule_jobs(self, jobs: List[BaseJob], nodes: List[BaseNode]) -> Dict[str, str]:
        """
        Schedule jobs to nodes using a greedy allocation strategy.
        
        Args:
            jobs: List of jobs to schedule
            nodes: List of available nodes
            
        Returns:
            Mapping of job IDs to node IDs
        """
        schedule = {}
        available_nodes = [n for n in nodes if n.is_available()]
        
        # Sort jobs by priority
        sorted_jobs = self._sort_jobs_by_priority(jobs)
        
        # Track which nodes have been assigned
        assigned_nodes = set()
        
        for job in sorted_jobs:
            if job.status != JobStatus.PENDING and job.status != JobStatus.QUEUED:
                continue
            
            # Find best node for this job
            best_node = self._find_best_node(job, available_nodes, assigned_nodes)
            
            if best_node:
                schedule[job.id] = best_node.id
                assigned_nodes.add(best_node.id)
                
                # Check if we need to preempt
                if self.preemption_enabled and not best_node.can_accommodate(job):
                    preempted = self._preempt_jobs_on_node(best_node, job)
                    if preempted:
                        self.logger.info(f"Preempted {len(preempted)} jobs for {job.id}")
        
        return schedule
    
    def update_priorities(self, jobs: List[BaseJob], current_time: datetime) -> List[BaseJob]:
        """
        Update job priorities based on current conditions.
        
        Args:
            jobs: Jobs to update priorities for
            current_time: Current timestamp
            
        Returns:
            Jobs with potentially updated priorities
        """
        for job in jobs:
            # Calculate dynamic priority adjustments
            if job.status == JobStatus.PENDING or job.status == JobStatus.QUEUED:
                # Increase priority for jobs waiting too long
                wait_time = (current_time - job.submission_time).total_seconds() / 3600
                
                if wait_time > 24 and job.priority == Priority.LOW:
                    job.priority = Priority.MEDIUM
                    self.logger.info(f"Elevated priority of {job.id} due to long wait")
                elif wait_time > 48 and job.priority == Priority.MEDIUM:
                    job.priority = Priority.HIGH
                    self.logger.info(f"Elevated priority of {job.id} due to very long wait")
                
                # Check for starvation
                if wait_time > 72 and job.priority != Priority.CRITICAL:
                    job.priority = Priority.CRITICAL
                    self.logger.warning(f"Job {job.id} elevated to CRITICAL due to starvation")
        
        return jobs
    
    def can_preempt(self, running_job: BaseJob, pending_job: BaseJob) -> bool:
        """
        Determine if a running job can be preempted for a pending job.
        
        Args:
            running_job: Currently running job
            pending_job: Job waiting to run
            
        Returns:
            True if preemption should occur
        """
        if not self.preemption_enabled:
            return False
        
        # Check preemption history
        preemption_count = self._preemption_history.get(running_job.id, 0)
        if preemption_count >= self.max_preemptions_per_job:
            return False
        
        # Check minimum runtime
        if running_job.start_time:
            runtime = datetime.now() - running_job.start_time
            if runtime < self.min_job_runtime:
                return False
        
        # Check priority difference
        if pending_job.priority <= running_job.priority:
            return False
        
        # Allow preemption for critical jobs
        if pending_job.priority == Priority.CRITICAL:
            return True
        
        # Check priority difference threshold
        priority_diff = self._calculate_priority_difference(running_job, pending_job)
        return priority_diff >= 2  # At least 2 levels difference
    
    def get_next_job(self, available_jobs: List[BaseJob], node: BaseNode) -> Optional[BaseJob]:
        """
        Get the next job to run on a specific node.
        
        Args:
            available_jobs: Jobs ready to run
            node: Node to assign job to
            
        Returns:
            Next job to run, or None if no suitable job
        """
        # Filter jobs that can run on this node
        suitable_jobs = [j for j in available_jobs if node.can_accommodate(j)]
        
        if not suitable_jobs:
            return None
        
        # Sort by priority and other factors
        sorted_jobs = self._sort_jobs_by_priority(suitable_jobs)
        
        # Return highest priority job that fits
        return sorted_jobs[0] if sorted_jobs else None
    
    def _sort_jobs_by_priority(self, jobs: List[BaseJob]) -> List[BaseJob]:
        """
        Sort jobs by priority and other scheduling factors.
        
        Args:
            jobs: Jobs to sort
            
        Returns:
            Sorted list of jobs
        """
        current_time = datetime.now()
        
        def job_sort_key(job: BaseJob) -> Tuple:
            priority_score = job.calculate_priority_score(current_time)
            wait_time = (current_time - job.submission_time).total_seconds()
            
            # Higher priority score is better (negative for reverse sort)
            # Longer wait time is better (negative for reverse sort)
            return (-priority_score, -wait_time, job.id)
        
        return sorted(jobs, key=job_sort_key)
    
    def _find_best_node(self, job: BaseJob, nodes: List[BaseNode], 
                       assigned: Set[str]) -> Optional[BaseNode]:
        """
        Find the best node for a job.
        
        Args:
            job: Job to place
            nodes: Available nodes
            assigned: Already assigned node IDs
            
        Returns:
            Best node for the job, or None
        """
        suitable_nodes = []
        
        for node in nodes:
            if node.id in assigned:
                continue
            
            if node.can_accommodate(job):
                # Calculate fitness score
                score = self._calculate_node_fitness(job, node)
                suitable_nodes.append((score, node))
        
        if not suitable_nodes:
            return None
        
        # Sort by fitness score (higher is better)
        suitable_nodes.sort(key=lambda x: x[0], reverse=True)
        return suitable_nodes[0][1]
    
    def _calculate_node_fitness(self, job: BaseJob, node: BaseNode) -> float:
        """
        Calculate how well a node fits a job's requirements.
        
        Args:
            job: Job to evaluate
            node: Node to evaluate
            
        Returns:
            Fitness score (higher is better)
        """
        score = 0.0
        
        # Base score from reliability
        score += node.reliability_score * 10
        
        # Resource utilization efficiency
        available = node.get_available_resources()
        total_available = sum(available.values())
        total_required = sum(req.amount for req in job.resource_requirements)
        
        if total_available > 0:
            utilization = total_required / total_available
            # Prefer nodes where job uses resources efficiently (not too much waste)
            if 0.5 <= utilization <= 0.9:
                score += 5
            elif 0.3 <= utilization < 0.5:
                score += 3
            elif utilization > 0.9:
                score += 4  # Very good fit
        
        # Penalty for heavily loaded nodes
        load_factor = len(node.assigned_jobs)
        score -= load_factor * 0.5
        
        return score
    
    def _preempt_jobs_on_node(self, node: BaseNode, new_job: BaseJob) -> List[str]:
        """
        Preempt jobs on a node to make room for a new job.
        
        Args:
            node: Node to preempt jobs on
            new_job: Job that needs resources
            
        Returns:
            List of preempted job IDs
        """
        # This is a placeholder - actual implementation would need
        # access to running jobs on the node
        preempted = []
        
        # Update preemption history
        for job_id in preempted:
            self._preemption_history[job_id] = self._preemption_history.get(job_id, 0) + 1
        
        return preempted
    
    def _calculate_priority_difference(self, job1: BaseJob, job2: BaseJob) -> int:
        """
        Calculate the priority level difference between two jobs.
        
        Args:
            job1: First job
            job2: Second job
            
        Returns:
            Number of priority levels difference
        """
        priority_order = [
            Priority.BACKGROUND,
            Priority.LOW,
            Priority.MEDIUM,
            Priority.HIGH,
            Priority.CRITICAL
        ]
        
        idx1 = priority_order.index(job1.priority)
        idx2 = priority_order.index(job2.priority)
        
        return abs(idx2 - idx1)
    
    @abstractmethod
    def handle_job_completion(self, job: BaseJob) -> None:
        """
        Handle job completion events.
        
        Args:
            job: Completed job
        """
        pass
    
    @abstractmethod
    def handle_job_failure(self, job: BaseJob) -> None:
        """
        Handle job failure events.
        
        Args:
            job: Failed job
        """
        pass