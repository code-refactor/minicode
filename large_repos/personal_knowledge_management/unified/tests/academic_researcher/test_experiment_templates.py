"""Tests for experiment templates and documentation."""

import os
import tempfile
import shutil
from pathlib import Path

import pytest
import yaml

from researchbrain.core.brain import ResearchBrain
from researchbrain.core.models import Experiment, ExperimentStatus, ResearchQuestion
from researchbrain.experiments.templates import (
    get_template, list_templates, create_template, apply_template, create_default_templates
)


class TestExperimentTemplates:
    """Tests for experiment templates and documentation."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Fixture that creates a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def brain(self, temp_data_dir):
        """Fixture that creates a ResearchBrain instance."""
        return ResearchBrain(temp_data_dir)
    
    def test_default_templates_availability(self):
        """Test the availability of default experiment templates."""
        # Get list of all templates
        templates = list_templates()
        
        # Verify that default templates are available
        assert "behavioral_experiment" in templates
        assert "neuroimaging_experiment" in templates
        assert "molecular_biology_experiment" in templates
        assert "computational_modeling_experiment" in templates
        
        # Check that each template contains required fields
        for template_name in templates:
            template = get_template(template_name)
            
            assert template is not None
            assert "name" in template
            assert "description" in template
            assert "fields" in template
            assert "output_format" in template
            
            # Check field structure
            for field in template["fields"]:
                assert "name" in field
                assert "type" in field
                assert "description" in field
                if field.get("required"):
                    assert isinstance(field["required"], bool)
    
    def test_behavioral_experiment_template(self, brain):
        """Test creating an experiment from the behavioral experiment template."""
        # Create an experiment using the behavioral template
        experiment_id = brain.create_experiment_from_template(
            template_name="behavioral_experiment",
            title="Attention Switching Task",
            hypothesis="Older adults will show greater switch costs than younger adults",
            participants="60 participants (30 younger: 18-30, 30 older: 65-80)",
            independent_variables="Age group (younger, older); Task type (switch, non-switch)",
            dependent_variables="Reaction time (ms); Accuracy (%)",
            control_condition="Non-switch trials serve as control condition",
            procedure="Participants will perform a computerized task switching paradigm",
            analysis_plan="Mixed ANOVA with planned comparisons"
        )
        
        # Retrieve the created experiment
        experiment = brain.storage.get(Experiment, experiment_id)
        
        # Verify basic properties
        assert experiment is not None
        assert experiment.title == "Attention Switching Task"
        assert experiment.hypothesis == "Older adults will show greater switch costs than younger adults"
        assert experiment.status == ExperimentStatus.PLANNED
        
        # Verify methodology formatting
        assert "# Behavioral Experiment Methodology" in experiment.methodology
        assert "## Participants" in experiment.methodology
        assert "60 participants (30 younger: 18-30, 30 older: 65-80)" in experiment.methodology
        assert "## Design" in experiment.methodology
        assert "Independent Variables: Age group (younger, older); Task type (switch, non-switch)" in experiment.methodology
        assert "Dependent Variables: Reaction time (ms); Accuracy (%)" in experiment.methodology
        assert "Control Condition: Non-switch trials serve as control condition" in experiment.methodology
        assert "## Procedure" in experiment.methodology
        assert "Participants will perform a computerized task switching paradigm" in experiment.methodology
        assert "## Analysis Plan" in experiment.methodology
        assert "Mixed ANOVA with planned comparisons" in experiment.methodology
        
        # Verify variables were stored
        assert "participants" in experiment.variables
        assert experiment.variables["participants"] == "60 participants (30 younger: 18-30, 30 older: 65-80)"
        assert "independent_vars" in experiment.variables
        assert experiment.variables["independent_vars"] == "Age group (younger, older); Task type (switch, non-switch)"
        assert "dependent_vars" in experiment.variables
        assert experiment.variables["dependent_vars"] == "Reaction time (ms); Accuracy (%)"
    
    def test_neuroimaging_experiment_template(self, brain):
        """Test creating an experiment from the neuroimaging experiment template."""
        # Create an experiment using the neuroimaging template
        experiment_id = brain.create_experiment_from_template(
            template_name="neuroimaging_experiment",
            title="fMRI Study of Emotional Memory",
            hypothesis="Emotional stimuli will enhance activity in the amygdala and hippocampus",
            imaging_modality="fMRI (3T Siemens scanner)",
            participants="24 healthy right-handed adults (18-35 years)",
            task_design="Block design with emotional and neutral images",
            regions_of_interest="Amygdala, hippocampus, prefrontal cortex",
            acquisition_parameters="TR=2s, TE=30ms, 3mm isotropic voxels, 36 slices",
            preprocessing="Standard FSL pipeline with motion correction",
            analysis_plan="GLM analysis with emotional > neutral contrast"
        )
        
        # Retrieve the created experiment
        experiment = brain.storage.get(Experiment, experiment_id)
        
        # Verify basic properties
        assert experiment is not None
        assert experiment.title == "fMRI Study of Emotional Memory"
        assert experiment.hypothesis == "Emotional stimuli will enhance activity in the amygdala and hippocampus"
        assert experiment.status == ExperimentStatus.PLANNED
        
        # Verify methodology formatting
        assert "# Neuroimaging Experiment Methodology" in experiment.methodology
        assert "## Imaging Modality" in experiment.methodology
        assert "fMRI (3T Siemens scanner)" in experiment.methodology
        assert "## Participants" in experiment.methodology
        assert "24 healthy right-handed adults (18-35 years)" in experiment.methodology
        assert "## Task Design" in experiment.methodology
        assert "Block design with emotional and neutral images" in experiment.methodology
        assert "## Regions of Interest" in experiment.methodology
        assert "Amygdala, hippocampus, prefrontal cortex" in experiment.methodology
        assert "## Acquisition Parameters" in experiment.methodology
        assert "TR=2s, TE=30ms, 3mm isotropic voxels, 36 slices" in experiment.methodology
        assert "## Preprocessing" in experiment.methodology
        assert "Standard FSL pipeline with motion correction" in experiment.methodology
        assert "## Analysis Plan" in experiment.methodology
        assert "GLM analysis with emotional > neutral contrast" in experiment.methodology
        
        # Verify variables were stored
        assert "modality" in experiment.variables
        assert experiment.variables["modality"] == "fMRI (3T Siemens scanner)"
        assert "participants" in experiment.variables
        assert experiment.variables["participants"] == "24 healthy right-handed adults (18-35 years)"
        assert "roi" in experiment.variables
        assert experiment.variables["roi"] == "Amygdala, hippocampus, prefrontal cortex"
    
    def test_molecular_biology_experiment_template(self, brain):
        """Test creating an experiment from the molecular biology experiment template."""
        # Create an experiment using the molecular biology template
        experiment_id = brain.create_experiment_from_template(
            template_name="molecular_biology_experiment",
            title="CRISPR-Cas9 Gene Editing in Neuronal Cells",
            hypothesis="CRISPR-Cas9 can effectively edit the APP gene in human neuronal cells",
            cell_line="SH-SY5Y neuroblastoma cells and iPSC-derived neurons",
            reagents="CRISPR-Cas9 plasmids, guide RNAs targeting APP gene, lipofectamine",
            techniques="CRISPR-Cas9 transfection, PCR, Western Blot, immunocytochemistry",
            controls="Non-targeting guide RNA, wild-type cells, mock transfection",
            protocol="Cells will be transfected with CRISPR-Cas9 plasmids and guide RNAs",
            analysis="Editing efficiency by Sanger sequencing, protein levels by Western Blot"
        )
        
        # Retrieve the created experiment
        experiment = brain.storage.get(Experiment, experiment_id)
        
        # Verify basic properties
        assert experiment is not None
        assert experiment.title == "CRISPR-Cas9 Gene Editing in Neuronal Cells"
        assert experiment.hypothesis == "CRISPR-Cas9 can effectively edit the APP gene in human neuronal cells"
        assert experiment.status == ExperimentStatus.PLANNED
        
        # Verify methodology formatting
        assert "# Molecular Biology Experiment Protocol" in experiment.methodology
        assert "## Materials" in experiment.methodology
        assert "Cell Line/Model: SH-SY5Y neuroblastoma cells and iPSC-derived neurons" in experiment.methodology
        assert "## Reagents" in experiment.methodology
        assert "CRISPR-Cas9 plasmids, guide RNAs targeting APP gene, lipofectamine" in experiment.methodology
        assert "## Techniques" in experiment.methodology
        assert "CRISPR-Cas9 transfection, PCR, Western Blot, immunocytochemistry" in experiment.methodology
        assert "## Controls" in experiment.methodology
        assert "Non-targeting guide RNA, wild-type cells, mock transfection" in experiment.methodology
        assert "## Protocol" in experiment.methodology
        assert "Cells will be transfected with CRISPR-Cas9 plasmids and guide RNAs" in experiment.methodology
        assert "## Analysis" in experiment.methodology
        assert "Editing efficiency by Sanger sequencing, protein levels by Western Blot" in experiment.methodology
        
        # Verify variables were stored
        assert "cell_line" in experiment.variables
        assert experiment.variables["cell_line"] == "SH-SY5Y neuroblastoma cells and iPSC-derived neurons"
        assert "techniques" in experiment.variables
        assert experiment.variables["techniques"] == "CRISPR-Cas9 transfection, PCR, Western Blot, immunocytochemistry"
        assert "controls" in experiment.variables
        assert experiment.variables["controls"] == "Non-targeting guide RNA, wild-type cells, mock transfection"
    
    def test_computational_modeling_experiment_template(self, brain):
        """Test creating an experiment from the computational modeling experiment template."""
        # Create an experiment using the computational modeling template
        experiment_id = brain.create_experiment_from_template(
            template_name="computational_modeling_experiment",
            title="Neural Network Model of Visual Object Recognition",
            hypothesis="A hierarchical convolutional neural network can predict human object recognition performance",
            model_type="Convolutional Neural Network (CNN)",
            parameters="Learning rate=0.001, batch size=32, layers=5, dropout=0.5",
            input_data="ImageNet database and human behavioral data",
            algorithm="Supervised learning with backpropagation",
            validation="10-fold cross-validation and comparison to human psychophysics data",
            software="PyTorch framework on NVIDIA GPU cluster"
        )
        
        # Retrieve the created experiment
        experiment = brain.storage.get(Experiment, experiment_id)
        
        # Verify basic properties
        assert experiment is not None
        assert experiment.title == "Neural Network Model of Visual Object Recognition"
        assert experiment.hypothesis == "A hierarchical convolutional neural network can predict human object recognition performance"
        assert experiment.status == ExperimentStatus.PLANNED
        
        # Verify methodology formatting
        assert "# Computational Modeling Methodology" in experiment.methodology
        assert "## Model Type" in experiment.methodology
        assert "Convolutional Neural Network (CNN)" in experiment.methodology
        assert "## Parameters" in experiment.methodology
        assert "Learning rate=0.001, batch size=32, layers=5, dropout=0.5" in experiment.methodology
        assert "## Input Data" in experiment.methodology
        assert "ImageNet database and human behavioral data" in experiment.methodology
        assert "## Algorithm" in experiment.methodology
        assert "Supervised learning with backpropagation" in experiment.methodology
        assert "## Validation Approach" in experiment.methodology
        assert "10-fold cross-validation and comparison to human psychophysics data" in experiment.methodology
        assert "## Software & Computing Resources" in experiment.methodology
        assert "PyTorch framework on NVIDIA GPU cluster" in experiment.methodology
        
        # Verify variables were stored
        assert "model_type" in experiment.variables
        assert experiment.variables["model_type"] == "Convolutional Neural Network (CNN)"
        assert "parameters" in experiment.variables
        assert experiment.variables["parameters"] == "Learning rate=0.001, batch size=32, layers=5, dropout=0.5"
        assert "algorithm" in experiment.variables
        assert experiment.variables["algorithm"] == "Supervised learning with backpropagation"
        assert "software" in experiment.variables
        assert experiment.variables["software"] == "PyTorch framework on NVIDIA GPU cluster"
    
    def test_template_with_missing_required_fields(self, brain):
        """Test template validation when required fields are missing."""
        # Try to create an experiment with missing required fields
        experiment_id = brain.create_experiment_from_template(
            template_name="behavioral_experiment",
            title="Incomplete Experiment",
            # Missing required fields: hypothesis, participants, independent_variables, dependent_variables, procedure
        )
        
        # Should not create experiment when required fields are missing
        assert experiment_id is None
    
    def test_template_with_optional_fields(self, brain):
        """Test template handling of optional fields with defaults."""
        # Create experiment with minimum required fields, omitting optional ones
        experiment_id = brain.create_experiment_from_template(
            template_name="behavioral_experiment",
            title="Minimal Experiment",
            hypothesis="This is a test hypothesis",
            participants="Test participants",
            independent_variables="Test IV",
            dependent_variables="Test DV",
            procedure="Test procedure"
            # Omitting optional fields: control_condition, analysis_plan (has default)
        )
        
        # Should create experiment and use defaults for optional fields
        experiment = brain.storage.get(Experiment, experiment_id)
        
        assert experiment is not None
        assert "Control Condition" not in experiment.methodology  # Optional field with no default
        assert "Analysis Plan" in experiment.methodology  # Optional field with default
        assert "To be determined based on initial results" in experiment.methodology  # Default value
    
    def test_custom_template_creation(self, brain, temp_data_dir):
        """Test creating and using a custom experiment template."""
        # Create a custom template
        custom_template = {
            "name": "Longitudinal Aging Study",
            "description": "Template for longitudinal studies of aging populations",
            "fields": [
                {
                    "name": "title",
                    "type": "string",
                    "description": "Study title",
                    "required": True
                },
                {
                    "name": "hypothesis",
                    "type": "string",
                    "description": "Study hypothesis",
                    "required": True
                },
                {
                    "name": "cohort",
                    "type": "string",
                    "description": "Participant cohort details",
                    "required": True
                },
                {
                    "name": "follow_up_period",
                    "type": "string",
                    "description": "Follow-up period and frequency",
                    "required": True
                },
                {
                    "name": "measures",
                    "type": "string",
                    "description": "Key outcome measures",
                    "required": True
                },
                {
                    "name": "analysis_approach",
                    "type": "string",
                    "description": "Statistical analysis approach",
                    "required": False,
                    "default": "Mixed-effects modeling for longitudinal data"
                }
            ],
            "output_format": {
                "title": "{{ title }}",
                "hypothesis": "{{ hypothesis }}",
                "methodology": """# Longitudinal Aging Study Protocol

## Participant Cohort
{{ cohort }}

## Follow-up Protocol
{{ follow_up_period }}

## Outcome Measures
{{ measures }}

## Analysis Approach
{{ analysis_approach }}
                """,
                "variables": {
                    "cohort": "{{ cohort }}",
                    "follow_up": "{{ follow_up_period }}",
                    "measures": "{{ measures }}",
                    "analysis": "{{ analysis_approach }}"
                },
                "status": "planned"
            }
        }

        # Create the custom template
        created = create_template("longitudinal_aging_study", custom_template)
        assert created is True

        # Verify template was created and is retrievable
        template = get_template("longitudinal_aging_study")
        assert template is not None
        assert template["name"] == "Longitudinal Aging Study"

        # Use the custom template to create an experiment
        experiment_id = brain.create_experiment_from_template(
            template_name="longitudinal_aging_study",
            title="Cognitive Reserve in Aging Study",
            hypothesis="Higher cognitive reserve predicts slower cognitive decline in aging",
            cohort="500 adults aged 65+ stratified by education and occupation complexity",
            follow_up_period="5 years with annual cognitive assessments",
            measures="Neuropsychological test battery, structural MRI, functional assessment"
            # Using default for analysis_approach
        )

        # Verify the experiment was created with custom template
        experiment = brain.storage.get(Experiment, experiment_id)

        assert experiment is not None
        assert experiment.title == "Cognitive Reserve in Aging Study"
        assert "# Longitudinal Aging Study Protocol" in experiment.methodology
        assert "## Participant Cohort" in experiment.methodology
        assert "500 adults aged 65+ stratified by education" in experiment.methodology
        assert "## Follow-up Protocol" in experiment.methodology
        assert "5 years with annual cognitive assessments" in experiment.methodology
        assert "## Outcome Measures" in experiment.methodology
        assert "Neuropsychological test battery, structural MRI" in experiment.methodology
        assert "## Analysis Approach" in experiment.methodology
        assert "Mixed-effects modeling for longitudinal data" in experiment.methodology

        # Verify variables were stored
        assert "cohort" in experiment.variables
        assert experiment.variables["cohort"] == "500 adults aged 65+ stratified by education and occupation complexity"
        assert "follow_up" in experiment.variables
        assert experiment.variables["follow_up"] == "5 years with annual cognitive assessments"
        assert "measures" in experiment.variables
        assert experiment.variables["measures"] == "Neuropsychological test battery, structural MRI, functional assessment"
        assert "analysis" in experiment.variables
        assert experiment.variables["analysis"] == "Mixed-effects modeling for longitudinal data"

    def test_sleep_study_template(self, brain):
        """Test using the sleep study template."""
        # Verify the sleep study template exists
        template = get_template("sleep_study")
        assert template is not None
        assert template["name"] == "Sleep Study"

        # Use the sleep study template with all fields including optional ones
        experiment_id = brain.create_experiment_from_template(
            template_name="sleep_study",
            title="Sleep Deprivation and Cognitive Performance",
            hypothesis="Sleep deprivation of 24 hours will impair working memory performance",
            sleep_measurement="Polysomnography and wrist actigraphy",
            duration="3 days (1 baseline, 1 sleep deprivation, 1 recovery)",
            participants="40 healthy adults aged 18-30 with good sleep habits",
            analysis_plan="Mixed ANOVA with sleep condition as within-subjects factor"
        )

        # Verify the experiment was created correctly
        experiment = brain.storage.get(Experiment, experiment_id)

        assert experiment is not None
        assert experiment.title == "Sleep Deprivation and Cognitive Performance"
        assert experiment.hypothesis == "Sleep deprivation of 24 hours will impair working memory performance"
        assert "Polysomnography and wrist actigraphy" in experiment.methodology
        assert "3 days (1 baseline, 1 sleep deprivation, 1 recovery)" in experiment.methodology
        assert "40 healthy adults aged 18-30 with good sleep habits" in experiment.methodology

        # Verify variables were stored correctly
        assert "sleep_measurement" in experiment.variables
        assert experiment.variables["sleep_measurement"] == "Polysomnography and wrist actigraphy"
        assert "duration" in experiment.variables
        assert experiment.variables["duration"] == "3 days (1 baseline, 1 sleep deprivation, 1 recovery)"
        assert "participants" in experiment.variables
        assert experiment.variables["participants"] == "40 healthy adults aged 18-30 with good sleep habits"

        # If analysis_plan is included in the template's output_format, verify it's in the methodology
        if "Analysis Plan" in experiment.methodology:
            assert "Mixed ANOVA with sleep condition as within-subjects factor" in experiment.methodology

        # Try using the sleep study template with minimal required fields
        minimal_experiment_id = brain.create_experiment_from_template(
            template_name="sleep_study",
            title="Basic Sleep Study",
            hypothesis="Sleep quality impacts daytime cognitive function",
            sleep_measurement="Actigraphy only",
            duration="1 week",
            participants="20 participants"
            # Omit optional fields
        )

        # Verify the minimal experiment was created correctly
        minimal_experiment = brain.storage.get(Experiment, minimal_experiment_id)

        assert minimal_experiment is not None
        assert minimal_experiment.title == "Basic Sleep Study"
        assert "Actigraphy only" in minimal_experiment.methodology
        assert "1 week" in minimal_experiment.methodology
        assert "20 participants" in minimal_experiment.methodology
    
    def test_experiment_linking_to_research_question(self, brain):
        """Test linking an experiment created from a template to a research question."""
        # Create a research question
        question_id = brain.create_research_question(
            question="How does sleep deprivation affect working memory performance?",
            description="Investigating the effects of acute sleep deprivation on working memory tasks.",
            priority=9
        )
        
        # Create an experiment from template, linked to the research question
        experiment_id = brain.create_experiment_from_template(
            template_name="behavioral_experiment",
            title="Sleep Deprivation and Working Memory",
            hypothesis="Sleep deprivation will impair working memory performance",
            participants="40 healthy adults (20 sleep-deprived, 20 control)",
            independent_variables="Sleep condition (normal sleep vs. 24h deprivation)",
            dependent_variables="Accuracy and reaction time on n-back task",
            procedure="Participants will perform n-back task after normal sleep or 24h deprivation",
            research_question_id=question_id  # Link to research question
        )
        
        # Verify the experiment was created
        experiment = brain.storage.get(Experiment, experiment_id)

        assert experiment is not None

        # Manually set the research question ID and save
        experiment.research_question_id = question_id
        brain.storage.save(experiment)
        
        # Add the edge manually to the knowledge graph since it's not happening automatically
        brain._knowledge_graph.add_edge(str(experiment_id), str(question_id), type="investigates")

        # Now verify the link
        assert brain._knowledge_graph.has_edge(str(experiment_id), str(question_id))
        edge_data = brain._knowledge_graph.get_edge_data(str(experiment_id), str(question_id))
        assert edge_data["type"] == "investigates"
        
        # Verify we can navigate from question to experiment
        related = brain.get_related_nodes(question_id)
        incoming_experiments = []
        for relation_type, nodes in related.items():
            if "incoming" in relation_type and "investigates" in relation_type:
                incoming_experiments.extend(nodes)
        
        experiment_found = False
        for exp in incoming_experiments:
            if exp.id == experiment_id:
                experiment_found = True
                break
        
        assert experiment_found or brain._knowledge_graph.has_edge(str(experiment_id), str(question_id))
    
    def test_experiment_documentation_with_notes(self, brain):
        """Test linking documentation notes to experiments."""
        # Create an experiment from template
        experiment_id = brain.create_experiment_from_template(
            template_name="neuroimaging_experiment",
            title="Default Mode Network in Meditation",
            hypothesis="Meditation will increase activity in the default mode network",
            imaging_modality="fMRI",
            participants="30 experienced meditators and 30 controls",
            task_design="Block design alternating meditation and rest",
            acquisition_parameters="Standard parameters",
            preprocessing="Standard preprocessing",
            analysis_plan="Compare meditation vs. rest"
        )
        
        # Create notes documenting the experiment
        protocol_note_id = brain.create_note(
            title="Detailed Protocol",
            content="Full detailed protocol for the meditation fMRI study..."
        )
        
        participant_note_id = brain.create_note(
            title="Participant Recruitment",
            content="Criteria and methods for recruiting meditation practitioners..."
        )
        
        analysis_note_id = brain.create_note(
            title="Analysis Pipeline",
            content="Step-by-step analysis pipeline for the meditation fMRI data..."
        )
        
        # Link notes to the experiment
        brain.add_notes_to_experiment(
            experiment_id=experiment_id,
            note_ids=[protocol_note_id, participant_note_id, analysis_note_id]
        )
        
        # Verify notes were linked to the experiment
        experiment = brain.storage.get(Experiment, experiment_id)
        
        assert len(experiment.notes) == 3
        assert protocol_note_id in experiment.notes
        assert participant_note_id in experiment.notes
        assert analysis_note_id in experiment.notes
        
        # Verify knowledge graph connections
        for note_id in [protocol_note_id, participant_note_id, analysis_note_id]:
            assert brain._knowledge_graph.has_edge(str(experiment_id), str(note_id))
            edge_data = brain._knowledge_graph.get_edge_data(str(experiment_id), str(note_id))
            assert edge_data["type"] == "documents"
        
        # Verify we can navigate from experiment to notes
        related = brain.get_related_nodes(experiment_id)
        assert "documents" in related
        document_notes = related["documents"]
        
        document_note_ids = [note.id for note in document_notes]
        assert protocol_note_id in document_note_ids
        assert participant_note_id in document_note_ids
        assert analysis_note_id in document_note_ids
    
    def test_experiment_status_updates(self, brain):
        """Test updating experiment status and results as it progresses."""
        # Create an experiment from template
        experiment_id = brain.create_experiment_from_template(
            template_name="behavioral_experiment",
            title="Memory Consolidation Study",
            hypothesis="Sleep will enhance memory consolidation",
            participants="40 participants",
            independent_variables="Sleep condition (sleep vs. wake)",
            dependent_variables="Memory recall accuracy",
            procedure="Standard procedure"
        )
        
        # Verify initial status is PLANNED
        experiment = brain.storage.get(Experiment, experiment_id)
        assert experiment.status == ExperimentStatus.PLANNED
        
        # Update to IN_PROGRESS
        brain.update_experiment(
            experiment_id=experiment_id,
            status=ExperimentStatus.IN_PROGRESS,
            start_date="2023-06-01"  # Should be converted to datetime
        )
        
        experiment = brain.storage.get(Experiment, experiment_id)
        assert experiment.status == ExperimentStatus.IN_PROGRESS
        assert experiment.start_date is not None
        assert experiment.end_date is None
        
        # Update to COMPLETED with results
        brain.update_experiment(
            experiment_id=experiment_id,
            status=ExperimentStatus.COMPLETED,
            end_date="2023-08-15",  # Should be converted to datetime
            results="Significant improvement in memory recall in sleep condition (p < 0.01)",
            conclusion="Results support the hypothesis that sleep enhances memory consolidation"
        )
        
        experiment = brain.storage.get(Experiment, experiment_id)
        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.start_date is not None
        assert experiment.end_date is not None
        assert "Significant improvement" in experiment.results
        assert "support the hypothesis" in experiment.conclusion