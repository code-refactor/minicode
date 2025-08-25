"""Tests for the scenario model."""

import pytest
from datetime import datetime

from concurrent_task_scheduler.models.scenario import (
    Scenario,
    ScenarioStatus,
    ScientificMetric,
    ResearchObjective,
    ComparisonResult,
    ScenarioEvaluationResult,
    ResourceAllocation,
)
from concurrent_task_scheduler.models.simulation import (
    Simulation,
    SimulationPriority,
    SimulationStatus,
)


class TestScientificMetric:
    """Tests for the ScientificMetric model."""
    
    def test_initialization(self):
        """Test initialization of scientific metrics."""
        # Basic initialization
        metric = ScientificMetric(
            name="accuracy",
            value=0.85,
        )
        
        assert metric.name == "accuracy"
        assert metric.value == 0.85
        assert metric.is_higher_better is True  # Default
        assert metric.weight == 1.0  # Default
        
        # Full initialization
        metric = ScientificMetric(
            name="error_rate",
            description="Error rate of simulation",
            value=0.15,
            unit="dimensionless",
            target_value=0.1,
            weight=1.2,
            is_higher_better=False,
            confidence=0.9,
        )
        
        assert metric.name == "error_rate"
        assert metric.description == "Error rate of simulation"
        assert metric.value == 0.15
        assert metric.unit == "dimensionless"
        assert metric.target_value == 0.1
        assert metric.weight == 1.2
        assert metric.is_higher_better is False
        assert metric.confidence == 0.9

    def test_normalized_score(self):
        """Test calculation of normalized scores."""
        # Test higher is better without target
        metric1 = ScientificMetric(
            name="accuracy",
            value=0.85,
            weight=1.0,
            is_higher_better=True,
        )
        
        assert metric1.normalized_score() == 0.85
        
        # Test lower is better without target
        metric2 = ScientificMetric(
            name="error",
            value=0.15,
            weight=1.0,
            is_higher_better=False,
        )
        
        assert metric2.normalized_score() == 0.85  # 1 - 0.15
        
        # Test higher is better with target (at target)
        metric3 = ScientificMetric(
            name="convergence",
            value=0.9,
            target_value=0.9,
            weight=1.0,
            is_higher_better=True,
        )
        
        assert metric3.normalized_score() == 1.0  # At target
        
        # Test higher is better with target (below target)
        metric4 = ScientificMetric(
            name="convergence",
            value=0.45,
            target_value=0.9,
            weight=1.0,
            is_higher_better=True,
        )
        
        assert metric4.normalized_score() == 0.5  # 0.45 / 0.9
        
        # Test lower is better with target (at target)
        metric5 = ScientificMetric(
            name="error_rate",
            value=0.1,
            target_value=0.1,
            weight=1.0,
            is_higher_better=False,
        )
        
        assert metric5.normalized_score() == 1.0  # At target
        
        # Test lower is better with target (above target)
        metric6 = ScientificMetric(
            name="error_rate",
            value=0.2,
            target_value=0.1,
            weight=1.0,
            is_higher_better=False,
        )
        
        assert metric6.normalized_score() == 0.5  # 0.1 / 0.2
        
        # Test with weight
        metric7 = ScientificMetric(
            name="accuracy",
            value=0.8,
            weight=1.5,
            is_higher_better=True,
        )
        
        # Use pytest.approx for float comparisons to handle floating point precision
        import pytest
        assert metric7.normalized_score() == pytest.approx(1.2)  # 0.8 * 1.5


class TestResearchObjective:
    """Tests for the ResearchObjective model."""
    
    def test_initialization(self):
        """Test initialization of research objectives."""
        objective = ResearchObjective(
            id="obj-123",
            name="Temperature Prediction",
            description="Improve global temperature prediction accuracy",
            importance=4.5,
            target_metrics={"accuracy": 0.95, "resolution": 25},
            success_criteria="Achieve 95% accuracy at 25km resolution",
        )
        
        assert objective.id == "obj-123"
        assert objective.name == "Temperature Prediction"
        assert objective.description == "Improve global temperature prediction accuracy"
        assert objective.importance == 4.5
        assert objective.target_metrics == {"accuracy": 0.95, "resolution": 25}
        assert objective.success_criteria == "Achieve 95% accuracy at 25km resolution"

    def test_is_relevant_to_scenario(self):
        """Test checking if an objective is relevant to a scenario."""
        objective = ResearchObjective(
            id="obj-123",
            name="Temperature Prediction",
            description="Improve global temperature prediction accuracy",
            target_metrics={"accuracy": 0.95, "resolution": 25},
            success_criteria="Achieve 95% accuracy at 25km resolution",
        )
        
        # Scenario with matching tags
        scenario1 = Scenario(
            id="scenario-1",
            name="High Accuracy Model",
            description="A model focused on accuracy",
            tags=["climate", "accuracy", "temperature"],
        )
        
        # Scenario without matching tags
        scenario2 = Scenario(
            id="scenario-2",
            name="Novel Approach",
            description="A novel modeling approach",
            tags=["climate", "novel", "experimental"],
        )
        
        assert objective.is_relevant_to_scenario(scenario1) is True
        assert objective.is_relevant_to_scenario(scenario2) is False


class TestScenario:
    """Tests for the Scenario model."""
    
    def test_initialization(self):
        """Test initialization of scenarios."""
        scenario = Scenario(
            id="scenario-123",
            name="Test Scenario",
            description="A test scenario",
            status=ScenarioStatus.ACTIVE,
            priority_score=0.75,
            tags=["climate", "test"],
        )
        
        assert scenario.id == "scenario-123"
        assert scenario.name == "Test Scenario"
        assert scenario.description == "A test scenario"
        assert scenario.status == ScenarioStatus.ACTIVE
        assert scenario.priority_score == 0.75
        assert scenario.tags == ["climate", "test"]
        assert isinstance(scenario.creation_time, datetime)
        assert isinstance(scenario.last_updated, datetime)
        assert scenario.simulations == {}

    def test_calculate_priority_score(self):
        """Test calculation of priority score from metrics."""
        scenario = Scenario(
            id="scenario-123",
            name="Test Scenario",
            description="A test scenario",
        )
        
        # Empty metrics should give default priority
        assert scenario.calculate_priority_score() == 0.5
        
        # Add some metrics
        scenario.scientific_metrics = {
            "accuracy": ScientificMetric(
                name="accuracy",
                value=0.9,
                weight=1.0,
            ),
            "convergence": ScientificMetric(
                name="convergence",
                value=0.8,
                weight=0.5,
            ),
            "efficiency": ScientificMetric(
                name="efficiency",
                value=0.7,
                weight=0.25,
            ),
        }
        
        # Calculate expected score manually
        expected_score = (
            (0.9 * 1.0) + (0.8 * 0.5) + (0.7 * 0.25)
        ) / (1.0 + 0.5 + 0.25)
        
        assert scenario.calculate_priority_score() == pytest.approx(expected_score)
        
        # Test with zero weights
        scenario.scientific_metrics = {
            "accuracy": ScientificMetric(
                name="accuracy",
                value=0.9,
                weight=0.0,
            ),
        }
        
        assert scenario.calculate_priority_score() == 0.5  # Default

    def test_update_priority(self):
        """Test updating a scenario's priority."""
        scenario = Scenario(
            id="scenario-123",
            name="Test Scenario",
            description="A test scenario",
            priority_score=0.5,
        )
        
        # Add metrics to change priority
        scenario.scientific_metrics = {
            "accuracy": ScientificMetric(
                name="accuracy",
                value=0.9,
                weight=1.0,
            ),
        }
        
        # Store original update time
        original_update_time = scenario.last_updated
        
        # Update after adding the metrics
        scenario.update_priority()
        
        # Priority should be updated
        assert scenario.priority_score == 0.9
        
        # Last updated should be changed
        assert scenario.last_updated > original_update_time

    def test_get_simulation_status_counts(self):
        """Test counting simulations by status."""
        scenario = Scenario(
            id="scenario-123",
            name="Test Scenario",
            description="A test scenario",
        )
        
        # Add simulations with different statuses
        sim1 = Simulation(
            id="sim-1",
            name="Sim 1",
            description="Running simulation",
            status=SimulationStatus.RUNNING,
            stages={},  # Empty stages dictionary to satisfy the requirement
        )
        
        sim2 = Simulation(
            id="sim-2",
            name="Sim 2",
            description="Completed simulation",
            status=SimulationStatus.COMPLETED,
            stages={},  # Empty stages dictionary to satisfy the requirement
        )
        
        sim3 = Simulation(
            id="sim-3",
            name="Sim 3",
            description="Another running simulation",
            status=SimulationStatus.RUNNING,
            stages={},  # Empty stages dictionary to satisfy the requirement
        )
        
        scenario.simulations = {
            "sim-1": sim1,
            "sim-2": sim2,
            "sim-3": sim3,
        }
        
        counts = scenario.get_simulation_status_counts()
        assert counts["running"] == 2
        assert counts["completed"] == 1
        assert "pending" not in counts

    def test_get_derived_priority(self):
        """Test converting numeric priority to simulation priority level."""
        scenario = Scenario(
            id="scenario-123",
            name="Test Scenario",
            description="A test scenario",
        )
        
        # Test different priority thresholds
        scenario.priority_score = 0.1
        assert scenario.get_derived_priority() == SimulationPriority.BACKGROUND
        
        scenario.priority_score = 0.3
        assert scenario.get_derived_priority() == SimulationPriority.LOW
        
        scenario.priority_score = 0.5
        assert scenario.get_derived_priority() == SimulationPriority.MEDIUM
        
        scenario.priority_score = 0.7
        assert scenario.get_derived_priority() == SimulationPriority.HIGH
        
        scenario.priority_score = 0.9
        assert scenario.get_derived_priority() == SimulationPriority.CRITICAL

    def test_total_progress(self):
        """Test calculating total progress across simulations."""
        scenario = Scenario(
            id="scenario-123",
            name="Test Scenario",
            description="A test scenario",
        )
        
        # Test with no simulations
        assert scenario.total_progress() == 0.0
        
        # Create a mock class that overrides total_progress
        class MockSimulation(Simulation):
            def __init__(self, id, name, description, progress_value, **kwargs):
                super().__init__(id=id, name=name, description=description, **kwargs)
                self._progress_value = progress_value
                
            def total_progress(self) -> float:
                return self._progress_value
        
        # Add simulations with different progress
        sim1 = MockSimulation(id="sim-1", name="Sim 1", description="Sim 1", stages={}, progress_value=0.25)
        sim2 = MockSimulation(id="sim-2", name="Sim 2", description="Sim 2", stages={}, progress_value=0.75)
        
        scenario.simulations = {
            "sim-1": sim1,
            "sim-2": sim2,
        }
        
        # Expected progress is average
        assert scenario.total_progress() == 0.5


class TestComparisonResult:
    """Tests for the ComparisonResult model."""
    
    def test_initialization(self):
        """Test initialization of comparison results."""
        comparison = ComparisonResult(
            scenario_id_a="scenario-a",
            scenario_id_b="scenario-b",
            metrics_comparison={"accuracy": {"a": 0.9, "b": 0.8}},
            overall_difference=0.15,
            confidence=0.85,
            recommendation="Scenario A shows more promise",
        )
        
        assert comparison.scenario_id_a == "scenario-a"
        assert comparison.scenario_id_b == "scenario-b"
        assert comparison.metrics_comparison == {"accuracy": {"a": 0.9, "b": 0.8}}
        assert comparison.overall_difference == 0.15
        assert comparison.confidence == 0.85
        assert comparison.recommendation == "Scenario A shows more promise"
        assert isinstance(comparison.comparison_time, datetime)

    def test_clear_winner(self):
        """Test determining if there's a clear winner."""
        # Clear winner A
        comparison1 = ComparisonResult(
            scenario_id_a="scenario-a",
            scenario_id_b="scenario-b",
            metrics_comparison={},
            overall_difference=0.25,
            confidence=0.8,
            recommendation="",
        )
        
        assert comparison1.clear_winner() == "scenario-a"
        
        # Clear winner B
        comparison2 = ComparisonResult(
            scenario_id_a="scenario-a",
            scenario_id_b="scenario-b",
            metrics_comparison={},
            overall_difference=-0.25,
            confidence=0.8,
            recommendation="",
        )
        
        assert comparison2.clear_winner() == "scenario-b"
        
        # No clear winner (difference too small)
        comparison3 = ComparisonResult(
            scenario_id_a="scenario-a",
            scenario_id_b="scenario-b",
            metrics_comparison={},
            overall_difference=0.1,
            confidence=0.8,
            recommendation="",
        )
        
        assert comparison3.clear_winner() is None
        
        # No clear winner (confidence too low)
        comparison4 = ComparisonResult(
            scenario_id_a="scenario-a",
            scenario_id_b="scenario-b",
            metrics_comparison={},
            overall_difference=0.3,
            confidence=0.6,
            recommendation="",
        )
        
        assert comparison4.clear_winner() is None


class TestScenarioEvaluationResult:
    """Tests for the ScenarioEvaluationResult model."""
    
    def test_initialization(self):
        """Test initialization of evaluation results."""
        evaluation = ScenarioEvaluationResult(
            scenario_id="scenario-123",
            overall_score=0.75,
            metric_scores={"accuracy": 0.9, "efficiency": 0.6},
            confidence=0.8,
            recommendation="continue",
            suggested_priority=0.8,
            reasons=["High accuracy", "Good convergence"]
        )
        
        assert evaluation.scenario_id == "scenario-123"
        assert evaluation.overall_score == 0.75
        assert evaluation.metric_scores == {"accuracy": 0.9, "efficiency": 0.6}
        assert evaluation.confidence == 0.8
        assert evaluation.recommendation == "continue"
        assert evaluation.suggested_priority == 0.8
        assert evaluation.reasons == ["High accuracy", "Good convergence"]
        assert isinstance(evaluation.evaluation_time, datetime)

    def test_should_adjust_priority(self):
        """Test determining if priority should be adjusted."""
        evaluation = ScenarioEvaluationResult(
            scenario_id="scenario-123",
            overall_score=0.75,
            metric_scores={},
            confidence=0.8,
            recommendation="continue",
            suggested_priority=0.8,
            reasons=[]
        )
        
        # Should adjust (difference above threshold)
        assert evaluation.should_adjust_priority(current_priority=0.6) is True
        
        # Should not adjust (difference below threshold)
        assert evaluation.should_adjust_priority(current_priority=0.79) is False
        
        # With custom threshold
        assert evaluation.should_adjust_priority(current_priority=0.75, threshold=0.01) is True


class TestResourceAllocation:
    """Tests for the ResourceAllocation model."""
    
    def test_initialization(self):
        """Test initialization of resource allocations."""
        allocation = ResourceAllocation(
            allocation_id="alloc-123",
            scenario_allocations={"scenario-a": 0.6, "scenario-b": 0.4},
            total_resources={"compute_nodes": 100, "storage": 500},
            allocation_reason={"scenario-a": "high priority", "scenario-b": "medium priority"},
            minimum_allocations={"scenario-a": 0.3, "scenario-b": 0.2},
        )
        
        assert allocation.allocation_id == "alloc-123"
        assert allocation.scenario_allocations == {"scenario-a": 0.6, "scenario-b": 0.4}
        assert allocation.total_resources == {"compute_nodes": 100, "storage": 500}
        assert allocation.allocation_reason == {"scenario-a": "high priority", "scenario-b": "medium priority"}
        assert allocation.minimum_allocations == {"scenario-a": 0.3, "scenario-b": 0.2}
        assert isinstance(allocation.allocation_time, datetime)
        assert allocation.expiration_time is None

    def test_get_absolute_allocation(self):
        """Test calculating absolute allocation for a scenario."""
        allocation = ResourceAllocation(
            allocation_id="alloc-123",
            scenario_allocations={"scenario-a": 0.7, "scenario-b": 0.3},
            total_resources={"compute_nodes": 100, "storage": 500},
        )
        
        # Check compute nodes
        assert allocation.get_absolute_allocation("compute_nodes", "scenario-a") == 70
        assert allocation.get_absolute_allocation("compute_nodes", "scenario-b") == 30
        
        # Check storage
        assert allocation.get_absolute_allocation("storage", "scenario-a") == 350
        assert allocation.get_absolute_allocation("storage", "scenario-b") == 150
        
        # Check nonexistent resource type or scenario
        assert allocation.get_absolute_allocation("nonexistent", "scenario-a") == 0
        assert allocation.get_absolute_allocation("compute_nodes", "nonexistent") == 0

    def test_is_valid(self):
        """Test validity checking for allocations."""
        # Valid allocation (100%)
        allocation1 = ResourceAllocation(
            allocation_id="alloc-1",
            scenario_allocations={"scenario-a": 0.7, "scenario-b": 0.3},
            total_resources={"compute_nodes": 100},
        )
        
        assert allocation1.is_valid() is True
        
        # Valid allocation (less than 100%)
        allocation2 = ResourceAllocation(
            allocation_id="alloc-2",
            scenario_allocations={"scenario-a": 0.6, "scenario-b": 0.2},
            total_resources={"compute_nodes": 100},
        )
        
        assert allocation2.is_valid() is True
        
        # Invalid allocation (more than 100%)
        allocation3 = ResourceAllocation(
            allocation_id="alloc-3",
            scenario_allocations={"scenario-a": 0.7, "scenario-b": 0.4},
            total_resources={"compute_nodes": 100},
        )
        
        assert allocation3.is_valid() is False