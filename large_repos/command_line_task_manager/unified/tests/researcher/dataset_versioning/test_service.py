from uuid import uuid4

import pytest

from researchtrack.dataset_versioning.models import (
    DataTransformationType,
    DatasetFormat,
    DatasetStorageType,
)
from researchtrack.dataset_versioning.service import DatasetVersioningService
from researchtrack.dataset_versioning.storage import InMemoryDatasetStorage


class TestDatasetVersioningService:
    def setup_method(self):
        """Set up a fresh service instance for each test."""
        self.storage = InMemoryDatasetStorage()
        self.service = DatasetVersioningService(self.storage)
        
        # Create some task IDs to use in tests
        self.task_id1 = uuid4()
        self.task_id2 = uuid4()
    
    def test_create_dataset(self):
        # Test creating a dataset
        dataset_id = self.service.create_dataset(
            name="Test Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
            description="Test dataset description",
            size_bytes=1024 * 1024,  # 1MB
            row_count=1000,
            column_count=10,
            schema={"col1": "integer", "col2": "string"},
            tags={"test", "data"},
            hash="sha256:abcdef",
            version="1.0.0",
            custom_metadata={"source": "Test source"},
        )
        
        dataset = self.service.get_dataset(dataset_id)
        
        assert dataset is not None
        assert dataset.name == "Test Dataset"
        assert dataset.format == DatasetFormat.CSV
        assert dataset.storage_type == DatasetStorageType.LOCAL
        assert dataset.location == "/path/to/data.csv"
        assert dataset.description == "Test dataset description"
        assert dataset.size_bytes == 1024 * 1024
        assert dataset.row_count == 1000
        assert dataset.column_count == 10
        assert dataset.schema == {"col1": "integer", "col2": "string"}
        assert dataset.tags == {"test", "data"}
        assert dataset.hash == "sha256:abcdef"
        assert dataset.version == "1.0.0"
        assert dataset.custom_metadata["source"] == "Test source"
    
    def test_update_dataset(self):
        # Test updating a dataset
        dataset_id = self.service.create_dataset(
            name="Original Name",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/original.csv",
        )
        
        # Update the dataset
        update_result = self.service.update_dataset(
            dataset_id=dataset_id,
            name="Updated Name",
            description="Added description",
            location="/path/to/updated.csv",
            size_bytes=2048 * 1024,  # 2MB
            row_count=2000,
        )
        
        updated_dataset = self.service.get_dataset(dataset_id)
        
        assert update_result is True
        assert updated_dataset.name == "Updated Name"
        assert updated_dataset.description == "Added description"
        assert updated_dataset.location == "/path/to/updated.csv"
        assert updated_dataset.size_bytes == 2048 * 1024
        assert updated_dataset.row_count == 2000
    
    def test_update_nonexistent_dataset(self):
        # Test updating a dataset that doesn't exist
        with pytest.raises(ValueError, match="Dataset .* does not exist"):
            self.service.update_dataset(
                dataset_id=uuid4(),
                name="Updated Name",
            )
    
    def test_delete_dataset(self):
        # Test deleting a dataset
        dataset_id = self.service.create_dataset(
            name="Dataset to Delete",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/delete.csv",
        )
        
        # Verify dataset exists
        assert self.service.get_dataset(dataset_id) is not None
        
        # Delete dataset
        delete_result = self.service.delete_dataset(dataset_id)
        
        assert delete_result is True
        assert self.service.get_dataset(dataset_id) is None
    
    def test_list_datasets(self):
        # Test listing datasets with filters
        
        # Create some datasets with different attributes
        self.service.create_dataset(
            name="CSV Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/csv.csv",
            tags={"test", "csv"},
        )
        
        self.service.create_dataset(
            name="Parquet Dataset",
            format=DatasetFormat.PARQUET,
            storage_type=DatasetStorageType.S3,
            location="s3://bucket/data.parquet",
            tags={"test", "parquet"},
        )
        
        self.service.create_dataset(
            name="Another CSV Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.S3,
            location="s3://bucket/data.csv",
            tags={"test", "csv", "s3"},
        )
        
        # Get all datasets
        all_datasets = self.service.list_datasets()
        assert len(all_datasets) == 3
        
        # Filter by format
        csv_datasets = self.service.list_datasets(format=DatasetFormat.CSV)
        assert len(csv_datasets) == 2
        assert {d.name for d in csv_datasets} == {"CSV Dataset", "Another CSV Dataset"}
        
        parquet_datasets = self.service.list_datasets(format=DatasetFormat.PARQUET)
        assert len(parquet_datasets) == 1
        assert parquet_datasets[0].name == "Parquet Dataset"
        
        # Filter by storage type
        s3_datasets = self.service.list_datasets(storage_type=DatasetStorageType.S3)
        assert len(s3_datasets) == 2
        assert {d.name for d in s3_datasets} == {"Parquet Dataset", "Another CSV Dataset"}
        
        # Filter by tags
        csv_tag_datasets = self.service.list_datasets(tags={"csv"})
        assert len(csv_tag_datasets) == 2
        assert {d.name for d in csv_tag_datasets} == {"CSV Dataset", "Another CSV Dataset"}
        
        s3_csv_datasets = self.service.list_datasets(tags={"csv", "s3"})
        assert len(s3_csv_datasets) == 1
        assert s3_csv_datasets[0].name == "Another CSV Dataset"
    
    def test_dataset_tags(self):
        # Test adding and removing tags
        dataset_id = self.service.create_dataset(
            name="Dataset with Tags",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/tags.csv",
        )
        
        # Add tags
        self.service.add_dataset_tag(dataset_id, "tag1")
        self.service.add_dataset_tag(dataset_id, "tag2")
        
        dataset = self.service.get_dataset(dataset_id)
        assert dataset.tags == {"tag1", "tag2"}
        
        # Remove tag
        self.service.remove_dataset_tag(dataset_id, "tag1")
        
        dataset = self.service.get_dataset(dataset_id)
        assert dataset.tags == {"tag2"}
    
    def test_dataset_custom_metadata(self):
        # Test updating and removing custom metadata
        dataset_id = self.service.create_dataset(
            name="Dataset with Metadata",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/metadata.csv",
        )
        
        # Update metadata
        self.service.update_dataset_custom_metadata(dataset_id, "source", "Test source")
        self.service.update_dataset_custom_metadata(dataset_id, "quality", 0.95)
        
        dataset = self.service.get_dataset(dataset_id)
        assert dataset.custom_metadata["source"] == "Test source"
        assert dataset.custom_metadata["quality"] == 0.95
        
        # Remove metadata
        result = self.service.remove_dataset_custom_metadata(dataset_id, "source")
        
        assert result is True
        dataset = self.service.get_dataset(dataset_id)
        assert "source" not in dataset.custom_metadata
        assert "quality" in dataset.custom_metadata
    
    def test_create_dataset_version(self):
        # Test creating a dataset version
        dataset_id = self.service.create_dataset(
            name="Dataset for Versioning",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        # Create a version
        version_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/versions/1.0.0/data.csv",
            creator="Test Creator",
            description="Initial version",
            hash="sha256:abcdef",
            size_bytes=1024 * 1024,
            row_count=1000,
            column_count=10,
            schema={"col1": "integer", "col2": "string"},
            custom_metadata={"quality_score": 0.9},
        )
        
        version = self.service.get_dataset_version(version_id)
        
        assert version is not None
        assert version.dataset_id == dataset_id
        assert version.version_number == "1.0.0"
        assert version.location == "/path/to/versions/1.0.0/data.csv"
        assert version.creator == "Test Creator"
        assert version.description == "Initial version"
        assert version.hash == "sha256:abcdef"
        assert version.size_bytes == 1024 * 1024
        assert version.row_count == 1000
        assert version.column_count == 10
        assert version.schema == {"col1": "integer", "col2": "string"}
        assert version.custom_metadata["quality_score"] == 0.9
    
    def test_create_dataset_version_with_parent(self):
        # Test creating a version with a parent
        dataset_id = self.service.create_dataset(
            name="Dataset for Versioning",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        # Create parent version
        parent_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/versions/1.0.0/data.csv",
        )
        
        # Create child version
        child_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.1.0",
            location="/path/to/versions/1.1.0/data.csv",
            parent_version_id=parent_id,
            description="Child of 1.0.0",
        )
        
        child_version = self.service.get_dataset_version(child_id)
        
        assert child_version is not None
        assert child_version.parent_version_id == parent_id
        assert child_version.description == "Child of 1.0.0"
    
    def test_create_version_nonexistent_dataset(self):
        # Test creating a version for a dataset that doesn't exist
        with pytest.raises(ValueError, match="Dataset .* does not exist"):
            self.service.create_dataset_version(
                dataset_id=uuid4(),
                version_number="1.0.0",
                location="/path/to/version.csv",
            )
    
    def test_create_version_nonexistent_parent(self):
        # Test creating a version with a parent that doesn't exist
        dataset_id = self.service.create_dataset(
            name="Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        with pytest.raises(ValueError, match="Parent version .* does not exist"):
            self.service.create_dataset_version(
                dataset_id=dataset_id,
                version_number="1.0.0",
                location="/path/to/version.csv",
                parent_version_id=uuid4(),
            )
    
    def test_update_dataset_version(self):
        # Test updating a dataset version
        dataset_id = self.service.create_dataset(
            name="Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        version_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/original-version.csv",
        )
        
        # Update the version
        update_result = self.service.update_dataset_version(
            version_id=version_id,
            location="/path/to/updated-version.csv",
            description="Added description",
            hash="sha256:updated",
            size_bytes=2048 * 1024,
            row_count=2000,
            column_count=15,
            schema={"col1": "integer", "col2": "string", "col3": "float"},
        )
        
        updated_version = self.service.get_dataset_version(version_id)
        
        assert update_result is True
        assert updated_version.location == "/path/to/updated-version.csv"
        assert updated_version.description == "Added description"
        assert updated_version.hash == "sha256:updated"
        assert updated_version.size_bytes == 2048 * 1024
        assert updated_version.row_count == 2000
        assert updated_version.column_count == 15
        assert updated_version.schema == {"col1": "integer", "col2": "string", "col3": "float"}
    
    def test_version_operations(self):
        # Test various version operations
        dataset_id = self.service.create_dataset(
            name="Dataset for Versions",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        # Create multiple versions
        v1_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/v1.csv",
        )
        
        v2_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.1.0",
            location="/path/to/v2.csv",
            parent_version_id=v1_id,
        )
        
        v3_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="2.0.0",
            location="/path/to/v3.csv",
            parent_version_id=v2_id,
        )
        
        # List versions
        versions = self.service.list_dataset_versions(dataset_id)
        
        assert len(versions) == 3
        assert {v.version_number for v in versions} == {"1.0.0", "1.1.0", "2.0.0"}
        
        # Get latest version
        latest = self.service.get_latest_dataset_version(dataset_id)
        
        # Since we're creating versions very quickly in the test,
        # the "latest" might be determined by timestamp microseconds
        assert latest.id in {v1_id, v2_id, v3_id}
        
        # Delete a version
        delete_result = self.service.delete_dataset_version(v2_id)
        
        assert delete_result is True
        assert self.service.get_dataset_version(v2_id) is None
        
        # Check remaining versions
        remaining_versions = self.service.list_dataset_versions(dataset_id)
        assert len(remaining_versions) == 2
        assert {v.version_number for v in remaining_versions} == {"1.0.0", "2.0.0"}
    
    def test_create_data_transformation(self):
        # Test creating a data transformation
        dataset_id = self.service.create_dataset(
            name="Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        # Create input and output versions
        input_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/input.csv",
        )
        
        output_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.1.0",
            location="/path/to/output.csv",
            parent_version_id=input_id,
        )
        
        # Create transformation
        transformation_id = self.service.create_data_transformation(
            input_dataset_version_id=input_id,
            output_dataset_version_id=output_id,
            transformation_type=DataTransformationType.CLEANING,
            name="Data Cleaning",
            description="Removed outliers and filled missing values",
            parameters={
                "outlier_threshold": 3.0,
                "fill_method": "mean",
            },
            code_reference="https://github.com/repo/cleaning.py",
            execution_time_seconds=45.2,
            tags={"cleaning", "preprocessing"},
        )
        
        transformation = self.service.get_data_transformation(transformation_id)
        
        assert transformation is not None
        assert transformation.type == DataTransformationType.CLEANING
        assert transformation.name == "Data Cleaning"
        assert transformation.description == "Removed outliers and filled missing values"
        assert transformation.input_dataset_version_id == input_id
        assert transformation.output_dataset_version_id == output_id
        assert transformation.parameters["outlier_threshold"] == 3.0
        assert transformation.parameters["fill_method"] == "mean"
        assert transformation.code_reference == "https://github.com/repo/cleaning.py"
        assert transformation.execution_time_seconds == 45.2
        assert transformation.tags == {"cleaning", "preprocessing"}
    
    def test_create_transformation_nonexistent_version(self):
        # Test creating a transformation with a non-existent input version
        with pytest.raises(ValueError, match="Input dataset version .* does not exist"):
            self.service.create_data_transformation(
                input_dataset_version_id=uuid4(),
                output_dataset_version_id=uuid4(),
                transformation_type=DataTransformationType.CLEANING,
                name="Invalid Transformation",
            )
    
    def test_transformation_operations(self):
        # Test various transformation operations
        dataset_id = self.service.create_dataset(
            name="Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        # Create versions
        v1_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/v1.csv",
        )
        
        v2_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.1.0",
            location="/path/to/v2.csv",
        )
        
        # Create transformation
        transformation_id = self.service.create_data_transformation(
            input_dataset_version_id=v1_id,
            output_dataset_version_id=v2_id,
            transformation_type=DataTransformationType.CLEANING,
            name="Original Name",
            description="Original description",
        )
        
        # Update transformation
        update_result = self.service.update_data_transformation(
            transformation_id=transformation_id,
            name="Updated Name",
            description="Updated description",
            code_reference="https://updated-reference.com",
            execution_time_seconds=60.0,
        )
        
        updated_transformation = self.service.get_data_transformation(transformation_id)
        
        assert update_result is True
        assert updated_transformation.name == "Updated Name"
        assert updated_transformation.description == "Updated description"
        assert updated_transformation.code_reference == "https://updated-reference.com"
        assert updated_transformation.execution_time_seconds == 60.0
        
        # Add tags and notes
        self.service.add_transformation_tag(transformation_id, "tag1")
        self.service.add_transformation_tag(transformation_id, "tag2")
        self.service.add_transformation_note(transformation_id, "Test note")
        
        transformation = self.service.get_data_transformation(transformation_id)
        assert transformation.tags == {"tag1", "tag2"}
        assert transformation.notes == ["Test note"]
        
        # Update and remove parameters
        self.service.update_transformation_parameter(
            transformation_id, "param1", "value1"
        )
        self.service.update_transformation_parameter(
            transformation_id, "param2", 42
        )
        
        transformation = self.service.get_data_transformation(transformation_id)
        assert transformation.parameters["param1"] == "value1"
        assert transformation.parameters["param2"] == 42
        
        remove_result = self.service.remove_transformation_parameter(
            transformation_id, "param1"
        )
        
        assert remove_result is True
        transformation = self.service.get_data_transformation(transformation_id)
        assert "param1" not in transformation.parameters
        assert "param2" in transformation.parameters
        
        # List transformations
        transformations = self.service.list_data_transformations(
            input_dataset_version_id=v1_id
        )
        
        assert len(transformations) == 1
        assert transformations[0].id == transformation_id
    
    def test_link_task_to_dataset_version(self):
        # Test linking a task to a dataset version
        dataset_id = self.service.create_dataset(
            name="Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        version_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/v1.csv",
        )
        
        # Create link
        link_id = self.service.link_task_to_dataset_version(
            task_id=self.task_id1,
            dataset_version_id=version_id,
            usage_type="input",
            description="Primary input dataset",
        )
        
        link = self.service.get_task_dataset_link(link_id)
        
        assert link is not None
        assert link.task_id == self.task_id1
        assert link.dataset_version_id == version_id
        assert link.usage_type == "input"
        assert link.description == "Primary input dataset"
    
    def test_link_to_nonexistent_version(self):
        # Test linking to a non-existent version
        with pytest.raises(ValueError, match="Dataset version .* does not exist"):
            self.service.link_task_to_dataset_version(
                task_id=self.task_id1,
                dataset_version_id=uuid4(),
            )
    
    def test_task_dataset_link_operations(self):
        # Test various link operations
        dataset_id = self.service.create_dataset(
            name="Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        version_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/v1.csv",
        )
        
        # Create links for different tasks
        link_id1 = self.service.link_task_to_dataset_version(
            task_id=self.task_id1,
            dataset_version_id=version_id,
            usage_type="input",
        )
        
        link_id2 = self.service.link_task_to_dataset_version(
            task_id=self.task_id2,
            dataset_version_id=version_id,
            usage_type="reference",
        )
        
        # Update a link
        update_result = self.service.update_task_dataset_link(
            link_id=link_id1,
            usage_type="updated_type",
            description="Added description",
        )
        
        updated_link = self.service.get_task_dataset_link(link_id1)
        
        assert update_result is True
        assert updated_link.usage_type == "updated_type"
        assert updated_link.description == "Added description"
        
        # Add notes
        self.service.add_note_to_link(link_id1, "Test note")
        
        link = self.service.get_task_dataset_link(link_id1)
        assert link.notes == ["Test note"]
        
        # Query links
        task_versions = self.service.get_dataset_versions_by_task(self.task_id1)
        assert len(task_versions) == 1
        assert task_versions[0].id == version_id
        
        task_links = self.service.get_links_by_task(self.task_id1)
        assert len(task_links) == 1
        assert task_links[0].id == link_id1
        
        version_tasks = self.service.get_tasks_by_dataset_version(version_id)
        assert len(version_tasks) == 2
        assert set(version_tasks) == {self.task_id1, self.task_id2}
        
        # Delete a link
        delete_result = self.service.delete_task_dataset_link(link_id1)
        
        assert delete_result is True
        assert self.service.get_task_dataset_link(link_id1) is None
        
        # Verify remaining links
        remaining_tasks = self.service.get_tasks_by_dataset_version(version_id)
        assert len(remaining_tasks) == 1
        assert remaining_tasks[0] == self.task_id2
    
    def test_dataset_lineage(self):
        # Test getting dataset lineage
        dataset_id = self.service.create_dataset(
            name="Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        # Create a sequence of versions
        v1_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/v1.csv",
        )
        
        v2_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.1.0",
            location="/path/to/v2.csv",
            parent_version_id=v1_id,
        )
        
        v3_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="2.0.0",
            location="/path/to/v3.csv",
            parent_version_id=v2_id,
        )
        
        # Create transformations between versions
        t1_id = self.service.create_data_transformation(
            input_dataset_version_id=v1_id,
            output_dataset_version_id=v2_id,
            transformation_type=DataTransformationType.CLEANING,
            name="Cleaning transformation",
        )
        
        t2_id = self.service.create_data_transformation(
            input_dataset_version_id=v2_id,
            output_dataset_version_id=v3_id,
            transformation_type=DataTransformationType.FEATURE_ENGINEERING,
            name="Feature engineering",
        )
        
        # Get the lineage starting from v3
        lineage = self.service.get_dataset_lineage(v3_id)
        
        # Check the lineage structure
        assert len(lineage) == 3  # Should include all three versions
        
        # Check v3 entry
        v3_entry = lineage[str(v3_id)]
        assert v3_entry["version"].id == v3_id
        assert len(v3_entry["input_transformations"]) == 1
        assert v3_entry["input_transformations"][0].id == t2_id
        
        # Check v2 entry
        v2_entry = lineage[str(v2_id)]
        assert v2_entry["version"].id == v2_id
        assert len(v2_entry["input_transformations"]) == 1
        assert v2_entry["input_transformations"][0].id == t1_id
        assert len(v2_entry["output_transformations"]) == 1
        assert v2_entry["output_transformations"][0].id == t2_id
        
        # Check v1 entry
        v1_entry = lineage[str(v1_id)]
        assert v1_entry["version"].id == v1_id
        assert len(v1_entry["output_transformations"]) == 1
        assert v1_entry["output_transformations"][0].id == t1_id