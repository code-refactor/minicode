from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from researchtrack.task_management.models import (
    ResearchQuestion,
    ResearchTask,
    TaskPriority,
    TaskStatus,
)


class TestResearchQuestion:
    def test_create_research_question(self):
        # Test basic creation
        question = ResearchQuestion(
            text="What factors influence climate model accuracy?",
            description="Investigating the key factors that affect predictive accuracy of climate models",
        )
        
        assert isinstance(question.id, UUID)
        assert question.text == "What factors influence climate model accuracy?"
        assert question.description == "Investigating the key factors that affect predictive accuracy of climate models"
        assert question.parent_question_id is None
        assert isinstance(question.created_at, datetime)
        assert isinstance(question.updated_at, datetime)
    
    def test_create_with_parent(self):
        # Test creation with parent reference
        parent_id = uuid4()
        question = ResearchQuestion(
            text="How do sea surface temperatures affect model accuracy?",
            description="Sub-question focusing specifically on SST impacts",
            parent_question_id=parent_id,
        )
        
        assert question.parent_question_id == parent_id
    
    def test_update_question(self):
        # Test updating fields
        question = ResearchQuestion(
            text="Original question",
            description="Original description",
        )
        
        original_updated_at = question.updated_at
        
        # Small delay to ensure updated_at will be different
        question.update(
            text="Updated question",
            description="Updated description",
        )
        
        assert question.text == "Updated question"
        assert question.description == "Updated description"
        assert question.updated_at > original_updated_at


class TestResearchTask:
    def test_create_research_task(self):
        # Test basic creation
        task = ResearchTask(
            title="Analyze climate data from 1950-2020",
            description="Perform time series analysis on global temperature data",
            status=TaskStatus.PLANNED,
            priority=TaskPriority.HIGH,
            estimated_hours=8.5,
        )
        
        assert isinstance(task.id, UUID)
        assert task.title == "Analyze climate data from 1950-2020"
        assert task.description == "Perform time series analysis on global temperature data"
        assert task.status == TaskStatus.PLANNED
        assert task.priority == TaskPriority.HIGH
        assert task.estimated_hours == 8.5
        assert task.actual_hours is None
        assert task.due_date is None
        assert task.completed_at is None
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)
        assert len(task.research_question_ids) == 0
        assert task.parent_task_id is None
        assert len(task.subtask_ids) == 0
        assert len(task.notes) == 0
        assert len(task.tags) == 0
        assert len(task.custom_metadata) == 0
    
    def test_task_with_due_date(self):
        # Test creation with due date
        due_date = datetime.now() + timedelta(days=7)
        task = ResearchTask(
            title="Submit preliminary findings",
            description="Prepare and submit initial findings report",
            due_date=due_date,
        )
        
        assert task.due_date == due_date
    
    def test_create_subtask(self):
        # Test creation with parent task
        parent_id = uuid4()
        task = ResearchTask(
            title="Data cleaning subtask",
            description="Clean and normalize the temperature dataset",
            parent_task_id=parent_id,
        )
        
        assert task.parent_task_id == parent_id
    
    def test_update_task(self):
        # Test updating fields
        task = ResearchTask(
            title="Original title",
            description="Original description",
            status=TaskStatus.PLANNED,
            priority=TaskPriority.MEDIUM,
        )
        
        original_updated_at = task.updated_at
        
        # Small delay to ensure updated_at will be different
        task.update(
            title="Updated title",
            description="Updated description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            estimated_hours=5.0,
            actual_hours=2.5,
        )
        
        assert task.title == "Updated title"
        assert task.description == "Updated description"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == TaskPriority.HIGH
        assert task.estimated_hours == 5.0
        assert task.actual_hours == 2.5
        assert task.updated_at > original_updated_at
        assert task.completed_at is None  # Not completed yet
    
    def test_complete_task(self):
        # Test completing a task
        task = ResearchTask(
            title="Task to complete",
            description="This task will be marked as completed",
            status=TaskStatus.IN_PROGRESS,
        )
        
        assert task.completed_at is None
        
        task.update(status=TaskStatus.COMPLETED)
        
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
    
    def test_add_note(self):
        # Test adding notes
        task = ResearchTask(
            title="Task with notes",
            description="Testing note functionality",
        )
        
        original_updated_at = task.updated_at
        
        task.add_note("First note about this task")
        task.add_note("Second note with additional information")
        
        assert len(task.notes) == 2
        assert task.notes[0] == "First note about this task"
        assert task.notes[1] == "Second note with additional information"
        assert task.updated_at > original_updated_at
    
    def test_manage_tags(self):
        # Test adding and removing tags
        task = ResearchTask(
            title="Task with tags",
            description="Testing tag functionality",
        )
        
        task.add_tag("climate")
        task.add_tag("data-analysis")
        task.add_tag("research")
        
        assert len(task.tags) == 3
        assert "climate" in task.tags
        assert "data-analysis" in task.tags
        assert "research" in task.tags
        
        task.remove_tag("data-analysis")
        
        assert len(task.tags) == 2
        assert "climate" in task.tags
        assert "data-analysis" not in task.tags
        assert "research" in task.tags
        
        # Adding the same tag twice should not duplicate
        task.add_tag("climate")
        assert len(task.tags) == 2
    
    def test_research_question_association(self):
        # Test associating with research questions
        task = ResearchTask(
            title="Task with research questions",
            description="Testing research question associations",
        )
        
        question_id1 = uuid4()
        question_id2 = uuid4()
        
        task.add_research_question(question_id1)
        task.add_research_question(question_id2)
        
        assert len(task.research_question_ids) == 2
        assert question_id1 in task.research_question_ids
        assert question_id2 in task.research_question_ids
        
        task.remove_research_question(question_id1)
        
        assert len(task.research_question_ids) == 1
        assert question_id1 not in task.research_question_ids
        assert question_id2 in task.research_question_ids
    
    def test_subtask_management(self):
        # Test subtask management
        task = ResearchTask(
            title="Parent task",
            description="Task with subtasks",
        )
        
        subtask_id1 = uuid4()
        subtask_id2 = uuid4()
        
        task.add_subtask(subtask_id1)
        task.add_subtask(subtask_id2)
        
        assert len(task.subtask_ids) == 2
        assert subtask_id1 in task.subtask_ids
        assert subtask_id2 in task.subtask_ids
        
        task.remove_subtask(subtask_id1)
        
        assert len(task.subtask_ids) == 1
        assert subtask_id1 not in task.subtask_ids
        assert subtask_id2 in task.subtask_ids
    
    def test_custom_metadata(self):
        # Test custom metadata functionality
        task = ResearchTask(
            title="Task with metadata",
            description="Testing custom metadata functionality",
        )
        
        task.update_custom_metadata("dataset_source", "NOAA Climate Database")
        task.update_custom_metadata("sample_size", 1000)
        task.update_custom_metadata("confidence_level", 0.95)
        task.update_custom_metadata("data_complete", True)
        task.update_custom_metadata("used_variables", ["temp", "pressure", "humidity"])
        task.update_custom_metadata(
            "model_params", {"max_depth": 5, "n_estimators": 100}
        )
        
        assert len(task.custom_metadata) == 6
        assert task.custom_metadata["dataset_source"] == "NOAA Climate Database"
        assert task.custom_metadata["sample_size"] == 1000
        assert task.custom_metadata["confidence_level"] == 0.95
        assert task.custom_metadata["data_complete"] is True
        assert task.custom_metadata["used_variables"] == ["temp", "pressure", "humidity"]
        assert task.custom_metadata["model_params"] == {"max_depth": 5, "n_estimators": 100}
        
        # Update existing metadata
        task.update_custom_metadata("sample_size", 1500)
        assert task.custom_metadata["sample_size"] == 1500