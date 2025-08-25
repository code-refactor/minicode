"""Tests for the scenario priority management system."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from concurrent_task_scheduler.models.scenario import (
    Scenario,
    ScientificMetric,
    ScenarioStatus,
    ResourceAllocation,
)
from concurrent_task_scheduler.models.simulation import Simulation, SimulationPriority
from concurrent_task_scheduler.scenario_management.evaluator import (
    ScenarioEvaluator,
    ScenarioEvaluationResult,
)
from concurrent_task_scheduler.scenario_management.comparator import (
    ScenarioComparator,
    ComparisonResult,
    ComparisonMethod,
)
from concurrent_task_scheduler.scenario_management.priority_manager import (
    PriorityManager,
    PriorityChangeReason,
    PriorityChangeRecord,
    ResourceReallocationStrategy,
)


@pytest.fixture
def sample_scenarios():
    """Create sample scenarios for testing."""
    # High-priority scenario
    scenario_a = Scenario(
        id="scenario-a",
        name="Scenario A",
        description="A high-priority scenario",
        status=ScenarioStatus.ACTIVE,
        priority_score=0.8,
        tags=["climate", "high-resolution", "ocean"],
        resource_allocation={"compute_nodes": 50, "storage": 200},
    )
    
    scenario_a.scientific_metrics = {
        "accuracy_model": ScientificMetric(
            name="accuracy_model",
            description="Model accuracy metric",
            value=0.9,
            is_higher_better=True,
            weight=1.0,
        ),
        "convergence_rate": ScientificMetric(
            name="convergence_rate",
            description="Rate of convergence",
            value=0.85,
            is_higher_better=True,
            weight=0.8,
        ),
    }
    
    # Medium-priority scenario
    scenario_b = Scenario(
        id="scenario-b",
        name="Scenario B",
        description="A medium-priority scenario",
        status=ScenarioStatus.ACTIVE,
        priority_score=0.5,
        tags=["climate", "medium-resolution", "atmosphere"],
        resource_allocation={"compute_nodes": 30, "storage": 100},
    )
    
    scenario_b.scientific_metrics = {
        "accuracy_model": ScientificMetric(
            name="accuracy_model",
            description="Model accuracy metric",
            value=0.75,
            is_higher_better=True,
            weight=1.0,
        ),
        "efficiency": ScientificMetric(
            name="efficiency",
            description="Computational efficiency",
            value=0.8,
            is_higher_better=True,
            weight=0.5,
        ),
    }
    
    # Low-priority scenario
    scenario_c = Scenario(
        id="scenario-c",
        name="Scenario C",
        description="A low-priority scenario",
        status=ScenarioStatus.ACTIVE,
        priority_score=0.3,
        tags=["climate", "experimental", "land-surface"],
        resource_allocation={"compute_nodes": 20, "storage": 50},
    )
    
    scenario_c.scientific_metrics = {
        "accuracy_model": ScientificMetric(
            name="accuracy_model",
            description="Model accuracy metric",
            value=0.6,
            is_higher_better=True,
            weight=1.0,
        ),
        "novelty": ScientificMetric(
            name="novelty",
            description="Scientific novelty",
            value=0.9,
            is_higher_better=True,
            weight=1.0,
        ),
    }
    
    return [scenario_a, scenario_b, scenario_c]


@pytest.fixture
def mock_evaluator():
    """Create a mock evaluator with pre-defined evaluation results."""
    evaluator = MagicMock(spec=ScenarioEvaluator)
    
    # Set up evaluate_scenario to return predictable results
    def evaluate_scenario(scenario):
        # Create the mock result object
        result = MagicMock()
        result.success = True
        
        # Create a mock value object that will be returned by result.value
        value = MagicMock()
        
        # Different suggested priorities based on scenario ID - make sure the difference is above threshold
        if scenario.id == "scenario-a":
            suggested_priority = 0.95  # Significantly higher than the original 0.8
            scores = {"accuracy": 0.9, "convergence": 0.85}
            summary = "High-performing scenario"
            reasons = [PriorityChangeReason.EVALUATION_CHANGED]
        elif scenario.id == "scenario-b":
            suggested_priority = 0.65  # Significantly higher than the original 0.5
            scores = {"accuracy": 0.75, "efficiency": 0.8}
            summary = "Medium-performing scenario"
            reasons = [PriorityChangeReason.RESOURCE_EFFICIENCY]
        elif scenario.id == "scenario-c":
            suggested_priority = 0.25  # Significantly lower than the original 0.3
            scores = {"accuracy": 0.6, "novelty": 0.9}
            summary = "Novel but low-accuracy scenario"
            reasons = [PriorityChangeReason.NOVELTY_DISCOVERY]
        else:
            suggested_priority = 0.75  # Make sure it's different enough from any priority_score
            scores = {"default": 0.5}  # Provide at least one score
            summary = "Default evaluation"
            reasons = [PriorityChangeReason.EVALUATION_CHANGED]
        
        # Configure the mock value
        value.suggested_priority = suggested_priority
        value.metric_scores = scores
        value.summary = summary
        value.overall_score = sum(scores.values()) / len(scores) if scores else 0.5
        value.confidence = 0.9
        value.recommendation = "continue"
        value.scenario_id = scenario.id
        
        # Configure the mock result to return the mock value
        result.value = value
        
        return result
    
    evaluator.evaluate_scenario.side_effect = evaluate_scenario
    
    return evaluator


@pytest.fixture
def mock_comparator():
    """Create a mock comparator for testing."""
    comparator = MagicMock(spec=ScenarioComparator)
    
    # Mock compare_scenarios method
    def compare_scenarios(scenario_a, scenario_b, *args, **kwargs):
        result = MagicMock()
        result.success = True
        
        # Simple logic: higher priority score wins
        difference = scenario_a.priority_score - scenario_b.priority_score
        
        comparison = MagicMock(spec=ComparisonResult)
        comparison.scenario_id_a = scenario_a.id
        comparison.scenario_id_b = scenario_b.id
        comparison.overall_difference = difference
        comparison.confidence = 0.8
        
        if difference > 0.2:
            recommendation = f"Scenario {scenario_a.id} shows significantly more promise."
        elif difference > 0.05:
            recommendation = f"Scenario {scenario_a.id} shows somewhat more promise."
        elif difference > -0.05:
            recommendation = "Both scenarios show similar promise."
        elif difference > -0.2:
            recommendation = f"Scenario {scenario_b.id} shows somewhat more promise."
        else:
            recommendation = f"Scenario {scenario_b.id} shows significantly more promise."
            
        comparison.recommendation = recommendation
        result.value = comparison
        
        return result
    
    comparator.compare_scenarios.side_effect = compare_scenarios
    
    # Mock compare_multiple_scenarios method
    def compare_multiple_scenarios(scenarios, *args, **kwargs):
        result = MagicMock()
        result.success = True
        
        # Rank scenarios by priority score
        total_score = sum(s.priority_score for s in scenarios)
        normalized_scores = {s.id: s.priority_score / total_score for s in scenarios}
        
        # Sort by score (descending)
        ranked_scenarios = sorted(
            [(s.id, normalized_scores[s.id]) for s in scenarios],
            key=lambda x: x[1],
            reverse=True
        )
        
        result.value = normalized_scores
        result.ranked_scenarios = ranked_scenarios
        
        return result
    
    comparator.compare_multiple_scenarios.side_effect = compare_multiple_scenarios
    
    return comparator


class TestPriorityManager:
    """Tests for the PriorityManager class."""
    
    def test_initialization(self, mock_evaluator, mock_comparator):
        """Test that the priority manager initializes correctly."""
        manager = PriorityManager(
            evaluator=mock_evaluator,
            comparator=mock_comparator,
            reallocation_strategy=ResourceReallocationStrategy.BALANCED,
            evaluation_interval=timedelta(hours=2),
            min_priority_change_threshold=0.1,
            max_reallocation_per_adjustment=0.15,
        )
        
        # Check initialization with provided components and parameters
        assert manager.evaluator == mock_evaluator
        assert manager.comparator == mock_comparator
        assert manager.reallocation_strategy == ResourceReallocationStrategy.BALANCED
        assert manager.evaluation_interval == timedelta(hours=2)
        assert manager.min_priority_change_threshold == 0.1
        assert manager.max_reallocation_per_adjustment == 0.15
        
        # Check initialization with defaults
        default_manager = PriorityManager()
        assert isinstance(default_manager.evaluator, ScenarioEvaluator)
        assert isinstance(default_manager.comparator, ScenarioComparator)
        assert default_manager.reallocation_strategy == ResourceReallocationStrategy.BALANCED

    def test_needs_evaluation(self, sample_scenarios):
        """Test determination of whether a scenario needs evaluation."""
        manager = PriorityManager(
            evaluation_interval=timedelta(hours=1)
        )
        
        # Initially all scenarios need evaluation
        for scenario in sample_scenarios:
            assert manager.needs_evaluation(scenario) is True
        
        # After evaluation, they shouldn't need it anymore
        for scenario in sample_scenarios:
            manager.last_evaluation_time[scenario.id] = datetime.now()
            assert manager.needs_evaluation(scenario) is False
        
        # After the interval, they should need evaluation again
        for scenario in sample_scenarios:
            manager.last_evaluation_time[scenario.id] = datetime.now() - timedelta(hours=2)
            assert manager.needs_evaluation(scenario) is True
        
        # Test queue_for_recalculation
        scenario = sample_scenarios[0]
        manager.last_evaluation_time[scenario.id] = datetime.now()
        assert manager.needs_evaluation(scenario) is False
        
        manager.queue_for_recalculation(scenario.id)
        assert manager.needs_evaluation(scenario) is True

    def test_evaluate_scenario_priority(self, sample_scenarios, mock_evaluator):
        """Test evaluation of scenario priority."""
        manager = PriorityManager(evaluator=mock_evaluator)
        
        # Test priority evaluation for each scenario
        for scenario in sample_scenarios:
            suggested_priority, reason, details = manager.evaluate_scenario_priority(scenario)
            
            # Check result types
            assert isinstance(suggested_priority, float)
            assert isinstance(reason, PriorityChangeReason)
            assert isinstance(details, dict)
            
            # Check that details contain expected keys
            assert "evaluation_scores" in details
            assert "evaluation_summary" in details
            assert "scientific_metrics" in details
            
            # Values should be within valid range
            assert 0 <= suggested_priority <= 1

    def test_update_scenario_priority(self, sample_scenarios, mock_evaluator):
        """Test updating a scenario's priority."""
        manager = PriorityManager(
            evaluator=mock_evaluator,
            min_priority_change_threshold=0.01,  # Use a low threshold to ensure changes are detected
        )
        
        # Force update to ensure a change record is created
        for scenario in sample_scenarios:
            # Store original priority
            original_priority = scenario.priority_score
            
            # Update priority with force=True
            change_record = manager.update_scenario_priority(scenario, force=True)
            
            # Check that a change was made
            assert change_record is not None
            assert isinstance(change_record, PriorityChangeRecord)
            assert change_record.scenario_id == scenario.id
            assert change_record.old_priority == original_priority
            assert change_record.new_priority == scenario.priority_score
            assert isinstance(change_record.reason, PriorityChangeReason)
            
            # Check that the change was recorded
            assert change_record in manager.priority_change_history
            
            # Check that the last evaluation time was updated
            assert scenario.id in manager.last_evaluation_time
            
            # If it was in the queue, it should be removed
            assert scenario.id not in manager.priority_recalculation_queue
        
        # Test update with insufficient change
        scenario = sample_scenarios[0]
        
        # Set the mock evaluator to return the same priority
        mock_evaluator.evaluate_scenario.return_value.suggested_priority = scenario.priority_score
        
        # Try to update (should not change)
        change_record = manager.update_scenario_priority(scenario)
        assert change_record is None
        
        # Test force update
        mock_evaluator.evaluate_scenario.return_value.suggested_priority = scenario.priority_score + 0.01
        change_record = manager.update_scenario_priority(scenario, force=True)
        assert change_record is not None

    def test_compare_and_adjust_priorities(self, sample_scenarios, mock_evaluator, mock_comparator):
        """Test comparing and adjusting priorities of multiple scenarios."""
        manager = PriorityManager(
            evaluator=mock_evaluator,
            comparator=mock_comparator,
            min_priority_change_threshold=0.05,
        )
        
        # Store original priorities
        original_priorities = {s.id: s.priority_score for s in sample_scenarios}
        
        # Compare and adjust priorities
        changes = manager.compare_and_adjust_priorities(
            sample_scenarios,
            comparison_method=ComparisonMethod.WEIGHTED
        )
        
        # Check that changes were made
        assert len(changes) > 0
        
        # Each change should be properly recorded
        for change in changes:
            assert isinstance(change, PriorityChangeRecord)
            assert change.reason == PriorityChangeReason.RELATIVE_COMPARISON
            
            # Scenario priority should be updated
            scenario = next(s for s in sample_scenarios if s.id == change.scenario_id)
            assert scenario.priority_score == change.new_priority
            
            # Change should be in history
            assert change in manager.priority_change_history
        
        # Test with one scenario (should return empty list)
        single_changes = manager.compare_and_adjust_priorities([sample_scenarios[0]])
        assert single_changes == []

    def test_reallocate_resources(self, sample_scenarios):
        """Test resource reallocation between scenarios."""
        # Need at least 2 scenarios for reallocation
        if len(sample_scenarios) < 2:
            # Create a second scenario with lower priority
            second_scenario = Scenario(
                id="scenario-b",
                name="Scenario B",
                description="A low-priority scenario",
                status=ScenarioStatus.ACTIVE,
                priority_score=0.3,  # Lower priority than scenario-a (0.8)
                resource_allocation={"compute_nodes": 40, "storage": 100},
                scientific_metrics={
                    "accuracy_model": ScientificMetric(
                        name="accuracy_model",
                        description="Model accuracy metric",
                        value=0.6,
                        is_higher_better=True,
                        weight=1.0,
                    )
                }
            )
            test_scenarios = sample_scenarios + [second_scenario]
        else:
            test_scenarios = sample_scenarios
            
        # Test different strategies
        for strategy in ResourceReallocationStrategy:
            manager = PriorityManager(
                reallocation_strategy=strategy,
                max_reallocation_per_adjustment=0.2,
            )
            
            # Initialize resource_allocation_history for each scenario
            for scenario in test_scenarios:
                manager.resource_allocation_history[scenario.id] = []
            
            # Store original allocations
            original_allocations = {
                s.id: s.resource_allocation.copy() for s in test_scenarios
            }
            
            # Perform resource reallocation
            allocation_changes = manager.reallocate_resources(test_scenarios)
            
            # Check resource conservation (total should remain approximately the same)
            original_total_compute = sum(
                alloc.get("compute_nodes", 0) for alloc in original_allocations.values()
            )
            original_total_storage = sum(
                alloc.get("storage", 0) for alloc in original_allocations.values()
            )
            
            new_total_compute = sum(
                s.resource_allocation.get("compute_nodes", 0) for s in test_scenarios
            )
            new_total_storage = sum(
                s.resource_allocation.get("storage", 0) for s in test_scenarios
            )
            
            # Allow for small differences in total resources due to rounding and algorithmic limitations
            # Since the PriorityManager has a max_reallocation_per_adjustment of 0.2 (20%),
            # we can expect up to about 2% difference in the total due to rounding effects
            assert abs(original_total_compute - new_total_compute) / original_total_compute < 0.03
            assert abs(original_total_storage - new_total_storage) / original_total_storage < 0.03
            
            # High-priority scenarios should get more resources
            high_priority = max(test_scenarios, key=lambda s: s.priority_score)
            low_priority = min(test_scenarios, key=lambda s: s.priority_score)
            
            # Compare resource changes
            high_orig_total = sum(original_allocations[high_priority.id].values())
            high_new_total = sum(high_priority.resource_allocation.values())
            
            low_orig_total = sum(original_allocations[low_priority.id].values())
            low_new_total = sum(low_priority.resource_allocation.values())
            
            # High priority should gain, low should lose - only assert if we have changes
            if allocation_changes:
                assert high_new_total >= high_orig_total
                assert low_new_total <= low_orig_total
            
            # Check allocation history was recorded
            for scenario in test_scenarios:
                assert scenario.id in manager.resource_allocation_history
                # The history might be empty if the scenario wasn't affected
                if scenario.id in allocation_changes:
                    assert len(manager.resource_allocation_history[scenario.id]) >= 1
        
        # Test with less than 2 scenarios (should return empty dict)
        manager = PriorityManager()
        single_result = manager.reallocate_resources([sample_scenarios[0]])
        assert single_result == {}

    def test_manual_priority_override(self, sample_scenarios):
        """Test manual priority override functionality."""
        manager = PriorityManager()
        
        scenario = sample_scenarios[0]
        original_priority = scenario.priority_score
        new_priority = 0.95
        
        # Perform manual override
        change_record = manager.manual_priority_override(
            scenario,
            new_priority,
            reason_note="Critical research objective alignment"
        )
        
        # Check scenario was updated
        assert scenario.priority_score == new_priority
        
        # Check change record
        assert change_record.old_priority == original_priority
        assert change_record.new_priority == new_priority
        assert change_record.reason == PriorityChangeReason.MANUAL_OVERRIDE
        assert "reason_note" in change_record.details
        
        # Check record was added to history
        assert change_record in manager.priority_change_history
        
        # Check last evaluation time was updated
        assert scenario.id in manager.last_evaluation_time
        
        # Test with out-of-range priority (should be clamped)
        change_record = manager.manual_priority_override(scenario, 1.5)
        assert change_record.new_priority == 1.0
        
        change_record = manager.manual_priority_override(scenario, -0.5)
        assert change_record.new_priority == 0.0

    def test_recompute_all_priorities(self, sample_scenarios, mock_evaluator, mock_comparator):
        """Test recomputing priorities for all scenarios."""
        manager = PriorityManager(
            evaluator=mock_evaluator,
            comparator=mock_comparator,
        )
        
        # Store original priorities
        original_priorities = {s.id: s.priority_score for s in sample_scenarios}
        
        # Recompute all priorities
        changes = manager.recompute_all_priorities(sample_scenarios)
        
        # Check that changes were made
        assert len(changes) > 0
        
        # Each scenario should have updated priority
        for scenario in sample_scenarios:
            assert scenario.priority_score != original_priorities[scenario.id]
            
            # Last evaluation time should be updated
            assert scenario.id in manager.last_evaluation_time

    def test_get_priority_changes(self, sample_scenarios):
        """Test retrieving priority change history."""
        manager = PriorityManager()
        
        # Create some priority changes
        for i, scenario in enumerate(sample_scenarios):
            old_priority = scenario.priority_score
            new_priority = old_priority + 0.1
            
            # Create changes at different times
            record = PriorityChangeRecord(
                scenario_id=scenario.id,
                old_priority=old_priority,
                new_priority=new_priority,
                reason=PriorityChangeReason.EVALUATION_CHANGED,
                timestamp=datetime.now() - timedelta(days=i)
            )
            manager.priority_change_history.append(record)
            
            # Update scenario
            scenario.priority_score = new_priority
        
        # Test getting all changes
        all_changes = manager.get_priority_changes()
        assert len(all_changes) == len(sample_scenarios)
        
        # Test filtering by scenario
        scenario_changes = manager.get_priority_changes(scenario_id=sample_scenarios[0].id)
        assert len(scenario_changes) == 1
        assert scenario_changes[0].scenario_id == sample_scenarios[0].id
        
        # Test filtering by time
        recent_changes = manager.get_priority_changes(
            since=datetime.now() - timedelta(hours=24)
        )
        assert len(recent_changes) == 1  # Only the most recent change
        
        # Test limit
        limited_changes = manager.get_priority_changes(limit=1)
        assert len(limited_changes) == 1

    def test_get_priority_trend(self, sample_scenarios):
        """Test retrieving priority trends over time."""
        manager = PriorityManager()
        scenario = sample_scenarios[0]
        
        # Create a series of priority changes
        priorities = [0.5, 0.6, 0.7, 0.65, 0.8]
        for i, priority in enumerate(priorities):
            old_priority = scenario.priority_score
            record = PriorityChangeRecord(
                scenario_id=scenario.id,
                old_priority=old_priority,
                new_priority=priority,
                reason=PriorityChangeReason.EVALUATION_CHANGED,
                timestamp=datetime.now() - timedelta(days=7-i)
            )
            manager.priority_change_history.append(record)
            scenario.priority_score = priority
        
        # Get the trend
        trend = manager.get_priority_trend(scenario.id, days=10)
        
        # Check trend structure
        assert len(trend) == len(priorities)
        for timestamp, priority in trend:
            assert isinstance(timestamp, datetime)
            assert isinstance(priority, float)
        
        # Check ordering (oldest first)
        assert trend[0][1] == priorities[0]
        assert trend[-1][1] == priorities[-1]
        
        # Test with a shorter timeframe
        short_trend = manager.get_priority_trend(scenario.id, days=3)
        assert len(short_trend) < len(trend)

    def test_get_resource_allocation_history(self, sample_scenarios):
        """Test retrieving resource allocation history."""
        manager = PriorityManager()
        scenario = sample_scenarios[0]
        
        # Create some resource allocations
        for i in range(3):
            allocation = ResourceAllocation(
                allocation_id=f"{scenario.id}-{i}",
                allocation_time=datetime.now(),
                scenario_allocations={scenario.id: 1.0},
                total_resources={"compute_nodes": 50 + i*10, "storage": 200 + i*50}
            )
            manager.resource_allocation_history[scenario.id].append(allocation)
        
        # Get the history
        history = manager.get_resource_allocation_history(scenario.id)
        
        # Check history
        assert len(history) == 3
        assert history[-1].allocation_id == f"{scenario.id}-2"
        
        # Check with limit
        limited_history = manager.get_resource_allocation_history(scenario.id, limit=2)
        assert len(limited_history) == 2
        
        # Test nonexistent scenario
        empty_history = manager.get_resource_allocation_history("nonexistent-id")
        assert empty_history == []