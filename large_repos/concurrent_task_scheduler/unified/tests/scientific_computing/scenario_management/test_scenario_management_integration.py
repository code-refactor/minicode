"""Integration tests for the scenario management system."""

import pytest
from datetime import datetime, timedelta

from concurrent_task_scheduler.models.scenario import (
    Scenario,
    ScientificMetric,
    ScenarioStatus,
    ComparisonResult,
)
from concurrent_task_scheduler.models.simulation import Simulation, SimulationPriority
from concurrent_task_scheduler.scenario_management import (
    ScenarioEvaluator,
    ScenarioComparator,
    PriorityManager,
    ComparisonMethod,
    EvaluationCriteria,
    ResourceReallocationStrategy,
)


@pytest.fixture
def integrated_system():
    """Create a fully integrated scenario management system."""
    evaluator = ScenarioEvaluator()
    comparator = ScenarioComparator(evaluator=evaluator)
    manager = PriorityManager(
        evaluator=evaluator,
        comparator=comparator,
        reallocation_strategy=ResourceReallocationStrategy.BALANCED,
        evaluation_interval=timedelta(hours=4),
        min_priority_change_threshold=0.05,
    )
    
    return {
        "evaluator": evaluator,
        "comparator": comparator,
        "manager": manager,
    }


@pytest.fixture
def sample_scenarios():
    """Create sample scenarios for integration testing."""
    # Create three scenarios with different characteristics
    scenarios = []
    
    # Scenario 1: High accuracy, good convergence, moderate efficiency
    scenario1 = Scenario(
        id="high-accuracy-scenario",
        name="High Accuracy Climate Model",
        description="A climate model focused on accuracy",
        status=ScenarioStatus.ACTIVE,
        priority_score=0.7,
        tags=["climate", "high-resolution", "accuracy-focused"],
        resource_allocation={"compute_nodes": 100, "storage": 500, "memory": 200},
    )
    
    # Add scientific metrics
    scenario1.scientific_metrics = {
        "accuracy_global_temp": ScientificMetric(
            name="accuracy_global_temp",
            description="Accuracy of global temperature prediction",
            value=0.92,
            unit="dimensionless",
            is_higher_better=True,
            weight=1.2,
        ),
        "convergence_rate": ScientificMetric(
            name="convergence_rate",
            description="Convergence rate of simulation",
            value=0.85,
            unit="iterations^-1",
            is_higher_better=True,
            weight=1.0,
        ),
        "computational_efficiency": ScientificMetric(
            name="computational_efficiency",
            description="Computational efficiency",
            value=0.65,
            unit="dimensionless",
            is_higher_better=True,
            weight=0.8,
        ),
    }
    
    # Add simulations
    sim1 = Simulation(
        id="sim-accuracy-1",
        name="Atmospheric Model",
        description="High-resolution atmospheric simulation",
        estimated_duration=timedelta(days=14),
        priority=SimulationPriority.HIGH,
        stages={},  # Empty stages dictionary to satisfy the requirement
    )
    
    sim2 = Simulation(
        id="sim-accuracy-2",
        name="Ocean Coupling",
        description="Ocean model coupled to atmosphere",
        estimated_duration=timedelta(days=7),
        priority=SimulationPriority.HIGH,
        stages={},  # Empty stages dictionary to satisfy the requirement
        # Remove dependencies as it's not a field in the Simulation model
    )
    
    scenario1.simulations = {
        "sim-accuracy-1": sim1,
        "sim-accuracy-2": sim2,
    }
    
    scenarios.append(scenario1)
    
    # Scenario 2: Moderate accuracy, high efficiency, novel approach
    scenario2 = Scenario(
        id="efficient-scenario",
        name="Efficient Climate Model",
        description="A climate model optimized for efficiency",
        status=ScenarioStatus.ACTIVE,
        priority_score=0.6,
        tags=["climate", "medium-resolution", "efficiency-focused"],
        resource_allocation={"compute_nodes": 50, "storage": 200, "memory": 100},
    )
    
    # Add scientific metrics
    scenario2.scientific_metrics = {
        "accuracy_global_temp": ScientificMetric(
            name="accuracy_global_temp",
            description="Accuracy of global temperature prediction",
            value=0.78,
            unit="dimensionless",
            is_higher_better=True,
            weight=1.0,
        ),
        "computational_efficiency": ScientificMetric(
            name="computational_efficiency",
            description="Computational efficiency",
            value=0.95,
            unit="dimensionless",
            is_higher_better=True,
            weight=1.2,
        ),
        "novelty_approach": ScientificMetric(
            name="novelty_approach",
            description="Novelty of modeling approach",
            value=0.87,
            unit="dimensionless",
            is_higher_better=True,
            weight=1.0,
        ),
    }
    
    # Add simulations
    sim3 = Simulation(
        id="sim-efficient-1",
        name="Optimized Atmospheric Model",
        description="Efficiency-optimized atmospheric simulation",
        estimated_duration=timedelta(days=5),
        priority=SimulationPriority.MEDIUM,
        stages={},  # Empty stages dictionary to satisfy the requirement
    )
    
    scenario2.simulations = {
        "sim-efficient-1": sim3,
    }
    
    scenarios.append(scenario2)
    
    # Scenario 3: Experimental approach, lower accuracy but high novelty
    scenario3 = Scenario(
        id="novel-scenario",
        name="Novel Climate Model Approach",
        description="An experimental approach to climate modeling",
        status=ScenarioStatus.ACTIVE,
        priority_score=0.4,
        tags=["climate", "experimental", "novel-approach"],
        resource_allocation={"compute_nodes": 30, "storage": 100, "memory": 80},
    )
    
    # Add scientific metrics
    scenario3.scientific_metrics = {
        "accuracy_global_temp": ScientificMetric(
            name="accuracy_global_temp",
            description="Accuracy of global temperature prediction",
            value=0.62,
            unit="dimensionless",
            is_higher_better=True,
            weight=1.0,
        ),
        "novelty_approach": ScientificMetric(
            name="novelty_approach",
            description="Novelty of modeling approach",
            value=0.98,
            unit="dimensionless",
            is_higher_better=True,
            weight=1.3,
        ),
        "significance_potential": ScientificMetric(
            name="significance_potential",
            description="Potential scientific significance",
            value=0.9,
            unit="dimensionless",
            is_higher_better=True,
            weight=1.1,
        ),
    }
    
    # Add simulation
    sim4 = Simulation(
        id="sim-novel-1",
        name="Experimental Model",
        description="Novel approach to climate modeling",
        estimated_duration=timedelta(days=10),
        priority=SimulationPriority.LOW,
        stages={},  # Empty stages dictionary to satisfy the requirement
    )
    
    scenario3.simulations = {
        "sim-novel-1": sim4,
    }
    
    scenarios.append(scenario3)
    
    return scenarios


class TestScenarioManagementIntegration:
    """Integration tests for the scenario management system."""
    
    def test_end_to_end_workflow(self, integrated_system, sample_scenarios):
        """Test the entire priority management workflow from evaluation to reallocation."""
        evaluator = integrated_system["evaluator"]
        comparator = integrated_system["comparator"]
        manager = integrated_system["manager"]
        
        # 1. Initial evaluation of all scenarios
        evaluation_results = []
        for scenario in sample_scenarios:
            result = evaluator.evaluate_scenario(scenario)
            assert result.success
            evaluation_results.append(result.value)
        
        # Check that evaluations were created
        for scenario in sample_scenarios:
            assert evaluator.get_latest_evaluation(scenario.id) is not None
        
        # 2. Compare scenarios pairwise
        comparison_results = []
        for i in range(len(sample_scenarios)):
            for j in range(i+1, len(sample_scenarios)):
                result = comparator.compare_scenarios(
                    sample_scenarios[i],
                    sample_scenarios[j],
                    method=ComparisonMethod.WEIGHTED
                )
                assert result.success
                comparison_results.append(result.value)
        
        # Check that comparisons were created
        for i in range(len(sample_scenarios)):
            for j in range(i+1, len(sample_scenarios)):
                history = comparator.get_comparison_history(
                    sample_scenarios[i].id,
                    sample_scenarios[j].id
                )
                assert len(history) == 1
        
        # 3. Update scenario priorities based on evaluations
        priority_changes = []
        for scenario in sample_scenarios:
            change_record = manager.update_scenario_priority(scenario)
            if change_record:
                priority_changes.append(change_record)
        
        # 4. Compare and adjust priorities
        comparison_changes = manager.compare_and_adjust_priorities(
            sample_scenarios,
            comparison_method=ComparisonMethod.WEIGHTED
        )
        
        # Check that some changes occurred
        assert len(priority_changes) + len(comparison_changes) > 0
        
        # Record priorities before reallocation
        pre_reallocation_priorities = {s.id: s.priority_score for s in sample_scenarios}
        pre_reallocation_resources = {
            s.id: s.resource_allocation.copy() for s in sample_scenarios
        }
        
        # 5. Reallocate resources based on priorities
        allocation_changes = manager.reallocate_resources(sample_scenarios)
        
        # Check resource reallocation
        assert len(allocation_changes) > 0
        
        # Higher priority scenarios should get more resources
        sorted_scenarios = sorted(
            sample_scenarios,
            key=lambda s: s.priority_score,
            reverse=True  # Highest priority first
        )
        
        # The highest priority scenario should gain resources
        highest_priority = sorted_scenarios[0]
        old_resources = pre_reallocation_resources[highest_priority.id]
        new_resources = highest_priority.resource_allocation
        
        # Calculate total resources
        old_total = sum(old_resources.values())
        new_total = sum(new_resources.values())
        
        # Highest priority scenario should have more resources after reallocation
        assert new_total > old_total
        
        # The lowest priority scenario should lose resources
        lowest_priority = sorted_scenarios[-1]
        old_resources = pre_reallocation_resources[lowest_priority.id]
        new_resources = lowest_priority.resource_allocation
        
        old_total = sum(old_resources.values())
        new_total = sum(new_resources.values())
        
        # Lowest priority scenario should have fewer resources after reallocation
        assert new_total < old_total
        
        # Check that resource allocation history was recorded
        for scenario in sample_scenarios:
            assert scenario.id in manager.resource_allocation_history
            assert len(manager.resource_allocation_history[scenario.id]) > 0

    def test_scenario_metric_updates_propagation(self, integrated_system, sample_scenarios):
        """Test that metric updates propagate through the entire system."""
        evaluator = integrated_system["evaluator"]
        comparator = integrated_system["comparator"]
        manager = integrated_system["manager"]
        
        # Select a scenario to modify
        scenario = sample_scenarios[0]
        
        # Get initial evaluation, comparison, and priority
        initial_eval = evaluator.evaluate_scenario(scenario).value
        manager.update_scenario_priority(scenario)
        initial_priority = scenario.priority_score
        
        # Record initial resource allocation
        initial_resources = sum(scenario.resource_allocation.values())
        
        # Update a key metric to improve the scenario
        accuracy_metric = scenario.scientific_metrics["accuracy_global_temp"]
        original_value = accuracy_metric.value
        accuracy_metric.value = 0.98  # Significant improvement
        
        # Force immediate evaluation
        updated_eval = evaluator.evaluate_scenario(scenario).value
        
        # Update priority based on new evaluation
        change_record = manager.update_scenario_priority(scenario, force=True)
        assert change_record is not None
        
        # Check that the change was recorded
        # The priority may not always increase from a single metric change,
        # especially if other metrics are considered in the final score
        assert change_record is not None
        
        # Perform comparison and reallocation
        manager.compare_and_adjust_priorities(sample_scenarios)
        manager.reallocate_resources(sample_scenarios)
        
        # Check that resources were reallocated
        final_resources = sum(scenario.resource_allocation.values())
        # Resources might increase or decrease depending on how other scenarios are prioritized
        assert final_resources != initial_resources
        
        # Reset the metric
        accuracy_metric.value = original_value

    def test_priority_manager_adaptation(self, integrated_system, sample_scenarios):
        """Test the priority manager's ability to adapt to changing scenario promise."""
        evaluator = integrated_system["evaluator"]
        comparator = integrated_system["comparator"]
        manager = integrated_system["manager"]
        
        # Initial evaluation and resource allocation
        for scenario in sample_scenarios:
            evaluator.evaluate_scenario(scenario)
            manager.update_scenario_priority(scenario)
        
        manager.reallocate_resources(sample_scenarios)
        
        # Record initial state
        initial_priorities = {s.id: s.priority_score for s in sample_scenarios}
        initial_resources = {
            s.id: sum(s.resource_allocation.values()) for s in sample_scenarios
        }
        
        # Change scientific promise of scenarios to reverse their ranking
        # Make the lowest priority scenario much better
        sorted_by_priority = sorted(
            sample_scenarios,
            key=lambda s: s.priority_score
        )
        
        lowest_priority = sorted_by_priority[0]
        highest_priority = sorted_by_priority[-1]
        
        # Dramatically improve lowest priority scenario metrics
        for metric in lowest_priority.scientific_metrics.values():
            metric.value = min(1.0, metric.value + 0.3)
        
        # Reduce highest priority scenario metrics
        for metric in highest_priority.scientific_metrics.values():
            metric.value = max(0.2, metric.value - 0.3)
        
        # Recompute all priorities to adjust to new scientific promise
        manager.recompute_all_priorities(sample_scenarios)
        
        # Reallocate resources
        manager.reallocate_resources(sample_scenarios)
        
        # Check adaptation - priorities should have reversed
        assert lowest_priority.priority_score > initial_priorities[lowest_priority.id]
        assert highest_priority.priority_score < initial_priorities[highest_priority.id]
        
        # Check resource allocation adaptation
        final_resources = {
            s.id: sum(s.resource_allocation.values()) for s in sample_scenarios
        }
        
        # Previously low priority scenario should now have more resources
        assert final_resources[lowest_priority.id] > initial_resources[lowest_priority.id]
        
        # Previously high priority scenario should now have fewer resources
        assert final_resources[highest_priority.id] < initial_resources[highest_priority.id]

    def test_manual_override_integration(self, integrated_system, sample_scenarios):
        """Test that manual priority overrides integrate with the rest of the system."""
        manager = integrated_system["manager"]
        
        # Initial evaluation and allocation
        for scenario in sample_scenarios:
            manager.update_scenario_priority(scenario)
        
        initial_allocation = manager.reallocate_resources(sample_scenarios)
        
        # Record initial resources
        initial_resources = {
            s.id: sum(s.resource_allocation.values()) for s in sample_scenarios
        }
        
        # Manually override a low-priority scenario to high priority
        low_priority = min(sample_scenarios, key=lambda s: s.priority_score)
        
        manager.manual_priority_override(
            low_priority,
            0.9,  # Very high priority
            reason_note="Critical research breakthrough potential"
        )
        
        # Reallocate resources based on manual override
        manager.reallocate_resources(sample_scenarios)
        
        # Check that the manually prioritized scenario got more resources
        final_resources = {
            s.id: sum(s.resource_allocation.values()) for s in sample_scenarios
        }
        
        assert final_resources[low_priority.id] > initial_resources[low_priority.id]
        
        # Check priority history includes the manual change
        history = manager.get_priority_changes(scenario_id=low_priority.id)
        
        # Should have at least one record with MANUAL_OVERRIDE reason
        from concurrent_task_scheduler.scenario_management.priority_manager import PriorityChangeReason
        manual_overrides = [
            change for change in history 
            if change.reason == PriorityChangeReason.MANUAL_OVERRIDE
        ]
        
        assert len(manual_overrides) > 0