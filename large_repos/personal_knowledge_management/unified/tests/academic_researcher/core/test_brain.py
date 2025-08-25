"""Integration tests for the ResearchBrain system."""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import networkx as nx
import pytest

from researchbrain.core.brain import ResearchBrain
from researchbrain.core.models import (
    Citation, EvidenceStrength, EvidenceType, Experiment, GrantProposal,
    ExperimentStatus, GrantStatus, ResearchQuestion
)


class TestResearchBrain:
    """Integration tests for the ResearchBrain class."""
    
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
    
    def test_create_and_get_note(self, brain):
        """Test creating and retrieving a note."""
        # Create a note
        note_id = brain.create_note(
            title="Test Note",
            content="This is a test note with a citation [@smith2023].",
            tags={"test", "research"}
        )
        
        # Retrieve the note
        note = brain.get_note(note_id)
        
        assert note is not None
        assert note.id == note_id
        assert note.title == "Test Note"
        assert note.content == "This is a test note with a citation [@smith2023]."
        assert note.tags == {"test", "research"}
    
    def test_update_note(self, brain):
        """Test updating a note."""
        # Create a note
        note_id = brain.create_note(
            title="Original Title",
            content="Original content",
            tags={"original"}
        )
        
        # Update the note
        updated = brain.update_note(
            note_id=note_id,
            title="Updated Title",
            content="Updated content",
            tags={"updated", "research"}
        )
        
        assert updated is True
        
        # Retrieve the updated note
        note = brain.get_note(note_id)
        
        assert note.title == "Updated Title"
        assert note.content == "Updated content"
        assert note.tags == {"updated", "research"}
    
    def test_delete_note(self, brain):
        """Test deleting a note."""
        # Create a note
        note_id = brain.create_note(
            title="Note to Delete",
            content="This note will be deleted"
        )
        
        # Verify the note exists
        assert brain.get_note(note_id) is not None
        
        # Delete the note
        deleted = brain.delete_note(note_id)
        
        assert deleted is True
        assert brain.get_note(note_id) is None
    
    def test_create_citation_and_link_note(self, brain):
        """Test creating a citation and linking it to a note."""
        # Create a citation
        citation_id = brain.create_citation(
            title="Test Paper",
            authors=["Smith, John", "Doe, Jane"],
            year=2023,
            journal="Journal of Testing"
        )
        
        # Create a note
        note_id = brain.create_note(
            title="Note about Test Paper",
            content="This note references the test paper."
        )
        
        # Link the note to the citation
        linked = brain.link_note_to_paper(note_id, citation_id, page=42)
        
        assert linked is True
        
        # Retrieve the note and verify the link
        note = brain.get_note(note_id)
        citation = brain.storage.get(Citation, citation_id)
        
        assert note.source == citation_id
        assert note.page_reference == 42
        assert citation_id in note.citations
        assert note_id in citation.notes
        
        # Check knowledge graph connections
        assert brain._knowledge_graph.has_edge(str(note_id), str(citation_id))
        assert brain._knowledge_graph.has_edge(str(citation_id), str(note_id))
    
    def test_create_research_question_and_add_evidence(self, brain):
        """Test creating a research question and adding evidence."""
        # Create a note with evidence
        note_id = brain.create_note(
            title="Evidence Note",
            content="This note contains evidence for a research question."
        )
        
        # Create a citation
        citation_id = brain.create_citation(
            title="Supporting Paper",
            authors=["Researcher, A"],
            year=2023
        )
        
        # Create a research question
        question_id = brain.create_research_question(
            question="How does X affect Y?",
            description="Investigating the relationship between X and Y",
            tags={"x", "y", "relationship"},
            priority=8
        )
        
        # Add evidence to the question
        evidence_id = brain.add_evidence_to_question(
            question_id=question_id,
            note_id=note_id,
            evidence_type=EvidenceType.SUPPORTING,
            strength=EvidenceStrength.STRONG,
            description="Strong experimental evidence",
            citation_ids=[citation_id]
        )
        
        assert evidence_id is not None
        
        # Retrieve the question and verify the evidence
        question = brain.storage.get(ResearchQuestion, question_id)
        
        assert len(question.evidence) == 1
        assert question.evidence[0].note_id == note_id
        assert question.evidence[0].evidence_type == EvidenceType.SUPPORTING
        assert question.evidence[0].strength == EvidenceStrength.STRONG
        assert question.evidence[0].description == "Strong experimental evidence"
        assert citation_id in question.evidence[0].citation_ids
        
        # Check knowledge graph connections
        assert brain._knowledge_graph.has_edge(str(question_id), str(note_id))
        edge_data = brain._knowledge_graph.get_edge_data(str(question_id), str(note_id))
        assert edge_data["type"] == "evidence"
        assert edge_data["evidence_type"] == EvidenceType.SUPPORTING
        assert edge_data["strength"] == EvidenceStrength.STRONG
    
    def test_create_experiment(self, brain):
        """Test creating an experiment."""
        # Create a research question
        question_id = brain.create_research_question(
            question="What is the effect of drug X on condition Y?",
            priority=9
        )
        
        # Create an experiment
        experiment_id = brain.create_experiment(
            title="Clinical Trial of Drug X",
            hypothesis="Drug X reduces symptoms of condition Y",
            methodology="Randomized controlled trial with 100 participants",
            status=ExperimentStatus.PLANNED,
            research_question_id=question_id,
            variables={"dose": "10mg", "duration": "8 weeks"}
        )
        
        # Retrieve the experiment
        experiment = brain.storage.get(Experiment, experiment_id)
        
        assert experiment is not None
        assert experiment.title == "Clinical Trial of Drug X"
        assert experiment.hypothesis == "Drug X reduces symptoms of condition Y"
        assert experiment.methodology == "Randomized controlled trial with 100 participants"
        assert experiment.status == ExperimentStatus.PLANNED
        assert experiment.research_question_id == question_id
        assert experiment.variables == {"dose": "10mg", "duration": "8 weeks"}
        
        # Check knowledge graph connections
        assert brain._knowledge_graph.has_edge(str(experiment_id), str(question_id))
        edge_data = brain._knowledge_graph.get_edge_data(str(experiment_id), str(question_id))
        assert edge_data["type"] == "investigates"
    
    def test_create_grant_proposal_and_add_items(self, brain):
        """Test creating a grant proposal and adding items to it."""
        # Create notes, experiments, and questions
        note_id = brain.create_note(
            title="Background Research",
            content="Literature review for grant proposal"
        )
        
        question_id = brain.create_research_question(
            question="How can we improve treatment X?",
            priority=9
        )
        
        experiment_id = brain.create_experiment(
            title="Preliminary Study",
            hypothesis="Treatment X works better with modification Y",
            methodology="Study design details",
            research_question_id=question_id
        )
        
        # Create a grant proposal
        grant_id = brain.create_grant_proposal(
            title="Improving Treatment X",
            funding_agency="NIH",
            description="A proposal to investigate improvements to treatment X",
            deadline=datetime(2024, 6, 30),
            status=GrantStatus.DRAFTING,
            amount=500000.0
        )
        
        # Add items to the grant workspace
        added = brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=[note_id],
            experiment_ids=[experiment_id],
            question_ids=[question_id]
        )
        
        assert added is True
        
        # Retrieve the grant proposal
        grant = brain.storage.get(GrantProposal, grant_id)
        
        assert note_id in grant.notes
        assert experiment_id in grant.experiments
        assert question_id in grant.research_questions
        
        # Check knowledge graph connections
        assert brain._knowledge_graph.has_edge(str(grant_id), str(note_id))
        assert brain._knowledge_graph.has_edge(str(grant_id), str(experiment_id))
        assert brain._knowledge_graph.has_edge(str(grant_id), str(question_id))
    
    def test_search(self, brain):
        """Test searching the knowledge base."""
        # Create some test data with a common theme
        brain.create_note(
            title="Neuroplasticity Research",
            content="Recent findings about brain plasticity"
        )
        
        brain.create_citation(
            title="Neuroplasticity in Adults",
            authors=["Smith, J"],
            year=2023,
            abstract="Research on adult neuroplasticity"
        )
        
        brain.create_research_question(
            question="How does exercise affect neuroplasticity?",
            priority=7
        )
        
        # Search for "neuroplasticity"
        results = brain.search("neuroplasticity")
        
        assert "notes" in results
        assert "citations" in results
        assert "questions" in results
        
        assert len(results["notes"]) == 1
        assert results["notes"][0].title == "Neuroplasticity Research"
        
        assert len(results["citations"]) == 1
        assert results["citations"][0].title == "Neuroplasticity in Adults"
        
        assert len(results["questions"]) == 1
        assert results["questions"][0].question == "How does exercise affect neuroplasticity?"
    
    def test_get_related_nodes(self, brain):
        """Test retrieving related nodes."""
        # Create interconnected test data
        note_id = brain.create_note(
            title="Research Note",
            content="Research findings"
        )
        
        citation_id = brain.create_citation(
            title="Related Paper",
            authors=["Author, A"]
        )
        
        brain.link_note_to_paper(note_id, citation_id)
        
        question_id = brain.create_research_question(
            question="Research Question"
        )
        
        brain.add_evidence_to_question(
            question_id=question_id,
            note_id=note_id,
            evidence_type=EvidenceType.SUPPORTING,
            strength=EvidenceStrength.MODERATE
        )
        
        # Get related nodes for the note
        related = brain.get_related_nodes(note_id)

        assert "references" in related
        assert "incoming_evidence" in related

        assert len(related["references"]) == 1
        assert related["references"][0].id == citation_id
        
        assert len(related["incoming_evidence"]) == 1
        assert related["incoming_evidence"][0].id == question_id
        
        # Get related nodes for the question
        related = brain.get_related_nodes(question_id)
        
        assert "evidence" in related
        assert len(related["evidence"]) == 1
        assert related["evidence"][0].id == note_id
    
    def test_create_collaborator_and_annotation(self, brain):
        """Test creating a collaborator and adding annotations."""
        # Create a note to annotate
        note_id = brain.create_note(
            title="Note to Annotate",
            content="This note will receive annotations"
        )
        
        # Create a collaborator
        collaborator_id = brain.create_collaborator(
            name="Jane Smith",
            email="jane@example.com",
            affiliation="University of Testing"
        )
        
        # Add an annotation
        annotation_id = brain.add_annotation(
            node_id=note_id,
            collaborator_id=collaborator_id,
            content="This is an important finding",
            position="paragraph 2"
        )
        
        assert annotation_id is not None
        
        # Get annotations for the note
        annotations = brain.get_annotations_for_node(note_id)
        
        assert len(annotations) == 1
        assert annotations[0].node_id == note_id
        assert annotations[0].collaborator_id == collaborator_id
        assert annotations[0].content == "This is an important finding"
        assert annotations[0].position == "paragraph 2"
    
    def test_generate_citation(self, brain):
        """Test generating formatted citations."""
        # Create a citation
        citation_id = brain.create_citation(
            title="Citation Formatting Test",
            authors=["Smith, John", "Doe, Jane"],
            year=2023,
            journal="Journal of Citation Formatting",
            volume="10",
            issue="2",
            pages="123-145",
            doi="10.1234/example"
        )
        
        # Generate APA style citation
        apa_citation = brain.generate_citation(citation_id, "apa")
        
        assert "Smith, John & Doe, Jane" in apa_citation
        assert "(2023)" in apa_citation
        assert "Citation Formatting Test" in apa_citation
        assert "Journal of Citation Formatting" in apa_citation
        
        # Generate MLA style citation
        mla_citation = brain.generate_citation(citation_id, "mla")
        
        assert "Smith, John and Doe, Jane" in mla_citation
        assert "Citation Formatting Test" in mla_citation
        assert "Journal of Citation Formatting" in mla_citation
        assert "2023" in mla_citation
    
    def test_backup_and_restore(self, brain, temp_data_dir):
        """Test backing up and restoring the knowledge base."""
        # Create some test data
        note_id = brain.create_note(
            title="Backup Test Note",
            content="Testing backup and restore functionality"
        )
        
        citation_id = brain.create_citation(
            title="Backup Test Citation",
            authors=["Author, Test"]
        )
        
        # Create a backup
        backup_dir = Path(temp_data_dir) / "backups"
        backup_path = brain.backup_knowledge_base(backup_dir)
        
        assert backup_path is not None
        assert backup_path.exists()
        
        # Delete the test data
        brain.delete_note(note_id)
        assert brain.get_note(note_id) is None
        
        # Restore from backup
        restored = brain.restore_from_backup(backup_path)
        
        assert restored is True
        
        # Verify data was restored
        restored_note = brain.get_note(note_id)
        restored_citation = brain.storage.get(Citation, citation_id)
        
        assert restored_note is not None
        assert restored_note.title == "Backup Test Note"
        assert restored_citation is not None
        assert restored_citation.title == "Backup Test Citation"
    
    def test_knowledge_graph_structure(self, brain):
        """Test the knowledge graph structure with various interconnected nodes."""
        # Create interconnected test data
        note1_id = brain.create_note(title="Note 1", content="Content 1")
        note2_id = brain.create_note(title="Note 2", content="Content 2")
        
        citation_id = brain.create_citation(title="Citation", authors=["Author"])
        
        question_id = brain.create_research_question(question="Question")
        
        experiment_id = brain.create_experiment(
            title="Experiment",
            hypothesis="Hypothesis",
            methodology="Methodology",
            research_question_id=question_id
        )
        
        grant_id = brain.create_grant_proposal(
            title="Grant",
            funding_agency="Agency",
            description="Description"
        )
        
        # Create connections
        brain.link_note_to_paper(note1_id, citation_id)
        
        brain.add_evidence_to_question(
            question_id=question_id,
            note_id=note2_id,
            evidence_type=EvidenceType.SUPPORTING,
            strength=EvidenceStrength.STRONG
        )
        
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=[note1_id],
            experiment_ids=[experiment_id],
            question_ids=[question_id]
        )
        
        # Check graph structure
        graph = brain._knowledge_graph
        
        # Verify nodes
        assert graph.has_node(str(note1_id))
        assert graph.has_node(str(note2_id))
        assert graph.has_node(str(citation_id))
        assert graph.has_node(str(question_id))
        assert graph.has_node(str(experiment_id))
        assert graph.has_node(str(grant_id))
        
        # Verify edges
        assert graph.has_edge(str(note1_id), str(citation_id))  # Note cites citation
        assert graph.has_edge(str(citation_id), str(note1_id))  # Citation cited in note
        
        assert graph.has_edge(str(question_id), str(note2_id))  # Question has evidence in note
        
        assert graph.has_edge(str(experiment_id), str(question_id))  # Experiment investigates question
        
        assert graph.has_edge(str(grant_id), str(note1_id))  # Grant includes note
        assert graph.has_edge(str(grant_id), str(experiment_id))  # Grant proposes experiment
        assert graph.has_edge(str(grant_id), str(question_id))  # Grant addresses question