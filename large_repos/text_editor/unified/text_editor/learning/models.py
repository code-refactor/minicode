"""
Data models for the learning mode system.
"""
from enum import Enum, auto
from typing import List, Dict, Set, Optional, Any
from pydantic import BaseModel, Field


class ConceptDifficulty(Enum):
    """Difficulty levels for computer science concepts."""
    BASIC = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


class ConceptCategory(Enum):
    """Categories of computer science concepts."""
    DATA_STRUCTURES = "data_structures"
    ALGORITHMS = "algorithms"
    DESIGN_PATTERNS = "design_patterns"
    EDITOR_INTERNALS = "editor_internals"
    PERFORMANCE = "performance"
    PROGRAMMING_LANGUAGES = "programming_languages"
    SOFTWARE_ARCHITECTURE = "software_architecture"
    USER_INTERFACE = "user_interface"


class Concept(BaseModel):
    """
    Represents a computer science concept that can be learned.
    """
    id: str
    name: str
    description: str
    category: ConceptCategory
    difficulty: ConceptDifficulty
    prerequisites: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)
    resources: List[Dict[str, str]] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    module_path: Optional[str] = None  # Path to the module implementing this concept


class Annotation(BaseModel):
    """
    Represents an annotation on source code that explains a concept.
    """
    concept_id: str
    start_line: int
    end_line: int
    text: str
    code_snippet: str


class ExtensionProject(BaseModel):
    """
    Represents a guided extension project for learning.
    """
    id: str
    name: str
    description: str
    difficulty: ConceptDifficulty
    concepts: List[str]  # List of concept IDs
    requirements: List[str]
    starter_code: Optional[str] = None
    solution_code: Optional[str] = None
    tests: List[str] = Field(default_factory=list)
    hints: List[str] = Field(default_factory=list)
    estimated_time_minutes: int = 60


class LearningProgress(BaseModel):
    """
    Tracks a user's progress in learning concepts.
    """
    completed_concepts: Set[str] = Field(default_factory=set)
    concept_mastery: Dict[str, float] = Field(default_factory=dict)  # 0.0 to 1.0
    completed_projects: Set[str] = Field(default_factory=set)
    viewed_annotations: Dict[str, int] = Field(default_factory=dict)  # concept_id -> count
    current_project: Optional[str] = None
    
    def mark_concept_viewed(self, concept_id: str) -> None:
        """
        Mark a concept as having been viewed.
        
        Args:
            concept_id: ID of the concept that was viewed
        """
        if concept_id not in self.viewed_annotations:
            self.viewed_annotations[concept_id] = 0
        
        self.viewed_annotations[concept_id] += 1
        
        # Update mastery based on view count
        views = self.viewed_annotations[concept_id]
        if views >= 5:
            self.concept_mastery[concept_id] = 1.0
        else:
            self.concept_mastery[concept_id] = views / 5.0
    
    def mark_concept_completed(self, concept_id: str) -> None:
        """
        Mark a concept as completed/mastered.
        
        Args:
            concept_id: ID of the concept that was completed
        """
        self.completed_concepts.add(concept_id)
        self.concept_mastery[concept_id] = 1.0
    
    def mark_project_completed(self, project_id: str) -> None:
        """
        Mark an extension project as completed.
        
        Args:
            project_id: ID of the project that was completed
        """
        self.completed_projects.add(project_id)
        self.current_project = None
    
    def set_current_project(self, project_id: str) -> None:
        """
        Set the current extension project.
        
        Args:
            project_id: ID of the project to set as current
        """
        self.current_project = project_id
    
    def get_mastery_level(self, concept_id: str) -> float:
        """
        Get the mastery level for a concept.
        
        Args:
            concept_id: ID of the concept to check
            
        Returns:
            Mastery level from 0.0 to 1.0
        """
        return self.concept_mastery.get(concept_id, 0.0)
    
    def is_concept_completed(self, concept_id: str) -> bool:
        """
        Check if a concept is completed.
        
        Args:
            concept_id: ID of the concept to check
            
        Returns:
            True if the concept is completed, False otherwise
        """
        return concept_id in self.completed_concepts
    
    def is_project_completed(self, project_id: str) -> bool:
        """
        Check if a project is completed.
        
        Args:
            project_id: ID of the project to check
            
        Returns:
            True if the project is completed, False otherwise
        """
        return project_id in self.completed_projects