"""
Feature store implementation for ML features with versioning and lineage tracking.

This module provides a feature store optimized for machine learning applications,
supporting efficient feature storage and retrieval with versioning,
lineage tracking, and vector operations.
"""

import time
import uuid
import json
from typing import Dict, List, Set, Tuple, Optional, Any, Union, Callable
from datetime import datetime
import threading
import copy

from vectordb.core.vector import Vector
from vectordb.indexing.index import VectorIndex
from vectordb.indexing.approximate_nn import ApproximateNearestNeighbor
from vectordb.feature_store.version import VersionManager
from vectordb.feature_store.lineage import LineageTracker
from common.core.storage import InMemoryStore
# from common.utils.threading import RWLock
from threading import RLock
from common.utils.validation import Validator, ValidationError
from common.query import QueryBuilder


class FeatureStore:
    """
    Feature store with versioning and lineage tracking.
    
    This class provides a comprehensive feature store optimized for ML
    applications, supporting feature versioning, lineage tracking,
    and efficient vector operations.
    """
    
    def __init__(
        self,
        vector_dimension: Optional[int] = None,
        distance_metric: str = "euclidean",
        max_versions_per_feature: Optional[int] = 10,
        approximate_search: bool = True
    ):
        """
        Initialize a feature store.
        
        Args:
            vector_dimension: Optional dimension for vector features
            distance_metric: Distance metric for vector comparisons
            max_versions_per_feature: Maximum versions to retain per feature
            approximate_search: Whether to use approximate nearest neighbor search
        """
        self._version_manager = VersionManager(max_versions_per_feature)
        self._lineage_tracker = LineageTracker()
        
        # Vector index for vectors (only created when needed)
        self._vector_dimension = vector_dimension
        self._distance_metric = distance_metric
        self._approximate_search = approximate_search
        self._vector_index = None
        
        # Use common library storage for metadata
        self._entity_storage = InMemoryStore()
        self._feature_metadata_storage = InMemoryStore()
        
        # Maintain backward compatibility with tests
        self._entity_metadata: Dict[str, Dict[str, Any]] = {}
        self._features: Dict[str, Dict[str, Any]] = {}
        
        # Track feature types for schema management
        self._feature_types: Dict[str, str] = {}
        
        # For concurrent access - use common library RWLock
        self._lock = RLock()  # Using RLock for simplicity
        
        # Last modified timestamp
        self._last_modified = time.time()
    
    @property
    def last_modified(self) -> float:
        """Get the timestamp of the last modification to the store."""
        return self._last_modified
    
    @property
    def vector_index(self) -> Union[VectorIndex, ApproximateNearestNeighbor, None]:
        """
        Get the vector index, creating it if necessary.
        
        Returns:
            The vector index, or None if vector dimension is not set
        """
        if self._vector_index is None and self._vector_dimension is not None:
            if self._approximate_search:
                self._vector_index = ApproximateNearestNeighbor(
                    dimensions=self._vector_dimension,
                    distance_metric=self._distance_metric
                )
            else:
                self._vector_index = VectorIndex(distance_metric=self._distance_metric)
                
        return self._vector_index
    
    def add_entity(
        self,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new entity to the store.
        
        Args:
            entity_id: Optional unique identifier for the entity
            metadata: Optional metadata for the entity
            
        Returns:
            The entity ID
        """
        with self._lock:
            # Generate ID if not provided
            if entity_id is None:
                entity_id = str(uuid.uuid4())
            
            # Validate entity metadata if provided
            if metadata is not None:
                try:
                    # Basic validation for metadata
                    validator = Validator().type_check(dict)
                    validator.validate(metadata)
                except ValidationError as e:
                    raise ValueError(f"Invalid entity metadata: {e}")
                
            # Store entity metadata using common storage
            self._entity_storage.insert(entity_id, metadata or {})
            
            # Maintain backward compatibility
            self._entity_metadata[entity_id] = metadata or {}
            if entity_id not in self._features:
                self._features[entity_id] = {}
            
            self._last_modified = time.time()
            return entity_id
    
    def set_feature(
        self,
        entity_id: str,
        feature_name: str,
        value: Any,
        feature_type: Optional[str] = None,
        version_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_features: Optional[List[Tuple[str, str]]] = None,
        transformation: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Set a feature value with versioning and lineage tracking.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            value: Value of the feature
            feature_type: Optional type of the feature (e.g., "scalar", "vector")
            version_id: Optional unique identifier for this version
            timestamp: Optional creation timestamp
            created_by: Optional identifier of the creator
            description: Optional description of this version
            metadata: Optional additional metadata
            parent_features: Optional list of (entity_id, feature_name) tuples for lineage
            transformation: Optional name of the transformation that created this feature
            parameters: Optional parameters of the transformation
            
        Returns:
            ID of the feature version
            
        Raises:
            ValueError: If the feature type is incompatible or vectors have wrong dimensions
            KeyError: If the entity doesn't exist
        """
        with self._lock:
            # Ensure entity exists
            if self._entity_storage.get(entity_id) is None:
                self.add_entity(entity_id)
            
            # Determine feature type if not provided
            if feature_type is None:
                if isinstance(value, Vector):
                    feature_type = "vector"
                elif isinstance(value, (list, tuple)) and all(isinstance(x, (int, float)) for x in value):
                    feature_type = "vector"
                    # Convert to Vector object
                    if not isinstance(value, Vector):
                        value = Vector(value)
                else:
                    feature_type = "scalar"
            
            # Validate vector features
            if feature_type == "vector":
                # Ensure value is a Vector object
                if not isinstance(value, Vector):
                    if isinstance(value, (list, tuple)) and all(isinstance(x, (int, float)) for x in value):
                        value = Vector(value)
                    else:
                        raise ValueError(f"Vector feature requires a Vector object or numeric list/tuple, got {type(value)}")
                
                # Check vector dimension
                if self._vector_dimension is not None and value.dimension != self._vector_dimension:
                    raise ValueError(f"Vector dimension mismatch: expected {self._vector_dimension}, got {value.dimension}")
            
            # Record feature type
            self._feature_types[feature_name] = feature_type
            
            # Add feature metadata if not exists
            try:
                existing_metadata = self._feature_metadata_storage.get(feature_name)
                if existing_metadata is None:
                    self._feature_metadata_storage.insert(feature_name, {"type": feature_type})
            except KeyError:
                self._feature_metadata_storage.insert(feature_name, {"type": feature_type})
            
            # Add version with the feature value
            version = self._version_manager.add_version(
                entity_id=entity_id,
                feature_name=feature_name,
                value=value,
                version_id=version_id,
                timestamp=timestamp,
                created_by=created_by,
                description=description,
                metadata=metadata
            )
            
            # Maintain backward compatibility with _features dict
            if entity_id not in self._features:
                self._features[entity_id] = {}
                self._entity_metadata[entity_id] = {}
            self._features[entity_id][feature_name] = value
            
            # Track lineage if parent features are provided
            if parent_features or transformation:
                self._track_feature_lineage(
                    entity_id=entity_id,
                    feature_name=feature_name,
                    version_id=version.version_id,
                    parent_features=parent_features,
                    transformation=transformation,
                    parameters=parameters,
                    timestamp=timestamp or version.timestamp,
                    created_by=created_by
                )
            
            # Add to vector index if it's a vector feature
            if feature_type == "vector" and self.vector_index is not None:
                # Create a unique ID for the vector
                vector_id = f"{entity_id}:{feature_name}:{version.version_id}"
                
                # Add to vector index with metadata
                vec_metadata = {
                    "entity_id": entity_id,
                    "feature_name": feature_name,
                    "version_id": version.version_id,
                    "timestamp": version.timestamp
                }
                if metadata:
                    vec_metadata.update(metadata)
                
                self.vector_index.add(value, vec_metadata)
            
            self._last_modified = time.time()
            return version.version_id
    
    def get_feature(
        self,
        entity_id: str,
        feature_name: str,
        version_id: Optional[str] = None,
        version_number: Optional[int] = None,
        timestamp: Optional[float] = None,
        default: Any = None
    ) -> Any:
        """
        Get a feature value.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            version_id: Optional specific version ID to retrieve
            version_number: Optional version number (0 is most recent, 1 is previous, etc.)
            timestamp: Optional timestamp to get the value at a specific time
            default: Value to return if the feature is not found
            
        Returns:
            The feature value if found, default otherwise
        """
        with self._lock:
            return self._version_manager.get_value(
                entity_id=entity_id,
                feature_name=feature_name,
                version_id=version_id,
                version_number=version_number,
                timestamp=timestamp,
                default=default
            )
    
    def get_feature_batch(
        self,
        entity_ids: List[str],
        feature_names: List[str],
        version_ids: Optional[Dict[str, Dict[str, str]]] = None,
        timestamps: Optional[Dict[str, float]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get feature values for multiple entities and features.
        
        Args:
            entity_ids: List of entity IDs
            feature_names: List of feature names
            version_ids: Optional mapping of entity_id -> feature_name -> version_id
            timestamps: Optional mapping of entity_id -> timestamp
            
        Returns:
            Nested dictionary of entity_id -> feature_name -> value
        """
        with self._lock:
            result: Dict[str, Dict[str, Any]] = {}
            
            for entity_id in entity_ids:
                result[entity_id] = {}
                
                for feature_name in feature_names:
                    # Determine version ID or timestamp for this feature
                    specific_version_id = None
                    specific_timestamp = None
                    
                    if version_ids is not None and entity_id in version_ids:
                        entity_versions = version_ids[entity_id]
                        if feature_name in entity_versions:
                            specific_version_id = entity_versions[feature_name]
                    
                    if timestamps is not None and entity_id in timestamps:
                        specific_timestamp = timestamps[entity_id]
                    
                    # Get the feature value
                    value = self.get_feature(
                        entity_id=entity_id,
                        feature_name=feature_name,
                        version_id=specific_version_id,
                        timestamp=specific_timestamp
                    )
                    
                    if value is not None:
                        result[entity_id][feature_name] = value
            
            return result
    
    def get_feature_history(
        self,
        entity_id: str,
        feature_name: str,
        limit: Optional[int] = None,
        since_timestamp: Optional[float] = None,
        until_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the version history of a feature.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            limit: Optional maximum number of versions to return
            since_timestamp: Optional filter for versions after this time
            until_timestamp: Optional filter for versions before this time
            
        Returns:
            List of feature version dictionaries, sorted by timestamp (most recent first)
        """
        with self._lock:
            versions = self._version_manager.get_history(
                entity_id=entity_id,
                feature_name=feature_name,
                limit=limit,
                since_timestamp=since_timestamp,
                until_timestamp=until_timestamp
            )
            
            # Convert to dictionaries with full information
            return [version.to_dict() for version in versions]
    
    def get_feature_lineage(
        self,
        entity_id: str,
        feature_name: str,
        version_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the lineage history of a feature.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            version_id: Optional specific version ID to retrieve
            
        Returns:
            List of transformations that led to this feature
            
        Raises:
            ValueError: If the feature or version doesn't exist
        """
        with self._lock:
            # Get the specific version
            version = self._version_manager.get_version(
                entity_id=entity_id,
                feature_name=feature_name,
                version_id=version_id
            )
            
            if version is None:
                raise ValueError(f"Feature {feature_name} for entity {entity_id} not found")
            
            # Create a node ID for this feature version
            node_id = f"{entity_id}:{feature_name}:{version.version_id}"
            
            # Get lineage nodes if they exist
            try:
                return self._lineage_tracker.get_node_history(node_id)
            except ValueError:
                # No lineage information for this feature
                return []
    
    def get_similar_vectors(
        self,
        query: Union[str, Vector, Tuple[str, str, Optional[str]]],
        k: int = 10,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar vectors to a query.
        
        Args:
            query: Either a Vector object, a vector ID in the form "entity_id:feature_name",
                  or a tuple of (entity_id, feature_name, version_id) where version_id is optional
            k: Number of similar vectors to return
            filter_fn: Optional function to filter results based on metadata
            
        Returns:
            List of dictionaries with entity_id, feature_name, version_id, distance, and metadata
            
        Raises:
            ValueError: If the vector index is not available or the query is invalid
        """
        with self._lock:
            if self.vector_index is None:
                raise ValueError("Vector index is not available")
            
            # Process the query
            query_vector = None
            
            if isinstance(query, Vector):
                # Direct vector query
                query_vector = query
                
            elif isinstance(query, str):
                # ID-based query (entity_id:feature_name)
                parts = query.split(":")
                if len(parts) < 2:
                    raise ValueError("Invalid query format. Expected 'entity_id:feature_name[:version_id]'")
                
                entity_id = parts[0]
                feature_name = parts[1]
                version_id = parts[2] if len(parts) > 2 else None
                
                # Get the vector
                feature_value = self.get_feature(
                    entity_id=entity_id,
                    feature_name=feature_name,
                    version_id=version_id
                )
                
                if not isinstance(feature_value, Vector):
                    raise ValueError(f"Feature {feature_name} for entity {entity_id} is not a vector")
                
                query_vector = feature_value
                
            elif isinstance(query, tuple) and len(query) >= 2:
                # Tuple-based query (entity_id, feature_name, [version_id])
                entity_id = query[0]
                feature_name = query[1]
                version_id = query[2] if len(query) > 2 else None
                
                # Get the vector
                feature_value = self.get_feature(
                    entity_id=entity_id,
                    feature_name=feature_name,
                    version_id=version_id
                )
                
                if not isinstance(feature_value, Vector):
                    raise ValueError(f"Feature {feature_name} for entity {entity_id} is not a vector")
                
                query_vector = feature_value
            
            else:
                raise ValueError("Invalid query format")
            
            # Define a filter adapter if needed
            metadata_filter = None
            if filter_fn is not None:
                def metadata_filter(vec_id: str, metadata: Dict[str, Any]) -> bool:
                    return filter_fn(metadata)
            
            # Get similar vectors
            if isinstance(self.vector_index, ApproximateNearestNeighbor):
                results = self.vector_index.nearest_with_metadata(query_vector, k, metadata_filter)
            else:
                results = self.vector_index.nearest_with_metadata(query_vector, k, metadata_filter)
            
            # Format results
            formatted_results = []
            for _, distance, metadata in results:
                formatted_results.append({
                    "entity_id": metadata.get("entity_id"),
                    "feature_name": metadata.get("feature_name"),
                    "version_id": metadata.get("version_id"),
                    "distance": distance,
                    "metadata": metadata
                })
            
            return formatted_results
    
    def delete_feature(
        self,
        entity_id: str,
        feature_name: str,
        delete_lineage: bool = False
    ) -> bool:
        """
        Delete a feature and all its versions.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            delete_lineage: Whether to delete lineage information
            
        Returns:
            True if the feature was deleted, False if it didn't exist
        """
        with self._lock:
            # Check if the feature exists
            if not self._version_manager.has_feature(entity_id, feature_name):
                return False
            
            # Get all versions to remove from vector index
            feature_history = self._version_manager.get_history(entity_id, feature_name)
            
            # Remove from vector index if applicable
            if self.vector_index is not None:
                for version in feature_history:
                    if self._feature_types.get(feature_name) == "vector":
                        # Construct vector ID
                        vector_id = f"{entity_id}:{feature_name}:{version.version_id}"
                        
                        # Remove from index
                        self.vector_index.remove(vector_id)
            
            # Delete lineage if requested
            if delete_lineage:
                for version in feature_history:
                    node_id = f"{entity_id}:{feature_name}:{version.version_id}"
                    try:
                        self._lineage_tracker.delete_node(node_id, cascade=True)
                    except ValueError:
                        # Node might not exist in lineage tracker
                        pass
            
            # Delete from version manager
            self._version_manager.delete_history(entity_id, feature_name)
            
            self._last_modified = time.time()
            return True
    
    def delete_entity(
        self,
        entity_id: str,
        delete_lineage: bool = False
    ) -> bool:
        """
        Delete an entity and all its features.
        
        Args:
            entity_id: ID of the entity
            delete_lineage: Whether to delete lineage information
            
        Returns:
            True if the entity was deleted, False if it didn't exist
        """
        with self._lock:
            # Check if the entity exists
            if self._entity_storage.get(entity_id) is None:
                return False
            
            # Get all features for this entity
            features = self._version_manager.get_features(entity_id)
            
            # Delete each feature
            for feature_name in features:
                self.delete_feature(entity_id, feature_name, delete_lineage)
            
            # Remove entity metadata
            self._entity_storage.delete(entity_id)
            
            self._last_modified = time.time()
            return True
    
    def get_entities(self) -> List[str]:
        """
        Get all entity IDs in the store.
        
        Returns:
            List of entity IDs
        """
        with self._lock:
            # Get all entity IDs from storage
            entity_ids = []
            for key in self._entity_storage._data.keys():
                entity_ids.append(str(key))
            return entity_ids
    
    def get_features(self, entity_id: Optional[str] = None) -> List[str]:
        """
        Get all feature names.
        
        Args:
            entity_id: Optional specific entity to get features for
            
        Returns:
            List of feature names
        """
        with self._lock:
            if entity_id is not None:
                return self._version_manager.get_features(entity_id)
            
            # If no entity specified, return all unique feature names
            all_features = set()
            entity_ids = self.get_entities()
            for eid in entity_ids:
                all_features.update(self._version_manager.get_features(eid))
            
            return list(all_features)
    
    def get_entity_metadata(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Entity metadata dictionary if found, None otherwise
        """
        with self._lock:
            return self._entity_storage.get(entity_id)
    
    def set_entity_metadata(self, entity_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Set metadata for an entity.
        
        Args:
            entity_id: ID of the entity
            metadata: Metadata dictionary
            
        Returns:
            True if the metadata was set, False if the entity wasn't found
        """
        with self._lock:
            if self._entity_storage.get(entity_id) is None:
                return False
            
            # Validate metadata
            if metadata is not None:
                try:
                    validator = Validator().type_check(dict)
                    validator.validate(metadata)
                except ValidationError as e:
                    raise ValueError(f"Invalid entity metadata: {e}")
            
            self._entity_storage.update(entity_id, metadata)
            self._last_modified = time.time()
            return True
    
    def get_feature_metadata(self, feature_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a feature.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            Feature metadata dictionary if found, None otherwise
        """
        with self._lock:
            return self._feature_metadata_storage.get(feature_name)
    
    def set_feature_metadata(self, feature_name: str, metadata: Dict[str, Any]) -> bool:
        """
        Set metadata for a feature.
        
        Args:
            feature_name: Name of the feature
            metadata: Metadata dictionary
            
        Returns:
            True if the metadata was set, False if the feature wasn't found
        """
        with self._lock:
            existing_metadata = self._feature_metadata_storage.get(feature_name)
            if existing_metadata is None:
                return False
            
            # Validate metadata
            if metadata is not None:
                try:
                    validator = Validator().type_check(dict)
                    validator.validate(metadata)
                except ValidationError as e:
                    raise ValueError(f"Invalid feature metadata: {e}")
            
            # Preserve the feature type
            feature_type = existing_metadata.get("type")
            if feature_type is not None:
                metadata["type"] = feature_type
            
            self._feature_metadata_storage.update(feature_name, metadata)
            self._last_modified = time.time()
            return True
    
    def _track_feature_lineage(
        self,
        entity_id: str,
        feature_name: str,
        version_id: str,
        parent_features: Optional[List[Tuple[str, str]]] = None,
        transformation: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
        created_by: Optional[str] = None
    ) -> None:
        """
        Track the lineage of a feature.
        
        Args:
            entity_id: ID of the entity
            feature_name: Name of the feature
            version_id: ID of the feature version
            parent_features: List of (entity_id, feature_name) tuples for parent features
            transformation: Name of the transformation
            parameters: Parameters of the transformation
            timestamp: Creation timestamp
            created_by: Identifier of the creator
        """
        # Create a node for this feature version
        feature_node_id = f"{entity_id}:{feature_name}:{version_id}"
        feature_node = self._lineage_tracker.add_node(
            node_type="feature",
            name=f"{entity_id}:{feature_name}",
            node_id=feature_node_id,
            timestamp=timestamp,
            created_by=created_by,
            metadata={"entity_id": entity_id, "feature_name": feature_name, "version_id": version_id}
        )
        
        # Process parent features
        parent_node_ids = []
        if parent_features:
            for parent_entity_id, parent_feature_name in parent_features:
                # Get the latest version of the parent feature
                parent_version = self._version_manager.get_version(
                    entity_id=parent_entity_id,
                    feature_name=parent_feature_name
                )
                
                if parent_version is not None:
                    parent_node_id = f"{parent_entity_id}:{parent_feature_name}:{parent_version.version_id}"
                    
                    # Check if parent node exists, create if not
                    if self._lineage_tracker.get_node(parent_node_id) is None:
                        self._lineage_tracker.add_node(
                            node_type="feature",
                            name=f"{parent_entity_id}:{parent_feature_name}",
                            node_id=parent_node_id,
                            timestamp=parent_version.timestamp,
                            created_by=parent_version.created_by,
                            metadata={
                                "entity_id": parent_entity_id,
                                "feature_name": parent_feature_name,
                                "version_id": parent_version.version_id
                            }
                        )
                    
                    parent_node_ids.append(parent_node_id)
        
        # Add transformation node if applicable
        if transformation:
            transform_metadata = {"transformation": transformation}
            if parameters:
                transform_metadata["parameters"] = parameters
            
            self._lineage_tracker.add_transformation(
                transform_name=transformation,
                inputs=parent_node_ids,
                outputs=[feature_node_id],
                parameters=parameters,
                created_by=created_by,
                timestamp=timestamp,
                metadata=transform_metadata
            )