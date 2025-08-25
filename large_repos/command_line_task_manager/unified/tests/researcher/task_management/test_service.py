from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from researchtrack.task_management.models import TaskPriority, TaskStatus
from researchtrack.task_management.service import TaskManagementService
from researchtrack.task_management.storage import InMemoryTaskStorage


class TestTaskManagementService:
    def setup_method(self):
        """Set up a fresh service instance for each test."""
        self.storage = InMemoryTaskStorage()
        self.service = TaskManagementService(self.storage)
    
    def test_create_task(self):
        # Test creating a basic task
        task_id = self.service.create_task(
            title="Analyze gene expression data",
            description="Run differential expression analysis on RNA-seq data",
            status=TaskStatus.PLANNED,
            priority=TaskPriority.HIGH,
            estimated_hours=6.0,
        )
        
        task = self.service.get_task(task_id)
        
        assert task is not None
        assert task.title == "Analyze gene expression data"
        assert task.description == "Run differential expression analysis on RNA-seq data"
        assert task.status == TaskStatus.PLANNED
        assert task.priority == TaskPriority.HIGH
        assert task.estimated_hours == 6.0
    
    def test_create_task_with_parent(self):
        # Test creating a task with a parent task
        parent_id = self.service.create_task(
            title="Main analysis project",
            description="Parent task for gene expression analysis",
        )
        
        subtask_id = self.service.create_task(
            title="Data preprocessing",
            description="Preprocess raw sequencing data",
            parent_task_id=parent_id,
        )
        
        parent_task = self.service.get_task(parent_id)
        subtask = self.service.get_task(subtask_id)
        
        assert subtask.parent_task_id == parent_id
        assert subtask_id in parent_task.subtask_ids
    
    def test_create_task_invalid_parent(self):
        # Test creating a task with invalid parent
        with pytest.raises(ValueError, match="Parent task .* does not exist"):
            self.service.create_task(
                title="Task with bad parent",
                description="This task has a nonexistent parent",
                parent_task_id=uuid4(),
            )
    
    def test_create_task_with_research_questions(self):
        # Test creating a task with research questions
        question_id1 = self.service.create_research_question(
            text="How does gene A influence phenotype B?",
        )
        question_id2 = self.service.create_research_question(
            text="What pathways are affected by gene A?",
        )
        
        task_id = self.service.create_task(
            title="Investigate gene A effects",
            description="Comprehensive analysis of gene A effects",
            research_question_ids={question_id1, question_id2},
        )
        
        task = self.service.get_task(task_id)
        
        assert question_id1 in task.research_question_ids
        assert question_id2 in task.research_question_ids
    
    def test_create_task_invalid_question(self):
        # Test creating a task with invalid research question
        with pytest.raises(ValueError, match="Research question .* does not exist"):
            self.service.create_task(
                title="Task with bad question",
                description="This task has a nonexistent research question",
                research_question_ids={uuid4()},
            )
    
    def test_update_task(self):
        # Test updating a task
        task_id = self.service.create_task(
            title="Original title",
            description="Original description",
            status=TaskStatus.PLANNED,
            priority=TaskPriority.MEDIUM,
        )
        
        result = self.service.update_task(
            task_id=task_id,
            title="Updated title",
            description="Updated description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            estimated_hours=10.0,
            actual_hours=2.5,
        )
        
        task = self.service.get_task(task_id)
        
        assert result is True
        assert task.title == "Updated title"
        assert task.description == "Updated description"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == TaskPriority.HIGH
        assert task.estimated_hours == 10.0
        assert task.actual_hours == 2.5
    
    def test_update_nonexistent_task(self):
        # Test updating a nonexistent task
        with pytest.raises(ValueError, match="Task .* does not exist"):
            self.service.update_task(
                task_id=uuid4(),
                title="Updated title",
            )
    
    def test_delete_task(self):
        # Test deleting a task
        task_id = self.service.create_task(
            title="Task to delete",
            description="This task will be deleted",
        )
        
        assert self.service.get_task(task_id) is not None
        
        result = self.service.delete_task(task_id)
        
        assert result is True
        assert self.service.get_task(task_id) is None
    
    def test_add_task_note(self):
        # Test adding a note to a task
        task_id = self.service.create_task(
            title="Task with notes",
            description="Testing note functionality",
        )
        
        self.service.add_task_note(task_id, "First research note")
        self.service.add_task_note(task_id, "Follow-up observation")
        
        task = self.service.get_task(task_id)
        
        assert len(task.notes) == 2
        assert task.notes[0] == "First research note"
        assert task.notes[1] == "Follow-up observation"
    
    def test_add_note_to_nonexistent_task(self):
        # Test adding a note to a nonexistent task
        with pytest.raises(ValueError, match="Task .* does not exist"):
            self.service.add_task_note(uuid4(), "Note on nonexistent task")
    
    def test_tag_management(self):
        # Test adding and removing tags
        task_id = self.service.create_task(
            title="Task with tags",
            description="Testing tag functionality",
        )
        
        self.service.add_task_tag(task_id, "genomics")
        self.service.add_task_tag(task_id, "bioinformatics")
        self.service.add_task_tag(task_id, "rnaseq")
        
        task = self.service.get_task(task_id)
        assert len(task.tags) == 3
        assert "genomics" in task.tags
        assert "bioinformatics" in task.tags
        assert "rnaseq" in task.tags
        
        self.service.remove_task_tag(task_id, "bioinformatics")
        
        task = self.service.get_task(task_id)
        assert len(task.tags) == 2
        assert "genomics" in task.tags
        assert "bioinformatics" not in task.tags
        assert "rnaseq" in task.tags
    
    def test_custom_metadata(self):
        # Test updating custom metadata
        task_id = self.service.create_task(
            title="Task with metadata",
            description="Testing metadata functionality",
        )
        
        self.service.update_task_custom_metadata(task_id, "dataset_source", "EBI ArrayExpress")
        self.service.update_task_custom_metadata(task_id, "sample_count", 48)
        self.service.update_task_custom_metadata(task_id, "includes_controls", True)
        
        task = self.service.get_task(task_id)
        
        assert task.custom_metadata["dataset_source"] == "EBI ArrayExpress"
        assert task.custom_metadata["sample_count"] == 48
        assert task.custom_metadata["includes_controls"] is True
    
    def test_filter_tasks(self):
        # Test filtering tasks
        # Create tasks with different properties
        self.service.create_task(
            title="Task 1",
            description="First task",
            status=TaskStatus.PLANNED,
            priority=TaskPriority.LOW,
            tags={"literature", "planning"},
        )
        
        self.service.create_task(
            title="Task 2",
            description="Second task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            tags={"experiment", "analysis"},
        )
        
        self.service.create_task(
            title="Task 3",
            description="Third task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            tags={"analysis", "computation"},
        )
        
        self.service.create_task(
            title="Task 4",
            description="Fourth task",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.MEDIUM,
            tags={"reporting", "analysis"},
        )
        
        # Test different filters
        planned_tasks = self.service.list_tasks(status=TaskStatus.PLANNED)
        assert len(planned_tasks) == 1
        assert planned_tasks[0].title == "Task 1"
        
        in_progress_tasks = self.service.list_tasks(status=TaskStatus.IN_PROGRESS)
        assert len(in_progress_tasks) == 2
        assert {task.title for task in in_progress_tasks} == {"Task 2", "Task 3"}
        
        medium_priority_tasks = self.service.list_tasks(priority=TaskPriority.MEDIUM)
        assert len(medium_priority_tasks) == 2
        assert {task.title for task in medium_priority_tasks} == {"Task 2", "Task 4"}
        
        analysis_tasks = self.service.list_tasks(tags={"analysis"})
        assert len(analysis_tasks) == 3
        assert {task.title for task in analysis_tasks} == {"Task 2", "Task 3", "Task 4"}
        
        in_progress_high_tasks = self.service.list_tasks(
            status=TaskStatus.IN_PROGRESS, priority=TaskPriority.HIGH
        )
        assert len(in_progress_high_tasks) == 1
        assert in_progress_high_tasks[0].title == "Task 3"
    
    def test_research_question_operations(self):
        # Test research question operations
        question_id = self.service.create_research_question(
            text="Main research question",
            description="Primary investigation focus",
        )
        
        question = self.service.get_research_question(question_id)
        
        assert question is not None
        assert question.text == "Main research question"
        assert question.description == "Primary investigation focus"
        
        # Update the question
        self.service.update_research_question(
            question_id=question_id,
            text="Updated research question",
            description="Refined focus",
        )
        
        updated_question = self.service.get_research_question(question_id)
        assert updated_question.text == "Updated research question"
        assert updated_question.description == "Refined focus"
        
        # Delete the question
        result = self.service.delete_research_question(question_id)
        assert result is True
        assert self.service.get_research_question(question_id) is None
    
    def test_research_question_hierarchy(self):
        # Test creating a hierarchy of research questions
        parent_id = self.service.create_research_question(
            text="How do climate factors affect agricultural yields?",
            description="Main research area",
        )
        
        sub_id1 = self.service.create_research_question(
            text="How does temperature variation impact wheat production?",
            description="Temperature sub-question",
            parent_question_id=parent_id,
        )
        
        sub_id2 = self.service.create_research_question(
            text="How does precipitation pattern affect corn yields?",
            description="Precipitation sub-question",
            parent_question_id=parent_id,
        )
        
        # List sub-questions
        sub_questions = self.service.list_research_questions(parent_question_id=parent_id)
        assert len(sub_questions) == 2
        assert {q.text for q in sub_questions} == {
            "How does temperature variation impact wheat production?",
            "How does precipitation pattern affect corn yields?",
        }
        
        # List top-level questions
        top_questions = self.service.list_research_questions(parent_question_id=None)
        assert len(top_questions) == 1
        assert top_questions[0].text == "How do climate factors affect agricultural yields?"
    
    def test_task_question_association(self):
        # Test associating tasks with research questions
        question_id = self.service.create_research_question(
            text="How effective is treatment X for condition Y?",
        )
        
        task_id = self.service.create_task(
            title="Literature review on treatment X",
            description="Comprehensive review of existing studies",
        )
        
        # Associate task with question
        result = self.service.associate_task_with_research_question(task_id, question_id)
        assert result is True
        
        # Check association exists
        task = self.service.get_task(task_id)
        assert question_id in task.research_question_ids
        
        # Get tasks by question
        question_tasks = self.service.get_tasks_by_research_question(question_id)
        assert len(question_tasks) == 1
        assert question_tasks[0].id == task_id
        
        # Remove association
        result = self.service.dissociate_task_from_research_question(task_id, question_id)
        assert result is True
        
        task = self.service.get_task(task_id)
        assert question_id not in task.research_question_ids
        
        question_tasks = self.service.get_tasks_by_research_question(question_id)
        assert len(question_tasks) == 0
    
    def test_associate_with_nonexistent_task(self):
        # Test associating a nonexistent task with a question
        question_id = self.service.create_research_question(
            text="Valid research question",
        )
        
        with pytest.raises(ValueError, match="Task .* does not exist"):
            self.service.associate_task_with_research_question(uuid4(), question_id)
    
    def test_associate_with_nonexistent_question(self):
        # Test associating a task with a nonexistent question
        task_id = self.service.create_task(
            title="Valid task",
            description="A valid task",
        )
        
        with pytest.raises(ValueError, match="Research question .* does not exist"):
            self.service.associate_task_with_research_question(task_id, uuid4())
    
    def test_get_subtasks(self):
        # Test getting subtasks of a parent task
        parent_id = self.service.create_task(
            title="Parent task",
            description="Main research project",
        )
        
        subtask1_id = self.service.create_task(
            title="Subtask 1",
            description="First component",
            parent_task_id=parent_id,
        )
        
        subtask2_id = self.service.create_task(
            title="Subtask 2",
            description="Second component",
            parent_task_id=parent_id,
        )
        
        subtasks = self.service.get_subtasks(parent_id)
        
        assert len(subtasks) == 2
        assert {task.title for task in subtasks} == {"Subtask 1", "Subtask 2"}