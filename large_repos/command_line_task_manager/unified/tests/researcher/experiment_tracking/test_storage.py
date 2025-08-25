import pytest
from uuid import UUID, uuid4

from researchtrack.experiment_tracking.models import (
    Experiment, ExperimentRun, Parameter, Metric, ExperimentComparison,
    ParameterType, MetricType, ExperimentStatus
)
from researchtrack.experiment_tracking.storage import InMemoryExperimentStorage


@pytest.fixture
def storage():
    """Create a fresh in-memory storage for each test."""
    return InMemoryExperimentStorage()


@pytest.fixture
def sample_experiment():
    """Create a sample experiment for testing."""
    return Experiment(
        name="Test Experiment",
        description="A test experiment",
        tags=["test", "experiment"]
    )


@pytest.fixture
def sample_run(sample_experiment):
    """Create a sample run for testing."""
    param = Parameter(name="p1", type=ParameterType.FLOAT, value=0.1)
    run = ExperimentRun(
        experiment_id=sample_experiment.id,
        run_number=1,
        parameters=[param]
    )
    return run


@pytest.fixture
def sample_comparison():
    """Create a sample comparison for testing."""
    return ExperimentComparison(
        name="Test Comparison",
        description="A test comparison",
        metrics=["accuracy", "loss"]
    )


def test_create_experiment(storage, sample_experiment):
    """Test creating an experiment in storage."""
    created = storage.create_experiment(sample_experiment)
    
    assert created.id == sample_experiment.id
    assert created.name == "Test Experiment"
    assert created.description == "A test experiment"
    assert created.tags == ["test", "experiment"]


def test_get_experiment(storage, sample_experiment):
    """Test retrieving an experiment from storage."""
    storage.create_experiment(sample_experiment)
    retrieved = storage.get_experiment(sample_experiment.id)
    
    assert retrieved is not None
    assert retrieved.id == sample_experiment.id
    assert retrieved.name == "Test Experiment"


def test_get_nonexistent_experiment(storage):
    """Test retrieving an experiment that doesn't exist."""
    non_existent_id = uuid4()
    retrieved = storage.get_experiment(non_existent_id)
    
    assert retrieved is None


def test_update_experiment(storage, sample_experiment):
    """Test updating an experiment in storage."""
    created = storage.create_experiment(sample_experiment)
    created.name = "Updated Experiment"
    updated = storage.update_experiment(created)
    
    assert updated.name == "Updated Experiment"
    
    # Verify the update is persisted
    retrieved = storage.get_experiment(sample_experiment.id)
    assert retrieved.name == "Updated Experiment"


def test_update_nonexistent_experiment(storage):
    """Test updating an experiment that doesn't exist."""
    experiment = Experiment(name="Nonexistent Experiment")
    updated = storage.update_experiment(experiment)
    
    assert updated is None


def test_delete_experiment(storage, sample_experiment):
    """Test deleting an experiment from storage."""
    storage.create_experiment(sample_experiment)
    result = storage.delete_experiment(sample_experiment.id)
    
    assert result is True
    assert storage.get_experiment(sample_experiment.id) is None


def test_delete_nonexistent_experiment(storage):
    """Test deleting an experiment that doesn't exist."""
    non_existent_id = uuid4()
    result = storage.delete_experiment(non_existent_id)
    
    assert result is False


def test_list_experiments(storage, sample_experiment):
    """Test listing all experiments in storage."""
    storage.create_experiment(sample_experiment)
    another_exp = Experiment(name="Another Experiment")
    storage.create_experiment(another_exp)
    
    experiments = storage.list_experiments()
    
    assert len(experiments) == 2
    assert any(e.id == sample_experiment.id for e in experiments)
    assert any(e.id == another_exp.id for e in experiments)


def test_list_experiments_by_task(storage, sample_experiment):
    """Test listing experiments filtered by task ID."""
    task_id = uuid4()
    sample_experiment.task_id = task_id
    storage.create_experiment(sample_experiment)
    
    # Another experiment with a different task ID
    another_exp = Experiment(name="Another Experiment", task_id=uuid4())
    storage.create_experiment(another_exp)
    
    # Another experiment with no task ID
    third_exp = Experiment(name="Third Experiment")
    storage.create_experiment(third_exp)
    
    # List experiments for the specified task
    experiments = storage.list_experiments(task_id)
    
    assert len(experiments) == 1
    assert experiments[0].id == sample_experiment.id


def test_get_experiment_by_name(storage, sample_experiment):
    """Test retrieving an experiment by name."""
    storage.create_experiment(sample_experiment)
    retrieved = storage.get_experiment_by_name("Test Experiment")
    
    assert retrieved is not None
    assert retrieved.id == sample_experiment.id
    
    # Non-existent name
    assert storage.get_experiment_by_name("Nonexistent") is None


def test_create_run(storage, sample_experiment, sample_run):
    """Test creating a run in storage."""
    storage.create_experiment(sample_experiment)
    created = storage.create_run(sample_experiment.id, sample_run)
    
    assert created is not None
    assert created.id == sample_run.id
    assert created.experiment_id == sample_experiment.id
    
    # Verify the run is added to the experiment
    experiment = storage.get_experiment(sample_experiment.id)
    assert len(experiment.runs) == 1
    assert experiment.runs[0].id == sample_run.id


def test_create_run_nonexistent_experiment(storage, sample_run):
    """Test creating a run for a non-existent experiment."""
    non_existent_id = uuid4()
    created = storage.create_run(non_existent_id, sample_run)
    
    assert created is None


def test_get_run(storage, sample_experiment, sample_run):
    """Test retrieving a run from storage."""
    storage.create_experiment(sample_experiment)
    storage.create_run(sample_experiment.id, sample_run)
    retrieved = storage.get_run(sample_run.id)
    
    assert retrieved is not None
    assert retrieved.id == sample_run.id
    assert retrieved.experiment_id == sample_experiment.id


def test_update_run(storage, sample_experiment, sample_run):
    """Test updating a run in storage."""
    storage.create_experiment(sample_experiment)
    storage.create_run(sample_experiment.id, sample_run)
    
    # Update the run
    sample_run.status = ExperimentStatus.RUNNING
    updated = storage.update_run(sample_run)
    
    assert updated.status == ExperimentStatus.RUNNING
    
    # Verify the update is persisted
    retrieved = storage.get_run(sample_run.id)
    assert retrieved.status == ExperimentStatus.RUNNING
    
    # Verify the run is updated in the experiment's runs list
    experiment = storage.get_experiment(sample_experiment.id)
    assert experiment.runs[0].status == ExperimentStatus.RUNNING


def test_update_nonexistent_run(storage):
    """Test updating a run that doesn't exist."""
    run = ExperimentRun(experiment_id=uuid4(), run_number=1)
    updated = storage.update_run(run)
    
    assert updated is None


def test_delete_run(storage, sample_experiment, sample_run):
    """Test deleting a run from storage."""
    storage.create_experiment(sample_experiment)
    storage.create_run(sample_experiment.id, sample_run)
    result = storage.delete_run(sample_run.id)
    
    assert result is True
    assert storage.get_run(sample_run.id) is None
    
    # Verify the run is removed from the experiment's runs list
    experiment = storage.get_experiment(sample_experiment.id)
    assert len(experiment.runs) == 0


def test_delete_nonexistent_run(storage):
    """Test deleting a run that doesn't exist."""
    non_existent_id = uuid4()
    result = storage.delete_run(non_existent_id)
    
    assert result is False


def test_create_comparison(storage, sample_comparison):
    """Test creating a comparison in storage."""
    created = storage.create_comparison(sample_comparison)
    
    assert created.id == sample_comparison.id
    assert created.name == "Test Comparison"
    assert created.description == "A test comparison"
    assert created.metrics == ["accuracy", "loss"]


def test_get_comparison(storage, sample_comparison):
    """Test retrieving a comparison from storage."""
    storage.create_comparison(sample_comparison)
    retrieved = storage.get_comparison(sample_comparison.id)
    
    assert retrieved is not None
    assert retrieved.id == sample_comparison.id
    assert retrieved.name == "Test Comparison"


def test_update_comparison(storage, sample_comparison):
    """Test updating a comparison in storage."""
    storage.create_comparison(sample_comparison)
    
    # Update the comparison
    sample_comparison.name = "Updated Comparison"
    updated = storage.update_comparison(sample_comparison)
    
    assert updated.name == "Updated Comparison"
    
    # Verify the update is persisted
    retrieved = storage.get_comparison(sample_comparison.id)
    assert retrieved.name == "Updated Comparison"


def test_update_nonexistent_comparison(storage):
    """Test updating a comparison that doesn't exist."""
    comparison = ExperimentComparison(name="Nonexistent Comparison")
    updated = storage.update_comparison(comparison)
    
    assert updated is None


def test_delete_comparison(storage, sample_comparison):
    """Test deleting a comparison from storage."""
    storage.create_comparison(sample_comparison)
    result = storage.delete_comparison(sample_comparison.id)
    
    assert result is True
    assert storage.get_comparison(sample_comparison.id) is None


def test_delete_nonexistent_comparison(storage):
    """Test deleting a comparison that doesn't exist."""
    non_existent_id = uuid4()
    result = storage.delete_comparison(non_existent_id)
    
    assert result is False


def test_list_comparisons(storage, sample_comparison):
    """Test listing all comparisons in storage."""
    storage.create_comparison(sample_comparison)
    another_comp = ExperimentComparison(name="Another Comparison")
    storage.create_comparison(another_comp)
    
    comparisons = storage.list_comparisons()
    
    assert len(comparisons) == 2
    assert any(c.id == sample_comparison.id for c in comparisons)
    assert any(c.id == another_comp.id for c in comparisons)