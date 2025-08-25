from datetime import datetime
from typing import Dict, List, Optional, Set, Union, Any
from uuid import UUID

from common.core import BaseService, InMemoryStorage
from .models import (
    Dataset, 
    DatasetVersion, 
    DataTransformation, 
    TaskDatasetLink, 
    DatasetFormat,
    DatasetStorageType,
    DataTransformationType
)
from .storage import DatasetStorageInterface, InMemoryDatasetStorage


class DatasetVersioningService(BaseService[Dataset]):
    """Service for managing datasets, their versions, and transformations."""
    
    def __init__(self, storage: Optional[DatasetStorageInterface] = None):
        """
        Initialize the dataset versioning service.
        
        Args:
            storage: The storage implementation to use. If None, uses InMemoryDatasetStorage.
        """
        # Initialize with dataset storage for base service
        dataset_storage = InMemoryStorage(Dataset) if storage is None else None
        super().__init__(dataset_storage) if dataset_storage else None
        
        # Use provided storage or default
        self._storage = storage or InMemoryDatasetStorage()
    
    # Dataset operations
    
    def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        format: Union[DatasetFormat, str] = DatasetFormat.CSV,
        storage_type: Union[DatasetStorageType, str] = DatasetStorageType.LOCAL,
        location: str = "",
        size_bytes: Optional[int] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        schema: Optional[Dict[str, str]] = None,
        tags: Optional[Set[str]] = None,
        hash: Optional[str] = None,
        version: Optional[str] = None,
        custom_metadata: Optional[Dict[str, Union[str, int, float, bool, list, dict]]] = None,
    ) -> str:
        """
        Create a new dataset.
        
        Args:
            name: Dataset name
            description: Dataset description
            format: Dataset format
            storage_type: Type of storage
            location: Path or URL to the dataset
            size_bytes: Size of the dataset in bytes
            row_count: Number of rows
            column_count: Number of columns
            schema: Data schema (column name -> data type)
            tags: Tags for categorization
            hash: Content hash for verification
            version: Version identifier
            custom_metadata: Custom metadata fields
            
        Returns:
            UUID: The ID of the created dataset
        """
        # Convert string enums to enum values if needed
        if isinstance(format, str):
            format = DatasetFormat(format)
        
        if isinstance(storage_type, str):
            storage_type = DatasetStorageType(storage_type)
        
        # Create the dataset
        dataset = Dataset(
            name=name,
            description=description,
            format=format,
            storage_type=storage_type,
            location=location,
            size_bytes=size_bytes,
            row_count=row_count,
            column_count=column_count,
            schema=schema or {},
            tags=tags or set(),
            hash=hash,
            version=version,
            custom_metadata=custom_metadata or {},
        )
        
        # Save the dataset
        return self._storage.create_dataset(dataset)
    
    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """
        Retrieve a dataset by ID.
        
        Args:
            dataset_id: The ID of the dataset to retrieve
            
        Returns:
            Optional[Dataset]: The dataset if found, None otherwise
        """
        return self._storage.get_dataset(dataset_id)
    
    def update_dataset(
        self,
        dataset_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        size_bytes: Optional[int] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        schema: Optional[Dict[str, str]] = None,
        hash: Optional[str] = None,
        version: Optional[str] = None,
    ) -> bool:
        """
        Update an existing dataset.
        
        Args:
            dataset_id: The ID of the dataset to update
            name: New dataset name
            description: New dataset description
            location: New path or URL
            size_bytes: New size in bytes
            row_count: New row count
            column_count: New column count
            schema: New schema
            hash: New content hash
            version: New version identifier
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if location is not None:
            update_data["location"] = location
        if size_bytes is not None:
            update_data["size_bytes"] = size_bytes
        if row_count is not None:
            update_data["row_count"] = row_count
        if column_count is not None:
            update_data["column_count"] = column_count
        if schema is not None:
            update_data["schema"] = schema
        if hash is not None:
            update_data["hash"] = hash
        if version is not None:
            update_data["version"] = version
        
        dataset.update(**update_data)
        return self._storage.update_dataset(dataset)
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a dataset and all its versions.
        
        Args:
            dataset_id: The ID of the dataset to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_dataset(dataset_id)
    
    def add_derivation(
        self,
        derived_dataset_id: str,
        source_dataset_id: str,
        transformation: str
    ) -> str:
        """
        Create a relationship between a derived dataset and its source.
        
        Args:
            derived_dataset_id: The ID of the derived dataset
            source_dataset_id: The ID of the source dataset
            transformation: Description of the transformation
            
        Returns:
            UUID: The ID of the created transformation record
            
        Raises:
            ValueError: If either dataset doesn't exist
        """
        # Check if both datasets exist
        derived_dataset = self._storage.get_dataset(derived_dataset_id)
        if not derived_dataset:
            raise ValueError(f"Derived dataset with ID {derived_dataset_id} does not exist")
            
        source_dataset = self._storage.get_dataset(source_dataset_id)
        if not source_dataset:
            raise ValueError(f"Source dataset with ID {source_dataset_id} does not exist")
        
        # Create a transformation record
        # For simplicity, we'll use the latest version of each dataset if available
        # or create a dummy version if none exists
        source_versions = self._storage.list_dataset_versions(source_dataset_id)
        derived_versions = self._storage.list_dataset_versions(derived_dataset_id)
        
        source_version_id = source_versions[0].id if source_versions else None
        derived_version_id = derived_versions[0].id if derived_versions else None
        
        # If no versions exist, we can't create a proper transformation record
        if not source_version_id or not derived_version_id:
            # Create a simple "dummy" relationship by using custom metadata
            if not source_version_id:
                source_version_id = self.create_dataset_version(
                    dataset_id=source_dataset_id,
                    version_number="1.0",
                    description="Initial version"
                )
                
            if not derived_version_id:
                derived_version_id = self.create_dataset_version(
                    dataset_id=derived_dataset_id,
                    version_number="1.0",
                    description="Initial version"
                )
        
        # Now create the transformation record
        transformation_id = self.create_data_transformation(
            input_dataset_version_id=source_version_id,
            output_dataset_version_id=derived_version_id,
            transformation_type=DataTransformationType.OTHER,  # Use OTHER since there's no CUSTOM type
            name="Dataset Derivation",
            description=transformation
        )
        
        return transformation_id
    
    def list_datasets(
        self, 
        format: Optional[Union[DatasetFormat, str]] = None, 
        storage_type: Optional[Union[DatasetStorageType, str]] = None,
        tags: Optional[Set[str]] = None
    ) -> List[Dataset]:
        """
        List datasets with optional filtering.
        
        Args:
            format: Filter by dataset format
            storage_type: Filter by storage type
            tags: Filter by tags (datasets must have all specified tags)
            
        Returns:
            List[Dataset]: List of datasets matching the criteria
        """
        # Get unfiltered list from storage
        datasets = self._storage.list_datasets(None, None)
        
        # Apply filters in memory
        if format:
            format_value = format.value if isinstance(format, DatasetFormat) else format
            datasets = [d for d in datasets if d.format.value == format_value]
            
        if storage_type:
            storage_type_value = storage_type.value if isinstance(storage_type, DatasetStorageType) else storage_type
            datasets = [d for d in datasets if d.storage_type.value == storage_type_value]
            
        if tags:
            datasets = [d for d in datasets if all(tag in d.tags for tag in tags)]
            
        return datasets
    
    def add_dataset_tag(self, dataset_id: UUID, tag: str) -> bool:
        """
        Add a tag to a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            tag: The tag to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        dataset.add_tag(tag)
        return self._storage.update_dataset(dataset)
        
    def add_tag_to_dataset(self, dataset_id: UUID, tag: str) -> bool:
        """
        Alias for add_dataset_tag for backward compatibility.
        
        Args:
            dataset_id: The ID of the dataset
            tag: The tag to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        return self.add_dataset_tag(dataset_id, tag)
    
    def remove_tag_from_dataset(self, dataset_id: UUID, tag: str) -> bool:
        """
        Remove a tag from a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            tag: The tag to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        dataset.remove_tag(tag)
        return self._storage.update_dataset(dataset)
        
    def remove_dataset_tag(self, dataset_id: UUID, tag: str) -> bool:
        """
        Alias for remove_tag_from_dataset for API consistency.
        
        Args:
            dataset_id: The ID of the dataset
            tag: The tag to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        return self.remove_tag_from_dataset(dataset_id, tag)
    
    def update_dataset_metadata(
        self, dataset_id: UUID, key: str, value: Union[str, int, float, bool, list, dict]
    ) -> bool:
        """
        Update a custom metadata field for a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            key: The metadata key
            value: The metadata value
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        dataset.update_custom_metadata(key, value)
        return self._storage.update_dataset(dataset)
        
    def update_dataset_custom_metadata(
        self, dataset_id: UUID, key: str, value: Union[str, int, float, bool, list, dict]
    ) -> bool:
        """
        Alias for update_dataset_metadata for API consistency.
        
        Args:
            dataset_id: The ID of the dataset
            key: The metadata key
            value: The metadata value
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        return self.update_dataset_metadata(dataset_id, key, value)
        
    def remove_dataset_custom_metadata(self, dataset_id: UUID, key: str) -> bool:
        """
        Remove a custom metadata field from a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            key: The metadata key to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        if key in dataset.custom_metadata:
            result = dataset.remove_custom_metadata(key)
            if result:
                return self._storage.update_dataset(dataset)
        return False
    
    # Dataset version operations
    
    def create_dataset_version(
        self,
        dataset_id: str,
        version_number: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        creator: Optional[str] = None,
        hash: Optional[str] = None,
        size_bytes: Optional[int] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        schema: Optional[Dict[str, str]] = None,
        parent_version_id: Optional[str] = None,
        custom_metadata: Optional[Dict[str, Union[str, int, float, bool, list, dict]]] = None,
    ) -> str:
        """
        Create a new version of a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            version_number: Version number or identifier
            description: Version description
            location: Path or URL to this specific version
            creator: Who created this version
            hash: Content hash for verification
            size_bytes: Size in bytes
            row_count: Number of rows
            column_count: Number of columns
            schema: Data schema (column name -> data type)
            parent_version_id: ID of the parent version
            custom_metadata: Custom metadata fields
            
        Returns:
            UUID: The ID of the created version
            
        Raises:
            ValueError: If dataset or parent version doesn't exist
        """
        # Check if dataset exists
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        # Check if parent version exists
        if parent_version_id:
            parent_version = self._storage.get_dataset_version(parent_version_id)
            if not parent_version:
                raise ValueError(f"Parent version with ID {parent_version_id} does not exist")
            
            # Ensure parent version belongs to the same dataset
            if parent_version.dataset_id != dataset_id:
                raise ValueError("Parent version belongs to a different dataset")
        
        # Create version
        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number=version_number,
            description=description,
            location=location or dataset.location,
            creator=creator,
            hash=hash,
            size_bytes=size_bytes,
            row_count=row_count,
            column_count=column_count,
            schema=schema or {},
            parent_version_id=parent_version_id,
            custom_metadata=custom_metadata or {},
        )
        
        # Save version
        return self._storage.create_dataset_version(version)
    
    def get_dataset_version(self, version_id: str) -> Optional[DatasetVersion]:
        """
        Retrieve a dataset version by ID.
        
        Args:
            version_id: The ID of the version to retrieve
            
        Returns:
            Optional[DatasetVersion]: The version if found, None otherwise
        """
        return self._storage.get_dataset_version(version_id)
    
    def update_dataset_version(
        self,
        version_id: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        hash: Optional[str] = None,
        size_bytes: Optional[int] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        schema: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Update an existing dataset version.
        
        Args:
            version_id: The ID of the version to update
            description: New description
            location: New path or URL
            hash: New content hash
            size_bytes: New size in bytes
            row_count: New row count
            column_count: New column count
            schema: New schema
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If version doesn't exist
        """
        version = self._storage.get_dataset_version(version_id)
        if not version:
            raise ValueError(f"Dataset version with ID {version_id} does not exist")
        
        update_data = {}
        if description is not None:
            update_data["description"] = description
        if location is not None:
            update_data["location"] = location
        if hash is not None:
            update_data["hash"] = hash
        if size_bytes is not None:
            update_data["size_bytes"] = size_bytes
        if row_count is not None:
            update_data["row_count"] = row_count
        if column_count is not None:
            update_data["column_count"] = column_count
        if schema is not None:
            update_data["schema"] = schema
        
        version.update(**update_data)
        return self._storage.update_dataset_version(version)
    
    def delete_dataset_version(self, version_id: str) -> bool:
        """
        Delete a dataset version.
        
        Args:
            version_id: The ID of the version to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_dataset_version(version_id)
    
    def list_dataset_versions(
        self, dataset_id: str, include_lineage: bool = False
    ) -> List[DatasetVersion]:
        """
        List versions of a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            include_lineage: Whether to include full version lineage
            
        Returns:
            List[DatasetVersion]: List of dataset versions
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        return self._storage.list_dataset_versions(dataset_id, include_lineage)
        
    def get_latest_dataset_version(self, dataset_id: str) -> Optional[DatasetVersion]:
        """
        Get the latest version of a dataset (by creation timestamp).
        
        Args:
            dataset_id: The ID of the dataset
            
        Returns:
            Optional[DatasetVersion]: The latest version if found, None if no versions exist
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        # Get all versions for this dataset
        versions = self._storage.list_dataset_versions(dataset_id)
        
        if not versions:
            return None
        
        # Sort by creation time (newest first)
        sorted_versions = sorted(versions, key=lambda v: v.created_at, reverse=True)
        
        return sorted_versions[0]
        
    def get_latest_version(self, dataset_id: str) -> Optional[DatasetVersion]:
        """Alias for get_latest_dataset_version"""
        return self.get_latest_dataset_version(dataset_id)
        
    def get_dataset_derivations(self, dataset_id: str) -> List[DataTransformation]:
        """
        Get all data transformations where this dataset is used as input.
        
        Args:
            dataset_id: The ID of the dataset
            
        Returns:
            List[DataTransformation]: List of transformations where this dataset is the input
        """
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return []
            
        # Find all transformations for all versions of this dataset
        latest_version = self.get_latest_version(dataset_id)
        if not latest_version:
            return []
            
        # Get transformations where the latest version of this dataset is the input
        return self._storage.find_transformations_by_input_version(latest_version.id)
    
    def get_dataset_lineage(self, version_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get the complete version lineage for a dataset version.
        
        Args:
            version_id: The ID of the dataset version
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary with version ID keys and lineage information
            
        Raises:
            ValueError: If version doesn't exist
        """
        version = self._storage.get_dataset_version(version_id)
        if not version:
            raise ValueError(f"Dataset version with ID {version_id} does not exist")
        
        lineage = {}
        current = version
        
        # First, walk backwards to find the root
        ancestor_chain = []
        while current:
            ancestor_chain.insert(0, current)
            if current.parent_version_id:
                current = self._storage.get_dataset_version(current.parent_version_id)
            else:
                break
        
        # Add each version to the lineage dict with its transformations
        for i, v in enumerate(ancestor_chain):
            lineage[str(v.id)] = {
                "version": v,
                "input_transformations": [],
                "output_transformations": []
            }
            
            # Link with input transformations (except for first version)
            if i > 0:
                # Find transformations where this version is the output
                input_transformations = self._storage.find_transformations_by_output_version(v.id)
                lineage[str(v.id)]["input_transformations"] = input_transformations
            
            # Link with output transformations (except for last version)
            if i < len(ancestor_chain) - 1:
                # Find transformations where this version is the input
                output_transformations = self._storage.find_transformations_by_input_version(v.id)
                lineage[str(v.id)]["output_transformations"] = output_transformations
        
        return lineage
    
    def update_version_metadata(
        self, version_id: UUID, key: str, value: Union[str, int, float, bool, list, dict]
    ) -> bool:
        """
        Update a custom metadata field for a dataset version.
        
        Args:
            version_id: The ID of the dataset version
            key: The metadata key
            value: The metadata value
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If version doesn't exist
        """
        version = self._storage.get_dataset_version(version_id)
        if not version:
            raise ValueError(f"Dataset version with ID {version_id} does not exist")
        
        version.update_custom_metadata(key, value)
        return self._storage.update_dataset_version(version)
    
    # Data transformation operations
    
    def create_data_transformation(
        self,
        input_dataset_version_id: str,
        output_dataset_version_id: str,
        transformation_type: Union[DataTransformationType, str],
        name: str,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        code_reference: Optional[str] = None,
        execution_time_seconds: Optional[float] = None,
        tags: Optional[Set[str]] = None,
    ) -> str:
        """
        Create a new data transformation.
        
        Args:
            input_dataset_version_id: ID of the input dataset version
            output_dataset_version_id: ID of the output dataset version
            transformation_type: Type of transformation
            name: Name of the transformation
            description: Description of the transformation
            parameters: Parameters used in the transformation
            code_reference: Reference to the code that performed the transformation
            execution_time_seconds: How long the transformation took
            tags: Tags for categorization
            
        Returns:
            UUID: The ID of the created transformation
            
        Raises:
            ValueError: If versions don't exist
        """
        # Check if versions exist
        input_version = self._storage.get_dataset_version(input_dataset_version_id)
        if not input_version:
            raise ValueError(f"Input dataset version with ID {input_dataset_version_id} does not exist")
        
        output_version = self._storage.get_dataset_version(output_dataset_version_id)
        if not output_version:
            raise ValueError(f"Output dataset version with ID {output_dataset_version_id} does not exist")
        
        # Convert string enum to enum value if needed
        if isinstance(transformation_type, str):
            transformation_type = DataTransformationType(transformation_type)
        
        # Create transformation
        transformation = DataTransformation(
            type=transformation_type,
            name=name,
            description=description,
            input_dataset_version_id=input_dataset_version_id,
            output_dataset_version_id=output_dataset_version_id,
            parameters=parameters or {},
            code_reference=code_reference,
            execution_time_seconds=execution_time_seconds,
            tags=tags or set(),
        )
        
        # Save transformation
        return self._storage.create_data_transformation(transformation)
    
    def get_data_transformation(self, transformation_id: str) -> Optional[DataTransformation]:
        """
        Retrieve a data transformation by ID.
        
        Args:
            transformation_id: The ID of the transformation to retrieve
            
        Returns:
            Optional[DataTransformation]: The transformation if found, None otherwise
        """
        return self._storage.get_data_transformation(transformation_id)
    
    def update_data_transformation(
        self,
        transformation_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        code_reference: Optional[str] = None,
        execution_time_seconds: Optional[float] = None,
    ) -> bool:
        """
        Update an existing data transformation.
        
        Args:
            transformation_id: The ID of the transformation to update
            name: New name
            description: New description
            code_reference: New code reference
            execution_time_seconds: New execution time
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If transformation doesn't exist
        """
        transformation = self._storage.get_data_transformation(transformation_id)
        if not transformation:
            raise ValueError(f"Transformation with ID {transformation_id} does not exist")
        
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if code_reference is not None:
            update_data["code_reference"] = code_reference
        if execution_time_seconds is not None:
            update_data["execution_time_seconds"] = execution_time_seconds
        
        transformation.update(**update_data)
        return self._storage.update_data_transformation(transformation)
    
    def delete_data_transformation(self, transformation_id: str) -> bool:
        """
        Delete a data transformation.
        
        Args:
            transformation_id: The ID of the transformation to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_data_transformation(transformation_id)
    
    def list_transformations_for_dataset(self, dataset_id: str) -> List[DataTransformation]:
        """
        List all transformations related to a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            
        Returns:
            List[DataTransformation]: List of data transformations
            
        Raises:
            ValueError: If dataset doesn't exist
        """
        dataset = self._storage.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset with ID {dataset_id} does not exist")
        
        return self._storage.list_transformations_for_dataset(dataset_id)
        
    def list_data_transformations(
        self, 
        input_dataset_version_id: Optional[str] = None,
        output_dataset_version_id: Optional[str] = None,
        transformation_type: Optional[DataTransformationType] = None
    ) -> List[DataTransformation]:
        """
        List data transformations with optional filtering.
        
        Args:
            input_dataset_version_id: Filter by input dataset version
            output_dataset_version_id: Filter by output dataset version
            transformation_type: Filter by transformation type
            
        Returns:
            List[DataTransformation]: List of matching data transformations
        """
        # Get all transformations first
        if input_dataset_version_id:
            transformations = self._storage.find_transformations_by_input_version(input_dataset_version_id)
        elif output_dataset_version_id:
            transformations = self._storage.find_transformations_by_output_version(output_dataset_version_id)
        else:
            # Get all transformations (this might be inefficient, but required for tests)
            datasets = self._storage.list_datasets()
            transformations = []
            for dataset in datasets:
                transformations.extend(self._storage.list_transformations_for_dataset(dataset.id))
        
        # Filter by type if needed
        if transformation_type:
            transformations = [t for t in transformations if t.type == transformation_type]
            
        return transformations
    
    def get_transformation_lineage(self, version_id: str) -> List[DataTransformation]:
        """
        Get the complete transformation lineage for a dataset version.
        
        Args:
            version_id: The ID of the dataset version
            
        Returns:
            List[DataTransformation]: List of transformations in lineage order
            
        Raises:
            ValueError: If version doesn't exist
        """
        version = self._storage.get_dataset_version(version_id)
        if not version:
            raise ValueError(f"Dataset version with ID {version_id} does not exist")
        
        return self._storage.get_transformation_lineage(version_id)
    
    def add_tag_to_transformation(self, transformation_id: UUID, tag: str) -> bool:
        """
        Add a tag to a transformation.
        
        Args:
            transformation_id: The ID of the transformation
            tag: The tag to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If transformation doesn't exist
        """
        transformation = self._storage.get_data_transformation(transformation_id)
        if not transformation:
            raise ValueError(f"Transformation with ID {transformation_id} does not exist")
        
        transformation.add_tag(tag)
        return self._storage.update_data_transformation(transformation)
        
    def add_transformation_tag(self, transformation_id: UUID, tag: str) -> bool:
        """
        Alias for add_tag_to_transformation for API consistency.
        
        Args:
            transformation_id: The ID of the transformation
            tag: The tag to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If transformation doesn't exist
        """
        return self.add_tag_to_transformation(transformation_id, tag)
    
    def remove_tag_from_transformation(self, transformation_id: UUID, tag: str) -> bool:
        """
        Remove a tag from a transformation.
        
        Args:
            transformation_id: The ID of the transformation
            tag: The tag to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If transformation doesn't exist
        """
        transformation = self._storage.get_data_transformation(transformation_id)
        if not transformation:
            raise ValueError(f"Transformation with ID {transformation_id} does not exist")
        
        transformation.remove_tag(tag)
        return self._storage.update_data_transformation(transformation)
    
    def add_note_to_transformation(self, transformation_id: UUID, note: str) -> bool:
        """
        Add a note to a transformation.
        
        Args:
            transformation_id: The ID of the transformation
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If transformation doesn't exist
        """
        transformation = self._storage.get_data_transformation(transformation_id)
        if not transformation:
            raise ValueError(f"Transformation with ID {transformation_id} does not exist")
        
        transformation.add_note(note)
        return self._storage.update_data_transformation(transformation)
        
    def add_transformation_note(self, transformation_id: UUID, note: str) -> bool:
        """
        Alias for add_note_to_transformation for API consistency.
        
        Args:
            transformation_id: The ID of the transformation
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If transformation doesn't exist
        """
        return self.add_note_to_transformation(transformation_id, note)
    
    def update_transformation_parameter(
        self, transformation_id: UUID, key: str, value: Union[str, int, float, bool, list, dict]
    ) -> bool:
        """
        Update a transformation parameter.
        
        Args:
            transformation_id: The ID of the transformation
            key: The parameter key
            value: The parameter value
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If transformation doesn't exist
        """
        transformation = self._storage.get_data_transformation(transformation_id)
        if not transformation:
            raise ValueError(f"Transformation with ID {transformation_id} does not exist")
        
        transformation.update_parameter(key, value)
        return self._storage.update_data_transformation(transformation)
        
    def remove_transformation_parameter(self, transformation_id: UUID, key: str) -> bool:
        """
        Remove a parameter from a transformation.
        
        Args:
            transformation_id: The ID of the transformation
            key: The parameter key to remove
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If transformation doesn't exist
        """
        transformation = self._storage.get_data_transformation(transformation_id)
        if not transformation:
            raise ValueError(f"Transformation with ID {transformation_id} does not exist")
        
        result = transformation.remove_parameter(key)
        if result:
            return self._storage.update_data_transformation(transformation)
        return False
    
    # Task-Dataset link operations
    
    def link_task_to_dataset_version(
        self,
        task_id: str,
        dataset_version_id: str,
        usage_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        """
        Link a task to a dataset version.
        
        Args:
            task_id: The ID of the task
            dataset_version_id: The ID of the dataset version
            usage_type: How the dataset is used (input, output, reference, etc.)
            description: Description of the relationship
            
        Returns:
            UUID: The ID of the created link
            
        Raises:
            ValueError: If version doesn't exist
        """
        version = self._storage.get_dataset_version(dataset_version_id)
        if not version:
            raise ValueError(f"Dataset version with ID {dataset_version_id} does not exist")
        
        # Check if link already exists
        existing_versions = self._storage.get_dataset_versions_by_task(task_id)
        for v in existing_versions:
            if v.id == dataset_version_id:
                # Link already exists
                return '00000000-0000-0000-0000-000000000000'
        
        # Create the link
        link = TaskDatasetLink(
            task_id=task_id,
            dataset_version_id=dataset_version_id,
            usage_type=usage_type,
            description=description,
        )
        
        return self._storage.create_task_dataset_link(link)
    
    def get_task_dataset_link(self, link_id: str) -> Optional[TaskDatasetLink]:
        """
        Get a task-dataset link by ID.
        
        Args:
            link_id: The ID of the link
            
        Returns:
            Optional[TaskDatasetLink]: The link if found, None otherwise
        """
        return self._storage.get_task_dataset_link(link_id)
    
    def update_task_dataset_link(
        self,
        link_id: str,
        usage_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        Update a task-dataset link.
        
        Args:
            link_id: The ID of the link to update
            usage_type: New usage type
            description: New description
            
        Returns:
            bool: True if update successful, False otherwise
            
        Raises:
            ValueError: If link doesn't exist
        """
        link = self._storage.get_task_dataset_link(link_id)
        if not link:
            raise ValueError(f"Link with ID {link_id} does not exist")
        
        if usage_type is not None:
            link.usage_type = usage_type
        if description is not None:
            link.description = description
            
        return self._storage.update_task_dataset_link(link)
    
    def delete_task_dataset_link(self, link_id: str) -> bool:
        """
        Delete a task-dataset link.
        
        Args:
            link_id: The ID of the link to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        return self._storage.delete_task_dataset_link(link_id)
    
    def get_dataset_versions_by_task(self, task_id: str) -> List[DatasetVersion]:
        """
        Get all dataset versions associated with a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[DatasetVersion]: List of associated dataset versions
        """
        return self._storage.get_dataset_versions_by_task(task_id)
    
    def get_tasks_by_dataset_version(self, version_id: str) -> List[str]:
        """
        Get all task IDs associated with a dataset version.
        
        Args:
            version_id: The ID of the dataset version
            
        Returns:
            List[str]: List of associated task IDs
        """
        return self._storage.get_tasks_by_dataset_version(version_id)
    
    def get_links_by_task(self, task_id: str) -> List[TaskDatasetLink]:
        """
        Get all dataset links for a task.
        
        Args:
            task_id: The ID of the task
            
        Returns:
            List[TaskDatasetLink]: List of links
        """
        return self._storage.get_links_by_task(task_id)
    
    def add_note_to_link(self, link_id: UUID, note: str) -> bool:
        """
        Add a note to a task-dataset link.
        
        Args:
            link_id: The ID of the link
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If link doesn't exist
        """
        link = self._storage.get_task_dataset_link(link_id)
        if not link:
            raise ValueError(f"Link with ID {link_id} does not exist")
        
        link.add_note(note)
        return self._storage.update_task_dataset_link(link)
        
    def add_note_to_task_dataset_link(self, task_id: str, version_id: str, note: str) -> bool:
        """
        Add a note to the link between a task and a dataset version.
        
        Args:
            task_id: The ID of the task
            version_id: The ID of the dataset version
            note: The note to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Find the link
        links = self._storage.get_links_by_task(task_id)
        for link in links:
            if link.dataset_version_id == version_id:
                link.add_note(note)
                return self._storage.update_task_dataset_link(link)
        
        return False