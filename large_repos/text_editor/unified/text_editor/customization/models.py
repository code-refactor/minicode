"""
Data models for the customization system.
"""
from enum import Enum, auto
from typing import Dict, List, Set, Optional, Any, Callable, Type
from pydantic import BaseModel, Field
import time


class CustomizationCategory(Enum):
    """Categories of editor components that can be customized."""
    TEXT_STORAGE = "text_storage"
    CURSOR_BEHAVIOR = "cursor_behavior"
    EDITING_OPERATIONS = "editing_operations"
    SEARCH_ALGORITHM = "search_algorithm"
    UNDO_REDO = "undo_redo"
    FILE_HANDLING = "file_handling"
    PERFORMANCE = "performance"


class CustomizationDifficulty(Enum):
    """Difficulty levels for customization tasks."""
    BASIC = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


class CustomizableComponent(BaseModel):
    """
    Represents a component of the editor that can be customized.
    """
    id: str
    name: str
    description: str
    category: CustomizationCategory
    difficulty: CustomizationDifficulty
    default_implementation: str
    alternative_implementations: Dict[str, str] = Field(default_factory=dict)
    impact_description: str
    implementation_hints: List[str] = Field(default_factory=list)
    current_implementation: str = "default"


class ExperimentResults(BaseModel):
    """
    Represents the results of a customization experiment.
    """
    component_id: str
    implementation_id: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    notes: str = ""
    
    def complete(self, success: bool, metrics: Dict[str, float] = None, error: str = None) -> None:
        """
        Mark the experiment as complete with results.
        
        Args:
            success: Whether the experiment was successful
            metrics: Performance metrics from the experiment
            error: Error message if the experiment failed
        """
        self.end_time = time.time()
        self.success = success
        
        if metrics:
            self.performance_metrics = metrics
            
        if error:
            self.error_message = error
    
    def duration(self) -> float:
        """
        Get the duration of the experiment in seconds.
        
        Returns:
            Duration of the experiment, or -1 if not completed
        """
        if self.end_time is None:
            return -1
        
        return self.end_time - self.start_time


class CustomizationHistory(BaseModel):
    """
    Tracks the history of customization experiments.
    """
    experiments: List[ExperimentResults] = Field(default_factory=list)
    snapshots: Dict[str, Any] = Field(default_factory=dict)
    
    def add_experiment(self, experiment: ExperimentResults) -> None:
        """
        Add an experiment to the history.
        
        Args:
            experiment: The experiment to add
        """
        self.experiments.append(experiment)
    
    def get_experiments_for_component(self, component_id: str) -> List[ExperimentResults]:
        """
        Get all experiments for a specific component.
        
        Args:
            component_id: ID of the component to get experiments for
            
        Returns:
            List of experiments for the component
        """
        return [e for e in self.experiments if e.component_id == component_id]
    
    def get_last_successful_experiment(self, component_id: str) -> Optional[ExperimentResults]:
        """
        Get the last successful experiment for a component.
        
        Args:
            component_id: ID of the component to check
            
        Returns:
            The last successful experiment, or None if none found
        """
        experiments = self.get_experiments_for_component(component_id)
        successful = [e for e in experiments if e.success]
        
        if successful:
            return successful[-1]
        
        return None
    
    def save_snapshot(self, snapshot_id: str, snapshot_data: Any) -> None:
        """
        Save a snapshot of the editor state.
        
        Args:
            snapshot_id: ID for the snapshot
            snapshot_data: Data to save
        """
        self.snapshots[snapshot_id] = snapshot_data
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Any]:
        """
        Get a saved snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to retrieve
            
        Returns:
            The snapshot data, or None if not found
        """
        return self.snapshots.get(snapshot_id)