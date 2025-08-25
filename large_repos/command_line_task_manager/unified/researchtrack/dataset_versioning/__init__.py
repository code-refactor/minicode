"""
Dataset versioning module for tracking datasets, their versions, and transformations.

This module allows researchers to keep track of different versions of their datasets
and the transformations applied to create new versions.
"""

from .models import (
    Dataset, 
    DatasetVersion, 
    DataTransformation, 
    TaskDatasetLink, 
    DatasetFormat,
    DatasetStorageType,
    DataTransformationType
)
from .service import DatasetVersioningService
from .storage import DatasetStorageInterface, InMemoryDatasetStorage
from typing import Dict, List, Optional, Set, Union, Any
from uuid import UUID


class DatasetService:
    """
    Compatibility wrapper for DatasetVersioningService.
    
    This class provides a simplified API that matches the expectations of integration tests,
    particularly returning objects with 'id' attributes rather than UUIDs directly.
    """
    
    def __init__(self, storage: DatasetStorageInterface):
        """
        Initialize the dataset service with storage.
        
        Args:
            storage: An implementation of DatasetStorageInterface
        """
        self._versioning_service = DatasetVersioningService(storage)
        self._storage = storage
    
    def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        format: Union[DatasetFormat, str] = DatasetFormat.CSV,
        storage_type: Union[DatasetStorageType, str] = DatasetStorageType.LOCAL,
        location: str = "",
        **kwargs
    ) -> Dataset:
        """
        Create a new dataset.
        
        Args:
            name: Dataset name
            description: Dataset description
            format: Dataset format
            storage_type: Type of storage
            location: Path or URL to the dataset
            **kwargs: Additional dataset attributes
            
        Returns:
            Dataset: The created dataset object
        """
        dataset_id = self._versioning_service.create_dataset(
            name=name,
            description=description,
            format=format,
            storage_type=storage_type,
            location=location,
            **kwargs
        )
        
        # Return the dataset object instead of just the ID
        return self._versioning_service.get_dataset(dataset_id)
    
    def get_dataset(self, dataset_id: UUID) -> Optional[Dataset]:
        """
        Retrieve a dataset by ID.
        
        Args:
            dataset_id: The ID of the dataset to retrieve
            
        Returns:
            Optional[Dataset]: The dataset if found, None otherwise
        """
        dataset = self._versioning_service.get_dataset(dataset_id)
        
        # Add versions to dataset
        if dataset:
            setattr(dataset, 'versions', self._versioning_service.list_dataset_versions(dataset_id))
            
        return dataset
    
    def create_version(
        self,
        dataset_id: UUID,
        version_number: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        parent_version_id: Optional[UUID] = None,
        **kwargs
    ) -> DatasetVersion:
        """
        Create a new version of a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            version_number: Version number or identifier
            description: Version description
            location: Path or URL to this specific version
            parent_version_id: ID of the parent version
            **kwargs: Additional version attributes
            
        Returns:
            DatasetVersion: The created dataset version object
        """
        version_id = self._versioning_service.create_dataset_version(
            dataset_id=dataset_id,
            version_number=version_number,
            description=description,
            location=location,
            parent_version_id=parent_version_id,
            **kwargs
        )
        
        # Return the version object instead of just the ID
        return self._versioning_service.get_dataset_version(version_id)
    
    def get_dataset_version(self, version_id: UUID) -> Optional[DatasetVersion]:
        """
        Retrieve a dataset version by ID.
        
        Args:
            version_id: The ID of the version to retrieve
            
        Returns:
            Optional[DatasetVersion]: The version if found, None otherwise
        """
        return self._versioning_service.get_dataset_version(version_id)
    
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
            tags: Filter by tags
            
        Returns:
            List[Dataset]: List of datasets matching the criteria
        """
        return self._versioning_service.list_datasets(format, storage_type, tags)
    
    def list_dataset_versions(self, dataset_id: UUID) -> List[DatasetVersion]:
        """
        List versions of a dataset.
        
        Args:
            dataset_id: The ID of the dataset
            
        Returns:
            List[DatasetVersion]: List of dataset versions
        """
        return self._versioning_service.list_dataset_versions(dataset_id)
    
    def add_derivation(
        self,
        derived_dataset_id: UUID,
        source_dataset_id: UUID,
        transformation: str
    ) -> UUID:
        """
        Create a relationship between a derived dataset and its source.
        
        Args:
            derived_dataset_id: The ID of the derived dataset
            source_dataset_id: The ID of the source dataset
            transformation: Description of the transformation
            
        Returns:
            UUID: The ID of the created transformation record
        """
        # Delegate to the versioning service
        return self._versioning_service.add_derivation(
            derived_dataset_id=derived_dataset_id,
            source_dataset_id=source_dataset_id,
            transformation=transformation
        )
    
    def get_dataset_derivations(self, dataset_id: UUID) -> List[DataTransformation]:
        """
        Get all derivations for a dataset (where this dataset is used as input).
        
        Args:
            dataset_id: The ID of the dataset
            
        Returns:
            List[DataTransformation]: List of transformations where this dataset is the input
        """
        return self._versioning_service.get_dataset_derivations(dataset_id)
        
    # Add any other methods needed for integration tests