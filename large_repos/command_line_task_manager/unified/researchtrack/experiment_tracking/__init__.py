"""
Experiment Tracking module for research documentation.

This module provides functionality for tracking experiments, their parameters,
metrics, and results to support reproducible research.
"""

from researchtrack.experiment_tracking.models import (
    Experiment, ExperimentRun, ExperimentComparison,
    Parameter, Metric, ParameterType, MetricType, ExperimentStatus
)
from researchtrack.experiment_tracking.storage import (
    ExperimentStorageInterface, InMemoryExperimentStorage
)
from researchtrack.experiment_tracking.service import ExperimentService
from researchtrack.experiment_tracking.visualizer import ExperimentVisualizer

__all__ = [
    # Models
    "Experiment", "ExperimentRun", "ExperimentComparison",
    "Parameter", "Metric", "ParameterType", "MetricType", "ExperimentStatus",
    
    # Storage
    "ExperimentStorageInterface", "InMemoryExperimentStorage",
    
    # Service
    "ExperimentService",
    
    # Visualizer
    "ExperimentVisualizer",
]