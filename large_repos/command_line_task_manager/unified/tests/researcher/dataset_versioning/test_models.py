from datetime import datetime
from uuid import UUID, uuid4

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


class TestDataset:
    def test_create_dataset(self):
        # Test basic creation
        dataset = Dataset(
            name="Climate Data 2010-2020",
            description="Global temperature and precipitation data",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.S3,
            location="s3://research-data/climate/2010-2020.csv",
            size_bytes=1024 * 1024 * 100,  # 100MB
            row_count=1000000,
            column_count=25,
            schema={
                "date": "datetime",
                "location_id": "integer",
                "temperature": "float",
                "precipitation": "float",
            },
            tags={"climate", "temperature", "precipitation"},
            hash="sha256:abcdef1234567890",
            version="1.0.0",
        )
        
        assert isinstance(dataset.id, UUID)
        assert dataset.name == "Climate Data 2010-2020"
        assert dataset.description == "Global temperature and precipitation data"
        assert dataset.format == DatasetFormat.CSV
        assert dataset.storage_type == DatasetStorageType.S3
        assert dataset.location == "s3://research-data/climate/2010-2020.csv"
        assert dataset.size_bytes == 1024 * 1024 * 100
        assert dataset.row_count == 1000000
        assert dataset.column_count == 25
        assert dataset.schema == {
            "date": "datetime",
            "location_id": "integer",
            "temperature": "float",
            "precipitation": "float",
        }
        assert dataset.tags == {"climate", "temperature", "precipitation"}
        assert dataset.hash == "sha256:abcdef1234567890"
        assert dataset.version == "1.0.0"
        assert dataset.parent_dataset_id is None
        assert isinstance(dataset.created_at, datetime)
        assert isinstance(dataset.updated_at, datetime)
    
    def test_update_dataset(self):
        # Test updating fields
        dataset = Dataset(
            name="Original Name",
            description="Original description",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        original_updated_at = dataset.updated_at
        
        dataset.update(
            name="Updated Name",
            description="Updated description",
            location="/new/path/to/data.csv",
            size_bytes=1024 * 1024,  # 1MB
            row_count=10000,
        )
        
        assert dataset.name == "Updated Name"
        assert dataset.description == "Updated description"
        assert dataset.location == "/new/path/to/data.csv"
        assert dataset.size_bytes == 1024 * 1024
        assert dataset.row_count == 10000
        assert dataset.updated_at > original_updated_at
    
    def test_dataset_tags(self):
        # Test adding and removing tags
        dataset = Dataset(
            name="Dataset with tags",
            format=DatasetFormat.PARQUET,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.parquet",
        )
        
        original_updated_at = dataset.updated_at
        
        dataset.add_tag("first_tag")
        dataset.add_tag("second_tag")
        dataset.add_tag("third_tag")
        
        assert dataset.tags == {"first_tag", "second_tag", "third_tag"}
        assert dataset.updated_at > original_updated_at
        
        # Adding duplicate tag should not change the set
        previous_updated_at = dataset.updated_at
        dataset.add_tag("first_tag")
        assert dataset.tags == {"first_tag", "second_tag", "third_tag"}
        assert dataset.updated_at > previous_updated_at
        
        # Remove tag
        dataset.remove_tag("second_tag")
        assert dataset.tags == {"first_tag", "third_tag"}
        
        # Removing non-existent tag
        previous_updated_at = dataset.updated_at
        dataset.remove_tag("nonexistent_tag")
        assert dataset.updated_at == previous_updated_at
    
    def test_dataset_custom_metadata(self):
        # Test custom metadata
        dataset = Dataset(
            name="Dataset with metadata",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.LOCAL,
            location="/path/to/data.csv",
        )
        
        original_updated_at = dataset.updated_at
        
        dataset.update_custom_metadata("source", "NOAA Climate Database")
        dataset.update_custom_metadata("license", "CC-BY-4.0")
        dataset.update_custom_metadata("quality_score", 0.95)
        dataset.update_custom_metadata("validated", True)
        dataset.update_custom_metadata("related_variables", ["temperature", "humidity", "pressure"])
        dataset.update_custom_metadata(
            "processing_steps", {"step1": "cleaning", "step2": "normalization"}
        )
        
        assert len(dataset.custom_metadata) == 6
        assert dataset.custom_metadata["source"] == "NOAA Climate Database"
        assert dataset.custom_metadata["license"] == "CC-BY-4.0"
        assert dataset.custom_metadata["quality_score"] == 0.95
        assert dataset.custom_metadata["validated"] is True
        assert dataset.custom_metadata["related_variables"] == ["temperature", "humidity", "pressure"]
        assert dataset.custom_metadata["processing_steps"] == {"step1": "cleaning", "step2": "normalization"}
        assert dataset.updated_at > original_updated_at
        
        # Update existing metadata
        previous_updated_at = dataset.updated_at
        dataset.update_custom_metadata("quality_score", 0.98)
        assert dataset.custom_metadata["quality_score"] == 0.98
        assert dataset.updated_at > previous_updated_at
        
        # Remove metadata field
        result = dataset.remove_custom_metadata("license")
        assert result is True
        assert "license" not in dataset.custom_metadata
        
        # Remove non-existent field
        non_existent_result = dataset.remove_custom_metadata("nonexistent")
        assert non_existent_result is False


class TestDatasetVersion:
    def test_create_dataset_version(self):
        # Test basic creation
        dataset_id = uuid4()
        parent_version_id = uuid4()
        
        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.2.3",
            created_at=datetime.now(),
            creator="Dr. Researcher",
            description="Added new weather stations and fixed missing values",
            location="s3://research-data/climate/v1.2.3/data.csv",
            hash="sha256:1234567890abcdef",
            size_bytes=1024 * 1024 * 120,  # 120MB
            parent_version_id=parent_version_id,
            row_count=1200000,
            column_count=25,
            schema={
                "date": "datetime",
                "location_id": "integer",
                "temperature": "float",
                "precipitation": "float",
                "station_type": "string",  # New column
            },
            custom_metadata={
                "quality_score": 0.98,
                "validation_date": "2023-05-15",
            },
        )
        
        assert isinstance(version.id, UUID)
        assert version.dataset_id == dataset_id
        assert version.version_number == "1.2.3"
        assert isinstance(version.created_at, datetime)
        assert version.creator == "Dr. Researcher"
        assert version.description == "Added new weather stations and fixed missing values"
        assert version.location == "s3://research-data/climate/v1.2.3/data.csv"
        assert version.hash == "sha256:1234567890abcdef"
        assert version.size_bytes == 1024 * 1024 * 120
        assert version.parent_version_id == parent_version_id
        assert version.row_count == 1200000
        assert version.column_count == 25
        assert "station_type" in version.schema
        assert version.custom_metadata["quality_score"] == 0.98
    
    def test_update_version(self):
        # Test updating fields
        dataset_id = uuid4()
        
        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/v1.0.0/data.csv",
        )
        
        version.update(
            description="Added description",
            hash="sha256:updated-hash",
            size_bytes=1024 * 1024 * 10,
            row_count=500000,
        )
        
        assert version.description == "Added description"
        assert version.hash == "sha256:updated-hash"
        assert version.size_bytes == 1024 * 1024 * 10
        assert version.row_count == 500000
    
    def test_version_custom_metadata(self):
        # Test custom metadata operations
        dataset_id = uuid4()
        
        version = DatasetVersion(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="/path/to/v1.0.0/data.csv",
        )
        
        version.update_custom_metadata("processing_time", 3600)  # 1 hour
        version.update_custom_metadata("validated_by", "Quality Assurance Team")
        version.update_custom_metadata("error_rate", 0.002)
        
        assert version.custom_metadata["processing_time"] == 3600
        assert version.custom_metadata["validated_by"] == "Quality Assurance Team"
        assert version.custom_metadata["error_rate"] == 0.002
        
        # Update existing field
        version.update_custom_metadata("error_rate", 0.001)
        assert version.custom_metadata["error_rate"] == 0.001
        
        # Remove field
        result = version.remove_custom_metadata("validated_by")
        assert result is True
        assert "validated_by" not in version.custom_metadata
        
        # Remove non-existent field
        non_existent_result = version.remove_custom_metadata("nonexistent")
        assert non_existent_result is False


class TestDataTransformation:
    def test_create_data_transformation(self):
        # Test basic creation
        input_version_id = uuid4()
        output_version_id = uuid4()
        
        transformation = DataTransformation(
            type=DataTransformationType.CLEANING,
            name="Data Cleaning Transformation",
            description="Removed outliers and filled missing values",
            input_dataset_version_id=input_version_id,
            output_dataset_version_id=output_version_id,
            parameters={
                "outlier_threshold": 3.0,
                "imputation_method": "mean",
                "columns_processed": ["temperature", "precipitation"],
            },
            code_reference="https://github.com/research/repo/data_cleaning.py",
            execution_time_seconds=120.5,
            tags={"cleaning", "outliers", "imputation"},
        )
        
        assert isinstance(transformation.id, UUID)
        assert transformation.type == DataTransformationType.CLEANING
        assert transformation.name == "Data Cleaning Transformation"
        assert transformation.description == "Removed outliers and filled missing values"
        assert transformation.input_dataset_version_id == input_version_id
        assert transformation.output_dataset_version_id == output_version_id
        assert transformation.parameters["outlier_threshold"] == 3.0
        assert transformation.parameters["imputation_method"] == "mean"
        assert transformation.code_reference == "https://github.com/research/repo/data_cleaning.py"
        assert transformation.execution_time_seconds == 120.5
        assert transformation.tags == {"cleaning", "outliers", "imputation"}
        assert len(transformation.notes) == 0
        assert isinstance(transformation.created_at, datetime)
    
    def test_update_transformation(self):
        # Test updating fields
        input_version_id = uuid4()
        output_version_id = uuid4()
        
        transformation = DataTransformation(
            type=DataTransformationType.CLEANING,
            name="Original name",
            description="Original description",
            input_dataset_version_id=input_version_id,
            output_dataset_version_id=output_version_id,
        )
        
        transformation.update(
            name="Updated name",
            description="Updated description",
            code_reference="https://updated-reference.com",
            execution_time_seconds=200.0,
        )
        
        assert transformation.name == "Updated name"
        assert transformation.description == "Updated description"
        assert transformation.code_reference == "https://updated-reference.com"
        assert transformation.execution_time_seconds == 200.0
    
    def test_transformation_tags(self):
        # Test adding and removing tags
        input_version_id = uuid4()
        output_version_id = uuid4()
        
        transformation = DataTransformation(
            type=DataTransformationType.NORMALIZATION,
            name="Data Normalization",
            input_dataset_version_id=input_version_id,
            output_dataset_version_id=output_version_id,
        )
        
        transformation.add_tag("normalization")
        transformation.add_tag("scaling")
        transformation.add_tag("preprocessing")
        
        assert transformation.tags == {"normalization", "scaling", "preprocessing"}
        
        # Adding duplicate tag should not change the set
        transformation.add_tag("normalization")
        assert transformation.tags == {"normalization", "scaling", "preprocessing"}
        
        # Remove tag
        transformation.remove_tag("scaling")
        assert transformation.tags == {"normalization", "preprocessing"}
        
        # Remove non-existent tag
        transformation.remove_tag("nonexistent")
        assert transformation.tags == {"normalization", "preprocessing"}
    
    def test_transformation_notes(self):
        # Test adding notes
        input_version_id = uuid4()
        output_version_id = uuid4()
        
        transformation = DataTransformation(
            type=DataTransformationType.FILTERING,
            name="Data Filtering",
            input_dataset_version_id=input_version_id,
            output_dataset_version_id=output_version_id,
        )
        
        transformation.add_note("First note on the transformation")
        transformation.add_note("Second note with additional details")
        
        assert len(transformation.notes) == 2
        assert transformation.notes[0] == "First note on the transformation"
        assert transformation.notes[1] == "Second note with additional details"
    
    def test_transformation_parameters(self):
        # Test parameters
        input_version_id = uuid4()
        output_version_id = uuid4()
        
        transformation = DataTransformation(
            type=DataTransformationType.FEATURE_ENGINEERING,
            name="Feature Engineering",
            input_dataset_version_id=input_version_id,
            output_dataset_version_id=output_version_id,
        )
        
        transformation.update_parameter("new_features", ["feature1", "feature2"])
        transformation.update_parameter("window_size", 7)
        transformation.update_parameter("use_lag", True)
        
        assert transformation.parameters["new_features"] == ["feature1", "feature2"]
        assert transformation.parameters["window_size"] == 7
        assert transformation.parameters["use_lag"] is True
        
        # Update existing parameter
        transformation.update_parameter("window_size", 14)
        assert transformation.parameters["window_size"] == 14
        
        # Remove parameter
        result = transformation.remove_parameter("use_lag")
        assert result is True
        assert "use_lag" not in transformation.parameters
        
        # Remove non-existent parameter
        non_existent_result = transformation.remove_parameter("nonexistent")
        assert non_existent_result is False


class TestTaskDatasetLink:
    def test_create_task_dataset_link(self):
        # Test basic creation
        task_id = uuid4()
        dataset_version_id = uuid4()
        
        link = TaskDatasetLink(
            task_id=task_id,
            dataset_version_id=dataset_version_id,
            usage_type="input",
            description="Primary dataset used for analysis",
        )
        
        assert isinstance(link.id, UUID)
        assert link.task_id == task_id
        assert link.dataset_version_id == dataset_version_id
        assert link.usage_type == "input"
        assert link.description == "Primary dataset used for analysis"
        assert len(link.notes) == 0
        assert isinstance(link.created_at, datetime)
        assert isinstance(link.updated_at, datetime)
    
    def test_update_link(self):
        # Test updating fields
        task_id = uuid4()
        dataset_version_id = uuid4()
        
        link = TaskDatasetLink(
            task_id=task_id,
            dataset_version_id=dataset_version_id,
            usage_type="original_type",
            description="Original description",
        )
        
        original_updated_at = link.updated_at
        
        link.update(
            usage_type="updated_type",
            description="Updated description",
        )
        
        assert link.usage_type == "updated_type"
        assert link.description == "Updated description"
        assert link.updated_at > original_updated_at
    
    def test_link_notes(self):
        # Test adding notes
        task_id = uuid4()
        dataset_version_id = uuid4()
        
        link = TaskDatasetLink(
            task_id=task_id,
            dataset_version_id=dataset_version_id,
        )
        
        original_updated_at = link.updated_at
        
        link.add_note("First note about this link")
        link.add_note("Second note with additional details")
        
        assert len(link.notes) == 2
        assert link.notes[0] == "First note about this link"
        assert link.notes[1] == "Second note with additional details"
        assert link.updated_at > original_updated_at