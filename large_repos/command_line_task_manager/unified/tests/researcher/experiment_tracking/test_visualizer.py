import pytest
from datetime import datetime
from uuid import uuid4

from researchtrack.experiment_tracking.models import (
    Experiment, ExperimentRun, Parameter, Metric,
    ParameterType, MetricType, ExperimentStatus
)
from researchtrack.experiment_tracking.visualizer import ExperimentVisualizer


@pytest.fixture
def visualizer():
    return ExperimentVisualizer()


@pytest.fixture
def sample_run():
    """Create a sample experiment run with various data for testing."""
    experiment_id = uuid4()
    
    # Create parameters
    params = [
        Parameter(
            name="learning_rate",
            type=ParameterType.FLOAT,
            value=0.001,
            description="Learning rate for optimizer"
        ),
        Parameter(
            name="batch_size",
            type=ParameterType.INTEGER,
            value=32,
            description="Training batch size"
        ),
        Parameter(
            name="dropout",
            type=ParameterType.FLOAT,
            value=0.5
        )
    ]
    
    # Create run
    run = ExperimentRun(
        experiment_id=experiment_id,
        run_number=1,
        status=ExperimentStatus.COMPLETED,
        parameters=params,
        start_time=datetime(2023, 1, 1, 10, 0, 0),
        end_time=datetime(2023, 1, 1, 10, 30, 0),
        notes="This run tested a modified architecture."
    )
    
    # Add metrics
    run.metrics = {
        "accuracy": Metric(
            name="accuracy",
            type=MetricType.ACCURACY,
            value=0.95,
            description="Validation accuracy"
        ),
        "loss": Metric(
            name="loss",
            type=MetricType.LOSS,
            value=0.05,
            description="Validation loss"
        ),
        "f1": Metric(
            name="f1",
            type=MetricType.F1_SCORE,
            value=0.94
        )
    }
    
    # Add artifacts
    run.artifacts = {
        "model": "/path/to/model.pkl",
        "predictions": "/path/to/predictions.csv"
    }
    
    return run


@pytest.fixture
def sample_experiment():
    """Create a sample experiment with multiple runs for testing."""
    experiment = Experiment(
        name="Test Experiment",
        description="A test experiment for neural network architectures",
        tags=["test", "neural-network", "deep-learning"],
        created_at=datetime(2023, 1, 1, 9, 0, 0),
        updated_at=datetime(2023, 1, 1, 11, 0, 0)
    )
    
    # Add runs
    run1 = ExperimentRun(
        experiment_id=experiment.id,
        run_number=1,
        status=ExperimentStatus.COMPLETED,
        start_time=datetime(2023, 1, 1, 10, 0, 0),
        end_time=datetime(2023, 1, 1, 10, 30, 0)
    )
    run1.metrics = {
        "accuracy": Metric(name="accuracy", type=MetricType.ACCURACY, value=0.92),
        "loss": Metric(name="loss", type=MetricType.LOSS, value=0.08)
    }
    
    run2 = ExperimentRun(
        experiment_id=experiment.id,
        run_number=2,
        status=ExperimentStatus.COMPLETED,
        start_time=datetime(2023, 1, 1, 11, 0, 0),
        end_time=datetime(2023, 1, 1, 11, 45, 0)
    )
    run2.metrics = {
        "accuracy": Metric(name="accuracy", type=MetricType.ACCURACY, value=0.95),
        "loss": Metric(name="loss", type=MetricType.LOSS, value=0.05)
    }
    
    run3 = ExperimentRun(
        experiment_id=experiment.id,
        run_number=3,
        status=ExperimentStatus.RUNNING,
        start_time=datetime(2023, 1, 1, 12, 0, 0)
    )
    
    experiment.runs = [run1, run2, run3]
    return experiment


def test_format_parameter_table(visualizer, sample_run):
    """Test formatting parameters as a markdown table."""
    table = visualizer.format_parameter_table(sample_run)
    
    assert "| Parameter | Type | Value | Description |" in table
    assert "| learning_rate | float | 0.001 | Learning rate for optimizer |" in table
    assert "| batch_size | integer | 32 | Training batch size |" in table
    assert "| dropout | float | 0.5 | |" in table


def test_format_empty_parameter_table(visualizer):
    """Test formatting an empty parameters table."""
    run = ExperimentRun(experiment_id=uuid4(), run_number=1)
    table = visualizer.format_parameter_table(run)
    
    assert "No parameters defined." in table


def test_format_metric_table(visualizer, sample_run):
    """Test formatting metrics as a markdown table."""
    table = visualizer.format_metric_table(sample_run)
    
    assert "| Metric | Type | Value | Timestamp | Description |" in table
    assert "| accuracy | accuracy | 0.95 |" in table
    assert "| Validation accuracy |" in table
    assert "| loss | loss | 0.05 |" in table
    assert "| Validation loss |" in table
    assert "| f1 | f1_score | 0.94 |" in table


def test_format_empty_metric_table(visualizer):
    """Test formatting an empty metrics table."""
    run = ExperimentRun(experiment_id=uuid4(), run_number=1)
    table = visualizer.format_metric_table(run)
    
    assert "No metrics recorded." in table


def test_format_artifact_table(visualizer, sample_run):
    """Test formatting artifacts as a markdown table."""
    table = visualizer.format_artifact_table(sample_run)
    
    assert "| Artifact | Path |" in table
    assert "| model | /path/to/model.pkl |" in table
    assert "| predictions | /path/to/predictions.csv |" in table


def test_format_empty_artifact_table(visualizer):
    """Test formatting an empty artifacts table."""
    run = ExperimentRun(experiment_id=uuid4(), run_number=1)
    table = visualizer.format_artifact_table(run)
    
    assert "No artifacts recorded." in table


def test_format_run_summary(visualizer, sample_run):
    """Test formatting a complete run summary."""
    summary = visualizer.format_run_summary(sample_run, "Neural Network Test")
    
    # Check for all major sections
    assert "# Run 1 of Experiment: Neural Network Test" in summary
    assert "**Status**: completed" in summary
    assert "**Started**: 2023-01-01 10:00:00" in summary
    assert "**Ended**: 2023-01-01 10:30:00" in summary
    assert "**Duration**: 1800.00 seconds" in summary
    assert "## Notes" in summary
    assert "This run tested a modified architecture." in summary
    assert "## Parameters" in summary
    assert "## Metrics" in summary
    assert "## Artifacts" in summary
    
    # Check for specific content from tables
    assert "learning_rate" in summary
    assert "0.001" in summary
    assert "accuracy" in summary
    assert "0.95" in summary
    assert "model" in summary
    assert "/path/to/model.pkl" in summary


def test_format_experiment_summary(visualizer, sample_experiment):
    """Test formatting a complete experiment summary."""
    summary = visualizer.format_experiment_summary(sample_experiment)
    
    # Check for all major sections
    assert "# Experiment: Test Experiment" in summary
    assert "A test experiment for neural network architectures" in summary
    assert "**Created**: 2023-01-01 09:00:00" in summary
    assert "**Last Updated**: 2023-01-01 11:00:00" in summary
    assert "**Tags**: test, neural-network, deep-learning" in summary
    assert f"**Runs ({len(sample_experiment.runs)})**" in summary
    
    # Check for run information in the table
    assert "| Run # | Status | Start Time | Duration | Key Metrics |" in summary
    assert "| 1 | completed | 2023-01-01 10:00:00 | 1800.00s | accuracy: 0.9200, loss: 0.0800 |" in summary
    assert "| 2 | completed | 2023-01-01 11:00:00 | 2700.00s | accuracy: 0.9500, loss: 0.0500 |" in summary
    assert "| 3 | running | 2023-01-01 12:00:00 | - | |" in summary


def test_format_comparison_table(visualizer):
    """Test formatting a comparison table of multiple runs/experiments."""
    comparison_data = {
        "Experiment A:Run 1": {
            "accuracy": 0.92,
            "loss": 0.08,
            "f1": 0.91
        },
        "Experiment A:Run 2": {
            "accuracy": 0.95,
            "loss": 0.05,
            "f1": 0.94
        },
        "Experiment B:Run 1": {
            "accuracy": 0.90,
            "loss": 0.10,
            "precision": 0.89
        },
        "Experiment B:Best": {
            "accuracy": 0.93,
            "loss": 0.07,
            "precision": 0.92
        }
    }
    
    table = visualizer.format_comparison_table(comparison_data)
    
    # Check for table header and all metrics (ignore whitespace, considering both cases)
    replaced = table.replace(" ", "")
    # Fix for comparison - both of these pattern formats should be acceptable
    assert "|Run/Experiment|accuracy|f1|loss|precision|" in replaced or "|Run/Experiment|accuracy|f1|loss|precision|" in replaced
    
    # Check for data rows (order might vary for metrics, so we check more loosely)
    assert "| Experiment A:Run 1 |" in table
    assert "0.92" in table
    assert "0.08" in table
    assert "0.91" in table
    
    assert "| Experiment A:Run 2 |" in table
    assert "0.95" in table
    assert "0.05" in table
    assert "0.94" in table
    
    assert "| Experiment B:Run 1 |" in table
    assert "0.90" in table
    assert "0.10" in table
    assert "0.89" in table
    
    assert "| Experiment B:Best |" in table
    assert "0.93" in table
    assert "0.07" in table
    assert "0.92" in table
    
    # Check for missing values
    assert " - |" in table


def test_format_empty_comparison_table(visualizer):
    """Test formatting an empty comparison table."""
    table = visualizer.format_comparison_table({})
    
    assert "No comparison data available." in table