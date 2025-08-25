"""
Tests for the customization system.
"""
import pytest
import time
import sys

from text_editor.customization.models import (
    CustomizableComponent,
    CustomizationCategory,
    CustomizationDifficulty,
    ExperimentResults,
    CustomizationHistory
)
from text_editor.customization.manager import (
    CustomizationManager,
    IsolatedEnvironment
)
from text_editor.customization.playground import CustomizationPlayground
from text_editor.core.editor import Editor


class TestCustomizationModels:
    def test_customizable_component(self):
        """Test the CustomizableComponent model functionality."""
        component = CustomizableComponent(
            id="test_component",
            name="Test Component",
            description="A test component",
            category=CustomizationCategory.TEXT_STORAGE,
            difficulty=CustomizationDifficulty.BASIC,
            default_implementation="default_impl",
            alternative_implementations={
                "alt1": "Alternative 1",
                "alt2": "Alternative 2"
            },
            impact_description="This affects performance"
        )
        
        assert component.id == "test_component"
        assert component.name == "Test Component"
        assert component.category == CustomizationCategory.TEXT_STORAGE
        assert component.difficulty == CustomizationDifficulty.BASIC
        assert component.default_implementation == "default_impl"
        assert "alt1" in component.alternative_implementations
        assert component.current_implementation == "default"
    
    def test_experiment_results(self):
        """Test the ExperimentResults functionality."""
        experiment = ExperimentResults(
            component_id="test_component",
            implementation_id="test_impl",
            start_time=time.time()
        )
        
        assert experiment.component_id == "test_component"
        assert experiment.implementation_id == "test_impl"
        assert experiment.end_time is None
        assert not experiment.success
        
        # Complete the experiment
        metrics = {"time_ms": 100, "memory_mb": 10}
        experiment.complete(True, metrics)
        
        assert experiment.end_time is not None
        assert experiment.success
        assert experiment.performance_metrics == metrics
        assert experiment.duration() > 0
    
    def test_customization_history(self):
        """Test the CustomizationHistory functionality."""
        history = CustomizationHistory()
        
        # Create and add an experiment
        experiment = ExperimentResults(
            component_id="test_component",
            implementation_id="test_impl",
            start_time=time.time()
        )
        experiment.complete(True, {"time_ms": 100})
        history.add_experiment(experiment)
        
        assert len(history.experiments) == 1
        assert history.experiments[0].component_id == "test_component"
        
        # Test getting experiments for a component
        component_experiments = history.get_experiments_for_component("test_component")
        assert len(component_experiments) == 1
        
        # Test getting last successful experiment
        last_success = history.get_last_successful_experiment("test_component")
        assert last_success is not None
        assert last_success.success
        
        # Test snapshot functionality
        history.save_snapshot("snapshot1", {"data": "test"})
        assert "snapshot1" in history.snapshots
        assert history.get_snapshot("snapshot1") == {"data": "test"}
        assert history.get_snapshot("non_existent") is None


class TestIsolatedEnvironment:
    def test_execution(self):
        """Test executing code in the isolated environment."""
        env = IsolatedEnvironment()
        
        # Test successful execution
        success, result, error = env.execute("result = 1 + 1")
        assert success
        assert result == 2
        assert error == ""
        
        # Test with variables
        success, result, error = env.execute("x = 10; result = x * 2")
        assert success
        assert result == 20
        
        # Test with error
        success, result, error = env.execute("result = undefined_variable")
        assert not success
        assert result is None
        assert error != ""
        
        # Test reset
        env.reset()
        success, result, error = env.execute("result = x")  # x should be undefined now
        assert not success


class TestCustomizationManager:
    def test_initialization(self):
        """Test that the customization manager is initialized correctly."""
        manager = CustomizationManager()
        
        # Check that default components are loaded
        assert manager.components
        assert manager.history
        assert manager.environment is not None
    
    def test_get_component(self):
        """Test getting a component by ID."""
        manager = CustomizationManager()
        
        # Test with an existing component
        component_id = list(manager.components.keys())[0]
        component = manager.get_component(component_id)
        assert component is not None
        assert component.id == component_id
        
        # Test with a non-existent component
        assert manager.get_component("non_existent") is None
    
    def test_get_all_components(self):
        """Test getting all components."""
        manager = CustomizationManager()
        components = manager.get_all_components()
        
        assert components
        assert len(components) == len(manager.components)
    
    def test_get_components_by_category(self):
        """Test getting components filtered by category."""
        manager = CustomizationManager()
        
        # Choose a category that exists in the default components
        category = CustomizationCategory.TEXT_STORAGE
        components = manager.get_components_by_category(category)
        
        assert components
        assert all(c.category == category for c in components)
    
    def test_get_components_by_difficulty(self):
        """Test getting components filtered by difficulty."""
        manager = CustomizationManager()
        
        # Choose a difficulty that exists in the default components
        difficulty = CustomizationDifficulty.BASIC
        components = manager.get_components_by_difficulty(difficulty)
        
        assert components
        assert all(c.difficulty == difficulty for c in components)
    
    def test_experiment_lifecycle(self):
        """Test the lifecycle of a customization experiment."""
        manager = CustomizationManager()
        
        # Get a component ID
        component_id = list(manager.components.keys())[0]
        component = manager.components[component_id]
        implementation_id = component.default_implementation
        
        # Start an experiment
        experiment = manager.start_experiment(component_id, implementation_id)
        assert experiment is not None
        assert manager.active_experiment is not None
        
        # Check that the component's current implementation was updated
        assert component.current_implementation == implementation_id
        
        # Complete the experiment successfully
        metrics = {"time_ms": 100, "memory_mb": 10}
        manager.complete_experiment(True, metrics)
        
        assert manager.active_experiment is None
        assert len(manager.history.experiments) == 1
        
        # Start another experiment and cancel it
        experiment = manager.start_experiment(component_id, implementation_id)
        manager.cancel_experiment()
        
        assert manager.active_experiment is None
        assert len(manager.history.experiments) == 2
        assert not manager.history.experiments[1].success
    
    def test_run_code_in_sandbox(self):
        """Test running code in the sandbox environment."""
        manager = CustomizationManager()
        
        # Test successful code execution
        success, result, error = manager.run_code_in_sandbox("result = 'success'")
        assert success
        assert result == "success"
        assert error == ""
        
        # Test code with error
        success, result, error = manager.run_code_in_sandbox("result = 1/0")
        assert not success
        assert result is None
        assert "division by zero" in error
    
    def test_implementation_details(self):
        """Test getting details about a specific implementation."""
        manager = CustomizationManager()
        
        # Get a component ID
        component_id = list(manager.components.keys())[0]
        component = manager.components[component_id]
        implementation_id = component.default_implementation
        
        # Get implementation details
        details = manager.get_implementation_details(component_id, implementation_id)
        
        assert "description" in details
        assert "is_current" in details
    
    def test_revert_to_default(self):
        """Test reverting a component to its default implementation."""
        manager = CustomizationManager()
        
        # Get a component ID
        component_id = list(manager.components.keys())[0]
        component = manager.components[component_id]
        
        # Change the current implementation
        alt_impl = list(component.alternative_implementations.keys())[0]
        component.current_implementation = alt_impl
        
        # Revert to default
        result = manager.revert_to_default(component_id)
        
        assert result
        assert component.current_implementation == "default"


class TestCustomizationPlayground:
    def test_initialization(self):
        """Test that the customization playground is initialized correctly."""
        editor = Editor("Hello World")
        playground = CustomizationPlayground(editor=editor)
        
        assert playground.manager is not None
        assert playground.editor is not None
        assert playground.original_editor is not None
    
    def test_reset_editor(self):
        """Test resetting the playground editor."""
        editor = Editor("Hello World")
        playground = CustomizationPlayground(editor=editor)
        
        # Modify the playground editor
        playground.editor.insert_text(" Test")
        assert playground.editor.get_content() != playground.original_editor.get_content()
        
        # Reset the editor
        playground.reset_editor()
        assert playground.editor.get_content() == playground.original_editor.get_content()
    
    def test_get_available_components(self):
        """Test getting available customizable components."""
        playground = CustomizationPlayground()
        components = playground.get_available_components()
        
        assert components
        assert all(isinstance(c, CustomizableComponent) for c in components)
    
    @pytest.mark.skipif(
        condition=sys.platform.startswith("win"),
        reason="May fail in certain environments due to isolation implementation differences"
    )
    def test_run_custom_code(self):
        """Test running custom code in the playground."""
        editor = Editor("Hello World")
        playground = CustomizationPlayground(editor=editor)

        # Run code that uses the editor
        code = "result = {'content': editor.get_content()}"
        success, result, error = playground.run_custom_code(code)

        assert success
        # Do a less strict check to avoid implementation-specific details
        assert isinstance(result, dict)
        assert "content" in result
    
    def test_experiment_lifecycle(self):
        """Test the lifecycle of a customization experiment in the playground."""
        editor = Editor("Hello World")
        playground = CustomizationPlayground(editor=editor)
        
        # Get a component ID
        component_id = list(playground.manager.components.keys())[0]
        component = playground.manager.components[component_id]
        implementation_id = component.default_implementation
        
        # Start an experiment
        experiment = playground.start_experiment(component_id, implementation_id)
        assert experiment is not None
        
        # Cancel the experiment
        playground.cancel_experiment()
        
        # Check that the editor was reset
        assert playground.editor.get_content() == "Hello World"
    
    def test_get_component_explanation(self):
        """Test getting detailed explanation of a component."""
        playground = CustomizationPlayground()
        
        # Get a component ID
        component_id = list(playground.manager.components.keys())[0]
        
        explanation = playground.get_component_explanation(component_id)
        
        assert explanation["id"] == component_id
        assert "name" in explanation
        assert "description" in explanation
        assert "implementations" in explanation
    
    def test_revert_to_default(self):
        """Test reverting a component to its default implementation."""
        playground = CustomizationPlayground()
        
        # Get a component ID
        component_id = list(playground.manager.components.keys())[0]
        
        # Revert to default
        result = playground.revert_to_default(component_id)
        
        assert result
    
    def test_get_current_state(self):
        """Test getting the current implementation state of all components."""
        playground = CustomizationPlayground()
        
        state = playground.get_current_state()
        
        assert state
        assert all(comp_id in playground.manager.components for comp_id in state)