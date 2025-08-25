"""
Performance tests for the Experiment Tracking module.

These tests verify that the experiment tracking functionality meets performance
requirements for large-scale experiment management.
"""

import pytest
import time
import random
from uuid import uuid4

from researchtrack.experiment_tracking import (
    ExperimentService, InMemoryExperimentStorage,
    Experiment, ExperimentRun, Parameter, Metric,
    ParameterType, MetricType, ExperimentStatus
)


@pytest.fixture
def experiment_service():
    """Create an experiment service for testing."""
    return ExperimentService(InMemoryExperimentStorage())


def create_random_parameter():
    """Create a random parameter for testing."""
    param_types = [
        (ParameterType.FLOAT, lambda: random.uniform(0.0001, 0.1)),
        (ParameterType.INTEGER, lambda: random.randint(1, 100)),
        (ParameterType.STRING, lambda: random.choice(["option1", "option2", "option3"])),
        (ParameterType.BOOLEAN, lambda: random.choice([True, False])),
    ]
    
    param_type, value_func = random.choice(param_types)
    param_names = ["learning_rate", "batch_size", "dropout", "epochs", 
                 "optimizer", "model", "weight_decay", "momentum",
                 "use_bias", "activation", "hidden_size", "num_layers"]
    
    return {
        "name": random.choice(param_names),
        "type": param_type,
        "value": value_func(),
        "description": f"Random parameter for performance testing"
    }


def create_experiment_with_runs(service, num_runs=10, params_per_run=5, metrics_per_run=5):
    """Create an experiment with multiple runs for performance testing."""
    experiment = service.create_experiment(
        name=f"Performance Test Experiment with {num_runs} runs",
        description="Experiment created for performance testing",
        tags=["performance", "test", "benchmark"]
    )
    
    runs = []
    
    # Create multiple runs with parameters and metrics
    for i in range(num_runs):
        # Create parameters
        parameters = []
        for _ in range(params_per_run):
            param_data = create_random_parameter()
            param = service.add_parameter(
                name=param_data["name"],
                type=param_data["type"],
                value=param_data["value"],
                description=param_data["description"]
            )
            parameters.append(param)
        
        # Create the run
        run = service.create_experiment_run(experiment.id, parameters)
        assert run is not None
        
        # Start the run
        run = service.start_run(run.id)
        
        # Add metrics
        metric_types = [
            (MetricType.ACCURACY, "accuracy", lambda: random.uniform(0.7, 1.0)),
            (MetricType.PRECISION, "precision", lambda: random.uniform(0.7, 1.0)),
            (MetricType.RECALL, "recall", lambda: random.uniform(0.7, 1.0)),
            (MetricType.F1_SCORE, "f1", lambda: random.uniform(0.7, 1.0)),
            (MetricType.LOSS, "loss", lambda: random.uniform(0.01, 0.5)),
            (MetricType.PERPLEXITY, "perplexity", lambda: random.uniform(1.0, 5.0)),
            (MetricType.MEAN_SQUARE_ERROR, "mse", lambda: random.uniform(0.01, 0.5)),
            (MetricType.CUSTOM, "inference_time", lambda: random.uniform(10.0, 500.0)),
        ]
        
        # Add exactly metrics_per_run metrics, repeating with numbered suffixes if needed
        for j in range(metrics_per_run):
            metric_idx = j % len(metric_types)  # Wrap around if needed
            metric_type, base_name, value_func = metric_types[metric_idx]
            
            # If we need more metrics than types, add a suffix
            suffix = f"_{j//len(metric_types) + 1}" if j >= len(metric_types) else ""
            name = f"{base_name}{suffix}"
                    
            service.add_run_metric(
                run_id=run.id,
                name=name,
                type=metric_type,
                value=value_func(),
                description=f"Random {name} metric for run {i+1}"
            )
        
        # Add an artifact
        service.add_run_artifact(
            run_id=run.id,
            name=f"model_{i+1}",
            path=f"/path/to/models/model_{i+1}.pkl"
        )
        
        # Complete the run
        run = service.complete_run(run.id)
        runs.append(run)
    
    return experiment, runs


def test_experiment_creation_performance(experiment_service):
    """Test the performance of creating an experiment with many runs."""
    start_time = time.time()
    
    experiment, runs = create_experiment_with_runs(
        experiment_service, 
        num_runs=20, 
        params_per_run=10,
        metrics_per_run=10
    )
    
    end_time = time.time()
    creation_time = end_time - start_time
    
    # Creating 20 runs with 10 parameters and 10 metrics each should be fast
    assert creation_time < 2.0, f"Experiment creation took {creation_time:.2f}s, expected < 2.0s"
    
    # Verify experiment structure
    experiment = experiment_service.get_experiment(experiment.id)
    assert len(experiment.runs) == 20
    assert all(len(run.parameters) == 10 for run in experiment.runs)
    assert all(len(run.metrics) == 10 for run in experiment.runs)


def test_best_run_query_performance(experiment_service):
    """Test the performance of querying for the best run in an experiment."""
    experiment, runs = create_experiment_with_runs(
        experiment_service, 
        num_runs=50,
        params_per_run=10,
        metrics_per_run=10
    )
    
    # Add the same metric to all runs for testing best run queries
    for i, run in enumerate(runs):
        experiment_service.add_run_metric(
            run_id=run.id,
            name="test_accuracy",
            type=MetricType.ACCURACY,
            value=0.75 + (i * 0.005)  # Gradually increasing values
        )
    
    start_time = time.time()
    
    # Query for best run by accuracy
    best_run = experiment_service.get_best_run(experiment.id, "test_accuracy")
    
    end_time = time.time()
    query_time = end_time - start_time
    
    # Best run query should be efficient
    assert query_time < 0.1, f"Best run query took {query_time:.2f}s, expected < 0.1s"
    
    # Verify best run is correct (should be the last run)
    assert best_run.id == runs[-1].id
    
    # Record performance metrics
    print(f"Best run query time for {len(runs)} runs: {query_time:.6f}s")


def test_comparison_performance(experiment_service):
    """Test the performance of creating and querying experiment comparisons."""
    # Create multiple experiments with runs
    experiment1, runs1 = create_experiment_with_runs(
        experiment_service, num_runs=10, params_per_run=5, metrics_per_run=5
    )
    
    experiment2, runs2 = create_experiment_with_runs(
        experiment_service, num_runs=10, params_per_run=5, metrics_per_run=5
    )
    
    # Add common metrics to all runs for comparison
    common_metrics = ["accuracy", "loss", "f1"]
    for i, (run_list, base_val) in enumerate([(runs1, 0.8), (runs2, 0.85)]):
        for j, run in enumerate(run_list):
            for k, metric in enumerate(common_metrics):
                experiment_service.add_run_metric(
                    run_id=run.id,
                    name=metric,
                    type=MetricType.CUSTOM,
                    value=base_val + (j * 0.01) - (k * 0.05)
                )
    
    # Measure comparison creation time
    start_time = time.time()
    
    comparison = experiment_service.create_comparison(
        name="Performance Test Comparison",
        description="Comparison created for performance testing",
        experiment_ids=[experiment1.id, experiment2.id],
        metrics=common_metrics
    )
    
    creation_time = time.time() - start_time
    
    # Comparison creation should be fast
    assert creation_time < 0.1, f"Comparison creation took {creation_time:.2f}s, expected < 0.1s"
    
    # Measure comparison data retrieval time
    start_time = time.time()
    
    comparison_data = experiment_service.get_comparison_data(comparison.id)
    
    retrieval_time = time.time() - start_time
    
    # Comparison data retrieval should be efficient
    assert retrieval_time < 0.2, f"Comparison data retrieval took {retrieval_time:.2f}s, expected < 0.2s"
    
    # Verify comparison data
    assert len(comparison_data) == 2  # Two experiment "best" entries
    for exp_key in comparison_data:
        assert all(metric in comparison_data[exp_key] for metric in common_metrics)


def test_large_experiment_performance(experiment_service):
    """Test performance with a very large experiment with many runs."""
    start_time = time.time()
    
    experiment, runs = create_experiment_with_runs(
        experiment_service,
        num_runs=100,
        params_per_run=20,
        metrics_per_run=20
    )
    
    creation_time = time.time() - start_time
    
    # Retrieving the experiment should be fast
    start_time = time.time()
    retrieved = experiment_service.get_experiment(experiment.id)
    retrieval_time = time.time() - start_time
    
    # Updating the experiment should be fast
    start_time = time.time()
    retrieved.description = "Updated description for performance test"
    updated = experiment_service.update_experiment(retrieved)
    update_time = time.time() - start_time
    
    # Log performance metrics
    print(f"Large experiment creation time: {creation_time:.2f}s")
    print(f"Large experiment retrieval time: {retrieval_time:.6f}s")
    print(f"Large experiment update time: {update_time:.6f}s")
    print(f"Total runs: {len(runs)}")
    print(f"Total parameters: {len(runs) * 20}")
    print(f"Total metrics: {len(runs) * 20}")
    
    # Performance should be reasonable even for large experiments
    assert creation_time < 5.0, f"Large experiment creation took {creation_time:.2f}s, expected < 5.0s"
    assert retrieval_time < 0.1, f"Large experiment retrieval took {retrieval_time:.6f}s, expected < 0.1s"
    assert update_time < 0.1, f"Large experiment update took {update_time:.6f}s, expected < 0.1s"