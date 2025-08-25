import time
from uuid import uuid4

import pytest

from researchtrack.dataset_versioning.models import (
    DataTransformationType,
    DatasetFormat,
    DatasetStorageType,
)
from researchtrack.dataset_versioning.service import DatasetVersioningService
from researchtrack.dataset_versioning.storage import InMemoryDatasetStorage


class TestDatasetVersioningPerformance:
    def setup_method(self):
        """Set up a fresh service instance for each test."""
        self.storage = InMemoryDatasetStorage()
        self.service = DatasetVersioningService(self.storage)
    
    def test_dataset_operations_performance(self):
        """Test performance of basic dataset operations."""
        # Create a dataset
        start_time = time.time()
        dataset_id = self.service.create_dataset(
            name="Performance Test Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.S3,
            location="s3://bucket/data.csv",
        )
        create_time = time.time() - start_time
        
        # Get the dataset
        start_time = time.time()
        self.service.get_dataset(dataset_id)
        get_time = time.time() - start_time
        
        # Update the dataset
        start_time = time.time()
        self.service.update_dataset(
            dataset_id=dataset_id,
            name="Updated Dataset",
            description="Added description",
        )
        update_time = time.time() - start_time
        
        # Delete the dataset
        start_time = time.time()
        self.service.delete_dataset(dataset_id)
        delete_time = time.time() - start_time
        
        # Assert performance metrics (50ms limit per operation)
        assert create_time < 0.05, f"Create operation took {create_time:.6f}s, exceeding 50ms limit"
        assert get_time < 0.05, f"Get operation took {get_time:.6f}s, exceeding 50ms limit"
        assert update_time < 0.05, f"Update operation took {update_time:.6f}s, exceeding 50ms limit"
        assert delete_time < 0.05, f"Delete operation took {delete_time:.6f}s, exceeding 50ms limit"
    
    def test_handle_large_dataset_catalog(self):
        """Test performance with a large number of datasets (1000+)."""
        dataset_ids = []
        
        # Create 1000 datasets
        formats = list(DatasetFormat)
        storage_types = list(DatasetStorageType)
        
        start_time = time.time()
        for i in range(1000):
            dataset_id = self.service.create_dataset(
                name=f"Dataset {i}",
                format=formats[i % len(formats)],
                storage_type=storage_types[i % len(storage_types)],
                location=f"/path/to/data_{i}.csv",
                tags={f"tag{i % 10}", f"category{i % 5}"},
            )
            dataset_ids.append(dataset_id)
        
        creation_time = time.time() - start_time
        avg_creation_time = creation_time / 1000
        
        # Test listing with various filters
        start_time = time.time()
        csv_datasets = self.service.list_datasets(format=DatasetFormat.CSV)
        list_by_format_time = time.time() - start_time
        
        start_time = time.time()
        s3_datasets = self.service.list_datasets(storage_type=DatasetStorageType.S3)
        list_by_storage_time = time.time() - start_time
        
        start_time = time.time()
        tag_datasets = self.service.list_datasets(tags={"tag1"})
        list_by_tag_time = time.time() - start_time
        
        # Test getting random datasets
        get_times = []
        for i in range(100):  # Test with 100 random datasets
            dataset_id = dataset_ids[i * 10]  # Spread across the 1000 datasets
            
            start_time = time.time()
            self.service.get_dataset(dataset_id)
            get_times.append(time.time() - start_time)
        
        avg_get_time = sum(get_times) / len(get_times)
        
        # Assert performance metrics
        assert avg_creation_time < 0.05, f"Average dataset creation took {avg_creation_time:.6f}s, exceeding 50ms limit"
        assert avg_get_time < 0.05, f"Average dataset retrieval took {avg_get_time:.6f}s, exceeding 50ms limit"
        assert list_by_format_time < 0.2, f"Listing by format took {list_by_format_time:.6f}s, exceeding reasonable limit"
        assert list_by_storage_time < 0.2, f"Listing by storage type took {list_by_storage_time:.6f}s, exceeding reasonable limit"
        assert list_by_tag_time < 0.2, f"Listing by tag took {list_by_tag_time:.6f}s, exceeding reasonable limit"
    
    def test_handle_100gb_dataset_metadata(self):
        """Test performance with metadata for a large (100GB) dataset."""
        # Create a dataset representing a 100GB file
        start_time = time.time()
        dataset_id = self.service.create_dataset(
            name="Large 100GB Dataset",
            format=DatasetFormat.PARQUET,
            storage_type=DatasetStorageType.S3,
            location="s3://large-data-bucket/100gb-dataset.parquet",
            size_bytes=100 * 1024 * 1024 * 1024,  # 100GB in bytes
            row_count=10_000_000_000,  # 10 billion rows
            column_count=50,
            schema={f"col{i}": "float" for i in range(50)},  # 50 columns
        )
        create_time = time.time() - start_time
        
        # Create 10 versions of this dataset
        version_ids = []
        
        start_time = time.time()
        for i in range(10):
            version_id = self.service.create_dataset_version(
                dataset_id=dataset_id,
                version_number=f"1.{i}.0",
                location=f"s3://large-data-bucket/versions/1.{i}.0/dataset.parquet",
                size_bytes=100 * 1024 * 1024 * 1024,  # 100GB
                row_count=10_000_000_000 + (i * 1_000_000),  # Adding rows with each version
                column_count=50 + i,  # Adding columns with each version
                schema={f"col{j}": "float" for j in range(50 + i)},
                parent_version_id=version_ids[-1] if version_ids else None,
            )
            version_ids.append(version_id)
        
        version_creation_time = time.time() - start_time
        avg_version_creation_time = version_creation_time / 10
        
        # Test retrieving versions
        get_version_times = []
        for version_id in version_ids:
            start_time = time.time()
            self.service.get_dataset_version(version_id)
            get_version_times.append(time.time() - start_time)
        
        avg_get_version_time = sum(get_version_times) / len(get_version_times)
        
        # Test getting the lineage of the last version
        start_time = time.time()
        self.service.get_dataset_lineage(version_ids[-1])
        lineage_time = time.time() - start_time
        
        # Assert performance metrics
        assert create_time < 0.05, f"Large dataset creation took {create_time:.6f}s, exceeding 50ms limit"
        assert avg_version_creation_time < 0.05, f"Average version creation took {avg_version_creation_time:.6f}s, exceeding 50ms limit"
        assert avg_get_version_time < 0.05, f"Average version retrieval took {avg_get_version_time:.6f}s, exceeding 50ms limit"
        assert lineage_time < 0.2, f"Lineage retrieval took {lineage_time:.6f}s, exceeding reasonable limit"
    
    def test_complex_transformation_chain_performance(self):
        """Test performance with a complex chain of dataset transformations."""
        # Create a dataset
        dataset_id = self.service.create_dataset(
            name="Transformation Test Dataset",
            format=DatasetFormat.CSV,
            storage_type=DatasetStorageType.S3,
            location="s3://bucket/data.csv",
        )
        
        # Create a chain of 20 versions with transformations between them
        version_ids = []
        transformation_ids = []
        
        # Create first version
        first_version_id = self.service.create_dataset_version(
            dataset_id=dataset_id,
            version_number="1.0.0",
            location="s3://bucket/versions/1.0.0/data.csv",
        )
        version_ids.append(first_version_id)
        
        # Create chain of versions and transformations
        start_time = time.time()
        
        for i in range(1, 20):
            # Create next version
            next_version_id = self.service.create_dataset_version(
                dataset_id=dataset_id,
                version_number=f"1.{i}.0",
                location=f"s3://bucket/versions/1.{i}.0/data.csv",
                parent_version_id=version_ids[-1],
            )
            version_ids.append(next_version_id)
            
            # Create transformation between versions
            transformation_type = list(DataTransformationType)[i % len(list(DataTransformationType))]
            transformation_id = self.service.create_data_transformation(
                input_dataset_version_id=version_ids[-2],
                output_dataset_version_id=version_ids[-1],
                transformation_type=transformation_type,
                name=f"Transformation {i}",
                description=f"Transform data from version 1.{i-1}.0 to 1.{i}.0",
                parameters={
                    "param1": i,
                    "param2": f"value{i}",
                    "param3": [j for j in range(i)],
                },
            )
            transformation_ids.append(transformation_id)
        
        chain_creation_time = time.time() - start_time
        avg_chain_step_time = chain_creation_time / 19  # 19 pairs of versions
        
        # Test getting the complete lineage
        start_time = time.time()
        lineage = self.service.get_dataset_lineage(version_ids[-1])
        lineage_time = time.time() - start_time
        
        # Assert performance metrics
        assert avg_chain_step_time < 0.05, f"Average transformation chain step took {avg_chain_step_time:.6f}s, exceeding 50ms limit"
        assert lineage_time < 0.5, f"Complex lineage retrieval took {lineage_time:.6f}s, exceeding reasonable limit"
        
        # Verify lineage contains all versions and transformations
        assert len(lineage) == 20  # All 20 versions
        
        # The last version should have one input transformation and no output transformations
        last_version_entry = lineage[str(version_ids[-1])]
        assert len(last_version_entry["input_transformations"]) == 1
        assert len(last_version_entry["output_transformations"]) == 0
    
    def test_task_dataset_link_performance(self):
        """Test performance with many task-dataset links."""
        # Create datasets and versions
        dataset_ids = []
        version_ids = []
        
        for i in range(10):
            dataset_id = self.service.create_dataset(
                name=f"Dataset {i}",
                format=DatasetFormat.CSV,
                storage_type=DatasetStorageType.LOCAL,
                location=f"/path/to/data_{i}.csv",
            )
            dataset_ids.append(dataset_id)
            
            # Create 5 versions for each dataset
            for j in range(5):
                version_id = self.service.create_dataset_version(
                    dataset_id=dataset_id,
                    version_number=f"1.{j}.0",
                    location=f"/path/to/versions/dataset_{i}/1.{j}.0/data.csv",
                )
                version_ids.append(version_id)
        
        # Create 100 task IDs
        task_ids = [uuid4() for _ in range(100)]
        
        # Create links (each task uses 5-10 dataset versions)
        link_ids = []
        
        start_time = time.time()
        for i, task_id in enumerate(task_ids):
            # Determine how many versions for this task
            num_versions = 5 + (i % 6)  # 5-10 versions
            
            for j in range(num_versions):
                # Pick a version (ensure distribution across all versions)
                version_index = (i * 7 + j * 13) % len(version_ids)
                version_id = version_ids[version_index]
                
                # Create the link
                usage_type = "input" if j < 2 else "reference" if j < 5 else "output"
                link_id = self.service.link_task_to_dataset_version(
                    task_id=task_id,
                    dataset_version_id=version_id,
                    usage_type=usage_type,
                    description=f"Link {i}-{j} description",
                )
                link_ids.append(link_id)
        
        link_creation_time = time.time() - start_time
        avg_link_creation_time = link_creation_time / len(link_ids)
        
        # Test querying links
        query_times = []
        for i in range(20):  # Test with 20 random tasks
            task_id = task_ids[i * 5]
            
            start_time = time.time()
            versions = self.service.get_dataset_versions_by_task(task_id)
            query_times.append(time.time() - start_time)
            
            start_time = time.time()
            links = self.service.get_links_by_task(task_id)
            query_times.append(time.time() - start_time)
        
        # Test with available versions (up to 20)
        num_test_versions = min(20, len(version_ids))
        for i in range(num_test_versions):
            # Calculate index to avoid going out of bounds
            idx = (i * len(version_ids) // num_test_versions) if num_test_versions > 1 else 0
            version_id = version_ids[idx]
            
            start_time = time.time()
            tasks = self.service.get_tasks_by_dataset_version(version_id)
            query_times.append(time.time() - start_time)
        
        avg_query_time = sum(query_times) / len(query_times)
        
        # Assert performance metrics
        assert avg_link_creation_time < 0.05, f"Average link creation took {avg_link_creation_time:.6f}s, exceeding 50ms limit"
        assert avg_query_time < 0.05, f"Average link query took {avg_query_time:.6f}s, exceeding 50ms limit"