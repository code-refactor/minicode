"""
Approximate Nearest Neighbor search implementation.

This module provides an approximate nearest neighbor search algorithm
optimized for high-dimensional vector spaces, implementing Locality-Sensitive
Hashing (LSH) for efficient similarity searches.
"""

import math
import random
import statistics
from typing import List, Dict, Tuple, Set, Optional, Callable, Any, Union
import time
import uuid

from vectordb.core.vector import Vector
from vectordb.indexing.index import VectorIndex


class RandomProjection:
    """
    Random projection for Locality-Sensitive Hashing (LSH).
    
    This class implements random projection vectors for dimensionality
    reduction used in LSH for approximate nearest neighbor search.
    """
    
    def __init__(self, dimensions: int, n_projections: int, seed: Optional[int] = None):
        """
        Initialize random projection vectors.
        
        Args:
            dimensions: Dimensionality of the input vectors
            n_projections: Number of random projections to create
            seed: Optional random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
            
        # Generate random unit vectors for projections
        self.projections = []
        for _ in range(n_projections):
            # Create a random vector with normal distribution
            projection = [random.gauss(0, 1) for _ in range(dimensions)]
            
            # Normalize to unit vector
            norm = math.sqrt(sum(x * x for x in projection))
            if norm > 0:  # Avoid division by zero
                projection = [x / norm for x in projection]
                
            self.projections.append(projection)
    
    def project(self, vector: Vector) -> List[int]:
        """
        Project a vector onto the random projection vectors to create a hash.
        
        Args:
            vector: Vector to project
            
        Returns:
            Binary hash code (list of 0s and 1s) representing the projections
        """
        hash_code = []
        for proj in self.projections:
            # Calculate dot product with the projection vector
            dot_product = sum(v * p for v, p in zip(vector.values, proj))
            
            # Convert to binary: 1 if positive, 0 if negative
            bit = 1 if dot_product >= 0 else 0
            hash_code.append(bit)
            
        return hash_code


class ApproximateNearestNeighbor:
    """
    Approximate Nearest Neighbor search using Locality-Sensitive Hashing.
    
    This class implements an efficient approximate nearest neighbor search
    algorithm based on LSH, optimized for high-dimensional vector spaces.
    """
    
    def __init__(
        self, 
        dimensions: int, 
        n_projections: int = 8,
        n_tables: int = 10,
        distance_metric: str = "euclidean",
        seed: Optional[int] = None
    ):
        """
        Initialize the approximate nearest neighbor index.
        
        Args:
            dimensions: Dimensionality of the input vectors
            n_projections: Number of random projections per hash table
            n_tables: Number of hash tables to use
            distance_metric: Distance metric to use for final ranking
            seed: Optional random seed for reproducibility
        """
        self._dimensions = dimensions
        self._n_projections = n_projections
        self._n_tables = n_tables
        self._distance_metric = distance_metric
        
        # Initialize the base vector index for storage and distance calculations
        self._vector_index = VectorIndex(distance_metric)
        
        # Create hash tables and projections
        self._hash_tables: List[Dict[Tuple[int, ...], Set[str]]] = [{} for _ in range(n_tables)]
        self._projections: List[RandomProjection] = []
        
        # Create random projections for each hash table
        base_seed = seed
        for i in range(n_tables):
            table_seed = None if base_seed is None else base_seed + i
            self._projections.append(RandomProjection(dimensions, n_projections, table_seed))
            
        self._last_modified = time.time()
    
    def __len__(self) -> int:
        """Return the number of vectors in the index."""
        return len(self._vector_index)
        
    def __contains__(self, id: str) -> bool:
        """Check if a vector with the given ID exists in the index."""
        return id in self._vector_index
    
    @property
    def ids(self) -> List[str]:
        """Get a list of all vector IDs in the index."""
        return self._vector_index.ids
    
    @property
    def last_modified(self) -> float:
        """Get the timestamp of the last modification to the index."""
        return self._last_modified
    
    def add(self, vector: Vector, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a vector to the index.
        
        Args:
            vector: Vector to add
            metadata: Optional metadata to store with the vector
            
        Returns:
            ID of the added vector
            
        Raises:
            ValueError: If the vector dimension doesn't match the index
        """
        if vector.dimension != self._dimensions:
            raise ValueError(f"Vector dimension ({vector.dimension}) does not match index dimension ({self._dimensions})")
        
        # Add to the base vector index
        vector_id = self._vector_index.add(vector, metadata)
        
        # Add to hash tables
        self._add_to_hash_tables(vector_id, vector)
        
        self._last_modified = time.time()
        return vector_id
    
    def add_batch(self, vectors: List[Vector], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Add multiple vectors to the index in a batch.
        
        Args:
            vectors: List of vectors to add
            metadatas: Optional list of metadata dictionaries
            
        Returns:
            List of vector IDs that were added
        """
        if metadatas is not None and len(vectors) != len(metadatas):
            raise ValueError("Number of vectors and metadata dictionaries must match")
            
        # Add to the base vector index
        ids = self._vector_index.add_batch(vectors, metadatas)
        
        # Add to hash tables
        for i, vector_id in enumerate(ids):
            self._add_to_hash_tables(vector_id, vectors[i])
            
        self._last_modified = time.time()
        return ids
    
    def remove(self, id: str) -> bool:
        """
        Remove a vector from the index.
        
        Args:
            id: ID of the vector to remove
            
        Returns:
            True if the vector was removed, False if not found
        """
        vector = self._vector_index.get(id)
        if vector is None:
            return False
            
        # Remove from hash tables
        for table_idx, projection in enumerate(self._projections):
            hash_code = tuple(projection.project(vector))
            if hash_code in self._hash_tables[table_idx]:
                self._hash_tables[table_idx][hash_code].discard(id)
                # Clean up empty buckets
                if not self._hash_tables[table_idx][hash_code]:
                    del self._hash_tables[table_idx][hash_code]
        
        # Remove from vector index
        self._vector_index.remove(id)
        
        self._last_modified = time.time()
        return True
    
    def clear(self) -> None:
        """Remove all vectors from the index."""
        self._vector_index.clear()
        for table in self._hash_tables:
            table.clear()
        self._last_modified = time.time()
    
    def get(self, id: str) -> Optional[Vector]:
        """
        Retrieve a vector by its ID.
        
        Args:
            id: ID of the vector to retrieve
            
        Returns:
            The vector if found, None otherwise
        """
        return self._vector_index.get(id)
    
    def get_metadata(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for a vector.
        
        Args:
            id: ID of the vector
            
        Returns:
            Metadata dictionary if found, None otherwise
        """
        return self._vector_index.get_metadata(id)
    
    def nearest(
        self, 
        query: Union[str, Vector],
        k: int = 10,
        ef_search: int = 50,
        filter_fn: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    ) -> List[Tuple[str, float]]:
        """
        Find the approximate k nearest neighbors to the query vector.
        
        Args:
            query: Query vector or vector ID
            k: Number of nearest neighbors to return
            ef_search: Size of the candidate set to consider (higher = more accurate but slower)
            filter_fn: Optional function to filter vectors based on ID and metadata
            
        Returns:
            List of (id, distance) tuples for the nearest vectors, sorted by distance
            
        Raises:
            ValueError: If the query vector has wrong dimensions or ID is not found
        """
        if k < 1:
            raise ValueError("k must be at least 1")
        
        if len(self._vector_index) == 0:
            return []
            
        # Get query vector object
        if isinstance(query, str):
            query_vector = self._vector_index.get(query)
            if query_vector is None:
                raise ValueError(f"Vector with ID '{query}' not found in the index")
        else:
            query_vector = query
            
        if query_vector.dimension != self._dimensions:
            raise ValueError(f"Query vector dimension ({query_vector.dimension}) does not match index dimension ({self._dimensions})")
        
        # Find candidate set using LSH
        # Check if ef_search is an integer
        search_size = 50  # Default
        if isinstance(ef_search, int):
            search_size = ef_search

        candidates = self._get_candidates(query_vector, search_size)

        # For very small indexes, just do a linear search
        if len(self._vector_index) <= search_size:
            candidates = set(self._vector_index.ids)
            if isinstance(query, str) and query in candidates:
                candidates.remove(query)
        
        # Calculate actual distances for the candidates
        results = []
        for candidate_id in candidates:
            # Skip if filtered out
            if filter_fn is not None:
                metadata = self._vector_index.get_metadata(candidate_id)
                if not filter_fn(candidate_id, metadata or {}):
                    continue
                    
            candidate_vector = self._vector_index.get(candidate_id)
            if candidate_vector is not None:  # Safety check
                distance = self._vector_index.distance(query_vector, candidate_vector)
                results.append((candidate_id, distance))
        
        # Sort by distance and return top k
        return sorted(results, key=lambda x: x[1])[:k]
    
    def nearest_with_metadata(
        self, 
        query: Union[str, Vector],
        k: int = 10,
        ef_search: int = 50,
        filter_fn: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Find approximate k nearest neighbors with metadata.
        
        Args:
            query: Query vector or vector ID
            k: Number of nearest neighbors to return
            ef_search: Size of the candidate set to consider
            filter_fn: Optional function to filter vectors
            
        Returns:
            List of (id, distance, metadata) tuples for nearest vectors
        """
        nearest_results = self.nearest(query, k, ef_search, filter_fn)
        
        # Add metadata to each result
        return [
            (id, dist, self._vector_index.get_metadata(id) or {}) 
            for id, dist in nearest_results
        ]
    
    def _add_to_hash_tables(self, vector_id: str, vector: Vector) -> None:
        """
        Add a vector to all hash tables.
        
        Args:
            vector_id: ID of the vector
            vector: The vector to add
        """
        for table_idx, projection in enumerate(self._projections):
            hash_code = tuple(projection.project(vector))
            
            if hash_code not in self._hash_tables[table_idx]:
                self._hash_tables[table_idx][hash_code] = set()
                
            self._hash_tables[table_idx][hash_code].add(vector_id)
    
    def _get_candidates(self, query: Vector, max_candidates: int) -> Set[str]:
        """
        Get candidate vectors using LSH.
        
        Args:
            query: Query vector
            max_candidates: Maximum number of candidates to return
            
        Returns:
            Set of candidate vector IDs
        """
        candidates = set()
        
        # Query each hash table
        for table_idx, projection in enumerate(self._projections):
            hash_code = tuple(projection.project(query))
            
            # Get vectors that hash to the same bucket
            if hash_code in self._hash_tables[table_idx]:
                candidates.update(self._hash_tables[table_idx][hash_code])
        
        # If we don't have enough candidates, we can use a fallback strategy
        if len(candidates) < max_candidates:
            # Try to find close matches by checking neighboring buckets
            # For simplicity, if we have no matches, return some random vectors as candidates
            if not candidates and len(self._vector_index) > 0:
                # Take a random sample of vectors to ensure we have some candidates
                sample_size = min(max_candidates, len(self._vector_index))
                candidates = set(random.sample(self._vector_index.ids, sample_size))
                
        return candidates