"""Tests for the dependency tracking system."""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from concurrent_task_scheduler.dependency_tracking import (
    DependencyGraph,
    DependencyState,
    DependencyTracker,
    DependencyType,
    GraphNodeType,
    SimulationDependency,
    TransitionRule,
    TransitionTrigger,
    WorkflowInstance,
    WorkflowManager,
    WorkflowNodeType,
    WorkflowStage,
    WorkflowTemplate,
    WorkflowTemplateType,
    WorkflowTransition,
    WorkflowTransitionType,
)
from concurrent_task_scheduler.models import (
    ResourceRequirement,
    ResourceType,
    Result,
    Simulation,
    SimulationPriority,
    SimulationStage,
    SimulationStageStatus,
    SimulationStatus,
)


class TestDependencyGraph:
    """Tests for the DependencyGraph class."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.graph = DependencyGraph("sim-test-1")
        
        # Add stages
        self.graph.add_stage("stage-1")
        self.graph.add_stage("stage-2")
        self.graph.add_stage("stage-3")
        self.graph.add_stage("stage-4")
        
        # Add dependencies
        self.graph.add_dependency("stage-1", "stage-2")  # 1 -> 2
        self.graph.add_dependency("stage-2", "stage-3")  # 2 -> 3
        self.graph.add_dependency("stage-2", "stage-4")  # 2 -> 4
    
    def test_add_stage(self):
        """Test adding a stage to the graph."""
        self.graph.add_stage("stage-5")
        assert "stage-5" in self.graph.graph.nodes()
    
    def test_add_dependency(self):
        """Test adding a dependency between stages."""
        result = self.graph.add_dependency("stage-3", "stage-4")
        assert result.success
        assert self.graph.graph.has_edge("stage-3", "stage-4")
        
        # Get the dependency
        dependency = self.graph.get_dependency("stage-3", "stage-4")
        assert dependency is not None
        assert dependency.from_stage_id == "stage-3"
        assert dependency.to_stage_id == "stage-4"
        assert dependency.dependency_type == DependencyType.SEQUENTIAL
        assert dependency.state == DependencyState.PENDING
    
    def test_add_dependency_with_cycle(self):
        """Test that adding a dependency that creates a cycle fails."""
        result = self.graph.add_dependency("stage-3", "stage-1")
        assert not result.success
        assert "cycle" in result.error.lower()
    
    def test_remove_dependency(self):
        """Test removing a dependency."""
        result = self.graph.remove_dependency("stage-2", "stage-3")
        assert result.success
        assert not self.graph.graph.has_edge("stage-2", "stage-3")
    
    def test_get_dependencies(self):
        """Test getting dependencies to and from a stage."""
        deps_from = self.graph.get_dependencies_from("stage-2")
        assert len(deps_from) == 2
        
        deps_to = self.graph.get_dependencies_to("stage-2")
        assert len(deps_to) == 1
        assert deps_to[0].from_stage_id == "stage-1"
    
    def test_get_root_and_leaf_stages(self):
        """Test getting root and leaf stages."""
        roots = self.graph.get_root_stages()
        assert "stage-1" in roots
        
        leaves = self.graph.get_leaf_stages()
        assert "stage-3" in leaves
        assert "stage-4" in leaves
    
    def test_get_ready_stages(self):
        """Test getting stages that are ready to execute."""
        # Initially, only the root stage should be ready
        completed_stages = set()
        ready = self.graph.get_ready_stages(completed_stages)
        assert "stage-1" in ready
        assert len(ready) == 1
        
        # After completing stage-1, stage-2 should be ready
        completed_stages.add("stage-1")
        ready = self.graph.get_ready_stages(completed_stages)
        assert "stage-2" in ready
        assert len(ready) == 1
        
        # After completing stage-2, both stage-3 and stage-4 should be ready
        completed_stages.add("stage-2")
        ready = self.graph.get_ready_stages(completed_stages)
        assert "stage-3" in ready
        assert "stage-4" in ready
        assert len(ready) == 2
    
    def test_are_all_dependencies_satisfied(self):
        """Test checking if all dependencies to a stage are satisfied."""
        # Initially, no dependencies are satisfied
        assert not self.graph.are_all_dependencies_satisfied("stage-2")
        
        # Satisfy the dependency from stage-1 to stage-2
        dep = self.graph.get_dependency("stage-1", "stage-2")
        dep.satisfy()
        
        # Now all dependencies to stage-2 should be satisfied
        assert self.graph.are_all_dependencies_satisfied("stage-2")
    
    def test_update_stage_status(self):
        """Test updating a stage's status and propagating changes."""
        # Complete stage-1
        affected = self.graph.update_stage_status("stage-1", SimulationStageStatus.COMPLETED)
        assert "stage-2" in affected
        
        # Check that the dependency from stage-1 to stage-2 is satisfied
        dep = self.graph.get_dependency("stage-1", "stage-2")
        assert dep.is_satisfied()
    
    def test_get_critical_path(self):
        """Test getting the critical path through the graph."""
        path = self.graph.get_critical_path()
        assert len(path) == 4
        assert path[0] == "stage-1"  # Starting point
        
        # Check that the order is correct
        assert path.index("stage-1") < path.index("stage-2")
        assert path.index("stage-2") < path.index("stage-3")
        assert path.index("stage-2") < path.index("stage-4")
    
    def test_is_stage_blocked(self):
        """Test checking if a stage is blocked."""
        # stage-2 is blocked by stage-1
        blocking = self.graph.is_stage_blocked("stage-2", set())
        assert "stage-1" in blocking
        
        # After completing stage-1, stage-2 should not be blocked
        blocking = self.graph.is_stage_blocked("stage-2", {"stage-1"})
        assert blocking is None
    
    def test_validate(self):
        """Test validating the graph."""
        # The test graph should be valid
        errors = self.graph.validate()
        assert not errors
        
        # Add a cycle to make it invalid
        # First remove a dependency to avoid error from add_dependency
        self.graph.remove_dependency("stage-2", "stage-3")
        
        # We manually create the cycle to bypass the add_dependency check
        self.graph.graph.add_edge("stage-3", "stage-1")
        
        # Now validation should fail
        errors = self.graph.validate()
        assert any("cycle" in error.lower() for error in errors)
    
    def test_serialize_deserialize(self):
        """Test serializing and deserializing the graph."""
        # Serialize
        data = self.graph.serialize()
        assert data["simulation_id"] == "sim-test-1"
        assert len(data["nodes"]) == 4
        assert len(data["edges"]) == 3
        
        # Deserialize
        new_graph = DependencyGraph.deserialize(data)
        assert new_graph.simulation_id == "sim-test-1"
        assert len(new_graph.graph.nodes()) == 4
        assert len(new_graph.graph.edges()) == 3
        assert new_graph.graph.has_edge("stage-1", "stage-2")
        assert new_graph.graph.has_edge("stage-2", "stage-3")
        assert new_graph.graph.has_edge("stage-2", "stage-4")


class TestDependencyTracker:
    """Tests for the DependencyTracker class."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.tracker = DependencyTracker()
        self.simulation = self._create_test_simulation()
    
    def _create_test_simulation(self) -> Simulation:
        """Create a test simulation with multiple stages."""
        # Create stages
        stage1 = SimulationStage(
            id="stage-1",
            name="Stage 1",
            estimated_duration=timedelta(hours=1),
            resource_requirements=[
                ResourceRequirement(
                    resource_type=ResourceType.CPU,
                    amount=4,
                    unit="cores",
                ),
            ],
        )
        
        stage2 = SimulationStage(
            id="stage-2",
            name="Stage 2",
            estimated_duration=timedelta(hours=2),
            resource_requirements=[
                ResourceRequirement(
                    resource_type=ResourceType.CPU,
                    amount=8,
                    unit="cores",
                ),
            ],
            dependencies={"stage-1"},  # Depends on stage-1
        )
        
        stage3 = SimulationStage(
            id="stage-3",
            name="Stage 3",
            estimated_duration=timedelta(hours=3),
            resource_requirements=[
                ResourceRequirement(
                    resource_type=ResourceType.CPU,
                    amount=4,
                    unit="cores",
                ),
            ],
            dependencies={"stage-2"},  # Depends on stage-2
        )
        
        # Create simulation
        return Simulation(
            id="sim-test-1",
            name="Test Simulation",
            stages={
                "stage-1": stage1,
                "stage-2": stage2,
                "stage-3": stage3,
            },
            owner="researcher-1",
            project="test-project",
        )
    
    def test_create_dependency_graph(self):
        """Test creating a dependency graph for a simulation."""
        result = self.tracker.create_dependency_graph(self.simulation)
        assert result.success
        
        # Check that the graph was created
        assert self.simulation.id in self.tracker.dependency_graphs
        
        # Check that the stages were added
        graph = self.tracker.dependency_graphs[self.simulation.id]
        assert "stage-1" in graph.graph.nodes()
        assert "stage-2" in graph.graph.nodes()
        assert "stage-3" in graph.graph.nodes()
        
        # Check that dependencies were added
        assert graph.graph.has_edge("stage-1", "stage-2")
        assert graph.graph.has_edge("stage-2", "stage-3")
    
    def test_add_dependency(self):
        """Test adding a dependency between stages."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Add a new dependency
        result = self.tracker.add_dependency(
            self.simulation.id,
            "stage-1",
            "stage-3",
            DependencyType.DATA,
        )
        
        assert result.success
        
        # Check that the dependency was added
        graph = self.tracker.dependency_graphs[self.simulation.id]
        assert graph.graph.has_edge("stage-1", "stage-3")
        
        # Check the dependency type
        dependency = graph.get_dependency("stage-1", "stage-3")
        assert dependency.dependency_type == DependencyType.DATA
    
    def test_remove_dependency(self):
        """Test removing a dependency between stages."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Remove a dependency
        result = self.tracker.remove_dependency(
            self.simulation.id,
            "stage-1",
            "stage-2",
        )
        
        assert result.success
        
        # Check that the dependency was removed
        graph = self.tracker.dependency_graphs[self.simulation.id]
        assert not graph.graph.has_edge("stage-1", "stage-2")
    
    def test_add_transition_rule(self):
        """Test adding a transition rule between stages."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Add a transition rule
        result = self.tracker.add_transition_rule(
            self.simulation.id,
            "stage-1",
            "stage-2",
            TransitionTrigger.AUTOMATIC,
        )
        
        assert result.success
        
        # Check that the rule was added
        assert self.simulation.id in self.tracker.transition_rules
        assert len(self.tracker.transition_rules[self.simulation.id]) == 1
        
        rule = self.tracker.transition_rules[self.simulation.id][0]
        assert rule.from_stage_id == "stage-1"
        assert rule.to_stage_id == "stage-2"
        assert rule.trigger == TransitionTrigger.AUTOMATIC
    
    def test_update_stage_status(self):
        """Test updating a stage's status and propagating changes."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Update stage-1 to completed
        result = self.tracker.update_stage_status(
            self.simulation,
            "stage-1",
            SimulationStageStatus.COMPLETED,
        )
        
        assert result.success
        propagated = result.value
        
        # Check that stage-2 is now queued
        assert "stage-2" in propagated
        assert self.simulation.stages["stage-2"].status == SimulationStageStatus.QUEUED
        
        # Check that the dependency from stage-1 to stage-2 is satisfied
        graph = self.tracker.dependency_graphs[self.simulation.id]
        dependency = graph.get_dependency("stage-1", "stage-2")
        assert dependency.is_satisfied()
    
    def test_get_ready_stages(self):
        """Test getting stages that are ready to execute."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Initially, only stage-1 should be ready
        ready = self.tracker.get_ready_stages(self.simulation)
        assert "stage-1" in ready
        assert len(ready) == 1
        
        # Complete stage-1
        self.simulation.stages["stage-1"].status = SimulationStageStatus.COMPLETED
        
        # Now stage-2 should be ready
        ready = self.tracker.get_ready_stages(self.simulation)
        assert "stage-2" in ready
        assert len(ready) == 1
    
    def test_is_stage_ready(self):
        """Test checking if a stage is ready to execute."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Stage-1 should be ready
        assert self.tracker.is_stage_ready(self.simulation, "stage-1")
        
        # Stage-2 should not be ready yet
        assert not self.tracker.is_stage_ready(self.simulation, "stage-2")
        
        # Complete stage-1
        self.simulation.stages["stage-1"].status = SimulationStageStatus.COMPLETED
        
        # Now stage-2 should be ready
        assert self.tracker.is_stage_ready(self.simulation, "stage-2")
    
    def test_get_blocking_stages(self):
        """Test getting stages that are blocking a specific stage."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Stage-2 is blocked by stage-1
        blocking = self.tracker.get_blocking_stages(self.simulation, "stage-2")
        assert "stage-1" in blocking
        
        # Complete stage-1
        self.simulation.stages["stage-1"].status = SimulationStageStatus.COMPLETED
        
        # Now stage-2 should not be blocked
        blocking = self.tracker.get_blocking_stages(self.simulation, "stage-2")
        assert not blocking
    
    def test_get_critical_path(self):
        """Test getting the critical path through the simulation."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Get critical path
        path = self.tracker.get_critical_path(self.simulation)
        
        # The path should include all stages in correct order
        assert len(path) == 3
        assert path[0] == "stage-1"
        assert path[1] == "stage-2"
        assert path[2] == "stage-3"
    
    def test_bypass_dependency(self):
        """Test manually bypassing a dependency."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Bypass the dependency from stage-1 to stage-2
        result = self.tracker.bypass_dependency(
            self.simulation.id,
            "stage-1",
            "stage-2",
        )
        
        assert result.success
        
        # Check that the dependency was bypassed
        graph = self.tracker.dependency_graphs[self.simulation.id]
        dependency = graph.get_dependency("stage-1", "stage-2")
        assert dependency.state == DependencyState.BYPASSED
        
        # Check that the manual override was recorded
        assert (
            "stage-1",
            "stage-2",
        ) in self.tracker.manual_overrides[self.simulation.id]
    
    def test_add_dynamic_dependency(self):
        """Test adding a dynamically discovered dependency at runtime."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Add a dynamic dependency from stage-1 to stage-3
        result = self.tracker.add_dynamic_dependency(
            self.simulation,
            "stage-1",
            "stage-3",
            DependencyType.DATA,
        )
        
        assert result.success
        
        # Check that the dependency was added to the simulation
        assert "stage-1" in self.simulation.stages["stage-3"].dependencies
        
        # Check that the dependency was added to the graph
        graph = self.tracker.dependency_graphs[self.simulation.id]
        assert graph.graph.has_edge("stage-1", "stage-3")
        
        # Check the dependency type
        dependency = graph.get_dependency("stage-1", "stage-3")
        assert dependency.dependency_type == DependencyType.DATA
    
    def test_get_execution_plan(self):
        """Test generating an execution plan for the simulation."""
        # Create dependency graph
        self.tracker.create_dependency_graph(self.simulation)
        
        # Get execution plan
        plan = self.tracker.get_execution_plan(self.simulation)
        
        # The plan should have 3 steps (one for each stage)
        assert len(plan) == 3
        
        # Check that the stages are in the correct order
        assert plan[0] == ["stage-1"]
        assert plan[1] == ["stage-2"]
        assert plan[2] == ["stage-3"]
    
    def test_validate_simulation(self):
        """Test validating the simulation dependency structure."""
        # The test simulation should be valid
        errors = self.tracker.validate_simulation(self.simulation)
        assert not errors
        
        # Add a dependency to a non-existent stage
        self.simulation.stages["stage-2"].dependencies.add("non-existent-stage")
        
        # Now validation should fail
        errors = self.tracker.validate_simulation(self.simulation)
        assert errors
        assert any("non-existent" in error.lower() for error in errors)


class TestWorkflowManager:
    """Tests for the WorkflowManager class."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.tracker = DependencyTracker()
        self.manager = WorkflowManager(self.tracker)
        self.simulation = self._create_test_simulation()
    
    def _create_test_simulation(self) -> Simulation:
        """Create a test simulation with no stages."""
        return Simulation(
            id="sim-test-1",
            name="Test Simulation",
            stages={},
            owner="researcher-1",
            project="test-project",
        )
    
    def test_register_template(self):
        """Test registering a workflow template."""
        # Create a simple sequential template
        template = WorkflowTemplate.create_sequential(
            name="Test Sequential Workflow",
            stage_names=["Stage 1", "Stage 2", "Stage 3"],
        )
        
        # Register the template
        result = self.manager.register_template(template)
        assert result.success
        
        # Check that the template was registered
        assert template.id in self.manager.templates
    
    def test_create_instance(self):
        """Test creating a workflow instance from a template."""
        # Create a simple sequential template
        template = WorkflowTemplate.create_sequential(
            name="Test Sequential Workflow",
            stage_names=["Stage 1", "Stage 2", "Stage 3"],
        )
        
        # Register the template
        self.manager.register_template(template)
        
        # Create an instance
        result = self.manager.create_instance(template.id, self.simulation)
        assert result.success
        
        instance = result.value
        
        # Check that the instance was created
        assert instance.id in self.manager.instances
        assert instance.template_id == template.id
        assert instance.simulation_id == self.simulation.id
        
        # Check that stages were created in the simulation
        assert len(self.simulation.stages) == 3
        
        # Check that the stages were mapped correctly
        assert len(instance.stage_mapping) == 3
        
        # Check that dependencies were set up
        self.tracker.create_dependency_graph(self.simulation)
        graph = self.tracker.dependency_graphs[self.simulation.id]
        
        # Find the stage IDs in the order they appear in the template
        stage_ids = list(self.simulation.stages.keys())
        stage_ids.sort(key=lambda s: self.simulation.stages[s].name)
        
        # Check the dependencies in the graph
        assert graph.graph.has_edge(stage_ids[0], stage_ids[1])
        assert graph.graph.has_edge(stage_ids[1], stage_ids[2])
    
    def test_create_linear_workflow(self):
        """Test creating a simple linear workflow."""
        # Create a linear workflow
        result = self.manager.create_linear_workflow(
            self.simulation,
            ["Stage A", "Stage B", "Stage C"],
        )
        
        assert result.success
        instance = result.value
        
        # Check that the instance was created
        assert instance.id in self.manager.instances
        
        # Check that stages were created in the simulation
        assert len(self.simulation.stages) == 3
        
        # Check that the dependencies work
        stage_ids = list(self.simulation.stages.keys())
        
        # Get stages by name
        stage_a = None
        stage_b = None
        stage_c = None
        
        for stage_id, stage in self.simulation.stages.items():
            if stage.name == "Stage A":
                stage_a = stage_id
            elif stage.name == "Stage B":
                stage_b = stage_id
            elif stage.name == "Stage C":
                stage_c = stage_id
        
        assert stage_a is not None
        assert stage_b is not None
        assert stage_c is not None
        
        # Check dependencies
        assert stage_a not in self.simulation.stages[stage_b].dependencies
        assert stage_b in self.simulation.stages[stage_c].dependencies
    
    def test_create_parallel_workflow(self):
        """Test creating a simple parallel workflow."""
        # Create a parallel workflow
        result = self.manager.create_parallel_workflow(
            self.simulation,
            ["Stage X", "Stage Y", "Stage Z"],
        )
        
        assert result.success
        instance = result.value
        
        # Check that the instance was created
        assert instance.id in self.manager.instances
        
        # Check that stages were created in the simulation (including start and end)
        assert len(self.simulation.stages) == 5
        
        # Check that the start and end stages exist
        has_start = False
        has_end = False
        
        for stage in self.simulation.stages.values():
            if stage.name == "Start":
                has_start = True
            elif stage.name == "End":
                has_end = True
        
        assert has_start
        assert has_end
        
        # Get the actual workflow template
        template = self.manager.templates[instance.template_id]
        
        # Check the structure of the template
        assert len(template.stages) == 5  # Start, End, and 3 real stages
        assert len(template.transitions) == 6  # 3 from Start and 3 to End
    
    def test_get_next_stages(self):
        """Test getting the next stages to execute in a workflow instance."""
        # Create a linear workflow
        result = self.manager.create_linear_workflow(
            self.simulation,
            ["Stage 1", "Stage 2", "Stage 3"],
        )
        
        assert result.success
        instance = result.value
        
        # Get the next stages (initially, only the first stage)
        next_result = self.manager.get_next_stages(instance.id, self.simulation)
        assert next_result.success
        next_stages = next_result.value
        
        assert len(next_stages) == 1
        
        # Get the stage ID of Stage 1
        stage_1_id = None
        for stage_id, stage in self.simulation.stages.items():
            if stage.name == "Stage 1":
                stage_1_id = stage_id
                break
        
        assert stage_1_id is not None
        assert stage_1_id in next_stages
        
        # Complete Stage 1
        self.manager.update_instance(
            instance.id,
            self.simulation,
            stage_1_id,
            SimulationStageStatus.COMPLETED,
        )
        
        # Get the next stages (now Stage 2)
        next_result = self.manager.get_next_stages(instance.id, self.simulation)
        assert next_result.success
        next_stages = next_result.value
        
        assert len(next_stages) == 1
        
        # Get the stage ID of Stage 2
        stage_2_id = None
        for stage_id, stage in self.simulation.stages.items():
            if stage.name == "Stage 2":
                stage_2_id = stage_id
                break
        
        assert stage_2_id is not None
        assert stage_2_id in next_stages
    
    def test_update_instance(self):
        """Test updating a stage status in a workflow instance."""
        # Create a linear workflow
        result = self.manager.create_linear_workflow(
            self.simulation,
            ["Stage 1", "Stage 2", "Stage 3"],
        )
        
        assert result.success
        instance = result.value
        
        # Get the stage ID of Stage 1
        stage_1_id = None
        for stage_id, stage in self.simulation.stages.items():
            if stage.name == "Stage 1":
                stage_1_id = stage_id
                break
        
        assert stage_1_id is not None
        
        # Update the status of Stage 1
        update_result = self.manager.update_instance(
            instance.id,
            self.simulation,
            stage_1_id,
            SimulationStageStatus.RUNNING,
        )
        assert update_result.success
        
        # Check that the stage status was updated
        assert self.simulation.stages[stage_1_id].status == SimulationStageStatus.RUNNING
        
        # Check that the instance status was updated
        assert instance.status == SimulationStatus.RUNNING
        assert instance.start_time is not None
        
        # Complete the stage
        update_result = self.manager.update_instance(
            instance.id,
            self.simulation,
            stage_1_id,
            SimulationStageStatus.COMPLETED,
        )
        assert update_result.success
        
        # Check that the stage status was updated
        assert self.simulation.stages[stage_1_id].status == SimulationStageStatus.COMPLETED
        assert self.simulation.stages[stage_1_id].end_time is not None
        
        # Check that the instance was updated
        assert stage_1_id in [
            instance.get_simulation_stage_id(stage_id)
            for stage_id in instance.completed_stages
        ]
    
    def test_get_workflow_status(self):
        """Test getting the current status of a workflow instance."""
        # Create a linear workflow
        result = self.manager.create_linear_workflow(
            self.simulation,
            ["Stage 1", "Stage 2", "Stage 3"],
        )
        
        assert result.success
        instance = result.value
        
        # Get status
        status_result = self.manager.get_workflow_status(instance.id)
        assert status_result.success
        status = status_result.value
        
        # Check status values
        assert status["instance_id"] == instance.id
        assert status["template_id"] == instance.template_id
        assert status["simulation_id"] == self.simulation.id
        assert status["status"] == SimulationStatus.SCHEDULED.value
        assert status["progress"] == 0.0
        assert status["total_stages"] == 3
        assert status["completed_stages"] == 0
        
        # Complete a stage
        stage_1_id = None
        for stage_id, stage in self.simulation.stages.items():
            if stage.name == "Stage 1":
                stage_1_id = stage_id
                break
        
        assert stage_1_id is not None
        self.manager.update_instance(
            instance.id,
            self.simulation,
            stage_1_id,
            SimulationStageStatus.COMPLETED,
        )
        
        # Get updated status
        status_result = self.manager.get_workflow_status(instance.id)
        assert status_result.success
        status = status_result.value
        
        # Check progress
        assert status["progress"] == 1/3  # 1 out of 3 stages completed
        assert status["completed_stages"] == 1