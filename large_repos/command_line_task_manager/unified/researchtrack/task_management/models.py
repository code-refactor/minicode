from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass, field

from common.core import BaseEntity, StatusMixin, TaggedMixin


class TaskStatus(str, Enum):
    """Status of a research task."""
    
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskPriority(str, Enum):
    """Priority level of a research task."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ResearchQuestion(BaseEntity):
    """Model representing a research question."""
    
    text: str = ""
    description: Optional[str] = None
    parent_question_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.text:
            raise ValueError("Research question text cannot be empty")


@dataclass
class ResearchTask(BaseEntity):
    """Model representing a research task with comprehensive metadata."""

    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PLANNED
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Associations with research questions and subtasks
    research_question_ids: Set[str] = field(default_factory=set)
    parent_task_id: Optional[str] = None
    subtask_ids: Set[str] = field(default_factory=set)

    # Associations with other research artifacts
    reference_ids: Set[str] = field(default_factory=set)  # Bibliographic references
    dataset_ids: Set[str] = field(default_factory=set)    # Dataset versions
    environment_ids: Set[str] = field(default_factory=set)  # Computational environments
    experiment_ids: Set[str] = field(default_factory=set)  # Experiments

    # Custom metadata fields for research-specific tracking
    notes: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    custom_metadata: Dict[str, Union[str, int, float, bool, list, dict]] = field(
        default_factory=dict
    )
    
    # Additional properties for integration tests
    # These aren't persisted, but used for convenience in tests
    research_questions: List[Any] = field(default_factory=list, init=False)
    references: List[Any] = field(default_factory=list, init=False)
    datasets: List[Any] = field(default_factory=list, init=False)
    environments: List[Any] = field(default_factory=list, init=False)
    experiments: List[Any] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.title:
            raise ValueError("Task title cannot be empty")
        if not self.description:
            raise ValueError("Task description cannot be empty")
    
    def update_fields(self, **kwargs) -> 'ResearchTask':
        """Update task fields and return updated instance."""
        # Update completion timestamp if status changed to completed
        if 'status' in kwargs and kwargs['status'] == TaskStatus.COMPLETED and not self.completed_at:
            kwargs['completed_at'] = datetime.now()
        
        return super().update(**kwargs)
    
    def update(self, **kwargs) -> 'ResearchTask':
        """Backward-compatible update method."""
        return self.update_fields(**kwargs)
    
    def add_note(self, note: str) -> None:
        """Add a note to the task."""
        self.notes.append(note)
        self.updated_at = datetime.now()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the task."""
        self.tags.add(tag)
        self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the task."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
    
    def add_research_question(self, question_id: str) -> None:
        """Associate a research question with this task."""
        self.research_question_ids.add(question_id)
        self.updated_at = datetime.now()
    
    def remove_research_question(self, question_id: str) -> None:
        """Remove association with a research question."""
        if question_id in self.research_question_ids:
            self.research_question_ids.remove(question_id)
            self.updated_at = datetime.now()

    def add_subtask(self, subtask_id: str) -> None:
        """Add a subtask to this task."""
        self.subtask_ids.add(subtask_id)
        self.updated_at = datetime.now()

    def remove_subtask(self, subtask_id: str) -> None:
        """Remove a subtask from this task."""
        if subtask_id in self.subtask_ids:
            self.subtask_ids.remove(subtask_id)
            self.updated_at = datetime.now()

    def update_custom_metadata(self, key: str, value: Union[str, int, float, bool, list, dict]) -> None:
        """Update a custom metadata field."""
        self.custom_metadata[key] = value
        self.updated_at = datetime.now()

    # Bibliographic reference association methods
    def add_reference(self, reference_id: str) -> None:
        """Associate a bibliographic reference with this task."""
        self.reference_ids.add(reference_id)
        self.updated_at = datetime.now()

    def remove_reference(self, reference_id: str) -> None:
        """Remove association with a bibliographic reference."""
        if reference_id in self.reference_ids:
            self.reference_ids.remove(reference_id)
            self.updated_at = datetime.now()

    # Dataset association methods
    def add_dataset(self, dataset_id: str) -> None:
        """Associate a dataset with this task."""
        self.dataset_ids.add(dataset_id)
        self.updated_at = datetime.now()

    def remove_dataset(self, dataset_id: str) -> None:
        """Remove association with a dataset."""
        if dataset_id in self.dataset_ids:
            self.dataset_ids.remove(dataset_id)
            self.updated_at = datetime.now()

    # Environment association methods
    def add_environment(self, environment_id: str) -> None:
        """Associate a computational environment with this task."""
        self.environment_ids.add(environment_id)
        self.updated_at = datetime.now()

    def remove_environment(self, environment_id: str) -> None:
        """Remove association with a computational environment."""
        if environment_id in self.environment_ids:
            self.environment_ids.remove(environment_id)
            self.updated_at = datetime.now()

    # Experiment association methods
    def add_experiment(self, experiment_id: str) -> None:
        """Associate an experiment with this task."""
        self.experiment_ids.add(experiment_id)
        self.updated_at = datetime.now()

    def remove_experiment(self, experiment_id: str) -> None:
        """Remove association with an experiment."""
        if experiment_id in self.experiment_ids:
            self.experiment_ids.remove(experiment_id)
            self.updated_at = datetime.now()