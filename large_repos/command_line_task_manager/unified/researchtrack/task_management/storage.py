from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Union
from uuid import UUID

from .models import ResearchQuestion, ResearchTask, TaskPriority, TaskStatus


class TaskStorageInterface(ABC):
    """Abstract interface for task storage implementations."""
    
    @abstractmethod
    def create_task(self, task: ResearchTask) -> UUID:
        """
        Create a new research task.
        
        Args:
            task: The task to create
            
        Returns:
            UUID: The ID of the created task
        """
        pass
    
    @abstractmethod
    def get_task(self, task_id: UUID) -> Optional[ResearchTask]:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            Optional[ResearchTask]: The task if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_task(self, task: ResearchTask) -> bool:
        """
        Update an existing task.
        
        Args:
            task: The task with updated fields
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_task(self, task_id: UUID) -> bool:
        """
        Delete a task by ID.
        
        Args:
            task_id: The ID of the task to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        tags: Optional[Set[str]] = None,
        research_question_id: Optional[UUID] = None,
    ) -> List[ResearchTask]:
        """
        List tasks with optional filtering.
        
        Args:
            status: Filter by task status
            priority: Filter by task priority
            tags: Filter by tags (tasks must have all specified tags)
            research_question_id: Filter by associated research question ID
            
        Returns:
            List[ResearchTask]: List of tasks matching the criteria
        """
        pass
    
    @abstractmethod
    def create_research_question(self, question: ResearchQuestion) -> UUID:
        """
        Create a new research question.
        
        Args:
            question: The research question to create
            
        Returns:
            UUID: The ID of the created research question
        """
        pass
    
    @abstractmethod
    def get_research_question(self, question_id: UUID) -> Optional[ResearchQuestion]:
        """
        Retrieve a research question by ID.
        
        Args:
            question_id: The ID of the research question to retrieve
            
        Returns:
            Optional[ResearchQuestion]: The research question if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_research_question(self, question: ResearchQuestion) -> bool:
        """
        Update an existing research question.
        
        Args:
            question: The research question with updated fields
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_research_question(self, question_id: UUID) -> bool:
        """
        Delete a research question by ID.
        
        Args:
            question_id: The ID of the research question to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_research_questions(
        self, parent_question_id: Optional[UUID] = ...
    ) -> List[ResearchQuestion]:
        """
        List research questions with optional filtering.
        
        Args:
            parent_question_id: Filter by parent question ID. If not provided, returns all questions.
                                If set to None, returns only top-level questions (with no parent).
            
        Returns:
            List[ResearchQuestion]: List of research questions matching the criteria
        """
        pass
    
    @abstractmethod
    def get_tasks_by_research_question(
        self, question_id: UUID
    ) -> List[ResearchTask]:
        """
        Get all tasks associated with a research question.
        
        Args:
            question_id: The ID of the research question
            
        Returns:
            List[ResearchTask]: List of tasks associated with the research question
        """
        pass
    
    @abstractmethod
    def get_subtasks(self, parent_task_id: UUID) -> List[ResearchTask]:
        """
        Get all subtasks of a parent task.
        
        Args:
            parent_task_id: The ID of the parent task
            
        Returns:
            List[ResearchTask]: List of subtasks
        """
        pass


class InMemoryTaskStorage(TaskStorageInterface):
    """In-memory implementation of task storage."""
    
    def __init__(self):
        self._tasks: Dict[UUID, ResearchTask] = {}
        self._questions: Dict[UUID, ResearchQuestion] = {}
    
    def create_task(self, task: ResearchTask) -> UUID:
        self._tasks[task.id] = task
        return task.id
    
    def get_task(self, task_id: UUID) -> Optional[ResearchTask]:
        return self._tasks.get(task_id)
    
    def update_task(self, task: ResearchTask) -> bool:
        if task.id not in self._tasks:
            return False
        self._tasks[task.id] = task
        return True
    
    def delete_task(self, task_id: UUID) -> bool:
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        # Remove this task as a subtask from any parent tasks
        for task in self._tasks.values():
            if task_id in task.subtask_ids:
                task.subtask_ids.remove(task_id)
        return True
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        tags: Optional[Set[str]] = None,
        research_question_id: Optional[UUID] = None,
    ) -> List[ResearchTask]:
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [task for task in tasks if task.status == status]
        
        if priority:
            tasks = [task for task in tasks if task.priority == priority]
        
        if tags:
            tasks = [
                task for task in tasks if all(tag in task.tags for tag in tags)
            ]
        
        if research_question_id:
            tasks = [
                task
                for task in tasks
                if research_question_id in task.research_question_ids
            ]
        
        return tasks
    
    def create_research_question(self, question: ResearchQuestion) -> UUID:
        self._questions[question.id] = question
        return question.id
    
    def get_research_question(self, question_id: UUID) -> Optional[ResearchQuestion]:
        return self._questions.get(question_id)
    
    def update_research_question(self, question: ResearchQuestion) -> bool:
        if question.id not in self._questions:
            return False
        self._questions[question.id] = question
        return True
    
    def delete_research_question(self, question_id: UUID) -> bool:
        if question_id not in self._questions:
            return False
        
        # Check if this question is a parent to any other questions
        child_questions = [q for q in self._questions.values() if q.parent_question_id == question_id]
        if child_questions:
            # Update child questions to remove parent reference
            for child in child_questions:
                child.parent_question_id = None
        
        # Remove association from any tasks
        for task in self._tasks.values():
            if question_id in task.research_question_ids:
                task.research_question_ids.remove(question_id)
                
        del self._questions[question_id]
        return True
    
    def list_research_questions(
        self, parent_question_id: Optional[UUID] = ...
    ) -> List[ResearchQuestion]:
        questions = list(self._questions.values())
        
        # If parent_question_id is not specified (default value), return all questions
        if parent_question_id is ...:
            return questions
        
        # If parent_question_id is set to None, return top-level questions (those with no parent)
        # Otherwise, return questions with the specified parent
        filtered_questions = []
        for q in questions:
            # For parent_question_id=None, include questions with no parent
            if parent_question_id is None and q.parent_question_id is None:
                filtered_questions.append(q)
            # For specific parent_id, include questions with that parent
            elif q.parent_question_id == parent_question_id:
                filtered_questions.append(q)
        
        return filtered_questions
    
    def get_tasks_by_research_question(self, question_id: UUID) -> List[ResearchTask]:
        all_tasks = list(self._tasks.values())
        return [
            task
            for task in all_tasks
            if question_id in task.research_question_ids
        ]
    
    def get_subtasks(self, parent_task_id: UUID) -> List[ResearchTask]:
        return [
            task for task in self._tasks.values()
            if task.parent_task_id == parent_task_id
        ]