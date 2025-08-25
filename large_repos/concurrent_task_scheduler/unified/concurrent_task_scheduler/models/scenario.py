"""Models for scenario management and prioritization."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from concurrent_task_scheduler.models.simulation import Simulation, Priority as SimulationPriority


class ScenarioStatus(str, Enum):
    """Status of a research scenario."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DEPRECATED = "deprecated"


class ScientificMetric(BaseModel):
    """A scientific metric used to evaluate scenario promise."""

    name: str
    description: Optional[str] = None
    value: float
    unit: Optional[str] = None
    target_value: Optional[float] = None
    weight: float = 1.0  # Importance weighting for this metric
    is_higher_better: bool = True  # True if higher values are better
    confidence: float = 1.0  # Confidence in this metric (0-1)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def normalized_score(self) -> float:
        """Calculate a normalized score (0-1) for this metric."""
        if self.target_value is None:
            return self.value * self.weight if self.is_higher_better else (1 - self.value) * self.weight
        
        # Normalize based on target
        if self.is_higher_better:
            if self.value >= self.target_value:
                return 1.0 * self.weight
            ratio = max(0, min(1, self.value / self.target_value))
            return ratio * self.weight
        else:
            if self.value <= self.target_value:
                return 1.0 * self.weight
            # Lower is better, so invert the ratio
            if self.target_value == 0:
                return 0.0
            ratio = max(0, min(1, self.target_value / self.value))
            return ratio * self.weight


class ResearchObjective(BaseModel):
    """A research objective that scenarios are trying to achieve."""

    id: str
    name: str
    description: str
    importance: float = 1.0  # Scale of 0-5
    target_metrics: Dict[str, float] = Field(default_factory=dict)
    success_criteria: str = "Meet target metrics with at least 95% confidence"
    
    def is_relevant_to_scenario(self, scenario: Scenario) -> bool:
        """Determine if this objective is relevant to the given scenario."""
        # Check if any tags overlap
        return bool(set(scenario.tags).intersection(set(self.target_metrics.keys())))


class Scenario(BaseModel):
    """A research scenario consisting of multiple simulations."""

    id: str
    name: str
    description: str
    simulations: Dict[str, Simulation] = Field(default_factory=dict)
    status: ScenarioStatus = ScenarioStatus.PROPOSED
    scientific_metrics: Dict[str, ScientificMetric] = Field(default_factory=dict)
    priority_score: float = 0.5  # 0-1 scale, dynamically updated
    tags: List[str] = Field(default_factory=list)
    creation_time: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    resource_allocation: Dict[str, float] = Field(default_factory=dict)
    researcher_ids: List[str] = Field(default_factory=list)
    related_scenarios: Set[str] = Field(default_factory=set)
    research_objectives: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def calculate_priority_score(self) -> float:
        """Calculate the overall priority score based on scientific metrics."""
        if not self.scientific_metrics:
            return 0.5  # Default middle priority
        
        total_weight = sum(metric.weight for metric in self.scientific_metrics.values())
        if total_weight == 0:
            return 0.5
        
        weighted_sum = sum(
            metric.normalized_score() * metric.confidence 
            for metric in self.scientific_metrics.values()
        )
        
        # Normalize to 0-1
        score = weighted_sum / total_weight
        return max(0.0, min(1.0, score))
    
    def update_priority(self, new_priority: Optional[float] = None) -> None:
        """
        Update the priority score based on current metrics or a provided value.
        
        Args:
            new_priority: If provided, directly set this as the new priority score.
                          Otherwise, calculate priority from metrics.
        """
        if new_priority is not None:
            self.priority_score = max(0.0, min(1.0, new_priority))  # Ensure between 0 and 1
        else:
            self.priority_score = self.calculate_priority_score()
        
        self.last_updated = datetime.now()
    
    def get_simulation_status_counts(self) -> Dict[str, int]:
        """Count simulations by status."""
        counts = {}
        for sim in self.simulations.values():
            status_str = sim.status.value
            counts[status_str] = counts.get(status_str, 0) + 1
        return counts
    
    def get_derived_priority(self) -> SimulationPriority:
        """Convert numeric priority score to simulation priority level."""
        if self.priority_score >= 0.8:
            return SimulationPriority.CRITICAL
        elif self.priority_score >= 0.6:
            return SimulationPriority.HIGH
        elif self.priority_score >= 0.4:
            return SimulationPriority.MEDIUM
        elif self.priority_score >= 0.2:
            return SimulationPriority.LOW
        else:
            return SimulationPriority.BACKGROUND
    
    def total_progress(self) -> float:
        """Calculate total progress across all simulations."""
        if not self.simulations:
            return 0.0
        
        return sum(sim.total_progress() for sim in self.simulations.values()) / len(self.simulations)


class ComparisonResult(BaseModel):
    """Result of comparing two scenarios."""

    scenario_id_a: str
    scenario_id_b: str
    metrics_comparison: Dict[str, Dict[str, float]]
    overall_difference: float  # Positive means A is better, negative means B is better
    confidence: float  # Confidence in the comparison (0-1)
    comparison_time: datetime = Field(default_factory=datetime.now)
    recommendation: str  # Human-readable recommendation
    
    def clear_winner(self) -> Optional[str]:
        """Determine if there's a clear winner."""
        if self.overall_difference > 0.2 and self.confidence > 0.7:
            return self.scenario_id_a
        elif self.overall_difference < -0.2 and self.confidence > 0.7:
            return self.scenario_id_b
        return None


class ScenarioEvaluationResult(BaseModel):
    """Result of evaluating a scenario's scientific promise."""

    scenario_id: str
    evaluation_time: datetime = Field(default_factory=datetime.now)
    overall_score: float  # 0-1 scale
    metric_scores: Dict[str, float]
    confidence: float  # 0-1 scale
    recommendation: str  # Continue, adjust, or deprioritize
    suggested_priority: float  # Suggested new priority score
    reasons: List[str] = Field(default_factory=list)  # Reasons for recommendation
    
    @property
    def scores(self) -> Dict[str, float]:
        """Alias for metric_scores for backward compatibility."""
        return self.metric_scores
    
    def should_adjust_priority(self, current_priority: float, threshold: float = 0.1) -> bool:
        """Determine if priority should be adjusted based on evaluation."""
        return abs(self.suggested_priority - current_priority) > threshold


class ResourceAllocation(BaseModel):
    """Resource allocation among different scenarios."""

    allocation_id: str
    allocation_time: datetime = Field(default_factory=datetime.now)
    scenario_allocations: Dict[str, float]  # Scenario ID to allocation percentage
    total_resources: Dict[str, float]  # Resource type to total amount
    allocation_reason: Dict[str, str] = Field(default_factory=dict)  # Scenario ID to reason
    minimum_allocations: Dict[str, float] = Field(default_factory=dict)  # Minimum guaranteed allocations
    expiration_time: Optional[datetime] = None  # When this allocation expires
    
    def get_absolute_allocation(self, resource_type: str, scenario_id: str) -> float:
        """Calculate the absolute allocation for a scenario and resource type."""
        if resource_type not in self.total_resources or scenario_id not in self.scenario_allocations:
            return 0.0
        
        percentage = self.scenario_allocations.get(scenario_id, 0.0)
        total = self.total_resources.get(resource_type, 0.0)
        
        return percentage * total
    
    def is_valid(self) -> bool:
        """Check if this allocation is valid (sums to 100% or less)."""
        total_percentage = sum(self.scenario_allocations.values())
        return 0.0 <= total_percentage <= 1.0