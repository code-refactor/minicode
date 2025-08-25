import time
from uuid import uuid4

import pytest

from researchtrack.environment.models import (
    ComputeResourceType,
    EnvironmentType,
    PackageInfo,
    PackageManagerType,
)
from researchtrack.environment.service import EnvironmentService
from researchtrack.environment.storage import InMemoryEnvironmentStorage


class TestEnvironmentPerformance:
    def setup_method(self):
        """Set up a fresh service instance for each test."""
        self.storage = InMemoryEnvironmentStorage()
        self.service = EnvironmentService(self.storage)
    
    def test_environment_operations_performance(self):
        """Test performance of basic environment operations."""
        # Create an environment
        start_time = time.time()
        env_id = self.service.create_environment_snapshot(
            name="Performance Test Environment",
            environment_type=EnvironmentType.CONDA,
            description="Environment for performance testing",
        )
        create_time = time.time() - start_time
        
        # Get the environment
        start_time = time.time()
        self.service.get_environment(env_id)
        get_time = time.time() - start_time
        
        # Update the environment
        start_time = time.time()
        self.service.update_environment(
            environment_id=env_id,
            name="Updated Environment Name",
            description="Updated description",
        )
        update_time = time.time() - start_time
        
        # Delete the environment
        start_time = time.time()
        self.service.delete_environment(env_id)
        delete_time = time.time() - start_time
        
        # Assert performance metrics (50ms limit per operation)
        assert create_time < 0.05, f"Create operation took {create_time:.6f}s, exceeding 50ms limit"
        assert get_time < 0.05, f"Get operation took {get_time:.6f}s, exceeding 50ms limit"
        assert update_time < 0.05, f"Update operation took {update_time:.6f}s, exceeding 50ms limit"
        assert delete_time < 0.05, f"Delete operation took {delete_time:.6f}s, exceeding 50ms limit"
    
    def test_environment_snapshot_generation_time(self):
        """Test that environment snapshots can be generated in under 5 seconds."""
        # Generate a comprehensive environment snapshot with all features
        start_time = time.time()
        
        env_id = self.service.capture_current_environment(
            name="Comprehensive Snapshot",
            description="Complete environment snapshot with all details",
            environment_type=EnvironmentType.LOCAL,
            include_packages=True,
            include_env_vars=True,
            tags={"performance", "test"},
            custom_metadata={"purpose": "performance testing"},
        )
        
        generation_time = time.time() - start_time
        
        # Assert that snapshot generation took less than 5 seconds
        assert generation_time < 5.0, f"Environment snapshot generation took {generation_time:.6f}s, exceeding 5s limit"
        
        # Verify the snapshot was created
        env = self.service.get_environment(env_id)
        assert env is not None
        assert env.name == "Comprehensive Snapshot"
    
    def test_large_environment_catalog_performance(self):
        """Test performance with many environments and complex queries."""
        env_ids = []
        
        # Generate a variety of environment types
        env_types = list(EnvironmentType)
        
        # Create 100 environments with varying characteristics
        start_time = time.time()
        for i in range(100):
            env_type = env_types[i % len(env_types)]
            
            # Create a set of tags
            tags = {"env" + str(i % 10)}
            if i % 2 == 0:
                tags.add("even")
            if i % 3 == 0:
                tags.add("divisible-by-3")
            if i % 5 == 0:
                tags.add("divisible-by-5")
            
            # Create some packages
            packages = []
            for j in range(5):  # 5 packages per environment
                packages.append(
                    PackageInfo(
                        name=f"package-{j}",
                        version=f"1.{i}.{j}",
                        manager=PackageManagerType.PIP,
                    )
                )
            
            env_id = self.service.create_environment_snapshot(
                name=f"Environment {i}",
                environment_type=env_type,
                description=f"Description for environment {i}",
                python_version=f"3.{i % 3 + 8}.{i % 10}",  # Vary Python versions
                packages=packages,
                tags=tags,
                custom_metadata={"index": i},
            )
            
            env_ids.append(env_id)
        
        creation_time = time.time() - start_time
        avg_creation_time = creation_time / 100
        
        # Test different query patterns
        
        # Filter by type
        start_time = time.time()
        conda_envs = self.service.list_environments(type=EnvironmentType.CONDA)
        filter_by_type_time = time.time() - start_time
        
        # Filter by tags
        start_time = time.time()
        tag_envs = self.service.list_environments(tags={"even", "divisible-by-5"})
        filter_by_tags_time = time.time() - start_time
        
        # Get and manipulate a random environment
        random_env_id = env_ids[42]
        
        start_time = time.time()
        env = self.service.get_environment(random_env_id)
        self.service.add_environment_tag(random_env_id, "new-tag")
        get_and_update_time = time.time() - start_time
        
        # Compare two environments
        start_time = time.time()
        self.service.compare_environments(env_ids[10], env_ids[20])
        compare_time = time.time() - start_time
        
        # Assert performance metrics
        assert avg_creation_time < 0.05, f"Average environment creation took {avg_creation_time:.6f}s, exceeding 50ms limit"
        assert filter_by_type_time < 0.2, f"Type filtering took {filter_by_type_time:.6f}s, exceeding reasonable limit"
        assert filter_by_tags_time < 0.2, f"Tag filtering took {filter_by_tags_time:.6f}s, exceeding reasonable limit"
        assert get_and_update_time < 0.1, f"Get and update took {get_and_update_time:.6f}s, exceeding reasonable limit"
        assert compare_time < 0.5, f"Environment comparison took {compare_time:.6f}s, exceeding reasonable limit"
    
    def test_complex_environment_performance(self):
        """Test performance with a very complex environment configuration."""
        # Create a complex environment with many components
        packages = []
        for i in range(500):  # 500 packages
            packages.append(
                PackageInfo(
                    name=f"package-{i}",
                    version=f"1.0.{i}",
                    manager=PackageManagerType.PIP if i % 2 == 0 else PackageManagerType.CONDA,
                )
            )
        
        # Create many environment variables
        env_vars = {}
        for i in range(200):  # 200 environment variables
            env_vars[f"ENV_VAR_{i}"] = f"value_{i}"
        
        # Create configuration files
        config_files = {}
        for i in range(100):  # 100 config files
            config_files[f"/path/to/config_{i}.yaml"] = f"config: {i}\nsettings:\n  value: {i}"
        
        start_time = time.time()
        env_id = self.service.create_environment_snapshot(
            name="Complex Environment",
            environment_type=EnvironmentType.CONDA,
            description="A very complex environment with many components",
            python_version="3.10.4",
            packages=packages,
            environment_variables=env_vars,
            config_files=config_files,
            tags={"complex", "test", "performance"},
        )
        create_time = time.time() - start_time
        
        # Test retrieving this complex environment
        start_time = time.time()
        env = self.service.get_environment(env_id)
        get_time = time.time() - start_time
        
        # Assert performance metrics
        assert create_time < 0.5, f"Complex environment creation took {create_time:.6f}s, exceeding reasonable limit"
        assert get_time < 0.05, f"Complex environment retrieval took {get_time:.6f}s, exceeding 50ms limit"
        
        # Verify the complex environment was created correctly
        assert len(env.packages) == 500
        assert len(env.environment_variables) == 200
        assert len(env.config_files) == 100
    
    def test_task_environment_link_performance(self):
        """Test performance with many task-environment links."""
        # Create environments and task IDs
        env_ids = []
        task_ids = []
        
        for i in range(10):
            env_id = self.service.create_environment_snapshot(
                name=f"Environment {i}",
                environment_type=EnvironmentType.LOCAL,
            )
            env_ids.append(env_id)
        
        for i in range(100):
            task_ids.append(uuid4())
        
        # Create links (each task uses 1-3 environments)
        link_ids = []
        
        start_time = time.time()
        for i, task_id in enumerate(task_ids):
            # Determine how many environments for this task
            num_envs = 1 + (i % 3)  # 1-3 environments
            
            for j in range(num_envs):
                # Pick an environment (ensure distribution across all environments)
                env_index = (i + j) % len(env_ids)
                env_id = env_ids[env_index]
                
                # Create the link
                link_id = self.service.link_task_to_environment(
                    task_id=task_id,
                    environment_id=env_id,
                    description=f"Link {i}-{j}",
                )
                link_ids.append(link_id)
        
        link_creation_time = time.time() - start_time
        avg_link_creation_time = link_creation_time / len(link_ids)
        
        # Test querying links
        query_times = []
        for i in range(20):  # Test with 20 random tasks
            task_id = task_ids[i * 5]
            
            start_time = time.time()
            environments = self.service.get_environments_by_task(task_id)
            query_times.append(time.time() - start_time)
            
            start_time = time.time()
            links = self.service.get_links_by_task(task_id)
            query_times.append(time.time() - start_time)
        
        for i in range(5):  # Test with 5 random environments
            env_id = env_ids[i]
            
            start_time = time.time()
            tasks = self.service.get_tasks_by_environment(env_id)
            query_times.append(time.time() - start_time)
        
        avg_query_time = sum(query_times) / len(query_times)
        
        # Assert performance metrics
        assert avg_link_creation_time < 0.05, f"Average link creation took {avg_link_creation_time:.6f}s, exceeding 50ms limit"
        assert avg_query_time < 0.05, f"Average link query took {avg_query_time:.6f}s, exceeding 50ms limit"