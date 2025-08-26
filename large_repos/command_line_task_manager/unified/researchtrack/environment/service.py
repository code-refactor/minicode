import os
import platform
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Set, Union, Any
try:
    from importlib.metadata import distributions
except ImportError:
    # Fallback for Python < 3.8
    try:
        from importlib_metadata import distributions
    except ImportError:
        distributions = None

from common.core import BaseService, InMemoryStorage
from .models import (
    EnvironmentSnapshot, 
    EnvironmentType, 
    PackageInfo, 
    PackageManagerType,
    ComputeResource,
    ComputeResourceType,
    OperatingSystemType,
    TaskEnvironmentLink
)
from .storage import EnvironmentStorageInterface, InMemoryEnvironmentStorage


class EnvironmentService(BaseService[EnvironmentSnapshot]):
    """Service for managing computational environment snapshots."""
    
    def __init__(self, storage: Optional[EnvironmentStorageInterface] = None):
        """
        Initialize the environment service.
        
        Args:
            storage: The storage implementation to use. If None, uses InMemoryEnvironmentStorage.
        """
        # Initialize with environment storage for base service
        env_storage = InMemoryStorage(EnvironmentSnapshot) if storage is None else None
        super().__init__(env_storage) if env_storage else None
        
        # Use provided storage or default
        self._storage = storage or InMemoryEnvironmentStorage()
    
    # Environment snapshot operations
    
    def create_snapshot(
        self,
        name: str,
        description: Optional[str] = None,
        type: Union[EnvironmentType, str] = EnvironmentType.LOCAL,
        python_version: Optional[str] = None,
        os_type: Optional[Union[OperatingSystemType, str]] = None,
        os_version: Optional[str] = None,
        architecture: Optional[str] = None,
        kernel_version: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        packages: Optional[List[PackageInfo]] = None,
        compute_resources: Optional[List[ComputeResource]] = None,
        config_files: Optional[Dict[str, str]] = None,
        container_image: Optional[str] = None,
        container_tag: Optional[str] = None,
        container_digest: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        cloud_region: Optional[str] = None,
        instance_type: Optional[str] = None,
        git_commit: Optional[str] = None,
        git_repository: Optional[str] = None,
        git_branch: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        custom_metadata: Optional[Dict[str, Union[str, int, float, bool, list, dict]]] = None,
    ) -> EnvironmentSnapshot:
        """
        Create a new environment snapshot.
        
        Args:
            name: Snapshot name
            description: Snapshot description
            type: Environment type
            python_version: Python version
            os_type: Operating system type
            os_version: Operating system version
            architecture: CPU architecture
            kernel_version: Kernel version
            environment_variables: Environment variables dictionary
            packages: List of package information
            compute_resources: List of compute resources
            config_files: Dictionary of configuration files (path -> content)
            container_image: Container image name
            container_tag: Container tag
            container_digest: Container digest
            cloud_provider: Cloud provider
            cloud_region: Cloud region
            instance_type: Instance type
            git_commit: Git commit hash
            git_repository: Git repository URL
            git_branch: Git branch name
            tags: Tags for categorization
            
        Returns:
            EnvironmentSnapshot: The created snapshot
        """
        # Convert string enums to enum values if needed
        if isinstance(type, str):
            type = EnvironmentType(type)
        
        if isinstance(os_type, str) and os_type:
            os_type = OperatingSystemType(os_type)
        
        # Create the snapshot
        snapshot = EnvironmentSnapshot(
            name=name,
            description=description,
            type=type,
            python_version=python_version,
            os_type=os_type,
            os_version=os_version,
            architecture=architecture,
            kernel_version=kernel_version,
            environment_variables=environment_variables or {},
            packages=packages or [],
            compute_resources=compute_resources or [],
            config_files=config_files or {},
            container_image=container_image,
            container_tag=container_tag,
            container_digest=container_digest,
            cloud_provider=cloud_provider,
            cloud_region=cloud_region,
            instance_type=instance_type,
            git_commit=git_commit,
            git_repository=git_repository,
            git_branch=git_branch,
            tags=tags or set(),
            custom_metadata=custom_metadata or {},
        )
        
        # Save the snapshot
        self._storage.create_environment(snapshot)
        
        return snapshot
    
    def get_snapshot(self, snapshot_id: str) -> Optional[EnvironmentSnapshot]:
        """
        Retrieve a snapshot by ID.
        
        Args:
            snapshot_id: The ID of the snapshot to retrieve
            
        Returns:
            Optional[EnvironmentSnapshot]: The snapshot if found, None otherwise
        """
        return self._storage.get_environment(snapshot_id)
        
    def get_environment(self, environment_id: str) -> Optional[EnvironmentSnapshot]:
        """
        Retrieve an environment snapshot by ID.
        
        Args:
            environment_id: The ID of the environment snapshot to retrieve
            
        Returns:
            Optional[EnvironmentSnapshot]: The environment snapshot if found, None otherwise
        """
        return self.get_snapshot(environment_id)
    
    def update_snapshot(
        self,
        snapshot_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        python_version: Optional[str] = None,
        os_type: Optional[Union[OperatingSystemType, str]] = None,
        os_version: Optional[str] = None,
        architecture: Optional[str] = None,
        kernel_version: Optional[str] = None,
        container_image: Optional[str] = None,
        container_tag: Optional[str] = None,
        container_digest: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        cloud_region: Optional[str] = None,
        instance_type: Optional[str] = None,
        git_commit: Optional[str] = None,
        git_repository: Optional[str] = None,
        git_branch: Optional[str] = None,
    ) -> bool:
        """
        Update an existing environment snapshot.
        
        Args:
            snapshot_id: The ID of the snapshot to update
            name: New snapshot name
            description: New snapshot description
            python_version: New Python version
            os_type: New operating system type
            os_version: New operating system version
            architecture: New CPU architecture
            kernel_version: New kernel version
            container_image: New container image name
            container_tag: New container tag
            container_digest: New container digest
            cloud_provider: New cloud provider
            cloud_region: New cloud region
            instance_type: New instance type
            git_commit: New Git commit hash
            git_repository: New Git repository URL
            git_branch: New Git branch name
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If snapshot doesn't exist
        """
        snapshot = self._storage.get_environment(snapshot_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {snapshot_id} does not exist")
        
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if python_version is not None:
            update_data["python_version"] = python_version
        if os_type is not None:
            if isinstance(os_type, str):
                os_type = OperatingSystemType(os_type)
            update_data["os_type"] = os_type
        if os_version is not None:
            update_data["os_version"] = os_version
        if architecture is not None:
            update_data["architecture"] = architecture
        if kernel_version is not None:
            update_data["kernel_version"] = kernel_version
        if container_image is not None:
            update_data["container_image"] = container_image
        if container_tag is not None:
            update_data["container_tag"] = container_tag
        if container_digest is not None:
            update_data["container_digest"] = container_digest
        if cloud_provider is not None:
            update_data["cloud_provider"] = cloud_provider
        if cloud_region is not None:
            update_data["cloud_region"] = cloud_region
        if instance_type is not None:
            update_data["instance_type"] = instance_type
        if git_commit is not None:
            update_data["git_commit"] = git_commit
        if git_repository is not None:
            update_data["git_repository"] = git_repository
        if git_branch is not None:
            update_data["git_branch"] = git_branch
        
        snapshot.update(**update_data)
        return self._storage.update_environment(snapshot)
        
    def update_environment(
        self,
        environment_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        python_version: Optional[str] = None,
        os_type: Optional[Union[OperatingSystemType, str]] = None,
        os_version: Optional[str] = None,
        architecture: Optional[str] = None,
        kernel_version: Optional[str] = None,
        container_image: Optional[str] = None,
        container_tag: Optional[str] = None,
        container_digest: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        cloud_region: Optional[str] = None,
        instance_type: Optional[str] = None,
        git_commit: Optional[str] = None,
        git_repository: Optional[str] = None,
        git_branch: Optional[str] = None,
    ) -> bool:
        """
        Update an existing environment snapshot.
        
        Args:
            environment_id: The ID of the environment snapshot to update
            name: New snapshot name
            description: New snapshot description
            python_version: New Python version
            os_type: New operating system type
            os_version: New operating system version
            architecture: New CPU architecture
            kernel_version: New kernel version
            container_image: New container image name
            container_tag: New container tag
            container_digest: New container digest
            cloud_provider: New cloud provider
            cloud_region: New cloud region
            instance_type: New instance type
            git_commit: New Git commit hash
            git_repository: New Git repository URL
            git_branch: New Git branch name
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        return self.update_snapshot(
            snapshot_id=environment_id,
            name=name,
            description=description,
            python_version=python_version,
            os_type=os_type,
            os_version=os_version,
            architecture=architecture,
            kernel_version=kernel_version,
            container_image=container_image,
            container_tag=container_tag,
            container_digest=container_digest,
            cloud_provider=cloud_provider,
            cloud_region=cloud_region,
            instance_type=instance_type,
            git_commit=git_commit,
            git_repository=git_repository,
            git_branch=git_branch,
        )
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete an environment snapshot.
        
        Args:
            snapshot_id: The ID of the snapshot to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_environment(snapshot_id)
        
    def delete_environment(self, environment_id: str) -> bool:
        """
        Delete an environment snapshot.
        
        Args:
            environment_id: The ID of the environment snapshot to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self.delete_snapshot(environment_id)
    
    def list_snapshots(
        self, environment_type: Optional[Union[EnvironmentType, str]] = None, tags: Optional[Set[str]] = None
    ) -> List[EnvironmentSnapshot]:
        """
        List environment snapshots with optional filtering.
        
        Args:
            environment_type: Filter by environment type
            tags: Filter by tags (snapshots must have all specified tags)
            
        Returns:
            List[EnvironmentSnapshot]: List of snapshots matching the criteria
        """
        if isinstance(environment_type, EnvironmentType):
            environment_type = environment_type.value
            
        return self._storage.list_environments(environment_type, tags)
        
    def list_environments(
        self, type: Optional[Union[EnvironmentType, str]] = None, tags: Optional[Set[str]] = None
    ) -> List[EnvironmentSnapshot]:
        """
        List environment snapshots with optional filtering.
        
        Args:
            type: Filter by environment type
            tags: Filter by tags (environments must have all specified tags)
            
        Returns:
            List[EnvironmentSnapshot]: List of environments matching the criteria
        """
        return self.list_snapshots(environment_type=type, tags=tags)
    
    def create_environment_snapshot(
        self,
        name: str,
        environment_type: Union[EnvironmentType, str] = EnvironmentType.LOCAL,
        description: Optional[str] = None,
        python_version: Optional[str] = None,
        os_type: Optional[Union[OperatingSystemType, str]] = None,
        os_version: Optional[str] = None,
        architecture: Optional[str] = None,
        kernel_version: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        packages: Optional[List[PackageInfo]] = None,
        compute_resources: Optional[List[ComputeResource]] = None,
        config_files: Optional[Dict[str, str]] = None,
        container_image: Optional[str] = None,
        container_tag: Optional[str] = None,
        container_digest: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        cloud_region: Optional[str] = None,
        instance_type: Optional[str] = None,
        git_commit: Optional[str] = None,
        git_repository: Optional[str] = None,
        git_branch: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        custom_metadata: Optional[Dict[str, Union[str, int, float, bool, list, dict]]] = None,
    ) -> str:
        """
        Create a new environment snapshot.
        
        Args:
            name: Snapshot name
            environment_type: Environment type
            description: Snapshot description
            python_version: Python version
            os_type: Operating system type
            os_version: Operating system version
            architecture: CPU architecture
            kernel_version: Kernel version
            environment_variables: Environment variables dictionary
            packages: List of package information
            compute_resources: List of compute resources
            config_files: Dictionary of configuration files (path -> content)
            container_image: Container image name
            container_tag: Container tag
            container_digest: Container digest
            cloud_provider: Cloud provider
            cloud_region: Cloud region
            instance_type: Instance type
            git_commit: Git commit hash
            git_repository: Git repository URL
            git_branch: Git branch name
            tags: Tags for categorization
            custom_metadata: Custom metadata dictionary
            
        Returns:
            str: The ID of the created snapshot
        """
        # Convert string enums to enum values if needed
        if isinstance(environment_type, str):
            environment_type = EnvironmentType(environment_type)
            
        # Use create_snapshot method to create the actual snapshot
        snapshot = self.create_snapshot(
            name=name,
            description=description,
            type=environment_type,
            python_version=python_version,
            os_type=os_type,
            os_version=os_version,
            architecture=architecture,
            kernel_version=kernel_version,
            environment_variables=environment_variables,
            packages=packages,
            compute_resources=compute_resources,
            config_files=config_files,
            container_image=container_image,
            container_tag=container_tag,
            container_digest=container_digest,
            cloud_provider=cloud_provider,
            cloud_region=cloud_region,
            instance_type=instance_type,
            git_commit=git_commit,
            git_repository=git_repository,
            git_branch=git_branch,
            tags=tags,
            custom_metadata=custom_metadata,
        )
        
        return str(snapshot.id) if not isinstance(snapshot.id, str) else snapshot.id
    
    def capture_current_environment(
        self, 
        name: str, 
        description: Optional[str] = None,
        environment_type: Union[EnvironmentType, str] = EnvironmentType.LOCAL,
        include_system_info: bool = True,
        include_env_vars: bool = True,
        include_packages: bool = True,
        include_git_info: bool = True,
        redact_sensitive_env_vars: bool = True,
        tags: Optional[Set[str]] = None,
        custom_metadata: Optional[Dict[str, Union[str, int, float, bool, list, dict]]] = None,
    ) -> str:
        """
        Capture the current Python environment into a snapshot.
        
        Args:
            name: Name for the snapshot
            description: Description for the snapshot
            include_system_info: Whether to include system information
            include_env_vars: Whether to include environment variables
            include_packages: Whether to include installed packages
            include_git_info: Whether to include Git information
            redact_sensitive_env_vars: Whether to redact sensitive environment variables
            tags: Tags for the snapshot
            
        Returns:
            EnvironmentSnapshot: The created snapshot
        """
        # Initialize data
        python_version = None
        os_type = None
        os_version = None
        architecture = None
        kernel_version = None
        packages = []
        environment_variables = {}
        compute_resources = []
        git_commit = None
        git_repository = None
        git_branch = None
        
        # System information
        if include_system_info:
            # Python version
            python_version = sys.version.split()[0]
            
            # OS information
            os_name = platform.system().lower()
            if os_name == "darwin":
                os_type = OperatingSystemType.MACOS
            elif os_name == "linux":
                os_type = OperatingSystemType.LINUX
            elif os_name == "windows":
                os_type = OperatingSystemType.WINDOWS
            else:
                os_type = OperatingSystemType.OTHER
            
            os_version = platform.version()
            architecture = platform.machine()
            
            try:
                if os_type == OperatingSystemType.LINUX:
                    kernel_version = platform.release()
                elif os_type == OperatingSystemType.MACOS:
                    kernel_version = subprocess.check_output(["uname", "-r"]).decode("utf-8").strip()
                elif os_type == OperatingSystemType.WINDOWS:
                    kernel_version = platform.release()
            except:
                kernel_version = "Unknown"
                
            # Add basic compute resource information
            try:
                # Try to detect CPU information
                cpu_count = os.cpu_count() or 1
                cpu_model = "Unknown"
                
                # On Linux, we can get more detailed CPU info
                if os_type == OperatingSystemType.LINUX:
                    try:
                        with open("/proc/cpuinfo", "r") as f:
                            for line in f:
                                if line.startswith("model name"):
                                    cpu_model = line.split(":", 1)[1].strip()
                                    break
                    except:
                        pass
                
                # Add CPU resource
                compute_resources.append(
                    ComputeResource(
                        type=ComputeResourceType.CPU,
                        count=cpu_count,
                        model=cpu_model,
                    )
                )
            except:
                # In case of any detection failure, add a generic resource
                compute_resources.append(
                    ComputeResource(
                        type=ComputeResourceType.CPU,
                        count=1,
                        model="Generic CPU",
                    )
                )
        
        # Environment variables
        if include_env_vars:
            for key, value in os.environ.items():
                # Redact sensitive environment variables
                if redact_sensitive_env_vars and (
                    "token" in key.lower() or 
                    "key" in key.lower() or 
                    "secret" in key.lower() or 
                    "password" in key.lower() or
                    "credential" in key.lower()
                ):
                    environment_variables[key] = "REDACTED"
                else:
                    environment_variables[key] = value
        
        # Installed packages
        if include_packages and distributions:
            for dist in distributions():
                package = PackageInfo(
                    name=dist.metadata['Name'] if 'Name' in dist.metadata else dist.name,
                    version=dist.version,
                    manager=PackageManagerType.PIP,
                )
                packages.append(package)
        
        # Git information
        if include_git_info:
            try:
                # Try to get git information
                git_repository = subprocess.check_output(
                    ["git", "config", "--get", "remote.origin.url"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8").strip()
                
                git_branch = subprocess.check_output(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8").strip()
                
                git_commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    stderr=subprocess.DEVNULL
                ).decode("utf-8").strip()
            except:
                # If git commands fail, ignore and continue
                pass
        
        # Convert string enums to enum values if needed
        if isinstance(environment_type, str):
            environment_type = EnvironmentType(environment_type)
            
        # Create the snapshot
        snapshot = self.create_snapshot(
            name=name,
            description=description,
            type=environment_type,
            python_version=python_version,
            os_type=os_type,
            os_version=os_version,
            architecture=architecture,
            kernel_version=kernel_version,
            environment_variables=environment_variables,
            packages=packages,
            compute_resources=compute_resources,
            git_commit=git_commit,
            git_repository=git_repository,
            git_branch=git_branch,
            tags=tags,
            custom_metadata=custom_metadata,
        )
        
        return str(snapshot.id) if not isinstance(snapshot.id, str) else snapshot.id
    
    def add_package(
        self, 
        env_id: str,
        package: Optional[PackageInfo] = None,
        name: Optional[str] = None, 
        version: Optional[str] = None, 
        manager: Union[PackageManagerType, str] = PackageManagerType.PIP,
        channel: Optional[str] = None,
        extras: Optional[List[str]] = None,
    ) -> bool:
        """
        Add a package to an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            name: Package name
            version: Package version
            manager: Package manager
            channel: Channel (for conda packages)
            extras: Extras (for pip packages with extras)
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        # Use provided package or create a new one
        if package is not None:
            # Use the provided package directly
            snapshot.add_package(package)
        else:
            # Convert string enum to enum value if needed
            if isinstance(manager, str):
                manager = PackageManagerType(manager)
            
            # Create package with provided parameters
            if name is not None and version is not None:
                new_package = PackageInfo(
                    name=name,
                    version=version,
                    manager=manager,
                    channel=channel,
                    extras=extras,
                )
                snapshot.add_package(new_package)
            else:
                raise ValueError("Either a package or name and version must be provided")
        
        return self._storage.update_environment(snapshot)
    
    def remove_package(
        self, env_id: str, package_name: str, manager: Union[PackageManagerType, str] = PackageManagerType.PIP
    ) -> bool:
        """
        Remove a package from an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            package_name: Package name
            manager: Package manager
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        # Convert string enum to enum value if needed
        if isinstance(manager, str):
            manager = PackageManagerType(manager)
        
        result = snapshot.remove_package(package_name, manager)
        if result:
            return self._storage.update_environment(snapshot)
        return False
    
    def add_compute_resource(
        self, 
        env_id: str,
        resource: Optional[ComputeResource] = None,
        type: Optional[Union[ComputeResourceType, str]] = None, 
        count: Optional[int] = None, 
        model: Optional[str] = None,
        memory_gb: Optional[float] = None,
    ) -> bool:
        """
        Add a compute resource to an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            resource: An already created ComputeResource object
            type: Type of compute resource
            count: Number of resources
            model: Model name/identifier
            memory_gb: Memory in gigabytes
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        # Use provided resource or create a new one
        if resource is not None:
            # Use the provided resource directly
            snapshot.add_compute_resource(resource)
        else:
            # Convert string enum to enum value if needed
            if isinstance(type, str) and type is not None:
                type_enum = ComputeResourceType(type)
            else:
                type_enum = type
                
            # Validate required parameters
            if type_enum is None or count is None:
                raise ValueError("Either a resource or type and count must be provided")
                
            # Create resource with provided parameters
            new_resource = ComputeResource(
                type=type_enum,
                count=count,
                model=model,
                memory_gb=memory_gb,
            )
            snapshot.add_compute_resource(new_resource)
        
        return self._storage.update_environment(snapshot)
    
    def remove_compute_resource(self, env_id: str, resource_index: int) -> bool:
        """
        Remove a compute resource from an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            resource_index: Index of the resource to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        if resource_index < 0 or resource_index >= len(snapshot.compute_resources):
            # Return False for invalid indices instead of raising IndexError
            return False
        
        result = snapshot.remove_compute_resource(resource_index)
        if result:
            return self._storage.update_environment(snapshot)
        return False
    
    def add_environment_variable(self, env_id: str, key: str, value: str) -> bool:
        """
        Add an environment variable to a snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            key: Variable name
            value: Variable value
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        snapshot.add_environment_variable(key, value)
        return self._storage.update_environment(snapshot)
    
    def remove_environment_variable(self, env_id: str, key: str) -> bool:
        """
        Remove an environment variable from a snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            key: Variable name
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        result = snapshot.remove_environment_variable(key)
        if result:
            return self._storage.update_environment(snapshot)
        return False
    
    def add_config_file(self, env_id: str, file_path: str, content: str) -> bool:
        """
        Add a configuration file to a snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            file_path: Path of the configuration file
            content: Content of the file
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        snapshot.add_config_file(file_path, content)
        return self._storage.update_environment(snapshot)
    
    def remove_config_file(self, env_id: str, file_path: str) -> bool:
        """
        Remove a configuration file from a snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            file_path: Path of the configuration file
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        result = snapshot.remove_config_file(file_path)
        if result:
            return self._storage.update_environment(snapshot)
        return False
    
    def add_tag(self, env_id: str, tag: str) -> bool:
        """
        Add a tag to an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            tag: The tag to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        snapshot.add_tag(tag)
        return self._storage.update_environment(snapshot)
    
    def add_environment_tag(self, environment_id: str, tag: str) -> bool:
        """
        Add a tag to an environment snapshot.
        
        Args:
            environment_id: The ID of the environment snapshot
            tag: The tag to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        return self.add_tag(environment_id, tag)
    
    def remove_tag(self, env_id: str, tag: str) -> bool:
        """
        Remove a tag from an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            tag: The tag to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        result = snapshot.remove_tag(tag)
        if result:
            return self._storage.update_environment(snapshot)
        return False
        
    def remove_environment_tag(self, environment_id: str, tag: str) -> bool:
        """
        Remove a tag from an environment snapshot.
        
        Args:
            environment_id: The ID of the environment snapshot
            tag: The tag to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        return self.remove_tag(environment_id, tag)
    
    def update_custom_metadata(
        self, env_id: str, key: str, value: Union[str, int, float, bool, list, dict]
    ) -> bool:
        """
        Update a custom metadata field for an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            key: The metadata key
            value: The metadata value
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        snapshot.update_custom_metadata(key, value)
        return self._storage.update_environment(snapshot)
    
    def remove_custom_metadata(self, env_id: str, key: str) -> bool:
        """
        Remove a custom metadata field from an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            key: The metadata key
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(env_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {env_id} does not exist")
        
        result = snapshot.remove_custom_metadata(key)
        if result:
            return self._storage.update_environment(snapshot)
        return False
    
    # Task-Environment link operations
    
    def link_task_to_environment(
        self,
        task_id: str,
        environment_id: str,
        description: Optional[str] = None,
        actual_execution_time: Optional[float] = None,
    ) -> str:
        """
        Link a task to an environment snapshot.
        
        Args:
            task_id: The ID of the task
            environment_id: The ID of the environment snapshot
            description: Description of the relationship
            actual_execution_time: Runtime in seconds, if applicable
            
        Returns:
            str: The ID of the created link
            
        Raises:
            ValueError: If environment doesn't exist
        """
        snapshot = self._storage.get_environment(environment_id)
        if not snapshot:
            raise ValueError(f"Environment snapshot with ID {environment_id} does not exist")
        
        # Check if link already exists
        existing_snapshots = self._storage.get_environments_by_task(task_id)
        for s in existing_snapshots:
            if s.id == environment_id:
                # Link already exists
                return '00000000-0000-0000-0000-000000000000'
        
        # Create the link
        link = TaskEnvironmentLink(
            task_id=task_id,
            environment_id=environment_id,
            description=description,
            actual_execution_time=actual_execution_time,
        )
        
        return self._storage.create_task_environment_link(link)
    
    def unlink_task_from_environment(self, task_id: str, env_id: str) -> bool:
        """
        Remove a link between a task and an environment snapshot.
        
        Args:
            task_id: The ID of the task
            env_id: The ID of the environment snapshot
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Find the link
        links = self._storage.get_links_by_task(task_id)
        for link in links:
            if link.environment_id == env_id:
                return self._storage.delete_task_environment_link(link.id)
        
        return False
        
    def get_links_by_task(self, task_id: str) -> List[TaskEnvironmentLink]:
        """
        Get all task-environment links for a given task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[TaskEnvironmentLink]: List of links for the task
        """
        return self._storage.get_links_by_task(task_id)
    
    def get_snapshots_for_task(self, task_id: str) -> List[EnvironmentSnapshot]:
        """
        Get all environment snapshots associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[EnvironmentSnapshot]: List of associated snapshots
        """
        return self._storage.get_environments_by_task(task_id)
        
    def get_environments_by_task(self, task_id: str) -> List[EnvironmentSnapshot]:
        """
        Get all environment snapshots associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[EnvironmentSnapshot]: List of associated environment snapshots
        """
        return self.get_snapshots_for_task(task_id)
    
    def get_tasks_for_snapshot(self, env_id: str) -> List[str]:
        """
        Get all task IDs associated with an environment snapshot.
        
        Args:
            env_id: The ID of the environment snapshot
            
        Returns:
            List[str]: List of associated task IDs
        """
        return self._storage.get_tasks_by_environment(env_id)
        
    def get_tasks_by_environment(self, environment_id: str) -> List[str]:
        """
        Get all task IDs associated with an environment snapshot.
        
        Args:
            environment_id: The ID of the environment snapshot
            
        Returns:
            List[str]: List of associated task IDs
        """
        return self.get_tasks_for_snapshot(environment_id)
    
    def get_task_environment_link(self, link_id: str) -> Optional[TaskEnvironmentLink]:
        """
        Get a task-environment link by ID.
        
        Args:
            link_id: The ID of the link to retrieve
            
        Returns:
            Optional[TaskEnvironmentLink]: The link if found, None otherwise
        """
        return self._storage.get_task_environment_link(link_id)
        
    def update_task_environment_link(
        self,
        link_id: str,
        description: Optional[str] = None,
        actual_execution_time: Optional[float] = None,
    ) -> bool:
        """
        Update a task-environment link.
        
        Args:
            link_id: The ID of the link to update
            description: New description
            actual_execution_time: New execution time
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If link doesn't exist
        """
        link = self._storage.get_task_environment_link(link_id)
        if not link:
            raise ValueError(f"Task-environment link with ID {link_id} does not exist")
        
        update_data = {}
        if description is not None:
            update_data["description"] = description
        if actual_execution_time is not None:
            update_data["actual_execution_time"] = actual_execution_time
            
        link.update(**update_data)
        return self._storage.update_task_environment_link(link)
    
    def add_note_to_link(self, link_id: str, note: str) -> bool:
        """
        Add a note to a task-environment link.
        
        Args:
            link_id: The ID of the link
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If link doesn't exist
        """
        link = self._storage.get_task_environment_link(link_id)
        if not link:
            raise ValueError(f"Task-environment link with ID {link_id} does not exist")
            
        link.add_note(note)
        return self._storage.update_task_environment_link(link)
        
    def delete_task_environment_link(self, link_id: str) -> bool:
        """
        Delete a task-environment link.
        
        Args:
            link_id: The ID of the link to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self._storage.delete_task_environment_link(link_id)
        
    def add_note_to_task_environment(self, task_id: str, env_id: str, note: str) -> bool:
        """
        Add a note to the link between a task and an environment snapshot.
        
        Args:
            task_id: The ID of the task
            env_id: The ID of the environment snapshot
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Find the link
        links = self._storage.get_links_by_task(task_id)
        for link in links:
            if link.environment_id == env_id:
                link.add_note(note)
                return self._storage.update_task_environment_link(link)
        
        return False
    
    def compare_snapshots(self, snapshot_id1: str, snapshot_id2: str) -> Dict[str, Any]:
        """
        Compare two environment snapshots to find differences.
        
        Args:
            snapshot_id1: The ID of the first snapshot
            snapshot_id2: The ID of the second snapshot
            
        Returns:
            Dict[str, Any]: Dictionary of differences
            
        Raises:
            ValueError: If snapshots don't exist
        """
        snapshot1 = self._storage.get_environment(snapshot_id1)
        if not snapshot1:
            raise ValueError(f"Environment snapshot with ID {snapshot_id1} does not exist")
        
        snapshot2 = self._storage.get_environment(snapshot_id2)
        if not snapshot2:
            raise ValueError(f"Environment snapshot with ID {snapshot_id2} does not exist")
        
        # Compare snapshots
        differences = {}
        
        # System information differences (python version, os info, etc.)
        system_differences = {}
        
        # Compare Python version
        if snapshot1.python_version != snapshot2.python_version:
            system_differences["python_version"] = {
                "env1": snapshot1.python_version,
                "env2": snapshot2.python_version,
            }
        
        # Compare OS information
        if snapshot1.os_type != snapshot2.os_type:
            system_differences["os_type"] = {
                "env1": snapshot1.os_type,
                "env2": snapshot2.os_type,
            }
        
        if snapshot1.os_version != snapshot2.os_version:
            system_differences["os_version"] = {
                "env1": snapshot1.os_version,
                "env2": snapshot2.os_version,
            }
            
        # Compare architecture
        if snapshot1.architecture != snapshot2.architecture:
            system_differences["architecture"] = {
                "env1": snapshot1.architecture,
                "env2": snapshot2.architecture,
            }
            
        # Compare kernel version
        if snapshot1.kernel_version != snapshot2.kernel_version:
            system_differences["kernel_version"] = {
                "env1": snapshot1.kernel_version,
                "env2": snapshot2.kernel_version,
            }
            
        # Add system differences to the main differences dict if any exist
        if system_differences:
            differences["system"] = system_differences
        
        # Compare packages
        packages1 = {(p.name, p.manager): p for p in snapshot1.packages}
        packages2 = {(p.name, p.manager): p for p in snapshot2.packages}
        
        # Packages in snapshot1 but not in snapshot2
        packages_only_in_1 = [
            {"name": p.name, "version": p.version, "manager": str(p.manager)}
            for (name, manager), p in packages1.items()
            if (name, manager) not in packages2
        ]
        
        # Packages in snapshot2 but not in snapshot1
        packages_only_in_2 = [
            {"name": p.name, "version": p.version, "manager": str(p.manager)}
            for (name, manager), p in packages2.items()
            if (name, manager) not in packages1
        ]
        
        # Packages with different versions
        packages_diff_version = [
            {
                "name": name,
                "manager": str(manager),
                "version1": packages1[(name, manager)].version,
                "version2": packages2[(name, manager)].version,
            }
            for (name, manager) in packages1.keys() & packages2.keys()
            if packages1[(name, manager)].version != packages2[(name, manager)].version
        ]
        
        if packages_only_in_1 or packages_only_in_2 or packages_diff_version:
            differences["packages"] = {
                "only_in_env1": packages_only_in_1,
                "only_in_env2": packages_only_in_2,
                "version_different": packages_diff_version,
            }
        
        # Compare environment variables
        env_vars1 = snapshot1.environment_variables
        env_vars2 = snapshot2.environment_variables
        
        env_vars_keys1 = set(env_vars1.keys())
        env_vars_keys2 = set(env_vars2.keys())
        
        only_in_env1 = list(env_vars_keys1 - env_vars_keys2)
        only_in_env2 = list(env_vars_keys2 - env_vars_keys1)
        
        # Variables with different values
        different_values = [
            key for key in env_vars_keys1 & env_vars_keys2
            if env_vars1[key] != env_vars2[key]
        ]
        
        if only_in_env1 or only_in_env2 or different_values:
            differences["environment_variables"] = {
                "only_in_env1": only_in_env1,
                "only_in_env2": only_in_env2,
                "value_different": different_values,
            }
            
        # Compare config files
        config_files1 = snapshot1.config_files
        config_files2 = snapshot2.config_files
        
        config_files_keys1 = set(config_files1.keys())
        config_files_keys2 = set(config_files2.keys())
        
        only_in_env1_files = list(config_files_keys1 - config_files_keys2)
        only_in_env2_files = list(config_files_keys2 - config_files_keys1)
        
        # Files with different content
        different_content = [
            key for key in config_files_keys1 & config_files_keys2
            if config_files1[key] != config_files2[key]
        ]
        
        if only_in_env1_files or only_in_env2_files or different_content:
            differences["config_files"] = {
                "only_in_env1": only_in_env1_files,
                "only_in_env2": only_in_env2_files,
                "content_different": different_content,
            }
            
        # Compare compute resources
        # For compute resources, just provide a count difference since they don't have unique identifiers
        if len(snapshot1.compute_resources) != len(snapshot2.compute_resources):
            differences["compute_resources"] = {
                "count_env1": len(snapshot1.compute_resources),
                "count_env2": len(snapshot2.compute_resources),
            }
            
        # Compare container information
        container_differences = {}
        
        if snapshot1.container_image != snapshot2.container_image:
            container_differences["image"] = {
                "env1": snapshot1.container_image,
                "env2": snapshot2.container_image,
            }
            
        if snapshot1.container_tag != snapshot2.container_tag:
            container_differences["tag"] = {
                "env1": snapshot1.container_tag,
                "env2": snapshot2.container_tag,
            }
            
        if snapshot1.container_digest != snapshot2.container_digest:
            container_differences["digest"] = {
                "env1": snapshot1.container_digest,
                "env2": snapshot2.container_digest,
            }
            
        if container_differences:
            differences["container"] = container_differences
            
        # Compare cloud information
        cloud_differences = {}
        
        if snapshot1.cloud_provider != snapshot2.cloud_provider:
            cloud_differences["provider"] = {
                "env1": snapshot1.cloud_provider,
                "env2": snapshot2.cloud_provider,
            }
            
        if snapshot1.cloud_region != snapshot2.cloud_region:
            cloud_differences["region"] = {
                "env1": snapshot1.cloud_region,
                "env2": snapshot2.cloud_region,
            }
            
        if snapshot1.instance_type != snapshot2.instance_type:
            cloud_differences["instance_type"] = {
                "env1": snapshot1.instance_type,
                "env2": snapshot2.instance_type,
            }
            
        if cloud_differences:
            differences["cloud"] = cloud_differences
        
        return differences
        
    def compare_environments(self, env_id1: str, env_id2: str) -> Dict[str, Any]:
        """
        Compare two environment snapshots to find differences.
        
        Args:
            env_id1: The ID of the first environment
            env_id2: The ID of the second environment
            
        Returns:
            Dict[str, Any]: Dictionary of differences
            
        Raises:
            ValueError: If environments don't exist
        """
        return self.compare_snapshots(env_id1, env_id2)
        
    def clone_snapshot(self, source_id: str, name: str, description: Optional[str] = None) -> EnvironmentSnapshot:
        """
        Clone an existing environment snapshot with a new name and description.
        
        Args:
            source_id: The ID of the source snapshot to clone
            name: Name for the new snapshot
            description: Description for the new snapshot
            
        Returns:
            EnvironmentSnapshot: The newly created snapshot
            
        Raises:
            ValueError: If source snapshot doesn't exist
        """
        # Get the source snapshot
        source = self._storage.get_environment(source_id)
        if not source:
            raise ValueError(f"Environment snapshot with ID {source_id} does not exist")
        
        # Create a new snapshot with basic properties but a different ID
        snapshot = EnvironmentSnapshot(
            name=name,
            description=description or f"Clone of {source.name}",
            type=source.type,
            python_version=source.python_version,
            os_type=source.os_type,
            os_version=source.os_version,
            architecture=source.architecture,
            kernel_version=source.kernel_version,
            environment_variables=source.environment_variables.copy(),
            config_files=source.config_files.copy(),
            container_image=source.container_image,
            container_tag=source.container_tag,
            container_digest=source.container_digest,
            cloud_provider=source.cloud_provider,
            cloud_region=source.cloud_region,
            instance_type=source.instance_type,
            git_commit=source.git_commit,
            git_repository=source.git_repository,
            git_branch=source.git_branch,
            tags=source.tags.copy(),
            custom_metadata=source.custom_metadata.copy(),
        )
        
        # Save the new snapshot to storage
        self._storage.create_environment(snapshot)
        
        # Copy packages - need to create new PackageInfo objects
        if hasattr(source, 'packages') and source.packages:
            for package in source.packages:
                # If it's a PackageInfo object, use its attributes
                if hasattr(package, 'name') and hasattr(package, 'version'):
                    self.add_package(
                        snapshot.id,
                        name=package.name,
                        version=package.version,
                        manager=package.manager if hasattr(package, 'manager') else PackageManagerType.PIP,
                        channel=package.channel if hasattr(package, 'channel') else None,
                        extras=package.extras if hasattr(package, 'extras') else None
                    )
                # If it's a tuple of (name, version) or a string
                elif isinstance(package, tuple) and len(package) >= 2:
                    self.add_package(
                        snapshot.id,
                        name=package[0],
                        version=package[1]
                    )
                elif isinstance(package, str):
                    # Assuming string is just the package name, use a default version
                    self.add_package(
                        snapshot.id,
                        name=package,
                        version="latest"
                    )
        
        # Copy compute resources - need to create new ComputeResource objects
        if hasattr(source, 'compute_resources') and source.compute_resources:
            for resource in source.compute_resources:
                if hasattr(resource, 'type') and hasattr(resource, 'count'):
                    self.add_compute_resource(
                        snapshot.id,
                        type=resource.type,
                        count=resource.count,
                        model=resource.model if hasattr(resource, 'model') else None,
                        memory_gb=resource.memory_gb if hasattr(resource, 'memory_gb') else None
                    )
        
        return snapshot