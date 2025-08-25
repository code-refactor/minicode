"""
Customization playground for safely experimenting with editor customizations.
"""
from typing import Dict, List, Set, Optional, Any, Callable, Type, Tuple
from pydantic import BaseModel, Field
import time
import sys
import traceback
import copy

from text_editor.customization.manager import CustomizationManager
from text_editor.customization.models import (
    CustomizableComponent, 
    CustomizationCategory,
    CustomizationDifficulty,
    ExperimentResults
)
from text_editor.core.editor import Editor


class CustomizationPlayground(BaseModel):
    """
    Playground for safely experimenting with editor customizations.
    
    This class provides a safe environment for testing different
    implementations of editor components without affecting the
    main editor instance.
    """
    manager: CustomizationManager = Field(default_factory=CustomizationManager)
    editor: Optional[Editor] = None
    original_editor: Optional[Editor] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, editor: Optional[Editor] = None, **kwargs):
        """
        Initialize the customization playground.
        
        Args:
            editor: The main editor instance to clone for experiments
        """
        super().__init__(**kwargs)
        
        if editor:
            self.set_editor(editor)
    
    def set_editor(self, editor: Editor) -> None:
        """
        Set the main editor instance to use for experiments.
        
        Args:
            editor: The main editor instance
        """
        self.original_editor = editor
        # Create a deep copy for experimentation
        self.editor = copy.deepcopy(editor)
    
    def reset_editor(self) -> None:
        """Reset the playground editor to match the original."""
        if self.original_editor:
            self.editor = copy.deepcopy(self.original_editor)
    
    def get_available_components(self) -> List[CustomizableComponent]:
        """
        Get all available customizable components.
        
        Returns:
            List of CustomizableComponent objects
        """
        return self.manager.get_all_components()
    
    def start_experiment(self, component_id: str, implementation_id: str) -> Optional[ExperimentResults]:
        """
        Start a customization experiment.
        
        Args:
            component_id: ID of the component to customize
            implementation_id: ID of the implementation to test
            
        Returns:
            The ExperimentResults object, or None if the experiment couldn't be started
        """
        # Create a fresh playground editor for the experiment
        self.reset_editor()
        
        # Start the experiment
        return self.manager.start_experiment(component_id, implementation_id)
    
    def cancel_experiment(self) -> None:
        """Cancel the active experiment and revert changes."""
        self.manager.cancel_experiment()
        self.reset_editor()
    
    def complete_experiment(self, success: bool, metrics: Dict[str, float] = None, error: str = None) -> None:
        """
        Complete the active experiment with results.
        
        Args:
            success: Whether the experiment was successful
            metrics: Performance metrics from the experiment
            error: Error message if the experiment failed
        """
        self.manager.complete_experiment(success, metrics, error)
    
    def run_custom_code(self, code: str) -> Tuple[bool, Any, str]:
        """
        Run custom code in the playground.
        
        Args:
            code: The Python code to execute
            
        Returns:
            Tuple of (success, result, error_message)
        """
        # Add the playground editor to the environment
        self.manager.environment.locals["editor"] = self.editor
        
        # Run the code
        return self.manager.run_code_in_sandbox(code)
    
    def apply_customization(self, component_id: str, implementation_id: str, code: str) -> Tuple[bool, str]:
        """
        Apply a customization to a component.
        
        Args:
            component_id: ID of the component to customize
            implementation_id: ID of the implementation to apply
            code: Custom implementation code
            
        Returns:
            Tuple of (success, error_message)
        """
        # Reset the playground editor
        self.reset_editor()
        
        # Add the playground editor to the environment
        self.manager.environment.locals["editor"] = self.editor
        
        # Apply the customization
        return self.manager.apply_component_customization(component_id, implementation_id, code)
    
    def test_customization(self, test_code: str) -> Tuple[bool, Dict[str, float], str]:
        """
        Test a customization with specific test code.
        
        Args:
            test_code: Python code that tests the customization
            
        Returns:
            Tuple of (success, performance_metrics, error_message)
        """
        # Add the playground editor to the environment
        self.manager.environment.locals["editor"] = self.editor
        
        # Run the test code
        success, result, error = self.manager.run_code_in_sandbox(test_code)
        
        # Extract metrics from the result
        metrics = {}
        if success and isinstance(result, dict):
            metrics = result.get("metrics", {})
            
        return success, metrics, error
    
    def compare_implementations(self, component_id: str, 
                               implementations: List[str], 
                               test_code: str) -> Dict[str, Dict[str, Any]]:
        """
        Compare multiple implementations of a component.
        
        Args:
            component_id: ID of the component to test
            implementations: List of implementation IDs to compare
            test_code: Python code that tests the implementations
            
        Returns:
            Dictionary mapping implementation IDs to result dictionaries
        """
        results = {}
        
        for impl_id in implementations:
            # Start an experiment for this implementation
            experiment = self.start_experiment(component_id, impl_id)
            if not experiment:
                results[impl_id] = {
                    "success": False,
                    "error": f"Failed to start experiment for {impl_id}",
                    "metrics": {}
                }
                continue
                
            # Run the test code
            success, metrics, error = self.test_customization(test_code)
            
            # Complete the experiment
            self.complete_experiment(success, metrics, error)
            
            # Save the results
            results[impl_id] = {
                "success": success,
                "error": error,
                "metrics": metrics
            }
            
        return results
    
    def get_experiment_history(self, component_id: Optional[str] = None) -> List[ExperimentResults]:
        """
        Get the history of experiments.
        
        Args:
            component_id: ID of the component to filter by (optional)
            
        Returns:
            List of ExperimentResults objects
        """
        return self.manager.get_experiment_history(component_id)
    
    def get_implementation_details(self, component_id: str, implementation_id: str) -> Dict[str, Any]:
        """
        Get details about a specific implementation.
        
        Args:
            component_id: ID of the component
            implementation_id: ID of the implementation
            
        Returns:
            Dictionary with implementation details
        """
        return self.manager.get_implementation_details(component_id, implementation_id)
    
    def get_component_explanation(self, component_id: str) -> Dict[str, Any]:
        """
        Get detailed explanation of a component and its customization options.
        
        Args:
            component_id: ID of the component to explain
            
        Returns:
            Dictionary with component explanation
        """
        component = self.manager.get_component(component_id)
        if not component:
            return {}
            
        # Get information about each implementation
        implementations = {}
        
        # Default implementation
        implementations["default"] = self.get_implementation_details(
            component_id, "default"
        )
        
        # Alternative implementations
        for impl_id in component.alternative_implementations:
            implementations[impl_id] = self.get_implementation_details(
                component_id, impl_id
            )
            
        return {
            "id": component.id,
            "name": component.name,
            "description": component.description,
            "category": component.category.value,
            "difficulty": component.difficulty.value,
            "impact_description": component.impact_description,
            "implementation_hints": component.implementation_hints,
            "current_implementation": component.current_implementation,
            "implementations": implementations
        }
    
    def revert_to_default(self, component_id: str) -> bool:
        """
        Revert a component to its default implementation.
        
        Args:
            component_id: ID of the component to revert
            
        Returns:
            True if successful, False otherwise
        """
        result = self.manager.revert_to_default(component_id)
        if result:
            self.reset_editor()
        return result
    
    def revert_all_to_default(self) -> None:
        """Revert all components to their default implementations."""
        for component in self.manager.get_all_components():
            self.manager.revert_to_default(component.id)
        self.reset_editor()
    
    def get_current_state(self) -> Dict[str, str]:
        """
        Get the current implementation state of all components.
        
        Returns:
            Dictionary mapping component IDs to current implementation IDs
        """
        return {
            component.id: component.current_implementation
            for component in self.manager.get_all_components()
        }