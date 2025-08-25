"""Integration tests for common user workflows."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from researchbrain.core.brain import ResearchBrain
from researchbrain.core.models import (
    EvidenceStrength, EvidenceType, ExperimentStatus, GrantStatus,
    Citation, Experiment, Note, ResearchQuestion, GrantProposal, Collaborator, Annotation
)


class TestUserWorkflows:
    """Integration tests for common user workflows."""
    
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
    
    def test_workflow_paper_import_to_note_creation(self, brain, tmp_path):
        """Test workflow: paper import -> citation linking -> note creation."""
        # Create a mock BibTeX file
        bibtex_path = tmp_path / "test_paper.bib"
        with open(bibtex_path, "w") as f:
            f.write("""
@article{smith2023neuroscience,
  title={Advances in Neuroscience Research},
  author={Smith, John and Doe, Jane},
  journal={Journal of Neuroscience},
  volume={42},
  number={3},
  pages={123-145},
  year={2023},
  publisher={Neuroscience Publishers},
  doi={10.1234/neuro.2023.42.3.123}
}
            """)
        
        # Import the paper
        citation_id = brain.import_paper(bibtex_path)
        
        assert citation_id is not None
        
        # Create a note referencing the paper
        note_id = brain.create_note(
            title="Notes on Smith & Doe (2023)",
            content="The paper by Smith and Doe [-@smith2023neuroscience] presents interesting findings about neural plasticity.",
            tags={"neuroscience", "plasticity", "research"}
        )
        
        # Link the note to the paper
        linked = brain.link_note_to_paper(note_id, citation_id, page=42)
        
        assert linked is True
        
        # Retrieve the note and verify
        note = brain.get_note(note_id)
        citation = brain.storage.get(Citation, citation_id)

        assert note.source == citation_id
        assert note.page_reference == 42
        assert citation_id in note.citations
        assert note_id in citation.notes
        
        # Check that the citation is properly formatted
        apa_citation = brain.generate_citation(citation_id, "apa")
        assert "Smith, John & Doe, Jane" in apa_citation
        assert "(2023)" in apa_citation
        assert "Advances in Neuroscience Research" in apa_citation
        assert "Journal of Neuroscience" in apa_citation
    
    def test_workflow_research_question_analysis(self, brain):
        """Test workflow: research question -> evidence evaluation with conflicting evidence."""
        # Create a research question
        question_id = brain.create_research_question(
            question="Does neuroplasticity decline with age?",
            description="Investigating the relationship between aging and neural plasticity",
            priority=9
        )
        
        # Create supporting evidence
        supporting_note_id = brain.create_note(
            title="Supporting Evidence",
            content="Studies by Smith et al. show clear decline in plasticity after age 60."
        )
        
        supporting_citation_id = brain.create_citation(
            title="Neural Plasticity in Aging",
            authors=["Smith, J", "Johnson, A"],
            year=2022,
            journal="Aging Neuroscience"
        )
        
        brain.link_note_to_paper(supporting_note_id, supporting_citation_id)
        
        # Add supporting evidence to the question
        brain.add_evidence_to_question(
            question_id=question_id,
            note_id=supporting_note_id,
            evidence_type=EvidenceType.SUPPORTING,
            strength=EvidenceStrength.STRONG,
            description="Strong evidence showing plasticity decline with age",
            citation_ids=[supporting_citation_id]
        )
        
        # Create contradicting evidence
        contradicting_note_id = brain.create_note(
            title="Contradicting Evidence",
            content="Recent work by Brown et al. suggests plasticity can be maintained with mental exercise."
        )
        
        contradicting_citation_id = brain.create_citation(
            title="Maintaining Neural Plasticity in Older Adults",
            authors=["Brown, R", "Garcia, M"],
            year=2023,
            journal="Cognitive Aging"
        )
        
        brain.link_note_to_paper(contradicting_note_id, contradicting_citation_id)
        
        # Add contradicting evidence to the question
        brain.add_evidence_to_question(
            question_id=question_id,
            note_id=contradicting_note_id,
            evidence_type=EvidenceType.CONTRADICTING,
            strength=EvidenceStrength.MODERATE,
            description="Evidence that challenges the universal decline model",
            citation_ids=[contradicting_citation_id]
        )
        
        # Retrieve the research question and verify the evidence
        question = brain.storage.get(ResearchQuestion, question_id)

        assert len(question.evidence) == 2
        
        # Verify that both supporting and contradicting evidence are present
        evidence_types = [e.evidence_type for e in question.evidence]
        assert EvidenceType.SUPPORTING in evidence_types
        assert EvidenceType.CONTRADICTING in evidence_types
        
        # Get related nodes for the question
        related = brain.get_related_nodes(question_id)
        
        assert "evidence" in related
        assert len(related["evidence"]) == 2
    
    def test_workflow_grant_proposal_assembly(self, brain):
        """Test workflow: grant proposal assembly from distributed knowledge elements."""
        # Create several elements that will go into a grant proposal
        
        # 1. Create research questions
        question1_id = brain.create_research_question(
            question="How does intervention X affect cognition in elderly population?",
            priority=9
        )
        
        question2_id = brain.create_research_question(
            question="What neural mechanisms underlie the effects of intervention X?",
            priority=8
        )
        
        # 2. Create notes with background research
        background_note_id = brain.create_note(
            title="Literature Review",
            content="Comprehensive review of prior research on intervention X."
        )
        
        methods_note_id = brain.create_note(
            title="Proposed Methods",
            content="Detailed description of the experimental methods."
        )
        
        budget_note_id = brain.create_note(
            title="Budget Justification",
            content="Justification for the requested funds."
        )
        
        # 3. Create experiments
        pilot_experiment_id = brain.create_experiment(
            title="Pilot Study",
            hypothesis="Intervention X improves cognitive function",
            methodology="Small-scale trial with 20 participants",
            status=ExperimentStatus.COMPLETED,
            results="Observed 15% improvement in cognitive scores",
            research_question_id=question1_id
        )
        
        proposed_experiment_id = brain.create_experiment(
            title="Full-Scale Study",
            hypothesis="Intervention X improves cognitive function and increases neural activity",
            methodology="Randomized controlled trial with 100 participants, fMRI component",
            status=ExperimentStatus.PLANNED,
            research_question_id=question1_id
        )
        
        mechanism_experiment_id = brain.create_experiment(
            title="Mechanism Investigation",
            hypothesis="Intervention X works through mechanism Y",
            methodology="Cellular and molecular analysis",
            status=ExperimentStatus.PLANNED,
            research_question_id=question2_id
        )
        
        # 4. Create the grant proposal
        grant_id = brain.create_grant_proposal(
            title="Effects of Intervention X on Cognitive Aging",
            funding_agency="National Institute on Aging",
            description="A comprehensive study of intervention X for cognitive aging",
            deadline=None,  # No deadline yet
            status=GrantStatus.DRAFTING,
            amount=750000.0
        )
        
        # 5. Add items to the grant workspace
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=[background_note_id, methods_note_id, budget_note_id],
            experiment_ids=[pilot_experiment_id, proposed_experiment_id, mechanism_experiment_id],
            question_ids=[question1_id, question2_id]
        )
        
        # Verify the grant proposal
        grant = brain.storage.get(GrantProposal, grant_id)

        assert len(grant.notes) == 3
        assert len(grant.experiments) == 3
        assert len(grant.research_questions) == 2
        
        # Export the grant proposal
        export_path = Path(tempfile.gettempdir()) / "grant_proposal.md"
        exported = brain.export_grant_proposal(grant_id, export_path)
        
        assert exported is True
        assert export_path.exists()
        
        # Verify export content
        with open(export_path, "r") as f:
            content = f.read()
        
        assert "Effects of Intervention X on Cognitive Aging" in content
        assert "National Institute on Aging" in content
        assert "Research Questions" in content
        assert "Proposed Experiments" in content
        assert "Pilot Study" in content
        assert "Full-Scale Study" in content
        assert "Mechanism Investigation" in content
        assert "Supporting Notes" in content
        
        # Clean up
        export_path.unlink()
    
    def test_workflow_collaborative_annotation(self, brain):
        """Test workflow: collaborative review and annotation of research materials."""
        # 1. Create a note to be annotated
        note_id = brain.create_note(
            title="Draft Manuscript",
            content="Abstract\nIntroduction\nMethods\nResults\nDiscussion\nConclusion"
        )
        
        # 2. Create collaborators
        advisor_id = brain.create_collaborator(
            name="Dr. Johnson",
            email="johnson@university.edu",
            affiliation="University of Science",
            role="advisor"
        )
        
        colleague_id = brain.create_collaborator(
            name="Dr. Smith",
            email="smith@university.edu",
            affiliation="University of Research",
            role="collaborator"
        )
        
        student_id = brain.create_collaborator(
            name="Graduate Student",
            email="student@university.edu",
            affiliation="University of Science",
            role="student"
        )
        
        # 3. Add annotations from different collaborators
        advisor_annotation_id = brain.add_annotation(
            node_id=note_id,
            collaborator_id=advisor_id,
            content="The introduction needs more context about prior research.",
            position="Introduction"
        )
        
        colleague_annotation_id = brain.add_annotation(
            node_id=note_id,
            collaborator_id=colleague_id,
            content="Consider adding a figure to illustrate the results.",
            position="Results"
        )
        
        student_annotation_id = brain.add_annotation(
            node_id=note_id,
            collaborator_id=student_id,
            content="Added additional statistical analysis as suggested.",
            position="Methods"
        )
        
        # 4. Retrieve annotations for the note
        annotations = brain.get_annotations_for_node(note_id)
        
        assert len(annotations) == 3
        
        # Verify annotations from different collaborators
        advisor_annotations = [a for a in annotations if a.collaborator_id == advisor_id]
        colleague_annotations = [a for a in annotations if a.collaborator_id == colleague_id]
        student_annotations = [a for a in annotations if a.collaborator_id == student_id]
        
        assert len(advisor_annotations) == 1
        assert len(colleague_annotations) == 1
        assert len(student_annotations) == 1
        
        assert advisor_annotations[0].position == "Introduction"
        assert colleague_annotations[0].position == "Results"
        assert student_annotations[0].position == "Methods"
    
    def test_workflow_experiment_documentation(self, brain):
        """Test workflow: experiment documentation with template-guided metadata."""
        # 1. Create an experiment from a template
        experiment_id = brain.create_experiment_from_template(
            template_name="behavioral_experiment",
            title="Memory Recall Experiment",
            hypothesis="Regular exercise improves memory recall in older adults",
            participants="60 adults aged 65-80, randomized into exercise and control groups",
            independent_variables="Exercise regimen (none vs. 30 min daily walking)",
            dependent_variables="Memory recall scores on standardized tests",
            control_condition="No exercise regimen",
            procedure="Participants will be tested at baseline, 6 weeks, and 12 weeks",
            analysis_plan="Mixed ANOVA with follow-up t-tests"
        )
        
        assert experiment_id is not None
        
        # 2. Retrieve the experiment and verify template application
        experiment = brain.storage.get(Experiment, experiment_id)

        assert experiment.title == "Memory Recall Experiment"
        assert experiment.hypothesis == "Regular exercise improves memory recall in older adults"
        assert "Behavioral Experiment Methodology" in experiment.methodology
        assert "60 adults aged 65-80" in experiment.methodology
        assert "Exercise regimen" in experiment.methodology
        assert "Memory recall scores" in experiment.methodology
        assert "No exercise regimen" in experiment.methodology
        assert "tested at baseline, 6 weeks, and 12 weeks" in experiment.methodology
        assert "Mixed ANOVA" in experiment.methodology
        
        assert experiment.status == ExperimentStatus.PLANNED
        assert "participants" in experiment.variables
        assert "independent_vars" in experiment.variables
        assert "dependent_vars" in experiment.variables
        
        # 3. Create research question related to experiment
        question_id = brain.create_research_question(
            question="How does exercise affect memory in older adults?",
            priority=8
        )
        
        # Update the experiment to link it to the research question
        brain.update_experiment(
            experiment_id=experiment_id,
            research_question_id=question_id
        )
        
        # Verify the link
        experiment = brain.storage.get(Experiment, experiment_id)
        assert experiment.research_question_id == question_id
        
        # 4. Create notes documenting the experiment
        protocol_note_id = brain.create_note(
            title="Detailed Protocol",
            content="Step-by-step protocol for the memory recall experiment."
        )
        
        ethics_note_id = brain.create_note(
            title="Ethics Approval",
            content="Documentation of IRB approval for the experiment."
        )
        
        # Link notes to the experiment
        brain.add_notes_to_experiment(
            experiment_id=experiment_id,
            note_ids=[protocol_note_id, ethics_note_id]
        )
        
        # Verify links
        experiment = brain.storage.get(Experiment, experiment_id)
        assert protocol_note_id in experiment.notes
        assert ethics_note_id in experiment.notes