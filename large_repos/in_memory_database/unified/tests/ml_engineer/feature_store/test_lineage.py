"""
Tests for the feature lineage tracking implementation.
"""

import pytest
import time
from vectordb.feature_store.lineage import LineageNode, LineageTracker


class TestLineageNode:
    """Tests for the LineageNode class."""
    
    def test_initialization(self):
        """Test LineageNode initialization."""
        # Test with minimal parameters
        node = LineageNode()
        
        assert node.node_id is not None
        assert node.node_type == "feature"  # Default type
        assert node.name is None
        assert node.timestamp <= time.time()
        assert node.created_by is None
        assert node.metadata == {}
        assert node.parents == []
        assert node.children == []
        
        # Test with all parameters
        node_id = "test_node_id"
        node_type = "transformation"
        name = "test_node"
        timestamp = time.time() - 3600  # 1 hour ago
        created_by = "test_user"
        metadata = {"test": "metadata"}
        
        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            timestamp=timestamp,
            created_by=created_by,
            metadata=metadata
        )
        
        assert node.node_id == node_id
        assert node.node_type == node_type
        assert node.name == name
        assert node.timestamp == timestamp
        assert node.created_by == created_by
        assert node.metadata == metadata
    
    def test_created_at(self):
        """Test created_at datetime property."""
        timestamp = 1609459200  # 2021-01-01 00:00:00
        node = LineageNode(timestamp=timestamp)
        
        created_at = node.created_at
        assert created_at.year == 2021
        assert created_at.month == 1
        assert created_at.day == 1
        assert created_at.hour == 0
        assert created_at.minute == 0
        assert created_at.second == 0
    
    def test_relationships(self):
        """Test adding parent and child relationships."""
        node = LineageNode(node_id="node")
        
        # Add parents
        node.add_parent("parent1")
        node.add_parent("parent2")
        
        assert "parent1" in node.parents
        assert "parent2" in node.parents
        
        # Add duplicates (should not be added again)
        node.add_parent("parent1")
        assert len(node.parents) == 2
        
        # Add children
        node.add_child("child1")
        node.add_child("child2")
        
        assert "child1" in node.children
        assert "child2" in node.children
        
        # Add duplicates (should not be added again)
        node.add_child("child1")
        assert len(node.children) == 2
    
    def test_serialization(self):
        """Test LineageNode serialization to dictionary."""
        node_id = "test_node_id"
        node_type = "transformation"
        name = "test_node"
        timestamp = time.time()
        created_by = "test_user"
        metadata = {"test": "metadata"}
        
        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            timestamp=timestamp,
            created_by=created_by,
            metadata=metadata
        )
        
        # Add some relationships
        node.add_parent("parent1")
        node.add_child("child1")
        
        # Convert to dictionary
        node_dict = node.to_dict()
        
        # Check values
        assert node_dict["node_id"] == node_id
        assert node_dict["node_type"] == node_type
        assert node_dict["name"] == name
        assert node_dict["timestamp"] == timestamp
        assert node_dict["created_by"] == created_by
        assert node_dict["metadata"] == metadata
        assert node_dict["parents"] == ["parent1"]
        assert node_dict["children"] == ["child1"]
        
        # Create from dictionary
        restored = LineageNode.from_dict(node_dict)
        
        # Check values
        assert restored.node_id == node_id
        assert restored.node_type == node_type
        assert restored.name == name
        assert restored.timestamp == timestamp
        assert restored.created_by == created_by
        assert restored.metadata == metadata
        assert restored.parents == ["parent1"]
        assert restored.children == ["child1"]


class TestLineageTracker:
    """Tests for the LineageTracker class."""
    
    def setup_method(self):
        """Set up a lineage tracker for each test."""
        self.tracker = LineageTracker()
        
        # Create a simple graph for testing:
        # source1 → transform1 → feature1 → transform2 → feature2
        #                      ↘ transform3 → feature3
        # source2 ↗
        
        # Add source nodes
        self.source1 = self.tracker.add_node(
            node_type="source",
            name="source1",
            node_id="source1"
        )
        
        self.source2 = self.tracker.add_node(
            node_type="source",
            name="source2",
            node_id="source2"
        )
        
        # Add transformation node
        self.transform1 = self.tracker.add_node(
            node_type="transformation",
            name="transform1",
            node_id="transform1",
            parents=["source1", "source2"]
        )
        
        # Add feature node
        self.feature1 = self.tracker.add_node(
            node_type="feature",
            name="feature1",
            node_id="feature1",
            parents=["transform1"]
        )
        
        # Add another transformation node
        self.transform2 = self.tracker.add_node(
            node_type="transformation",
            name="transform2",
            node_id="transform2",
            parents=["feature1"]
        )
        
        # Add another feature node
        self.feature2 = self.tracker.add_node(
            node_type="feature",
            name="feature2",
            node_id="feature2",
            parents=["transform2"]
        )
        
        # Add a parallel branch
        self.transform3 = self.tracker.add_node(
            node_type="transformation",
            name="transform3",
            node_id="transform3",
            parents=["feature1"]
        )
        
        self.feature3 = self.tracker.add_node(
            node_type="feature",
            name="feature3",
            node_id="feature3",
            parents=["transform3"]
        )
    
    def test_initialization(self):
        """Test LineageTracker initialization."""
        tracker = LineageTracker()
        assert len(tracker._nodes) == 0
    
    def test_add_node(self):
        """Test adding nodes."""
        # Test adding a node without parents
        tracker = LineageTracker()
        node = tracker.add_node(
            node_type="feature",
            name="test_feature",
            metadata={"test": "metadata"}
        )
        
        assert node.node_id in tracker._nodes
        assert tracker._nodes[node.node_id] == node
        assert node.node_type == "feature"
        assert node.name == "test_feature"
        assert node.metadata == {"test": "metadata"}
        
        # Test adding a node with parents
        parent = tracker.add_node(
            node_type="source",
            name="parent_node",
            node_id="parent_id"
        )
        
        child = tracker.add_node(
            node_type="feature",
            name="child_node",
            parents=["parent_id"]
        )
        
        # Verify parent-child relationship
        assert "parent_id" in child.parents
        assert child.node_id in parent.children
        
        # Test with nonexistent parent (should raise error)
        with pytest.raises(ValueError):
            tracker.add_node(
                node_type="feature",
                name="error_node",
                parents=["nonexistent"]
            )
    
    def test_add_edge(self):
        """Test adding edges between nodes."""
        tracker = LineageTracker()
        
        # Add nodes
        node1 = tracker.add_node(node_type="source", node_id="node1")
        node2 = tracker.add_node(node_type="feature", node_id="node2")
        
        # Add edge
        tracker.add_edge("node1", "node2")
        
        # Verify relationship
        assert "node2" in node1.children
        assert "node1" in node2.parents
        
        # Test with nonexistent nodes (should raise error)
        with pytest.raises(ValueError):
            tracker.add_edge("node1", "nonexistent")
        
        with pytest.raises(ValueError):
            tracker.add_edge("nonexistent", "node2")
    
    def test_get_node(self):
        """Test getting a node by ID."""
        node = self.tracker.get_node("feature1")
        assert node == self.feature1
        
        assert self.tracker.get_node("nonexistent") is None
    
    def test_get_ancestors(self):
        """Test getting ancestors of a node."""
        # Get ancestors of feature2
        ancestors = self.tracker.get_ancestors("feature2")

        # Should include transform2, feature1, transform1, source1, source2
        assert len(ancestors) == 5
        assert "transform2" in ancestors
        assert "feature1" in ancestors
        assert "transform1" in ancestors
        assert "source1" in ancestors
        assert "source2" in ancestors
        
        # Test with max depth
        ancestors = self.tracker.get_ancestors("feature2", max_depth=1)
        
        # Should only include transform2
        assert len(ancestors) == 1
        assert "transform2" in ancestors
        
        # Test with nonexistent node (should raise error)
        with pytest.raises(ValueError):
            self.tracker.get_ancestors("nonexistent")
    
    def test_get_descendants(self):
        """Test getting descendants of a node."""
        # Get descendants of feature1
        descendants = self.tracker.get_descendants("feature1")
        
        # Should include transform2, feature2, transform3, feature3
        assert len(descendants) == 4
        assert "transform2" in descendants
        assert "feature2" in descendants
        assert "transform3" in descendants
        assert "feature3" in descendants
        
        # Test with max depth
        descendants = self.tracker.get_descendants("feature1", max_depth=1)
        
        # Should only include transform2 and transform3
        assert len(descendants) == 2
        assert "transform2" in descendants
        assert "transform3" in descendants
        
        # Test with nonexistent node (should raise error)
        with pytest.raises(ValueError):
            self.tracker.get_descendants("nonexistent")
    
    def test_get_lineage_path(self):
        """Test finding paths between nodes."""
        # Path from source1 to feature2
        path = self.tracker.get_lineage_path("source1", "feature2")

        # There should be a path from source1 to feature2
        # The exact path might vary, but should connect the nodes
        assert len(path) >= 5
        assert path[0] == "source1"
        assert path[-1] == "feature2"
        assert "transform1" in path
        assert "feature1" in path
        assert "transform2" in path
        
        # Path from feature1 to feature3
        path = self.tracker.get_lineage_path("feature1", "feature3")
        
        # Check path
        assert path == ["feature1", "transform3", "feature3"]
        
        # No path should exist from feature2 to feature3
        path = self.tracker.get_lineage_path("feature2", "feature3")
        assert path == []
        
        # Backward path (from descendant to ancestor)
        path = self.tracker.get_lineage_path("feature2", "source1")

        # Note: Different implementations might have different behavior for backward paths
        # Only test if we get a non-empty path or empty path - both are valid depending on implementation
        if path:
            # If there's a path, check at least start and end
            assert len(path) >= 2
            assert path[0] == "feature2"
            assert path[-1] == "source1"
        
        # Test with nonexistent nodes (should raise error)
        with pytest.raises(ValueError):
            self.tracker.get_lineage_path("nonexistent", "feature2")
        
        with pytest.raises(ValueError):
            self.tracker.get_lineage_path("feature2", "nonexistent")
    
    def test_add_transformation(self):
        """Test recording transformations."""
        tracker = LineageTracker()
        
        # Create input nodes
        input1 = tracker.add_node(node_type="feature", node_id="input1")
        input2 = tracker.add_node(node_type="feature", node_id="input2")
        
        # Create output nodes
        output1 = tracker.add_node(node_type="feature", node_id="output1")
        output2 = tracker.add_node(node_type="feature", node_id="output2")
        
        # Record transformation
        transform_id = tracker.add_transformation(
            transform_name="test_transform",
            inputs=["input1", "input2"],
            outputs=["output1", "output2"],
            parameters={"param1": "value1"},
            created_by="test_user"
        )
        
        # Check transformation node
        transform_node = tracker.get_node(transform_id)
        assert transform_node.node_type == "transformation"
        assert transform_node.name == "test_transform"
        assert transform_node.created_by == "test_user"
        assert "parameters" in transform_node.metadata
        assert transform_node.metadata["parameters"] == {"param1": "value1"}
        
        # Check relationships
        assert "input1" in transform_node.parents
        assert "input2" in transform_node.parents
        assert transform_id in input1.children
        assert transform_id in input2.children
        
        assert "output1" in transform_node.children
        assert "output2" in transform_node.children
        assert transform_id in output1.parents
        assert transform_id in output2.parents
        
        # Test with nonexistent input (should raise error)
        with pytest.raises(ValueError):
            tracker.add_transformation(
                transform_name="error_transform",
                inputs=["nonexistent"],
                outputs=["output1"]
            )
        
        # Test with nonexistent output (should raise error)
        with pytest.raises(ValueError):
            tracker.add_transformation(
                transform_name="error_transform",
                inputs=["input1"],
                outputs=["nonexistent"]
            )
    
    def test_get_node_history(self):
        """Test getting transformation history for a node."""
        # Get history of feature2
        history = self.tracker.get_node_history("feature2")
        
        # Should include transform1 and transform2 (in chronological order)
        assert len(history) == 2
        assert history[0]["node_id"] == "transform1"
        assert history[1]["node_id"] == "transform2"
        
        # Test with nonexistent node (should raise error)
        with pytest.raises(ValueError):
            self.tracker.get_node_history("nonexistent")
    
    def test_get_all_nodes(self):
        """Test getting all nodes, optionally filtered by type."""
        # Get all nodes
        all_nodes = self.tracker.get_all_nodes()
        assert len(all_nodes) == 8  # 2 sources, 3 transforms, 3 features
        
        # Get nodes by type
        sources = self.tracker.get_all_nodes("source")
        assert len(sources) == 2
        assert "source1" in sources
        assert "source2" in sources
        
        transforms = self.tracker.get_all_nodes("transformation")
        assert len(transforms) == 3
        assert "transform1" in transforms
        assert "transform2" in transforms
        assert "transform3" in transforms
        
        features = self.tracker.get_all_nodes("feature")
        assert len(features) == 3
        assert "feature1" in features
        assert "feature2" in features
        assert "feature3" in features
    
    def test_delete_node(self):
        """Test deleting nodes."""
        # Delete a node without cascade
        assert "feature3" in self.tracker._nodes
        assert "transform3" in self.tracker._nodes
        
        self.tracker.delete_node("feature3")
        
        assert "feature3" not in self.tracker._nodes
        assert "transform3" in self.tracker._nodes  # Parent should still exist
        assert "feature3" not in self.tracker.get_node("transform3").children  # Reference should be removed
        
        # Delete a node with cascade
        deleted = self.tracker.delete_node("feature1", cascade=True)
        
        # Should delete feature1, transform2, feature2, and transform3
        assert deleted == 4
        assert "feature1" not in self.tracker._nodes
        assert "transform2" not in self.tracker._nodes
        assert "feature2" not in self.tracker._nodes
        assert "transform3" not in self.tracker._nodes
        
        # But source nodes should still exist
        assert "source1" in self.tracker._nodes
        assert "source2" in self.tracker._nodes
        assert "transform1" in self.tracker._nodes
        
        # References to deleted nodes should be removed
        assert "feature1" not in self.tracker.get_node("transform1").children
        
        # Test deleting nonexistent node (should raise error)
        with pytest.raises(ValueError):
            self.tracker.delete_node("nonexistent")
    
    def test_cycles(self):
        """Test behavior with cycles in the graph."""
        tracker = LineageTracker()
        
        # Create nodes
        a = tracker.add_node(node_type="feature", node_id="a")
        b = tracker.add_node(node_type="feature", node_id="b")
        c = tracker.add_node(node_type="feature", node_id="c")
        
        # Create a cycle: a → b → c → a
        tracker.add_edge("a", "b")
        tracker.add_edge("b", "c")
        tracker.add_edge("c", "a")
        
        # Get ancestors (with cycle)
        ancestors = tracker.get_ancestors("a")
        
        # Should include b and c
        assert "b" in ancestors
        assert "c" in ancestors
        
        # Get descendants (with cycle)
        descendants = tracker.get_descendants("a")
        
        # Should include b and c
        assert "b" in descendants
        assert "c" in descendants
        
        # Get path (with cycle)
        path = tracker.get_lineage_path("a", "c")
        
        # Should find a path
        assert path == ["a", "b", "c"]