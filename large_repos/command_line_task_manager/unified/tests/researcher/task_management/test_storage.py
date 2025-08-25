import pytest
from uuid import uuid4

from researchtrack.task_management.models import (
    ResearchQuestion,
    ResearchTask,
    TaskPriority,
    TaskStatus,
)
from researchtrack.task_management.storage import InMemoryTaskStorage


class TestInMemoryTaskStorage:
    def test_create_and_get_task(self):
        # Test creating and retrieving a task
        storage = InMemoryTaskStorage()
        
        task = ResearchTask(
            title="Analyze neural network architecture effectiveness",
            description="Compare performance of different NN architectures on climate data",
        )
        
        task_id = storage.create_task(task)
        retrieved_task = storage.get_task(task_id)
        
        assert retrieved_task is not None
        assert retrieved_task.id == task_id
        assert retrieved_task.title == "Analyze neural network architecture effectiveness"
        assert retrieved_task.description == "Compare performance of different NN architectures on climate data"
    
    def test_update_task(self):
        # Test updating a task
        storage = InMemoryTaskStorage()
        
        task = ResearchTask(
            title="Original title",
            description="Original description",
        )
        
        task_id = storage.create_task(task)
        
        # Update the task
        task.title = "Updated title"
        task.description = "Updated description"
        task.status = TaskStatus.IN_PROGRESS
        
        update_result = storage.update_task(task)
        retrieved_task = storage.get_task(task_id)
        
        assert update_result is True
        assert retrieved_task.title == "Updated title"
        assert retrieved_task.description == "Updated description"
        assert retrieved_task.status == TaskStatus.IN_PROGRESS
    
    def test_update_nonexistent_task(self):
        # Test updating a task that doesn't exist
        storage = InMemoryTaskStorage()
        
        task = ResearchTask(
            title="Nonexistent task",
            description="This task hasn't been created in storage",
        )
        
        update_result = storage.update_task(task)
        assert update_result is False
    
    def test_delete_task(self):
        # Test deleting a task
        storage = InMemoryTaskStorage()
        
        task = ResearchTask(
            title="Task to delete",
            description="This task will be deleted",
        )
        
        task_id = storage.create_task(task)
        delete_result = storage.delete_task(task_id)
        retrieved_task = storage.get_task(task_id)
        
        assert delete_result is True
        assert retrieved_task is None
    
    def test_delete_nonexistent_task(self):
        # Test deleting a task that doesn't exist
        storage = InMemoryTaskStorage()
        
        delete_result = storage.delete_task(uuid4())
        assert delete_result is False
    
    def test_list_tasks_empty(self):
        # Test listing tasks when storage is empty
        storage = InMemoryTaskStorage()
        
        tasks = storage.list_tasks()
        assert len(tasks) == 0
    
    def test_list_tasks_with_filters(self):
        # Test listing tasks with various filters
        storage = InMemoryTaskStorage()
        
        # Create tasks with different statuses, priorities, and tags
        task1 = ResearchTask(
            title="Task 1",
            description="First task",
            status=TaskStatus.PLANNED,
            priority=TaskPriority.LOW,
        )
        task1.add_tag("data")
        task1.add_tag("planning")
        
        task2 = ResearchTask(
            title="Task 2",
            description="Second task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
        )
        task2.add_tag("analysis")
        
        task3 = ResearchTask(
            title="Task 3",
            description="Third task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
        )
        task3.add_tag("data")
        task3.add_tag("analysis")
        
        task4 = ResearchTask(
            title="Task 4",
            description="Fourth task",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.MEDIUM,
        )
        task4.add_tag("reporting")
        
        storage.create_task(task1)
        storage.create_task(task2)
        storage.create_task(task3)
        storage.create_task(task4)
        
        # Test filtering by status
        planned_tasks = storage.list_tasks(status=TaskStatus.PLANNED)
        assert len(planned_tasks) == 1
        assert planned_tasks[0].title == "Task 1"
        
        in_progress_tasks = storage.list_tasks(status=TaskStatus.IN_PROGRESS)
        assert len(in_progress_tasks) == 2
        assert {task.title for task in in_progress_tasks} == {"Task 2", "Task 3"}
        
        # Test filtering by priority
        medium_priority_tasks = storage.list_tasks(priority=TaskPriority.MEDIUM)
        assert len(medium_priority_tasks) == 2
        assert {task.title for task in medium_priority_tasks} == {"Task 2", "Task 4"}
        
        # Test filtering by tags
        data_tasks = storage.list_tasks(tags={"data"})
        assert len(data_tasks) == 2
        assert {task.title for task in data_tasks} == {"Task 1", "Task 3"}
        
        analysis_data_tasks = storage.list_tasks(tags={"data", "analysis"})
        assert len(analysis_data_tasks) == 1
        assert analysis_data_tasks[0].title == "Task 3"
        
        # Test combined filters
        in_progress_high_priority = storage.list_tasks(
            status=TaskStatus.IN_PROGRESS, priority=TaskPriority.HIGH
        )
        assert len(in_progress_high_priority) == 1
        assert in_progress_high_priority[0].title == "Task 3"
    
    def test_research_question_operations(self):
        # Test research question CRUD operations
        storage = InMemoryTaskStorage()
        
        # Create
        question = ResearchQuestion(
            text="How do atmospheric aerosols impact cloud formation?",
            description="Investigating the relationship between aerosol concentrations and cloud properties",
        )
        
        question_id = storage.create_research_question(question)
        
        # Read
        retrieved_question = storage.get_research_question(question_id)
        
        assert retrieved_question is not None
        assert retrieved_question.id == question_id
        assert retrieved_question.text == "How do atmospheric aerosols impact cloud formation?"
        
        # Update
        question.text = "Updated research question"
        update_result = storage.update_research_question(question)
        retrieved_question = storage.get_research_question(question_id)
        
        assert update_result is True
        assert retrieved_question.text == "Updated research question"
        
        # Delete
        delete_result = storage.delete_research_question(question_id)
        retrieved_question = storage.get_research_question(question_id)
        
        assert delete_result is True
        assert retrieved_question is None
    
    def test_update_nonexistent_question(self):
        # Test updating a question that doesn't exist
        storage = InMemoryTaskStorage()
        
        question = ResearchQuestion(
            text="Nonexistent question",
            description="This question hasn't been created in storage",
        )
        
        update_result = storage.update_research_question(question)
        assert update_result is False
    
    def test_delete_nonexistent_question(self):
        # Test deleting a question that doesn't exist
        storage = InMemoryTaskStorage()
        
        delete_result = storage.delete_research_question(uuid4())
        assert delete_result is False
    
    def test_list_research_questions(self):
        # Test listing research questions
        storage = InMemoryTaskStorage()
        
        # Create parent question
        parent_question = ResearchQuestion(
            text="Main research question",
            description="The main area of investigation",
        )
        parent_id = storage.create_research_question(parent_question)
        
        # Create sub-questions
        sub_question1 = ResearchQuestion(
            text="Sub-question 1",
            description="First sub-area",
            parent_question_id=parent_id,
        )
        sub_question2 = ResearchQuestion(
            text="Sub-question 2",
            description="Second sub-area",
            parent_question_id=parent_id,
        )
        
        # Create unrelated question
        unrelated_question = ResearchQuestion(
            text="Unrelated question",
            description="Different research area",
        )
        
        sub_id1 = storage.create_research_question(sub_question1)
        sub_id2 = storage.create_research_question(sub_question2)
        unrelated_id = storage.create_research_question(unrelated_question)
        
        # List all questions
        all_questions = storage.list_research_questions()
        assert len(all_questions) == 4
        
        # List sub-questions
        sub_questions = storage.list_research_questions(parent_question_id=parent_id)
        assert len(sub_questions) == 2
        assert {q.text for q in sub_questions} == {"Sub-question 1", "Sub-question 2"}
        
        # List top-level questions (no parent)
        top_questions = storage.list_research_questions(parent_question_id=None)
        assert len(top_questions) == 2
        assert {q.text for q in top_questions} == {"Main research question", "Unrelated question"}
    
    def test_task_question_associations(self):
        # Test associations between tasks and research questions
        storage = InMemoryTaskStorage()
        
        # Create questions
        question1 = ResearchQuestion(text="Question 1")
        question2 = ResearchQuestion(text="Question 2")
        question3 = ResearchQuestion(text="Question 3")
        
        q1_id = storage.create_research_question(question1)
        q2_id = storage.create_research_question(question2)
        q3_id = storage.create_research_question(question3)
        
        # Create tasks with associations
        task1 = ResearchTask(title="Task 1", description="First task")
        task1.add_research_question(q1_id)
        task1.add_research_question(q2_id)
        
        task2 = ResearchTask(title="Task 2", description="Second task")
        task2.add_research_question(q1_id)
        
        task3 = ResearchTask(title="Task 3", description="Third task")
        task3.add_research_question(q3_id)
        
        t1_id = storage.create_task(task1)
        t2_id = storage.create_task(task2)
        t3_id = storage.create_task(task3)
        
        # Get tasks by question
        q1_tasks = storage.get_tasks_by_research_question(q1_id)
        assert len(q1_tasks) == 2
        assert {task.title for task in q1_tasks} == {"Task 1", "Task 2"}
        
        q2_tasks = storage.get_tasks_by_research_question(q2_id)
        assert len(q2_tasks) == 1
        assert q2_tasks[0].title == "Task 1"
        
        q3_tasks = storage.get_tasks_by_research_question(q3_id)
        assert len(q3_tasks) == 1
        assert q3_tasks[0].title == "Task 3"
        
        # Test filtering tasks by question
        q1_filtered_tasks = storage.list_tasks(research_question_id=q1_id)
        assert len(q1_filtered_tasks) == 2
        assert {task.title for task in q1_filtered_tasks} == {"Task 1", "Task 2"}
    
    def test_subtask_relationships(self):
        # Test parent-child task relationships
        storage = InMemoryTaskStorage()
        
        # Create parent task
        parent_task = ResearchTask(
            title="Parent task",
            description="Main research task",
        )
        parent_id = storage.create_task(parent_task)
        
        # Create subtasks
        subtask1 = ResearchTask(
            title="Subtask 1",
            description="First subtask",
            parent_task_id=parent_id,
        )
        subtask2 = ResearchTask(
            title="Subtask 2",
            description="Second subtask",
            parent_task_id=parent_id,
        )
        
        subtask1_id = storage.create_task(subtask1)
        subtask2_id = storage.create_task(subtask2)
        
        # Update parent with subtask references
        parent_task = storage.get_task(parent_id)
        parent_task.add_subtask(subtask1_id)
        parent_task.add_subtask(subtask2_id)
        storage.update_task(parent_task)
        
        # Verify parent has subtask references
        updated_parent = storage.get_task(parent_id)
        assert len(updated_parent.subtask_ids) == 2
        assert subtask1_id in updated_parent.subtask_ids
        assert subtask2_id in updated_parent.subtask_ids
        
        # Get subtasks by parent
        subtasks = storage.get_subtasks(parent_id)
        assert len(subtasks) == 2
        assert {task.title for task in subtasks} == {"Subtask 1", "Subtask 2"}
    
    def test_delete_task_subtask_cleanup(self):
        # Test that deleting a task also cleans up references from parent tasks
        storage = InMemoryTaskStorage()
        
        # Create parent and subtask
        parent_task = ResearchTask(title="Parent task", description="Main task")
        subtask = ResearchTask(title="Subtask", description="Child task")
        
        parent_id = storage.create_task(parent_task)
        subtask_id = storage.create_task(subtask)
        
        # Link subtask to parent
        parent_task = storage.get_task(parent_id)
        parent_task.add_subtask(subtask_id)
        storage.update_task(parent_task)
        
        # Verify link exists
        parent_task = storage.get_task(parent_id)
        assert subtask_id in parent_task.subtask_ids
        
        # Delete subtask
        storage.delete_task(subtask_id)
        
        # Verify parent no longer references deleted subtask
        parent_task = storage.get_task(parent_id)
        assert subtask_id not in parent_task.subtask_ids
    
    def test_delete_question_cleanup(self):
        # Test that deleting a question cleans up references
        storage = InMemoryTaskStorage()
        
        # Create parent and child questions
        parent_question = ResearchQuestion(text="Parent question")
        child_question = ResearchQuestion(text="Child question")
        
        parent_id = storage.create_research_question(parent_question)
        
        # Set parent relationship
        child_question.parent_question_id = parent_id
        child_id = storage.create_research_question(child_question)
        
        # Create task with reference to the question
        task = ResearchTask(title="Related task", description="Task related to the question")
        task.add_research_question(parent_id)
        task_id = storage.create_task(task)
        
        # Verify relationships
        child = storage.get_research_question(child_id)
        assert child.parent_question_id == parent_id
        
        task = storage.get_task(task_id)
        assert parent_id in task.research_question_ids
        
        # Delete parent question
        storage.delete_research_question(parent_id)
        
        # Verify child question's parent reference is removed
        child = storage.get_research_question(child_id)
        assert child.parent_question_id is None
        
        # Verify task's reference to the question is removed
        task = storage.get_task(task_id)
        assert parent_id not in task.research_question_ids