from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Union

from common.core import InMemoryStorage
from .models import (
    EnvironmentSnapshot, 
    PackageInfo, 
    ComputeResource, 
    TaskEnvironmentLink
)


class EnvironmentStorageInterface(ABC):
    """Abstract interface for environment snapshot storage implementations."""
    
    @abstractmethod
    def create_environment(self, environment: EnvironmentSnapshot) -> str:
        """
        Create a new environment snapshot.
        
        Args:
            environment: The environment to create
            
        Returns:
            str: The ID of the created environment
        """
        pass
    
    @abstractmethod
    def get_environment(self, environment_id: str) -> Optional[EnvironmentSnapshot]:
        """
        Retrieve an environment by ID.
        
        Args:
            environment_id: The ID of the environment to retrieve
            
        Returns:
            Optional[EnvironmentSnapshot]: The environment if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_environment(self, environment: EnvironmentSnapshot) -> bool:
        """
        Update an existing environment.
        
        Args:
            environment: The environment with updated fields
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_environment(self, environment_id: str) -> bool:
        """
        Delete an environment by ID.
        
        Args:
            environment_id: The ID of the environment to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_environments(
        self, type: Optional[str] = None, tags: Optional[Set[str]] = None
    ) -> List[EnvironmentSnapshot]:
        """
        List environments with optional filtering.
        
        Args:
            type: Filter by environment type
            tags: Filter by tags (environments must have all specified tags)
            
        Returns:
            List[EnvironmentSnapshot]: List of environments matching the criteria
        """
        pass
    
    @abstractmethod
    def create_task_environment_link(self, link: TaskEnvironmentLink) -> str:
        """
        Create a link between a task and an environment snapshot.
        
        Args:
            link: The link to create
            
        Returns:
            str: The ID of the created link
        """
        pass
    
    @abstractmethod
    def get_task_environment_link(self, link_id: str) -> Optional[TaskEnvironmentLink]:
        """
        Retrieve a task-environment link by ID.
        
        Args:
            link_id: The ID of the link to retrieve
            
        Returns:
            Optional[TaskEnvironmentLink]: The link if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update_task_environment_link(self, link: TaskEnvironmentLink) -> bool:
        """
        Update an existing task-environment link.
        
        Args:
            link: The link with updated fields
            
        Returns:
            bool: True if update successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_task_environment_link(self, link_id: str) -> bool:
        """
        Delete a task-environment link by ID.
        
        Args:
            link_id: The ID of the link to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_environments_by_task(self, task_id: str) -> List[EnvironmentSnapshot]:
        """
        Get all environment snapshots associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[EnvironmentSnapshot]: List of associated environments
        """
        pass
    
    @abstractmethod
    def get_tasks_by_environment(self, environment_id: str) -> List[str]:
        """
        Get all task IDs associated with an environment.
        
        Args:
            environment_id: The ID of the environment
            
        Returns:
            List[str]: List of associated task IDs
        """
        pass
        
    @abstractmethod
    def get_links_by_task(self, task_id: str) -> List[TaskEnvironmentLink]:
        """
        Get all environment links for a specific task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[TaskEnvironmentLink]: List of task-environment links for this task
        """
        pass


class InMemoryEnvironmentStorage(EnvironmentStorageInterface):
    """In-memory implementation of environment snapshot storage using common.core."""
    
    def __init__(self):
        self._environment_storage = InMemoryStorage(EnvironmentSnapshot)
        self._link_storage = InMemoryStorage(TaskEnvironmentLink)
    
    def create_environment(self, environment: EnvironmentSnapshot) -> str:
        return self._environment_storage.create(environment)
    
    def get_environment(self, environment_id: str) -> Optional[EnvironmentSnapshot]:
        return self._environment_storage.get(environment_id)
    
    def update_environment(self, environment: EnvironmentSnapshot) -> bool:
        updated = self._environment_storage.update(environment)
        return updated is not None
    
    def delete_environment(self, environment_id: str) -> bool:
        if not self._environment_storage.exists(environment_id):
            return False
        
        # Delete any links that reference this environment
        links = self._link_storage.list({"environment_id": environment_id})
        for link in links:
            self.delete_task_environment_link(link.id)
        
        # Delete the environment
        return self._environment_storage.delete(environment_id)
    
    def list_environments(
        self, type: Optional[str] = None, tags: Optional[Set[str]] = None
    ) -> List[EnvironmentSnapshot]:
        filters = {}
        if type:
            filters["type"] = type
            
        environments = self._environment_storage.list(filters)
        
        # Apply tag filtering manually since it's set-based
        if tags:
            environments = [
                env for env in environments
                if all(tag in env.tags for tag in tags)
            ]
        
        return environments
    
    def create_task_environment_link(self, link: TaskEnvironmentLink) -> str:
        return self._link_storage.create(link)
    
    def get_task_environment_link(self, link_id: str) -> Optional[TaskEnvironmentLink]:
        return self._link_storage.get(link_id)
    
    def update_task_environment_link(self, link: TaskEnvironmentLink) -> bool:
        updated = self._link_storage.update(link)
        return updated is not None
    
    def delete_task_environment_link(self, link_id: str) -> bool:
        return self._link_storage.delete(link_id)
    
    def get_environments_by_task(self, task_id: str) -> List[EnvironmentSnapshot]:
        # Get all links for this task
        links = self._link_storage.list({"task_id": task_id})
        
        # Get all associated environments
        environments = []
        for link in links:
            environment = self.get_environment(link.environment_id)
            if environment:
                environments.append(environment)
        
        return environments
    
    def get_tasks_by_environment(self, environment_id: str) -> List[str]:
        # Get all links for this environment
        links = self._link_storage.list({"environment_id": environment_id})
        
        # Return task IDs
        return [link.task_id for link in links]
        
    def get_links_by_task(self, task_id: str) -> List[TaskEnvironmentLink]:
        # Get all links for this task
        return self._link_storage.list({"task_id": task_id})