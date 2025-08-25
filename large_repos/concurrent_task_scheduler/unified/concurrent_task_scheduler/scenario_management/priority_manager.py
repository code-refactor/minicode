"""
Priority Manager for Scenario Management.

This module provides functionality for dynamic priority adjustment of scenarios
based on their scientific promise, evaluation results, and comparison analysis.
It handles resource reallocation between scenarios and implements an adaptive
prioritization system to maximize research output.
"""

import logging
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from concurrent_task_scheduler.models.scenario import (
    Scenario, 
    ResourceAllocation, 
    ScientificMetric
)
from concurrent_task_scheduler.models.simulation import SimulationPriority
from concurrent_task_scheduler.scenario_management.evaluator import (
    ScenarioEvaluator,
    ScenarioEvaluationResult,
)
from concurrent_task_scheduler.scenario_management.comparator import (
    ScenarioComparator,
    ComparisonResult,
    ComparisonMethod,
)

logger = logging.getLogger(__name__)

class PriorityChangeReason(Enum):
    """Reasons for priority changes."""
    EVALUATION_CHANGED = "evaluation_changed"
    RESOURCE_CONSTRAINT = "resource_constraint"
    MANUAL_OVERRIDE = "manual_override"
    RELATIVE_COMPARISON = "relative_comparison"
    RESEARCH_OBJECTIVE_ALIGNMENT = "research_objective_alignment"
    CONVERGENCE_RATE = "convergence_rate"
    RESOURCE_EFFICIENCY = "resource_efficiency"
    NOVELTY_DISCOVERY = "novelty_discovery"


class PriorityChangeRecord:
    """Record of a priority change for auditing and analysis."""
    
    def __init__(
        self,
        scenario_id: str,
        old_priority: float,
        new_priority: float,
        reason: PriorityChangeReason,
        timestamp: Optional[datetime] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.scenario_id = scenario_id
        self.old_priority = old_priority
        self.new_priority = new_priority
        self.reason = reason
        self.timestamp = timestamp or datetime.now()
        self.details = details or {}
    
    def __repr__(self) -> str:
        return (
            f"PriorityChangeRecord(scenario_id={self.scenario_id}, "
            f"old_priority={self.old_priority:.3f}, "
            f"new_priority={self.new_priority:.3f}, "
            f"reason={self.reason.value}, "
            f"timestamp={self.timestamp.isoformat()})"
        )


class ResourceReallocationStrategy(Enum):
    """Strategies for reallocating resources between scenarios."""
    
    PROPORTIONAL = "proportional"  # Reallocate proportionally to priority differences
    THRESHOLD_BASED = "threshold_based"  # Reallocate when differences exceed thresholds
    GRADUAL = "gradual"  # Make small adjustments over time
    AGGRESSIVE = "aggressive"  # Make larger adjustments quickly
    BALANCED = "balanced"  # Balance between scientific promise and resource efficiency


class PriorityManager:
    """
    Manages dynamic prioritization of scenarios based on scientific promise.
    
    This class is responsible for:
    1. Adjusting scenario priorities based on evaluation results
    2. Reallocating resources between scenarios based on priority
    3. Tracking priority changes over time
    4. Implementing adaptive prioritization strategies
    5. Providing interfaces for manual priority adjustments
    """
    
    def __init__(
        self,
        evaluator: Optional[ScenarioEvaluator] = None,
        comparator: Optional[ScenarioComparator] = None,
        reallocation_strategy: ResourceReallocationStrategy = ResourceReallocationStrategy.BALANCED,
        evaluation_interval: timedelta = timedelta(hours=4),
        min_priority_change_threshold: float = 0.05,
        max_reallocation_per_adjustment: float = 0.2,
    ):
        """
        Initialize the PriorityManager.
        
        Args:
            evaluator: The scenario evaluator to use for priority assessment
            comparator: The scenario comparator to use for relative prioritization
            reallocation_strategy: Strategy for reallocating resources
            evaluation_interval: How often to re-evaluate priorities
            min_priority_change_threshold: Minimum change required to update priority
            max_reallocation_per_adjustment: Maximum resource % to reallocate in one adjustment
        """
        self.evaluator = evaluator or ScenarioEvaluator()
        self.comparator = comparator or ScenarioComparator()
        self.reallocation_strategy = reallocation_strategy
        self.evaluation_interval = evaluation_interval
        self.min_priority_change_threshold = min_priority_change_threshold
        self.max_reallocation_per_adjustment = max_reallocation_per_adjustment
        
        # Track when scenarios were last evaluated
        self.last_evaluation_time: Dict[str, datetime] = {}
        
        # Track priority change history
        self.priority_change_history: List[PriorityChangeRecord] = []
        
        # Track resource allocation changes
        self.resource_allocation_history: Dict[str, List[ResourceAllocation]] = defaultdict(list)
        
        # Track scenarios that need priority recalculation
        self.priority_recalculation_queue: Set[str] = set()
        
        logger.info(
            f"PriorityManager initialized with {reallocation_strategy.value} "
            f"strategy, {evaluation_interval} evaluation interval"
        )
    
    def needs_evaluation(self, scenario: Scenario) -> bool:
        """
        Determine if a scenario needs priority re-evaluation.
        
        Args:
            scenario: The scenario to check
            
        Returns:
            True if the scenario should be re-evaluated, False otherwise
        """
        scenario_id = scenario.id
        
        # If never evaluated or explicitly queued for recalculation
        if (scenario_id not in self.last_evaluation_time or 
            scenario_id in self.priority_recalculation_queue):
            return True
        
        # Check if evaluation interval has passed
        last_eval_time = self.last_evaluation_time.get(scenario_id)
        if not last_eval_time:
            return True
            
        time_since_last_eval = datetime.now() - last_eval_time
        return time_since_last_eval >= self.evaluation_interval
    
    def queue_for_recalculation(self, scenario_id: str) -> None:
        """
        Queue a scenario for priority recalculation.
        
        Args:
            scenario_id: ID of the scenario to recalculate
        """
        self.priority_recalculation_queue.add(scenario_id)
        logger.debug(f"Scenario {scenario_id} queued for priority recalculation")
    
    def evaluate_scenario_priority(
        self, scenario: Scenario
    ) -> Tuple[float, PriorityChangeReason, Dict[str, Any]]:
        """
        Evaluate a scenario to determine its priority.
        
        Args:
            scenario: The scenario to evaluate
            
        Returns:
            Tuple of (suggested_priority, change_reason, details)
        """
        # Use the evaluator to assess scientific promise
        eval_result_obj = self.evaluator.evaluate_scenario(scenario)
        
        # Handle both Result[ScenarioEvaluationResult] and direct ScenarioEvaluationResult
        if hasattr(eval_result_obj, 'value') and eval_result_obj.success:
            eval_result = eval_result_obj.value
        else:
            eval_result = eval_result_obj
        
        # Determine the most significant factor in the evaluation
        change_reason = self._determine_priority_change_reason(scenario, eval_result)
        
        # Prepare detail information
        details = {
            "evaluation_scores": eval_result.metric_scores,
            "evaluation_summary": eval_result.recommendation,
            "scientific_metrics": {
                name: metric.value for name, metric in scenario.scientific_metrics.items()
            },
        }
        
        return eval_result.suggested_priority, change_reason, details
    
    def _determine_priority_change_reason(
        self, scenario: Scenario, eval_result: ScenarioEvaluationResult
    ) -> PriorityChangeReason:
        """
        Determine the primary reason for a priority change based on evaluation.
        
        Args:
            scenario: The scenario being evaluated
            eval_result: The evaluation result
            
        Returns:
            The primary reason for the priority change
        """
        # Find the criterion with the highest impact on the evaluation
        if eval_result.metric_scores:
            max_criterion = max(eval_result.metric_scores.items(), key=lambda x: x[1])
            
            # Map criteria to reasons
            criteria_to_reason = {
                "convergence": PriorityChangeReason.CONVERGENCE_RATE,
                "efficiency": PriorityChangeReason.RESOURCE_EFFICIENCY,
                "novelty": PriorityChangeReason.NOVELTY_DISCOVERY,
                "objectives": PriorityChangeReason.RESEARCH_OBJECTIVE_ALIGNMENT,
            }
            
            # If we can map the criterion to a specific reason, return it
            for criterion_prefix, reason in criteria_to_reason.items():
                if max_criterion[0].lower().startswith(criterion_prefix):
                    return reason
                    
        # Default to evaluation changed if we can't determine a more specific reason
        return PriorityChangeReason.EVALUATION_CHANGED
    
    def update_scenario_priority(
        self, 
        scenario: Scenario,
        force: bool = False,
    ) -> Optional[PriorityChangeRecord]:
        """
        Update a scenario's priority based on evaluation.
        
        Args:
            scenario: The scenario to update
            force: Force update even if below threshold
            
        Returns:
            PriorityChangeRecord if priority was changed, None otherwise
        """
        if not force and not self.needs_evaluation(scenario):
            return None
            
        # Get the old priority for record-keeping
        old_priority = scenario.priority_score
        
        # Evaluate the new priority
        new_priority, change_reason, details = self.evaluate_scenario_priority(scenario)
        
        # Check if the change exceeds our threshold
        priority_change = abs(new_priority - old_priority)
        if not force and priority_change < self.min_priority_change_threshold:
            logger.debug(
                f"Scenario {scenario.id} priority change ({priority_change:.3f}) "
                f"below threshold, not updating"
            )
            
            # Still update the last evaluation time
            self.last_evaluation_time[scenario.id] = datetime.now()
            
            # Remove from recalculation queue if present
            if scenario.id in self.priority_recalculation_queue:
                self.priority_recalculation_queue.remove(scenario.id)
                
            return None
        
        # Update the priority
        scenario.update_priority(new_priority)
        
        # Create and record the change
        change_record = PriorityChangeRecord(
            scenario_id=scenario.id,
            old_priority=old_priority,
            new_priority=new_priority,
            reason=change_reason,
            details=details,
        )
        self.priority_change_history.append(change_record)
        
        # Update last evaluation time
        self.last_evaluation_time[scenario.id] = datetime.now()
        
        # Remove from recalculation queue if present
        if scenario.id in self.priority_recalculation_queue:
            self.priority_recalculation_queue.remove(scenario.id)
        
        logger.info(
            f"Updated scenario {scenario.id} priority from {old_priority:.3f} "
            f"to {new_priority:.3f} due to {change_reason.value}"
        )
        
        return change_record
    
    def compare_and_adjust_priorities(
        self, 
        scenarios: List[Scenario],
        comparison_method: ComparisonMethod = ComparisonMethod.WEIGHTED,
    ) -> List[PriorityChangeRecord]:
        """
        Compare multiple scenarios and adjust their priorities relative to each other.
        
        Args:
            scenarios: List of scenarios to compare and adjust
            comparison_method: Method to use for comparison
            
        Returns:
            List of priority change records resulting from the adjustments
        """
        if len(scenarios) < 2:
            logger.warning("Need at least 2 scenarios to compare, skipping adjustment")
            return []
            
        # First update individual priorities for any stale scenarios
        for scenario in scenarios:
            if self.needs_evaluation(scenario):
                self.update_scenario_priority(scenario)
        
        # Use the comparator to establish relative priorities
        comparison_results = self.comparator.compare_multiple_scenarios(
            scenarios, method=comparison_method
        )
        
        # The comparison results contain a dict of scenario_id -> score
        if not comparison_results.success:
            return []
            
        # Extract the ranked scenarios and scores from the dictionary
        ranked_scenarios = list(comparison_results.value.items())
        
        # No changes needed if we couldn't rank them
        if not ranked_scenarios:
            return []
        
        # Adjust priorities based on the ranking
        changes = []
        for i, (scenario_id, rank_score) in enumerate(ranked_scenarios):
            # Find the scenario object
            scenario = next((s for s in scenarios if s.id == scenario_id), None)
            if not scenario:
                continue
                
            # The rank score from the comparator should be between 0-1
            # We can use it directly as a priority score or apply some transformation
            old_priority = scenario.priority_score
            
            # Check if we need to adjust
            if abs(rank_score - old_priority) >= self.min_priority_change_threshold:
                scenario.update_priority(rank_score)
                
                change_record = PriorityChangeRecord(
                    scenario_id=scenario_id,
                    old_priority=old_priority,
                    new_priority=rank_score,
                    reason=PriorityChangeReason.RELATIVE_COMPARISON,
                    details={
                        "comparison_method": comparison_method.value,
                        "rank": i + 1,
                        "total_scenarios": len(ranked_scenarios),
                        "relative_score": rank_score,
                    }
                )
                
                self.priority_change_history.append(change_record)
                changes.append(change_record)
                
                logger.info(
                    f"Adjusted scenario {scenario_id} priority from {old_priority:.3f} "
                    f"to {rank_score:.3f} based on relative comparison (rank {i+1}/{len(ranked_scenarios)})"
                )
                
                # Update last evaluation time
                self.last_evaluation_time[scenario_id] = datetime.now()
        
        return changes
    
    def reallocate_resources(
        self, 
        scenarios: List[Scenario],
        max_reallocation_factor: Optional[float] = None,
    ) -> Dict[str, Tuple[ResourceAllocation, ResourceAllocation]]:
        """
        Reallocate resources between scenarios based on their priorities.
        
        Args:
            scenarios: List of scenarios to consider for reallocation
            max_reallocation_factor: Maximum fraction of resources to reallocate
                                     (overrides the instance default if provided)
                                     
        Returns:
            Dictionary mapping scenario IDs to tuples of (old_allocation, new_allocation)
        """
        if len(scenarios) < 2:
            logger.warning("Need at least 2 scenarios for resource reallocation")
            return {}
            
        # Use provided factor or instance default
        reallocation_factor = max_reallocation_factor or self.max_reallocation_per_adjustment
        
        # Group scenarios by priority to identify donors and recipients
        scenarios_by_priority = sorted(
            scenarios, 
            key=lambda s: s.priority_score,
            reverse=True  # Highest priority first
        )
        
        # Determine cutoff points for donors and recipients based on strategy
        if self.reallocation_strategy == ResourceReallocationStrategy.THRESHOLD_BASED:
            # Use a threshold approach - scenarios above 0.7 get more, below 0.3 give up
            donors = [s for s in scenarios if s.priority_score < 0.3]
            recipients = [s for s in scenarios if s.priority_score > 0.7]
            
        elif self.reallocation_strategy == ResourceReallocationStrategy.AGGRESSIVE:
            # Aggressive - bottom 30% donate to top 30%
            threshold_idx = max(1, int(len(scenarios) * 0.3))
            donors = scenarios_by_priority[-threshold_idx:]
            recipients = scenarios_by_priority[:threshold_idx]
            
        elif self.reallocation_strategy == ResourceReallocationStrategy.GRADUAL:
            # Gradual - bottom 20% donate to top 20%
            threshold_idx = max(1, int(len(scenarios) * 0.2))
            donors = scenarios_by_priority[-threshold_idx:]
            recipients = scenarios_by_priority[:threshold_idx]
            
        else:
            # Default balanced/proportional approach - bottom half donates to top half
            # with donation proportional to priority difference
            mid_idx = len(scenarios) // 2
            donors = scenarios_by_priority[mid_idx:]
            recipients = scenarios_by_priority[:mid_idx]
        
        # No reallocation if we don't have both donors and recipients
        if not donors or not recipients:
            logger.info("No suitable donors or recipients found for reallocation")
            return {}
            
        # Calculate how much to reallocate from each donor
        total_donor_resources = sum(
            sum(d.resource_allocation.values()) for d in donors
        )
        total_donation = total_donor_resources * reallocation_factor
        
        # Calculate how much each recipient should get based on priorities
        total_recipient_priority = sum(s.priority_score for s in recipients)
        
        # Track allocations for return
        allocation_changes = {}
        
        # Reduce resources for donors
        for donor in donors:
            donor_id = donor.id
            old_allocation = donor.resource_allocation.copy()
            
            # Calculate donor's contribution proportion
            donor_resource_total = sum(donor.resource_allocation.values())
            donor_fraction = donor_resource_total / total_donor_resources
            donor_contribution = total_donation * donor_fraction
            
            # Reduce each resource type proportionally
            reduction_factor = max(0, 1 - (donor_contribution / donor_resource_total))
            
            # Create new allocation with reduced resources
            new_allocation = {
                resource_type: amount * reduction_factor
                for resource_type, amount in donor.resource_allocation.items()
            }
            
            # Update donor's allocation
            donor.resource_allocation = new_allocation
            allocation_changes[donor_id] = (old_allocation, new_allocation)
            
            # Record the change
            # Create a proper ResourceAllocation instance
            resource_alloc = ResourceAllocation(
                allocation_id=f"{donor_id}-{datetime.now().timestamp()}",
                allocation_time=datetime.now(),
                scenario_allocations={donor_id: 1.0},  # Full allocation to this scenario
                total_resources=new_allocation,
                allocation_reason={donor_id: "Priority-based reallocation"}
            )
            self.resource_allocation_history[donor_id].append(resource_alloc)
            
            logger.info(
                f"Reduced resources for scenario {donor_id} by "
                f"{donor_contribution:.2f} units ({(1-reduction_factor)*100:.1f}%)"
            )
        
        # Increase resources for recipients
        for recipient in recipients:
            recipient_id = recipient.id
            old_allocation = recipient.resource_allocation.copy()
            
            # Calculate recipient's share based on priority
            priority_fraction = recipient.priority_score / total_recipient_priority
            recipient_addition = total_donation * priority_fraction
            
            # Distribute the addition proportionally across resource types
            recipient_resource_total = sum(recipient.resource_allocation.values())
            
            # Handle edge case where recipient has no resources yet
            if recipient_resource_total == 0:
                # Distribute evenly across all resource types in the system
                all_resource_types = set()
                for s in scenarios:
                    all_resource_types.update(s.resource_allocation.keys())
                
                if all_resource_types:
                    new_allocation = {
                        resource_type: recipient_addition / len(all_resource_types)
                        for resource_type in all_resource_types
                    }
                else:
                    # Fallback to a default resource type if none exists
                    new_allocation = {"compute_node": recipient_addition}
            else:
                # Increase proportionally for existing resources
                increase_factor = 1 + (recipient_addition / recipient_resource_total)
                new_allocation = {
                    resource_type: amount * increase_factor
                    for resource_type, amount in recipient.resource_allocation.items()
                }
            
            # Update recipient's allocation
            recipient.resource_allocation = new_allocation
            allocation_changes[recipient_id] = (old_allocation, new_allocation)
            
            # Record the change
            # Create a proper ResourceAllocation instance
            resource_alloc = ResourceAllocation(
                allocation_id=f"{recipient_id}-{datetime.now().timestamp()}",
                allocation_time=datetime.now(),
                scenario_allocations={recipient_id: 1.0},  # Full allocation to this scenario
                total_resources=new_allocation,
                allocation_reason={recipient_id: "Priority-based reallocation"}
            )
            self.resource_allocation_history[recipient_id].append(resource_alloc)
            
            logger.info(
                f"Increased resources for scenario {recipient_id} by "
                f"{recipient_addition:.2f} units"
            )
        
        return allocation_changes
    
    def manual_priority_override(
        self, 
        scenario: Scenario, 
        new_priority: float,
        reason_note: Optional[str] = None,
    ) -> PriorityChangeRecord:
        """
        Manual override of a scenario's priority.
        
        Args:
            scenario: The scenario to update
            new_priority: The new priority value (0-1)
            reason_note: Optional note explaining the override
            
        Returns:
            Record of the priority change
        """
        # Validate the new priority
        new_priority = max(0.0, min(1.0, new_priority))
        
        # Save the old priority for record-keeping
        old_priority = scenario.priority_score
        
        # Update the scenario
        scenario.update_priority(new_priority)
        
        # Create a change record
        details = {"reason_note": reason_note} if reason_note else {}
        change_record = PriorityChangeRecord(
            scenario_id=scenario.id,
            old_priority=old_priority,
            new_priority=new_priority,
            reason=PriorityChangeReason.MANUAL_OVERRIDE,
            details=details,
        )
        
        # Record the change
        self.priority_change_history.append(change_record)
        
        # Update last evaluation time
        self.last_evaluation_time[scenario.id] = datetime.now()
        
        logger.info(
            f"Manual priority override for scenario {scenario.id}: "
            f"{old_priority:.3f} -> {new_priority:.3f}"
        )
        
        return change_record
    
    def recompute_all_priorities(
        self, 
        scenarios: List[Scenario]
    ) -> List[PriorityChangeRecord]:
        """
        Recompute priorities for all scenarios.
        
        Args:
            scenarios: List of all scenarios to update
            
        Returns:
            List of priority change records
        """
        changes = []
        
        # First update individual priorities
        for scenario in scenarios:
            change = self.update_scenario_priority(scenario, force=True)
            if change:
                changes.append(change)
        
        # Then perform relative comparison adjustment
        if len(scenarios) >= 2:
            comparison_changes = self.compare_and_adjust_priorities(scenarios)
            changes.extend(comparison_changes)
        
        return changes
    
    def get_priority_changes(
        self,
        scenario_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[PriorityChangeRecord]:
        """
        Get priority change history for analysis.
        
        Args:
            scenario_id: Optional ID to filter changes for a specific scenario
            since: Optional timestamp to get only recent changes
            limit: Maximum number of records to return
            
        Returns:
            List of priority change records matching the criteria
        """
        filtered_changes = self.priority_change_history
        
        # Filter by scenario if specified
        if scenario_id:
            filtered_changes = [c for c in filtered_changes if c.scenario_id == scenario_id]
            
        # Filter by date if specified
        if since:
            filtered_changes = [c for c in filtered_changes if c.timestamp >= since]
            
        # Sort by timestamp (most recent first) and limit
        return sorted(filtered_changes, key=lambda c: c.timestamp, reverse=True)[:limit]
    
    def get_priority_trend(
        self, 
        scenario_id: str,
        days: int = 7
    ) -> List[Tuple[datetime, float]]:
        """
        Get the priority trend for a scenario over time.
        
        Args:
            scenario_id: ID of the scenario to analyze
            days: Number of days to look back
            
        Returns:
            List of (timestamp, priority) tuples
        """
        # Filter changes for this scenario
        since_date = datetime.now() - timedelta(days=days)
        changes = self.get_priority_changes(
            scenario_id=scenario_id,
            since=since_date,
            limit=1000,  # Higher limit for trend analysis
        )
        
        # Build the trend list with timestamp and priority value
        trend = [(c.timestamp, c.new_priority) for c in changes]
        
        # Sort by timestamp (oldest first)
        return sorted(trend, key=lambda x: x[0])
    
    def get_resource_allocation_history(
        self,
        scenario_id: str,
        limit: int = 10
    ) -> List[ResourceAllocation]:
        """
        Get the resource allocation history for a scenario.
        
        Args:
            scenario_id: ID of the scenario
            limit: Maximum number of records to return
            
        Returns:
            List of resource allocations, most recent first
        """
        history = self.resource_allocation_history.get(scenario_id, [])
        
        # Return the most recent records, limited by the limit parameter
        return history[-limit:]