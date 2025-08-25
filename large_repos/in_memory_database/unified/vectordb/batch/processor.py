"""
Batch processing engine for efficient feature retrieval and transformation.

This module provides optimized batch operations for feature retrieval
and transformation, designed for high-throughput ML inference scenarios.
"""

import concurrent.futures
from typing import Dict, List, Set, Tuple, Optional, Any, Union, Callable
import time
import threading
from collections import defaultdict
import math

from vectordb.core.vector import Vector
from vectordb.feature_store.store import FeatureStore


class BatchProcessor:
    """
    Batch processor for optimized feature operations.
    
    This class implements efficient batch operations for feature retrieval,
    vector operations, and transformations to support high-throughput
    prediction scenarios.
    """
    
    def __init__(
        self,
        feature_store: FeatureStore,
        default_batch_size: int = 100,
        max_workers: Optional[int] = None,
        use_parallelization: bool = True
    ):
        """
        Initialize a batch processor.
        
        Args:
            feature_store: The feature store to use for data retrieval
            default_batch_size: Default size for batches when not specified
            max_workers: Maximum number of worker threads for parallelization
            use_parallelization: Whether to use parallel processing
        """
        self._feature_store = feature_store
        self._default_batch_size = default_batch_size
        self._max_workers = max_workers
        self._use_parallelization = use_parallelization
        
        # For tracking performance metrics
        self._performance_metrics = {
            "batch_retrievals": 0,
            "total_entities_processed": 0,
            "total_features_processed": 0,
            "total_processing_time": 0.0,
        }
        
        # Lock for thread-safe operation
        self._lock = threading.RLock()
    
    @property
    def performance_metrics(self) -> Dict[str, Any]:
        """Get the current performance metrics."""
        with self._lock:
            metrics = self._performance_metrics.copy()
            
            # Calculate averages if we have data
            if metrics["batch_retrievals"] > 0:
                metrics["avg_entities_per_batch"] = metrics["total_entities_processed"] / metrics["batch_retrievals"]
                metrics["avg_features_per_batch"] = metrics["total_features_processed"] / metrics["batch_retrievals"]
                metrics["avg_time_per_batch"] = metrics["total_processing_time"] / metrics["batch_retrievals"]
                if metrics["total_entities_processed"] > 0:
                    metrics["avg_time_per_entity"] = metrics["total_processing_time"] / metrics["total_entities_processed"]
            
            return metrics
    
    def retrieve_batch(
        self,
        entity_ids: List[str],
        feature_names: List[str],
        version_ids: Optional[Dict[str, Dict[str, str]]] = None,
        timestamps: Optional[Dict[str, float]] = None,
        transformations: Optional[List[Callable[[Dict[str, Any]], Dict[str, Any]]]] = None,
        batch_size: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve features for multiple entities in optimized batches.
        
        Args:
            entity_ids: List of entity IDs
            feature_names: List of feature names to retrieve
            version_ids: Optional specific versions to use (entity_id -> feature_name -> version_id)
            timestamps: Optional timestamps for point-in-time retrieval (entity_id -> timestamp)
            transformations: Optional list of transformation functions to apply to each entity's features
            batch_size: Optional batch size (defaults to self._default_batch_size)
            
        Returns:
            Nested dictionary mapping entity_id -> feature_name -> value
        """
        start_time = time.time()
        
        # Use default batch size if not specified
        batch_size = batch_size or self._default_batch_size
        
        # Split entity IDs into batches
        entity_batches = self._split_into_batches(entity_ids, batch_size)
        
        results = {}
        
        if self._use_parallelization and len(entity_batches) > 1:
            # Process batches in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                # Submit batch processing tasks
                future_to_batch = {
                    executor.submit(
                        self._process_entity_batch,
                        batch,
                        feature_names,
                        version_ids,
                        timestamps,
                        transformations
                    ): i for i, batch in enumerate(entity_batches)
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_results = future.result()
                    results.update(batch_results)
        else:
            # Process batches sequentially
            for batch in entity_batches:
                batch_results = self._process_entity_batch(
                    batch,
                    feature_names,
                    version_ids,
                    timestamps,
                    transformations
                )
                results.update(batch_results)
        
        # Update performance metrics
        processing_time = time.time() - start_time
        with self._lock:
            self._performance_metrics["batch_retrievals"] += 1
            self._performance_metrics["total_entities_processed"] += len(entity_ids)
            self._performance_metrics["total_features_processed"] += len(entity_ids) * len(feature_names)
            self._performance_metrics["total_processing_time"] += processing_time
        
        return results
    
    def vector_operation_batch(
        self,
        operation: str,
        vector_features: List[Tuple[str, str]],
        entity_ids: List[str],
        result_feature: Optional[str] = None,
        version_ids: Optional[Dict[str, Dict[str, str]]] = None,
        timestamps: Optional[Dict[str, float]] = None,
        batch_size: Optional[int] = None,
        store_results: bool = False
    ) -> Dict[str, Any]:
        """
        Perform batch vector operations across entities.
        
        Args:
            operation: Vector operation to perform ('add', 'average', 'concat', etc.)
            vector_features: List of (entity_id, feature_name) tuples for vectors
            entity_ids: List of entity IDs to process
            result_feature: Optional name for storing results
            version_ids: Optional specific versions to use
            timestamps: Optional timestamps for point-in-time operations
            batch_size: Optional batch size
            store_results: Whether to store results in the feature store
            
        Returns:
            Dictionary mapping entity_id -> result vector
            
        Raises:
            ValueError: If the operation is not supported or vectors have incompatible dimensions
        """
        start_time = time.time()
        
        # Use default batch size if not specified
        batch_size = batch_size or self._default_batch_size
        
        # Split entity IDs into batches
        entity_batches = self._split_into_batches(entity_ids, batch_size)
        
        results = {}
        
        if self._use_parallelization and len(entity_batches) > 1:
            # Process batches in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                # Submit batch processing tasks
                future_to_batch = {
                    executor.submit(
                        self._process_vector_batch,
                        operation,
                        vector_features,
                        batch,
                        result_feature,
                        version_ids,
                        timestamps,
                        store_results
                    ): i for i, batch in enumerate(entity_batches)
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_results = future.result()
                    results.update(batch_results)
        else:
            # Process batches sequentially
            for batch in entity_batches:
                batch_results = self._process_vector_batch(
                    operation,
                    vector_features,
                    batch,
                    result_feature,
                    version_ids,
                    timestamps,
                    store_results
                )
                results.update(batch_results)
        
        # Update performance metrics
        processing_time = time.time() - start_time
        with self._lock:
            self._performance_metrics["batch_retrievals"] += 1
            self._performance_metrics["total_entities_processed"] += len(entity_ids)
            self._performance_metrics["total_features_processed"] += len(entity_ids) * len(vector_features)
            self._performance_metrics["total_processing_time"] += processing_time
        
        return results
    
    def similarity_search_batch(
        self,
        query_vectors: Dict[str, Vector],
        k: int = 10,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
        batch_size: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform similarity searches for multiple query vectors.
        
        Args:
            query_vectors: Dictionary mapping query_id -> Vector
            k: Number of similar vectors to find for each query
            filter_fn: Optional function to filter results
            batch_size: Optional batch size
            
        Returns:
            Dictionary mapping query_id -> list of similarity results
            
        Raises:
            ValueError: If vector operations are not supported by the feature store
        """
        start_time = time.time()
        
        # Check if vector index is available
        if getattr(self._feature_store, "vector_index", None) is None:
            raise ValueError("Feature store does not support vector operations")
        
        # Use default batch size if not specified
        batch_size = batch_size or self._default_batch_size
        
        # Split queries into batches
        query_ids = list(query_vectors.keys())
        query_batches = self._split_into_batches(query_ids, batch_size)
        
        results = {}
        
        if self._use_parallelization and len(query_batches) > 1:
            # Process batches in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                # Submit batch processing tasks
                future_to_batch = {
                    executor.submit(
                        self._process_similarity_batch,
                        {qid: query_vectors[qid] for qid in batch},
                        k,
                        filter_fn
                    ): i for i, batch in enumerate(query_batches)
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_results = future.result()
                    results.update(batch_results)
        else:
            # Process batches sequentially
            for batch in query_batches:
                batch_results = self._process_similarity_batch(
                    {qid: query_vectors[qid] for qid in batch},
                    k,
                    filter_fn
                )
                results.update(batch_results)
        
        # Update performance metrics
        processing_time = time.time() - start_time
        with self._lock:
            self._performance_metrics["batch_retrievals"] += 1
            self._performance_metrics["total_entities_processed"] += len(query_ids)
            self._performance_metrics["total_processing_time"] += processing_time
        
        return results
    
    def clear_metrics(self) -> None:
        """Reset the performance metrics."""
        with self._lock:
            self._performance_metrics = {
                "batch_retrievals": 0,
                "total_entities_processed": 0,
                "total_features_processed": 0,
                "total_processing_time": 0.0,
            }
    
    def _split_into_batches(self, items: List[Any], batch_size: int) -> List[List[Any]]:
        """
        Split a list of items into batches.
        
        Args:
            items: List of items to split
            batch_size: Size of each batch
            
        Returns:
            List of batches
        """
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    def _process_entity_batch(
        self,
        entity_batch: List[str],
        feature_names: List[str],
        version_ids: Optional[Dict[str, Dict[str, str]]],
        timestamps: Optional[Dict[str, float]],
        transformations: Optional[List[Callable[[Dict[str, Any]], Dict[str, Any]]]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process a batch of entities to retrieve their features.
        
        Args:
            entity_batch: Batch of entity IDs
            feature_names: List of feature names to retrieve
            version_ids: Optional specific versions to use
            timestamps: Optional timestamps for point-in-time retrieval
            transformations: Optional transformations to apply
            
        Returns:
            Batch results as entity_id -> feature_name -> value
        """
        # Retrieve features for this batch
        batch_results = self._feature_store.get_feature_batch(
            entity_ids=entity_batch,
            feature_names=feature_names,
            version_ids=version_ids,
            timestamps=timestamps
        )
        
        # Apply transformations if specified
        if transformations:
            for entity_id, features in batch_results.items():
                if features:  # Skip empty feature sets
                    for transform_fn in transformations:
                        # Apply transformation to features
                        features = transform_fn(features)
                    batch_results[entity_id] = features
        
        return batch_results
    
    def _process_vector_batch(
        self,
        operation: str,
        vector_features: List[Tuple[str, str]],
        entity_batch: List[str],
        result_feature: Optional[str],
        version_ids: Optional[Dict[str, Dict[str, str]]],
        timestamps: Optional[Dict[str, float]],
        store_results: bool
    ) -> Dict[str, Vector]:
        """
        Process a batch of vector operations.
        
        Args:
            operation: Vector operation to perform
            vector_features: List of (entity_id, feature_name) tuples
            entity_batch: Batch of entity IDs
            result_feature: Optional name for storing results
            version_ids: Optional specific versions
            timestamps: Optional timestamps
            store_results: Whether to store results
            
        Returns:
            Batch results as entity_id -> result vector
            
        Raises:
            ValueError: If operation is not supported or vectors are incompatible
        """
        results = {}
        
        for entity_id in entity_batch:
            # Retrieve the vectors for this entity
            vectors = []
            for feature_entity_id, feature_name in vector_features:
                # Determine which version/timestamp to use
                specific_version_id = None
                if version_ids is not None and feature_entity_id in version_ids:
                    entity_versions = version_ids[feature_entity_id]
                    if feature_name in entity_versions:
                        specific_version_id = entity_versions[feature_name]
                
                specific_timestamp = None
                if timestamps is not None and feature_entity_id in timestamps:
                    specific_timestamp = timestamps[feature_entity_id]
                
                # Get the vector
                feature_value = self._feature_store.get_feature(
                    entity_id=feature_entity_id,
                    feature_name=feature_name,
                    version_id=specific_version_id,
                    timestamp=specific_timestamp
                )
                
                if feature_value is None:
                    # Skip if vector not found
                    continue
                
                if not isinstance(feature_value, Vector):
                    # Convert to Vector if possible
                    if isinstance(feature_value, (list, tuple)) and all(isinstance(x, (int, float)) for x in feature_value):
                        feature_value = Vector(feature_value)
                    else:
                        # Skip non-vector features
                        continue
                
                vectors.append(feature_value)
            
            # Perform the operation if we have vectors
            if vectors:
                result_vector = self._vector_operation(operation, vectors)
                
                # Store the result if requested
                if store_results and result_feature is not None:
                    self._feature_store.set_feature(
                        entity_id=entity_id,
                        feature_name=result_feature,
                        value=result_vector,
                        feature_type="vector",
                        parent_features=vector_features,
                        transformation=operation
                    )
                
                results[entity_id] = result_vector
        
        return results
    
    def _process_similarity_batch(
        self,
        query_batch: Dict[str, Vector],
        k: int,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process a batch of similarity searches.
        
        Args:
            query_batch: Dictionary of query_id -> query vector
            k: Number of results per query
            filter_fn: Optional result filter function
            
        Returns:
            Dictionary of query_id -> similarity results
        """
        results = {}
        
        for query_id, query_vector in query_batch.items():
            # Perform the similarity search
            similar_vectors = self._feature_store.get_similar_vectors(
                query=query_vector,
                k=k,
                filter_fn=filter_fn
            )
            
            results[query_id] = similar_vectors
        
        return results
    
    def _vector_operation(self, operation: str, vectors: List[Vector]) -> Vector:
        """
        Perform a vector operation.
        
        Args:
            operation: Operation to perform
            vectors: List of vectors to operate on
            
        Returns:
            Result vector
            
        Raises:
            ValueError: If the operation is not supported or vectors are incompatible
        """
        if not vectors:
            raise ValueError("No vectors provided for operation")
        
        if operation == "add":
            # Vector addition
            result = vectors[0]
            for vec in vectors[1:]:
                result = result.add(vec)
            return result
            
        elif operation == "average" or operation == "mean":
            # Vector averaging
            result = vectors[0]
            for vec in vectors[1:]:
                result = result.add(vec)
            return result.scale(1.0 / len(vectors))
            
        elif operation == "subtract":
            # Vector subtraction (only works with 2 vectors)
            if len(vectors) != 2:
                raise ValueError("Subtract operation requires exactly 2 vectors")
            return vectors[0].subtract(vectors[1])
            
        elif operation == "scale":
            # Scale vector by a constant (second "vector" must be a scalar)
            if len(vectors) != 2:
                raise ValueError("Scale operation requires exactly 2 inputs")
            if vectors[1].dimension != 1:
                raise ValueError("Second input for scale operation must be a scalar (1D vector)")
            return vectors[0].scale(vectors[1][0])
            
        elif operation == "normalize":
            # Normalize each vector and average
            normalized = [vec.normalize() for vec in vectors]
            result = normalized[0]
            for vec in normalized[1:]:
                result = result.add(vec)
            return result.scale(1.0 / len(vectors))
            
        else:
            raise ValueError(f"Unsupported vector operation: {operation}")
            
    def submit_batch_job(
        self,
        job_type: str,
        params: Dict[str, Any],
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> str:
        """
        Submit an asynchronous batch job.
        
        Args:
            job_type: Type of batch job to run
            params: Parameters for the job
            callback: Optional callback function for when the job completes
            
        Returns:
            Job ID
            
        Note: This is a simplified version that just runs the job in a thread.
        A real implementation would use a proper job queue and worker pool.
        """
        # Create a unique job ID
        job_id = f"job_{time.time()}_{hash(str(params))}"
        
        # Define the job function
        def run_job():
            try:
                result = None
                
                if job_type == "retrieve":
                    result = self.retrieve_batch(
                        entity_ids=params.get("entity_ids", []),
                        feature_names=params.get("feature_names", []),
                        version_ids=params.get("version_ids"),
                        timestamps=params.get("timestamps"),
                        transformations=params.get("transformations"),
                        batch_size=params.get("batch_size")
                    )
                    
                elif job_type == "vector_operation":
                    result = self.vector_operation_batch(
                        operation=params.get("operation", "add"),
                        vector_features=params.get("vector_features", []),
                        entity_ids=params.get("entity_ids", []),
                        result_feature=params.get("result_feature"),
                        version_ids=params.get("version_ids"),
                        timestamps=params.get("timestamps"),
                        batch_size=params.get("batch_size"),
                        store_results=params.get("store_results", False)
                    )
                    
                elif job_type == "similarity_search":
                    result = self.similarity_search_batch(
                        query_vectors=params.get("query_vectors", {}),
                        k=params.get("k", 10),
                        filter_fn=params.get("filter_fn"),
                        batch_size=params.get("batch_size")
                    )
                    
                else:
                    raise ValueError(f"Unsupported job type: {job_type}")
                
                # Call the callback with the result
                if callback:
                    callback({"job_id": job_id, "status": "completed", "result": result})
                    
            except Exception as e:
                # Call the callback with the error
                if callback:
                    callback({"job_id": job_id, "status": "failed", "error": str(e)})
        
        # Start the job in a separate thread
        thread = threading.Thread(target=run_job)
        thread.daemon = True
        thread.start()
        
        return job_id