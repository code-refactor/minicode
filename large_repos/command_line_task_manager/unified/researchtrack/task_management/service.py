from datetime import datetime
from typing import Dict, List, Optional, Set, Union, Any
from uuid import uuid4

from .models import ResearchQuestion, ResearchTask, TaskPriority, TaskStatus
from .storage import TaskStorageInterface


class TaskManagementService:
    """Service for managing research tasks and questions."""

    def __init__(self, storage: TaskStorageInterface):
        """
        Initialize the task management service.

        Args:
            storage: The storage implementation to use
        """
        self._storage = storage

        # Reference validation callback to be set by external services
        self._validate_reference_callback = None

        # Dataset validation callback to be set by external services
        self._validate_dataset_callback = None

        # Environment validation callback to be set by external services
        self._validate_environment_callback = None

        # Experiment validation callback to be set by external services
        self._validate_experiment_callback = None

    def set_reference_validator(self, validator_callback):
        """
        Set a callback function to validate reference IDs.

        Args:
            validator_callback: A function that takes a reference ID and returns True if valid
        """
        self._validate_reference_callback = validator_callback

    def set_dataset_validator(self, validator_callback):
        """
        Set a callback function to validate dataset IDs.

        Args:
            validator_callback: A function that takes a dataset ID and returns True if valid
        """
        self._validate_dataset_callback = validator_callback

    def set_environment_validator(self, validator_callback):
        """
        Set a callback function to validate environment IDs.

        Args:
            validator_callback: A function that takes an environment ID and returns True if valid
        """
        self._validate_environment_callback = validator_callback

    def set_experiment_validator(self, validator_callback):
        """
        Set a callback function to validate experiment IDs.

        Args:
            validator_callback: A function that takes an experiment ID and returns True if valid
        """
        self._validate_experiment_callback = validator_callback
    
    # Task operations
    
    def create_task(
        self,
        title: str,
        description: str,
        status: TaskStatus = TaskStatus.PLANNED,
        priority: TaskPriority = TaskPriority.MEDIUM,
        estimated_hours: Optional[float] = None,
        due_date: Optional[datetime] = None,
        parent_task_id: Optional[str] = None,
        research_question_ids: Optional[Set[str]] = None,
        tags: Optional[Set[str]] = None,
        custom_metadata: Optional[Dict[str, Union[str, int, float, bool, list, dict]]] = None,
    ) -> str:
        """
        Create a new research task.
        
        Args:
            title: Task title
            description: Task description
            status: Task status
            priority: Task priority
            estimated_hours: Estimated hours to complete the task
            due_date: Task due date
            parent_task_id: Parent task ID if this is a subtask
            research_question_ids: Associated research question IDs
            tags: Task tags
            custom_metadata: Custom metadata key-value pairs
            
        Returns:
            str: The ID of the created task
            
        Raises:
            ValueError: If parent task doesn't exist
        """
        # Validate parent task if provided
        if parent_task_id:
            parent_task = self._storage.get_task(parent_task_id)
            if not parent_task:
                raise ValueError(f"Parent task with ID {parent_task_id} does not exist")
        
        # Validate research questions if provided
        if research_question_ids:
            for q_id in research_question_ids:
                question = self._storage.get_research_question(q_id)
                if not question:
                    raise ValueError(f"Research question with ID {q_id} does not exist")
        
        # Create task
        task = ResearchTask(
            title=title,
            description=description,
            status=status,
            priority=priority,
            estimated_hours=estimated_hours,
            due_date=due_date,
            parent_task_id=parent_task_id,
            research_question_ids=research_question_ids or set(),
            tags=tags or set(),
            custom_metadata=custom_metadata or {},
        )
        
        # Save task
        task_id = self._storage.create_task(task)
        
        # Update parent task if needed
        if parent_task_id:
            parent_task = self._storage.get_task(parent_task_id)
            if parent_task:
                parent_task.add_subtask(task_id)
                self._storage.update_task(parent_task)
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            Optional[ResearchTask]: The task if found, None otherwise
        """
        return self._storage.get_task(task_id)
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        estimated_hours: Optional[float] = None,
        actual_hours: Optional[float] = None,
        due_date: Optional[datetime] = None,
    ) -> bool:
        """
        Update an existing task.
        
        Args:
            task_id: The ID of the task to update
            title: New task title
            description: New task description
            status: New task status
            priority: New task priority
            estimated_hours: New estimated hours
            actual_hours: New actual hours
            due_date: New due date
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")
        
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if status is not None:
            update_data["status"] = status
        if priority is not None:
            update_data["priority"] = priority
        if estimated_hours is not None:
            update_data["estimated_hours"] = estimated_hours
        if actual_hours is not None:
            update_data["actual_hours"] = actual_hours
        if due_date is not None:
            update_data["due_date"] = due_date
        
        task = task.update_fields(**update_data)
        return self._storage.update_task(task)
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task by ID.
        
        Args:
            task_id: The ID of the task to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_task(task_id)
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        tags: Optional[Set[str]] = None,
        research_question_id: Optional[str] = None,
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
        return self._storage.list_tasks(
            status=status,
            priority=priority,
            tags=tags,
            research_question_id=research_question_id,
        )
    
    def add_task_note(self, task_id: str, note: str) -> bool:
        """
        Add a note to a task.
        
        Args:
            task_id: The ID of the task
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")
        
        task.add_note(note)
        return self._storage.update_task(task)
    
    def add_task_tag(self, task_id: str, tag: str) -> bool:
        """
        Add a tag to a task.
        
        Args:
            task_id: The ID of the task
            tag: The tag to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")
        
        task.add_tag(tag)
        return self._storage.update_task(task)
    
    def remove_task_tag(self, task_id: str, tag: str) -> bool:
        """
        Remove a tag from a task.
        
        Args:
            task_id: The ID of the task
            tag: The tag to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")
        
        task.remove_tag(tag)
        return self._storage.update_task(task)
    
    def update_task_custom_metadata(
        self, task_id: str, key: str, value: Union[str, int, float, bool, list, dict]
    ) -> bool:
        """
        Update a custom metadata field on a task.
        
        Args:
            task_id: The ID of the task
            key: The metadata key
            value: The metadata value
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")
        
        task.update_custom_metadata(key, value)
        return self._storage.update_task(task)
    
    def get_subtasks(self, parent_task_id: str) -> List[ResearchTask]:
        """
        Get all subtasks of a parent task.
        
        Args:
            parent_task_id: The ID of the parent task
            
        Returns:
            List[ResearchTask]: List of subtasks
        """
        return self._storage.get_subtasks(parent_task_id)
    
    # Research question operations
    
    def create_research_question(
        self, text: str, description: Optional[str] = None, parent_question_id: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Create a new research question and optionally associate it with a task.

        Args:
            text: The research question text
            description: Optional detailed description
            parent_question_id: Parent question ID if this is a sub-question
            task_id: The ID of the task to associate with this question

        Returns:
            str: The ID of the created question

        Raises:
            ValueError: If parent question or task doesn't exist
        """
        # Validate parent question if provided
        if parent_question_id:
            parent_question = self._storage.get_research_question(parent_question_id)
            if not parent_question:
                raise ValueError(f"Parent question with ID {parent_question_id} does not exist")

        # Create question
        question = ResearchQuestion(
            text=text,
            description=description,
            parent_question_id=parent_question_id,
        )

        # Save question
        question_id = self._storage.create_research_question(question)

        # Associate with task if provided
        if task_id:
            task = self._storage.get_task(task_id)
            if not task:
                raise ValueError(f"Task with ID {task_id} does not exist")

            task.add_research_question(question_id)
            self._storage.update_task(task)

        return question_id
    
    def get_research_question(self, question_id: str) -> Optional[ResearchQuestion]:
        """
        Retrieve a research question by ID.
        
        Args:
            question_id: The ID of the research question to retrieve
            
        Returns:
            Optional[ResearchQuestion]: The research question if found, None otherwise
        """
        return self._storage.get_research_question(question_id)
    
    def update_research_question(
        self, question_id: str, text: Optional[str] = None, description: Optional[str] = None
    ) -> bool:
        """
        Update an existing research question.
        
        Args:
            question_id: The ID of the question to update
            text: New question text
            description: New description
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If question doesn't exist
        """
        question = self._storage.get_research_question(question_id)
        if not question:
            raise ValueError(f"Research question with ID {question_id} does not exist")
        
        update_data = {}
        if text is not None:
            update_data["text"] = text
        if description is not None:
            update_data["description"] = description
        
        question = question.update(**update_data)
        return self._storage.update_research_question(question)
    
    def delete_research_question(self, question_id: str) -> bool:
        """
        Delete a research question by ID.
        
        Args:
            question_id: The ID of the research question to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_research_question(question_id)
    
    def list_research_questions(
        self, parent_question_id: Optional[str] = ...
    ) -> List[ResearchQuestion]:
        """
        List research questions with optional filtering.
        
        Args:
            parent_question_id: Filter by parent question ID. If not provided, returns all questions.
                                If set to None, returns only top-level questions (with no parent).
            
        Returns:
            List[ResearchQuestion]: List of research questions matching the criteria
        """
        return self._storage.list_research_questions(parent_question_id=parent_question_id)
    
    def get_tasks_by_research_question(
        self, question_id: str
    ) -> List[ResearchTask]:
        """
        Get all tasks associated with a research question.
        
        Args:
            question_id: The ID of the research question
            
        Returns:
            List[ResearchTask]: List of tasks associated with the research question
        """
        return self._storage.get_tasks_by_research_question(question_id)
    
    def associate_task_with_research_question(
        self, task_id: str, question_id: str
    ) -> bool:
        """
        Associate a task with a research question.
        
        Args:
            task_id: The ID of the task
            question_id: The ID of the research question
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task or question doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")
        
        question = self._storage.get_research_question(question_id)
        if not question:
            raise ValueError(f"Research question with ID {question_id} does not exist")
        
        task.add_research_question(question_id)
        return self._storage.update_task(task)
    
    def dissociate_task_from_research_question(
        self, task_id: str, question_id: str
    ) -> bool:
        """
        Remove association between a task and a research question.

        Args:
            task_id: The ID of the task
            question_id: The ID of the research question

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        task.remove_research_question(question_id)
        return self._storage.update_task(task)

    # Reference association methods

    def add_reference_to_task(self, task_id: str, reference_id: str) -> bool:
        """
        Associate a bibliographic reference with a task.

        Args:
            task_id: The ID of the task
            reference_id: The ID of the bibliographic reference

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist or reference ID is invalid
        """
        # Validate task
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        # Validate reference if validator is set
        if self._validate_reference_callback and not self._validate_reference_callback(reference_id):
            raise ValueError(f"Reference with ID {reference_id} does not exist")

        # Add reference to task
        task.add_reference(reference_id)
        return self._storage.update_task(task)

    def remove_reference_from_task(self, task_id: str, reference_id: str) -> bool:
        """
        Remove association between a bibliographic reference and a task.

        Args:
            task_id: The ID of the task
            reference_id: The ID of the bibliographic reference

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist
        """
        # Validate task
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        # Remove reference from task
        task.remove_reference(reference_id)
        return self._storage.update_task(task)

    def get_task_references(self, task_id: str) -> Set[str]:
        """
        Get all bibliographic references associated with a task.

        Args:
            task_id: The ID of the task

        Returns:
            Set[str]: Set of reference IDs

        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        return task.reference_ids

    # Dataset association methods

    def add_dataset_to_task(self, task_id: str, dataset_id: str) -> bool:
        """
        Associate a dataset with a task.

        Args:
            task_id: The ID of the task
            dataset_id: The ID of the dataset

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist or dataset ID is invalid
        """
        # Validate task
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        # Validate dataset if validator is set
        if self._validate_dataset_callback and not self._validate_dataset_callback(dataset_id):
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")

        # Add dataset to task
        task.add_dataset(dataset_id)
        return self._storage.update_task(task)

    def remove_dataset_from_task(self, task_id: str, dataset_id: str) -> bool:
        """
        Remove association between a dataset and a task.

        Args:
            task_id: The ID of the task
            dataset_id: The ID of the dataset

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist
        """
        # Validate task
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        # Remove dataset from task
        task.remove_dataset(dataset_id)
        return self._storage.update_task(task)

    def get_task_datasets(self, task_id: str) -> Set[str]:
        """
        Get all datasets associated with a task.

        Args:
            task_id: The ID of the task

        Returns:
            Set[str]: Set of dataset IDs

        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        return task.dataset_ids

    # Environment association methods

    def add_environment_to_task(self, task_id: str, environment_id: str) -> bool:
        """
        Associate a computational environment with a task.

        Args:
            task_id: The ID of the task
            environment_id: The ID of the environment

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist or environment ID is invalid
        """
        # Validate task
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        # Validate environment if validator is set
        if self._validate_environment_callback and not self._validate_environment_callback(environment_id):
            raise ValueError(f"Environment with ID {environment_id} does not exist")

        # Add environment to task
        task.add_environment(environment_id)
        return self._storage.update_task(task)

    def remove_environment_from_task(self, task_id: str, environment_id: str) -> bool:
        """
        Remove association between a computational environment and a task.

        Args:
            task_id: The ID of the task
            environment_id: The ID of the environment

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist
        """
        # Validate task
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        # Remove environment from task
        task.remove_environment(environment_id)
        return self._storage.update_task(task)

    def get_task_environments(self, task_id: str) -> Set[str]:
        """
        Get all computational environments associated with a task.

        Args:
            task_id: The ID of the task

        Returns:
            Set[str]: Set of environment IDs

        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        return task.environment_ids

    # Experiment association methods

    def add_experiment_to_task(self, task_id: str, experiment_id: str) -> bool:
        """
        Associate an experiment with a task.

        Args:
            task_id: The ID of the task
            experiment_id: The ID of the experiment

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist or experiment ID is invalid
        """
        # Validate task
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        # Validate experiment if validator is set
        if self._validate_experiment_callback and not self._validate_experiment_callback(experiment_id):
            raise ValueError(f"Experiment with ID {experiment_id} does not exist")

        # Add experiment to task
        task.add_experiment(experiment_id)
        return self._storage.update_task(task)

    def remove_experiment_from_task(self, task_id: str, experiment_id: str) -> bool:
        """
        Remove association between an experiment and a task.

        Args:
            task_id: The ID of the task
            experiment_id: The ID of the experiment

        Returns:
            bool: True if successful, False otherwise

        Raises:
            ValueError: If task doesn't exist
        """
        # Validate task
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        # Remove experiment from task
        task.remove_experiment(experiment_id)
        return self._storage.update_task(task)

    def get_task_experiments(self, task_id: str) -> Set[str]:
        """
        Get all experiments associated with a task.

        Args:
            task_id: The ID of the task

        Returns:
            Set[str]: Set of experiment IDs

        Raises:
            ValueError: If task doesn't exist
        """
        task = self._storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} does not exist")

        return task.experiment_ids


class TaskService:
    """
    Service for managing research tasks and questions, designed for integration with other services.
    
    This service wraps the TaskManagementService to provide a compatible API for integration tests.
    It adjusts method signatures and return types to match expected usage patterns.
    """
    
    def __init__(self, storage):
        """
        Initialize the task service with a storage implementation.
        
        Args:
            storage: Storage implementation for tasks and questions
        """
        self._service = TaskManagementService(storage)
        
        # Maps for resolving external references
        self._references = {}
        self._datasets = {}
        self._environments = {}
        self._experiments = {}
        
    def create_task(
        self,
        title: str,
        description: str,
        status: TaskStatus = TaskStatus.PLANNED,
        priority: TaskPriority = TaskPriority.MEDIUM,
        estimated_hours: Optional[float] = None,
        due_date: Optional[datetime] = None,
        parent_id: Optional[str] = None,  # Different parameter name from TaskManagementService
        research_question_ids: Optional[Set[str]] = None,
        tags: Optional[Set[str]] = None,
        custom_metadata: Optional[Dict[str, Union[str, int, float, bool, list, dict]]] = None,
    ) -> ResearchTask:
        """
        Create a new research task.
        
        Args:
            title: Task title
            description: Task description
            status: Task status
            priority: Task priority
            estimated_hours: Estimated hours to complete the task
            due_date: Task due date
            parent_id: Parent task ID if this is a subtask (note: different from parent_task_id)
            research_question_ids: Associated research question IDs
            tags: Task tags
            custom_metadata: Custom metadata key-value pairs
            
        Returns:
            ResearchTask: The created task (not just the ID)
            
        Raises:
            ValueError: If parent task doesn't exist
        """
        task_id = self._service.create_task(
            title=title,
            description=description,
            status=status,
            priority=priority,
            estimated_hours=estimated_hours,
            due_date=due_date,
            parent_task_id=parent_id,  # Map parent_id to parent_task_id
            research_question_ids=research_question_ids,
            tags=tags,
            custom_metadata=custom_metadata,
        )
        
        # Return the task object, not just the ID
        return self._service.get_task(task_id)
    
    def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: The ID of the task to retrieve
            
        Returns:
            Optional[ResearchTask]: The task if found, None otherwise
        """
        task = self._service.get_task(task_id)
        if task:
            # Populate convenience properties for integration tests
            # References
            reference_ids = task.reference_ids
            task.references = [self._references.get(ref_id) for ref_id in reference_ids if ref_id in self._references]
            
            # Datasets
            dataset_ids = task.dataset_ids
            task.datasets = [self._datasets.get(ds_id) for ds_id in dataset_ids if ds_id in self._datasets]
            
            # Environments
            environment_ids = task.environment_ids
            task.environments = [self._environments.get(env_id) for env_id in environment_ids if env_id in self._environments]
            
            # Experiments
            experiment_ids = task.experiment_ids
            task.experiments = [self._experiments.get(exp_id) for exp_id in experiment_ids if exp_id in self._experiments]
            
            # Research Questions
            question_ids = task.research_question_ids
            task.research_questions = [self._service.get_research_question(q_id) for q_id in question_ids]
        
        return task
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        estimated_hours: Optional[float] = None,
        actual_hours: Optional[float] = None,
        due_date: Optional[datetime] = None,
    ) -> ResearchTask:
        """
        Update an existing task.
        
        Args:
            task_id: The ID of the task to update
            title: New task title
            description: New task description
            status: New task status
            priority: New task priority
            estimated_hours: New estimated hours
            actual_hours: New actual hours
            due_date: New due date
            
        Returns:
            ResearchTask: The updated task
            
        Raises:
            ValueError: If task doesn't exist
        """
        self._service.update_task(
            task_id=task_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
            due_date=due_date,
        )
        
        # Return the updated task object
        return self._service.get_task(task_id)
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task by ID.
        
        Args:
            task_id: The ID of the task to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._service.delete_task(task_id)
    
    def get_subtasks(self, parent_id: str) -> List[ResearchTask]:
        """
        Get all subtasks of a parent task.
        
        Args:
            parent_id: The ID of the parent task
            
        Returns:
            List[ResearchTask]: List of subtasks
        """
        return self._service.get_subtasks(parent_id)
    
    def create_research_question(
        self, 
        text: str = None,  # Make text optional
        description: Optional[str] = None, 
        parent_question_id: Optional[str] = None,
        task_id: Optional[str] = None,
        question: Optional[str] = None  # Add new parameter for integration tests
    ) -> ResearchQuestion:
        """
        Create a new research question.
        
        Args:
            text: The research question text (original parameter)
            description: Optional detailed description
            parent_question_id: Parent question ID if this is a sub-question
            task_id: Optional task ID to associate with this question
            question: Alternative parameter for the question text (for integration tests)
            
        Returns:
            ResearchQuestion: The created research question (not just the ID)
            
        Raises:
            ValueError: If parent question doesn't exist
        """
        # Use 'question' parameter if provided, otherwise use 'text'
        actual_text = question if question is not None else text
        if actual_text is None:
            raise ValueError("Either 'text' or 'question' parameter must be provided")
            
        question_id = self._service.create_research_question(
            text=actual_text,
            description=description,
            parent_question_id=parent_question_id,
            task_id=task_id
        )
        
        # Return the question object, not just the ID
        return self._service.get_research_question(question_id)
    
    def get_research_question(self, question_id: str) -> Optional[ResearchQuestion]:
        """
        Retrieve a research question by ID.
        
        Args:
            question_id: The ID of the research question to retrieve
            
        Returns:
            Optional[ResearchQuestion]: The research question if found, None otherwise
        """
        return self._service.get_research_question(question_id)
    
    def update_research_question(
        self, question_id: str, text: Optional[str] = None, description: Optional[str] = None
    ) -> ResearchQuestion:
        """
        Update an existing research question.
        
        Args:
            question_id: The ID of the question to update
            text: New question text
            description: New description
            
        Returns:
            ResearchQuestion: The updated research question
            
        Raises:
            ValueError: If question doesn't exist
        """
        self._service.update_research_question(
            question_id=question_id,
            text=text,
            description=description,
        )
        
        # Return the updated question object
        return self._service.get_research_question(question_id)
    
    def delete_research_question(self, question_id: str) -> bool:
        """
        Delete a research question by ID.
        
        Args:
            question_id: The ID of the research question to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._service.delete_research_question(question_id)
    
    def list_research_questions(
        self, parent_question_id: Optional[str] = ...
    ) -> List[ResearchQuestion]:
        """
        List research questions with optional filtering.
        
        Args:
            parent_question_id: Filter by parent question ID. If not provided, returns all questions.
                                If set to None, returns only top-level questions (with no parent).
            
        Returns:
            List[ResearchQuestion]: List of research questions matching the criteria
        """
        return self._service.list_research_questions(parent_question_id=parent_question_id)
    
    # Reference association methods
    
    def register_reference(self, reference_id: str, reference_obj):
        """
        Register a reference object for lookup by ID.
        
        Args:
            reference_id: The ID of the reference
            reference_obj: The reference object
        """
        self._references[reference_id] = reference_obj
    
    def add_reference_to_task(self, task_id: str, reference_or_id: Union[str, Any]) -> bool:
        """
        Associate a bibliographic reference with a task.
        
        Args:
            task_id: The ID of the task
            reference_or_id: The reference object or ID of the reference
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        # Handle both reference objects and strs
        reference_id = reference_or_id
        if hasattr(reference_or_id, 'id') and not isinstance(reference_or_id, str):
            reference_id = reference_or_id.id
            # Register the reference object for lookup
            self._references[reference_id] = reference_or_id
        
        return self._service.add_reference_to_task(task_id, reference_id)
    
    def remove_reference_from_task(self, task_id: str, reference_id: str) -> bool:
        """
        Remove association between a bibliographic reference and a task.
        
        Args:
            task_id: The ID of the task
            reference_id: The ID of the bibliographic reference
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        return self._service.remove_reference_from_task(task_id, reference_id)
    
    def get_task_references(self, task_id: str) -> List:
        """
        Get all bibliographic references associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List: List of reference objects associated with the task
            
        Raises:
            ValueError: If task doesn't exist
        """
        reference_ids = self._service.get_task_references(task_id)
        references = [self._references.get(ref_id) for ref_id in reference_ids if ref_id in self._references]
        # Add references property for compatibility with integration tests
        task = self._service.get_task(task_id)
        if task:
            task.references = references
        return references
    
    # Dataset association methods
    
    def register_dataset(self, dataset_id: str, dataset_obj):
        """
        Register a dataset object for lookup by ID.
        
        Args:
            dataset_id: The ID of the dataset
            dataset_obj: The dataset object
        """
        self._datasets[dataset_id] = dataset_obj
    
    def add_dataset_to_task(self, task_id: str, dataset_or_id: Union[str, Any]) -> bool:
        """
        Associate a dataset with a task.
        
        Args:
            task_id: The ID of the task
            dataset_or_id: The dataset object or ID of the dataset
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        # Handle both dataset objects and strs
        dataset_id = dataset_or_id
        if hasattr(dataset_or_id, 'id') and not isinstance(dataset_or_id, str):
            dataset_id = dataset_or_id.id
        
        result = self._service.add_dataset_to_task(task_id, dataset_id)
        
        # Register the dataset object for lookup if it's an object
        if hasattr(dataset_or_id, 'id') and not isinstance(dataset_or_id, str) and dataset_or_id.id not in self._datasets:
            self._datasets[dataset_or_id.id] = dataset_or_id
            
        return result
    
    def remove_dataset_from_task(self, task_id: str, dataset_id: str) -> bool:
        """
        Remove association between a dataset and a task.
        
        Args:
            task_id: The ID of the task
            dataset_id: The ID of the dataset
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        return self._service.remove_dataset_from_task(task_id, dataset_id)
    
    def get_task_datasets(self, task_id: str) -> List:
        """
        Get all datasets associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List: List of dataset objects associated with the task
            
        Raises:
            ValueError: If task doesn't exist
        """
        dataset_ids = self._service.get_task_datasets(task_id)
        datasets = [self._datasets.get(ds_id) for ds_id in dataset_ids if ds_id in self._datasets] 
        # Add datasets property for compatibility with integration tests
        task = self._service.get_task(task_id)
        if task:
            task.datasets = datasets
        return datasets
    
    # Environment association methods
    
    def register_environment(self, environment_id: str, environment_obj):
        """
        Register an environment object for lookup by ID.
        
        Args:
            environment_id: The ID of the environment
            environment_obj: The environment object
        """
        self._environments[environment_id] = environment_obj
    
    def add_environment_to_task(self, task_id: str, environment_or_id: Union[str, Any]) -> bool:
        """
        Associate an environment with a task.
        
        Args:
            task_id: The ID of the task
            environment_or_id: The environment object or ID of the environment
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        # Handle both environment objects and strs
        environment_id = environment_or_id
        if hasattr(environment_or_id, 'id') and not isinstance(environment_or_id, str):
            environment_id = environment_or_id.id
            # Register the environment object for lookup
            self._environments[environment_id] = environment_or_id
            
        return self._service.add_environment_to_task(task_id, environment_id)
    
    def remove_environment_from_task(self, task_id: str, environment_id: str) -> bool:
        """
        Remove association between an environment and a task.
        
        Args:
            task_id: The ID of the task
            environment_id: The ID of the environment
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        return self._service.remove_environment_from_task(task_id, environment_id)
    
    def get_task_environments(self, task_id: str) -> List:
        """
        Get all environments associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List: List of environment objects associated with the task
            
        Raises:
            ValueError: If task doesn't exist
        """
        environment_ids = self._service.get_task_environments(task_id)
        environments = [self._environments.get(env_id) for env_id in environment_ids if env_id in self._environments]
        # Add environments property for compatibility with integration tests
        task = self._service.get_task(task_id)
        if task:
            task.environments = environments
        return environments
    
    # Experiment association methods
    
    def register_experiment(self, experiment_id: str, experiment_obj):
        """
        Register an experiment object for lookup by ID.
        
        Args:
            experiment_id: The ID of the experiment
            experiment_obj: The experiment object
        """
        self._experiments[experiment_id] = experiment_obj
    
    def add_experiment_to_task(self, task_id: str, experiment_or_id: Union[str, Any]) -> bool:
        """
        Associate an experiment with a task.
        
        Args:
            task_id: The ID of the task
            experiment_or_id: The experiment object or ID of the experiment
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        # Handle both experiment objects and strs
        experiment_id = experiment_or_id
        if hasattr(experiment_or_id, 'id') and not isinstance(experiment_or_id, str):
            experiment_id = experiment_or_id.id
            # Register the experiment object for lookup
            self._experiments[experiment_id] = experiment_or_id
            
        return self._service.add_experiment_to_task(task_id, experiment_id)
    
    def remove_experiment_from_task(self, task_id: str, experiment_id: str) -> bool:
        """
        Remove association between an experiment and a task.
        
        Args:
            task_id: The ID of the task
            experiment_id: The ID of the experiment
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If task doesn't exist
        """
        return self._service.remove_experiment_from_task(task_id, experiment_id)
    
    def get_task_experiments(self, task_id: str) -> List:
        """
        Get all experiments associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List: List of experiment objects associated with the task
            
        Raises:
            ValueError: If task doesn't exist
        """
        experiment_ids = self._service.get_task_experiments(task_id)
        experiments = [self._experiments.get(exp_id) for exp_id in experiment_ids if exp_id in self._experiments]
        # Add experiments property for compatibility with integration tests
        task = self._service.get_task(task_id)
        if task:
            task.experiments = experiments
        return experiments