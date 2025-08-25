"""Queue management for long-running simulation jobs."""

from __future__ import annotations

import heapq
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from concurrent_task_scheduler.models import (
    Result,
    Simulation,
    Priority as SimulationPriority,  # Import Priority as SimulationPriority for compatibility
    SimulationStatus,
)
from concurrent_task_scheduler.models.utils import generate_id

logger = logging.getLogger(__name__)


class QueuePolicy(str, Enum):
    """Policies for managing the job queue."""

    FIFO = "fifo"  # First in, first out
    PRIORITY = "priority"  # Strict priority ordering
    FAIR = "fair"  # Fair sharing between users/projects
    DEADLINE = "deadline"  # Deadline-driven ordering
    WEIGHTED = "weighted"  # Weighted combination of factors


class FairnessMetric(str, Enum):
    """Metrics for evaluating fairness in resource allocation."""

    CPU_TIME = "cpu_time"  # Total CPU time allocated
    WAIT_TIME = "wait_time"  # Queue wait time
    JOB_COUNT = "job_count"  # Number of jobs run
    RESOURCE_SHARE = "resource_share"  # Share of total resources
    WEIGHTED = "weighted"  # Weighted combination of metrics


class QueueStats:
    """Statistics for a job queue."""

    def __init__(self):
        self.total_jobs_submitted = 0
        self.total_jobs_started = 0
        self.total_jobs_completed = 0
        self.total_jobs_failed = 0
        self.total_jobs_cancelled = 0
        self.total_wait_time = timedelta()
        self.avg_wait_time = timedelta()
        self.max_wait_time = timedelta()
        self.current_queue_length = 0
        self.peak_queue_length = 0
        self.by_priority: Dict[SimulationPriority, int] = {
            priority: 0 for priority in SimulationPriority
        }
        self.by_user: Dict[str, int] = {}
        self.by_project: Dict[str, int] = {}
        self.last_updated = datetime.now()
    
    def update_on_submit(self, simulation: Simulation) -> None:
        """Update stats when a simulation is submitted."""
        self.total_jobs_submitted += 1
        self.current_queue_length += 1
        self.peak_queue_length = max(self.peak_queue_length, self.current_queue_length)
        self.by_priority[simulation.priority] += 1
        
        self.by_user[simulation.owner] = self.by_user.get(simulation.owner, 0) + 1
        self.by_project[simulation.project] = self.by_project.get(simulation.project, 0) + 1
        self.last_updated = datetime.now()
    
    def update_on_start(self, simulation: Simulation, submit_time: datetime) -> None:
        """Update stats when a simulation starts running."""
        self.total_jobs_started += 1
        self.current_queue_length -= 1
        
        wait_time = datetime.now() - submit_time
        self.total_wait_time += wait_time
        self.max_wait_time = max(self.max_wait_time, wait_time)
        
        if self.total_jobs_started > 0:
            self.avg_wait_time = self.total_wait_time / self.total_jobs_started
        
        self.last_updated = datetime.now()
    
    def update_on_complete(self, simulation: Simulation) -> None:
        """Update stats when a simulation completes."""
        self.total_jobs_completed += 1
        self.last_updated = datetime.now()
    
    def update_on_fail(self, simulation: Simulation) -> None:
        """Update stats when a simulation fails."""
        self.total_jobs_failed += 1
        self.last_updated = datetime.now()
    
    def update_on_cancel(self, simulation: Simulation) -> None:
        """Update stats when a simulation is cancelled."""
        self.total_jobs_cancelled += 1
        self.current_queue_length -= 1
        self.last_updated = datetime.now()


class QueuedJob:
    """A job in the simulation queue."""

    def __init__(self, simulation: Simulation, submit_time: datetime):
        self.simulation = simulation
        self.submit_time = submit_time
        self.priority_updates: List[Tuple[datetime, SimulationPriority]] = [
            (submit_time, simulation.priority)
        ]
        self.effective_priority = simulation.priority
        self.last_priority_decay = submit_time
        self.preemption_count = 0
        self.last_preemption_time: Optional[datetime] = None
        self.estimated_start_time: Optional[datetime] = None
        self.user_notified = False
        self.retry_count = 0
    
    def wait_time(self) -> timedelta:
        """Get the current wait time for this job."""
        return datetime.now() - self.submit_time
    
    def update_priority(self, new_priority: SimulationPriority) -> None:
        """Update the job's priority."""
        if new_priority != self.simulation.priority:
            self.simulation.priority = new_priority
            self.priority_updates.append((datetime.now(), new_priority))
            self.effective_priority = new_priority
    
    def record_preemption(self) -> None:
        """Record that this job was preempted."""
        self.preemption_count += 1
        self.last_preemption_time = datetime.now()
    
    def get_priority_history(self) -> List[Tuple[datetime, SimulationPriority]]:
        """Get the job's priority history."""
        return self.priority_updates.copy()
    
    def __lt__(self, other: QueuedJob) -> bool:
        """Compare jobs for priority queue ordering."""
        if self.effective_priority != other.effective_priority:
            # Higher priority (CRITICAL) comes first
            return self.effective_priority.value < other.effective_priority.value
        
        # For same priority, older jobs come first (FIFO)
        return self.submit_time < other.submit_time


class PreemptionAction(str, Enum):
    """Actions that can be taken when preemption is triggered."""

    CHECKPOINT_AND_STOP = "checkpoint_and_stop"  # Create checkpoint and stop job
    MIGRATE = "migrate"  # Try to migrate job to other resources
    REQUEUE = "requeue"  # Move job back to queue
    CONTINUE_LIMITED = "continue_limited"  # Continue with limited resources
    CANCEL = "cancel"  # Cancel job entirely


class PreemptionTrigger(str, Enum):
    """Triggers for job preemption."""

    HIGHER_PRIORITY = "higher_priority"  # Higher priority job needs resources
    MAINTENANCE = "maintenance"  # System maintenance
    RESOURCE_SHORTAGE = "resource_shortage"  # Insufficient resources
    FAIRNESS = "fairness"  # Fairness policy enforcement
    ADMIN = "admin"  # Administrative action
    DEADLINE = "deadline"  # Job exceeded deadline


class PreemptionPolicy:
    """Policy for job preemption."""

    def __init__(
        self,
        max_preemptions_per_day: Dict[SimulationPriority, int] = None,
        min_runtime_before_preemption: timedelta = timedelta(hours=1),
        protection_after_preemption: timedelta = timedelta(hours=6),
        checkpoint_before_preemption: bool = True,
    ):
        if max_preemptions_per_day is None:
            self.max_preemptions_per_day = {
                SimulationPriority.CRITICAL: 0,  # Cannot be preempted
                SimulationPriority.HIGH: 1,
                SimulationPriority.MEDIUM: 2,
                SimulationPriority.LOW: 4,
                SimulationPriority.BACKGROUND: 8,
            }
        else:
            self.max_preemptions_per_day = max_preemptions_per_day
        
        self.min_runtime_before_preemption = min_runtime_before_preemption
        self.protection_after_preemption = protection_after_preemption
        self.checkpoint_before_preemption = checkpoint_before_preemption
        self.preemption_history: Dict[str, List[datetime]] = {}
    
    def can_preempt(
        self,
        simulation: Simulation,
        trigger: PreemptionTrigger,
        current_time: Optional[datetime] = None,
        runtime: Optional[timedelta] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Determine if a simulation can be preempted."""
        if current_time is None:
            current_time = datetime.now()
        
        # Critical jobs cannot be preempted
        if simulation.priority == SimulationPriority.CRITICAL:
            return False, "Critical priority jobs cannot be preempted"
        
        # Maintenance preemption may override other restrictions
        if trigger == PreemptionTrigger.MAINTENANCE:
            # Still don't preempt critical jobs
            if simulation.priority == SimulationPriority.CRITICAL:
                return False, "Critical priority jobs cannot be preempted even for maintenance"
            
            # For others, maintenance can override
            return True, None
        
        # Check if it's been running long enough
        if runtime is not None and runtime < self.min_runtime_before_preemption:
            return False, f"Job has not run long enough for preemption ({runtime} < {self.min_runtime_before_preemption})"
        
        # Check preemption history
        sim_id = simulation.id
        if sim_id in self.preemption_history:
            # Check if recently preempted
            last_preemption = max(self.preemption_history[sim_id])
            if current_time - last_preemption < self.protection_after_preemption:
                return False, f"Job was recently preempted and is protected ({current_time - last_preemption} < {self.protection_after_preemption})"
            
            # Check daily limit
            today = current_time.date()
            preemptions_today = sum(
                1 for ts in self.preemption_history[sim_id]
                if ts.date() == today
            )
            
            max_preemptions = self.max_preemptions_per_day.get(simulation.priority, 0)
            if preemptions_today >= max_preemptions:
                return False, f"Job has reached maximum preemptions for today ({preemptions_today} >= {max_preemptions})"
        
        return True, None
    
    def record_preemption(self, simulation_id: str, time: Optional[datetime] = None) -> None:
        """Record a preemption event."""
        if time is None:
            time = datetime.now()
        
        if simulation_id not in self.preemption_history:
            self.preemption_history[simulation_id] = []
        
        self.preemption_history[simulation_id].append(time)
    
    def get_action_for_trigger(
        self,
        simulation: Simulation,
        trigger: PreemptionTrigger,
    ) -> PreemptionAction:
        """Determine the appropriate preemption action for a trigger."""
        if trigger == PreemptionTrigger.MAINTENANCE:
            return PreemptionAction.CHECKPOINT_AND_STOP
        
        if trigger == PreemptionTrigger.HIGHER_PRIORITY:
            # Try migration first for high priority jobs
            if simulation.priority in [SimulationPriority.HIGH, SimulationPriority.MEDIUM]:
                return PreemptionAction.MIGRATE
            return PreemptionAction.CHECKPOINT_AND_STOP
        
        if trigger == PreemptionTrigger.RESOURCE_SHORTAGE:
            # For resource shortage, requeue lower priority jobs
            if simulation.priority in [SimulationPriority.LOW, SimulationPriority.BACKGROUND]:
                return PreemptionAction.REQUEUE
            return PreemptionAction.CONTINUE_LIMITED
        
        if trigger == PreemptionTrigger.FAIRNESS:
            return PreemptionAction.REQUEUE
        
        if trigger == PreemptionTrigger.ADMIN:
            return PreemptionAction.CHECKPOINT_AND_STOP
        
        if trigger == PreemptionTrigger.DEADLINE:
            return PreemptionAction.CANCEL
        
        # Default
        return PreemptionAction.CHECKPOINT_AND_STOP


class JobQueue:
    """Queue for managing simulation jobs."""

    def __init__(
        self,
        policy: QueuePolicy = QueuePolicy.WEIGHTED,
        preemption_policy: Optional[PreemptionPolicy] = None,
    ):
        self.policy = policy
        self.preemption_policy = preemption_policy or PreemptionPolicy()
        self.queue: List[QueuedJob] = []
        self.job_map: Dict[str, QueuedJob] = {}
        self.stats = QueueStats()
        self.priority_aging_factor = 0.1  # How much to boost priority over time
        self.aging_interval = timedelta(hours=12)  # How often to apply aging
        self.user_fairness_weights: Dict[str, float] = {}  # Weights for fair sharing
        self.project_fairness_weights: Dict[str, float] = {}  # Weights for fair sharing
        self.fairness_metric = FairnessMetric.WEIGHTED
        self.last_fairness_adjustment = datetime.now()
        self.fairness_adjustment_interval = timedelta(hours=6)
    
    def enqueue(self, simulation: Simulation) -> str:
        """Add a simulation to the queue."""
        if simulation.id in self.job_map:
            return f"Simulation {simulation.id} is already in the queue"
        
        job = QueuedJob(simulation, datetime.now())
        heapq.heappush(self.queue, job)
        self.job_map[simulation.id] = job
        
        self.stats.update_on_submit(simulation)
        
        return f"Simulation {simulation.id} added to queue"
    
    def dequeue(self) -> Optional[QueuedJob]:
        """Get the highest priority job from the queue."""
        if not self.queue:
            return None
        
        # Get the highest priority job
        job = heapq.heappop(self.queue)
        
        # Remove from job map
        del self.job_map[job.simulation.id]
        
        # Update stats
        self.stats.update_on_start(job.simulation, job.submit_time)
        
        return job
    
    def peek(self) -> Optional[QueuedJob]:
        """Look at the highest priority job without removing it."""
        if not self.queue:
            return None
        
        return self.queue[0]
    
    def remove(self, simulation_id: str) -> bool:
        """Remove a specific simulation from the queue."""
        if simulation_id not in self.job_map:
            return False
        
        job = self.job_map[simulation_id]
        self.queue.remove(job)
        heapq.heapify(self.queue)  # Reestablish heap invariant
        
        del self.job_map[simulation_id]
        
        # Update stats
        self.stats.update_on_cancel(job.simulation)
        
        return True
    
    def update_priority(self, simulation_id: str, new_priority: SimulationPriority) -> bool:
        """Update the priority of a queued simulation."""
        if simulation_id not in self.job_map:
            return False
        
        job = self.job_map[simulation_id]
        old_priority = job.simulation.priority
        
        if old_priority == new_priority:
            return True  # No change needed
        
        # Update priority
        job.update_priority(new_priority)
        
        # Reheapify the queue
        heapq.heapify(self.queue)
        
        return True
    
    def get_position(self, simulation_id: str) -> Optional[int]:
        """Get the position of a simulation in the queue."""
        if simulation_id not in self.job_map:
            return None
        
        job = self.job_map[simulation_id]
        return self.queue.index(job) + 1  # 1-based position
    
    def apply_aging(self) -> None:
        """Apply priority aging to long-waiting jobs."""
        now = datetime.now()
        
        for job in self.queue:
            # Skip jobs that had priority updates recently
            last_update = job.priority_updates[-1][0]
            if now - last_update < self.aging_interval:
                continue
            
            # Skip jobs with highest priority already
            if job.simulation.priority == SimulationPriority.CRITICAL:
                continue
            
            # Calculate aging factor based on wait time
            wait_time = now - job.submit_time
            aging_periods = wait_time / self.aging_interval
            
            # Only apply aging if waited for at least one period
            if aging_periods >= 1:
                # Calculate if priority should be boosted
                priority_values = [p.value for p in SimulationPriority]
                current_value = job.simulation.priority.value
                
                # Lower index means higher priority in our enum
                current_index = priority_values.index(current_value)
                
                # Potentially move to next higher priority
                if current_index > 0:  # Not already at highest
                    # Probability of promotion increases with wait time
                    promotion_probability = min(1.0, self.priority_aging_factor * aging_periods)
                    
                    # Simple deterministic approach for this implementation
                    if promotion_probability >= 0.5:
                        new_priority = SimulationPriority(priority_values[current_index - 1])
                        self.update_priority(job.simulation.id, new_priority)
                        logger.info(
                            f"Priority aged for long-waiting job {job.simulation.id}: "
                            f"{job.simulation.priority.value} -> {new_priority.value}"
                        )
    
    def apply_fairness_adjustments(self) -> None:
        """Apply fairness adjustments to the queue."""
        now = datetime.now()
        
        # Only apply fairness adjustments periodically
        if now - self.last_fairness_adjustment < self.fairness_adjustment_interval:
            return
        
        self.last_fairness_adjustment = now
        
        # Skip if queue is small
        if len(self.queue) < 2:
            return
        
        # Get resource usage by user and project
        user_usage: Dict[str, float] = {}
        project_usage: Dict[str, float] = {}
        
        for job in self.queue:
            user = job.simulation.owner
            project = job.simulation.project
            
            # For now, just count jobs
            user_usage[user] = user_usage.get(user, 0) + 1
            project_usage[project] = project_usage.get(project, 0) + 1
        
        # Calculate fair shares
        total_jobs = len(self.queue)
        
        for job in self.queue:
            user = job.simulation.owner
            project = job.simulation.project
            
            # Skip critical jobs
            if job.simulation.priority == SimulationPriority.CRITICAL:
                continue
            
            user_share = user_usage.get(user, 0) / total_jobs
            project_share = project_usage.get(project, 0) / total_jobs
            
            user_weight = self.user_fairness_weights.get(user, 1.0)
            project_weight = self.project_fairness_weights.get(project, 1.0)
            
            # If user or project is using more than their fair share, lower priority
            fair_share_threshold = 0.5  # Arbitrary threshold
            
            if (user_share > fair_share_threshold / user_weight or
                project_share > fair_share_threshold / project_weight):
                
                # Only lower priority if not already at lowest
                if job.simulation.priority != SimulationPriority.BACKGROUND:
                    # Find the next lower priority
                    priority_values = [p.value for p in SimulationPriority]
                    current_value = job.simulation.priority.value
                    current_index = priority_values.index(current_value)
                    
                    if current_index < len(priority_values) - 1:
                        new_priority = SimulationPriority(priority_values[current_index + 1])
                        self.update_priority(job.simulation.id, new_priority)
                        logger.info(
                            f"Priority lowered for fairness: {job.simulation.id} "
                            f"({job.simulation.priority.value} -> {new_priority.value})"
                        )
        
        # Reheapify the queue after all adjustments
        heapq.heapify(self.queue)
    
    def get_stats(self) -> QueueStats:
        """Get current queue statistics."""
        return self.stats
    
    def get_wait_time_estimate(self, simulation: Simulation) -> timedelta:
        """Estimate wait time for a new simulation."""
        # This is a placeholder for a more sophisticated estimation algorithm
        # In a real system, this would consider:
        # - Current queue length and composition
        # - Historic throughput
        # - Simulation priority and resource requirements
        # - Scheduled maintenance
        
        base_wait_time = timedelta(minutes=30)
        
        # Adjust based on priority
        priority_factor = {
            SimulationPriority.CRITICAL: 0.2,
            SimulationPriority.HIGH: 0.5,
            SimulationPriority.MEDIUM: 1.0,
            SimulationPriority.LOW: 2.0,
            SimulationPriority.BACKGROUND: 4.0,
        }.get(simulation.priority, 1.0)
        
        # Adjust based on queue length
        queue_factor = max(1.0, len(self.queue) / 10)
        
        return base_wait_time * priority_factor * queue_factor