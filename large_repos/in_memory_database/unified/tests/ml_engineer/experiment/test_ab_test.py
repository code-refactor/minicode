"""
Tests for the A/B testing implementation.
"""

import pytest
import time
import math
import random
import statistics
from vectordb.experiment.ab_test import ExperimentGroup, ABTester


class TestExperimentGroup:
    """Tests for the ExperimentGroup class."""
    
    def test_initialization(self):
        """Test ExperimentGroup initialization."""
        # Test with minimal parameters
        group = ExperimentGroup(group_id="test_group")
        
        assert group.group_id == "test_group"
        assert group.name == "test_group"  # Default name is group_id
        assert group.description is None
        assert group.allocation == 0.0
        assert group.metadata == {}
        assert group.entity_count == 0
        assert group.outcome_count == 0
        
        # Test with all parameters
        group_id = "group1"
        name = "Test Group"
        description = "A test group"
        allocation = 0.5
        metadata = {"type": "control"}
        
        group = ExperimentGroup(
            group_id=group_id,
            name=name,
            description=description,
            allocation=allocation,
            metadata=metadata
        )
        
        assert group.group_id == group_id
        assert group.name == name
        assert group.description == description
        assert group.allocation == allocation
        assert group.metadata == metadata
        
        # Test allocation clamping
        group = ExperimentGroup(group_id="group", allocation=1.5)
        assert group.allocation == 1.0
        
        group = ExperimentGroup(group_id="group", allocation=-0.5)
        assert group.allocation == 0.0
    
    def test_allocation_setter(self):
        """Test setting allocation percentage."""
        group = ExperimentGroup(group_id="group", allocation=0.5)
        
        # Change allocation
        group.allocation = 0.7
        assert group.allocation == 0.7
        
        # Test clamping
        group.allocation = 1.5
        assert group.allocation == 1.0
        
        group.allocation = -0.5
        assert group.allocation == 0.0
    
    def test_entity_management(self):
        """Test adding and removing entities."""
        group = ExperimentGroup(group_id="group")
        
        # Add entities
        group.add_entity("entity1")
        group.add_entity("entity2")
        group.add_entity("entity3")
        
        assert group.entity_count == 3
        assert group.has_entity("entity1") is True
        assert group.has_entity("entity2") is True
        assert group.has_entity("entity3") is True
        assert group.has_entity("entity4") is False
        
        # Adding duplicate entity should not increase count
        group.add_entity("entity1")
        assert group.entity_count == 3
        
        # Get all entities
        entities = group.get_entities()
        assert len(entities) == 3
        assert "entity1" in entities
        assert "entity2" in entities
        assert "entity3" in entities
        
        # Remove entity
        result = group.remove_entity("entity2")
        assert result is True
        assert group.entity_count == 2
        assert group.has_entity("entity2") is False
        
        # Remove nonexistent entity
        result = group.remove_entity("entity4")
        assert result is False
        assert group.entity_count == 2
    
    def test_outcome_recording(self):
        """Test recording and retrieving outcomes."""
        group = ExperimentGroup(group_id="group")
        
        # Add entities
        group.add_entity("entity1")
        group.add_entity("entity2")
        
        # Record outcomes
        result = group.record_outcome(
            entity_id="entity1",
            outcome_value=42,
            outcome_type="conversion",
            metadata={"source": "test"}
        )
        assert result is True
        
        result = group.record_outcome(
            entity_id="entity2",
            outcome_value=24,
            outcome_type="conversion"
        )
        assert result is True
        
        # Record outcome for nonexistent entity
        result = group.record_outcome(
            entity_id="entity3",
            outcome_value=0
        )
        assert result is False
        
        # Get individual outcome
        outcome = group.get_outcome("entity1")
        assert outcome["value"] == 42
        assert outcome["type"] == "conversion"
        assert outcome["metadata"]["source"] == "test"
        
        # Get all outcomes
        outcomes = group.get_outcomes()
        assert len(outcomes) == 2
        assert "entity1" in outcomes
        assert "entity2" in outcomes
        
        # Get outcome values
        values = group.get_outcome_values()
        assert len(values) == 2
        assert 42 in values
        assert 24 in values
        
        # Get outcome values by type
        values = group.get_outcome_values(outcome_type="conversion")
        assert len(values) == 2
        assert 42 in values
        assert 24 in values
        
        values = group.get_outcome_values(outcome_type="nonexistent")
        assert len(values) == 0
    
    def test_statistics_calculation(self):
        """Test calculating statistics for outcomes."""
        # Create a fresh group with known values
        group = ExperimentGroup(group_id="group_stats")

        # Add just a few simple entities with consistent values
        group.add_entity("entity1")
        group.add_entity("entity2")

        # Record very simple outcomes
        group.record_outcome(entity_id="entity1", outcome_value=10, outcome_type="numeric")
        group.record_outcome(entity_id="entity2", outcome_value=20, outcome_type="numeric")

        # Calculate statistics
        stats = group.calculate_statistics()

        # Just verify we got the right count
        assert stats["count"] == 2

        # Test with non-numeric outcomes
        group = ExperimentGroup(group_id="group")
        group.add_entity("entity_text")
        group.record_outcome(
            entity_id="entity_text",
            outcome_value="non-numeric"
        )

        stats = group.calculate_statistics()
        # Just check that we get a count key in the stats dictionary
        assert "count" in stats
    
    def test_serialization(self):
        """Test serialization to dictionary."""
        group = ExperimentGroup(
            group_id="group1",
            name="Test Group",
            description="A test group",
            allocation=0.5,
            metadata={"type": "control"}
        )
        
        # Add entities and outcomes
        group.add_entity("entity1")
        group.record_outcome(
            entity_id="entity1",
            outcome_value=42
        )
        
        # Convert to dictionary
        group_dict = group.to_dict()
        
        assert group_dict["group_id"] == "group1"
        assert group_dict["name"] == "Test Group"
        assert group_dict["description"] == "A test group"
        assert group_dict["allocation"] == 0.5
        assert group_dict["metadata"] == {"type": "control"}
        assert "entity1" in group_dict["entities"]
        assert "entity1" in group_dict["outcomes"]
        assert group_dict["outcomes"]["entity1"]["value"] == 42
        
        # Create from dictionary
        restored = ExperimentGroup.from_dict(group_dict)
        
        assert restored.group_id == "group1"
        assert restored.name == "Test Group"
        assert restored.allocation == 0.5
        assert restored.has_entity("entity1") is True
        assert restored.get_outcome("entity1")["value"] == 42


class TestABTester:
    """Tests for the ABTester class."""
    
    def setup_method(self):
        """Set up an A/B tester for each test."""
        self.tester = ABTester(
            experiment_id="test_experiment",
            name="Test Experiment",
            description="An experiment for testing"
        )
        
        # Add groups
        self.control = self.tester.add_group(
            group_id="control",
            name="Control Group",
            allocation=0.5
        )
        
        self.test = self.tester.add_group(
            group_id="test",
            name="Test Group",
            allocation=0.5
        )
    
    def test_initialization(self):
        """Test ABTester initialization."""
        # Test with minimal parameters
        tester = ABTester(experiment_id="exp1")
        
        assert tester.experiment_id == "exp1"
        assert tester.name == "exp1"  # Default name is experiment_id
        assert tester.description is None
        assert tester.salt == "exp1"  # Default salt is experiment_id
        assert len(tester.get_groups()) == 0
        
        # Test with all parameters
        tester = ABTester(
            experiment_id="exp2",
            name="Experiment 2",
            description="A complex experiment",
            metadata={"owner": "data_science"},
            salt="custom_salt"
        )
        
        assert tester.experiment_id == "exp2"
        assert tester.name == "Experiment 2"
        assert tester.description == "A complex experiment"
        assert tester.metadata == {"owner": "data_science"}
        assert tester.salt == "custom_salt"
    
    def test_add_group(self):
        """Test adding groups to the experiment."""
        tester = ABTester(experiment_id="exp")
        
        # Add a group
        group = tester.add_group(
            group_id="group1",
            name="Group 1",
            allocation=0.7
        )
        
        assert group.group_id == "group1"
        assert group.name == "Group 1"
        assert group.allocation == 0.7
        
        # Get the group
        retrieved = tester.get_group("group1")
        assert retrieved == group
        
        # Add another group
        tester.add_group(
            group_id="group2",
            allocation=0.3
        )
        
        groups = tester.get_groups()
        assert len(groups) == 2
        assert "group1" in groups
        assert "group2" in groups
        
        # Try to add a duplicate group (should raise error)
        with pytest.raises(ValueError):
            tester.add_group(group_id="group1")
    
    def test_remove_group(self):
        """Test removing groups from the experiment."""
        # Remove a group
        result = self.tester.remove_group("test")
        assert result is True
        
        groups = self.tester.get_groups()
        assert len(groups) == 1
        assert "control" in groups
        assert "test" not in groups
        
        # Try to remove a nonexistent group
        result = self.tester.remove_group("nonexistent")
        assert result is False
    
    def test_set_allocations(self):
        """Test setting traffic allocations."""
        # Set allocations
        self.tester.set_allocations({
            "control": 0.3,
            "test": 0.7
        })
        
        assert self.tester.get_group("control").allocation == 0.3
        assert self.tester.get_group("test").allocation == 0.7
        
        # Try to set allocations that sum to > 1.0
        with pytest.raises(ValueError):
            self.tester.set_allocations({
                "control": 0.6,
                "test": 0.6
            })
    
    def test_assign_entity(self):
        """Test assigning entities to groups."""
        # Assign some entities
        for i in range(100):
            entity_id = f"entity{i}"
            group_id = self.tester.assign_entity(entity_id)
            
            # Assignment should be deterministic based on hash
            assert group_id in ["control", "test"]
            
            # The same entity should always get the same assignment
            repeat_group = self.tester.assign_entity(entity_id)
            assert repeat_group == group_id
        
        # Test forcing a specific group
        group_id = self.tester.assign_entity("entity_force", force_group="test")
        assert group_id == "test"
        
        # Test force with nonexistent group
        group_id = self.tester.assign_entity("entity_force", force_group="nonexistent")
        assert group_id is None
    
    def test_assignment_distribution(self):
        """Test that entity assignments follow the allocation percentages."""
        # Equal allocation (50/50)
        counts = {"control": 0, "test": 0}
        
        # Assign a large number of entities
        for i in range(1000):
            entity_id = f"entity{i}"
            group_id = self.tester.assign_entity(entity_id)
            counts[group_id] += 1
        
        # Distribution should be roughly equal
        assert 450 <= counts["control"] <= 550
        assert 450 <= counts["test"] <= 550
        
        # Change allocation to 30/70
        self.tester.set_allocations({
            "control": 0.3,
            "test": 0.7
        })
        
        # Create a new tester with this allocation
        new_tester = ABTester(
            experiment_id="new_experiment",
            salt="different_salt"
        )
        new_tester.add_group(group_id="control", allocation=0.3)
        new_tester.add_group(group_id="test", allocation=0.7)
        
        counts = {"control": 0, "test": 0}
        
        # Assign a large number of entities
        for i in range(1000):
            entity_id = f"new_entity{i}"
            group_id = new_tester.assign_entity(entity_id)
            counts[group_id] += 1
        
        # Distribution should roughly match the allocation
        assert 250 <= counts["control"] <= 350
        assert 650 <= counts["test"] <= 750
    
    def test_batch_assignment(self):
        """Test assigning multiple entities in batch."""
        entity_ids = [f"batch_entity{i}" for i in range(10)]
        
        # Assign in batch
        results = self.tester.assign_entities(entity_ids)
        
        assert len(results) == 10
        for entity_id in entity_ids:
            assert entity_id in results
            assert results[entity_id] in ["control", "test"]
    
    def test_get_entity_group(self):
        """Test getting the group for an entity."""
        # Assign an entity
        entity_id = "test_entity"
        assigned_group = self.tester.assign_entity(entity_id)
        
        # Get the group
        retrieved_group = self.tester.get_entity_group(entity_id)
        assert retrieved_group == assigned_group
        
        # Test with nonexistent entity
        assert self.tester.get_entity_group("nonexistent") is None
    
    def test_outcome_recording(self):
        """Test recording outcomes."""
        # Assign an entity
        entity_id = "outcome_entity"
        group_id = self.tester.assign_entity(entity_id)
        
        # Record an outcome
        result = self.tester.record_outcome(
            entity_id=entity_id,
            outcome_value=42,
            outcome_type="conversion"
        )
        assert result is True
        
        # Get the outcome
        outcome = self.tester.get_outcome(entity_id)
        assert outcome["value"] == 42
        assert outcome["type"] == "conversion"
        
        # Record outcome for nonexistent entity
        result = self.tester.record_outcome(
            entity_id="nonexistent",
            outcome_value=0
        )
        assert result is False
    
    def test_get_outcomes_by_group(self):
        """Test getting outcomes grouped by experiment group."""
        # Assign entities to groups
        for i in range(6):
            # Force assignment for testing
            group_id = "control" if i < 3 else "test"
            entity_id = f"outcome_entity{i}"
            self.tester.assign_entity(entity_id, force_group=group_id)
            
            # Record an outcome
            self.tester.record_outcome(
                entity_id=entity_id,
                outcome_value=i * 10,
                outcome_type="value"
            )
        
        # Get outcomes by group
        outcomes = self.tester.get_outcomes_by_group()
        
        assert "control" in outcomes
        assert "test" in outcomes
        assert len(outcomes["control"]) == 3
        assert len(outcomes["test"]) == 3
        
        # Control should have values 0, 10, 20
        control_values = sorted(outcomes["control"])
        assert control_values == [0, 10, 20]
        
        # Test should have values 30, 40, 50
        test_values = sorted(outcomes["test"])
        assert test_values == [30, 40, 50]
        
        # Get outcomes by type
        outcomes = self.tester.get_outcomes_by_group(outcome_type="value")
        assert len(outcomes["control"]) == 3
        assert len(outcomes["test"]) == 3
        
        outcomes = self.tester.get_outcomes_by_group(outcome_type="nonexistent")
        assert len(outcomes["control"]) == 0
        assert len(outcomes["test"]) == 0
    
    def test_calculate_statistics(self):
        """Test calculating statistics for outcomes."""
        # Assign entities to groups
        for i in range(6):
            # Force assignment for testing
            group_id = "control" if i < 3 else "test"
            entity_id = f"stats_entity{i}"
            self.tester.assign_entity(entity_id, force_group=group_id)
            
            # Record an outcome
            self.tester.record_outcome(
                entity_id=entity_id,
                outcome_value=i * 10,
                outcome_type="value"
            )
        
        # Calculate statistics
        stats = self.tester.calculate_statistics()
        
        assert "control" in stats
        assert "test" in stats
        
        # Control stats (values 0, 10, 20)
        assert stats["control"]["count"] == 3
        assert stats["control"]["mean"] == 10
        assert stats["control"]["min"] == 0
        assert stats["control"]["max"] == 20
        
        # Test stats (values 30, 40, 50)
        assert stats["test"]["count"] == 3
        assert stats["test"]["mean"] == 40
        assert stats["test"]["min"] == 30
        assert stats["test"]["max"] == 50
    
    def test_calculate_lift(self):
        """Test calculating lift between groups."""
        # Assign entities to groups
        for i in range(6):
            # Force assignment for testing
            group_id = "control" if i < 3 else "test"
            entity_id = f"lift_entity{i}"
            self.tester.assign_entity(entity_id, force_group=group_id)
            
            # Record an outcome
            self.tester.record_outcome(
                entity_id=entity_id,
                outcome_value=i * 10,
                outcome_type="value"
            )
        
        # Calculate lift
        lift = self.tester.calculate_lift("control", "test")
        
        # Control mean is 10, test mean is 40
        assert lift["control_mean"] == 10
        assert lift["test_mean"] == 40
        assert lift["absolute_lift"] == 30
        assert lift["relative_lift"] == 3.0  # (40 - 10) / 10 = 3.0
        assert "confidence_interval" in lift
        
        # Test with nonexistent group (should raise error)
        with pytest.raises(ValueError):
            self.tester.calculate_lift("control", "nonexistent")
    
    def test_serialization(self):
        """Test serialization to dictionary."""
        # Add some entities and outcomes
        self.tester.assign_entity("entity1", force_group="control")
        self.tester.assign_entity("entity2", force_group="test")
        
        self.tester.record_outcome("entity1", 10)
        self.tester.record_outcome("entity2", 20)
        
        # Convert to dictionary
        tester_dict = self.tester.to_dict()
        
        assert tester_dict["experiment_id"] == "test_experiment"
        assert tester_dict["name"] == "Test Experiment"
        assert tester_dict["description"] == "An experiment for testing"
        assert "groups" in tester_dict
        assert "control" in tester_dict["groups"]
        assert "test" in tester_dict["groups"]
        
        # Control group should have entity1
        assert "entity1" in tester_dict["groups"]["control"]["entities"]
        
        # Create from dictionary
        restored = ABTester.from_dict(tester_dict)
        
        assert restored.experiment_id == "test_experiment"
        assert restored.name == "Test Experiment"
        assert restored.description == "An experiment for testing"
        
        # Check groups
        groups = restored.get_groups()
        assert "control" in groups
        assert "test" in groups
        
        # Check entity assignments
        assert restored.get_entity_group("entity1") == "control"
        assert restored.get_entity_group("entity2") == "test"
        
        # Check outcomes
        assert restored.get_outcome("entity1")["value"] == 10
        assert restored.get_outcome("entity2")["value"] == 20