"""
Tests for the Stakeholder Insight Manager.
"""
import os
import pytest
from uuid import uuid4

from productmind.stakeholder_insights.manager import StakeholderInsightManager
from productmind.models import Stakeholder, Perspective, StakeholderRelationship, StakeholderType, Priority


class TestStakeholderInsightManager:
    """Test suite for StakeholderInsightManager."""

    def test_initialization(self, temp_data_dir):
        """Test manager initialization creates required directories."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        
        assert os.path.exists(os.path.join(temp_data_dir, "stakeholders"))
        assert os.path.exists(os.path.join(temp_data_dir, "perspectives"))
        assert os.path.exists(os.path.join(temp_data_dir, "stakeholder_relationships"))
        
        assert manager.storage_dir == temp_data_dir
        assert isinstance(manager._stakeholders_cache, dict)
        assert isinstance(manager._perspectives_cache, dict)
        assert isinstance(manager._relationships_cache, dict)

    def test_add_stakeholder(self, temp_data_dir, stakeholder_samples):
        """Test adding stakeholders to the manager."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        
        # Test adding a single stakeholder
        single_stakeholder = stakeholder_samples[0]
        stakeholder_ids = manager.add_stakeholder(single_stakeholder)
        
        assert len(stakeholder_ids) == 1
        assert stakeholder_ids[0] == str(single_stakeholder.id)
        assert str(single_stakeholder.id) in manager._stakeholders_cache
        assert os.path.exists(os.path.join(temp_data_dir, "stakeholders", f"{single_stakeholder.id}.json"))
        
        # Test adding multiple stakeholders
        multiple_stakeholders = stakeholder_samples[1:3]
        stakeholder_ids = manager.add_stakeholder(multiple_stakeholders)
        
        assert len(stakeholder_ids) == 2
        assert stakeholder_ids[0] == str(multiple_stakeholders[0].id)
        assert stakeholder_ids[1] == str(multiple_stakeholders[1].id)
        assert str(multiple_stakeholders[0].id) in manager._stakeholders_cache
        assert str(multiple_stakeholders[1].id) in manager._stakeholders_cache
        assert os.path.exists(os.path.join(temp_data_dir, "stakeholders", f"{multiple_stakeholders[0].id}.json"))
        assert os.path.exists(os.path.join(temp_data_dir, "stakeholders", f"{multiple_stakeholders[1].id}.json"))

    def test_add_perspective(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test adding perspectives to the manager."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        
        # Add stakeholders first
        manager.add_stakeholder(stakeholder_samples)
        
        # Test adding a single perspective
        single_perspective = perspective_samples[0]
        perspective_ids = manager.add_perspective(single_perspective)
        
        assert len(perspective_ids) == 1
        assert perspective_ids[0] == str(single_perspective.id)
        assert str(single_perspective.id) in manager._perspectives_cache
        assert os.path.exists(os.path.join(temp_data_dir, "perspectives", f"{single_perspective.id}.json"))
        
        # Verify stakeholder was updated with perspective ID
        stakeholder = manager.get_stakeholder(str(single_perspective.stakeholder_id))
        # Check if the UUID object is in the perspectives list
        assert single_perspective.id in stakeholder.perspectives
        
        # Test adding multiple perspectives
        multiple_perspectives = perspective_samples[1:3]
        perspective_ids = manager.add_perspective(multiple_perspectives)
        
        assert len(perspective_ids) == 2
        assert perspective_ids[0] == str(multiple_perspectives[0].id)
        assert perspective_ids[1] == str(multiple_perspectives[1].id)
        assert str(multiple_perspectives[0].id) in manager._perspectives_cache
        assert str(multiple_perspectives[1].id) in manager._perspectives_cache
        assert os.path.exists(os.path.join(temp_data_dir, "perspectives", f"{multiple_perspectives[0].id}.json"))
        assert os.path.exists(os.path.join(temp_data_dir, "perspectives", f"{multiple_perspectives[1].id}.json"))

    def test_add_relationship(self, temp_data_dir, stakeholder_samples, stakeholder_relationship_samples):
        """Test adding stakeholder relationships to the manager."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        
        # Add stakeholders first
        manager.add_stakeholder(stakeholder_samples)
        
        # Test adding a single relationship
        single_relationship = stakeholder_relationship_samples[0]
        relationship_ids = manager.add_relationship(single_relationship)
        
        assert len(relationship_ids) == 1
        assert relationship_ids[0] == str(single_relationship.id)
        assert str(single_relationship.id) in manager._relationships_cache
        assert os.path.exists(os.path.join(temp_data_dir, "stakeholder_relationships", f"{single_relationship.id}.json"))
        
        # Test adding multiple relationships
        multiple_relationships = stakeholder_relationship_samples[1:3]
        relationship_ids = manager.add_relationship(multiple_relationships)
        
        assert len(relationship_ids) == 2
        assert relationship_ids[0] == str(multiple_relationships[0].id)
        assert relationship_ids[1] == str(multiple_relationships[1].id)
        assert str(multiple_relationships[0].id) in manager._relationships_cache
        assert str(multiple_relationships[1].id) in manager._relationships_cache
        assert os.path.exists(os.path.join(temp_data_dir, "stakeholder_relationships", f"{multiple_relationships[0].id}.json"))
        assert os.path.exists(os.path.join(temp_data_dir, "stakeholder_relationships", f"{multiple_relationships[1].id}.json"))

    def test_get_stakeholder(self, temp_data_dir, stakeholder_samples):
        """Test retrieving stakeholders."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        
        # Test retrieving existing stakeholder
        for stakeholder in stakeholder_samples:
            retrieved = manager.get_stakeholder(str(stakeholder.id))
            assert retrieved is not None
            assert retrieved.id == stakeholder.id
            assert retrieved.name == stakeholder.name
            assert retrieved.title == stakeholder.title
        
        # Test retrieving non-existent stakeholder
        non_existent = manager.get_stakeholder("non-existent-id")
        assert non_existent is None

    def test_get_perspective(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test retrieving perspectives."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_perspective(perspective_samples)
        
        # Test retrieving existing perspective
        for perspective in perspective_samples:
            retrieved = manager.get_perspective(str(perspective.id))
            assert retrieved is not None
            assert retrieved.id == perspective.id
            assert retrieved.topic == perspective.topic
            assert retrieved.content == perspective.content
        
        # Test retrieving non-existent perspective
        non_existent = manager.get_perspective("non-existent-id")
        assert non_existent is None

    def test_get_relationship(self, temp_data_dir, stakeholder_samples, stakeholder_relationship_samples):
        """Test retrieving stakeholder relationships."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_relationship(stakeholder_relationship_samples)
        
        # Test retrieving existing relationship
        for relationship in stakeholder_relationship_samples:
            retrieved = manager.get_relationship(str(relationship.id))
            assert retrieved is not None
            assert retrieved.id == relationship.id
            assert retrieved.stakeholder1_id == relationship.stakeholder1_id
            assert retrieved.stakeholder2_id == relationship.stakeholder2_id
        
        # Test retrieving non-existent relationship
        non_existent = manager.get_relationship("non-existent-id")
        assert non_existent is None

    def test_get_all_stakeholders(self, temp_data_dir, stakeholder_samples):
        """Test retrieving all stakeholders."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        
        all_stakeholders = manager.get_all_stakeholders()
        assert len(all_stakeholders) == len(stakeholder_samples)
        
        stakeholder_ids = [str(s.id) for s in all_stakeholders]
        expected_ids = [str(s.id) for s in stakeholder_samples]
        
        # Check that all expected ids are present
        for expected_id in expected_ids:
            assert expected_id in stakeholder_ids

    def test_get_all_perspectives(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test retrieving all perspectives."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_perspective(perspective_samples)
        
        all_perspectives = manager.get_all_perspectives()
        assert len(all_perspectives) == len(perspective_samples)
        
        perspective_ids = [str(p.id) for p in all_perspectives]
        expected_ids = [str(p.id) for p in perspective_samples]
        
        # Check that all expected ids are present
        for expected_id in expected_ids:
            assert expected_id in perspective_ids

    def test_get_all_relationships(self, temp_data_dir, stakeholder_samples, stakeholder_relationship_samples):
        """Test retrieving all stakeholder relationships."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_relationship(stakeholder_relationship_samples)
        
        all_relationships = manager.get_all_relationships()
        assert len(all_relationships) == len(stakeholder_relationship_samples)
        
        relationship_ids = [str(r.id) for r in all_relationships]
        expected_ids = [str(r.id) for r in stakeholder_relationship_samples]
        
        # Check that all expected ids are present
        for expected_id in expected_ids:
            assert expected_id in relationship_ids

    def test_get_stakeholder_perspectives(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test retrieving perspectives for a stakeholder."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_perspective(perspective_samples)
        
        # Group perspectives by stakeholder
        perspectives_by_stakeholder = {}
        for perspective in perspective_samples:
            sid = str(perspective.stakeholder_id)
            if sid not in perspectives_by_stakeholder:
                perspectives_by_stakeholder[sid] = []
            perspectives_by_stakeholder[sid].append(perspective)
        
        # Test for each stakeholder with perspectives
        for sid, expected_perspectives in perspectives_by_stakeholder.items():
            stakeholder_perspectives = manager.get_stakeholder_perspectives(sid)
            
            assert len(stakeholder_perspectives) == len(expected_perspectives)
            
            perspective_ids = [str(p.id) for p in stakeholder_perspectives]
            expected_ids = [str(p.id) for p in expected_perspectives]
            
            # Check that all expected ids are present
            for expected_id in expected_ids:
                assert expected_id in perspective_ids
        
        # Test with stakeholder who has no perspectives
        stakeholder_with_no_perspectives = None
        for stakeholder in stakeholder_samples:
            if not stakeholder.perspectives:
                stakeholder_with_no_perspectives = stakeholder
                break
        
        if stakeholder_with_no_perspectives:
            no_perspectives = manager.get_stakeholder_perspectives(str(stakeholder_with_no_perspectives.id))
            assert len(no_perspectives) == 0

    def test_get_perspectives_by_topic(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test retrieving perspectives by topic."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_perspective(perspective_samples)
        
        # Group perspectives by topic
        perspectives_by_topic = {}
        for perspective in perspective_samples:
            topic = perspective.topic
            if topic not in perspectives_by_topic:
                perspectives_by_topic[topic] = []
            perspectives_by_topic[topic].append(perspective)
        
        # Test for each topic
        for topic, expected_perspectives in perspectives_by_topic.items():
            topic_perspectives = manager.get_perspectives_by_topic(topic)
            
            assert len(topic_perspectives) == len(expected_perspectives)
            
            perspective_ids = [str(p.id) for p in topic_perspectives]
            expected_ids = [str(p.id) for p in expected_perspectives]
            
            # Check that all expected ids are present
            for expected_id in expected_ids:
                assert expected_id in perspective_ids
        
        # Test with non-existent topic
        no_perspectives = manager.get_perspectives_by_topic("non-existent-topic")
        assert len(no_perspectives) == 0

    def test_get_stakeholder_relationships(self, temp_data_dir, stakeholder_samples, stakeholder_relationship_samples):
        """Test retrieving relationships for a stakeholder."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_relationship(stakeholder_relationship_samples)
        
        # Test for first stakeholder
        if stakeholder_relationship_samples:
            stakeholder_id = str(stakeholder_relationship_samples[0].stakeholder1_id)
            
            # Count expected relationships for this stakeholder
            expected_count = 0
            for relationship in stakeholder_relationship_samples:
                if (str(relationship.stakeholder1_id) == stakeholder_id or 
                    str(relationship.stakeholder2_id) == stakeholder_id):
                    expected_count += 1
            
            stakeholder_relationships = manager.get_stakeholder_relationships(stakeholder_id)
            
            assert len(stakeholder_relationships) == expected_count
            
            # Verify relationship structure
            for relationship in stakeholder_relationships:
                assert "relationship_id" in relationship
                assert "relationship_type" in relationship
                assert "alignment_level" in relationship
                assert "notes" in relationship
                assert "stakeholder" in relationship
                
                # Verify stakeholder details
                stakeholder_details = relationship["stakeholder"]
                assert "id" in stakeholder_details
                assert "name" in stakeholder_details
                assert "title" in stakeholder_details
                assert "department" in stakeholder_details
                assert "type" in stakeholder_details
                
                # Verify other stakeholder is different from the one we're querying
                assert stakeholder_details["id"] != stakeholder_id
        
        # Test with non-existent stakeholder
        no_relationships = manager.get_stakeholder_relationships("non-existent-id")
        assert len(no_relationships) == 0

    def test_detect_conflicts(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test detecting conflicts between stakeholders."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        
        # Create perspectives with conflicting views
        stakeholder1 = stakeholder_samples[0]
        stakeholder2 = stakeholder_samples[1]
        
        conflict_topic = "Conflicting Topic"
        
        perspective1 = Perspective(
            id=uuid4(),
            topic=conflict_topic,
            content="Strong opinion in favor",
            priority=Priority.HIGH,
            influence_level=0.8,
            agreement_level=0.9,  # High agreement with their position
            stakeholder_id=stakeholder1.id
        )
        
        perspective2 = Perspective(
            id=uuid4(),
            topic=conflict_topic,
            content="Strong opinion against",
            priority=Priority.HIGH,
            influence_level=0.8,
            agreement_level=0.1,  # High agreement with opposite position
            stakeholder_id=stakeholder2.id
        )
        
        # Add original perspectives and the conflict ones
        manager.add_perspective(perspective_samples)
        manager.add_perspective([perspective1, perspective2])
        
        # Detect conflicts for all topics
        all_conflicts = manager.detect_conflicts()
        
        # There should be at least one conflict (the one we created)
        assert len(all_conflicts) > 0
        
        # Find our conflict
        our_conflict = None
        for conflict in all_conflicts:
            if conflict["topic"] == conflict_topic:
                our_conflict = conflict
                break
        
        assert our_conflict is not None
        assert our_conflict["topic"] == conflict_topic
        assert our_conflict["stakeholder1"]["id"] in [str(stakeholder1.id), str(stakeholder2.id)]
        assert our_conflict["stakeholder2"]["id"] in [str(stakeholder1.id), str(stakeholder2.id)]
        assert our_conflict["agreement_level"] < 0.5  # Low agreement level indicates conflict
        
        # Detect conflicts for specific topic
        topic_conflicts = manager.detect_conflicts(topic=conflict_topic)
        assert len(topic_conflicts) > 0
        
        # Detect conflicts for non-existent topic
        no_conflicts = manager.detect_conflicts(topic="non-existent-topic")
        assert len(no_conflicts) == 0

    def test_identify_consensus(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test identifying areas of consensus on a topic."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        
        # Add original perspectives
        manager.add_perspective(perspective_samples)
        
        # Find a topic that has multiple perspectives
        test_topic = None
        topic_count = {}
        
        for perspective in perspective_samples:
            topic = perspective.topic
            if topic not in topic_count:
                topic_count[topic] = 0
            topic_count[topic] += 1
        
        for topic, count in topic_count.items():
            if count >= 2:
                test_topic = topic
                break
        
        if test_topic:
            # Identify consensus
            consensus = manager.identify_consensus(test_topic)
            
            assert consensus["topic"] == test_topic
            assert consensus["perspectives_count"] > 1
            assert 0 <= consensus["average_agreement"] <= 1.0
            assert 0 <= consensus["consensus_level"] <= 1.0
            assert len(consensus["stakeholders"]) > 1
            
            # Verify stakeholder details
            for stakeholder in consensus["stakeholders"]:
                assert "stakeholder_id" in stakeholder
                assert "name" in stakeholder
                assert "type" in stakeholder
                assert "department" in stakeholder
                assert "agreement_level" in stakeholder
                assert "influence_level" in stakeholder
                assert "priority" in stakeholder
        
        # Test with non-existent topic
        no_consensus = manager.identify_consensus("non-existent-topic")
        assert no_consensus["perspectives_count"] == 0
        assert no_consensus["average_agreement"] == 0.0
        assert no_consensus["consensus_level"] == 0.0
        assert len(no_consensus["stakeholders"]) == 0

    def test_integrate_perspectives(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test integrating perspectives on a topic."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        
        # Add original perspectives
        manager.add_perspective(perspective_samples)
        
        # Find a topic that has multiple perspectives
        test_topic = None
        topic_count = {}
        
        for perspective in perspective_samples:
            topic = perspective.topic
            if topic not in topic_count:
                topic_count[topic] = 0
            topic_count[topic] += 1
        
        for topic, count in topic_count.items():
            if count >= 2:
                test_topic = topic
                break
        
        if test_topic:
            # Test different weighting strategies
            strategies = ["influence", "priority", "balanced"]
            
            for strategy in strategies:
                integrated = manager.integrate_perspectives(test_topic, strategy)
                
                assert integrated["topic"] == test_topic
                assert integrated["perspectives_count"] > 1
                assert 0 <= integrated["integrated_value"] <= 1.0
                assert 0 <= integrated["confidence"] <= 1.0
                assert len(integrated["stakeholder_perspectives"]) > 1
                
                # Verify stakeholder perspective structure
                for perspective in integrated["stakeholder_perspectives"]:
                    assert "stakeholder_id" in perspective
                    assert "name" in perspective
                    assert "type" in perspective
                    assert "agreement_level" in perspective
                    assert "weight" in perspective
                    assert "priority" in perspective
                    assert "perspective_id" in perspective
        
        # Test with non-existent topic
        no_integration = manager.integrate_perspectives("non-existent-topic")
        assert no_integration["perspectives_count"] == 0
        assert no_integration["integrated_value"] == 0.0
        assert no_integration["confidence"] == 0.0
        assert len(no_integration["stakeholder_perspectives"]) == 0

    def test_generate_stakeholder_map(self, temp_data_dir, stakeholder_samples, stakeholder_relationship_samples):
        """Test generating a stakeholder map."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_relationship(stakeholder_relationship_samples)
        
        # Generate map
        map_data = manager.generate_stakeholder_map()
        
        assert "nodes" in map_data
        assert "links" in map_data
        assert "departments" in map_data
        assert "types" in map_data
        
        assert len(map_data["nodes"]) == len(stakeholder_samples)
        assert len(map_data["links"]) == len(stakeholder_relationship_samples)
        
        # Verify node structure
        for node in map_data["nodes"]:
            assert "id" in node
            assert "name" in node
            assert "department" in node
            assert "type" in node
            assert "influence" in node
        
        # Verify link structure
        for link in map_data["links"]:
            assert "source" in link
            assert "target" in link
            assert "type" in link
            assert "alignment" in link
            
            # Verify source and target exist in nodes
            source_exists = any(node["id"] == link["source"] for node in map_data["nodes"])
            target_exists = any(node["id"] == link["target"] for node in map_data["nodes"])
            assert source_exists and target_exists
        
        # Verify department grouping
        departments = set(node["department"] for node in map_data["nodes"])
        assert len(map_data["departments"]) == len(departments)
        
        # Verify stakeholder type grouping
        types = set(node["type"] for node in map_data["nodes"])
        assert len(map_data["types"]) == len(types)

    def test_analyze_stakeholder_influence(self, temp_data_dir, stakeholder_samples):
        """Test analyzing stakeholder influence."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        
        # Analyze influence
        analysis = manager.analyze_stakeholder_influence()
        
        assert "total_stakeholders" in analysis
        assert "influence_by_type" in analysis
        assert "influence_by_department" in analysis
        assert "stakeholders_by_influence" in analysis
        
        assert analysis["total_stakeholders"] == len(stakeholder_samples)
        assert len(analysis["stakeholders_by_influence"]) == len(stakeholder_samples)
        
        # Verify stakeholder types
        stakeholder_types = set(s.type for s in stakeholder_samples)
        assert len(analysis["influence_by_type"]) == len(stakeholder_types)
        
        # Verify departments
        departments = set(s.department for s in stakeholder_samples)
        assert len(analysis["influence_by_department"]) == len(departments)
        
        # Verify influence sorting
        for i in range(len(analysis["stakeholders_by_influence"]) - 1):
            assert (analysis["stakeholders_by_influence"][i]["influence"] >= 
                    analysis["stakeholders_by_influence"][i + 1]["influence"])

    def test_generate_stakeholder_matrix(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test generating a power/interest stakeholder matrix."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_perspective(perspective_samples)
        
        # Generate matrix
        matrix = manager.generate_stakeholder_matrix()
        
        assert "high_power_high_interest" in matrix
        assert "high_power_low_interest" in matrix
        assert "low_power_high_interest" in matrix
        assert "low_power_low_interest" in matrix
        
        # Sum of stakeholders in all quadrants should equal total stakeholders
        total_in_quadrants = (
            len(matrix["high_power_high_interest"]) +
            len(matrix["high_power_low_interest"]) +
            len(matrix["low_power_high_interest"]) +
            len(matrix["low_power_low_interest"])
        )
        
        assert total_in_quadrants == len(stakeholder_samples)
        
        # Verify stakeholder structure in quadrants
        for quadrant in [
            "high_power_high_interest",
            "high_power_low_interest",
            "low_power_high_interest",
            "low_power_low_interest"
        ]:
            for stakeholder in matrix[quadrant]:
                assert "id" in stakeholder
                assert "name" in stakeholder
                assert "title" in stakeholder
                assert "department" in stakeholder
                assert "type" in stakeholder
                assert "power" in stakeholder
                assert "interest" in stakeholder
                
                # Verify power and interest match quadrant
                if quadrant.startswith("high_power"):
                    assert stakeholder["power"] >= 0.5
                else:
                    assert stakeholder["power"] < 0.5
                    
                if quadrant.endswith("high_interest"):
                    assert stakeholder["interest"] >= 0.5
                else:
                    assert stakeholder["interest"] < 0.5

    def test_analyze_perspective_alignment(self, temp_data_dir, stakeholder_samples, perspective_samples):
        """Test analyzing alignment of perspectives."""
        manager = StakeholderInsightManager(storage_dir=temp_data_dir)
        manager.add_stakeholder(stakeholder_samples)
        manager.add_perspective(perspective_samples)
        
        # Analyze all topics
        all_alignment = manager.analyze_perspective_alignment()
        
        assert "topics" in all_alignment
        assert "overall_alignment" in all_alignment
        assert "topics_alignment" in all_alignment
        assert "stakeholder_agreement" in all_alignment
        
        assert 0 <= all_alignment["overall_alignment"] <= 1.0
        
        # Count unique topics
        topics = set(p.topic for p in perspective_samples)
        assert len(all_alignment["topics"]) == len(topics)
        assert len(all_alignment["topics_alignment"]) == len(topics)
        
        # Verify topic alignment structure
        for topic, alignment in all_alignment["topics_alignment"].items():
            assert "perspective_count" in alignment
            assert "stakeholder_count" in alignment
            assert "average_agreement" in alignment
            assert 0 <= alignment["average_agreement"] <= 1.0
        
        # Verify stakeholder agreement structure
        for stakeholder_id, agreement in all_alignment["stakeholder_agreement"].items():
            assert "name" in agreement
            assert "department" in agreement
            assert "type" in agreement
            assert "average_agreement" in agreement
            assert "perspective_count" in agreement
            assert "topics_count" in agreement
            assert 0 <= agreement["average_agreement"] <= 1.0
        
        # Test with specific topic
        if topics:
            test_topic = next(iter(topics))
            topic_alignment = manager.analyze_perspective_alignment(topic=test_topic)
            
            assert len(topic_alignment["topics"]) == 1
            assert test_topic in topic_alignment["topics"]
            assert test_topic in topic_alignment["topics_alignment"]
        
        # Test with non-existent topic
        no_alignment = manager.analyze_perspective_alignment(topic="non-existent-topic")
        assert len(no_alignment["topics"]) == 0
        assert no_alignment["overall_alignment"] == 0.0