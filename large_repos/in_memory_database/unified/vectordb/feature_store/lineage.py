"""
Feature lineage tracking implementation.

This module provides mechanisms for tracking data lineage and transformation
history to ensure reproducibility and auditability of feature transformations.
"""

import time
import uuid
from typing import Dict, List, Set, Optional, Any, Tuple, Union
from datetime import datetime

from common.core.storage import InMemoryStore
from common.core.serialization import Serializable
# from common.utils.threading import RWLock
from threading import RLock


class LineageNode(Serializable):
    """
    Represents a node in the feature lineage graph.
    
    This class tracks a feature's origin, transformations applied,
    and dependencies on other features or data sources.
    """
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        node_type: str = "feature",
        name: Optional[str] = None,
        timestamp: Optional[float] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a lineage node.
        
        Args:
            node_id: Optional unique identifier for this node
            node_type: Type of node (e.g., "feature", "transformation", "source")
            name: Optional name or identifier for this node
            timestamp: Optional creation timestamp (defaults to current time)
            created_by: Optional identifier of the creator
            metadata: Optional additional metadata
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.node_type = node_type
        self.name = name
        self.timestamp = timestamp or time.time()
        self.created_by = created_by
        self.metadata = metadata or {}
        
        # Track relationships between nodes
        self.parents: List[str] = []  # IDs of parent nodes
        self.children: List[str] = []  # IDs of child nodes
        
    @property
    def created_at(self) -> datetime:
        """Get the creation time as a datetime object."""
        # Use UTC timestamp to avoid timezone issues
        return datetime.utcfromtimestamp(self.timestamp).replace(microsecond=0)
    
    def add_parent(self, parent_id: str) -> None:
        """
        Add a parent node.
        
        Args:
            parent_id: ID of the parent node
        """
        if parent_id not in self.parents:
            self.parents.append(parent_id)
    
    def add_child(self, child_id: str) -> None:
        """
        Add a child node.
        
        Args:
            child_id: ID of the child node
        """
        if child_id not in self.children:
            self.children.append(child_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this node to a dictionary.
        
        Returns:
            Dictionary representation of this node
        """
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "timestamp": self.timestamp,
            "created_by": self.created_by,
            "metadata": self.metadata,
            "parents": self.parents,
            "children": self.children
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LineageNode':
        """
        Create a LineageNode from a dictionary.
        
        Args:
            data: Dictionary containing node data
            
        Returns:
            A new LineageNode instance
        """
        node = cls(
            node_id=data["node_id"],
            node_type=data["node_type"],
            name=data.get("name"),
            timestamp=data["timestamp"],
            created_by=data.get("created_by"),
            metadata=data.get("metadata", {})
        )
        
        # Set relationships
        node.parents = data.get("parents", [])
        node.children = data.get("children", [])
        
        return node


class LineageTracker:
    """
    Tracks feature lineage and transformation history.
    
    This class maintains a graph of feature transformations and dependencies,
    allowing for tracing the origins and transformations of features.
    Uses common library storage for thread-safe operations.
    """
    
    def __init__(self):
        """Initialize a lineage tracker."""
        self._storage = InMemoryStore()
        self._lock = RLock()  # Using RLock for simplicity
        
        # Maintain _nodes dict for backward compatibility with tests
        self._nodes: Dict[str, LineageNode] = {}
        
    def add_node(
        self,
        node_type: str,
        name: Optional[str] = None,
        node_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parents: Optional[List[str]] = None
    ) -> LineageNode:
        """
        Add a node to the lineage graph.
        
        Args:
            node_type: Type of node (e.g., "feature", "transformation", "source")
            name: Optional name or identifier for this node
            node_id: Optional unique identifier for this node
            timestamp: Optional creation timestamp
            created_by: Optional identifier of the creator
            metadata: Optional additional metadata
            parents: Optional list of parent node IDs
            
        Returns:
            The created LineageNode
            
        Raises:
            ValueError: If a parent node doesn't exist
        """
        # Create the node
        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            timestamp=timestamp,
            created_by=created_by,
            metadata=metadata
        )
        
        # Add to the storage
        with self._lock:
            self._storage.insert(node.node_id, node)
            # Maintain backward compatibility
            self._nodes[node.node_id] = node
        
        # Set up parent-child relationships
        if parents:
            for parent_id in parents:
                self.add_edge(parent_id, node.node_id)
        
        return node
    
    def add_edge(self, parent_id: str, child_id: str) -> None:
        """
        Add an edge between two nodes.
        
        Args:
            parent_id: ID of the parent node
            child_id: ID of the child node
            
        Raises:
            ValueError: If either node doesn't exist
        """
        with self._lock:
            parent = self._storage.get(parent_id)
            child = self._storage.get(child_id)
            
            if parent is None:
                raise ValueError(f"Parent node {parent_id} does not exist")
            if child is None:
                raise ValueError(f"Child node {child_id} does not exist")
            
            # Update parent node
            parent.add_child(child_id)
            self._storage.update(parent_id, parent)
            
            # Update child node
            child.add_parent(parent_id)
            self._storage.update(child_id, child)
    
    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """
        Get a node by its ID.
        
        Args:
            node_id: ID of the node
            
        Returns:
            The LineageNode if found, None otherwise
        """
        with self._lock:
            return self._storage.get(node_id)
    
    def get_ancestors(self, node_id: str, max_depth: Optional[int] = None) -> Dict[str, LineageNode]:
        """
        Get all ancestors of a node.
        
        Args:
            node_id: ID of the node
            max_depth: Optional maximum depth to traverse (None for unlimited)
            
        Returns:
            Dictionary of ancestor_id -> LineageNode
            
        Raises:
            ValueError: If the node doesn't exist
        """
        with self._lock:
            start_node = self._storage.get(node_id)
            if start_node is None:
                raise ValueError(f"Node {node_id} does not exist")
            
            ancestors: Dict[str, LineageNode] = {}
            visited: Set[str] = set()
            
            def dfs(current_id: str, depth: int = 0) -> None:
                """Depth-first search to find ancestors."""
                if current_id in visited:
                    return
                
                visited.add(current_id)
                current = self._storage.get(current_id)
                if current is None:
                    return
                
                for parent_id in current.parents:
                    parent = self._storage.get(parent_id)
                    if parent and (max_depth is None or depth < max_depth):
                        ancestors[parent_id] = parent
                        dfs(parent_id, depth + 1)
            
            dfs(node_id)
            return ancestors
    
    def get_descendants(self, node_id: str, max_depth: Optional[int] = None) -> Dict[str, LineageNode]:
        """
        Get all descendants of a node.
        
        Args:
            node_id: ID of the node
            max_depth: Optional maximum depth to traverse (None for unlimited)
            
        Returns:
            Dictionary of descendant_id -> LineageNode
            
        Raises:
            ValueError: If the node doesn't exist
        """
        with self._lock:
            start_node = self._storage.get(node_id)
            if start_node is None:
                raise ValueError(f"Node {node_id} does not exist")
            
            descendants: Dict[str, LineageNode] = {}
            visited: Set[str] = set()
            
            def dfs(current_id: str, depth: int = 0) -> None:
                """Depth-first search to find descendants."""
                if current_id in visited:
                    return
                
                visited.add(current_id)
                current = self._storage.get(current_id)
                if current is None:
                    return
                
                for child_id in current.children:
                    child = self._storage.get(child_id)
                    if child and (max_depth is None or depth < max_depth):
                        descendants[child_id] = child
                        dfs(child_id, depth + 1)
            
            dfs(node_id)
            return descendants
    
    def get_lineage_path(self, start_id: str, end_id: str) -> List[str]:
        """
        Find a path between two nodes in the lineage graph.
        
        Args:
            start_id: ID of the starting node
            end_id: ID of the ending node
            
        Returns:
            List of node IDs forming a path from start to end,
            or an empty list if no path exists
            
        Raises:
            ValueError: If either node doesn't exist
        """
        with self._lock:
            if self._storage.get(start_id) is None:
                raise ValueError(f"Start node {start_id} does not exist")
            if self._storage.get(end_id) is None:
                raise ValueError(f"End node {end_id} does not exist")
        
        # Check if there's a path from start to end (descendant path)
        descendants = self.get_descendants(start_id)
        if end_id in descendants:
            # If end is a descendant of start, find the path using BFS
            return self._find_path(start_id, end_id, forward=True)
        
        # Check if there's a path from end to start (ancestor path)
        ancestors = self.get_ancestors(end_id)
        if start_id in ancestors:
            # If start is an ancestor of end, find the path
            path = self._find_path(end_id, start_id, forward=False)
            return list(reversed(path))
        
        # No path exists
        return []
    
    def _find_path(self, start_id: str, end_id: str, forward: bool = True) -> List[str]:
        """
        Find a path between two nodes using BFS.
        
        Args:
            start_id: ID of the starting node
            end_id: ID of the ending node
            forward: If True, follow child links; if False, follow parent links
            
        Returns:
            List of node IDs forming a path from start to end
        """
        # Simple BFS implementation
        queue: List[Tuple[str, List[str]]] = [(start_id, [start_id])]
        visited: Set[str] = {start_id}
        
        while queue:
            current_id, path = queue.pop(0)
            
            # Get next nodes based on direction
            current_node = self._storage.get(current_id)
            if current_node is None:
                continue
                
            next_nodes = (current_node.children if forward else current_node.parents)
            
            for next_id in next_nodes:
                if next_id not in visited and self._storage.get(next_id) is not None:
                    new_path = path + [next_id]
                    
                    if next_id == end_id:
                        return new_path
                    
                    visited.add(next_id)
                    queue.append((next_id, new_path))
        
        # No path found
        return []
    
    def add_transformation(
        self,
        transform_name: str,
        inputs: List[str],
        outputs: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a transformation that generated new features from input features.
        
        Args:
            transform_name: Name of the transformation
            inputs: List of input node IDs
            outputs: List of output node IDs
            parameters: Optional parameters used in the transformation
            created_by: Optional identifier of the creator
            timestamp: Optional creation timestamp
            metadata: Optional additional metadata
            
        Returns:
            ID of the transformation node
            
        Raises:
            ValueError: If input or output nodes don't exist
        """
        # Check that all input nodes exist
        with self._lock:
            for node_id in inputs:
                if self._storage.get(node_id) is None:
                    raise ValueError(f"Input node {node_id} does not exist")
        
        # Create transformation metadata
        transform_metadata = metadata or {}
        if parameters:
            transform_metadata["parameters"] = parameters
        
        # Create transformation node
        transform_node = self.add_node(
            node_type="transformation",
            name=transform_name,
            timestamp=timestamp,
            created_by=created_by,
            metadata=transform_metadata,
            parents=inputs
        )
        
        # Connect outputs to the transformation
        for output_id in outputs:
            # Ensure the output node exists
            with self._lock:
                if self._storage.get(output_id) is None:
                    raise ValueError(f"Output node {output_id} does not exist")
            
            # Link transformation to output
            self.add_edge(transform_node.node_id, output_id)
        
        return transform_node.node_id
    
    def get_node_history(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Get the full history of transformations that led to a node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            List of transformation dictionaries in chronological order
            
        Raises:
            ValueError: If the node doesn't exist
        """
        with self._lock:
            if self._storage.get(node_id) is None:
                raise ValueError(f"Node {node_id} does not exist")
        
        ancestors = self.get_ancestors(node_id)
        
        # Get all transformation nodes that contributed to this node
        transformations = [
            {
                "node_id": node.node_id,
                "name": node.name,
                "type": node.node_type,
                "timestamp": node.timestamp,
                "created_by": node.created_by,
                "metadata": node.metadata,
                "inputs": node.parents,
                "outputs": node.children
            }
            for node in ancestors.values()
            if node.node_type == "transformation"
        ]
        
        # Sort by timestamp
        return sorted(transformations, key=lambda x: x["timestamp"])
    
    def get_all_nodes(self, node_type: Optional[str] = None) -> Dict[str, LineageNode]:
        """
        Get all nodes in the lineage graph, optionally filtered by type.
        
        Args:
            node_type: Optional type to filter by
            
        Returns:
            Dictionary of node_id -> LineageNode
        """
        with self._lock:
            # Query all nodes from storage
            all_data = self._storage.query()
            
            result = {}
            for node in all_data:
                if isinstance(node, LineageNode):
                    if node_type is None or node.node_type == node_type:
                        result[node.node_id] = node
            
            return result
    
    def delete_node(self, node_id: str, cascade: bool = False) -> int:
        """
        Delete a node from the lineage graph.
        
        Args:
            node_id: ID of the node to delete
            cascade: If True, also delete all descendants
            
        Returns:
            Number of nodes deleted
            
        Raises:
            ValueError: If the node doesn't exist
        """
        with self._lock:
            if self._storage.get(node_id) is None:
                raise ValueError(f"Node {node_id} does not exist")
            
            deleted_count = 0
            
            if cascade:
                # Delete all descendants as well
                descendants = self.get_descendants(node_id)
                
                # Start with leaf nodes and work backwards
                nodes_to_delete = list(descendants.keys()) + [node_id]
                
                # Topological sort would be better, but for simplicity we'll
                # just delete the nodes and handle the broken references
                for delete_id in nodes_to_delete:
                    if self._storage.get(delete_id) is not None:
                        self._remove_node_references(delete_id)
                        self._storage.delete(delete_id)
                        deleted_count += 1
            else:
                # Just delete this node and update references
                self._remove_node_references(node_id)
                self._storage.delete(node_id)
                self._nodes.pop(node_id, None)  # Maintain backward compatibility
                deleted_count = 1
            
            return deleted_count
    
    def _remove_node_references(self, node_id: str) -> None:
        """
        Remove all references to a node from its parents and children.
        
        Args:
            node_id: ID of the node
        """
        node = self._storage.get(node_id)
        if node is None:
            return
        
        # Remove references from parents
        for parent_id in node.parents:
            parent = self._storage.get(parent_id)
            if parent and node_id in parent.children:
                parent.children.remove(node_id)
                self._storage.update(parent_id, parent)
        
        # Remove references from children
        for child_id in node.children:
            child = self._storage.get(child_id)
            if child and node_id in child.parents:
                child.parents.remove(node_id)
                self._storage.update(child_id, child)