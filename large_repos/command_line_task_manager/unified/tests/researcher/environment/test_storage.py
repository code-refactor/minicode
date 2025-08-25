from uuid import uuid4

import pytest

from researchtrack.environment.models import (
    EnvironmentSnapshot,
    EnvironmentType,
    PackageInfo,
    PackageManagerType,
    TaskEnvironmentLink,
)
from researchtrack.environment.storage import InMemoryEnvironmentStorage


class TestInMemoryEnvironmentStorage:
    def setup_method(self):
        """Set up a fresh storage instance for each test."""
        self.storage = InMemoryEnvironmentStorage()
        
        # Create some test data to use in multiple tests
        self.environment1 = EnvironmentSnapshot(
            name="Python Development Environment",
            description="Local Python development setup",
            type=EnvironmentType.VENV,
            python_version="3.10.4",
            tags={"python", "development"},
            packages=[
                PackageInfo(
                    name="numpy",
                    version="1.24.3",
                    manager=PackageManagerType.PIP,
                ),
                PackageInfo(
                    name="pandas",
                    version="2.0.0",
                    manager=PackageManagerType.PIP,
                ),
            ],
        )
        
        self.environment2 = EnvironmentSnapshot(
            name="Deep Learning Environment",
            description="GPU-accelerated environment for ML",
            type=EnvironmentType.CONDA,
            python_version="3.9.16",
            tags={"python", "deep-learning", "gpu"},
            packages=[
                PackageInfo(
                    name="tensorflow",
                    version="2.12.0",
                    manager=PackageManagerType.CONDA,
                ),
                PackageInfo(
                    name="torch",
                    version="2.0.0",
                    manager=PackageManagerType.CONDA,
                ),
            ],
        )
        
        self.task_id1 = uuid4()
        self.task_id2 = uuid4()
    
    def test_create_and_get_environment(self):
        # Test creating and retrieving an environment
        env_id = self.storage.create_environment(self.environment1)
        
        retrieved_env = self.storage.get_environment(env_id)
        
        assert retrieved_env is not None
        assert retrieved_env.id == env_id
        assert retrieved_env.name == "Python Development Environment"
        assert retrieved_env.type == EnvironmentType.VENV
        assert retrieved_env.python_version == "3.10.4"
        assert len(retrieved_env.packages) == 2
    
    def test_update_environment(self):
        # Test updating an environment
        env_id = self.storage.create_environment(self.environment1)
        
        # Update the environment
        self.environment1.name = "Updated Environment Name"
        self.environment1.description = "Updated description"
        
        update_result = self.storage.update_environment(self.environment1)
        retrieved_env = self.storage.get_environment(env_id)
        
        assert update_result is True
        assert retrieved_env.name == "Updated Environment Name"
        assert retrieved_env.description == "Updated description"
    
    def test_update_nonexistent_environment(self):
        # Test updating an environment that doesn't exist
        nonexistent_env = EnvironmentSnapshot(
            id=uuid4(),
            name="Nonexistent Environment",
            type=EnvironmentType.LOCAL,
        )
        
        update_result = self.storage.update_environment(nonexistent_env)
        assert update_result is False
    
    def test_delete_environment(self):
        # Test deleting an environment
        env_id = self.storage.create_environment(self.environment1)
        
        # Create a link to this environment
        link = TaskEnvironmentLink(
            task_id=self.task_id1,
            environment_id=env_id,
        )
        link_id = self.storage.create_task_environment_link(link)
        
        # Delete the environment
        delete_result = self.storage.delete_environment(env_id)
        
        assert delete_result is True
        assert self.storage.get_environment(env_id) is None
        
        # Verify that the link was also deleted
        assert self.storage.get_task_environment_link(link_id) is None
    
    def test_delete_nonexistent_environment(self):
        # Test deleting an environment that doesn't exist
        delete_result = self.storage.delete_environment(uuid4())
        assert delete_result is False
    
    def test_list_environments_empty(self):
        # Test listing environments when storage is empty
        environments = self.storage.list_environments()
        assert len(environments) == 0
    
    def test_list_environments_with_filters(self):
        # Test listing environments with various filters
        self.storage.create_environment(self.environment1)
        self.storage.create_environment(self.environment2)
        
        # Filter by type
        venv_environments = self.storage.list_environments(type=EnvironmentType.VENV)
        assert len(venv_environments) == 1
        assert venv_environments[0].name == "Python Development Environment"
        
        conda_environments = self.storage.list_environments(type=EnvironmentType.CONDA)
        assert len(conda_environments) == 1
        assert conda_environments[0].name == "Deep Learning Environment"
        
        # Filter by tags
        python_environments = self.storage.list_environments(tags={"python"})
        assert len(python_environments) == 2
        
        gpu_environments = self.storage.list_environments(tags={"gpu"})
        assert len(gpu_environments) == 1
        assert gpu_environments[0].name == "Deep Learning Environment"
        
        # Multiple tags
        python_gpu_environments = self.storage.list_environments(tags={"python", "gpu"})
        assert len(python_gpu_environments) == 1
        assert python_gpu_environments[0].name == "Deep Learning Environment"
        
        # No matches
        no_environments = self.storage.list_environments(tags={"nonexistent"})
        assert len(no_environments) == 0
    
    def test_task_environment_link_operations(self):
        # Test task-environment link CRUD operations
        env_id1 = self.storage.create_environment(self.environment1)
        env_id2 = self.storage.create_environment(self.environment2)
        
        # Create links
        link1 = TaskEnvironmentLink(
            task_id=self.task_id1,
            environment_id=env_id1,
            description="Link 1 description",
        )
        
        link2 = TaskEnvironmentLink(
            task_id=self.task_id1,
            environment_id=env_id2,
            description="Link 2 description",
        )
        
        link3 = TaskEnvironmentLink(
            task_id=self.task_id2,
            environment_id=env_id1,
            description="Link 3 description",
        )
        
        link_id1 = self.storage.create_task_environment_link(link1)
        link_id2 = self.storage.create_task_environment_link(link2)
        link_id3 = self.storage.create_task_environment_link(link3)
        
        # Test retrieving link
        retrieved_link = self.storage.get_task_environment_link(link_id1)
        
        assert retrieved_link is not None
        assert retrieved_link.id == link_id1
        assert retrieved_link.task_id == self.task_id1
        assert retrieved_link.environment_id == env_id1
        assert retrieved_link.description == "Link 1 description"
        
        # Test updating link
        link1.description = "Updated description"
        update_result = self.storage.update_task_environment_link(link1)
        updated_link = self.storage.get_task_environment_link(link_id1)
        
        assert update_result is True
        assert updated_link.description == "Updated description"
        
        # Test querying links
        task1_environments = self.storage.get_environments_by_task(self.task_id1)
        assert len(task1_environments) == 2
        assert {env.id for env in task1_environments} == {env_id1, env_id2}
        
        task1_links = self.storage.get_links_by_task(self.task_id1)
        assert len(task1_links) == 2
        assert {link.id for link in task1_links} == {link_id1, link_id2}
        
        env1_tasks = self.storage.get_tasks_by_environment(env_id1)
        assert len(env1_tasks) == 2
        assert set(env1_tasks) == {self.task_id1, self.task_id2}
        
        # Test deleting link
        delete_result = self.storage.delete_task_environment_link(link_id1)
        
        assert delete_result is True
        assert self.storage.get_task_environment_link(link_id1) is None
        
        # Verify the updated queries
        updated_task1_environments = self.storage.get_environments_by_task(self.task_id1)
        assert len(updated_task1_environments) == 1
        assert updated_task1_environments[0].id == env_id2
        
        updated_env1_tasks = self.storage.get_tasks_by_environment(env_id1)
        assert len(updated_env1_tasks) == 1
        assert updated_env1_tasks[0] == self.task_id2