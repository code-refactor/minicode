"""Dependency resolution for the unified task scheduling library."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
import logging

from ..core.models import BaseJob, JobStatus, JobDependency, DependencyType
from ..core.result import Result, ErrorCode
from .dependency_graph import DependencyGraph, DependencyStatus


logger = logging.getLogger(__name__)


class ResolutionStrategy(str, Enum):
    """Strategies for resolving dependencies."""
    STRICT = "strict"            # All dependencies must be satisfied
    BEST_EFFORT = "best_effort"  # Try to satisfy as many as possible
    TIMEOUT_BASED = "timeout_based"  # Skip dependencies after timeout
    PRIORITY_AWARE = "priority_aware"  # Consider job priorities in resolution


class ConflictResolution(str, Enum):
    """Ways to resolve dependency conflicts."""
    FAIL_FAST = "fail_fast"      # Fail immediately on conflict
    BYPASS_FAILED = "bypass_failed"  # Bypass failed dependencies
    RETRY_FAILED = "retry_failed"    # Retry failed dependencies
    MANUAL_REVIEW = "manual_review"  # Queue for manual review


@dataclass
class ResolutionResult:
    """Result of dependency resolution."""
    resolved_jobs: List[str]
    blocked_jobs: List[str]
    failed_dependencies: List[Tuple[str, str, str]]  # (from_job, to_job, reason)
    bypassed_dependencies: List[Tuple[str, str, str]]  # (from_job, to_job, reason)
    warnings: List[str]
    resolution_time: datetime = field(default_factory=datetime.now)


@dataclass
class ResolutionContext:
    """Context for dependency resolution."""
    current_time: datetime = field(default_factory=datetime.now)
    completed_jobs: Set[str] = field(default_factory=set)
    failed_jobs: Set[str] = field(default_factory=set)
    running_jobs: Set[str] = field(default_factory=set)
    timeout_threshold: timedelta = timedelta(hours=24)
    priority_threshold: int = 0
    max_resolution_depth: int = 100


class DependencyResolver:
    """
    Dependency resolver for the unified task scheduling library.
    
    This class handles:
    - Resolving job dependencies based on current state
    - Handling dependency conflicts and failures
    - Providing resolution strategies
    - Optimizing dependency resolution performance
    """
    
    def __init__(self, 
                 strategy: ResolutionStrategy = ResolutionStrategy.STRICT,
                 conflict_resolution: ConflictResolution = ConflictResolution.FAIL_FAST,
                 default_timeout: timedelta = timedelta(hours=24)):
        """
        Initialize the dependency resolver.
        
        Args:
            strategy: Default resolution strategy
            conflict_resolution: How to handle conflicts
            default_timeout: Default timeout for dependency resolution
        """
        self.strategy = strategy
        self.conflict_resolution = conflict_resolution
        self.default_timeout = default_timeout
        
        # Resolution history and statistics
        self.resolution_history: List[ResolutionResult] = []
        self.dependency_timeouts: Dict[Tuple[str, str], datetime] = {}
        self.manual_review_queue: List[Tuple[str, str, str]] = []  # (from_job, to_job, reason)
        
        # Performance optimization
        self._resolution_cache: Dict[str, ResolutionResult] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(minutes=5)
        
        logger.info(f"DependencyResolver initialized with {strategy.value} strategy")
    
    def resolve_dependencies(self, 
                           dependency_graph: DependencyGraph,
                           jobs: List[BaseJob],
                           context: Optional[ResolutionContext] = None) -> ResolutionResult:
        """
        Resolve dependencies for a set of jobs.
        
        Args:
            dependency_graph: The dependency graph
            jobs: Jobs to resolve dependencies for
            context: Resolution context
            
        Returns:
            Resolution result with resolved and blocked jobs
        """
        if context is None:
            context = ResolutionContext()
        
        # Check cache first
        cache_key = self._get_cache_key(jobs, context)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        result = ResolutionResult(
            resolved_jobs=[],
            blocked_jobs=[],
            failed_dependencies=[],
            bypassed_dependencies=[],
            warnings=[]
        )
        
        # Update context with current job states
        self._update_context_from_jobs(context, jobs)
        
        # Process jobs based on strategy
        if self.strategy == ResolutionStrategy.STRICT:
            result = self._strict_resolution(dependency_graph, jobs, context)
        elif self.strategy == ResolutionStrategy.BEST_EFFORT:
            result = self._best_effort_resolution(dependency_graph, jobs, context)
        elif self.strategy == ResolutionStrategy.TIMEOUT_BASED:
            result = self._timeout_based_resolution(dependency_graph, jobs, context)
        elif self.strategy == ResolutionStrategy.PRIORITY_AWARE:
            result = self._priority_aware_resolution(dependency_graph, jobs, context)
        
        # Apply conflict resolution
        result = self._apply_conflict_resolution(dependency_graph, result, context)
        
        # Cache result
        self._cache_result(cache_key, result)
        
        # Store in history
        self.resolution_history.append(result)
        if len(self.resolution_history) > 1000:  # Keep only recent history
            self.resolution_history = self.resolution_history[-1000:]
        
        logger.debug(f"Resolved {len(result.resolved_jobs)} jobs, "
                    f"blocked {len(result.blocked_jobs)} jobs")
        
        return result
    
    def check_job_readiness(self, 
                          job: BaseJob, 
                          dependency_graph: DependencyGraph,
                          context: Optional[ResolutionContext] = None) -> Tuple[bool, List[str]]:
        """
        Check if a specific job is ready to run.
        
        Args:
            job: Job to check
            dependency_graph: The dependency graph
            context: Resolution context
            
        Returns:
            Tuple of (is_ready, blocking_dependencies)
        """
        if context is None:
            context = ResolutionContext()
        
        dependencies = dependency_graph.get_job_dependencies(job.id)
        blocking_deps = []
        
        for dep_job_id in dependencies:
            # Check if dependency is satisfied
            if not self._is_dependency_satisfied(job.id, dep_job_id, dependency_graph, context):
                blocking_deps.append(dep_job_id)
        
        is_ready = len(blocking_deps) == 0
        return is_ready, blocking_deps
    
    def suggest_dependency_optimizations(self, 
                                       dependency_graph: DependencyGraph,
                                       jobs: List[BaseJob]) -> List[Dict[str, Any]]:
        """
        Suggest optimizations for the dependency graph.
        
        Args:
            dependency_graph: The dependency graph
            jobs: Jobs to analyze
            
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Detect long dependency chains
        critical_path = dependency_graph.get_critical_path()
        if len(critical_path) > 10:  # Arbitrary threshold
            suggestions.append({
                "type": "long_critical_path",
                "severity": "medium",
                "description": f"Critical path has {len(critical_path)} jobs",
                "recommendation": "Consider parallelizing some dependencies",
                "affected_jobs": critical_path
            })
        
        # Detect jobs with many dependencies
        for job in jobs:
            deps = dependency_graph.get_job_dependencies(job.id)
            if len(deps) > 5:  # Arbitrary threshold
                suggestions.append({
                    "type": "many_dependencies",
                    "severity": "low",
                    "description": f"Job {job.id} has {len(deps)} dependencies",
                    "recommendation": "Consider splitting job or reducing dependencies",
                    "affected_jobs": [job.id]
                })
        
        # Detect potential bottlenecks
        for job in jobs:
            dependents = dependency_graph.get_job_dependents(job.id)
            if len(dependents) > 10:  # Arbitrary threshold
                suggestions.append({
                    "type": "bottleneck",
                    "severity": "high",
                    "description": f"Job {job.id} blocks {len(dependents)} other jobs",
                    "recommendation": "Prioritize this job or parallelize its outputs",
                    "affected_jobs": [job.id] + dependents
                })
        
        # Detect circular dependencies
        cycles = dependency_graph.detect_circular_dependencies(jobs)
        for cycle in cycles:
            suggestions.append({
                "type": "circular_dependency",
                "severity": "critical",
                "description": f"Circular dependency detected: {' -> '.join(cycle)}",
                "recommendation": "Break the circular dependency",
                "affected_jobs": cycle
            })
        
        return suggestions
    
    def bypass_dependency(self, 
                         from_job_id: str, 
                         to_job_id: str,
                         dependency_graph: DependencyGraph,
                         reason: str = "Manual bypass") -> Result[None]:
        """
        Bypass a specific dependency.
        
        Args:
            from_job_id: Source job ID
            to_job_id: Target job ID
            dependency_graph: The dependency graph
            reason: Reason for bypass
            
        Returns:
            Result indicating success or failure
        """
        result = dependency_graph.bypass_dependency(from_job_id, to_job_id, reason)
        
        if result.success:
            # Clear related caches
            self._clear_cache()
            
            logger.info(f"Bypassed dependency {from_job_id} -> {to_job_id}: {reason}")
        
        return result
    
    def get_resolution_statistics(self) -> Dict[str, Any]:
        """Get statistics about dependency resolution."""
        if not self.resolution_history:
            return {"message": "No resolution history available"}
        
        recent_resolutions = self.resolution_history[-100:]  # Last 100 resolutions
        
        stats = {
            "total_resolutions": len(self.resolution_history),
            "recent_resolutions": len(recent_resolutions),
            "average_resolved_jobs": 0,
            "average_blocked_jobs": 0,
            "total_failed_dependencies": 0,
            "total_bypassed_dependencies": 0,
            "cache_hit_rate": 0,
            "manual_review_queue_size": len(self.manual_review_queue)
        }
        
        if recent_resolutions:
            stats["average_resolved_jobs"] = sum(len(r.resolved_jobs) for r in recent_resolutions) / len(recent_resolutions)
            stats["average_blocked_jobs"] = sum(len(r.blocked_jobs) for r in recent_resolutions) / len(recent_resolutions)
            stats["total_failed_dependencies"] = sum(len(r.failed_dependencies) for r in recent_resolutions)
            stats["total_bypassed_dependencies"] = sum(len(r.bypassed_dependencies) for r in recent_resolutions)
        
        # Calculate cache statistics
        total_cache_requests = len(self._resolution_cache) + len(recent_resolutions)
        if total_cache_requests > 0:
            cache_hits = len(self._resolution_cache)
            stats["cache_hit_rate"] = cache_hits / total_cache_requests
        
        return stats
    
    def _strict_resolution(self, 
                          dependency_graph: DependencyGraph, 
                          jobs: List[BaseJob],
                          context: ResolutionContext) -> ResolutionResult:
        """Perform strict dependency resolution."""
        result = ResolutionResult(
            resolved_jobs=[],
            blocked_jobs=[],
            failed_dependencies=[],
            bypassed_dependencies=[],
            warnings=[]
        )
        
        for job in jobs:
            if job.status not in [JobStatus.PENDING, JobStatus.QUEUED]:
                continue
            
            dependencies = dependency_graph.get_job_dependencies(job.id)
            
            # Check if all dependencies are satisfied
            all_satisfied = True
            for dep_job_id in dependencies:
                if not self._is_dependency_satisfied(job.id, dep_job_id, dependency_graph, context):
                    all_satisfied = False
                    break
            
            if all_satisfied:
                result.resolved_jobs.append(job.id)
            else:
                result.blocked_jobs.append(job.id)
        
        return result
    
    def _best_effort_resolution(self, 
                               dependency_graph: DependencyGraph,
                               jobs: List[BaseJob],
                               context: ResolutionContext) -> ResolutionResult:
        """Perform best-effort dependency resolution."""
        result = ResolutionResult(
            resolved_jobs=[],
            blocked_jobs=[],
            failed_dependencies=[],
            bypassed_dependencies=[],
            warnings=[]
        )
        
        for job in jobs:
            if job.status not in [JobStatus.PENDING, JobStatus.QUEUED]:
                continue
            
            dependencies = dependency_graph.get_job_dependencies(job.id)
            satisfied_deps = 0
            failed_deps = []
            
            for dep_job_id in dependencies:
                if self._is_dependency_satisfied(job.id, dep_job_id, dependency_graph, context):
                    satisfied_deps += 1
                else:
                    # Check if dependency has failed
                    if dep_job_id in context.failed_jobs:
                        failed_deps.append(dep_job_id)
            
            # If most dependencies are satisfied or failed dependencies can be bypassed
            satisfaction_ratio = satisfied_deps / len(dependencies) if dependencies else 1.0
            
            if satisfaction_ratio >= 0.8 or not dependencies:  # 80% threshold
                result.resolved_jobs.append(job.id)
                
                # Bypass failed dependencies
                for failed_dep in failed_deps:
                    result.bypassed_dependencies.append((failed_dep, job.id, "Failed dependency bypassed in best-effort mode"))
            else:
                result.blocked_jobs.append(job.id)
        
        return result
    
    def _timeout_based_resolution(self,
                                 dependency_graph: DependencyGraph,
                                 jobs: List[BaseJob],
                                 context: ResolutionContext) -> ResolutionResult:
        """Perform timeout-based dependency resolution."""
        result = ResolutionResult(
            resolved_jobs=[],
            blocked_jobs=[],
            failed_dependencies=[],
            bypassed_dependencies=[],
            warnings=[]
        )
        
        for job in jobs:
            if job.status not in [JobStatus.PENDING, JobStatus.QUEUED]:
                continue
            
            dependencies = dependency_graph.get_job_dependencies(job.id)
            can_run = True
            timed_out_deps = []
            
            for dep_job_id in dependencies:
                if self._is_dependency_satisfied(job.id, dep_job_id, dependency_graph, context):
                    continue
                
                # Check if dependency has timed out
                dep_key = (dep_job_id, job.id)
                if dep_key not in self.dependency_timeouts:
                    self.dependency_timeouts[dep_key] = context.current_time
                
                wait_time = context.current_time - self.dependency_timeouts[dep_key]
                
                if wait_time > context.timeout_threshold:
                    timed_out_deps.append(dep_job_id)
                    result.bypassed_dependencies.append((dep_job_id, job.id, f"Dependency timed out after {wait_time}"))
                else:
                    can_run = False
            
            if can_run:
                result.resolved_jobs.append(job.id)
            else:
                result.blocked_jobs.append(job.id)
        
        return result
    
    def _priority_aware_resolution(self,
                                  dependency_graph: DependencyGraph,
                                  jobs: List[BaseJob],
                                  context: ResolutionContext) -> ResolutionResult:
        """Perform priority-aware dependency resolution."""
        result = ResolutionResult(
            resolved_jobs=[],
            blocked_jobs=[],
            failed_dependencies=[],
            bypassed_dependencies=[],
            warnings=[]
        )
        
        # Sort jobs by priority
        sorted_jobs = sorted(jobs, key=lambda j: j.calculate_priority_score(context.current_time), reverse=True)
        
        for job in sorted_jobs:
            if job.status not in [JobStatus.PENDING, JobStatus.QUEUED]:
                continue
            
            job_priority_score = job.calculate_priority_score(context.current_time)
            dependencies = dependency_graph.get_job_dependencies(job.id)
            
            can_run = True
            bypassed_low_priority_deps = []
            
            for dep_job_id in dependencies:
                if self._is_dependency_satisfied(job.id, dep_job_id, dependency_graph, context):
                    continue
                
                # Find the dependency job to check its priority
                dep_job = next((j for j in jobs if j.id == dep_job_id), None)
                
                if dep_job is None:
                    # Dependency job not found - might be external or completed
                    can_run = False
                    continue
                
                dep_priority_score = dep_job.calculate_priority_score(context.current_time)
                
                # If current job has much higher priority, consider bypassing the dependency
                if job_priority_score > dep_priority_score * 1.5:  # 50% higher priority
                    bypassed_low_priority_deps.append(dep_job_id)
                    result.bypassed_dependencies.append((dep_job_id, job.id, 
                                                       f"Bypassed low-priority dependency (job priority: {job_priority_score:.2f}, dep priority: {dep_priority_score:.2f})"))
                else:
                    can_run = False
            
            if can_run:
                result.resolved_jobs.append(job.id)
            else:
                result.blocked_jobs.append(job.id)
        
        return result
    
    def _apply_conflict_resolution(self,
                                  dependency_graph: DependencyGraph,
                                  result: ResolutionResult,
                                  context: ResolutionContext) -> ResolutionResult:
        """Apply conflict resolution strategy."""
        if self.conflict_resolution == ConflictResolution.FAIL_FAST:
            # Default behavior - no additional processing
            pass
        
        elif self.conflict_resolution == ConflictResolution.BYPASS_FAILED:
            # Bypass dependencies to failed jobs
            additional_bypasses = []
            for job_id in result.blocked_jobs[:]:  # Copy list to modify during iteration
                dependencies = dependency_graph.get_job_dependencies(job_id)
                failed_deps = [dep for dep in dependencies if dep in context.failed_jobs]
                
                if failed_deps:
                    # Bypass failed dependencies
                    for failed_dep in failed_deps:
                        additional_bypasses.append((failed_dep, job_id, "Bypassed failed dependency"))
                    
                    # Move job from blocked to resolved
                    result.blocked_jobs.remove(job_id)
                    result.resolved_jobs.append(job_id)
            
            result.bypassed_dependencies.extend(additional_bypasses)
        
        elif self.conflict_resolution == ConflictResolution.RETRY_FAILED:
            # Mark failed dependencies for retry
            for job_id in result.blocked_jobs:
                dependencies = dependency_graph.get_job_dependencies(job_id)
                for dep_job_id in dependencies:
                    if dep_job_id in context.failed_jobs:
                        # Reset dependency status for retry
                        dep_status = dependency_graph.get_dependency_status(dep_job_id, job_id)
                        if dep_status == DependencyStatus.FAILED:
                            result.warnings.append(f"Retrying failed dependency: {dep_job_id} -> {job_id}")
        
        elif self.conflict_resolution == ConflictResolution.MANUAL_REVIEW:
            # Queue complex conflicts for manual review
            for job_id in result.blocked_jobs:
                dependencies = dependency_graph.get_job_dependencies(job_id)
                complex_deps = []
                
                for dep_job_id in dependencies:
                    if (dep_job_id in context.failed_jobs or 
                        (dep_job_id, job_id) in self.dependency_timeouts):
                        complex_deps.append(dep_job_id)
                
                if complex_deps:
                    for dep_job_id in complex_deps:
                        self.manual_review_queue.append((dep_job_id, job_id, "Complex dependency conflict"))
                        result.warnings.append(f"Queued for manual review: {dep_job_id} -> {job_id}")
        
        return result
    
    def _is_dependency_satisfied(self,
                                job_id: str,
                                dep_job_id: str,
                                dependency_graph: DependencyGraph,
                                context: ResolutionContext) -> bool:
        """Check if a dependency is satisfied."""
        # Check dependency status in graph
        dep_status = dependency_graph.get_dependency_status(dep_job_id, job_id)
        
        if dep_status in [DependencyStatus.SATISFIED, DependencyStatus.BYPASSED]:
            return True
        
        if dep_status == DependencyStatus.FAILED:
            return False
        
        # Check if dependency job is completed
        if dep_job_id in context.completed_jobs:
            return True
        
        # Check if dependency job is running (for START type dependencies)
        # This would need to be enhanced based on dependency type
        if dep_job_id in context.running_jobs:
            # For now, assume running jobs don't satisfy dependencies
            # In practice, this would depend on the dependency type
            return False
        
        return False
    
    def _update_context_from_jobs(self, context: ResolutionContext, jobs: List[BaseJob]):
        """Update resolution context based on current job states."""
        for job in jobs:
            if job.status == JobStatus.COMPLETED:
                context.completed_jobs.add(job.id)
            elif job.status == JobStatus.FAILED:
                context.failed_jobs.add(job.id)
            elif job.status == JobStatus.RUNNING:
                context.running_jobs.add(job.id)
    
    def _get_cache_key(self, jobs: List[BaseJob], context: ResolutionContext) -> str:
        """Generate cache key for resolution result."""
        job_states = tuple(sorted(f"{job.id}:{job.status.value}" for job in jobs))
        context_hash = hash((
            tuple(sorted(context.completed_jobs)),
            tuple(sorted(context.failed_jobs)),
            tuple(sorted(context.running_jobs)),
            context.current_time.replace(second=0, microsecond=0)  # Minute precision
        ))
        
        return f"{hash(job_states)}:{context_hash}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[ResolutionResult]:
        """Get cached resolution result if still valid."""
        if cache_key in self._resolution_cache:
            expiry = self._cache_expiry.get(cache_key)
            if expiry and datetime.now() < expiry:
                return self._resolution_cache[cache_key]
            else:
                # Remove expired entry
                del self._resolution_cache[cache_key]
                self._cache_expiry.pop(cache_key, None)
        
        return None
    
    def _cache_result(self, cache_key: str, result: ResolutionResult):
        """Cache resolution result."""
        self._resolution_cache[cache_key] = result
        self._cache_expiry[cache_key] = datetime.now() + self.cache_ttl
        
        # Limit cache size
        if len(self._resolution_cache) > 100:
            # Remove oldest entries
            oldest_keys = sorted(self._cache_expiry.keys(), key=lambda k: self._cache_expiry[k])[:50]
            for key in oldest_keys:
                self._resolution_cache.pop(key, None)
                self._cache_expiry.pop(key, None)
    
    def _clear_cache(self):
        """Clear resolution cache."""
        self._resolution_cache.clear()
        self._cache_expiry.clear()