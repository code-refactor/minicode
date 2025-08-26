from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass, field

from common.core import BaseEntity


class EnvironmentType(str, Enum):
    """Types of computational environments."""
    
    CONDA = "conda"
    VENV = "venv"
    POETRY = "poetry"
    DOCKER = "docker"
    SINGULARITY = "singularity"
    KUBERNETES = "kubernetes"
    CLOUD_INSTANCE = "cloud_instance"
    LOCAL = "local"
    OTHER = "other"


class PackageManagerType(str, Enum):
    """Types of package managers."""
    
    PIP = "pip"
    CONDA = "conda"
    APT = "apt"
    YUM = "yum"
    NPM = "npm"
    YARN = "yarn"
    GEM = "gem"
    BREW = "brew"
    OTHER = "other"


class OperatingSystemType(str, Enum):
    """Types of operating systems."""
    
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"
    OTHER = "other"


class ComputeResourceType(str, Enum):
    """Types of compute resources."""
    
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"
    FPGA = "fpga"
    QUANTUM = "quantum"
    OTHER = "other"


@dataclass
class PackageInfo:
    """Information about a software package."""
    
    name: str = ""
    version: str = ""
    manager: PackageManagerType = PackageManagerType.PIP
    channel: Optional[str] = None  # For conda packages
    extras: Optional[List[str]] = None  # For pip packages with extras
    custom_metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class ComputeResource:
    """Information about a compute resource."""
    
    type: ComputeResourceType = ComputeResourceType.CPU
    count: int = 1
    model: Optional[str] = None
    memory_gb: Optional[float] = None
    custom_metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class EnvironmentSnapshot(BaseEntity):
    """Model representing a computational environment snapshot."""
    
    name: str = ""
    description: Optional[str] = None
    type: EnvironmentType = EnvironmentType.LOCAL
    
    # System information
    python_version: Optional[str] = None
    os_type: Optional[OperatingSystemType] = None
    os_version: Optional[str] = None
    architecture: Optional[str] = None
    kernel_version: Optional[str] = None
    
    # Compute resources
    compute_resources: List[ComputeResource] = field(default_factory=list)
    
    # Environment variables (with sensitive values redacted)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    
    # Installed packages
    packages: List[PackageInfo] = field(default_factory=list)
    
    # Configuration files and their content
    config_files: Dict[str, str] = field(default_factory=dict)
    
    # Container information
    container_image: Optional[str] = None
    container_tag: Optional[str] = None
    container_digest: Optional[str] = None
    
    # Cloud information
    cloud_provider: Optional[str] = None
    cloud_region: Optional[str] = None
    instance_type: Optional[str] = None
    
    # Version control information
    git_commit: Optional[str] = None
    git_repository: Optional[str] = None
    git_branch: Optional[str] = None
    
    # Tags for organization
    tags: Set[str] = field(default_factory=set)
    
    # Custom metadata
    custom_metadata: Dict[str, Union[str, int, float, bool, list, dict]] = field(
        default_factory=dict
    )
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Environment name cannot be empty")
    
    def update(self, **kwargs) -> 'EnvironmentSnapshot':
        """Update environment snapshot fields in place."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        return self
    
    def add_package(self, package: PackageInfo) -> None:
        """Add a package to the environment."""
        self.packages.append(package)
        self.updated_at = datetime.now()
    
    def remove_package(self, package_name: str, manager: PackageManagerType) -> bool:
        """
        Remove a package from the environment.
        
        Args:
            package_name: The name of the package to remove
            manager: The package manager of the package
            
        Returns:
            bool: True if package was removed, False if not found
        """
        original_length = len(self.packages)
        self.packages = [
            p for p in self.packages 
            if not (p.name == package_name and p.manager == manager)
        ]
        
        if len(self.packages) < original_length:
            self.updated_at = datetime.now()
            return True
        return False
    
    def add_compute_resource(self, resource: ComputeResource) -> None:
        """Add a compute resource to the environment."""
        self.compute_resources.append(resource)
        self.updated_at = datetime.now()
    
    def remove_compute_resource(self, resource_index: int) -> bool:
        """
        Remove a compute resource from the environment.
        
        Args:
            resource_index: The index of the resource to remove
            
        Returns:
            bool: True if resource was removed, False if index is invalid
        """
        if 0 <= resource_index < len(self.compute_resources):
            self.compute_resources.pop(resource_index)
            self.updated_at = datetime.now()
            return True
        return False
    
    def add_environment_variable(self, key: str, value: str) -> None:
        """Add an environment variable to the snapshot."""
        self.environment_variables[key] = value
        self.updated_at = datetime.now()
    
    def remove_environment_variable(self, key: str) -> bool:
        """
        Remove an environment variable from the snapshot.
        
        Args:
            key: The key of the environment variable to remove
            
        Returns:
            bool: True if variable was removed, False if not found
        """
        if key in self.environment_variables:
            del self.environment_variables[key]
            self.updated_at = datetime.now()
            return True
        return False
    
    def add_config_file(self, file_path: str, content: str) -> None:
        """Add a configuration file to the snapshot."""
        self.config_files[file_path] = content
        self.updated_at = datetime.now()
    
    def remove_config_file(self, file_path: str) -> bool:
        """
        Remove a configuration file from the snapshot.
        
        Args:
            file_path: The path of the configuration file to remove
            
        Returns:
            bool: True if file was removed, False if not found
        """
        if file_path in self.config_files:
            del self.config_files[file_path]
            self.updated_at = datetime.now()
            return True
        return False
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the environment snapshot."""
        self.tags.add(tag)
        self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> bool:
        """
        Remove a tag from the environment snapshot.
        
        Args:
            tag: The tag to remove
            
        Returns:
            bool: True if tag was removed, False if not found
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
            return True
        return False
    
    def update_custom_metadata(self, key: str, value: Union[str, int, float, bool, list, dict]) -> None:
        """Update a custom metadata field."""
        self.custom_metadata[key] = value
        self.updated_at = datetime.now()
    
    def remove_custom_metadata(self, key: str) -> bool:
        """
        Remove a custom metadata field.
        
        Args:
            key: The key of the custom field to remove
            
        Returns:
            bool: True if field was removed, False if not found
        """
        if key in self.custom_metadata:
            del self.custom_metadata[key]
            self.updated_at = datetime.now()
            return True
        return False


@dataclass
class TaskEnvironmentLink(BaseEntity):
    """Model representing a link between a research task and an environment snapshot."""
    
    task_id: str = ""
    environment_id: str = ""
    
    # Link metadata
    description: Optional[str] = None  # Description of how this environment relates to the task
    actual_execution_time: Optional[float] = None  # Runtime in seconds, if applicable
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")
        if not self.environment_id:
            raise ValueError("Environment ID cannot be empty")
    
    def update(self, **kwargs) -> 'TaskEnvironmentLink':
        """Update link fields in place."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        return self
    
    def add_note(self, note: str) -> None:
        """Add a note to the link."""
        self.notes.append(note)
        self.updated_at = datetime.now()