from uuid import uuid4

import pytest

from researchtrack.environment.models import (
    ComputeResource,
    ComputeResourceType,
    EnvironmentType,
    OperatingSystemType,
    PackageInfo,
    PackageManagerType,
)
from researchtrack.environment.service import EnvironmentService
from researchtrack.environment.storage import InMemoryEnvironmentStorage


class TestEnvironmentService:
    def setup_method(self):
        """Set up a fresh service instance for each test."""
        self.storage = InMemoryEnvironmentStorage()
        self.service = EnvironmentService(self.storage)
        
        # Create some task IDs to use in tests
        self.task_id1 = uuid4()
        self.task_id2 = uuid4()
    
    def test_create_environment_snapshot(self):
        # Test creating a basic environment snapshot
        env_id = self.service.create_environment_snapshot(
            name="Test Environment",
            environment_type=EnvironmentType.CONDA,
            description="Test environment description",
            python_version="3.10.4",
            os_type=OperatingSystemType.LINUX,
            os_version="Ubuntu 22.04",
            architecture="x86_64",
            kernel_version="5.15.0-58-generic",
            tags={"test", "conda"},
            custom_metadata={"purpose": "testing"},
        )
        
        env = self.service.get_environment(env_id)
        
        assert env is not None
        assert env.name == "Test Environment"
        assert env.type == EnvironmentType.CONDA
        assert env.description == "Test environment description"
        assert env.python_version == "3.10.4"
        assert env.os_type == OperatingSystemType.LINUX
        assert env.os_version == "Ubuntu 22.04"
        assert env.architecture == "x86_64"
        assert env.kernel_version == "5.15.0-58-generic"
        assert env.tags == {"test", "conda"}
        assert env.custom_metadata["purpose"] == "testing"
    
    def test_create_environment_with_packages_and_resources(self):
        # Test creating an environment with packages and compute resources
        compute_resources = [
            ComputeResource(
                type=ComputeResourceType.CPU,
                count=8,
                model="Intel Xeon",
                memory_gb=32.0,
            ),
            ComputeResource(
                type=ComputeResourceType.GPU,
                count=2,
                model="NVIDIA A100",
                memory_gb=40.0,
            ),
        ]
        
        packages = [
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
            PackageInfo(
                name="tensorflow",
                version="2.12.0",
                manager=PackageManagerType.PIP,
            ),
        ]
        
        env_vars = {
            "PYTHONPATH": "/home/user/project",
            "TF_FORCE_GPU_ALLOW_GROWTH": "true",
            "CUDA_VISIBLE_DEVICES": "0,1",
        }
        
        config_files = {
            "/home/user/.keras/keras.json": '{"backend": "tensorflow", "image_data_format": "channels_last"}',
            "/home/user/project/config.yaml": "batch_size: 32\nlearning_rate: 0.001",
        }
        
        env_id = self.service.create_environment_snapshot(
            name="ML Environment",
            environment_type=EnvironmentType.CONDA,
            description="Machine learning environment",
            python_version="3.9.16",
            compute_resources=compute_resources,
            environment_variables=env_vars,
            packages=packages,
            config_files=config_files,
            container_image="tensorflow/tensorflow",
            container_tag="2.12.0-gpu",
            cloud_provider="AWS",
            cloud_region="us-west-2",
            instance_type="p3.8xlarge",
            tags={"ml", "gpu", "tensorflow"},
        )
        
        env = self.service.get_environment(env_id)
        
        assert env is not None
        assert env.name == "ML Environment"
        assert len(env.compute_resources) == 2
        assert env.compute_resources[0].type == ComputeResourceType.CPU
        assert env.compute_resources[0].count == 8
        assert env.compute_resources[1].type == ComputeResourceType.GPU
        assert env.compute_resources[1].count == 2
        assert len(env.packages) == 3
        assert {p.name for p in env.packages} == {"numpy", "pandas", "tensorflow"}
        assert len(env.environment_variables) == 3
        assert env.environment_variables["PYTHONPATH"] == "/home/user/project"
        assert len(env.config_files) == 2
        assert "/home/user/.keras/keras.json" in env.config_files
        assert env.container_image == "tensorflow/tensorflow"
        assert env.container_tag == "2.12.0-gpu"
        assert env.cloud_provider == "AWS"
        assert env.cloud_region == "us-west-2"
        assert env.instance_type == "p3.8xlarge"
        assert env.tags == {"ml", "gpu", "tensorflow"}
    
    def test_capture_current_environment(self):
        # Test capturing the current environment
        # This is a simplified test since we can't directly test the actual environment detection
        env_id = self.service.capture_current_environment(
            name="Current Environment",
            description="Captured from the current Python environment",
            environment_type=EnvironmentType.LOCAL,
            include_packages=True,
            include_env_vars=True,
            tags={"current", "test"},
            custom_metadata={"purpose": "testing"},
        )
        
        env = self.service.get_environment(env_id)
        
        assert env is not None
        assert env.name == "Current Environment"
        assert env.description == "Captured from the current Python environment"
        assert env.type == EnvironmentType.LOCAL
        assert env.python_version is not None  # Should be captured from the actual environment
        assert env.os_type is not None  # Should be captured from the actual environment
        assert env.os_version is not None  # Should be captured from the actual environment
        assert env.architecture is not None  # Should be captured from the actual environment
        assert len(env.packages) > 0  # Should have captured some packages
        assert len(env.environment_variables) > 0  # Should have captured some env vars
        assert len(env.compute_resources) > 0  # Should have captured compute resources
        assert env.tags == {"current", "test"}
        assert env.custom_metadata["purpose"] == "testing"
    
    def test_update_environment(self):
        # Test updating an environment
        env_id = self.service.create_environment_snapshot(
            name="Original Name",
            environment_type=EnvironmentType.LOCAL,
            description="Original description",
        )
        
        # Update the environment
        update_result = self.service.update_environment(
            environment_id=env_id,
            name="Updated Name",
            description="Updated description",
            container_image="new/image",
            container_tag="latest",
            cloud_provider="GCP",
            cloud_region="us-central1",
            instance_type="n1-standard-8",
            git_commit="abcdef1234567890",
            git_repository="https://github.com/user/repo",
            git_branch="main",
        )
        
        updated_env = self.service.get_environment(env_id)
        
        assert update_result is True
        assert updated_env.name == "Updated Name"
        assert updated_env.description == "Updated description"
        assert updated_env.container_image == "new/image"
        assert updated_env.container_tag == "latest"
        assert updated_env.cloud_provider == "GCP"
        assert updated_env.cloud_region == "us-central1"
        assert updated_env.instance_type == "n1-standard-8"
        assert updated_env.git_commit == "abcdef1234567890"
        assert updated_env.git_repository == "https://github.com/user/repo"
        assert updated_env.git_branch == "main"
    
    def test_update_nonexistent_environment(self):
        # Test updating a non-existent environment
        with pytest.raises(ValueError, match="Environment snapshot .* does not exist"):
            self.service.update_environment(
                environment_id=uuid4(),
                name="Updated Name",
            )
    
    def test_delete_environment(self):
        # Test deleting an environment
        env_id = self.service.create_environment_snapshot(
            name="Environment to Delete",
            environment_type=EnvironmentType.LOCAL,
        )
        
        # Verify environment exists
        assert self.service.get_environment(env_id) is not None
        
        # Delete environment
        delete_result = self.service.delete_environment(env_id)
        
        assert delete_result is True
        assert self.service.get_environment(env_id) is None
    
    def test_list_environments(self):
        # Test listing environments with filters
        
        # Create environments with different attributes
        self.service.create_environment_snapshot(
            name="Conda Environment",
            environment_type=EnvironmentType.CONDA,
            tags={"python", "conda"},
        )
        
        self.service.create_environment_snapshot(
            name="Docker Environment",
            environment_type=EnvironmentType.DOCKER,
            tags={"python", "docker"},
        )
        
        self.service.create_environment_snapshot(
            name="Another Conda Environment",
            environment_type=EnvironmentType.CONDA,
            tags={"python", "conda", "ml"},
        )
        
        # Get all environments
        all_environments = self.service.list_environments()
        assert len(all_environments) == 3
        
        # Filter by type
        conda_environments = self.service.list_environments(type=EnvironmentType.CONDA)
        assert len(conda_environments) == 2
        assert {env.name for env in conda_environments} == {"Conda Environment", "Another Conda Environment"}
        
        docker_environments = self.service.list_environments(type=EnvironmentType.DOCKER)
        assert len(docker_environments) == 1
        assert docker_environments[0].name == "Docker Environment"
        
        # Filter by tags
        python_environments = self.service.list_environments(tags={"python"})
        assert len(python_environments) == 3
        
        conda_tag_environments = self.service.list_environments(tags={"conda"})
        assert len(conda_tag_environments) == 2
        assert {env.name for env in conda_tag_environments} == {"Conda Environment", "Another Conda Environment"}
        
        ml_environments = self.service.list_environments(tags={"ml"})
        assert len(ml_environments) == 1
        assert ml_environments[0].name == "Another Conda Environment"
        
        # Combined filters
        conda_ml_environments = self.service.list_environments(
            type=EnvironmentType.CONDA, tags={"ml"}
        )
        assert len(conda_ml_environments) == 1
        assert conda_ml_environments[0].name == "Another Conda Environment"
    
    def test_environment_tag_operations(self):
        # Test adding and removing tags
        env_id = self.service.create_environment_snapshot(
            name="Tag Test Environment",
            environment_type=EnvironmentType.LOCAL,
            tags={"initial"},
        )
        
        # Add tags
        self.service.add_environment_tag(env_id, "tag1")
        self.service.add_environment_tag(env_id, "tag2")
        
        env = self.service.get_environment(env_id)
        assert env.tags == {"initial", "tag1", "tag2"}
        
        # Remove tag
        result = self.service.remove_environment_tag(env_id, "tag1")
        
        assert result is True
        env = self.service.get_environment(env_id)
        assert env.tags == {"initial", "tag2"}
        
        # Try to remove non-existent tag
        non_existent_result = self.service.remove_environment_tag(env_id, "nonexistent")
        
        assert non_existent_result is False
        env = self.service.get_environment(env_id)
        assert env.tags == {"initial", "tag2"}
    
    def test_package_operations(self):
        # Test adding and removing packages
        env_id = self.service.create_environment_snapshot(
            name="Package Test Environment",
            environment_type=EnvironmentType.VENV,
            packages=[
                PackageInfo(
                    name="initial-package",
                    version="1.0.0",
                    manager=PackageManagerType.PIP,
                ),
            ],
        )
        
        # Add packages
        numpy_package = PackageInfo(
            name="numpy",
            version="1.24.3",
            manager=PackageManagerType.PIP,
        )
        
        pandas_package = PackageInfo(
            name="pandas",
            version="2.0.0",
            manager=PackageManagerType.PIP,
        )
        
        self.service.add_package(env_id, numpy_package)
        self.service.add_package(env_id, pandas_package)
        
        env = self.service.get_environment(env_id)
        assert len(env.packages) == 3
        assert {p.name for p in env.packages} == {"initial-package", "numpy", "pandas"}
        
        # Remove package
        result = self.service.remove_package(env_id, "numpy", PackageManagerType.PIP)
        
        assert result is True
        env = self.service.get_environment(env_id)
        assert len(env.packages) == 2
        assert {p.name for p in env.packages} == {"initial-package", "pandas"}
        
        # Try to remove non-existent package
        non_existent_result = self.service.remove_package(env_id, "nonexistent", PackageManagerType.PIP)
        
        assert non_existent_result is False
        env = self.service.get_environment(env_id)
        assert len(env.packages) == 2
    
    def test_compute_resource_operations(self):
        # Test adding and removing compute resources
        env_id = self.service.create_environment_snapshot(
            name="Compute Resource Test Environment",
            environment_type=EnvironmentType.LOCAL,
            compute_resources=[
                ComputeResource(
                    type=ComputeResourceType.CPU,
                    count=4,
                    model="Initial CPU",
                ),
            ],
        )
        
        # Add compute resources
        gpu_resource = ComputeResource(
            type=ComputeResourceType.GPU,
            count=1,
            model="NVIDIA RTX 3080",
            memory_gb=10.0,
        )
        
        self.service.add_compute_resource(env_id, gpu_resource)
        
        env = self.service.get_environment(env_id)
        assert len(env.compute_resources) == 2
        assert env.compute_resources[0].type == ComputeResourceType.CPU
        assert env.compute_resources[1].type == ComputeResourceType.GPU
        assert env.compute_resources[1].model == "NVIDIA RTX 3080"
        
        # Remove compute resource
        result = self.service.remove_compute_resource(env_id, 0)
        
        assert result is True
        env = self.service.get_environment(env_id)
        assert len(env.compute_resources) == 1
        assert env.compute_resources[0].type == ComputeResourceType.GPU
        
        # Try to remove with invalid index
        invalid_index_result = self.service.remove_compute_resource(env_id, 5)
        
        assert invalid_index_result is False
        env = self.service.get_environment(env_id)
        assert len(env.compute_resources) == 1
    
    def test_environment_variable_operations(self):
        # Test adding and removing environment variables
        env_id = self.service.create_environment_snapshot(
            name="Environment Variable Test",
            environment_type=EnvironmentType.LOCAL,
            environment_variables={
                "INITIAL_VAR": "initial_value",
            },
        )
        
        # Add environment variables
        self.service.add_environment_variable(env_id, "PATH", "/usr/local/bin:/usr/bin")
        self.service.add_environment_variable(env_id, "PYTHONPATH", "/home/user/project")
        
        env = self.service.get_environment(env_id)
        assert len(env.environment_variables) == 3
        assert env.environment_variables["INITIAL_VAR"] == "initial_value"
        assert env.environment_variables["PATH"] == "/usr/local/bin:/usr/bin"
        assert env.environment_variables["PYTHONPATH"] == "/home/user/project"
        
        # Update existing variable
        self.service.add_environment_variable(env_id, "PATH", "/new/path")
        
        env = self.service.get_environment(env_id)
        assert env.environment_variables["PATH"] == "/new/path"
        
        # Remove variable
        result = self.service.remove_environment_variable(env_id, "PYTHONPATH")
        
        assert result is True
        env = self.service.get_environment(env_id)
        assert len(env.environment_variables) == 2
        assert "PYTHONPATH" not in env.environment_variables
        
        # Try to remove non-existent variable
        non_existent_result = self.service.remove_environment_variable(env_id, "NONEXISTENT")
        
        assert non_existent_result is False
        env = self.service.get_environment(env_id)
        assert len(env.environment_variables) == 2
    
    def test_config_file_operations(self):
        # Test adding and removing configuration files
        env_id = self.service.create_environment_snapshot(
            name="Config File Test",
            environment_type=EnvironmentType.LOCAL,
            config_files={
                "/initial/file.conf": "initial content",
            },
        )
        
        # Add config files
        self.service.add_config_file(
            env_id,
            "/path/to/config.yaml",
            "param1: value1\nparam2: value2",
        )
        self.service.add_config_file(
            env_id,
            "/path/to/settings.json",
            '{"setting1": "value1", "setting2": "value2"}',
        )
        
        env = self.service.get_environment(env_id)
        assert len(env.config_files) == 3
        assert env.config_files["/initial/file.conf"] == "initial content"
        assert env.config_files["/path/to/config.yaml"] == "param1: value1\nparam2: value2"
        assert env.config_files["/path/to/settings.json"] == '{"setting1": "value1", "setting2": "value2"}'
        
        # Update existing file
        self.service.add_config_file(
            env_id,
            "/path/to/config.yaml",
            "updated: content",
        )
        
        env = self.service.get_environment(env_id)
        assert env.config_files["/path/to/config.yaml"] == "updated: content"
        
        # Remove file
        result = self.service.remove_config_file(env_id, "/path/to/settings.json")
        
        assert result is True
        env = self.service.get_environment(env_id)
        assert len(env.config_files) == 2
        assert "/path/to/settings.json" not in env.config_files
        
        # Try to remove non-existent file
        non_existent_result = self.service.remove_config_file(env_id, "/nonexistent/file")
        
        assert non_existent_result is False
        env = self.service.get_environment(env_id)
        assert len(env.config_files) == 2
    
    def test_custom_metadata_operations(self):
        # Test updating and removing custom metadata
        env_id = self.service.create_environment_snapshot(
            name="Metadata Test",
            environment_type=EnvironmentType.LOCAL,
            custom_metadata={
                "initial_key": "initial_value",
            },
        )
        
        # Update metadata
        self.service.update_custom_metadata(env_id, "string_key", "string_value")
        self.service.update_custom_metadata(env_id, "int_key", 42)
        self.service.update_custom_metadata(env_id, "float_key", 3.14)
        self.service.update_custom_metadata(env_id, "bool_key", True)
        self.service.update_custom_metadata(env_id, "list_key", [1, 2, 3])
        self.service.update_custom_metadata(env_id, "dict_key", {"a": 1, "b": 2})
        
        env = self.service.get_environment(env_id)
        assert len(env.custom_metadata) == 7
        assert env.custom_metadata["initial_key"] == "initial_value"
        assert env.custom_metadata["string_key"] == "string_value"
        assert env.custom_metadata["int_key"] == 42
        assert env.custom_metadata["float_key"] == 3.14
        assert env.custom_metadata["bool_key"] is True
        assert env.custom_metadata["list_key"] == [1, 2, 3]
        assert env.custom_metadata["dict_key"] == {"a": 1, "b": 2}
        
        # Update existing metadata
        self.service.update_custom_metadata(env_id, "int_key", 100)
        
        env = self.service.get_environment(env_id)
        assert env.custom_metadata["int_key"] == 100
        
        # Remove metadata
        result = self.service.remove_custom_metadata(env_id, "list_key")
        
        assert result is True
        env = self.service.get_environment(env_id)
        assert len(env.custom_metadata) == 6
        assert "list_key" not in env.custom_metadata
        
        # Try to remove non-existent metadata
        non_existent_result = self.service.remove_custom_metadata(env_id, "nonexistent")
        
        assert non_existent_result is False
        env = self.service.get_environment(env_id)
        assert len(env.custom_metadata) == 6
    
    def test_compare_environments(self):
        # Test comparing two environments
        env_id1 = self.service.create_environment_snapshot(
            name="Environment 1",
            environment_type=EnvironmentType.CONDA,
            python_version="3.9.12",
            os_type=OperatingSystemType.LINUX,
            os_version="Ubuntu 20.04",
            packages=[
                PackageInfo(
                    name="numpy",
                    version="1.22.3",
                    manager=PackageManagerType.CONDA,
                ),
                PackageInfo(
                    name="pandas",
                    version="1.4.2",
                    manager=PackageManagerType.CONDA,
                ),
                PackageInfo(
                    name="matplotlib",
                    version="3.5.1",
                    manager=PackageManagerType.CONDA,
                ),
            ],
            environment_variables={
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": "/home/user/project",
                "LANG": "en_US.UTF-8",
            },
            config_files={
                "/home/user/.condarc": "channels:\n  - conda-forge\n  - defaults",
                "/home/user/project/config.yaml": "param1: value1\nparam2: value2",
            },
        )
        
        env_id2 = self.service.create_environment_snapshot(
            name="Environment 2",
            environment_type=EnvironmentType.CONDA,
            python_version="3.10.4",
            os_type=OperatingSystemType.LINUX,
            os_version="Ubuntu 22.04",
            packages=[
                PackageInfo(
                    name="numpy",
                    version="1.23.0",
                    manager=PackageManagerType.CONDA,
                ),
                PackageInfo(
                    name="pandas",
                    version="1.4.2",  # Same version
                    manager=PackageManagerType.CONDA,
                ),
                PackageInfo(
                    name="scikit-learn",  # Different package instead of matplotlib
                    version="1.1.1",
                    manager=PackageManagerType.CONDA,
                ),
            ],
            environment_variables={
                "PATH": "/usr/local/bin:/usr/bin:/bin",  # Different value
                "PYTHONPATH": "/home/user/project",  # Same value
                "CUDA_VISIBLE_DEVICES": "0",  # New variable
                # LANG is missing
            },
            config_files={
                "/home/user/.condarc": "channels:\n  - conda-forge\n  - defaults",  # Same content
                "/home/user/project/config.yaml": "param1: new_value\nparam2: value2",  # Different content
                "/home/user/project/new_config.yaml": "new: config",  # New file
            },
        )
        
        differences = self.service.compare_environments(env_id1, env_id2)
        
        # Check system differences
        assert "system" in differences
        assert "python_version" in differences["system"]
        assert differences["system"]["python_version"]["env1"] == "3.9.12"
        assert differences["system"]["python_version"]["env2"] == "3.10.4"
        assert "os_version" in differences["system"]
        assert differences["system"]["os_version"]["env1"] == "Ubuntu 20.04"
        assert differences["system"]["os_version"]["env2"] == "Ubuntu 22.04"
        
        # Check package differences
        assert "packages" in differences
        assert "only_in_env1" in differences["packages"]
        assert any(p["name"] == "matplotlib" for p in differences["packages"]["only_in_env1"])
        assert "only_in_env2" in differences["packages"]
        assert any(p["name"] == "scikit-learn" for p in differences["packages"]["only_in_env2"])
        assert "version_different" in differences["packages"]
        assert any(p["name"] == "numpy" for p in differences["packages"]["version_different"])
        
        # Check environment variable differences
        assert "environment_variables" in differences
        assert "only_in_env1" in differences["environment_variables"]
        assert "LANG" in differences["environment_variables"]["only_in_env1"]
        assert "only_in_env2" in differences["environment_variables"]
        assert "CUDA_VISIBLE_DEVICES" in differences["environment_variables"]["only_in_env2"]
        assert "value_different" in differences["environment_variables"]
        assert "PATH" in differences["environment_variables"]["value_different"]
        
        # Check config file differences
        assert "config_files" in differences
        assert "only_in_env2" in differences["config_files"]
        assert "/home/user/project/new_config.yaml" in differences["config_files"]["only_in_env2"]
        assert "content_different" in differences["config_files"]
        assert "/home/user/project/config.yaml" in differences["config_files"]["content_different"]
    
    def test_link_task_to_environment(self):
        # Test linking a task to an environment
        env_id = self.service.create_environment_snapshot(
            name="Environment for Task",
            environment_type=EnvironmentType.LOCAL,
        )
        
        # Create link
        link_id = self.service.link_task_to_environment(
            task_id=self.task_id1,
            environment_id=env_id,
            description="Environment used for task execution",
            actual_execution_time=123.45,
        )
        
        link = self.service.get_task_environment_link(link_id)
        
        assert link is not None
        assert link.task_id == self.task_id1
        assert link.environment_id == env_id
        assert link.description == "Environment used for task execution"
        assert link.actual_execution_time == 123.45
    
    def test_link_to_nonexistent_environment(self):
        # Test linking to a non-existent environment
        with pytest.raises(ValueError, match="Environment snapshot .* does not exist"):
            self.service.link_task_to_environment(
                task_id=self.task_id1,
                environment_id=uuid4(),
            )
    
    def test_task_environment_link_operations(self):
        # Test various link operations
        env_id1 = self.service.create_environment_snapshot(
            name="Environment 1",
            environment_type=EnvironmentType.LOCAL,
        )
        
        env_id2 = self.service.create_environment_snapshot(
            name="Environment 2",
            environment_type=EnvironmentType.DOCKER,
        )
        
        # Create links for different tasks
        link_id1 = self.service.link_task_to_environment(
            task_id=self.task_id1,
            environment_id=env_id1,
            description="Link 1",
        )
        
        link_id2 = self.service.link_task_to_environment(
            task_id=self.task_id2,
            environment_id=env_id1,
            description="Link 2",
        )
        
        link_id3 = self.service.link_task_to_environment(
            task_id=self.task_id1,
            environment_id=env_id2,
            description="Link 3",
        )
        
        # Update a link
        update_result = self.service.update_task_environment_link(
            link_id=link_id1,
            description="Updated description",
            actual_execution_time=456.78,
        )
        
        updated_link = self.service.get_task_environment_link(link_id1)
        
        assert update_result is True
        assert updated_link.description == "Updated description"
        assert updated_link.actual_execution_time == 456.78
        
        # Add notes
        note_result = self.service.add_note_to_link(link_id1, "Test note")
        
        assert note_result is True
        link_with_note = self.service.get_task_environment_link(link_id1)
        assert len(link_with_note.notes) == 1
        assert link_with_note.notes[0] == "Test note"
        
        # Query operations
        task1_environments = self.service.get_environments_by_task(self.task_id1)
        assert len(task1_environments) == 2
        assert {env.id for env in task1_environments} == {env_id1, env_id2}
        
        task1_links = self.service.get_links_by_task(self.task_id1)
        assert len(task1_links) == 2
        assert {link.id for link in task1_links} == {link_id1, link_id3}
        
        env1_tasks = self.service.get_tasks_by_environment(env_id1)
        assert len(env1_tasks) == 2
        assert set(env1_tasks) == {self.task_id1, self.task_id2}
        
        # Delete a link
        delete_result = self.service.delete_task_environment_link(link_id1)
        
        assert delete_result is True
        assert self.service.get_task_environment_link(link_id1) is None
        
        # Verify the updated queries
        updated_task1_environments = self.service.get_environments_by_task(self.task_id1)
        assert len(updated_task1_environments) == 1
        assert updated_task1_environments[0].id == env_id2
        
        updated_env1_tasks = self.service.get_tasks_by_environment(env_id1)
        assert len(updated_env1_tasks) == 1
        assert updated_env1_tasks[0] == self.task_id2