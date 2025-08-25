"""
Tests for the learning mode system.
"""
import pytest
import time

from text_editor.learning.models import (
    Concept,
    ConceptCategory,
    ConceptDifficulty,
    Annotation,
    ExtensionProject,
    LearningProgress
)
from text_editor.learning.manager import LearningManager


class TestLearningModels:
    def test_concept_model(self):
        """Test the Concept model functionality."""
        concept = Concept(
            id="test_concept",
            name="Test Concept",
            description="A test concept",
            category=ConceptCategory.DATA_STRUCTURES,
            difficulty=ConceptDifficulty.BASIC
        )
        
        assert concept.id == "test_concept"
        assert concept.name == "Test Concept"
        assert concept.category == ConceptCategory.DATA_STRUCTURES
        assert concept.difficulty == ConceptDifficulty.BASIC
    
    def test_annotation_model(self):
        """Test the Annotation model functionality."""
        annotation = Annotation(
            concept_id="test_concept",
            start_line=10,
            end_line=20,
            text="This is an annotation",
            code_snippet="def test():\n    pass"
        )
        
        assert annotation.concept_id == "test_concept"
        assert annotation.start_line == 10
        assert annotation.end_line == 20
        assert annotation.text == "This is an annotation"
        assert annotation.code_snippet == "def test():\n    pass"
    
    def test_extension_project_model(self):
        """Test the ExtensionProject model functionality."""
        project = ExtensionProject(
            id="test_project",
            name="Test Project",
            description="A test project",
            difficulty=ConceptDifficulty.BASIC,
            concepts=["concept1", "concept2"],
            requirements=["req1", "req2"],
            starter_code="def start():\n    pass",
            solution_code="def solution():\n    return True"
        )
        
        assert project.id == "test_project"
        assert project.name == "Test Project"
        assert project.difficulty == ConceptDifficulty.BASIC
        assert project.concepts == ["concept1", "concept2"]
        assert project.requirements == ["req1", "req2"]
        assert project.starter_code == "def start():\n    pass"
        assert project.solution_code == "def solution():\n    return True"
    
    def test_learning_progress(self):
        """Test the LearningProgress functionality."""
        progress = LearningProgress()
        
        # Test initial state
        assert not progress.completed_concepts
        assert not progress.concept_mastery
        assert not progress.completed_projects
        assert not progress.viewed_annotations
        assert progress.current_project is None
        
        # Test marking a concept as viewed
        progress.mark_concept_viewed("concept1")
        assert "concept1" in progress.viewed_annotations
        assert progress.viewed_annotations["concept1"] == 1
        assert progress.get_mastery_level("concept1") > 0
        
        # View it multiple times to increase mastery
        for _ in range(4):
            progress.mark_concept_viewed("concept1")
        assert progress.get_mastery_level("concept1") == 1.0
        
        # Test marking a concept as completed
        progress.mark_concept_completed("concept2")
        assert "concept2" in progress.completed_concepts
        assert progress.get_mastery_level("concept2") == 1.0
        assert progress.is_concept_completed("concept2")
        
        # Test project management
        progress.set_current_project("project1")
        assert progress.current_project == "project1"
        
        progress.mark_project_completed("project1")
        assert "project1" in progress.completed_projects
        assert progress.current_project is None
        assert progress.is_project_completed("project1")


class TestLearningManager:
    def test_initialization(self):
        """Test that the learning manager is initialized correctly."""
        manager = LearningManager()
        
        # Check that default concepts and projects are loaded
        assert manager.concepts
        assert manager.extension_projects
        assert manager.learning_progress
    
    def test_get_concept(self):
        """Test getting a concept by ID."""
        manager = LearningManager()
        
        # Test with an existing concept
        concept = manager.concepts[list(manager.concepts.keys())[0]]
        retrieved = manager.get_concept(concept.id)
        assert retrieved is not None
        assert retrieved.id == concept.id
        
        # Test with a non-existent concept
        assert manager.get_concept("non_existent") is None
    
    def test_get_all_concepts(self):
        """Test getting all concepts."""
        manager = LearningManager()
        concepts = manager.get_all_concepts()
        
        assert concepts
        assert len(concepts) == len(manager.concepts)
    
    def test_get_concepts_by_category(self):
        """Test getting concepts filtered by category."""
        manager = LearningManager()
        
        # Choose a category that exists in the default concepts
        category = ConceptCategory.DATA_STRUCTURES
        concepts = manager.get_concepts_by_category(category)
        
        assert all(c.category == category for c in concepts)
    
    def test_get_concepts_by_difficulty(self):
        """Test getting concepts filtered by difficulty."""
        manager = LearningManager()
        
        # Choose a difficulty that exists in the default concepts
        difficulty = ConceptDifficulty.BASIC
        concepts = manager.get_concepts_by_difficulty(difficulty)
        
        assert all(c.difficulty == difficulty for c in concepts)
    
    def test_get_annotated_source(self):
        """Test getting annotated source code for a concept."""
        manager = LearningManager()
        
        # Find a concept with a module path
        concept = None
        for c in manager.concepts.values():
            if c.module_path:
                concept = c
                break
                
        if concept:
            annotations = manager.get_annotated_source(concept.id)
            
            # Even if no annotations are found, the concept should be marked as viewed
            assert concept.id in manager.learning_progress.viewed_annotations
    
    def test_get_extension_project(self):
        """Test getting an extension project by ID."""
        manager = LearningManager()
        
        # Test with an existing project
        project = manager.extension_projects[list(manager.extension_projects.keys())[0]]
        retrieved = manager.get_extension_project(project.id)
        assert retrieved is not None
        assert retrieved.id == project.id
        
        # Test with a non-existent project
        assert manager.get_extension_project("non_existent") is None
    
    def test_get_all_extension_projects(self):
        """Test getting all extension projects."""
        manager = LearningManager()
        projects = manager.get_all_extension_projects()
        
        assert projects
        assert len(projects) == len(manager.extension_projects)
    
    def test_get_projects_by_difficulty(self):
        """Test getting projects filtered by difficulty."""
        manager = LearningManager()
        
        # Choose a difficulty that exists in the default projects
        difficulty = ConceptDifficulty.BASIC
        projects = manager.get_projects_by_difficulty(difficulty)
        
        assert all(p.difficulty == difficulty for p in projects)
    
    def test_get_projects_by_concept(self):
        """Test getting projects related to a specific concept."""
        manager = LearningManager()
        
        # Find a concept that's used in a project
        concept_id = None
        for project in manager.extension_projects.values():
            if project.concepts:
                concept_id = project.concepts[0]
                break
                
        if concept_id:
            projects = manager.get_projects_by_concept(concept_id)
            assert all(concept_id in p.concepts for p in projects)
    
    def test_start_complete_project(self):
        """Test starting and completing an extension project."""
        manager = LearningManager()
        
        # Get a project ID
        project_id = list(manager.extension_projects.keys())[0]
        
        # Start the project
        result = manager.start_extension_project(project_id)
        assert result
        assert manager.learning_progress.current_project == project_id
        
        # Complete the project
        result = manager.complete_extension_project(project_id)
        assert result
        assert project_id in manager.learning_progress.completed_projects
        assert manager.learning_progress.current_project is None
        
        # Check that related concepts are marked as completed
        project = manager.extension_projects[project_id]
        for concept_id in project.concepts:
            assert concept_id in manager.learning_progress.completed_concepts
    
    def test_get_learning_progress(self):
        """Test getting a summary of learning progress."""
        manager = LearningManager()
        
        # Mark a concept as completed
        concept_id = list(manager.concepts.keys())[0]
        manager.learning_progress.mark_concept_completed(concept_id)
        
        # Mark a project as completed
        project_id = list(manager.extension_projects.keys())[0]
        manager.learning_progress.mark_project_completed(project_id)
        
        progress = manager.get_learning_progress()
        
        assert progress["completed_concepts"] == 1
        assert progress["total_concepts"] == len(manager.concepts)
        assert progress["completed_projects"] == 1
        assert progress["total_projects"] == len(manager.extension_projects)
        assert progress["overall_mastery"] > 0