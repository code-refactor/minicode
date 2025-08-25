"""Queue management for the unified task scheduling library."""

import heapq
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging

from ..core.models import BaseJob, Priority, JobStatus
from ..core.interfaces import QueueManagerInterface
from ..core.result import Result, ErrorCode


logger = logging.getLogger(__name__)


class QueuePolicy(str, Enum):
    """Queue management policies."""
    FIFO = "fifo"  # First in, first out
    PRIORITY = "priority"  # Strict priority ordering  
    FAIR_SHARE = "fair_share"  # Fair resource sharing
    WEIGHTED_FAIR = "weighted_fair"  # Weighted fair queuing
    DEADLINE_DRIVEN = "deadline_driven"  # Deadline-aware scheduling
    MULTI_LEVEL = "multi_level"  # Multi-level feedback queue


class QueueState(str, Enum):
    """Queue states."""
    ACTIVE = "active"  # Queue is actively processing jobs
    PAUSED = "paused"  # Queue is paused
    DRAINING = "draining"  # Queue is draining but not accepting new jobs
    STOPPED = "stopped"  # Queue is stopped


@dataclass
class QueuedJob:
    """A job in the queue with additional scheduling metadata."""
    job: BaseJob
    enqueue_time: datetime = field(default_factory=datetime.now)
    priority_score: float = 0.0
    wait_time: timedelta = field(default_factory=timedelta)
    attempts: int = 0
    last_attempt_time: Optional[datetime] = None
    queue_position: int = -1
    estimated_start_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Calculate initial priority score."""
        self.priority_score = self._calculate_priority_score()
    
    def _calculate_priority_score(self) -> float:
        """Calculate priority score for queue ordering."""
        base_score = {
            Priority.BACKGROUND: 0.1,
            Priority.LOW: 0.3,
            Priority.MEDIUM: 0.5,
            Priority.HIGH: 0.8,
            Priority.CRITICAL: 1.0
        }.get(self.job.priority, 0.5)
        
        # Add aging factor
        current_time = datetime.now()
        wait_hours = (current_time - self.enqueue_time).total_seconds() / 3600
        aging_boost = min(wait_hours / 24, 0.3)  # Max 0.3 boost for 24+ hours wait
        
        return base_score + aging_boost
    
    def update_priority_score(self):
        """Update the priority score."""
        self.priority_score = self._calculate_priority_score()
    
    def __lt__(self, other):
        """Compare for priority queue ordering (higher score = higher priority)."""
        if self.priority_score != other.priority_score:
            return self.priority_score > other.priority_score  # Higher score first
        return self.enqueue_time < other.enqueue_time  # Older jobs first for same priority


@dataclass 
class QueueStats:
    """Statistics for a job queue."""
    total_enqueued: int = 0
    total_dequeued: int = 0
    current_size: int = 0
    peak_size: int = 0
    avg_wait_time: timedelta = field(default_factory=timedelta)
    max_wait_time: timedelta = field(default_factory=timedelta)
    jobs_by_priority: Dict[Priority, int] = field(default_factory=lambda: defaultdict(int))
    jobs_by_status: Dict[JobStatus, int] = field(default_factory=lambda: defaultdict(int))
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_on_enqueue(self, job: BaseJob):
        """Update stats when a job is enqueued."""
        self.total_enqueued += 1
        self.current_size += 1
        self.peak_size = max(self.peak_size, self.current_size)
        self.jobs_by_priority[job.priority] += 1
        self.jobs_by_status[job.status] += 1
        self.last_updated = datetime.now()
    
    def update_on_dequeue(self, queued_job: QueuedJob):
        """Update stats when a job is dequeued."""
        self.total_dequeued += 1
        self.current_size -= 1
        
        # Update wait time statistics
        wait_time = datetime.now() - queued_job.enqueue_time
        self.max_wait_time = max(self.max_wait_time, wait_time)
        
        # Update average wait time
        if self.total_dequeued > 0:
            total_wait = self.avg_wait_time * (self.total_dequeued - 1) + wait_time
            self.avg_wait_time = total_wait / self.total_dequeued
        
        self.last_updated = datetime.now()


class BaseQueueManager(QueueManagerInterface):
    """Base implementation of queue management."""
    
    def __init__(self, policy: QueuePolicy = QueuePolicy.PRIORITY, 
                 max_size: Optional[int] = None):
        """
        Initialize the queue manager.
        
        Args:
            policy: Queuing policy to use
            max_size: Maximum queue size (None for unlimited)
        """
        self.policy = policy
        self.max_size = max_size
        self.state = QueueState.ACTIVE
        self.queue: List[QueuedJob] = []
        self.job_map: Dict[str, QueuedJob] = {}
        self.stats = QueueStats()
        self.priority_weights: Dict[Priority, float] = {
            Priority.CRITICAL: 1.0,
            Priority.HIGH: 0.8,
            Priority.MEDIUM: 0.6,
            Priority.LOW: 0.4,
            Priority.BACKGROUND: 0.2
        }
        self.user_weights: Dict[str, float] = {}  # For fair sharing
        self.last_rebalance: datetime = datetime.now()
        self.rebalance_interval = timedelta(minutes=30)
        
        logger.info(f"QueueManager initialized with {policy.value} policy")
    
    def enqueue(self, job: BaseJob) -> Result[None]:
        """Add a job to the queue."""
        if self.state == QueueState.STOPPED:
            return Result.err("Queue is stopped", ErrorCode.INVALID_STATE)
        
        if self.state == QueueState.DRAINING:
            return Result.err("Queue is draining and not accepting new jobs", ErrorCode.INVALID_STATE)
        
        if job.id in self.job_map:
            return Result.err(f"Job {job.id} is already in queue", ErrorCode.ALREADY_EXISTS)
        
        if self.max_size and len(self.queue) >= self.max_size:
            return Result.err("Queue is at maximum capacity", ErrorCode.CAPACITY_EXCEEDED)
        
        # Create queued job
        queued_job = QueuedJob(job=job)
        
        # Add to queue based on policy
        if self.policy == QueuePolicy.FIFO:
            self.queue.append(queued_job)
        else:
            heapq.heappush(self.queue, queued_job)
        
        self.job_map[job.id] = queued_job
        self.stats.update_on_enqueue(job)
        
        logger.debug(f"Job {job.id} enqueued with priority {job.priority.value}")
        return Result.ok(None)
    
    def dequeue(self) -> Optional[BaseJob]:
        """Remove and return the next job from the queue."""
        if not self.queue or self.state == QueueState.STOPPED:
            return None
        
        # Get next job based on policy
        if self.policy == QueuePolicy.FIFO:
            queued_job = self.queue.pop(0)
        else:
            queued_job = heapq.heappop(self.queue)
        
        # Remove from job map
        del self.job_map[queued_job.job.id]
        
        # Update stats
        self.stats.update_on_dequeue(queued_job)
        
        # Update job status
        queued_job.job.status = JobStatus.RUNNING
        queued_job.job.start_time = datetime.now()
        
        logger.debug(f"Job {queued_job.job.id} dequeued after {queued_job.wait_time}")
        return queued_job.job
    
    def peek(self) -> Optional[BaseJob]:
        """Look at the next job without removing it."""
        if not self.queue:
            return None
        
        if self.policy == QueuePolicy.FIFO:
            return self.queue[0].job
        else:
            return self.queue[0].job
    
    def remove_job(self, job_id: str) -> Result[BaseJob]:
        """Remove a specific job from the queue."""
        if job_id not in self.job_map:
            return Result.err(f"Job {job_id} not found in queue", ErrorCode.NOT_FOUND)
        
        queued_job = self.job_map[job_id]
        
        # Remove from queue
        try:
            if self.policy == QueuePolicy.FIFO:
                self.queue.remove(queued_job)
            else:
                self.queue.remove(queued_job)
                heapq.heapify(self.queue)  # Restore heap property
        except ValueError:
            return Result.err(f"Job {job_id} not found in queue structure", ErrorCode.NOT_FOUND)
        
        # Remove from job map
        del self.job_map[job_id]
        
        # Update stats
        self.stats.current_size -= 1
        
        logger.debug(f"Job {job_id} removed from queue")
        return Result.ok(queued_job.job)
    
    def reorder(self, priority_function: Callable[[BaseJob], float]) -> None:
        """Reorder queue based on a priority function."""
        if self.policy == QueuePolicy.FIFO:
            logger.warning("Cannot reorder FIFO queue")
            return
        
        # Update priority scores
        for queued_job in self.queue:
            queued_job.priority_score = priority_function(queued_job.job)
        
        # Reheapify
        heapq.heapify(self.queue)
        
        logger.debug("Queue reordered based on new priority function")
    
    def update_job_priority(self, job_id: str, new_priority: Priority) -> Result[None]:
        """Update the priority of a queued job."""
        if job_id not in self.job_map:
            return Result.err(f"Job {job_id} not found in queue", ErrorCode.NOT_FOUND)
        
        queued_job = self.job_map[job_id]
        old_priority = queued_job.job.priority
        
        # Update job priority
        queued_job.job.priority = new_priority
        queued_job.update_priority_score()
        
        # Reheapify if not FIFO
        if self.policy != QueuePolicy.FIFO:
            heapq.heapify(self.queue)
        
        logger.info(f"Job {job_id} priority updated: {old_priority.value} -> {new_priority.value}")
        return Result.ok(None)
    
    def get_position(self, job_id: str) -> Optional[int]:
        """Get the position of a job in the queue."""
        if job_id not in self.job_map:
            return None
        
        queued_job = self.job_map[job_id]
        
        try:
            # For priority queues, position depends on sorting
            if self.policy == QueuePolicy.FIFO:
                return self.queue.index(queued_job) + 1
            else:
                # Sort queue by priority for position calculation
                sorted_queue = sorted(self.queue, reverse=True)  # Higher priority first
                return sorted_queue.index(queued_job) + 1
        except ValueError:
            return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        current_time = datetime.now()
        
        stats_dict = {
            "total_enqueued": self.stats.total_enqueued,
            "total_dequeued": self.stats.total_dequeued,
            "current_size": len(self.queue),
            "peak_size": self.stats.peak_size,
            "avg_wait_time_seconds": self.stats.avg_wait_time.total_seconds(),
            "max_wait_time_seconds": self.stats.max_wait_time.total_seconds(),
            "queue_state": self.state.value,
            "policy": self.policy.value
        }
        
        # Add priority distribution
        priority_dist = defaultdict(int)
        for queued_job in self.queue:
            priority_dist[queued_job.job.priority.value] += 1
        stats_dict["priority_distribution"] = dict(priority_dist)
        
        # Add wait time distribution
        wait_times = []
        for queued_job in self.queue:
            wait_time = current_time - queued_job.enqueue_time
            wait_times.append(wait_time.total_seconds())
        
        if wait_times:
            stats_dict["current_avg_wait_seconds"] = sum(wait_times) / len(wait_times)
            stats_dict["current_max_wait_seconds"] = max(wait_times)
        else:
            stats_dict["current_avg_wait_seconds"] = 0
            stats_dict["current_max_wait_seconds"] = 0
        
        return stats_dict
    
    def set_state(self, new_state: QueueState) -> Result[None]:
        """Change the queue state."""
        if new_state == self.state:
            return Result.ok(None)
        
        old_state = self.state
        self.state = new_state
        
        logger.info(f"Queue state changed: {old_state.value} -> {new_state.value}")
        return Result.ok(None)
    
    def drain(self) -> Result[None]:
        """Put queue in draining mode (no new jobs, process existing)."""
        return self.set_state(QueueState.DRAINING)
    
    def pause(self) -> Result[None]:
        """Pause the queue."""
        return self.set_state(QueueState.PAUSED)
    
    def resume(self) -> Result[None]:
        """Resume the queue."""
        return self.set_state(QueueState.ACTIVE)
    
    def clear(self) -> Result[int]:
        """Clear all jobs from the queue."""
        if self.state == QueueState.ACTIVE:
            return Result.err("Cannot clear active queue", ErrorCode.INVALID_STATE)
        
        count = len(self.queue)
        self.queue.clear()
        self.job_map.clear()
        self.stats.current_size = 0
        
        logger.info(f"Queue cleared, removed {count} jobs")
        return Result.ok(count)
    
    def rebalance_queue(self) -> None:
        """Rebalance the queue based on current policy."""
        current_time = datetime.now()
        
        if current_time - self.last_rebalance < self.rebalance_interval:
            return
        
        # Update priority scores for all jobs (aging)
        for queued_job in self.queue:
            queued_job.update_priority_score()
        
        # Reheapify if using priority-based ordering
        if self.policy != QueuePolicy.FIFO:
            heapq.heapify(self.queue)
        
        self.last_rebalance = current_time
        logger.debug("Queue rebalanced")
    
    def get_jobs_by_priority(self, priority: Priority) -> List[BaseJob]:
        """Get all jobs with a specific priority."""
        return [qj.job for qj in self.queue if qj.job.priority == priority]
    
    def get_jobs_by_user(self, user: str) -> List[BaseJob]:
        """Get all jobs for a specific user."""
        jobs = []
        for qj in self.queue:
            if hasattr(qj.job, 'owner') and qj.job.owner == user:
                jobs.append(qj.job)
        return jobs
    
    def estimate_wait_time(self, job: BaseJob) -> timedelta:
        """Estimate wait time for a new job."""
        if not self.queue:
            return timedelta(0)
        
        # Simple estimation based on queue position and average processing time
        estimated_position = 1
        
        for queued_job in self.queue:
            if queued_job.priority_score <= job.calculate_priority_score(datetime.now()):
                estimated_position += 1
        
        # Assume average job takes 30 minutes (can be made configurable)
        avg_job_duration = timedelta(minutes=30)
        return avg_job_duration * estimated_position


class FairShareQueueManager(BaseQueueManager):
    """Queue manager with fair share capabilities."""
    
    def __init__(self, max_size: Optional[int] = None):
        super().__init__(QueuePolicy.FAIR_SHARE, max_size)
        self.user_shares: Dict[str, float] = {}  # User -> share allocation
        self.user_usage: Dict[str, float] = {}   # User -> current usage
        
    def set_user_share(self, user: str, share: float) -> None:
        """Set the resource share for a user."""
        self.user_shares[user] = max(0.0, min(1.0, share))
        logger.info(f"User {user} share set to {share:.2%}")
    
    def dequeue(self) -> Optional[BaseJob]:
        """Dequeue with fair share considerations."""
        if not self.queue:
            return None
        
        # Find the user who is most under-allocated
        best_job = None
        best_ratio = float('inf')
        
        for queued_job in self.queue:
            user = getattr(queued_job.job, 'owner', 'default')
            user_share = self.user_shares.get(user, 1.0)
            user_usage = self.user_usage.get(user, 0.0)
            
            # Calculate usage ratio (lower is better for fairness)
            ratio = user_usage / max(user_share, 0.01)
            
            if ratio < best_ratio:
                best_ratio = ratio
                best_job = queued_job
        
        if best_job:
            # Remove from queue
            self.queue.remove(best_job)
            del self.job_map[best_job.job.id]
            
            # Update user usage
            user = getattr(best_job.job, 'owner', 'default')
            self.user_usage[user] = self.user_usage.get(user, 0.0) + 1.0
            
            # Update stats
            self.stats.update_on_dequeue(best_job)
            
            best_job.job.status = JobStatus.RUNNING
            best_job.job.start_time = datetime.now()
            
            return best_job.job
        
        return None