"""Priority management for the unified task scheduling library."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
import logging

from ..core.models import BaseJob, Priority, JobStatus
from ..core.result import Result, ErrorCode


logger = logging.getLogger(__name__)


class PriorityChangeReason(str, Enum):
    """Reasons for priority changes."""
    AGING = "aging"  # Job has been waiting too long
    DEADLINE_APPROACH = "deadline_approach"  # Job deadline is approaching
    RESOURCE_AVAILABILITY = "resource_availability"  # Resources became available
    DEPENDENCY_SATISFIED = "dependency_satisfied"  # Dependencies were satisfied  
    MANUAL_OVERRIDE = "manual_override"  # Manual priority adjustment
    FAIRNESS_ADJUSTMENT = "fairness_adjustment"  # Fairness-based adjustment
    SYSTEM_LOAD = "system_load"  # Adjustment based on system load
    STARVATION_PREVENTION = "starvation_prevention"  # Prevent job starvation


class PriorityAdjustmentPolicy(str, Enum):
    """Policies for priority adjustments."""
    CONSERVATIVE = "conservative"  # Small, gradual adjustments
    AGGRESSIVE = "aggressive"  # Larger, faster adjustments
    BALANCED = "balanced"  # Balance between conservative and aggressive
    ADAPTIVE = "adaptive"  # Adjust policy based on system state


@dataclass
class PriorityChangeRecord:
    """Record of a priority change for auditing."""
    job_id: str
    old_priority: Priority
    new_priority: Priority
    reason: PriorityChangeReason
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return (f"PriorityChange({self.job_id}: {self.old_priority.value} -> "
                f"{self.new_priority.value}, reason={self.reason.value})")


@dataclass
class PriorityConfig:
    """Configuration for priority management."""
    aging_enabled: bool = True
    aging_interval: timedelta = timedelta(hours=6)
    aging_factor: float = 0.1
    max_aging_boost: int = 2  # Max priority levels to boost
    starvation_threshold: timedelta = timedelta(days=2)
    deadline_priority_boost_threshold: timedelta = timedelta(hours=12)
    fairness_enabled: bool = True
    fairness_window: timedelta = timedelta(hours=24)
    max_priority_changes_per_job: int = 10
    adjustment_policy: PriorityAdjustmentPolicy = PriorityAdjustmentPolicy.BALANCED


class PriorityManager:
    """
    Manages dynamic priority adjustments for jobs in the scheduling system.
    
    This class handles:
    - Priority aging for long-waiting jobs
    - Deadline-driven priority boosts
    - Fairness-based priority adjustments
    - Manual priority overrides
    - Starvation prevention
    """
    
    def __init__(self, config: Optional[PriorityConfig] = None):
        """
        Initialize the priority manager.
        
        Args:
            config: Configuration for priority management behavior
        """
        self.config = config or PriorityConfig()
        self.change_history: List[PriorityChangeRecord] = []
        self.last_aging_check: Dict[str, datetime] = {}
        self.job_change_counts: Dict[str, int] = {}
        self.user_job_history: Dict[str, List[Tuple[datetime, str]]] = {}
        
        # Priority level ordering (for aging calculations)
        self.priority_levels = [
            Priority.BACKGROUND,
            Priority.LOW, 
            Priority.MEDIUM,
            Priority.HIGH,
            Priority.CRITICAL
        ]
        
        logger.info(f"PriorityManager initialized with policy: {self.config.adjustment_policy}")
    
    def calculate_dynamic_priority(self, job: BaseJob, current_time: Optional[datetime] = None) -> Priority:
        """
        Calculate the dynamic priority for a job based on various factors.
        
        Args:
            job: Job to calculate priority for
            current_time: Current timestamp (defaults to now)
            
        Returns:
            Suggested priority for the job
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Start with base priority
        suggested_priority = job.priority
        
        # Apply aging if enabled
        if self.config.aging_enabled and self.should_apply_aging(job, current_time):
            suggested_priority = self._apply_aging_boost(job, suggested_priority, current_time)
        
        # Check for deadline pressure
        if hasattr(job, 'deadline') and job.deadline:
            suggested_priority = self._apply_deadline_boost(job, suggested_priority, current_time)
        
        # Check for starvation prevention
        wait_time = current_time - job.submission_time
        if wait_time > self.config.starvation_threshold:
            suggested_priority = self._apply_starvation_prevention(job, suggested_priority)
        
        return suggested_priority
    
    def update_job_priority(self, job: BaseJob, reason: Optional[PriorityChangeReason] = None, 
                          details: Optional[Dict[str, Any]] = None,
                          current_time: Optional[datetime] = None) -> Optional[PriorityChangeRecord]:
        """
        Update a job's priority if needed.
        
        Args:
            job: Job to update
            reason: Reason for the update (auto-detected if None)
            details: Additional details about the change
            current_time: Current timestamp
            
        Returns:
            PriorityChangeRecord if priority was changed, None otherwise
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Check if job has hit maximum changes
        change_count = self.job_change_counts.get(job.id, 0)
        if change_count >= self.config.max_priority_changes_per_job:
            logger.debug(f"Job {job.id} has reached maximum priority changes ({change_count})")
            return None
        
        # Calculate suggested priority
        old_priority = job.priority
        suggested_priority = self.calculate_dynamic_priority(job, current_time)
        
        # No change needed
        if suggested_priority == old_priority:
            return None
        
        # Update the job priority
        job.priority = suggested_priority
        
        # Determine reason if not provided
        if reason is None:
            reason = self._determine_change_reason(job, old_priority, suggested_priority, current_time)
        
        # Create change record
        change_record = PriorityChangeRecord(
            job_id=job.id,
            old_priority=old_priority,
            new_priority=suggested_priority,
            reason=reason,
            timestamp=current_time,
            details=details or {}
        )
        
        # Record the change
        self.change_history.append(change_record)
        self.job_change_counts[job.id] = change_count + 1
        self.last_aging_check[job.id] = current_time
        
        logger.info(f"Priority updated: {change_record}")
        return change_record
    
    def manual_priority_override(self, job: BaseJob, new_priority: Priority,
                               reason_note: Optional[str] = None) -> PriorityChangeRecord:
        """
        Manually override a job's priority.
        
        Args:
            job: Job to update
            new_priority: New priority to set
            reason_note: Optional note explaining the override
            
        Returns:
            Record of the priority change
        """
        old_priority = job.priority
        job.priority = new_priority
        
        details = {"note": reason_note} if reason_note else {}
        
        change_record = PriorityChangeRecord(
            job_id=job.id,
            old_priority=old_priority,
            new_priority=new_priority,
            reason=PriorityChangeReason.MANUAL_OVERRIDE,
            details=details
        )
        
        self.change_history.append(change_record)
        self.job_change_counts[job.id] = self.job_change_counts.get(job.id, 0) + 1
        
        logger.info(f"Manual priority override: {change_record}")
        return change_record
    
    def apply_fairness_adjustments(self, jobs: List[BaseJob], 
                                 current_time: Optional[datetime] = None) -> List[PriorityChangeRecord]:
        """
        Apply fairness-based priority adjustments across multiple jobs.
        
        Args:
            jobs: List of jobs to adjust
            current_time: Current timestamp
            
        Returns:
            List of priority change records
        """
        if not self.config.fairness_enabled or len(jobs) < 2:
            return []
        
        if current_time is None:
            current_time = datetime.now()
        
        changes = []
        
        # Group jobs by user
        user_jobs: Dict[str, List[BaseJob]] = {}
        for job in jobs:
            user = getattr(job, 'owner', 'unknown')
            if user not in user_jobs:
                user_jobs[user] = []
            user_jobs[user].append(job)
        
        # Calculate fairness metrics
        for user, user_job_list in user_jobs.items():
            if len(user_job_list) <= 1:
                continue
            
            # Sort by submission time to find longest waiting
            user_job_list.sort(key=lambda j: j.submission_time)
            
            # Check if user has too many high-priority jobs relative to others
            high_priority_count = sum(1 for j in user_job_list 
                                    if j.priority in [Priority.HIGH, Priority.CRITICAL])
            
            if high_priority_count > len(user_job_list) // 2:  # More than half are high priority
                # Lower priority of some jobs for fairness
                for job in user_job_list[high_priority_count//2:]:
                    if job.priority in [Priority.HIGH, Priority.CRITICAL]:
                        lower_priority = self._get_lower_priority(job.priority)
                        if lower_priority != job.priority:
                            job.priority = lower_priority
                            
                            change_record = PriorityChangeRecord(
                                job_id=job.id,
                                old_priority=job.priority,
                                new_priority=lower_priority,
                                reason=PriorityChangeReason.FAIRNESS_ADJUSTMENT,
                                timestamp=current_time,
                                details={"user": user, "high_priority_count": high_priority_count}
                            )
                            changes.append(change_record)
                            self.change_history.append(change_record)
        
        if changes:
            logger.info(f"Applied {len(changes)} fairness adjustments")
        
        return changes
    
    def should_apply_aging(self, job: BaseJob, current_time: datetime) -> bool:
        """
        Determine if aging should be applied to a job.
        
        Args:
            job: Job to check
            current_time: Current timestamp
            
        Returns:
            True if aging should be applied
        """
        if not self.config.aging_enabled:
            return False
        
        # Don't age completed jobs
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        # Don't age critical priority jobs
        if job.priority == Priority.CRITICAL:
            return False
        
        # Check if enough time has passed since last aging
        last_check = self.last_aging_check.get(job.id)
        if last_check and (current_time - last_check) < self.config.aging_interval:
            return False
        
        # Check if job has been waiting long enough
        wait_time = current_time - job.submission_time
        return wait_time >= self.config.aging_interval
    
    def get_priority_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about priority management.
        
        Returns:
            Dictionary of statistics
        """
        stats = {
            "total_changes": len(self.change_history),
            "changes_by_reason": {},
            "jobs_with_changes": len(self.job_change_counts),
            "avg_changes_per_job": 0,
            "recent_changes": 0
        }
        
        # Count changes by reason
        for record in self.change_history:
            reason = record.reason.value
            stats["changes_by_reason"][reason] = stats["changes_by_reason"].get(reason, 0) + 1
        
        # Calculate averages
        if self.job_change_counts:
            stats["avg_changes_per_job"] = sum(self.job_change_counts.values()) / len(self.job_change_counts)
        
        # Count recent changes (last hour)
        recent_cutoff = datetime.now() - timedelta(hours=1)
        stats["recent_changes"] = sum(1 for record in self.change_history 
                                    if record.timestamp >= recent_cutoff)
        
        return stats
    
    def get_job_priority_history(self, job_id: str) -> List[PriorityChangeRecord]:
        """
        Get priority change history for a specific job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            List of priority change records for the job
        """
        return [record for record in self.change_history if record.job_id == job_id]
    
    def _apply_aging_boost(self, job: BaseJob, current_priority: Priority, current_time: datetime) -> Priority:
        """Apply aging-based priority boost."""
        wait_time = current_time - job.submission_time
        aging_periods = wait_time / self.config.aging_interval
        
        # Calculate boost based on wait time and policy
        if self.config.adjustment_policy == PriorityAdjustmentPolicy.AGGRESSIVE:
            boost_threshold = 1.0
        elif self.config.adjustment_policy == PriorityAdjustmentPolicy.CONSERVATIVE:
            boost_threshold = 3.0
        else:  # BALANCED or ADAPTIVE
            boost_threshold = 2.0
        
        if aging_periods >= boost_threshold:
            current_index = self.priority_levels.index(current_priority)
            boost_levels = min(int(aging_periods / boost_threshold), self.config.max_aging_boost)
            new_index = min(len(self.priority_levels) - 1, current_index + boost_levels)
            return self.priority_levels[new_index]
        
        return current_priority
    
    def _apply_deadline_boost(self, job: BaseJob, current_priority: Priority, current_time: datetime) -> Priority:
        """Apply deadline-based priority boost."""
        if not hasattr(job, 'deadline') or not job.deadline:
            return current_priority
        
        time_to_deadline = job.deadline - current_time
        if time_to_deadline <= self.config.deadline_priority_boost_threshold:
            # Boost priority for jobs approaching deadline
            if current_priority != Priority.CRITICAL:
                current_index = self.priority_levels.index(current_priority)
                return self.priority_levels[min(len(self.priority_levels) - 1, current_index + 1)]
        
        return current_priority
    
    def _apply_starvation_prevention(self, job: BaseJob, current_priority: Priority) -> Priority:
        """Apply starvation prevention boost."""
        if current_priority == Priority.CRITICAL:
            return current_priority
        
        # Boost to high priority to prevent starvation
        return Priority.HIGH
    
    def _determine_change_reason(self, job: BaseJob, old_priority: Priority, 
                                new_priority: Priority, current_time: datetime) -> PriorityChangeReason:
        """Determine the reason for a priority change."""
        wait_time = current_time - job.submission_time
        
        if wait_time > self.config.starvation_threshold:
            return PriorityChangeReason.STARVATION_PREVENTION
        
        if hasattr(job, 'deadline') and job.deadline:
            time_to_deadline = job.deadline - current_time
            if time_to_deadline <= self.config.deadline_priority_boost_threshold:
                return PriorityChangeReason.DEADLINE_APPROACH
        
        if wait_time >= self.config.aging_interval:
            return PriorityChangeReason.AGING
        
        return PriorityChangeReason.SYSTEM_LOAD
    
    def _get_lower_priority(self, priority: Priority) -> Priority:
        """Get the next lower priority level."""
        try:
            current_index = self.priority_levels.index(priority)
            if current_index > 0:
                return self.priority_levels[current_index - 1]
        except ValueError:
            pass
        return priority