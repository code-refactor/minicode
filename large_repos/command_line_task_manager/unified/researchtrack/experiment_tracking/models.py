"""
Models for the Experiment Tracking module.

This module provides data models for tracking experiments, including
parameters, metrics, and results.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

from common.core import BaseEntity


class ParameterType(str, Enum):
    """Types of parameters that can be used in experiments."""
    
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class Parameter(BaseEntity):
    """A parameter used in an experiment."""
    
    name: str = ""
    type: ParameterType = ParameterType.STRING
    value: Any = None
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Parameter name cannot be empty")


class MetricType(str, Enum):
    """Types of metrics that can be tracked in experiments."""
    
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LOSS = "loss"
    PERPLEXITY = "perplexity"
    AUC = "auc"
    MEAN_SQUARE_ERROR = "mean_square_error"
    MEAN_ABSOLUTE_ERROR = "mean_absolute_error"
    R_SQUARED = "r_squared"
    CUSTOM = "custom"


@dataclass
class Metric(BaseEntity):
    """A metric used to evaluate an experiment."""
    
    name: str = ""
    type: MetricType = MetricType.CUSTOM
    value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Metric name cannot be empty")


class ExperimentStatus(str, Enum):
    """Status of an experiment run."""
    
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ExperimentRun(BaseEntity):
    """A single run of an experiment."""
    
    experiment_id: str = ""
    run_number: int = 0
    status: ExperimentStatus = ExperimentStatus.PLANNED
    parameters: List[Parameter] = field(default_factory=list)
    metrics: Dict[str, Metric] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)  # name -> path
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.experiment_id:
            raise ValueError("Experiment ID cannot be empty")
        if self.run_number < 1:
            raise ValueError("Run number must be positive")
    
    def duration(self) -> Optional[float]:
        """Calculate the duration of the experiment run in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class Experiment(BaseEntity):
    """An experiment with multiple runs."""
    
    name: str = ""
    description: Optional[str] = None
    task_id: Optional[str] = None  # Link to a research task
    dataset_id: Optional[str] = None  # Link to a dataset
    environment_id: Optional[str] = None  # Link to an environment snapshot
    runs: List[ExperimentRun] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Experiment name cannot be empty")
    
    def add_run(self, parameters: List[Parameter]) -> ExperimentRun:
        """Add a new run to this experiment."""
        run_number = len(self.runs) + 1
        run = ExperimentRun(
            experiment_id=self.id,
            run_number=run_number,
            parameters=parameters
        )
        self.runs.append(run)
        self.updated_at = datetime.now()
        return run
    
    def get_run(self, run_id: str) -> Optional[ExperimentRun]:
        """Get a specific run by ID."""
        for run in self.runs:
            if run.id == run_id:
                return run
        return None
    
    def get_run_by_number(self, run_number: int) -> Optional[ExperimentRun]:
        """Get a specific run by run number."""
        for run in self.runs:
            if run.run_number == run_number:
                return run
        return None
    
    def get_best_run(self, metric_name: str, higher_is_better: bool = True) -> Optional[ExperimentRun]:
        """Get the best run based on a specific metric."""
        if not self.runs:
            return None
            
        best_run = None
        best_value = None
        
        for run in self.runs:
            if run.status != ExperimentStatus.COMPLETED:
                continue
                
            if metric_name in run.metrics:
                value = run.metrics[metric_name].value
                
                if best_value is None or (higher_is_better and value > best_value) or (not higher_is_better and value < best_value):
                    best_value = value
                    best_run = run
                    
        return best_run


@dataclass
class ExperimentComparison(BaseEntity):
    """A comparison between multiple experiment runs."""
    
    name: str = ""
    description: Optional[str] = None
    experiment_ids: List[str] = field(default_factory=list)
    run_ids: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Comparison name cannot be empty")
    
    def add_experiment(self, experiment_id: str) -> None:
        """Add an experiment to the comparison."""
        if experiment_id not in self.experiment_ids:
            self.experiment_ids.append(experiment_id)
            self.updated_at = datetime.now()
    
    def add_run(self, run_id: str) -> None:
        """Add a specific run to the comparison."""
        if run_id not in self.run_ids:
            self.run_ids.append(run_id)
            self.updated_at = datetime.now()
    
    def add_metric(self, metric_name: str) -> None:
        """Add a metric to compare across runs."""
        if metric_name not in self.metrics:
            self.metrics.append(metric_name)
            self.updated_at = datetime.now()