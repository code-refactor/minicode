import pytest
from datetime import datetime
from uuid import UUID, uuid4

from researchtrack.experiment_tracking.models import (
    Experiment, ExperimentRun, Parameter, Metric,
    ParameterType, MetricType, ExperimentStatus, ExperimentComparison
)


def test_parameter_creation():
    """Test creating a parameter."""
    param = Parameter(
        name="learning_rate",
        type=ParameterType.FLOAT,
        value=0.001,
        description="Learning rate for optimizer"
    )
    
    assert isinstance(param.id, UUID)
    assert param.name == "learning_rate"
    assert param.type == ParameterType.FLOAT
    assert param.value == 0.001
    assert param.description == "Learning rate for optimizer"


def test_metric_creation():
    """Test creating a metric."""
    metric = Metric(
        name="accuracy",
        type=MetricType.ACCURACY,
        value=0.95,
        description="Validation accuracy"
    )
    
    assert isinstance(metric.id, UUID)
    assert metric.name == "accuracy"
    assert metric.type == MetricType.ACCURACY
    assert metric.value == 0.95
    assert metric.description == "Validation accuracy"
    assert isinstance(metric.timestamp, datetime)


def test_experiment_run_creation():
    """Test creating an experiment run."""
    experiment_id = uuid4()
    param1 = Parameter(name="p1", type=ParameterType.FLOAT, value=0.1)
    param2 = Parameter(name="p2", type=ParameterType.INTEGER, value=10)
    
    run = ExperimentRun(
        experiment_id=experiment_id,
        run_number=1,
        parameters=[param1, param2]
    )
    
    assert isinstance(run.id, UUID)
    assert run.experiment_id == experiment_id
    assert run.run_number == 1
    assert run.status == ExperimentStatus.PLANNED
    assert len(run.parameters) == 2
    assert run.metrics == {}
    assert run.artifacts == {}
    assert run.start_time is None
    assert run.end_time is None
    assert run.notes is None
    assert run.duration() is None


def test_experiment_run_duration():
    """Test calculating experiment run duration."""
    # Create a run with start and end time
    run = ExperimentRun(
        experiment_id=uuid4(),
        run_number=1,
        start_time=datetime(2023, 1, 1, 10, 0, 0),
        end_time=datetime(2023, 1, 1, 10, 0, 30)
    )
    
    # Duration should be 30 seconds
    assert run.duration() == 30.0
    
    # Run with no end time should return None
    run.end_time = None
    assert run.duration() is None
    
    # Run with no start time should return None
    run.start_time = None
    run.end_time = datetime(2023, 1, 1, 10, 0, 30)
    assert run.duration() is None


def test_experiment_creation():
    """Test creating an experiment."""
    experiment = Experiment(
        name="Test Experiment",
        description="A test experiment",
        tags=["test", "experiment"]
    )
    
    assert isinstance(experiment.id, UUID)
    assert experiment.name == "Test Experiment"
    assert experiment.description == "A test experiment"
    assert experiment.tags == ["test", "experiment"]
    assert experiment.task_id is None
    assert experiment.dataset_id is None
    assert experiment.environment_id is None
    assert isinstance(experiment.created_at, datetime)
    assert isinstance(experiment.updated_at, datetime)
    assert len(experiment.runs) == 0


def test_experiment_add_run():
    """Test adding a run to an experiment."""
    experiment = Experiment(name="Test Experiment")
    param = Parameter(name="p1", type=ParameterType.FLOAT, value=0.1)
    
    # Add a run
    run = experiment.add_run([param])
    
    assert isinstance(run, ExperimentRun)
    assert run.experiment_id == experiment.id
    assert run.run_number == 1
    assert len(run.parameters) == 1
    assert len(experiment.runs) == 1
    assert experiment.runs[0].id == run.id
    
    # Add another run
    run2 = experiment.add_run([])
    assert run2.run_number == 2
    assert len(experiment.runs) == 2


def test_experiment_get_run():
    """Test getting a run from an experiment."""
    experiment = Experiment(name="Test Experiment")
    run = experiment.add_run([])
    
    # Get by ID
    retrieved = experiment.get_run(run.id)
    assert retrieved is not None
    assert retrieved.id == run.id
    
    # Get by run number
    retrieved = experiment.get_run_by_number(1)
    assert retrieved is not None
    assert retrieved.run_number == 1
    
    # Get non-existent run
    assert experiment.get_run(uuid4()) is None
    assert experiment.get_run_by_number(99) is None


def test_experiment_get_best_run():
    """Test getting the best run from an experiment."""
    experiment = Experiment(name="Test Experiment")
    
    # Add runs with different metrics
    run1 = experiment.add_run([])
    run1.status = ExperimentStatus.COMPLETED
    run1.metrics["accuracy"] = Metric(name="accuracy", type=MetricType.ACCURACY, value=0.9)
    run1.metrics["loss"] = Metric(name="loss", type=MetricType.LOSS, value=0.1)
    
    run2 = experiment.add_run([])
    run2.status = ExperimentStatus.COMPLETED
    run2.metrics["accuracy"] = Metric(name="accuracy", type=MetricType.ACCURACY, value=0.8)
    run2.metrics["loss"] = Metric(name="loss", type=MetricType.LOSS, value=0.2)
    
    run3 = experiment.add_run([])
    run3.status = ExperimentStatus.RUNNING  # Not completed, should be ignored
    run3.metrics["accuracy"] = Metric(name="accuracy", type=MetricType.ACCURACY, value=0.95)
    
    # Best run by accuracy (higher is better)
    best = experiment.get_best_run("accuracy", higher_is_better=True)
    assert best is not None
    assert best.id == run1.id
    assert best.metrics["accuracy"].value == 0.9
    
    # Best run by loss (lower is better)
    best = experiment.get_best_run("loss", higher_is_better=False)
    assert best is not None
    assert best.id == run1.id
    assert best.metrics["loss"].value == 0.1
    
    # Metric not present in any completed run
    assert experiment.get_best_run("nonexistent") is None
    
    # No completed runs
    experiment = Experiment(name="Empty Experiment")
    assert experiment.get_best_run("accuracy") is None


def test_experiment_comparison_creation():
    """Test creating an experiment comparison."""
    comparison = ExperimentComparison(
        name="Test Comparison",
        description="A test comparison",
        experiment_ids=[uuid4(), uuid4()],
        run_ids=[uuid4(), uuid4()],
        metrics=["accuracy", "loss"]
    )
    
    assert isinstance(comparison.id, UUID)
    assert comparison.name == "Test Comparison"
    assert comparison.description == "A test comparison"
    assert len(comparison.experiment_ids) == 2
    assert len(comparison.run_ids) == 2
    assert comparison.metrics == ["accuracy", "loss"]
    assert isinstance(comparison.created_at, datetime)


def test_experiment_comparison_add_methods():
    """Test adding items to an experiment comparison."""
    comparison = ExperimentComparison(name="Test Comparison")
    
    # Add experiments
    exp_id1 = uuid4()
    exp_id2 = uuid4()
    comparison.add_experiment(exp_id1)
    comparison.add_experiment(exp_id2)
    assert len(comparison.experiment_ids) == 2
    assert exp_id1 in comparison.experiment_ids
    assert exp_id2 in comparison.experiment_ids
    
    # Add duplicate experiment (should not add)
    comparison.add_experiment(exp_id1)
    assert len(comparison.experiment_ids) == 2
    
    # Add runs
    run_id1 = uuid4()
    run_id2 = uuid4()
    comparison.add_run(run_id1)
    comparison.add_run(run_id2)
    assert len(comparison.run_ids) == 2
    assert run_id1 in comparison.run_ids
    assert run_id2 in comparison.run_ids
    
    # Add metrics
    comparison.add_metric("accuracy")
    comparison.add_metric("loss")
    assert len(comparison.metrics) == 2
    assert "accuracy" in comparison.metrics
    assert "loss" in comparison.metrics
    
    # Add duplicate metric (should not add)
    comparison.add_metric("accuracy")
    assert len(comparison.metrics) == 2