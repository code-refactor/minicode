from datetime import datetime
from uuid import UUID, uuid4

import pytest

from researchtrack.environment.models import (
    ComputeResource,
    ComputeResourceType,
    EnvironmentSnapshot,
    EnvironmentType,
    OperatingSystemType,
    PackageInfo,
    PackageManagerType,
    TaskEnvironmentLink,
)


class TestPackageInfo:
    def test_create_package_info(self):
        # Test basic creation
        package = PackageInfo(
            name="numpy",
            version="1.24.3",
            manager=PackageManagerType.PIP,
            channel="conda-forge",
            extras=["test"],
            custom_metadata={"homepage": "https://numpy.org/"},
        )
        
        assert package.name == "numpy"
        assert package.version == "1.24.3"
        assert package.manager == PackageManagerType.PIP
        assert package.channel == "conda-forge"
        assert package.extras == ["test"]
        assert package.custom_metadata == {"homepage": "https://numpy.org/"}
        
        # Test with minimal fields
        minimal_package = PackageInfo(
            name="pandas",
            version="2.0.0",
            manager=PackageManagerType.CONDA,
        )
        
        assert minimal_package.name == "pandas"
        assert minimal_package.version == "2.0.0"
        assert minimal_package.manager == PackageManagerType.CONDA
        assert minimal_package.channel is None
        assert minimal_package.extras is None
        assert minimal_package.custom_metadata == {}


class TestComputeResource:
    def test_create_compute_resource(self):
        # Test basic creation
        cpu_resource = ComputeResource(
            type=ComputeResourceType.CPU,
            count=8,
            model="Intel Xeon E5-2686 v4",
            memory_gb=32.0,
            custom_metadata={"clock_speed": "2.3 GHz"},
        )
        
        assert cpu_resource.type == ComputeResourceType.CPU
        assert cpu_resource.count == 8
        assert cpu_resource.model == "Intel Xeon E5-2686 v4"
        assert cpu_resource.memory_gb == 32.0
        assert cpu_resource.custom_metadata == {"clock_speed": "2.3 GHz"}
        
        # Test with minimal fields
        minimal_resource = ComputeResource(
            type=ComputeResourceType.GPU,
            count=2,
        )
        
        assert minimal_resource.type == ComputeResourceType.GPU
        assert minimal_resource.count == 2
        assert minimal_resource.model is None
        assert minimal_resource.memory_gb is None
        assert minimal_resource.custom_metadata == {}


class TestEnvironmentSnapshot:
    def test_create_environment_snapshot(self):
        # Test basic creation
        cpu_resource = ComputeResource(
            type=ComputeResourceType.CPU,
            count=4,
            model="Intel Core i7-9700K",
            memory_gb=16.0,
        )
        
        gpu_resource = ComputeResource(
            type=ComputeResourceType.GPU,
            count=1,
            model="NVIDIA RTX 3080",
            memory_gb=10.0,
        )
        
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
        
        snapshot = EnvironmentSnapshot(
            name="Deep Learning Environment",
            description="Environment for training neural networks",
            type=EnvironmentType.CONDA,
            python_version="3.10.4",
            os_type=OperatingSystemType.LINUX,
            os_version="Ubuntu 22.04",
            architecture="x86_64",
            kernel_version="5.15.0-58-generic",
            compute_resources=[cpu_resource, gpu_resource],
            environment_variables={
                "PYTHONPATH": "/home/user/projects",
                "CUDA_VISIBLE_DEVICES": "0",
            },
            packages=[numpy_package, pandas_package],
            config_files={
                "/home/user/.condarc": "channels:\n  - conda-forge\n  - defaults",
                "/home/user/project/config.yaml": "batch_size: 32\nlearning_rate: 0.001",
            },
            container_image="pytorch/pytorch",
            container_tag="2.0.0-cuda11.7-cudnn8-runtime",
            container_digest="sha256:abcdef1234567890",
            cloud_provider="AWS",
            cloud_region="us-west-2",
            instance_type="p3.2xlarge",
            git_commit="a1b2c3d4e5f6",
            git_repository="https://github.com/user/project",
            git_branch="main",
            tags={"deep-learning", "pytorch", "research"},
            custom_metadata={
                "experiment_id": "exp-001",
                "framework_version": "2.0.0",
                "startup_time_seconds": 45.2,
            },
        )
        
        assert isinstance(snapshot.id, UUID)
        assert snapshot.name == "Deep Learning Environment"
        assert snapshot.description == "Environment for training neural networks"
        assert snapshot.type == EnvironmentType.CONDA
        assert snapshot.python_version == "3.10.4"
        assert snapshot.os_type == OperatingSystemType.LINUX
        assert snapshot.os_version == "Ubuntu 22.04"
        assert snapshot.architecture == "x86_64"
        assert snapshot.kernel_version == "5.15.0-58-generic"
        assert len(snapshot.compute_resources) == 2
        assert snapshot.compute_resources[0].type == ComputeResourceType.CPU
        assert snapshot.compute_resources[1].type == ComputeResourceType.GPU
        assert len(snapshot.environment_variables) == 2
        assert snapshot.environment_variables["PYTHONPATH"] == "/home/user/projects"
        assert len(snapshot.packages) == 2
        assert snapshot.packages[0].name == "numpy"
        assert snapshot.packages[1].name == "pandas"
        assert len(snapshot.config_files) == 2
        assert "/home/user/.condarc" in snapshot.config_files
        assert snapshot.container_image == "pytorch/pytorch"
        assert snapshot.container_tag == "2.0.0-cuda11.7-cudnn8-runtime"
        assert snapshot.container_digest == "sha256:abcdef1234567890"
        assert snapshot.cloud_provider == "AWS"
        assert snapshot.cloud_region == "us-west-2"
        assert snapshot.instance_type == "p3.2xlarge"
        assert snapshot.git_commit == "a1b2c3d4e5f6"
        assert snapshot.git_repository == "https://github.com/user/project"
        assert snapshot.git_branch == "main"
        assert snapshot.tags == {"deep-learning", "pytorch", "research"}
        assert snapshot.custom_metadata["experiment_id"] == "exp-001"
        assert snapshot.custom_metadata["framework_version"] == "2.0.0"
        assert snapshot.custom_metadata["startup_time_seconds"] == 45.2
        assert isinstance(snapshot.created_at, datetime)
        assert isinstance(snapshot.updated_at, datetime)
    
    def test_update_environment_snapshot(self):
        # Test updating fields
        snapshot = EnvironmentSnapshot(
            name="Original Name",
            type=EnvironmentType.LOCAL,
            description="Original description",
        )
        
        original_updated_at = snapshot.updated_at
        
        snapshot.update(
            name="Updated Name",
            description="Updated description",
            python_version="3.11.0",
            container_image="new-image",
            container_tag="latest",
        )
        
        assert snapshot.name == "Updated Name"
        assert snapshot.description == "Updated description"
        assert snapshot.python_version == "3.11.0"
        assert snapshot.container_image == "new-image"
        assert snapshot.container_tag == "latest"
        assert snapshot.updated_at > original_updated_at
    
    def test_package_management(self):
        # Test adding and removing packages
        snapshot = EnvironmentSnapshot(
            name="Package Test Environment",
            type=EnvironmentType.VENV,
        )
        
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
        
        original_updated_at = snapshot.updated_at
        
        snapshot.add_package(numpy_package)
        snapshot.add_package(pandas_package)
        
        assert len(snapshot.packages) == 2
        assert snapshot.packages[0].name == "numpy"
        assert snapshot.packages[1].name == "pandas"
        assert snapshot.updated_at > original_updated_at
        
        # Remove package
        result = snapshot.remove_package("numpy", PackageManagerType.PIP)
        
        assert result is True
        assert len(snapshot.packages) == 1
        assert snapshot.packages[0].name == "pandas"
        
        # Try to remove non-existent package
        non_existent_result = snapshot.remove_package("scikit-learn", PackageManagerType.PIP)
        
        assert non_existent_result is False
        
        # Try to remove package with wrong manager
        wrong_manager_result = snapshot.remove_package("pandas", PackageManagerType.CONDA)
        
        assert wrong_manager_result is False
        assert len(snapshot.packages) == 1  # pandas is still there
    
    def test_compute_resource_management(self):
        # Test adding and removing compute resources
        snapshot = EnvironmentSnapshot(
            name="Compute Resource Test Environment",
            type=EnvironmentType.DOCKER,
        )
        
        cpu_resource = ComputeResource(
            type=ComputeResourceType.CPU,
            count=4,
        )
        
        gpu_resource = ComputeResource(
            type=ComputeResourceType.GPU,
            count=1,
        )
        
        original_updated_at = snapshot.updated_at
        
        snapshot.add_compute_resource(cpu_resource)
        snapshot.add_compute_resource(gpu_resource)
        
        assert len(snapshot.compute_resources) == 2
        assert snapshot.compute_resources[0].type == ComputeResourceType.CPU
        assert snapshot.compute_resources[1].type == ComputeResourceType.GPU
        assert snapshot.updated_at > original_updated_at
        
        # Remove resource by index
        result = snapshot.remove_compute_resource(0)
        
        assert result is True
        assert len(snapshot.compute_resources) == 1
        assert snapshot.compute_resources[0].type == ComputeResourceType.GPU
        
        # Try to remove with invalid index
        invalid_index_result = snapshot.remove_compute_resource(5)
        
        assert invalid_index_result is False
        assert len(snapshot.compute_resources) == 1
    
    def test_environment_variable_management(self):
        # Test adding and removing environment variables
        snapshot = EnvironmentSnapshot(
            name="Environment Variable Test",
            type=EnvironmentType.LOCAL,
        )
        
        original_updated_at = snapshot.updated_at
        
        snapshot.add_environment_variable("PATH", "/usr/local/bin:/usr/bin")
        snapshot.add_environment_variable("PYTHONPATH", "/home/user/project")
        
        assert len(snapshot.environment_variables) == 2
        assert snapshot.environment_variables["PATH"] == "/usr/local/bin:/usr/bin"
        assert snapshot.environment_variables["PYTHONPATH"] == "/home/user/project"
        assert snapshot.updated_at > original_updated_at
        
        # Update existing variable
        snapshot.add_environment_variable("PATH", "/new/path")
        
        assert snapshot.environment_variables["PATH"] == "/new/path"
        
        # Remove variable
        result = snapshot.remove_environment_variable("PYTHONPATH")
        
        assert result is True
        assert len(snapshot.environment_variables) == 1
        assert "PYTHONPATH" not in snapshot.environment_variables
        
        # Try to remove non-existent variable
        non_existent_result = snapshot.remove_environment_variable("NONEXISTENT")
        
        assert non_existent_result is False
    
    def test_config_file_management(self):
        # Test adding and removing configuration files
        snapshot = EnvironmentSnapshot(
            name="Config File Test",
            type=EnvironmentType.LOCAL,
        )
        
        original_updated_at = snapshot.updated_at
        
        snapshot.add_config_file(
            "/path/to/config.yaml",
            "param1: value1\nparam2: value2",
        )
        snapshot.add_config_file(
            "/path/to/settings.json",
            '{"setting1": "value1", "setting2": "value2"}',
        )
        
        assert len(snapshot.config_files) == 2
        assert snapshot.config_files["/path/to/config.yaml"] == "param1: value1\nparam2: value2"
        assert snapshot.config_files["/path/to/settings.json"] == '{"setting1": "value1", "setting2": "value2"}'
        assert snapshot.updated_at > original_updated_at
        
        # Update existing file
        snapshot.add_config_file(
            "/path/to/config.yaml",
            "updated: content",
        )
        
        assert snapshot.config_files["/path/to/config.yaml"] == "updated: content"
        
        # Remove file
        result = snapshot.remove_config_file("/path/to/settings.json")
        
        assert result is True
        assert len(snapshot.config_files) == 1
        assert "/path/to/settings.json" not in snapshot.config_files
        
        # Try to remove non-existent file
        non_existent_result = snapshot.remove_config_file("/nonexistent/file")
        
        assert non_existent_result is False
    
    def test_tag_management(self):
        # Test adding and removing tags
        snapshot = EnvironmentSnapshot(
            name="Tag Test",
            type=EnvironmentType.LOCAL,
        )
        
        original_updated_at = snapshot.updated_at
        
        snapshot.add_tag("tag1")
        snapshot.add_tag("tag2")
        snapshot.add_tag("tag3")
        
        assert snapshot.tags == {"tag1", "tag2", "tag3"}
        assert snapshot.updated_at > original_updated_at
        
        # Adding duplicate tag should not change the set
        previous_updated_at = snapshot.updated_at
        snapshot.add_tag("tag1")
        assert snapshot.tags == {"tag1", "tag2", "tag3"}
        assert snapshot.updated_at > previous_updated_at
        
        # Remove tag
        result = snapshot.remove_tag("tag2")
        
        assert result is True
        assert snapshot.tags == {"tag1", "tag3"}
        
        # Try to remove non-existent tag
        non_existent_result = snapshot.remove_tag("nonexistent")
        
        assert non_existent_result is False
    
    def test_custom_metadata_management(self):
        # Test custom metadata operations
        snapshot = EnvironmentSnapshot(
            name="Metadata Test",
            type=EnvironmentType.LOCAL,
        )
        
        original_updated_at = snapshot.updated_at
        
        snapshot.update_custom_metadata("string_key", "string_value")
        snapshot.update_custom_metadata("int_key", 42)
        snapshot.update_custom_metadata("float_key", 3.14)
        snapshot.update_custom_metadata("bool_key", True)
        snapshot.update_custom_metadata("list_key", [1, 2, 3])
        snapshot.update_custom_metadata("dict_key", {"a": 1, "b": 2})
        
        assert len(snapshot.custom_metadata) == 6
        assert snapshot.custom_metadata["string_key"] == "string_value"
        assert snapshot.custom_metadata["int_key"] == 42
        assert snapshot.custom_metadata["float_key"] == 3.14
        assert snapshot.custom_metadata["bool_key"] is True
        assert snapshot.custom_metadata["list_key"] == [1, 2, 3]
        assert snapshot.custom_metadata["dict_key"] == {"a": 1, "b": 2}
        assert snapshot.updated_at > original_updated_at
        
        # Update existing metadata
        snapshot.update_custom_metadata("int_key", 100)
        
        assert snapshot.custom_metadata["int_key"] == 100
        
        # Remove metadata
        result = snapshot.remove_custom_metadata("list_key")
        
        assert result is True
        assert len(snapshot.custom_metadata) == 5
        assert "list_key" not in snapshot.custom_metadata
        
        # Try to remove non-existent metadata
        non_existent_result = snapshot.remove_custom_metadata("nonexistent")
        
        assert non_existent_result is False


class TestTaskEnvironmentLink:
    def test_create_task_environment_link(self):
        # Test basic creation
        task_id = uuid4()
        environment_id = uuid4()
        
        link = TaskEnvironmentLink(
            task_id=task_id,
            environment_id=environment_id,
            description="Environment used for task execution",
            actual_execution_time=123.45,
        )
        
        assert isinstance(link.id, UUID)
        assert link.task_id == task_id
        assert link.environment_id == environment_id
        assert link.description == "Environment used for task execution"
        assert link.actual_execution_time == 123.45
        assert len(link.notes) == 0
        assert isinstance(link.created_at, datetime)
        assert isinstance(link.updated_at, datetime)
    
    def test_update_link(self):
        # Test updating fields
        task_id = uuid4()
        environment_id = uuid4()
        
        link = TaskEnvironmentLink(
            task_id=task_id,
            environment_id=environment_id,
            description="Original description",
            actual_execution_time=100.0,
        )
        
        original_updated_at = link.updated_at
        
        link.update(
            description="Updated description",
            actual_execution_time=150.5,
        )
        
        assert link.description == "Updated description"
        assert link.actual_execution_time == 150.5
        assert link.updated_at > original_updated_at
    
    def test_add_note(self):
        # Test adding notes
        task_id = uuid4()
        environment_id = uuid4()
        
        link = TaskEnvironmentLink(
            task_id=task_id,
            environment_id=environment_id,
        )
        
        original_updated_at = link.updated_at
        
        link.add_note("First note about the environment")
        link.add_note("Second note with additional details")
        
        assert len(link.notes) == 2
        assert link.notes[0] == "First note about the environment"
        assert link.notes[1] == "Second note with additional details"
        assert link.updated_at > original_updated_at