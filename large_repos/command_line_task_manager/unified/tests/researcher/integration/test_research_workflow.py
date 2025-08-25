"""
Integration tests for research workflows.

These tests verify that the various modules of the system work together
to support complete research workflows.
"""

import pytest
from datetime import datetime
from uuid import UUID

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


def test_complete_research_workflow(services):
    """
    Test a complete research workflow from task creation to publication.
    
    This test simulates a research workflow where:
    1. A research task is created
    2. Bibliographic references are added
    3. A dataset is versioned
    4. The computational environment is captured
    5. Experiments are run
    6. Results are exported as an academic document
    """
    # 1. Create a research task
    task = services["task"].create_task(
        title="Investigate Neural Network Performance",
        description="Investigate performance of different neural network architectures on image classification"
    )
    
    # Add research questions
    question = services["task"].create_research_question(
        task_id=task.id,
        question="Which neural network architecture performs best on image classification?"
    )
    
    # 2. Add bibliographic references
    ref1 = services["bibliography"].create_reference(
        title="Deep Residual Learning for Image Recognition",
        authors=["He, Kaiming", "Zhang, Xiangyu", "Ren, Shaoqing", "Sun, Jian"],
        year=2016,
        venue="IEEE Conference on Computer Vision and Pattern Recognition",
        doi="10.1109/CVPR.2016.90"
    )
    
    ref2 = services["bibliography"].create_reference(
        title="ImageNet Classification with Deep Convolutional Neural Networks",
        authors=["Krizhevsky, Alex", "Sutskever, Ilya", "Hinton, Geoffrey E."],
        year=2012,
        venue="Advances in Neural Information Processing Systems"
    )
    
    # Link references to the task
    services["task"].add_reference_to_task(task.id, ref1)
    services["task"].add_reference_to_task(task.id, ref2)
    
    # 3. Create a dataset and versions
    dataset = services["dataset"].create_dataset(
        name="ImageNet Subset",
        description="A subset of the ImageNet dataset for testing",
        location="/path/to/imagenet"
    )
    
    # Link dataset to task
    services["task"].add_dataset_to_task(task.id, dataset)
    
    # Create dataset versions
    version1 = services["dataset"].create_version(
        dataset_id=dataset.id,
        version_number="1.0",
        description="Initial version",
        location="/path/to/imagenet/v1"
    )
    
    version2 = services["dataset"].create_version(
        dataset_id=dataset.id,
        version_number="1.1",
        description="Added data augmentation",
        location="/path/to/imagenet/v1.1",
        parent_version_id=version1.id
    )
    
    # 4. Capture computational environment
    env = services["environment"].create_snapshot(
        name="Deep Learning Environment",
        description="Python environment for deep learning experiments"
    )
    
    # Register the environment with the task service
    services["task"].register_environment(env.id, env)
    
    # Add packages
    services["environment"].add_package(
        env_id=env.id,
        name="tensorflow",
        version="2.8.0"
    )
    
    services["environment"].add_package(
        env_id=env.id,
        name="numpy",
        version="1.22.3"
    )
    
    # 5. Run experiments
    experiment = services["experiment"].create_experiment(
        name="CNN Architecture Comparison",
        description="Comparing ResNet, VGG, and MobileNet architectures",
        task_id=task.id,
        dataset_id=dataset.id,
        environment_id=env.id,
        tags=["neural-networks", "image-classification"]
    )
    
    # Register the experiment with the task service
    services["task"].register_experiment(experiment.id, experiment)
    
    # Create experiment runs for different architectures
    # ResNet Run
    resnet_params = [
        services["experiment"].add_parameter(
            name="architecture",
            type="string",
            value="ResNet50"
        ),
        services["experiment"].add_parameter(
            name="learning_rate",
            type="float",
            value=0.001
        ),
        services["experiment"].add_parameter(
            name="batch_size",
            type="integer",
            value=32
        )
    ]
    
    resnet_run = services["experiment"].create_experiment_run(
        experiment_id=experiment.id,
        parameters=resnet_params
    )
    
    services["experiment"].start_run(resnet_run.id)
    services["experiment"].add_run_metric(
        run_id=resnet_run.id,
        name="accuracy",
        type="accuracy",
        value=0.92
    )
    services["experiment"].add_run_metric(
        run_id=resnet_run.id,
        name="inference_time",
        type="custom",
        value=120.5,
        description="Average inference time in ms"
    )
    services["experiment"].complete_run(resnet_run.id)
    
    # VGG Run
    vgg_params = [
        services["experiment"].add_parameter(
            name="architecture",
            type="string",
            value="VGG16"
        ),
        services["experiment"].add_parameter(
            name="learning_rate",
            type="float",
            value=0.001
        ),
        services["experiment"].add_parameter(
            name="batch_size",
            type="integer",
            value=32
        )
    ]
    
    vgg_run = services["experiment"].create_experiment_run(
        experiment_id=experiment.id,
        parameters=vgg_params
    )
    
    services["experiment"].start_run(vgg_run.id)
    services["experiment"].add_run_metric(
        run_id=vgg_run.id,
        name="accuracy",
        type="accuracy",
        value=0.89
    )
    services["experiment"].add_run_metric(
        run_id=vgg_run.id,
        name="inference_time",
        type="custom",
        value=145.2,
        description="Average inference time in ms"
    )
    services["experiment"].complete_run(vgg_run.id)
    
    # 6. Export results as an academic document
    document = services["export"].create_document(
        title="Comparison of Neural Network Architectures for Image Classification",
        authors=["Researcher, Academic"],
        affiliations=["University Research Lab"],
        corresponding_email="researcher@university.edu",
        keywords=["deep learning", "neural networks", "image classification"]
    )
    
    # Add introduction section
    intro_section = services["export"].add_section(
        document_id=document.id,
        title="Introduction"
    )
    
    intro_text = services["export"].create_text_block(
        content="This study investigates the performance of different neural network architectures for image classification tasks."
    )
    
    services["export"].add_content_block(
        document_id=document.id,
        section_index=0,
        block=intro_text
    )
    
    # Add methods section
    methods_section = services["export"].add_section(
        document_id=document.id,
        title="Methods"
    )
    
    dataset_text = services["export"].create_text_block(
        content=f"We used the ImageNet Subset dataset (version {version2.version_number}) containing preprocessed images for training and evaluation."
    )
    
    services["export"].add_content_block(
        document_id=document.id,
        section_index=1,
        block=dataset_text
    )
    
    # Add results section
    results_section = services["export"].add_section(
        document_id=document.id,
        title="Results"
    )
    
    # Create a table with experiment results
    results_table = services["export"].create_table_block(
        headers=["Architecture", "Accuracy", "Inference Time (ms)"],
        data=[
            ["ResNet50", "0.92", "120.5"],
            ["VGG16", "0.89", "145.2"]
        ],
        caption="Performance metrics for neural network architectures"
    )
    
    services["export"].add_content_block(
        document_id=document.id,
        section_index=2,
        block=results_table
    )
    
    # Add conclusion section
    conclusion_section = services["export"].add_section(
        document_id=document.id,
        title="Conclusion"
    )
    
    conclusion_text = services["export"].create_text_block(
        content="ResNet50 demonstrated superior performance in both accuracy and inference time compared to VGG16."
    )
    
    services["export"].add_content_block(
        document_id=document.id,
        section_index=3,
        block=conclusion_text
    )
    
    # Generate markdown content
    markdown = services["export"].generate_markdown(document.id)
    
    # Verify the complete workflow
    # 1. Verify task
    task = services["task"].get_task(task.id)
    assert len(task.references) == 2
    assert len(task.datasets) == 1
    assert len(task.research_questions) == 1
    
    # 2. Verify dataset
    dataset = services["dataset"].get_dataset(dataset.id)
    assert len(dataset.versions) == 2
    assert dataset.versions[1].parent_version_id == version1.id
    
    # 3. Verify environment
    env = services["environment"].get_snapshot(env.id)
    assert len(env.packages) == 2
    
    # 4. Verify experiment
    experiment = services["experiment"].get_experiment(experiment.id)
    assert len(experiment.runs) == 2
    
    # Get best run by accuracy
    best_run = services["experiment"].get_best_run(experiment.id, "accuracy")
    assert best_run.id == resnet_run.id
    
    # 5. Verify document
    document = services["export"].get_document(document.id)
    assert len(document.sections) == 4
    
    # Verify markdown content
    assert "Comparison of Neural Network Architectures" in markdown
    assert "Researcher, Academic" in markdown
    assert "University Research Lab" in markdown
    assert "ImageNet Subset dataset" in markdown
    assert "ResNet50" in markdown
    assert "VGG16" in markdown
    assert "0.92" in markdown  # Accuracy value
    assert "superior performance" in markdown