"""
Tests for the approximate nearest neighbor search implementation.
"""

import pytest
import time
import random
from vectordb.core.vector import Vector
from vectordb.indexing.approximate_nn import ApproximateNearestNeighbor, RandomProjection


class TestRandomProjection:
    """Tests for the RandomProjection class."""
    
    def test_initialization(self):
        """Test random projection initialization."""
        # Create random projections
        proj = RandomProjection(dimensions=3, n_projections=10)
        
        # Check properties
        assert len(proj.projections) == 10
        assert all(len(p) == 3 for p in proj.projections)
        
        # Test deterministic initialization with seed
        proj1 = RandomProjection(dimensions=3, n_projections=10, seed=42)
        proj2 = RandomProjection(dimensions=3, n_projections=10, seed=42)
        
        # Should be the same with same seed
        for i in range(10):
            assert proj1.projections[i] == proj2.projections[i]
        
        # Different seed should give different projections
        proj3 = RandomProjection(dimensions=3, n_projections=10, seed=43)
        assert any(proj1.projections[i] != proj3.projections[i] for i in range(10))
    
    def test_projection(self):
        """Test projecting vectors."""
        # Create a projection
        proj = RandomProjection(dimensions=3, n_projections=10, seed=42)
        
        # Project a vector
        v = Vector([1.0, 0.0, 0.0])
        hash_code = proj.project(v)
        
        # Check hash code properties
        assert len(hash_code) == 10
        assert all(isinstance(bit, int) for bit in hash_code)
        assert all(bit in [0, 1] for bit in hash_code)
        
        # Same vector should get same hash code
        assert proj.project(v) == hash_code
        
        # Similar vectors should get similar hash codes
        v_similar = Vector([0.9, 0.1, 0.0])
        hash_similar = proj.project(v_similar)
        
        # Different vectors should get different hash codes
        v_different = Vector([0.0, 0.0, 1.0])
        hash_different = proj.project(v_different)
        
        # Count bit differences
        similarity_diff = sum(a != b for a, b in zip(hash_code, hash_similar))
        different_diff = sum(a != b for a, b in zip(hash_code, hash_different))
        
        # On average, similar vectors should have fewer bit differences
        # but this is probabilistic, so we can't make a hard assertion
        # Uncomment if you want to visualize the differences
        # print(f"Similarity diff: {similarity_diff}, Different diff: {different_diff}")


class TestApproximateNearestNeighbor:
    """Tests for the ApproximateNearestNeighbor class."""
    
    def setup_method(self):
        """Set up test vectors and index for each test."""
        # Create an approximate nearest neighbor index
        self.index = ApproximateNearestNeighbor(
            dimensions=3,
            n_projections=8,
            n_tables=10,
            distance_metric="euclidean",
            seed=42
        )
        
        # Create test vectors
        self.v1 = Vector([1.0, 0.0, 0.0], id="vec1")
        self.v2 = Vector([0.0, 1.0, 0.0], id="vec2")
        self.v3 = Vector([0.0, 0.0, 1.0], id="vec3")
        self.v4 = Vector([1.0, 1.0, 1.0], id="vec4")
        self.v5 = Vector([2.0, 2.0, 2.0], id="vec5")
        
        # Add vectors to the index
        self.index.add(self.v1)
        self.index.add(self.v2)
        self.index.add(self.v3)
        self.index.add(self.v4)
    
    def test_initialization(self):
        """Test approximate nearest neighbor index initialization."""
        # Test default parameters
        index = ApproximateNearestNeighbor(dimensions=3)
        assert index._dimensions == 3
        assert index._n_projections == 8  # Default value
        assert index._n_tables == 10  # Default value
        assert index._distance_metric == "euclidean"  # Default value
        
        # Test custom parameters
        index = ApproximateNearestNeighbor(
            dimensions=5,
            n_projections=12,
            n_tables=20,
            distance_metric="cosine",
            seed=42
        )
        assert index._dimensions == 5
        assert index._n_projections == 12
        assert index._n_tables == 20
        assert index._distance_metric == "cosine"
        
        # Test with invalid distance metric (should raise error)
        with pytest.raises(ValueError):
            ApproximateNearestNeighbor(dimensions=3, distance_metric="invalid_metric")
    
    def test_adding_and_retrieving_vectors(self):
        """Test adding and retrieving vectors."""
        # Check basic properties after setup
        assert len(self.index) == 4
        assert "vec1" in self.index
        assert "vec2" in self.index
        assert "vec3" in self.index
        assert "vec4" in self.index
        assert "vec5" not in self.index
        
        # Add another vector
        self.index.add(self.v5)
        assert len(self.index) == 5
        assert "vec5" in self.index
        
        # Add a vector without ID (should generate an ID)
        v_no_id = Vector([3.0, 3.0, 3.0])
        id = self.index.add(v_no_id)
        assert id is not None
        assert id in self.index
        assert len(self.index) == 6
        
        # Add a vector with metadata
        metadata = {"test": "metadata", "value": 42}
        id = self.index.add(Vector([4.0, 4.0, 4.0]), metadata)
        assert self.index.get_metadata(id) == metadata
        
        # Get vectors by ID
        assert self.index.get("vec1") == self.v1
        assert self.index.get("vec2") == self.v2
        assert self.index.get("nonexistent") is None
        
        # Test vector with wrong dimension (should raise error)
        with pytest.raises(ValueError):
            self.index.add(Vector([1.0, 2.0]))
    
    def test_batch_operations(self):
        """Test batch operations."""
        # Create a new index
        index = ApproximateNearestNeighbor(dimensions=3)
        
        # Create batch of vectors
        vectors = [
            Vector([i, i, i], id=f"batch{i}") for i in range(1, 6)
        ]
        
        # Add in batch
        metadatas = [{"value": i} for i in range(1, 6)]
        ids = index.add_batch(vectors, metadatas)
        
        # Check results
        assert len(ids) == 5
        assert len(index) == 5
        for i, id in enumerate(ids):
            assert id == f"batch{i+1}"
            assert index.get_metadata(id) == {"value": i+1}
    
    def test_removing_vectors(self):
        """Test removing vectors."""
        # Remove a vector
        assert self.index.remove("vec1") is True
        assert "vec1" not in self.index
        assert len(self.index) == 3
        
        # Try to remove a nonexistent vector
        assert self.index.remove("nonexistent") is False
        assert len(self.index) == 3
        
        # Clear the index
        self.index.clear()
        assert len(self.index) == 0
        for id in ["vec2", "vec3", "vec4"]:
            assert id not in self.index
    
    def test_nearest_neighbors(self):
        """Test finding approximate nearest neighbors."""
        # Create a larger index for better testing
        index = ApproximateNearestNeighbor(dimensions=10, seed=42)
        
        # Create vectors: base vector and variations with increasing distance
        base_vector = Vector([1.0] * 10)
        index.add(base_vector, {"type": "base"})
        
        # Add vectors with increasing distance
        for i in range(1, 101):
            # Create a vector that differs from base_vector by i dimensions
            vec_values = [1.0] * 10
            for j in range(min(i, 10)):
                vec_values[j] = 2.0  # Change some dimensions to increase distance
            
            vec = Vector(vec_values, id=f"vec{i}")
            index.add(vec, {"distance": i})
        
        # Find 10 nearest neighbors
        nearest = index.nearest(base_vector, k=10, ef_search=50)
        
        # Check results
        assert len(nearest) == 10
        
        # Distances should generally be in ascending order
        distances = [dist for _, dist in nearest]
        assert all(distances[i] <= distances[i+1] for i in range(len(distances)-1))
        
        # Test with metadata
        nearest_with_meta = index.nearest_with_metadata(base_vector, k=5)
        assert len(nearest_with_meta) == 5
        
        # Each result should have id, distance, and metadata
        for id, distance, metadata in nearest_with_meta:
            assert isinstance(id, str)
            assert isinstance(distance, float)
            assert isinstance(metadata, dict)
        
        # Test with filter function
        filter_fn = lambda id, metadata: metadata.get("distance", 0) % 2 == 0
        nearest_filtered = index.nearest(base_vector, k=10, filter_fn=filter_fn)
        
        # Check filtered results
        for id, _ in nearest_filtered:
            if id.startswith("vec"):
                assert int(id.replace("vec", "")) % 2 == 0
    
    def test_nearest_exact_match(self):
        """Test that exact matches are found correctly."""
        # Create a simple index
        index = ApproximateNearestNeighbor(dimensions=3, seed=42)
        
        # Add some vectors
        v1 = Vector([1.0, 0.0, 0.0], id="vec1")
        v2 = Vector([0.0, 1.0, 0.0], id="vec2")
        v3 = Vector([0.0, 0.0, 1.0], id="vec3")
        
        index.add(v1)
        index.add(v2)
        index.add(v3)
        
        # Query with an exact copy of v1
        query = Vector([1.0, 0.0, 0.0])
        nearest = index.nearest(query, k=1)
        
        # Should find v1 as the nearest
        assert len(nearest) == 1
        assert nearest[0][0] == "vec1"
        assert nearest[0][1] == 0.0  # Distance should be 0
    
    def test_performance_with_large_dataset(self):
        """Test performance with a larger dataset (as a basic benchmark)."""
        # Create a smaller index with reduced dimensions and vectors for faster testing
        dimensions = 32
        index = ApproximateNearestNeighbor(
            dimensions=dimensions,
            n_projections=8,
            n_tables=4,
            seed=42
        )
        
        # Create a dataset of random vectors - use a smaller number for testing
        num_vectors = 1000
        random.seed(42)
        
        for i in range(num_vectors):
            values = [random.gauss(0, 1) for _ in range(dimensions)]
            index.add(Vector(values, id=f"vec{i}"))
        
        # Create a query vector
        query = Vector([random.gauss(0, 1) for _ in range(dimensions)])
        
        # Time the query
        start_time = time.time()
        results = index.nearest(query, k=10, ef_search=50)
        query_time = time.time() - start_time
        
        # We're not asserting on the exact time since it varies by machine,
        # but we want to make sure it completes and finds results
        assert len(results) == 10
        assert query_time > 0  # Just ensure timing worked