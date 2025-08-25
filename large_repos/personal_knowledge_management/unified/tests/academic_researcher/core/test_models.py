"""Tests for the core data models."""

import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from researchbrain.core.models import (
    Citation, CitationType, Collaborator, CollaboratorRole, Evidence,
    EvidenceStrength, EvidenceType, Experiment, ExperimentStatus, GrantProposal,
    GrantStatus, KnowledgeNode, Note, ResearchQuestion
)


class TestKnowledgeNode:
    """Tests for the KnowledgeNode base class."""
    
    def test_init_default_values(self):
        """Test initialization with default values."""
        node = KnowledgeNode()
        
        assert isinstance(node.id, UUID)
        assert isinstance(node.created_at, datetime.datetime)
        assert isinstance(node.updated_at, datetime.datetime)
        assert node.tags == set()
    
    def test_init_custom_values(self):
        """Test initialization with custom values."""
        test_id = uuid4()
        test_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        test_tags = {"tag1", "tag2"}
        
        node = KnowledgeNode(
            id=test_id,
            created_at=test_time,
            updated_at=test_time,
            tags=test_tags
        )
        
        assert node.id == test_id
        assert node.created_at == test_time
        assert node.updated_at == test_time
        assert node.tags == test_tags
    
    def test_update_method(self):
        """Test the update method updates the timestamp."""
        test_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        node = KnowledgeNode(updated_at=test_time)
        
        assert node.updated_at == test_time
        
        node.update()
        assert node.updated_at > test_time


class TestNote:
    """Tests for the Note model."""
    
    def test_init_minimal(self):
        """Test initialization with minimal required fields."""
        note = Note(title="Test Note", content="Test content")
        
        assert note.title == "Test Note"
        assert note.content == "Test content"
        assert note.source is None
        assert note.page_reference is None
        assert note.attachments == []
        assert note.citations == []
    
    def test_init_full(self):
        """Test initialization with all fields."""
        source_id = uuid4()
        citation_id = uuid4()
        
        note = Note(
            title="Test Note",
            content="Test content",
            source=source_id,
            page_reference=42,
            attachments=["/path/to/attachment.pdf"],
            citations=[citation_id]
        )
        
        assert note.title == "Test Note"
        assert note.content == "Test content"
        assert note.source == source_id
        assert note.page_reference == 42
        assert len(note.attachments) == 1
        assert str(note.attachments[0]) == "/path/to/attachment.pdf"
        assert len(note.citations) == 1
        assert note.citations[0] == citation_id


class TestCitation:
    """Tests for the Citation model."""
    
    def test_init_minimal(self):
        """Test initialization with minimal required fields."""
        citation = Citation(
            title="Test Paper",
            authors=["Smith, John", "Doe, Jane"]
        )
        
        assert citation.title == "Test Paper"
        assert citation.authors == ["Smith, John", "Doe, Jane"]
        assert citation.year is None
        assert citation.doi is None
        assert citation.url is None
        assert citation.journal is None
        assert citation.citation_type == CitationType.ARTICLE
        assert citation.notes == []
    
    def test_init_full(self):
        """Test initialization with all fields."""
        note_id = uuid4()
        
        citation = Citation(
            title="Test Paper",
            authors=["Smith, John", "Doe, Jane"],
            year=2023,
            doi="10.1234/example",
            url="https://example.com/paper",
            journal="Journal of Testing",
            volume="10",
            issue="2",
            pages="123-145",
            publisher="Test Publisher",
            citation_type=CitationType.CONFERENCE,
            abstract="This is an abstract",
            keywords=["keyword1", "keyword2"],
            file_path="/path/to/paper.pdf",
            bibtex="@article{test2023, title={Test Paper}}",
            notes=[note_id]
        )
        
        assert citation.title == "Test Paper"
        assert citation.authors == ["Smith, John", "Doe, Jane"]
        assert citation.year == 2023
        assert citation.doi == "10.1234/example"
        assert citation.url == "https://example.com/paper"
        assert citation.journal == "Journal of Testing"
        assert citation.volume == "10"
        assert citation.issue == "2"
        assert citation.pages == "123-145"
        assert citation.publisher == "Test Publisher"
        assert citation.citation_type == CitationType.CONFERENCE
        assert citation.abstract == "This is an abstract"
        assert citation.keywords == ["keyword1", "keyword2"]
        assert str(citation.file_path) == "/path/to/paper.pdf"
        assert citation.bibtex == "@article{test2023, title={Test Paper}}"
        assert len(citation.notes) == 1
        assert citation.notes[0] == note_id


class TestResearchQuestion:
    """Tests for the ResearchQuestion model."""
    
    def test_init_minimal(self):
        """Test initialization with minimal required fields."""
        question = ResearchQuestion(
            question="What is the effect of X on Y?"
        )
        
        assert question.question == "What is the effect of X on Y?"
        assert question.description is None
        assert question.evidence == []
        assert question.status == "open"
        assert question.priority == 0
    
    def test_init_with_evidence(self):
        """Test initialization with evidence."""
        note_id = uuid4()
        
        evidence = Evidence(
            note_id=note_id,
            evidence_type=EvidenceType.SUPPORTING,
            strength=EvidenceStrength.STRONG,
            description="Strong evidence supporting the hypothesis"
        )
        
        question = ResearchQuestion(
            question="What is the effect of X on Y?",
            description="Detailed description",
            evidence=[evidence],
            status="resolved",
            priority=5
        )
        
        assert question.question == "What is the effect of X on Y?"
        assert question.description == "Detailed description"
        assert len(question.evidence) == 1
        assert question.evidence[0].note_id == note_id
        assert question.evidence[0].evidence_type == EvidenceType.SUPPORTING
        assert question.evidence[0].strength == EvidenceStrength.STRONG
        assert question.status == "resolved"
        assert question.priority == 5


class TestExperiment:
    """Tests for the Experiment model."""
    
    def test_init_minimal(self):
        """Test initialization with minimal required fields."""
        experiment = Experiment(
            title="Test Experiment",
            hypothesis="X increases Y",
            methodology="Detailed methodology"
        )
        
        assert experiment.title == "Test Experiment"
        assert experiment.hypothesis == "X increases Y"
        assert experiment.methodology == "Detailed methodology"
        assert experiment.status == ExperimentStatus.PLANNED
        assert experiment.start_date is None
        assert experiment.end_date is None
        assert experiment.results is None
        assert experiment.conclusion is None
        assert experiment.research_question_id is None
        assert experiment.notes == []
    
    def test_init_full(self):
        """Test initialization with all fields."""
        question_id = uuid4()
        note_id = uuid4()
        start_date = datetime.datetime(2023, 1, 1)
        end_date = datetime.datetime(2023, 2, 1)
        
        experiment = Experiment(
            title="Test Experiment",
            hypothesis="X increases Y",
            methodology="Detailed methodology",
            status=ExperimentStatus.COMPLETED,
            start_date=start_date,
            end_date=end_date,
            variables={"x": 10, "y": 20},
            results="Experiment results",
            conclusion="Experiment conclusion",
            research_question_id=question_id,
            notes=[note_id]
        )
        
        assert experiment.title == "Test Experiment"
        assert experiment.hypothesis == "X increases Y"
        assert experiment.methodology == "Detailed methodology"
        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.start_date == start_date
        assert experiment.end_date == end_date
        assert experiment.variables == {"x": 10, "y": 20}
        assert experiment.results == "Experiment results"
        assert experiment.conclusion == "Experiment conclusion"
        assert experiment.research_question_id == question_id
        assert len(experiment.notes) == 1
        assert experiment.notes[0] == note_id
    
    def test_end_date_validation(self):
        """Test validation that end_date must be after start_date."""
        start_date = datetime.datetime(2023, 2, 1)
        end_date = datetime.datetime(2023, 1, 1)  # Before start_date
        
        with pytest.raises(ValidationError):
            Experiment(
                title="Test Experiment",
                hypothesis="X increases Y",
                methodology="Detailed methodology",
                start_date=start_date,
                end_date=end_date
            )


class TestGrantProposal:
    """Tests for the GrantProposal model."""
    
    def test_init_minimal(self):
        """Test initialization with minimal required fields."""
        grant = GrantProposal(
            title="Test Grant",
            funding_agency="NSF",
            description="Grant description"
        )
        
        assert grant.title == "Test Grant"
        assert grant.funding_agency == "NSF"
        assert grant.description == "Grant description"
        assert grant.deadline is None
        assert grant.status == GrantStatus.DRAFTING
        assert grant.amount is None
        assert grant.notes == []
        assert grant.experiments == []
        assert grant.research_questions == []
    
    def test_init_full(self):
        """Test initialization with all fields."""
        note_id = uuid4()
        experiment_id = uuid4()
        question_id = uuid4()
        deadline = datetime.datetime(2023, 12, 31)
        
        grant = GrantProposal(
            title="Test Grant",
            funding_agency="NSF",
            description="Grant description",
            deadline=deadline,
            status=GrantStatus.SUBMITTED,
            amount=500000.0,
            notes=[note_id],
            experiments=[experiment_id],
            research_questions=[question_id]
        )
        
        assert grant.title == "Test Grant"
        assert grant.funding_agency == "NSF"
        assert grant.description == "Grant description"
        assert grant.deadline == deadline
        assert grant.status == GrantStatus.SUBMITTED
        assert grant.amount == 500000.0
        assert len(grant.notes) == 1
        assert grant.notes[0] == note_id
        assert len(grant.experiments) == 1
        assert grant.experiments[0] == experiment_id
        assert len(grant.research_questions) == 1
        assert grant.research_questions[0] == question_id


class TestCollaborator:
    """Tests for the Collaborator model."""
    
    def test_init_minimal(self):
        """Test initialization with minimal required fields."""
        collaborator = Collaborator(name="John Smith")
        
        assert collaborator.name == "John Smith"
        assert collaborator.email is None
        assert collaborator.affiliation is None
        assert collaborator.role == CollaboratorRole.COLLABORATOR
        assert collaborator.notes == []
    
    def test_init_full(self):
        """Test initialization with all fields."""
        note_id = uuid4()
        
        collaborator = Collaborator(
            name="John Smith",
            email="john@example.com",
            affiliation="University of Testing",
            role=CollaboratorRole.PRINCIPAL_INVESTIGATOR,
            notes=[note_id]
        )
        
        assert collaborator.name == "John Smith"
        assert collaborator.email == "john@example.com"
        assert collaborator.affiliation == "University of Testing"
        assert collaborator.role == CollaboratorRole.PRINCIPAL_INVESTIGATOR
        assert len(collaborator.notes) == 1
        assert collaborator.notes[0] == note_id