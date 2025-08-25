"""Dependency graph implementation for the unified task scheduling library."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
import logging

from ..core.models import BaseJob, JobDependency, DependencyType, JobStatus
from ..core.interfaces import DependencyManagerInterface
from ..core.result import Result, ErrorCode


logger = logging.getLogger(__name__)


class DependencyStatus(str, Enum):
    """Status of a dependency."""
    PENDING = "pending"      # Dependency not yet satisfied
    SATISFIED = "satisfied"  # Dependency has been satisfied
    FAILED = "failed"        # Dependency cannot be satisfied
    BYPASSED = "bypassed"    # Dependency was manually bypassed


@dataclass
class DependencyNode:
    """A node in the dependency graph representing a job."""
    job_id: str
    job: Optional[BaseJob] = None
    dependencies: Set[str] = field(default_factory=set)  # Jobs this depends on
    dependents: Set[str] = field(default_factory=set)    # Jobs that depend on this
    status: JobStatus = JobStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_ready(self, completed_jobs: Set[str]) -> bool:
        """Check if this job is ready to run (all dependencies satisfied)."""
        return all(dep_id in completed_jobs for dep_id in self.dependencies)


@dataclass
class DependencyEdge:
    """An edge in the dependency graph representing a dependency relationship."""
    from_job_id: str
    to_job_id: str
    dependency_type: DependencyType
    status: DependencyStatus = DependencyStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    satisfied_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def satisfy(self):
        """Mark this dependency as satisfied."""
        self.status = DependencyStatus.SATISFIED
        self.satisfied_time = datetime.now()
    
    def fail(self):
        """Mark this dependency as failed."""
        self.status = DependencyStatus.FAILED
    
    def bypass(self):
        """Bypass this dependency."""
        self.status = DependencyStatus.BYPASSED


class DependencyGraph(DependencyManagerInterface):
    """
    Dependency graph for managing job dependencies in the unified task scheduling system.
    
    This class handles:
    - Building and maintaining dependency graphs
    - Detecting circular dependencies
    - Finding ready-to-run jobs
    - Dependency lifecycle management
    """
    
    def __init__(self):
        """Initialize the dependency graph."""
        self.nodes: Dict[str, DependencyNode] = {}
        self.edges: Dict[Tuple[str, str], DependencyEdge] = {}
        self.completed_jobs: Set[str] = set()
        self.failed_jobs: Set[str] = set()
        
        # Caching for performance
        self._ready_jobs_cache: Optional[List[str]] = None
        self._cache_dirty: bool = True
        
        logger.info("DependencyGraph initialized")
    
    def add_job(self, job: BaseJob) -> Result[None]:
        """
        Add a job to the dependency graph.
        
        Args:
            job: Job to add
            
        Returns:
            Result indicating success or failure
        """
        if job.id in self.nodes:
            return Result.err(f"Job {job.id} already exists in dependency graph", ErrorCode.ALREADY_EXISTS)
        
        # Create node for the job
        node = DependencyNode(
            job_id=job.id,
            job=job,
            status=job.status
        )
        
        self.nodes[job.id] = node
        self._mark_cache_dirty()
        
        logger.debug(f"Added job {job.id} to dependency graph")
        return Result.ok(None)
    
    def remove_job(self, job_id: str) -> Result[None]:
        """
        Remove a job from the dependency graph.
        
        Args:
            job_id: ID of job to remove
            
        Returns:
            Result indicating success or failure
        """
        if job_id not in self.nodes:
            return Result.err(f"Job {job_id} not found in dependency graph", ErrorCode.NOT_FOUND)
        
        node = self.nodes[job_id]
        
        # Remove all dependencies involving this job
        edges_to_remove = []
        for (from_id, to_id) in self.edges:
            if from_id == job_id or to_id == job_id:
                edges_to_remove.append((from_id, to_id))
        
        for edge_key in edges_to_remove:
            del self.edges[edge_key]
        
        # Update other nodes
        for other_node in self.nodes.values():
            other_node.dependencies.discard(job_id)
            other_node.dependents.discard(job_id)
        
        # Remove node
        del self.nodes[job_id]
        self._mark_cache_dirty()
        
        logger.debug(f"Removed job {job_id} from dependency graph")
        return Result.ok(None)
    
    def add_dependency(self, dependency: JobDependency) -> Result[None]:
        """
        Add a dependency between jobs.
        
        Args:
            dependency: Dependency to add
            
        Returns:
            Result indicating success or failure
        """
        from_id = dependency.from_job
        to_id = dependency.to_job
        
        # Validate that both jobs exist
        if from_id not in self.nodes:
            return Result.err(f"Source job {from_id} not found in graph", ErrorCode.NOT_FOUND)
        
        if to_id not in self.nodes:
            return Result.err(f"Target job {to_id} not found in graph", ErrorCode.NOT_FOUND)
        
        # Check for self-dependency
        if from_id == to_id:
            return Result.err("Job cannot depend on itself", ErrorCode.INVALID_OPERATION)
        
        # Check if dependency already exists
        edge_key = (from_id, to_id)
        if edge_key in self.edges:
            return Result.err(f"Dependency from {from_id} to {to_id} already exists", ErrorCode.ALREADY_EXISTS)
        
        # Check for circular dependencies
        if self._would_create_cycle(from_id, to_id):
            return Result.err(f"Adding dependency would create a circular dependency", ErrorCode.CIRCULAR_DEPENDENCY)
        
        # Create dependency edge
        edge = DependencyEdge(
            from_job_id=from_id,
            to_job_id=to_id,
            dependency_type=dependency.dependency_type,
            metadata=dependency.metadata.copy()
        )
        
        # Add edge to graph
        self.edges[edge_key] = edge
        
        # Update nodes
        self.nodes[from_id].dependents.add(to_id)
        self.nodes[to_id].dependencies.add(from_id)
        
        self._mark_cache_dirty()
        
        logger.debug(f"Added dependency: {from_id} -> {to_id} ({dependency.dependency_type.value})")
        return Result.ok(None)
    
    def remove_dependency(self, from_job: str, to_job: str) -> Result[None]:
        """
        Remove a dependency between jobs.
        
        Args:
            from_job: Source job ID
            to_job: Target job ID
            
        Returns:
            Result indicating success or failure
        """
        edge_key = (from_job, to_job)
        
        if edge_key not in self.edges:
            return Result.err(f"Dependency from {from_job} to {to_job} not found", ErrorCode.NOT_FOUND)
        
        # Remove edge
        del self.edges[edge_key]
        
        # Update nodes
        if from_job in self.nodes:
            self.nodes[from_job].dependents.discard(to_job)
        
        if to_job in self.nodes:
            self.nodes[to_job].dependencies.discard(from_job)
        
        self._mark_cache_dirty()
        
        logger.debug(f"Removed dependency: {from_job} -> {to_job}")
        return Result.ok(None)
    
    def get_ready_jobs(self, jobs: List[BaseJob], completed_jobs: List[str]) -> List[BaseJob]:
        """
        Get jobs that are ready to run based on satisfied dependencies.
        
        Args:
            jobs: All jobs
            completed_jobs: IDs of completed jobs
            
        Returns:
            Jobs with all dependencies satisfied
        """
        completed_set = set(completed_jobs)
        completed_set.update(self.completed_jobs)
        
        ready_jobs = []
        
        for job in jobs:
            if job.id not in self.nodes:
                # Job not in dependency graph - assume it has no dependencies
                if job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
                    ready_jobs.append(job)
                continue
            
            node = self.nodes[job.id]
            
            # Skip jobs that are not in a runnable state
            if job.status not in [JobStatus.PENDING, JobStatus.QUEUED]:
                continue
            
            # Check if all dependencies are satisfied
            if node.is_ready(completed_set):
                ready_jobs.append(job)
        
        return ready_jobs
    
    def detect_circular_dependencies(self, jobs: List[BaseJob]) -> List[List[str]]:
        """
        Detect circular dependencies in job graph.
        
        Args:
            jobs: Jobs to check
            
        Returns:
            List of circular dependency chains
        """
        cycles = []
        visited = set()
        recursion_stack = set()
        path = []
        
        def dfs(job_id: str) -> bool:
            if job_id in recursion_stack:
                # Found a cycle - extract it from the path
                cycle_start = path.index(job_id)
                cycle = path[cycle_start:] + [job_id]
                cycles.append(cycle)
                return True
            
            if job_id in visited:
                return False
            
            visited.add(job_id)
            recursion_stack.add(job_id)
            path.append(job_id)
            
            # Visit all dependents
            if job_id in self.nodes:
                for dependent_id in self.nodes[job_id].dependents:
                    if dfs(dependent_id):
                        return True
            
            recursion_stack.remove(job_id)
            path.pop()
            return False
        
        # Check all nodes for cycles
        for job_id in self.nodes:
            if job_id not in visited:
                dfs(job_id)
        
        return cycles
    
    def get_dependency_graph(self, jobs: List[BaseJob]) -> Dict[str, List[str]]:
        """
        Get the dependency graph as an adjacency list.
        
        Args:
            jobs: Jobs to include in the graph
            
        Returns:
            Adjacency list representation of dependency graph
        """
        graph = {}
        job_ids = {job.id for job in jobs}
        
        for job_id in job_ids:
            graph[job_id] = []
            
            if job_id in self.nodes:
                # Add dependencies (jobs this depends on)
                for dep_id in self.nodes[job_id].dependencies:
                    if dep_id in job_ids:
                        graph[job_id].append(dep_id)
        
        return graph
    
    def update_job_status(self, job_id: str, new_status: JobStatus) -> Result[List[str]]:
        """
        Update a job's status and propagate dependency changes.
        
        Args:
            job_id: ID of job to update
            new_status: New status
            
        Returns:
            Result containing list of jobs whose ready status may have changed
        """
        if job_id not in self.nodes:
            return Result.err(f"Job {job_id} not found in dependency graph", ErrorCode.NOT_FOUND)
        
        node = self.nodes[job_id]
        old_status = node.status
        node.status = new_status
        
        affected_jobs = []
        
        if old_status != new_status:
            self._mark_cache_dirty()
            
            # Update completion tracking
            if new_status == JobStatus.COMPLETED:
                self.completed_jobs.add(job_id)
                self.failed_jobs.discard(job_id)
                
                # Satisfy outgoing dependencies
                for dependent_id in node.dependents:
                    edge_key = (job_id, dependent_id)
                    if edge_key in self.edges:
                        edge = self.edges[edge_key]
                        if edge.status == DependencyStatus.PENDING:
                            edge.satisfy()
                            affected_jobs.append(dependent_id)
            
            elif new_status == JobStatus.FAILED:
                self.failed_jobs.add(job_id)
                self.completed_jobs.discard(job_id)
                
                # Fail outgoing dependencies for completion-type dependencies
                for dependent_id in node.dependents:
                    edge_key = (job_id, dependent_id)
                    if edge_key in self.edges:
                        edge = self.edges[edge_key]
                        if (edge.status == DependencyStatus.PENDING and 
                            edge.dependency_type == DependencyType.COMPLETION):
                            edge.fail()
                            affected_jobs.append(dependent_id)
            
            # If job was previously completed/failed but now in different state
            elif old_status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                self.completed_jobs.discard(job_id)
                self.failed_jobs.discard(job_id)
                
                # Reset outgoing dependencies to pending
                for dependent_id in node.dependents:
                    edge_key = (job_id, dependent_id)
                    if edge_key in self.edges:
                        edge = self.edges[edge_key]
                        if edge.status in [DependencyStatus.SATISFIED, DependencyStatus.FAILED]:
                            edge.status = DependencyStatus.PENDING
                            edge.satisfied_time = None
                            affected_jobs.append(dependent_id)
        
        return Result.ok(affected_jobs)
    
    def bypass_dependency(self, from_job: str, to_job: str, reason: str = "Manual bypass") -> Result[None]:
        """
        Bypass a dependency relationship.
        
        Args:
            from_job: Source job ID
            to_job: Target job ID
            reason: Reason for bypass
            
        Returns:
            Result indicating success or failure
        """
        edge_key = (from_job, to_job)
        
        if edge_key not in self.edges:
            return Result.err(f"Dependency from {from_job} to {to_job} not found", ErrorCode.NOT_FOUND)
        
        edge = self.edges[edge_key]
        edge.bypass()
        edge.metadata["bypass_reason"] = reason
        edge.metadata["bypass_time"] = datetime.now().isoformat()
        
        self._mark_cache_dirty()
        
        logger.info(f"Bypassed dependency {from_job} -> {to_job}: {reason}")
        return Result.ok(None)
    
    def get_job_dependencies(self, job_id: str) -> List[str]:
        """Get all jobs that a specific job depends on."""
        if job_id not in self.nodes:
            return []
        
        return list(self.nodes[job_id].dependencies)
    
    def get_job_dependents(self, job_id: str) -> List[str]:
        """Get all jobs that depend on a specific job."""
        if job_id not in self.nodes:
            return []
        
        return list(self.nodes[job_id].dependents)
    
    def get_dependency_status(self, from_job: str, to_job: str) -> Optional[DependencyStatus]:
        """Get the status of a specific dependency."""
        edge_key = (from_job, to_job)
        if edge_key in self.edges:
            return self.edges[edge_key].status
        return None
    
    def get_topological_order(self) -> List[str]:
        """Get jobs in topological order (dependencies before dependents)."""
        # Kahn's algorithm for topological sorting
        in_degree = {}
        for job_id in self.nodes:
            in_degree[job_id] = len(self.nodes[job_id].dependencies)
        
        queue = [job_id for job_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            job_id = queue.pop(0)
            result.append(job_id)
            
            # Process dependents
            for dependent_id in self.nodes[job_id].dependents:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        # Check for cycles
        if len(result) != len(self.nodes):
            logger.warning("Circular dependencies detected - topological sort incomplete")
        
        return result
    
    def get_critical_path(self) -> List[str]:
        """Get the critical path (longest path) through the dependency graph."""
        # This is a simplified implementation
        # In practice, would need job duration estimates
        
        topo_order = self.get_topological_order()
        distances = {job_id: 0 for job_id in self.nodes}
        predecessors = {}
        
        # Calculate longest paths
        for job_id in topo_order:
            node = self.nodes[job_id]
            for dependent_id in node.dependents:
                # Assume each job takes 1 unit of time (would use actual duration in practice)
                new_distance = distances[job_id] + 1
                if new_distance > distances[dependent_id]:
                    distances[dependent_id] = new_distance
                    predecessors[dependent_id] = job_id
        
        # Find the job with maximum distance (end of critical path)
        max_distance = max(distances.values()) if distances else 0
        end_jobs = [job_id for job_id, dist in distances.items() if dist == max_distance]
        
        if not end_jobs:
            return []
        
        # Reconstruct critical path
        critical_path = []
        current = end_jobs[0]  # Use first end job if multiple
        
        while current:
            critical_path.append(current)
            current = predecessors.get(current)
        
        critical_path.reverse()
        return critical_path
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dependency graph statistics."""
        stats = {
            "total_jobs": len(self.nodes),
            "total_dependencies": len(self.edges),
            "completed_jobs": len(self.completed_jobs),
            "failed_jobs": len(self.failed_jobs),
            "jobs_without_dependencies": 0,
            "jobs_without_dependents": 0,
            "dependency_types": {},
            "dependency_statuses": {}
        }
        
        # Count jobs without dependencies/dependents
        for node in self.nodes.values():
            if not node.dependencies:
                stats["jobs_without_dependencies"] += 1
            if not node.dependents:
                stats["jobs_without_dependents"] += 1
        
        # Count dependency types and statuses
        for edge in self.edges.values():
            dep_type = edge.dependency_type.value
            dep_status = edge.status.value
            
            stats["dependency_types"][dep_type] = stats["dependency_types"].get(dep_type, 0) + 1
            stats["dependency_statuses"][dep_status] = stats["dependency_statuses"].get(dep_status, 0) + 1
        
        return stats
    
    def _would_create_cycle(self, from_id: str, to_id: str) -> bool:
        """Check if adding a dependency would create a cycle."""
        # Use DFS to check if there's already a path from to_id to from_id
        visited = set()
        
        def has_path(start: str, target: str) -> bool:
            if start == target:
                return True
            
            if start in visited:
                return False
            
            visited.add(start)
            
            if start in self.nodes:
                for dependent in self.nodes[start].dependents:
                    if has_path(dependent, target):
                        return True
            
            return False
        
        return has_path(to_id, from_id)
    
    def _mark_cache_dirty(self):
        """Mark caches as dirty."""
        self._cache_dirty = True
        self._ready_jobs_cache = None