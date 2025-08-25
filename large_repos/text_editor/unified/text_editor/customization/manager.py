"""
Customization manager for the text editor.
"""
from typing import Dict, List, Set, Optional, Any, Callable, Type, Tuple
from pydantic import BaseModel, Field
import time
import copy
import importlib
import sys
import traceback

from text_editor.customization.models import (
    CustomizableComponent,
    CustomizationCategory,
    CustomizationDifficulty,
    ExperimentResults,
    CustomizationHistory
)


# Define default customizable components
DEFAULT_COMPONENTS = [
    CustomizableComponent(
        id="text_buffer",
        name="Text Buffer",
        description="The core data structure for storing and manipulating text.",
        category=CustomizationCategory.TEXT_STORAGE,
        difficulty=CustomizationDifficulty.BASIC,
        default_implementation="list_of_lines",
        alternative_implementations={
            "list_of_lines": "Store text as a list of lines (simple, good for line-oriented operations)",
            "single_string": "Store text as a single string (simpler but less efficient for some operations)",
            "gap_buffer": "Store text with a gap at the cursor position (more efficient for insertions)",
            "piece_table": "Store text as a series of references to an append-only buffer (memory efficient)"
        },
        impact_description="The text buffer directly affects editing performance, especially for large files.",
        implementation_hints=[
            "Consider how insertions and deletions will be handled",
            "Think about memory usage for large files",
            "Consider how line-based operations will be optimized"
        ]
    ),
    CustomizableComponent(
        id="cursor_movement",
        name="Cursor Movement",
        description="Algorithms for moving the cursor through the text.",
        category=CustomizationCategory.CURSOR_BEHAVIOR,
        difficulty=CustomizationDifficulty.BASIC,
        default_implementation="character_wise",
        alternative_implementations={
            "character_wise": "Move the cursor one character at a time",
            "word_wise": "Move the cursor one word at a time",
            "semantic": "Move the cursor based on code semantics",
            "virtual_space": "Allow the cursor to move beyond the end of lines"
        },
        impact_description="Cursor movement affects the user experience and navigation efficiency.",
        implementation_hints=[
            "Consider how the cursor should behave at line ends",
            "Think about word boundaries for word-wise movement",
            "Consider different behavior in different content types (code vs plain text)"
        ]
    ),
    CustomizableComponent(
        id="search_algorithm",
        name="Text Search Algorithm",
        description="Algorithm for finding text within the document.",
        category=CustomizationCategory.SEARCH_ALGORITHM,
        difficulty=CustomizationDifficulty.INTERMEDIATE,
        default_implementation="simple_search",
        alternative_implementations={
            "simple_search": "Basic string.find() search (simple but can be slow for large files)",
            "boyer_moore": "Boyer-Moore algorithm (efficient for large files and long search strings)",
            "regex": "Regular expression search (powerful but can be slower)",
            "fuzzy_search": "Fuzzy matching to find approximate matches"
        },
        impact_description="The search algorithm affects search speed and capabilities.",
        implementation_hints=[
            "Consider the tradeoff between speed and flexibility",
            "Think about case sensitivity and whole word options",
            "Consider how to handle special characters and regex metacharacters"
        ]
    ),
    CustomizableComponent(
        id="undo_system",
        name="Undo/Redo System",
        description="System for tracking and reversing operations.",
        category=CustomizationCategory.UNDO_REDO,
        difficulty=CustomizationDifficulty.INTERMEDIATE,
        default_implementation="operation_based",
        alternative_implementations={
            "operation_based": "Track each operation and its inverse (standard approach)",
            "snapshot_based": "Take snapshots of the document state (simpler but more memory intensive)",
            "command_pattern": "Use the Command pattern to encapsulate operations",
            "diff_based": "Store diffs between states (more efficient for large changes)"
        },
        impact_description="The undo system affects memory usage and the granularity of undo operations.",
        implementation_hints=[
            "Consider how much memory each approach will use",
            "Think about how complex operations will be handled",
            "Consider how to group related operations"
        ]
    ),
    CustomizableComponent(
        id="file_encoding",
        name="File Encoding Handling",
        description="System for handling different file encodings.",
        category=CustomizationCategory.FILE_HANDLING,
        difficulty=CustomizationDifficulty.ADVANCED,
        default_implementation="utf8_with_fallback",
        alternative_implementations={
            "utf8_with_fallback": "Default to UTF-8 with fallback to other encodings",
            "auto_detect": "Automatically detect the encoding from file contents",
            "configurable": "Use encoding specified in configuration",
            "bom_aware": "Handle byte order mark (BOM) for Unicode encodings"
        },
        impact_description="File encoding handling affects compatibility with different file types.",
        implementation_hints=[
            "Consider how to handle encoding errors",
            "Think about performance implications of detection algorithms",
            "Consider how to preserve encoding when saving"
        ]
    ),
    CustomizableComponent(
        id="insert_algorithm",
        name="Text Insertion Algorithm",
        description="Algorithm for inserting text efficiently.",
        category=CustomizationCategory.EDITING_OPERATIONS,
        difficulty=CustomizationDifficulty.ADVANCED,
        default_implementation="simple_insert",
        alternative_implementations={
            "simple_insert": "Direct insertion at cursor position",
            "batch_insert": "Batch multiple insertions for better performance",
            "rope_data_structure": "Use a rope data structure for efficient insertion",
            "linked_list": "Use a linked list for efficient insertion at arbitrary positions"
        },
        impact_description="The insertion algorithm affects editing performance, especially for large files.",
        implementation_hints=[
            "Consider the impact on surrounding text",
            "Think about how to handle multi-line insertions",
            "Consider the memory implications of different approaches"
        ]
    ),
]


class IsolatedEnvironment:
    """
    A class to manage an isolated environment for running customization code.
    """
    def __init__(self):
        """Initialize the isolated environment."""
        self.globals = {}
        self.locals = {}
        
    def execute(self, code: str) -> Tuple[bool, Any, str]:
        """
        Execute code in the isolated environment.
        
        Args:
            code: The Python code to execute
            
        Returns:
            Tuple of (success, result, error_message)
        """
        try:
            # Execute the code
            exec(code, self.globals, self.locals)
            return True, self.locals.get("result", None), ""
        except Exception as e:
            # Capture the error
            error_details = traceback.format_exc()
            return False, None, f"{str(e)}\n{error_details}"
    
    def reset(self):
        """Reset the environment to a clean state."""
        self.globals = {}
        self.locals = {}


class CustomizationManager(BaseModel):
    """
    Manages the customization system for the text editor.
    
    This class provides a safe environment for experimenting with 
    different editor behaviors and algorithms.
    """
    components: Dict[str, CustomizableComponent] = Field(default_factory=dict)
    history: CustomizationHistory = Field(default_factory=CustomizationHistory)
    environment: Optional[IsolatedEnvironment] = None
    active_experiment: Optional[ExperimentResults] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, **kwargs):
        """Initialize the customization manager with default components."""
        super().__init__(**kwargs)
        
        # Initialize with default components
        for component in DEFAULT_COMPONENTS:
            self.components[component.id] = component
            
        # Initialize the isolated environment
        self.environment = IsolatedEnvironment()
    
    def get_component(self, component_id: str) -> Optional[CustomizableComponent]:
        """
        Get a specific customizable component.
        
        Args:
            component_id: ID of the component to retrieve
            
        Returns:
            The CustomizableComponent object, or None if not found
        """
        return self.components.get(component_id)
    
    def get_all_components(self) -> List[CustomizableComponent]:
        """
        Get all customizable components.
        
        Returns:
            List of all CustomizableComponent objects
        """
        return list(self.components.values())
    
    def get_components_by_category(self, category: CustomizationCategory) -> List[CustomizableComponent]:
        """
        Get components filtered by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of CustomizableComponent objects in the specified category
        """
        return [c for c in self.components.values() if c.category == category]
    
    def get_components_by_difficulty(self, difficulty: CustomizationDifficulty) -> List[CustomizableComponent]:
        """
        Get components filtered by difficulty.
        
        Args:
            difficulty: Difficulty level to filter by
            
        Returns:
            List of CustomizableComponent objects at the specified difficulty
        """
        return [c for c in self.components.values() if c.difficulty == difficulty]
    
    def start_experiment(self, component_id: str, implementation_id: str) -> Optional[ExperimentResults]:
        """
        Start a customization experiment.
        
        Args:
            component_id: ID of the component to customize
            implementation_id: ID of the implementation to test
            
        Returns:
            The ExperimentResults object, or None if the experiment couldn't be started
        """
        component = self.get_component(component_id)
        if not component:
            return None
            
        # Check if the implementation exists
        if (implementation_id != "default" and 
            implementation_id not in component.alternative_implementations):
            return None
            
        # Create a new experiment
        experiment = ExperimentResults(
            component_id=component_id,
            implementation_id=implementation_id,
            start_time=time.time()
        )
        
        # Save the current state
        snapshot_id = f"{component_id}_{int(experiment.start_time)}"
        self.history.save_snapshot(snapshot_id, {
            "component": component.dict(),
            "current_implementation": component.current_implementation
        })
        
        # Set the active experiment
        self.active_experiment = experiment
        
        # Update the component's current implementation
        component.current_implementation = implementation_id
        
        return experiment
    
    def complete_experiment(self, success: bool, metrics: Dict[str, float] = None, error: str = None) -> None:
        """
        Complete the active experiment with results.
        
        Args:
            success: Whether the experiment was successful
            metrics: Performance metrics from the experiment
            error: Error message if the experiment failed
        """
        if not self.active_experiment:
            return
            
        # Complete the experiment
        self.active_experiment.complete(success, metrics, error)
        
        # Add to history
        self.history.add_experiment(self.active_experiment)
        
        # If the experiment failed, revert the component
        if not success:
            component_id = self.active_experiment.component_id
            component = self.get_component(component_id)
            if component:
                component.current_implementation = "default"
                
        # Clear the active experiment
        self.active_experiment = None
    
    def cancel_experiment(self) -> None:
        """Cancel the active experiment and revert changes."""
        if not self.active_experiment:
            return
            
        component_id = self.active_experiment.component_id
        component = self.get_component(component_id)
        
        if component:
            # Revert to the default implementation
            component.current_implementation = "default"
            
        # Mark as failed and add to history
        self.active_experiment.complete(False, error="Experiment cancelled")
        self.history.add_experiment(self.active_experiment)
        
        # Clear the active experiment
        self.active_experiment = None
    
    def run_code_in_sandbox(self, code: str) -> Tuple[bool, Any, str]:
        """
        Run code in a sandboxed environment to test a customization.
        
        Args:
            code: The Python code to execute
            
        Returns:
            Tuple of (success, result, error_message)
        """
        # Execute the code without resetting the environment
        # This allows us to preserve any variables added to the environment
        return self.environment.execute(code)
    
    def get_experiment_history(self, component_id: Optional[str] = None) -> List[ExperimentResults]:
        """
        Get the history of experiments.
        
        Args:
            component_id: ID of the component to filter by (optional)
            
        Returns:
            List of ExperimentResults objects
        """
        if component_id:
            return self.history.get_experiments_for_component(component_id)
        else:
            return self.history.experiments
    
    def get_implementation_details(self, component_id: str, implementation_id: str) -> Dict[str, Any]:
        """
        Get details about a specific implementation.
        
        Args:
            component_id: ID of the component
            implementation_id: ID of the implementation
            
        Returns:
            Dictionary with implementation details
        """
        component = self.get_component(component_id)
        if not component:
            return {}
            
        if implementation_id == "default":
            description = f"Default implementation: {component.default_implementation}"
            impl_id = component.default_implementation
        else:
            description = component.alternative_implementations.get(implementation_id, "")
            impl_id = implementation_id
            
        # Get performance history for this implementation
        experiments = self.history.get_experiments_for_component(component_id)
        matching_experiments = [e for e in experiments if e.implementation_id == impl_id]
        
        # Calculate success rate
        total = len(matching_experiments)
        successful = len([e for e in matching_experiments if e.success])
        success_rate = successful / total if total > 0 else 0
        
        # Get average performance metrics
        avg_metrics = {}
        if successful > 0:
            for experiment in [e for e in matching_experiments if e.success]:
                for metric, value in experiment.performance_metrics.items():
                    if metric not in avg_metrics:
                        avg_metrics[metric] = []
                    avg_metrics[metric].append(value)
                    
            avg_metrics = {
                metric: sum(values) / len(values)
                for metric, values in avg_metrics.items()
            }
            
        return {
            "description": description,
            "total_experiments": total,
            "successful_experiments": successful,
            "success_rate": success_rate,
            "average_metrics": avg_metrics,
            "is_current": component.current_implementation == impl_id
        }
    
    def apply_component_customization(self, component_id: str, implementation_id: str, 
                                     code: str) -> Tuple[bool, str]:
        """
        Apply a customization to a component.
        
        Args:
            component_id: ID of the component to customize
            implementation_id: ID of the implementation to apply
            code: Custom implementation code
            
        Returns:
            Tuple of (success, error_message)
        """
        component = self.get_component(component_id)
        if not component:
            return False, f"Component {component_id} not found"
            
        # Check if the implementation exists
        if (implementation_id != "default" and 
            implementation_id not in component.alternative_implementations):
            return False, f"Implementation {implementation_id} not found"
            
        # Start an experiment
        experiment = self.start_experiment(component_id, implementation_id)
        if not experiment:
            return False, "Failed to start experiment"
            
        # Run the code in the sandbox
        success, result, error = self.run_code_in_sandbox(code)
        
        # Get performance metrics
        metrics = {}
        if success and isinstance(result, dict):
            metrics = result.get("metrics", {})
            
        # Complete the experiment
        self.complete_experiment(success, metrics, error)
        
        if not success:
            return False, error
            
        return True, ""
    
    def revert_to_default(self, component_id: str) -> bool:
        """
        Revert a component to its default implementation.
        
        Args:
            component_id: ID of the component to revert
            
        Returns:
            True if successful, False otherwise
        """
        component = self.get_component(component_id)
        if not component:
            return False
            
        # Cancel any active experiment for this component
        if (self.active_experiment and 
            self.active_experiment.component_id == component_id):
            self.cancel_experiment()
            
        # Set to default implementation
        component.current_implementation = "default"
        
        return True
    
    def get_current_implementation(self, component_id: str) -> Optional[str]:
        """
        Get the current implementation for a component.
        
        Args:
            component_id: ID of the component to check
            
        Returns:
            The implementation ID, or None if the component doesn't exist
        """
        component = self.get_component(component_id)
        if not component:
            return None
            
        return component.current_implementation