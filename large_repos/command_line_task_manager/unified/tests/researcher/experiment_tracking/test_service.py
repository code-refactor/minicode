import pytest
from uuid import UUID, uuid4

from researchtrack.experiment_tracking.models import (
    Experiment, ExperimentRun, Parameter, Metric, ExperimentComparison,
    ParameterType, MetricType, ExperimentStatus
)
from researchtrack.experiment_tracking.storage import InMemoryExperimentStorage
from researchtrack.experiment_tracking.service import ExperimentService


@pytest.fixture
def storage():
    return InMemoryExperimentStorage()


@pytest.fixture
def service(storage):
    return ExperimentService(storage)


def test_create_experiment(service):
    """Test creating an experiment through the service."""
    experiment = service.create_experiment(
        name="Test Experiment",
        description="A test experiment",
        tags=["test", "experiment"]
    )
    
    assert isinstance(experiment.id, UUID)
    assert experiment.name == "Test Experiment"
    assert experiment.description == "A test experiment"
    assert experiment.tags == ["test", "experiment"]
    assert len(experiment.runs) == 0


def test_get_experiment(service):
    """Test retrieving an experiment through the service."""
    experiment = service.create_experiment(name="Test Experiment")
    retrieved = service.get_experiment(experiment.id)
    
    assert retrieved is not None
    assert retrieved.id == experiment.id
    assert retrieved.name == "Test Experiment"


def test_get_experiment_by_name(service):
    """Test retrieving an experiment by name through the service."""
    service.create_experiment(name="Test Experiment")
    retrieved = service.get_experiment_by_name("Test Experiment")
    
    assert retrieved is not None
    assert retrieved.name == "Test Experiment"
    
    # Non-existent name
    assert service.get_experiment_by_name("Nonexistent") is None


def test_update_experiment(service):
    """Test updating an experiment through the service."""
    experiment = service.create_experiment(name="Original Name")
    experiment.name = "Updated Name"
    updated = service.update_experiment(experiment)
    
    assert updated.name == "Updated Name"
    
    # Verify the update is persisted
    retrieved = service.get_experiment(experiment.id)
    assert retrieved.name == "Updated Name"


def test_delete_experiment(service):
    """Test deleting an experiment through the service."""
    experiment = service.create_experiment(name="Test Experiment")
    result = service.delete_experiment(experiment.id)
    
    assert result is True
    assert service.get_experiment(experiment.id) is None


def test_list_experiments(service):
    """Test listing experiments through the service."""
    service.create_experiment(name="Experiment 1")
    service.create_experiment(name="Experiment 2")
    
    experiments = service.list_experiments()
    
    assert len(experiments) == 2
    assert any(e.name == "Experiment 1" for e in experiments)
    assert any(e.name == "Experiment 2" for e in experiments)


def test_list_experiments_by_task(service):
    """Test listing experiments filtered by task ID through the service."""
    task_id = uuid4()
    experiment = service.create_experiment(name="Task Experiment", task_id=task_id)
    service.create_experiment(name="Other Experiment")
    
    experiments = service.list_experiments(task_id)
    
    assert len(experiments) == 1
    assert experiments[0].id == experiment.id


def test_add_parameter(service):
    """Test creating a parameter through the service."""
    param = service.add_parameter(
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


def test_add_metric(service):
    """Test creating a metric through the service."""
    metric = service.add_metric(
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


def test_create_experiment_run(service):
    """Test creating an experiment run through the service."""
    experiment = service.create_experiment(name="Test Experiment")
    param = service.add_parameter(name="p1", type=ParameterType.FLOAT, value=0.1)
    
    run = service.create_experiment_run(experiment.id, [param])
    
    assert run is not None
    assert run.experiment_id == experiment.id
    assert run.run_number == 1
    assert len(run.parameters) == 1
    assert run.parameters[0].name == "p1"
    
    # Verify the run is added to the experiment
    experiment = service.get_experiment(experiment.id)
    assert len(experiment.runs) == 1
    assert experiment.runs[0].id == run.id


def test_create_experiment_run_nonexistent_experiment(service):
    """Test creating a run for a non-existent experiment."""
    param = service.add_parameter(name="p1", type=ParameterType.FLOAT, value=0.1)
    run = service.create_experiment_run(uuid4(), [param])
    
    assert run is None


def test_get_experiment_run(service):
    """Test retrieving an experiment run through the service."""
    experiment = service.create_experiment(name="Test Experiment")
    run = service.create_experiment_run(experiment.id, [])
    
    retrieved = service.get_experiment_run(run.id)
    
    assert retrieved is not None
    assert retrieved.id == run.id
    assert retrieved.experiment_id == experiment.id


def test_run_lifecycle(service):
    """Test the complete lifecycle of an experiment run."""
    experiment = service.create_experiment(name="Test Experiment")
    param = service.add_parameter(name="p1", type=ParameterType.FLOAT, value=0.1)
    
    # Create a run
    run = service.create_experiment_run(experiment.id, [param])
    assert run.status == ExperimentStatus.PLANNED
    
    # Start the run
    run = service.start_run(run.id)
    assert run.status == ExperimentStatus.RUNNING
    assert run.start_time is not None
    
    # Add a metric
    run = service.add_run_metric(
        run.id, "accuracy", MetricType.ACCURACY, 0.9, "Validation accuracy"
    )
    assert "accuracy" in run.metrics
    assert run.metrics["accuracy"].value == 0.9
    
    # Add an artifact
    run = service.add_run_artifact(run.id, "model", "/path/to/model.pkl")
    assert "model" in run.artifacts
    assert run.artifacts["model"] == "/path/to/model.pkl"
    
    # Update notes
    run = service.update_run_notes(run.id, "This run performed well.")
    assert run.notes == "This run performed well."
    
    # Complete the run
    run = service.complete_run(run.id)
    assert run.status == ExperimentStatus.COMPLETED
    assert run.end_time is not None
    assert run.duration() is not None


def test_failed_and_aborted_runs(service):
    """Test marking runs as failed or aborted."""
    experiment = service.create_experiment(name="Test Experiment")
    
    # Create and start a run that will fail
    failed_run = service.create_experiment_run(experiment.id, [])
    service.start_run(failed_run.id)
    failed_run = service.fail_run(failed_run.id)
    
    assert failed_run.status == ExperimentStatus.FAILED
    assert failed_run.end_time is not None
    
    # Create and start a run that will be aborted
    aborted_run = service.create_experiment_run(experiment.id, [])
    service.start_run(aborted_run.id)
    aborted_run = service.abort_run(aborted_run.id)
    
    assert aborted_run.status == ExperimentStatus.ABORTED
    assert aborted_run.end_time is not None


def test_get_best_run(service):
    """Test getting the best run for an experiment."""
    experiment = service.create_experiment(name="Test Experiment")
    
    # Create several runs with different metrics
    run1 = service.create_experiment_run(experiment.id, [])
    service.start_run(run1.id)
    service.add_run_metric(run1.id, "accuracy", MetricType.ACCURACY, 0.9)
    service.complete_run(run1.id)
    
    run2 = service.create_experiment_run(experiment.id, [])
    service.start_run(run2.id)
    service.add_run_metric(run2.id, "accuracy", MetricType.ACCURACY, 0.95)
    service.complete_run(run2.id)
    
    run3 = service.create_experiment_run(experiment.id, [])
    service.start_run(run3.id)
    service.add_run_metric(run3.id, "accuracy", MetricType.ACCURACY, 0.85)
    service.complete_run(run3.id)
    
    # Get the best run by accuracy (higher is better)
    best = service.get_best_run(experiment.id, "accuracy", higher_is_better=True)
    
    assert best is not None
    assert best.id == run2.id
    assert best.metrics["accuracy"].value == 0.95


def test_create_comparison(service):
    """Test creating an experiment comparison through the service."""
    experiment1 = service.create_experiment(name="Experiment 1")
    experiment2 = service.create_experiment(name="Experiment 2")
    
    comparison = service.create_comparison(
        name="Test Comparison",
        description="A test comparison",
        experiment_ids=[experiment1.id, experiment2.id],
        metrics=["accuracy", "loss"]
    )
    
    assert isinstance(comparison.id, UUID)
    assert comparison.name == "Test Comparison"
    assert comparison.description == "A test comparison"
    assert len(comparison.experiment_ids) == 2
    assert experiment1.id in comparison.experiment_ids
    assert experiment2.id in comparison.experiment_ids
    assert comparison.metrics == ["accuracy", "loss"]


def test_get_comparison(service):
    """Test retrieving a comparison through the service."""
    comparison = service.create_comparison(name="Test Comparison")
    retrieved = service.get_comparison(comparison.id)
    
    assert retrieved is not None
    assert retrieved.id == comparison.id
    assert retrieved.name == "Test Comparison"


def test_update_comparison(service):
    """Test updating a comparison through the service."""
    comparison = service.create_comparison(name="Original Name")
    comparison.name = "Updated Name"
    updated = service.update_comparison(comparison)
    
    assert updated.name == "Updated Name"
    
    # Verify the update is persisted
    retrieved = service.get_comparison(comparison.id)
    assert retrieved.name == "Updated Name"


def test_delete_comparison(service):
    """Test deleting a comparison through the service."""
    comparison = service.create_comparison(name="Test Comparison")
    result = service.delete_comparison(comparison.id)
    
    assert result is True
    assert service.get_comparison(comparison.id) is None


def test_list_comparisons(service):
    """Test listing comparisons through the service."""
    service.create_comparison(name="Comparison 1")
    service.create_comparison(name="Comparison 2")
    
    comparisons = service.list_comparisons()
    
    assert len(comparisons) == 2
    assert any(c.name == "Comparison 1" for c in comparisons)
    assert any(c.name == "Comparison 2" for c in comparisons)


def test_get_comparison_data(service):
    """Test getting comparison data through the service."""
    # Create experiments and runs with metrics
    experiment1 = service.create_experiment(name="Experiment 1")
    run1 = service.create_experiment_run(experiment1.id, [])
    service.start_run(run1.id)
    service.add_run_metric(run1.id, "accuracy", MetricType.ACCURACY, 0.9)
    service.add_run_metric(run1.id, "loss", MetricType.LOSS, 0.1)
    service.complete_run(run1.id)
    
    experiment2 = service.create_experiment(name="Experiment 2")
    run2 = service.create_experiment_run(experiment2.id, [])
    service.start_run(run2.id)
    service.add_run_metric(run2.id, "accuracy", MetricType.ACCURACY, 0.85)
    service.add_run_metric(run2.id, "loss", MetricType.LOSS, 0.15)
    service.complete_run(run2.id)
    
    # Create a comparison
    comparison = service.create_comparison(
        name="Test Comparison",
        run_ids=[run1.id, run2.id],
        metrics=["accuracy", "loss"]
    )
    
    # Get comparison data
    data = service.get_comparison_data(comparison.id)
    
    assert len(data) == 2
    assert "Experiment 1:Run 1" in data
    assert "Experiment 2:Run 1" in data
    
    assert data["Experiment 1:Run 1"]["accuracy"] == 0.9
    assert data["Experiment 1:Run 1"]["loss"] == 0.1
    assert data["Experiment 2:Run 1"]["accuracy"] == 0.85
    assert data["Experiment 2:Run 1"]["loss"] == 0.15