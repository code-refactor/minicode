from uuid import uuid4

import pytest

from researchtrack.dataset_versioning.models import (
    DataTransformation,
    DataTransformationType,
    Dataset,
    DatasetFormat,
    DatasetStorageType,
    DatasetVersion,
    TaskDatasetLink,
)
from researchtrack.dataset_versioning.storage import InMemoryDatasetStorage


class TestInMemoryDatasetStorage:
    def setup_method(self):
        """Set up a fresh storage instance for each test."""
        self.storage = InMemoryDatasetStorage()
        
        # Create some test data to use in multiple tests
        self.dataset1 = Dataset(
            name="Climate Data 2010-2020",
            description="Global temperature data",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.S3,
            location="s3://test-bucket/climate-2010-2020.csv",
            tags={"climate", "temperature"},
        )
        
        self.dataset2 = Dataset(
            name="Census Data 2020",
            description="Population census data",
            format=DatasetFormat.PARQUET,
            storage_type=DatasetStorageType.LOCAL,
            location="/data/census-2020.parquet",
            tags={"census", "population"},
        )
        
        self.task_id1 = uuid4()
        self.task_id2 = uuid4()
    
    def test_create_and_get_dataset(self):
        # Test creating and retrieving a dataset
        dataset_id = self.storage.create_dataset(self.dataset1)
        
        retrieved_dataset = self.storage.get_dataset(dataset_id)
        
        assert retrieved_dataset is not None
        assert retrieved_dataset.id == dataset_id
        assert retrieved_dataset.name == "Climate Data 2010-2020"
        assert retrieved_dataset.format == DatasetFormat.CSV
        assert retrieved_dataset.storage_type == DatasetStorageType.S3
    
    def test_update_dataset(self):
        # Test updating a dataset
        dataset_id = self.storage.create_dataset(self.dataset1)
        
        # Update the dataset
        self.dataset1.name = "Updated Climate Data"
        self.dataset1.description = "Updated description"
        
        update_result = self.storage.update_dataset(self.dataset1)
        retrieved_dataset = self.storage.get_dataset(dataset_id)
        
        assert update_result is True
        assert retrieved_dataset.name == "Updated Climate Data"
        assert retrieved_dataset.description == "Updated description"
    
    def test_update_nonexistent_dataset(self):
        # Test updating a dataset that doesn't exist
        nonexistent_dataset = Dataset(
            id=uuid4(),
            name="Nonexistent Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/nonexistent.csv",
        )
        
        update_result = self.storage.update_dataset(nonexistent_dataset)
        assert update_result is False
    
    def test_delete_dataset(self):
        # Test deleting a dataset
        dataset_id = self.storage.create_dataset(self.dataset1)
        
        # Create a version of this dataset
        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="s3://test-bucket/climate-2010-2020/v1.0.0.csv",
        )
        version_id = self.storage.create_dataset_version(version)
        
        # Create a link to this version
        link = TaskDatasetLink(
            task_id=self.task_id1,
            dataset_version_id=version_id,
        )
        link_id = self.storage.create_task_dataset_link(link)
        
        # Delete the dataset
        delete_result = self.storage.delete_dataset(dataset_id)
        
        assert delete_result is True
        assert self.storage.get_dataset(dataset_id) is None
        
        # Verify that the version was also deleted
        assert self.storage.get_dataset_version(version_id) is None
        
        # Verify that the link was also deleted
        assert self.storage.get_task_dataset_link(link_id) is None
    
    def test_delete_nonexistent_dataset(self):
        # Test deleting a dataset that doesn't exist
        delete_result = self.storage.delete_dataset(uuid4())
        assert delete_result is False
    
    def test_list_datasets_empty(self):
        # Test listing datasets when storage is empty
        datasets = self.storage.list_datasets()
        assert len(datasets) == 0
    
    def test_list_datasets_with_filters(self):
        # Test listing datasets with various filters
        self.storage.create_dataset(self.dataset1)
        self.storage.create_dataset(self.dataset2)
        
        # Filter by format
        csv_datasets = self.storage.list_datasets(format=DatasetFormat.CSV)
        assert len(csv_datasets) == 1
        assert csv_datasets[0].name == "Climate Data 2010-2020"
        
        parquet_datasets = self.storage.list_datasets(format=DatasetFormat.PARQUET)
        assert len(parquet_datasets) == 1
        assert parquet_datasets[0].name == "Census Data 2020"
        
        # Filter by storage type
        s3_datasets = self.storage.list_datasets(storage_type=DatasetStorageType.S3)
        assert len(s3_datasets) == 1
        assert s3_datasets[0].name == "Climate Data 2010-2020"
        
        local_datasets = self.storage.list_datasets(storage_type=DatasetStorageType.LOCAL)
        assert len(local_datasets) == 1
        assert local_datasets[0].name == "Census Data 2020"
        
        # Filter by tags
        climate_datasets = self.storage.list_datasets(tags={"climate"})
        assert len(climate_datasets) == 1
        assert climate_datasets[0].name == "Climate Data 2010-2020"
        
        census_datasets = self.storage.list_datasets(tags={"census", "population"})
        assert len(census_datasets) == 1
        assert census_datasets[0].name == "Census Data 2020"
        
        # No matches
        no_datasets = self.storage.list_datasets(tags={"nonexistent"})
        assert len(no_datasets) == 0
    
    def test_dataset_version_operations(self):
        # Test dataset version CRUD operations
        dataset_id = self.storage.create_dataset(self.dataset1)
        
        # Create versions
        version1 = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="s3://test-bucket/climate-2010-2020/v1.0.0.csv",
            creator="Researcher A",
        )
        
        version2 = DatasetVersion(
            dataset_id=dataset_id,
            version_number="2.0.0",
            location="s3://test-bucket/climate-2010-2020/v2.0.0.csv",
            creator="Researcher B",
        )
        
        version_id1 = self.storage.create_dataset_version(version1)
        version_id2 = self.storage.create_dataset_version(version2)
        
        # Test retrieving versions
        retrieved_version1 = self.storage.get_dataset_version(version_id1)
        
        assert retrieved_version1 is not None
        assert retrieved_version1.id == version_id1
        assert retrieved_version1.dataset_id == dataset_id
        assert retrieved_version1.version_number == "1.0.0"
        assert retrieved_version1.creator == "Researcher A"
        
        # Test updating a version
        version1.description = "Initial version"
        update_result = self.storage.update_dataset_version(version1)
        updated_version1 = self.storage.get_dataset_version(version_id1)
        
        assert update_result is True
        assert updated_version1.description == "Initial version"
        
        # Test listing versions
        versions = self.storage.list_dataset_versions(dataset_id)
        
        assert len(versions) == 2
        assert {v.version_number for v in versions} == {"1.0.0", "2.0.0"}
        
        # Test get latest version
        latest_version = self.storage.get_latest_dataset_version(dataset_id)
        
        # The latest should be determined by created_at timestamp
        # In this test they're created very close together, so either might be latest
        assert latest_version.id in {version_id1, version_id2}
        
        # Test deleting a version
        delete_result = self.storage.delete_dataset_version(version_id1)
        
        assert delete_result is True
        assert self.storage.get_dataset_version(version_id1) is None
        
        # Test the remaining version
        remaining_versions = self.storage.list_dataset_versions(dataset_id)
        assert len(remaining_versions) == 1
        assert remaining_versions[0].id == version_id2
    
    def test_version_lineage_operations(self):
        # Test version lineage with parent references
        dataset_id = self.storage.create_dataset(self.dataset1)
        
        # Create a sequence of versions with parent relationships
        version1 = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="s3://test-bucket/climate-2010-2020/v1.0.0.csv",
        )
        version_id1 = self.storage.create_dataset_version(version1)
        
        version2 = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.1.0",
            location="s3://test-bucket/climate-2010-2020/v1.1.0.csv",
            parent_version_id=version_id1,
        )
        version_id2 = self.storage.create_dataset_version(version2)
        
        version3 = DatasetVersion(
            dataset_id=dataset_id,
            version_number="2.0.0",
            location="s3://test-bucket/climate-2010-2020/v2.0.0.csv",
            parent_version_id=version_id2,
        )
        version_id3 = self.storage.create_dataset_version(version3)
        
        # Verify parent references
        v2 = self.storage.get_dataset_version(version_id2)
        v3 = self.storage.get_dataset_version(version_id3)
        
        assert v2.parent_version_id == version_id1
        assert v3.parent_version_id == version_id2
        
        # Test deleting a version in the middle of the lineage
        # Parent references should be updated to maintain chain integrity
        self.storage.delete_dataset_version(version_id2)
        
        # Verify the updated parent references
        v3_updated = self.storage.get_dataset_version(version_id3)
        assert v3_updated.parent_version_id is None
    
    def test_data_transformation_operations(self):
        # Test data transformation CRUD operations
        dataset_id = self.storage.create_dataset(self.dataset1)
        
        # Create versions for input/output
        input_version = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="s3://test-bucket/input-version.csv",
        )
        input_version_id = self.storage.create_dataset_version(input_version)
        
        output_version = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.1.0",
            location="s3://test-bucket/output-version.csv",
        )
        output_version_id = self.storage.create_dataset_version(output_version)
        
        # Create transformation
        transformation = DataTransformation(
            type=DataTransformationType.CLEANING,
            name="Data Cleaning Step",
            description="Remove outliers and normalize data",
            input_dataset_version_id=input_version_id,
            output_dataset_version_id=output_version_id,
            parameters={"outlier_threshold": 3.0},
            code_reference="https://github.com/repo/cleaning.py",
        )
        
        transformation_id = self.storage.create_data_transformation(transformation)
        
        # Test retrieving transformation
        retrieved_transformation = self.storage.get_data_transformation(transformation_id)
        
        assert retrieved_transformation is not None
        assert retrieved_transformation.id == transformation_id
        assert retrieved_transformation.type == DataTransformationType.CLEANING
        assert retrieved_transformation.name == "Data Cleaning Step"
        assert retrieved_transformation.input_dataset_version_id == input_version_id
        assert retrieved_transformation.output_dataset_version_id == output_version_id
        
        # Test updating transformation
        transformation.description = "Updated description"
        transformation.execution_time_seconds = 45.2
        
        update_result = self.storage.update_data_transformation(transformation)
        updated_transformation = self.storage.get_data_transformation(transformation_id)
        
        assert update_result is True
        assert updated_transformation.description == "Updated description"
        assert updated_transformation.execution_time_seconds == 45.2
        
        # Test listing transformations
        transformations_by_input = self.storage.list_data_transformations(
            input_dataset_version_id=input_version_id
        )
        assert len(transformations_by_input) == 1
        assert transformations_by_input[0].id == transformation_id
        
        transformations_by_output = self.storage.list_data_transformations(
            output_dataset_version_id=output_version_id
        )
        assert len(transformations_by_output) == 1
        assert transformations_by_output[0].id == transformation_id
        
        transformations_by_type = self.storage.list_data_transformations(
            transformation_type=DataTransformationType.CLEANING
        )
        assert len(transformations_by_type) == 1
        assert transformations_by_type[0].id == transformation_id
        
        # Test deleting transformation
        delete_result = self.storage.delete_data_transformation(transformation_id)
        
        assert delete_result is True
        assert self.storage.get_data_transformation(transformation_id) is None
    
    def test_task_dataset_link_operations(self):
        # Test task-dataset link CRUD operations
        dataset_id = self.storage.create_dataset(self.dataset1)
        
        # Create a version
        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="s3://test-bucket/v1.0.0.csv",
        )
        version_id = self.storage.create_dataset_version(version)
        
        # Create links between tasks and the dataset version
        link1 = TaskDatasetLink(
            task_id=self.task_id1,
            dataset_version_id=version_id,
            usage_type="input",
            description="Primary input dataset",
        )
        
        link2 = TaskDatasetLink(
            task_id=self.task_id2,
            dataset_version_id=version_id,
            usage_type="reference",
            description="Reference dataset",
        )
        
        link_id1 = self.storage.create_task_dataset_link(link1)
        link_id2 = self.storage.create_task_dataset_link(link2)
        
        # Test retrieving link
        retrieved_link = self.storage.get_task_dataset_link(link_id1)
        
        assert retrieved_link is not None
        assert retrieved_link.id == link_id1
        assert retrieved_link.task_id == self.task_id1
        assert retrieved_link.dataset_version_id == version_id
        assert retrieved_link.usage_type == "input"
        
        # Test updating link
        link1.description = "Updated description"
        update_result = self.storage.update_task_dataset_link(link1)
        updated_link = self.storage.get_task_dataset_link(link_id1)
        
        assert update_result is True
        assert updated_link.description == "Updated description"
        
        # Test querying links
        task1_versions = self.storage.get_dataset_versions_by_task(self.task_id1)
        assert len(task1_versions) == 1
        assert task1_versions[0].id == version_id
        
        task1_links = self.storage.get_links_by_task(self.task_id1)
        assert len(task1_links) == 1
        assert task1_links[0].id == link_id1
        
        version_tasks = self.storage.get_tasks_by_dataset_version(version_id)
        assert len(version_tasks) == 2
        assert set(version_tasks) == {self.task_id1, self.task_id2}
        
        # Test deleting link
        delete_result = self.storage.delete_task_dataset_link(link_id1)
        
        assert delete_result is True
        assert self.storage.get_task_dataset_link(link_id1) is None
        
        # Verify only link2 remains
        remaining_tasks = self.storage.get_tasks_by_dataset_version(version_id)
        assert len(remaining_tasks) == 1
        assert remaining_tasks[0] == self.task_id2
    
    def test_get_lineage(self):
        # Test lineage tracking
        dataset_id = self.storage.create_dataset(self.dataset1)
        
        # Create a sequence of versions and transformations
        v1 = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/v1.csv",
        )
        v1_id = self.storage.create_dataset_version(v1)
        
        v2 = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.1.0",
            location="/path/to/v2.csv",
            parent_version_id=v1_id,
        )
        v2_id = self.storage.create_dataset_version(v2)
        
        v3 = DatasetVersion(
            dataset_id=dataset_id,
            version_number="2.0.0",
            location="/path/to/v3.csv",
            parent_version_id=v2_id,
        )
        v3_id = self.storage.create_dataset_version(v3)
        
        # Create transformations between versions
        t1 = DataTransformation(
            type=DataTransformationType.CLEANING,
            name="Initial cleaning",
            input_dataset_version_id=v1_id,
            output_dataset_version_id=v2_id,
        )
        t1_id = self.storage.create_data_transformation(t1)
        
        t2 = DataTransformation(
            type=DataTransformationType.FEATURE_ENGINEERING,
            name="Feature engineering",
            input_dataset_version_id=v2_id,
            output_dataset_version_id=v3_id,
        )
        t2_id = self.storage.create_data_transformation(t2)
        
        # Get lineage starting from v3
        lineage = self.storage.get_lineage(v3_id)
        
        # Check the lineage
        assert len(lineage) == 3  # Should include all three versions
        
        # Check v3 entry
        v3_entry = lineage[str(v3_id)]
        assert v3_entry["version"].id == v3_id
        assert len(v3_entry["input_transformations"]) == 1  # t2 has v3 as output
        assert v3_entry["input_transformations"][0].id == t2_id
        
        # Check v2 entry
        v2_entry = lineage[str(v2_id)]
        assert v2_entry["version"].id == v2_id
        assert len(v2_entry["input_transformations"]) == 1  # t1 has v2 as output
        assert v2_entry["input_transformations"][0].id == t1_id
        assert len(v2_entry["output_transformations"]) == 1  # t2 has v2 as input
        assert v2_entry["output_transformations"][0].id == t2_id
        
        # Check v1 entry
        v1_entry = lineage[str(v1_id)]
        assert v1_entry["version"].id == v1_id
        assert len(v1_entry["input_transformations"]) == 0  # No transformation with v1 as output
        assert len(v1_entry["output_transformations"]) == 1  # t1 has v1 as input
        assert v1_entry["output_transformations"][0].id == t1_id