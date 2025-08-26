from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass, field

from common.core import BaseEntity


class DatasetFormat(str, Enum):
    """Supported dataset formats."""
    
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    HDF5 = "hdf5"
    EXCEL = "excel"
    SQL = "sql"
    PICKLE = "pickle"
    NUMPY = "numpy"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"


class DatasetStorageType(str, Enum):
    """Types of dataset storage."""
    
    LOCAL = "local"
    S3 = "s3"
    GCS = "gs"
    AZURE = "azure"
    HTTP = "http"
    DATABASE = "database"
    GIT_LFS = "git_lfs"
    DVC = "dvc"
    OTHER = "other"


class DataTransformationType(str, Enum):
    """Types of data transformations."""
    
    CLEANING = "cleaning"
    NORMALIZATION = "normalization"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"
    FEATURE_ENGINEERING = "feature_engineering"
    IMPUTATION = "imputation"
    ENCODING = "encoding"
    DIMENSIONALITY_REDUCTION = "dimensionality_reduction"
    RESAMPLING = "resampling"
    SPLITTING = "splitting"
    AUGMENTATION = "augmentation"
    OTHER = "other"


@dataclass
class Dataset(BaseEntity):
    """Model representing a dataset."""
    
    name: str = ""
    description: Optional[str] = None
    format: DatasetFormat = DatasetFormat.CSV
    storage_type: DatasetStorageType = DatasetStorageType.LOCAL
    location: str = ""  # Path or URL to the dataset
    
    # Metadata
    size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    schema: Optional[Dict[str, str]] = None  # Column name -> data type
    tags: Set[str] = field(default_factory=set)
    custom_metadata: Dict[str, Union[str, int, float, bool, list, dict]] = field(
        default_factory=dict
    )
    
    # Version control
    hash: Optional[str] = None  # Content hash for verification
    version: Optional[str] = None  # Version identifier
    parent_dataset_id: Optional[str] = None  # Previous version in lineage
    
    # Additional properties for integration tests
    # This isn't persisted, but used for convenience in tests
    versions: List[Any] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Dataset name cannot be empty")
        if not self.location:
            raise ValueError("Dataset location cannot be empty")
    
    def update(self, **kwargs) -> 'Dataset':
        """Update dataset fields in place."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        return self
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the dataset."""
        self.tags.add(tag)
        self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the dataset."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
    
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
class DatasetVersion(BaseEntity):
    """Model representing a specific version of a dataset."""
    
    dataset_id: str = ""  # Reference to the dataset
    version_number: str = ""  # Semantic version or other identifier
    creator: Optional[str] = None  # Who created this version
    description: Optional[str] = None  # What changed in this version
    
    # Version details
    location: str = ""  # Path or URL to this specific version
    hash: Optional[str] = None  # Content hash for verification
    size_bytes: Optional[int] = None
    parent_version_id: Optional[str] = None  # Previous version
    
    # Metadata specific to this version
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    schema: Optional[Dict[str, str]] = None  # Column name -> data type
    custom_metadata: Dict[str, Union[str, int, float, bool, list, dict]] = field(
        default_factory=dict
    )
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.dataset_id:
            raise ValueError("Dataset ID cannot be empty")
        if not self.version_number:
            raise ValueError("Version number cannot be empty")
        if not self.location:
            raise ValueError("Version location cannot be empty")
    
    def update(self, **kwargs) -> 'DatasetVersion':
        """Update version fields in place."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        return self
    
    def update_custom_metadata(self, key: str, value: Union[str, int, float, bool, list, dict]) -> None:
        """Update a custom metadata field."""
        self.custom_metadata[key] = value
    
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
            return True
        return False


@dataclass
class DataTransformation(BaseEntity):
    """Model representing a transformation applied to a dataset."""
    
    type: DataTransformationType = DataTransformationType.OTHER
    name: str = ""  # Name of the transformation
    description: Optional[str] = None
    
    # Input and output datasets
    input_dataset_version_id: str = ""  # Version ID of the input dataset
    output_dataset_version_id: str = ""  # Version ID of the output dataset
    
    # Transformation details
    parameters: Dict[str, Union[str, int, float, bool, list, dict]] = field(
        default_factory=dict
    )  # Parameters used in the transformation
    code_reference: Optional[str] = None  # Reference to the code that performed the transformation
    execution_time_seconds: Optional[float] = None  # How long the transformation took
    
    # Metadata
    tags: Set[str] = field(default_factory=set)
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Transformation name cannot be empty")
        if not self.input_dataset_version_id:
            raise ValueError("Input dataset version ID cannot be empty")
        if not self.output_dataset_version_id:
            raise ValueError("Output dataset version ID cannot be empty")
    
    def update(self, **kwargs) -> 'DataTransformation':
        """Update transformation fields in place."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
        return self
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the transformation."""
        self.tags.add(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the transformation."""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def add_note(self, note: str) -> None:
        """Add a note to the transformation."""
        self.notes.append(note)
    
    def update_parameter(self, key: str, value: Union[str, int, float, bool, list, dict]) -> None:
        """Update a transformation parameter."""
        self.parameters[key] = value
    
    def remove_parameter(self, key: str) -> bool:
        """
        Remove a transformation parameter.
        
        Args:
            key: The key of the parameter to remove
            
        Returns:
            bool: True if parameter was removed, False if not found
        """
        if key in self.parameters:
            del self.parameters[key]
            return True
        return False


@dataclass
class TaskDatasetLink(BaseEntity):
    """Model representing a link between a research task and a dataset version."""
    
    task_id: str = ""
    dataset_version_id: str = ""
    
    # Link metadata
    usage_type: Optional[str] = None  # How the dataset is used (input, output, reference, etc.)
    description: Optional[str] = None  # Description of how this dataset relates to the task
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields."""
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")
        if not self.dataset_version_id:
            raise ValueError("Dataset version ID cannot be empty")
    
    def update(self, **kwargs) -> 'TaskDatasetLink':
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