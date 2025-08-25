"""
Integration performance tests for the Research Track system.

These tests verify that the combined system modules meet performance
requirements for realistic research workflows.
"""

import pytest
import time
import random
import string
from uuid import uuid4

from researchtrack.task_management import TaskService, InMemoryTaskStorage
from researchtrack.bibliography import BibliographyService, InMemoryBibliographyStorage
from researchtrack.dataset_versioning import DatasetService, InMemoryDatasetStorage
from researchtrack.environment import EnvironmentService, InMemoryEnvironmentStorage
from researchtrack.experiment_tracking import ExperimentService, InMemoryExperimentStorage
from researchtrack.export import ExportService, InMemoryExportStorage


@pytest.fixture
def services():
    """Create all services with in-memory storage for integrated testing."""
    task_storage = InMemoryTaskStorage()
    bibliography_storage = InMemoryBibliographyStorage()
    dataset_storage = InMemoryDatasetStorage()
    environment_storage = InMemoryEnvironmentStorage()
    experiment_storage = InMemoryExperimentStorage()
    export_storage = InMemoryExportStorage()
    
    return {
        "task": TaskService(task_storage),
        "bibliography": BibliographyService(bibliography_storage),
        "dataset": DatasetService(dataset_storage),
        "environment": EnvironmentService(environment_storage),
        "experiment": ExperimentService(experiment_storage),
        "export": ExportService(export_storage)
    }


def random_string(length=10):
    """Generate a random string of fixed length."""
    return ''.join(random.choices(string.ascii_letters, k=length))


def test_large_research_project_performance(services):
    """
    Test the performance of a large-scale research project workflow.
    
    This test simulates a complex research project with:
    - Multiple research tasks and questions
    - Many bibliographic references
    - Multiple datasets with versions
    - Several environment snapshots
    - Multiple experiments with many runs
    - Document generation with the results
    """
    start_time = time.time()
    
    # 1. Create research tasks and questions
    tasks = []
    for i in range(10):
        task = services["task"].create_task(
            title=f"Research Task {i+1}: {random_string(20)}",
            description=f"Description for task {i+1}: {random_string(100)}",
            tags=[f"tag{i+1}", "research", random_string(8)]
        )
        
        # Add research questions
        for j in range(5):
            question = services["task"].create_research_question(
                task_id=task.id,
                question=f"Question {j+1} for Task {i+1}: {random_string(50)}?"
            )
        
        tasks.append(task)
    
    task_creation_time = time.time() - start_time
    print(f"Created {len(tasks)} tasks with 5 questions each in {task_creation_time:.2f}s")
    
    # 2. Create bibliographic references
    start_time = time.time()
    
    references = []
    for i in range(50):
        ref = services["bibliography"].create_reference(
            title=f"Reference {i+1}: {random_string(30)}",
            authors=[f"Author {j+1}" for j in range(random.randint(1, 5))],
            year=random.randint(2000, 2023),
            venue=random.choice(["Journal A", "Conference B", "Workshop C", "Symposium D"]),
            doi=f"10.1234/ref{i+1}" if random.random() > 0.3 else None
        )
        references.append(ref)
        
        # Link references to tasks (each task gets ~10 random references)
        for task in random.sample(tasks, min(5, len(tasks))):
            services["task"].add_reference_to_task(task.id, ref.id)
    
    reference_creation_time = time.time() - start_time
    print(f"Created {len(references)} references and linked them to tasks in {reference_creation_time:.2f}s")
    
    # 3. Create datasets and versions
    start_time = time.time()
    
    datasets = []
    for i in range(20):
        dataset = services["dataset"].create_dataset(
            name=f"Dataset {i+1}: {random_string(20)}",
            description=f"Description for dataset {i+1}: {random_string(100)}",
            location=f"/path/to/dataset{i+1}"
        )
        
        # Create versions
        previous_version = None
        for j in range(3):
            version = services["dataset"].create_version(
                dataset_id=dataset.id,
                version_number=f"1.{j}",
                description=f"Version 1.{j} of dataset {i+1}",
                location=f"/path/to/dataset{i+1}/v1_{j}",
                parent_version_id=previous_version.id if previous_version else None
            )
            previous_version = version
        
        datasets.append(dataset)
        
        # Link datasets to tasks
        for task in random.sample(tasks, min(3, len(tasks))):
            services["task"].add_dataset_to_task(task.id, dataset.id)
    
    dataset_creation_time = time.time() - start_time
    print(f"Created {len(datasets)} datasets with 3 versions each in {dataset_creation_time:.2f}s")
    
    # 4. Create environment snapshots
    start_time = time.time()
    
    environments = []
    for i in range(5):
        env = services["environment"].create_snapshot(
            name=f"Environment {i+1}: {random_string(20)}",
            description=f"Description for environment {i+1}: {random_string(100)}"
        )
        
        # Add packages
        for j in range(20):
            services["environment"].add_package(
                env_id=env.id,
                name=f"package{j+1}",
                version=f"{random.randint(1, 5)}.{random.randint(0, 10)}.{random.randint(0, 20)}"
            )
        
        environments.append(env)
    
    environment_creation_time = time.time() - start_time
    print(f"Created {len(environments)} environments with 20 packages each in {environment_creation_time:.2f}s")
    
    # 5. Create experiments and runs
    start_time = time.time()
    
    experiments = []
    for i, task in enumerate(random.sample(tasks, 5)):
        experiment = services["experiment"].create_experiment(
            name=f"Experiment {i+1}: {random_string(20)}",
            description=f"Description for experiment {i+1}: {random_string(100)}",
            task_id=task.id,
            dataset_id=random.choice(datasets).id,
            environment_id=random.choice(environments).id,
            tags=[f"exp{i+1}", "research", random_string(8)]
        )
        
        # Create runs
        for j in range(10):
            # Create parameters
            parameters = []
            for k in range(10):
                # Choose a type first
                param_type = random.choice(["float", "integer", "string"])
                # Then pick an appropriate value for that type
                if param_type == "float":
                    param_value = random.random() * 100
                elif param_type == "integer":
                    param_value = random.randint(1, 100)
                else:  # string
                    param_value = random_string(5)
                
                param = services["experiment"].add_parameter(
                    name=f"param{k+1}",
                    type=param_type,
                    value=param_value
                )
                parameters.append(param)
            
            # Create run
            run = services["experiment"].create_experiment_run(
                experiment_id=experiment.id,
                parameters=parameters
            )
            
            # Start and complete run with metrics
            services["experiment"].start_run(run.id)
            for k in range(5):
                services["experiment"].add_run_metric(
                    run_id=run.id,
                    name=f"metric{k+1}",
                    type=random.choice(["accuracy", "loss", "f1_score", "custom"]),
                    value=random.random()
                )
            services["experiment"].complete_run(run.id)
        
        experiments.append(experiment)
    
    experiment_creation_time = time.time() - start_time
    print(f"Created {len(experiments)} experiments with 10 runs each in {experiment_creation_time:.2f}s")
    
    # 6. Generate documents from experiment results
    start_time = time.time()
    
    documents = []
    for i, experiment in enumerate(experiments):
        document = services["export"].create_document(
            title=f"Results for {experiment.name}",
            authors=[f"Researcher {j+1}" for j in range(3)],
            affiliations=["Research Lab A", "University B"],
            corresponding_email="researcher@example.com",
            keywords=["research", "results", random_string(8)]
        )
        
        # Add sections
        intro = services["export"].add_section(
            document_id=document.id,
            title="Introduction"
        )
        
        intro_text = services["export"].create_text_block(
            content=f"This document presents the results of {experiment.name}. {random_string(200)}"
        )
        
        services["export"].add_content_block(
            document_id=document.id,
            section_index=0,
            block=intro_text
        )
        
        methods = services["export"].add_section(
            document_id=document.id,
            title="Methods"
        )
        
        methods_text = services["export"].create_text_block(
            content=f"The methods used in this experiment are described here. {random_string(300)}"
        )
        
        services["export"].add_content_block(
            document_id=document.id,
            section_index=1,
            block=methods_text
        )
        
        results = services["export"].add_section(
            document_id=document.id,
            title="Results"
        )
        
        # Create a results table
        results_table = services["export"].create_table_block(
            headers=["Run", "Metric1", "Metric2", "Metric3"],
            data=[
                [f"Run {j+1}", f"{random.random():.4f}", f"{random.random():.4f}", f"{random.random():.4f}"]
                for j in range(5)  # Show results for 5 runs
            ],
            caption=f"Results from {experiment.name}"
        )
        
        services["export"].add_content_block(
            document_id=document.id,
            section_index=2,
            block=results_table
        )
        
        # Generate markdown
        markdown = services["export"].generate_markdown(document.id)
        documents.append(document)
    
    document_creation_time = time.time() - start_time
    print(f"Created {len(documents)} documents with content and generated markdown in {document_creation_time:.2f}s")
    
    # 7. Test some complex queries
    start_time = time.time()
    
    # Get all experiments related to a specific task
    task = random.choice(tasks)
    task_experiments = [
        exp for exp in experiments 
        if services["experiment"].get_experiment(exp.id).task_id == task.id
    ]
    
    # Get all datasets used in experiments for a specific task
    task_datasets = services["task"].get_task_datasets(task.id)
    
    # Get all references for a specific task
    task_references = services["task"].get_task_references(task.id)
    
    # Get the best run across all experiments for a specific metric
    best_runs = []
    for exp in experiments:
        best_run = services["experiment"].get_best_run(exp.id, "metric1")
        if best_run:
            best_runs.append(best_run)
    
    query_time = time.time() - start_time
    print(f"Executed complex queries across the system in {query_time:.2f}s")
    
    # Performance assertions
    assert task_creation_time < 1.0, f"Task creation took {task_creation_time:.2f}s, expected < 1.0s"
    assert reference_creation_time < 2.0, f"Reference creation took {reference_creation_time:.2f}s, expected < 2.0s"
    assert dataset_creation_time < 2.0, f"Dataset creation took {dataset_creation_time:.2f}s, expected < 2.0s"
    assert environment_creation_time < 1.0, f"Environment creation took {environment_creation_time:.2f}s, expected < 1.0s"
    assert experiment_creation_time < 5.0, f"Experiment creation took {experiment_creation_time:.2f}s, expected < 5.0s"
    assert document_creation_time < 2.0, f"Document creation took {document_creation_time:.2f}s, expected < 2.0s"
    assert query_time < 1.0, f"Complex queries took {query_time:.2f}s, expected < 1.0s"