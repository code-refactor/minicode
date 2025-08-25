"""Core data models for the ResearchBrain knowledge management system."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from common.core import TaggableEntity


class KnowledgeNode(TaggableEntity):
    """Base class for all knowledge nodes in the system."""
    pass


class Note(KnowledgeNode):
    """Represents a research note with content and metadata."""

    title: str
    content: str
    source: Optional[UUID] = None  # Reference to a source document
    page_reference: Optional[int] = None  # Page number in the source document
    attachments: List[Path] = Field(default_factory=list)
    citations: List[UUID] = Field(default_factory=list)  # References to Citation objects
    section_references: Dict[str, str] = Field(default_factory=dict)  # Section references in source documents


class CitationType(str, Enum):
    """Types of academic citations."""

    BOOK = "book"
    ARTICLE = "article"
    CONFERENCE = "conference"
    THESIS = "thesis"
    REPORT = "report"
    WEBPAGE = "webpage"
    PREPRINT = "preprint"
    OTHER = "other"


class Citation(KnowledgeNode):
    """Represents a citation to an academic source."""

    title: str
    authors: List[str]
    year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    citation_type: CitationType = CitationType.ARTICLE
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    file_path: Optional[Path] = None
    bibtex: Optional[str] = None
    ris: Optional[str] = None  # RIS format citation data
    notes: List[UUID] = Field(default_factory=list)  # References to linked Note objects
    pdf_metadata: Dict[str, Any] = Field(default_factory=dict)  # Extracted metadata from PDF
    sections: Dict[str, str] = Field(default_factory=dict)  # Extracted sections from the paper


class CitationFormat(str, Enum):
    """Academic citation formats."""

    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    HARVARD = "harvard"
    IEEE = "ieee"
    VANCOUVER = "vancouver"
    BIBTEX = "bibtex"
    RIS = "ris"


class EvidenceType(str, Enum):
    """Types of evidence for research questions."""

    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    INCONCLUSIVE = "inconclusive"
    RELATED = "related"


class EvidenceStrength(str, Enum):
    """Strength levels for evidence."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    ANECDOTAL = "anecdotal"
    THEORETICAL = "theoretical"


class Evidence(BaseModel):
    """Evidence linked to a research question."""

    id: UUID = Field(default_factory=uuid4)
    note_id: UUID  # Reference to the note containing the evidence
    evidence_type: EvidenceType
    strength: EvidenceStrength
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    citation_ids: List[UUID] = Field(default_factory=list)  # References to supporting citations
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata for the evidence


class ResearchQuestion(KnowledgeNode):
    """Represents a research question or hypothesis."""

    question: str
    description: Optional[str] = None
    evidence: List[Evidence] = Field(default_factory=list)
    status: str = "open"  # open, resolved, abandoned
    priority: int = 0  # 0-10 scale of importance
    related_questions: List[UUID] = Field(default_factory=list)  # References to related questions
    knowledge_gaps: List[str] = Field(default_factory=list)  # Identified knowledge gaps


class ExperimentStatus(str, Enum):
    """Status options for experiments."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class Experiment(KnowledgeNode):
    """Represents a scientific experiment with structured metadata."""

    title: str
    hypothesis: str
    status: ExperimentStatus = ExperimentStatus.PLANNED
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    methodology: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[str] = None
    conclusion: Optional[str] = None
    research_question_id: Optional[UUID] = None  # Link to a research question
    notes: List[UUID] = Field(default_factory=list)  # References to linked Note objects
    collaborators: List[UUID] = Field(default_factory=list)  # References to collaborators
    template_name: Optional[str] = None  # Name of the template used to create the experiment
    reproducibility_info: Dict[str, Any] = Field(default_factory=dict)  # Information for reproducibility

    @field_validator("end_date")
    def end_date_after_start_date(cls, v, info):
        """Validate that end_date is after start_date if both are provided."""
        values = info.data
        if v and "start_date" in values and values["start_date"]:
            if v < values["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v


class GrantStatus(str, Enum):
    """Status options for grant proposals."""

    DRAFTING = "drafting"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    AWARDED = "awarded"
    REJECTED = "rejected"
    COMPLETED = "completed"


class GrantProposal(KnowledgeNode):
    """Represents a grant proposal workspace."""

    title: str
    funding_agency: str
    deadline: Optional[datetime] = None
    status: GrantStatus = GrantStatus.DRAFTING
    amount: Optional[float] = None
    description: str
    notes: List[UUID] = Field(default_factory=list)  # References to related notes
    experiments: List[UUID] = Field(default_factory=list)  # References to related experiments
    research_questions: List[UUID] = Field(default_factory=list)  # References to research questions
    collaborators: List[UUID] = Field(default_factory=list)  # References to collaborators
    budget_items: Dict[str, Any] = Field(default_factory=dict)  # Budget line items and justifications
    timeline: Dict[str, Any] = Field(default_factory=dict)  # Project timeline information
    export_history: List[Dict[str, Any]] = Field(default_factory=list)  # Record of exports


class CollaboratorRole(str, Enum):
    """Roles for collaborators."""

    PRINCIPAL_INVESTIGATOR = "principal_investigator"
    CO_INVESTIGATOR = "co_investigator"
    COLLABORATOR = "collaborator"
    ADVISOR = "advisor"
    CONSULTANT = "consultant"
    STUDENT = "student"


class Collaborator(KnowledgeNode):
    """Represents a research collaborator."""

    name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None
    role: CollaboratorRole = CollaboratorRole.COLLABORATOR
    notes: List[UUID] = Field(default_factory=list)  # References to notes they've contributed to
    permissions: Dict[str, bool] = Field(default_factory=dict)  # Permissions for different operations
    experiments: List[UUID] = Field(default_factory=list)  # Experiments they're involved in
    grants: List[UUID] = Field(default_factory=list)  # Grants they're involved in


class Annotation(KnowledgeNode):
    """Represents an annotation or comment on a knowledge node."""

    node_id: UUID  # Reference to the annotated knowledge node
    collaborator_id: UUID  # Who made the annotation
    content: str
    position: Optional[str] = None  # For annotations with specific position in document
    status: str = "open"  # Status of the annotation (open, addressed, rejected)
    replies: List[UUID] = Field(default_factory=list)  # References to reply annotations
    parent_id: Optional[UUID] = None  # Reference to parent annotation if this is a reply
    resolved_by: Optional[UUID] = None  # Reference to collaborator who resolved this