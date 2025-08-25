"""
Vector index implementation for efficient similarity searches.

This module provides a base vector index for storing and retrieving
high-dimensional vectors with optimized distance calculations.
"""

import math
import heapq
import time
from typing import List, Dict, Tuple, Callable, Optional, Set, Any, Iterator, Union
import random
import uuid

from vectordb.core.vector import Vector
from vectordb.core.distance import get_distance_function, euclidean_distance
from common.core.storage import InMemoryStore
# from common.utils.threading import RWLock
from threading import RLock


class VectorIndex:
    """
    Base vector index for efficient similarity searches.
    
    This class provides a simple but efficient index for vectors
    with support for nearest neighbor queries using various distance metrics.
    """
    
    def __init__(self, distance_metric: str = "euclidean"):
        """
        Initialize a vector index.
        
        Args:
            distance_metric: The distance metric to use for similarity calculations.
                             Supported metrics: euclidean, squared_euclidean, manhattan, 
                             cosine, angular, chebyshev.
                             
        Raises:
            ValueError: If an unsupported distance metric is provided.
        """
        self._storage = InMemoryStore()
        self._lock = RLock()  # Using RLock for simplicity
        self._distance_function = get_distance_function(distance_metric)
        self._distance_metric = distance_metric
        self._last_modified = time.time()
        
    def __len__(self) -> int:
        """Return the number of vectors in the index."""
        with self._lock:
            return self._storage.size()
        
    def __contains__(self, id: str) -> bool:
        """Check if a vector with the given ID exists in the index."""
        with self._lock:
            vector_data = self._storage.get(id)
            return vector_data is not None
        
    def __iter__(self) -> Iterator[Vector]:
        """Iterate over all vectors in the index."""
        with self._lock:
            all_data = self._storage.query()
            vectors = []
            for data in all_data:
                if isinstance(data, dict) and 'vector' in data:
                    vectors.append(data['vector'])
            return iter(vectors)
    
    @property
    def ids(self) -> List[str]:
        """Get a list of all vector IDs in the index."""
        with self._lock:
            # Get all keys from storage - we need to implement this differently
            # Since InMemoryStore doesn't expose keys directly, we query all data
            all_data = self._storage.query()
            ids = []
            # This is a workaround - in a real implementation, we'd modify InMemoryStore
            # to expose keys() method or store vector IDs separately
            for key in self._storage._data.keys():
                ids.append(str(key))
            return ids
    
    @property
    def last_modified(self) -> float:
        """Get the timestamp of the last modification to the index."""
        return self._last_modified
    
    @property
    def distance_metric(self) -> str:
        """Get the distance metric used by this index."""
        return self._distance_metric
        
    def add(self, vector: Vector, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a vector to the index.
        
        Args:
            vector: The vector to add
            metadata: Optional metadata to associate with the vector
            
        Returns:
            The ID of the added vector
            
        Raises:
            ValueError: If the vector does not have an ID and cannot be added
        """
        with self._lock:
            # Generate an ID if the vector doesn't have one
            vector_id = vector.id
            if vector_id is None:
                vector_id = str(uuid.uuid4())
                # Create a new vector with the generated ID
                vector = Vector(vector.values, vector_id)
            
            # Store vector and metadata together
            vector_data = {
                'vector': vector,
                'metadata': metadata or {}
            }
            
            self._storage.insert(vector_id, vector_data)
            self._last_modified = time.time()
            return vector_id
    
    def add_batch(self, vectors: List[Vector], metadatas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """
        Add multiple vectors to the index in a batch.
        
        Args:
            vectors: List of vectors to add
            metadatas: Optional list of metadata dictionaries, one per vector
            
        Returns:
            List of vector IDs that were added
            
        Raises:
            ValueError: If the lengths of vectors and metadatas don't match
        """
        if metadatas is not None and len(vectors) != len(metadatas):
            raise ValueError("Number of vectors and metadata dictionaries must match")
            
        ids = []
        for i, vector in enumerate(vectors):
            metadata = metadatas[i] if metadatas is not None else None
            ids.append(self.add(vector, metadata))
            
        return ids
    
    def get(self, id: str) -> Optional[Vector]:
        """
        Retrieve a vector by its ID.
        
        Args:
            id: The ID of the vector to retrieve
            
        Returns:
            The vector if found, None otherwise
        """
        with self._lock:
            vector_data = self._storage.get(id)
            if vector_data and isinstance(vector_data, dict) and 'vector' in vector_data:
                return vector_data['vector']
            return None
    
    def get_metadata(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the metadata associated with a vector.
        
        Args:
            id: The ID of the vector
            
        Returns:
            The metadata dictionary if the vector exists, None otherwise
        """
        with self._lock:
            vector_data = self._storage.get(id)
            if vector_data and isinstance(vector_data, dict) and 'metadata' in vector_data:
                return vector_data['metadata']
            return None
    
    def update_metadata(self, id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update the metadata for a vector.
        
        Args:
            id: The ID of the vector
            metadata: The new metadata dictionary
            
        Returns:
            True if the metadata was updated, False if the vector was not found
        """
        with self._lock:
            vector_data = self._storage.get(id)
            if vector_data is None:
                return False
            
            vector_data['metadata'] = metadata
            self._storage.update(id, vector_data)
            self._last_modified = time.time()
            return True
    
    def remove(self, id: str) -> bool:
        """
        Remove a vector from the index.
        
        Args:
            id: The ID of the vector to remove
            
        Returns:
            True if the vector was removed, False if it was not found
        """
        with self._lock:
            success = self._storage.delete(id)
            if success:
                self._last_modified = time.time()
            return success
    
    def remove_batch(self, ids: List[str]) -> int:
        """
        Remove multiple vectors from the index.
        
        Args:
            ids: List of vector IDs to remove
            
        Returns:
            Number of vectors actually removed
        """
        removed_count = 0
        for id in ids:
            if self.remove(id):
                removed_count += 1
                
        return removed_count
    
    def clear(self) -> None:
        """Remove all vectors from the index."""
        with self._lock:
            self._storage.clear()
            self._last_modified = time.time()
    
    def distance(self, v1: Union[str, Vector], v2: Union[str, Vector]) -> float:
        """
        Calculate the distance between two vectors.
        
        Args:
            v1: Either a vector ID or a Vector object
            v2: Either a vector ID or a Vector object
            
        Returns:
            The distance between the vectors
            
        Raises:
            ValueError: If either vector ID is not found or vectors have different dimensions
        """
        # Get actual vector objects if IDs were provided
        vec1 = self._get_vector_object(v1)
        vec2 = self._get_vector_object(v2)
        
        return self._distance_function(vec1, vec2)
    
    def nearest(self, query: Union[str, Vector], k: int = 1, filter_fn: Optional[Callable[[str, Dict[str, Any]], bool]] = None) -> List[Tuple[str, float]]:
        """
        Find the k nearest vectors to the query vector.
        
        Args:
            query: Query vector or vector ID
            k: Number of nearest neighbors to return
            filter_fn: Optional function to filter vectors based on ID and metadata
            
        Returns:
            List of (id, distance) tuples for the nearest vectors, sorted by distance
            
        Raises:
            ValueError: If the query vector ID is not found
        """
        if k < 1:
            raise ValueError("k must be at least 1")
        
        with self._lock:
            if self._storage.size() == 0:
                return []
                
            # Ensure we have a Vector object
            query_vector = self._get_vector_object(query)
            
            # Calculate distances and filter results
            distances = []
            all_data = self._storage.query()
            for key in self._storage._data.keys():
                vector_data = self._storage.get(key)
                if not vector_data or not isinstance(vector_data, dict) or 'vector' not in vector_data:
                    continue
                    
                vec_id = str(key)
                vector = vector_data['vector']
                metadata = vector_data.get('metadata', {})
                
                # Skip if the filter excludes this vector
                if filter_fn is not None and not filter_fn(vec_id, metadata):
                    continue
                    
                # Skip if this is the query vector itself
                if isinstance(query, str) and query == vec_id:
                    continue
                    
                dist = self._distance_function(query_vector, vector)
                distances.append((vec_id, dist))
            
            # Sort by distance and return the k nearest
            return sorted(distances, key=lambda x: x[1])[:k]
    
    def nearest_with_metadata(self, query: Union[str, Vector], k: int = 1, filter_fn: Optional[Callable[[str, Dict[str, Any]], bool]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Find the k nearest vectors to the query vector, including their metadata.
        
        Args:
            query: Query vector or vector ID
            k: Number of nearest neighbors to return
            filter_fn: Optional function to filter vectors based on ID and metadata
            
        Returns:
            List of (id, distance, metadata) tuples for the nearest vectors, sorted by distance
        """
        nearest_results = self.nearest(query, k, filter_fn)
        
        # Add metadata to each result
        result = []
        with self._lock:
            for id, dist in nearest_results:
                metadata = self.get_metadata(id) or {}
                result.append((id, dist, metadata))
        return result
    
    def _get_vector_object(self, vector_or_id: Union[str, Vector]) -> Vector:
        """
        Get a Vector object from either a vector or an ID.
        
        Args:
            vector_or_id: Either a Vector object or a vector ID
            
        Returns:
            The Vector object
            
        Raises:
            ValueError: If the ID doesn't exist in the index
        """
        if isinstance(vector_or_id, str):
            with self._lock:
                vector = self.get(vector_or_id)
                if vector is None:
                    raise ValueError(f"Vector with ID '{vector_or_id}' not found in the index")
                return vector
        return vector_or_id
    
    def sample(self, n: int, seed: Optional[int] = None) -> List[Vector]:
        """
        Sample n random vectors from the index.
        
        Args:
            n: Number of vectors to sample
            seed: Optional random seed for reproducibility
            
        Returns:
            List of sampled Vector objects
            
        Raises:
            ValueError: If n is greater than the number of vectors in the index
        """
        with self._lock:
            index_size = self._storage.size()
            if n > index_size:
                raise ValueError(f"Cannot sample {n} vectors from an index of size {index_size}")
                
            if seed is not None:
                random.seed(seed)
                
            # Get all vector IDs
            all_ids = []
            for key in self._storage._data.keys():
                all_ids.append(str(key))
            
            sampled_ids = random.sample(all_ids, n)
            result = []
            for id in sampled_ids:
                vector = self.get(id)
                if vector:
                    result.append(vector)
            return result