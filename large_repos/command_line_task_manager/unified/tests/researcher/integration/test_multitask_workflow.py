"""
Integration tests for multitask research workflows.

These tests verify that the system can handle complex scenarios with
multiple interconnected research tasks.
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
    
    # Create services
    task_service = TaskService(task_storage)
    bib_service = BibliographyService(bibliography_storage)
    dataset_service = DatasetService(dataset_storage)
    environment_service = EnvironmentService(environment_storage)
    experiment_service = ExperimentService(experiment_storage)
    export_service = ExportService(export_storage)
    
    # Set up reference and dataset validators for integration
    def validate_reference(ref_id):
        return bib_service.get_reference(ref_id) is not None
    
    def validate_dataset(dataset_id):
        return dataset_service.get_dataset(dataset_id) is not None
    
    task_service._service._validate_reference_callback = validate_reference
    task_service._service._validate_dataset_callback = validate_dataset
    
    # Return all services
    return {
        "task": task_service,
        "bibliography": bib_service,
        "dataset": dataset_service,
        "environment": environment_service,
        "experiment": experiment_service,
        "export": export_service
    }


def test_multitask_research_project(services):
    """
    Test a research project with multiple interconnected tasks.
    
    This test simulates a complex research project with:
    1. A main research task with subtasks
    2. Shared bibliographic references
    3. Datasets that evolve across tasks
    4. Multiple experiment runs with comparisons
    5. Consolidated reporting
    """
    # 1. Create main research task
    main_task = services["task"].create_task(
        title="Improving NLP Models for Scientific Literature",
        description="Research project to improve NLP models for scientific literature analysis",
        tags=["nlp", "science", "literature"]
    )
    
    # Create subtasks
    data_task = services["task"].create_task(
        title="Data Collection and Preprocessing",
        description="Collect and preprocess scientific papers dataset",
        parent_id=main_task.id,
        tags=["data", "preprocessing"]
    )
    
    model_task = services["task"].create_task(
        title="Model Architecture Development",
        description="Develop specialized NLP model architectures",
        parent_id=main_task.id,
        tags=["model", "architecture"]
    )
    
    eval_task = services["task"].create_task(
        title="Model Evaluation",
        description="Evaluate model performance on various scientific domains",
        parent_id=main_task.id,
        tags=["evaluation", "metrics"]
    )
    
    # 2. Add shared bibliographic references
    ref1 = services["bibliography"].create_reference(
        title="BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        authors=["Devlin, Jacob", "Chang, Ming-Wei", "Lee, Kenton", "Toutanova, Kristina"],
        year=2019,
        venue="NAACL-HLT",
        doi="10.18653/v1/N19-1423"
    )
    
    ref2 = services["bibliography"].create_reference(
        title="SciBERT: A Pretrained Language Model for Scientific Text",
        authors=["Beltagy, Iz", "Lo, Kyle", "Cohan, Arman"],
        year=2019,
        venue="EMNLP-IJCNLP",
        doi="10.18653/v1/D19-1371"
    )
    
    ref3 = services["bibliography"].create_reference(
        title="Don't Stop Pretraining: Adapt Language Models to Domains and Tasks",
        authors=["Gururangan, Suchin", "Marasović, Ana", "Swayamdipta, Swabha"],
        year=2020,
        venue="ACL"
    )
    
    # Register all references with the task service
    services["task"].register_reference(ref1.id, ref1)
    services["task"].register_reference(ref2.id, ref2)
    services["task"].register_reference(ref3.id, ref3)
    
    # Link references to tasks
    # Main task gets all references
    for ref_id in [ref1.id, ref2.id, ref3.id]:
        services["task"].add_reference_to_task(main_task.id, ref_id)
    
    # Subtasks get relevant references
    services["task"].add_reference_to_task(data_task.id, ref3.id)
    services["task"].add_reference_to_task(model_task.id, ref1.id)
    services["task"].add_reference_to_task(model_task.id, ref2.id)
    services["task"].add_reference_to_task(eval_task.id, ref2.id)
    
    # 3. Create datasets that evolve across tasks
    raw_dataset = services["dataset"].create_dataset(
        name="Scientific Papers Corpus",
        description="Raw corpus of scientific papers from various domains",
        location="/data/raw/scientific_papers"
    )
    
    # Register dataset with task service
    services["task"].register_dataset(raw_dataset.id, raw_dataset)
    
    # Link to data collection task
    services["task"].add_dataset_to_task(data_task.id, raw_dataset.id)
    
    # Create initial version
    raw_v1 = services["dataset"].create_version(
        dataset_id=raw_dataset.id,
        version_number="1.0",
        description="Initial data collection with 10,000 papers",
        location="/data/raw/scientific_papers/v1"
    )
    
    # Create processed dataset (derived from raw dataset)
    processed_dataset = services["dataset"].create_dataset(
        name="Processed Scientific Papers",
        description="Preprocessed corpus of scientific papers",
        location="/data/processed/scientific_papers"
    )
    
    # Link datasets with provenance
    services["dataset"].add_derivation(
        derived_dataset_id=processed_dataset.id,
        source_dataset_id=raw_dataset.id,
        transformation="Tokenization, cleaning, and sentence splitting"
    )
    
    # Create processed version
    processed_v1 = services["dataset"].create_version(
        dataset_id=processed_dataset.id,
        version_number="1.0",
        description="Processed version of raw dataset v1.0",
        location="/data/processed/scientific_papers/v1"
    )
    
    # Register processed dataset with task service
    services["task"].register_dataset(processed_dataset.id, processed_dataset)
    
    # Link to model development task
    services["task"].add_dataset_to_task(model_task.id, processed_dataset.id)
    
    # 4. Set up environments
    base_env = services["environment"].create_snapshot(
        name="NLP Base Environment",
        description="Base Python environment for NLP research"
    )
    
    # Add base packages
    base_packages = [
        ("python", "3.9.10"),
        ("pytorch", "1.10.2"),
        ("transformers", "4.16.2"),
        ("numpy", "1.22.2"),
        ("pandas", "1.4.1")
    ]
    
    for name, version in base_packages:
        services["environment"].add_package(base_env.id, name, version)
    
    # Clone environment for experiment variations
    exp1_env = services["environment"].clone_snapshot(
        base_env.id, 
        "NLP Experiment 1 Environment",
        "Modified environment with extra logging"
    )
    
    services["environment"].add_package(exp1_env.id, "tensorboard", "2.8.0")
    
    exp2_env = services["environment"].clone_snapshot(
        base_env.id, 
        "NLP Experiment 2 Environment",
        "Modified environment with extra optimization tools"
    )
    
    services["environment"].add_package(exp2_env.id, "optuna", "2.10.0")
    
    # 5. Run experiments for the model development task
    vanilla_exp = services["experiment"].create_experiment(
        name="Vanilla BERT Adaptation",
        description="Adapting vanilla BERT to scientific papers",
        task_id=model_task.id,
        dataset_id=processed_dataset.id,
        environment_id=exp1_env.id,
        tags=["bert", "baseline"]
    )
    
    scibert_exp = services["experiment"].create_experiment(
        name="SciBERT Adaptation",
        description="Adapting SciBERT to our specific scientific domains",
        task_id=model_task.id,
        dataset_id=processed_dataset.id,
        environment_id=exp2_env.id,
        tags=["scibert", "domain-specific"]
    )
    
    # Run BERT experiments
    bert_params = [
        services["experiment"].add_parameter(
            name="model", type="string", value="bert-base-uncased"
        ),
        services["experiment"].add_parameter(
            name="learning_rate", type="float", value=2e-5
        ),
        services["experiment"].add_parameter(
            name="epochs", type="integer", value=3
        )
    ]
    
    bert_run1 = services["experiment"].create_experiment_run(
        experiment_id=vanilla_exp.id,
        parameters=bert_params
    )
    
    services["experiment"].start_run(bert_run1.id)
    services["experiment"].add_run_metric(
        run_id=bert_run1.id, name="accuracy", type="accuracy", value=0.78
    )
    services["experiment"].add_run_metric(
        run_id=bert_run1.id, name="f1", type="f1_score", value=0.76
    )
    services["experiment"].complete_run(bert_run1.id)
    
    # Run SciBERT experiments
    scibert_params = [
        services["experiment"].add_parameter(
            name="model", type="string", value="allenai/scibert_scivocab_uncased"
        ),
        services["experiment"].add_parameter(
            name="learning_rate", type="float", value=2e-5
        ),
        services["experiment"].add_parameter(
            name="epochs", type="integer", value=3
        )
    ]
    
    scibert_run1 = services["experiment"].create_experiment_run(
        experiment_id=scibert_exp.id,
        parameters=scibert_params
    )
    
    services["experiment"].start_run(scibert_run1.id)
    services["experiment"].add_run_metric(
        run_id=scibert_run1.id, name="accuracy", type="accuracy", value=0.85
    )
    services["experiment"].add_run_metric(
        run_id=scibert_run1.id, name="f1", type="f1_score", value=0.83
    )
    services["experiment"].complete_run(scibert_run1.id)
    
    # Try another learning rate with SciBERT
    scibert_params2 = [
        services["experiment"].add_parameter(
            name="model", type="string", value="allenai/scibert_scivocab_uncased"
        ),
        services["experiment"].add_parameter(
            name="learning_rate", type="float", value=3e-5
        ),
        services["experiment"].add_parameter(
            name="epochs", type="integer", value=3
        )
    ]
    
    scibert_run2 = services["experiment"].create_experiment_run(
        experiment_id=scibert_exp.id,
        parameters=scibert_params2
    )
    
    services["experiment"].start_run(scibert_run2.id)
    services["experiment"].add_run_metric(
        run_id=scibert_run2.id, name="accuracy", type="accuracy", value=0.87
    )
    services["experiment"].add_run_metric(
        run_id=scibert_run2.id, name="f1", type="f1_score", value=0.86
    )
    services["experiment"].complete_run(scibert_run2.id)
    
    # Create experiment comparison
    comparison = services["experiment"].create_comparison(
        name="BERT vs SciBERT Comparison",
        description="Comparing vanilla BERT and SciBERT performance",
        run_ids=[bert_run1.id, scibert_run1.id, scibert_run2.id],
        metrics=["accuracy", "f1"]
    )
    
    # 6. Create a consolidated report for the model task
    model_doc = services["export"].create_document(
        title="Model Architecture Development for Scientific NLP",
        authors=["Researcher, Academic"],
        affiliations=["AI Research Lab"],
        corresponding_email="researcher@ailab.org",
        keywords=["NLP", "BERT", "SciBERT", "scientific text"]
    )
    
    # Add introduction
    intro_section = services["export"].add_section(
        document_id=model_doc.id,
        title="Introduction"
    )
    
    intro_text = services["export"].create_text_block(
        content="This document outlines our work on adapting transformer-based language models for scientific text analysis."
    )
    
    services["export"].add_content_block(
        document_id=model_doc.id,
        section_index=0,
        block=intro_text
    )
    
    # Add citation to the introduction
    citation = services["export"].create_citation_block(
        reference_ids=[ref1.id, ref2.id],
        context="Previous work has shown the effectiveness of domain-specific pretraining"
    )
    
    services["export"].add_content_block(
        document_id=model_doc.id,
        section_index=0,
        block=citation
    )
    
    # Add experiments section
    exp_section = services["export"].add_section(
        document_id=model_doc.id,
        title="Experiments"
    )
    
    exp_text = services["export"].create_text_block(
        content="We conducted experiments comparing vanilla BERT and SciBERT models on our scientific papers dataset."
    )
    
    services["export"].add_content_block(
        document_id=model_doc.id,
        section_index=1,
        block=exp_text
    )
    
    # Add results section
    results_section = services["export"].add_section(
        document_id=model_doc.id,
        title="Results"
    )
    
    # Create a table with experiment results
    results_table = services["export"].create_table_block(
        headers=["Model", "Learning Rate", "Accuracy", "F1 Score"],
        data=[
            ["BERT", "2e-5", "0.78", "0.76"],
            ["SciBERT", "2e-5", "0.85", "0.83"],
            ["SciBERT", "3e-5", "0.87", "0.86"]
        ],
        caption="Performance comparison of BERT variants on scientific papers"
    )
    
    services["export"].add_content_block(
        document_id=model_doc.id,
        section_index=2,
        block=results_table
    )
    
    # Generate markdown
    markdown = services["export"].generate_markdown(model_doc.id)
    
    # Verify the complete workflow
    # 1. Verify task hierarchy
    main_task = services["task"].get_task(main_task.id)
    subtasks = services["task"].get_subtasks(main_task.id)
    assert len(subtasks) == 3
    
    # 2. Verify reference sharing
    main_refs = services["task"].get_task_references(main_task.id)
    assert len(main_refs) == 3
    model_refs = services["task"].get_task_references(model_task.id)
    assert len(model_refs) == 2
    
    # 3. Verify dataset evolution
    datasets = services["task"].get_task_datasets(data_task.id)
    assert len(datasets) == 1
    assert datasets[0].id == raw_dataset.id
    
    processed = services["dataset"].get_dataset(processed_dataset.id)
    raw = services["dataset"].get_dataset(raw_dataset.id)
    derivations = services["dataset"].get_dataset_derivations(raw_dataset.id)
    assert len(derivations) == 1
    assert derivations[0].output_dataset_version_id is not None
    
    # 4. Verify environments
    env = services["environment"].get_snapshot(exp2_env.id)
    packages = env.packages
    assert len(packages) == 6  # Base packages + optuna
    
    # Check if optuna exists in packages, regardless of format
    has_optuna = False
    for p in packages:
        if isinstance(p, str) and p == "optuna":
            has_optuna = True
            break
        elif hasattr(p, 'name') and p.name == "optuna":
            has_optuna = True
            break
    assert has_optuna, f"Package 'optuna' not found in packages: {packages}"
    
    # 5. Verify experiments
    scibert_exp_obj = services["experiment"].get_experiment(scibert_exp.id)
    assert len(scibert_exp_obj.runs) == 2
    
    # Verify best run
    best_run = services["experiment"].get_best_run(scibert_exp.id, "accuracy")
    assert best_run.id == scibert_run2.id
    assert best_run.metrics["accuracy"].value == 0.87
    
    # Verify comparison
    comp_data = services["experiment"].get_comparison_data(comparison.id)
    assert len(comp_data) == 3
    
    # 6. Verify document
    document = services["export"].get_document(model_doc.id)
    assert len(document.sections) == 3
    
    # Verify markdown content
    assert "Model Architecture Development for Scientific NLP" in markdown
    assert "Researcher, Academic" in markdown
    assert "AI Research Lab" in markdown
    assert "Previous work has shown the effectiveness" in markdown
    assert "SciBERT" in markdown
    assert "0.87" in markdown  # Best accuracy value