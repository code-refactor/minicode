"""
Tests for the Decision Registry.
"""
import os
import pytest
import datetime
from uuid import uuid4

from productmind.decision_registry.registry import DecisionRegistry
from productmind.models import Alternative, Decision


class TestDecisionRegistry:
    """Test suite for DecisionRegistry."""

    def test_initialization(self, temp_data_dir):
        """Test registry initialization creates required directories."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        
        assert os.path.exists(os.path.join(temp_data_dir, "decisions"))
        
        assert registry.storage_dir == temp_data_dir
        assert isinstance(registry._decisions_cache, dict)

    def test_add_decision(self, temp_data_dir, decision_samples):
        """Test adding decisions to the registry."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        
        # Test adding a single decision
        single_decision = decision_samples[0]
        decision_ids = registry.add_decision(single_decision)
        
        assert len(decision_ids) == 1
        assert decision_ids[0] == str(single_decision.id)
        assert str(single_decision.id) in registry._decisions_cache
        assert os.path.exists(os.path.join(temp_data_dir, "decisions", f"{single_decision.id}.json"))
        
        # Test adding multiple decisions
        if len(decision_samples) > 1:
            multiple_decisions = decision_samples[1:]
            decision_ids = registry.add_decision(multiple_decisions)
            
            assert len(decision_ids) == len(multiple_decisions)
            for i, decision in enumerate(multiple_decisions):
                assert decision_ids[i] == str(decision.id)
                assert str(decision.id) in registry._decisions_cache
                assert os.path.exists(os.path.join(temp_data_dir, "decisions", f"{decision.id}.json"))

    def test_get_decision(self, temp_data_dir, decision_samples):
        """Test retrieving decisions."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        # Test retrieving existing decision
        for decision in decision_samples:
            retrieved = registry.get_decision(str(decision.id))
            assert retrieved is not None
            assert retrieved.id == decision.id
            assert retrieved.title == decision.title
            assert retrieved.description == decision.description
        
        # Test retrieving non-existent decision
        non_existent = registry.get_decision("non-existent-id")
        assert non_existent is None

    def test_get_all_decisions(self, temp_data_dir, decision_samples):
        """Test retrieving all decisions."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        all_decisions = registry.get_all_decisions()
        assert len(all_decisions) == len(decision_samples)
        
        decision_ids = [str(d.id) for d in all_decisions]
        expected_ids = [str(d.id) for d in decision_samples]
        
        # Check that all expected ids are present
        for expected_id in expected_ids:
            assert expected_id in decision_ids

    def test_add_alternative_to_decision(self, temp_data_dir, decision_samples):
        """Test adding alternatives to a decision."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        decision_id = str(decision_samples[0].id)
        
        # Create a new alternative
        new_alternative = Alternative(
            id=uuid4(),
            name="New Alternative",
            description="A new alternative option",
            pros=["Pro 1", "Pro 2"],
            cons=["Con 1"],
            estimated_cost=75000,
            estimated_benefit=85000,
            estimated_risk=0.4,
            score=7.9
        )
        
        # Add the alternative to the decision
        updated_decision = registry.add_alternative_to_decision(decision_id, new_alternative)
        
        assert updated_decision is not None
        
        # Find the new alternative in the updated decision
        found_alternative = None
        for alt in updated_decision.alternatives:
            if alt.name == "New Alternative":
                found_alternative = alt
                break
        
        assert found_alternative is not None
        assert found_alternative.id == new_alternative.id
        assert found_alternative.description == new_alternative.description
        assert found_alternative.pros == new_alternative.pros
        assert found_alternative.cons == new_alternative.cons
        
        # Verify the decision was updated in storage
        retrieved = registry.get_decision(decision_id)
        # Check that the new alternative exists in the retrieved decision
        found_in_retrieved = False
        for alt in retrieved.alternatives:
            if alt.name == "New Alternative":
                found_in_retrieved = True
                break
        assert found_in_retrieved
        
        # Test adding an alternative with a duplicate name
        duplicate_alternative = Alternative(
            id=uuid4(),
            name="New Alternative",  # Same name as the one we just added
            description="Another description"
        )
        
        with pytest.raises(ValueError):
            registry.add_alternative_to_decision(decision_id, duplicate_alternative)
        
        # Test with non-existent decision
        with pytest.raises(ValueError):
            registry.add_alternative_to_decision("non-existent-id", new_alternative)

    def test_link_related_decisions(self, temp_data_dir, decision_samples):
        """Test linking related decisions."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        if len(decision_samples) < 2:
            # Create another decision if we don't have enough samples
            new_decision = Decision(
                id=uuid4(),
                title="New Decision",
                description="A new decision for testing",
                context="Test context",
                problem_statement="Test problem",
                decision_date=datetime.datetime.now(),
                decision_maker="Test Maker",
                chosen_alternative=str(uuid4()),
                alternatives=[],
                rationale="Test rationale",
                success_criteria=["Test criterion"]
            )
            registry.add_decision(new_decision)
            decision_samples.append(new_decision)
        
        decision1_id = str(decision_samples[0].id)
        decision2_id = str(decision_samples[1].id)
        
        # Link the decisions
        updated_decision = registry.link_related_decisions(decision1_id, [decision2_id])
        
        assert updated_decision is not None
        assert decision2_id in updated_decision.related_decisions
        
        # Verify bi-directional linking
        decision2 = registry.get_decision(decision2_id)
        assert decision1_id in decision2.related_decisions
        
        # Test with non-existent decision
        with pytest.raises(ValueError):
            registry.link_related_decisions("non-existent-id", [decision2_id])
        
        # Test with non-existent related decision
        with pytest.raises(ValueError):
            registry.link_related_decisions(decision1_id, ["non-existent-id"])

    def test_record_outcome_assessment(self, temp_data_dir, decision_samples):
        """Test recording outcome assessment for a decision."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        decision_id = str(decision_samples[0].id)
        
        # Record outcome assessment
        outcome = "Implementation was successful and met all success criteria. User satisfaction improved by 35%."
        updated_decision = registry.record_outcome_assessment(decision_id, outcome)
        
        assert updated_decision is not None
        assert updated_decision.outcome_assessment == outcome
        assert updated_decision.status == "assessed"
        
        # Verify the decision was updated in storage
        retrieved = registry.get_decision(decision_id)
        assert retrieved.outcome_assessment == outcome
        assert retrieved.status == "assessed"
        
        # Test with non-existent decision
        with pytest.raises(ValueError):
            registry.record_outcome_assessment("non-existent-id", outcome)

    def test_search_decisions(self, temp_data_dir, decision_samples):
        """Test searching for decisions."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        # Add a decision with specific searchable content
        search_decision = Decision(
            id=uuid4(),
            title="Searchable Decision",
            description="A decision with searchable content",
            context="This decision contains the searchable term XYZ123",
            problem_statement="Need to solve the XYZ123 problem",
            decision_date=datetime.datetime.now(),
            decision_maker="Test Maker",
            chosen_alternative=str(uuid4()),
            alternatives=[],
            rationale="We chose this option because of XYZ123 considerations",
            success_criteria=["Success with XYZ123"]
        )
        registry.add_decision(search_decision)
        
        # Search for specific term that should only be in the search_decision
        results = registry.search_decisions("XYZ123")
        
        assert len(results) == 1
        assert results[0].id == search_decision.id
        
        # Search in specific fields
        field_results = registry.search_decisions("XYZ123", search_fields=["context", "rationale"])
        
        assert len(field_results) == 1
        assert field_results[0].id == search_decision.id
        
        # Search for a term that shouldn't exist in any decision
        no_results = registry.search_decisions("nonexistentterm123456789")
        assert len(no_results) == 0

    def test_get_decision_history(self, temp_data_dir, decision_samples):
        """Test getting decision history."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        # Get all decision history
        history = registry.get_decision_history()
        
        assert len(history) == len(decision_samples)
        
        # Verify history structure
        for item in history:
            assert "id" in item
            assert "title" in item
            assert "decision_date" in item
            assert "decision_maker" in item
            assert "chosen_alternative" in item
            assert "status" in item
            assert "num_alternatives" in item
            assert "has_outcome_assessment" in item
            assert "related_decisions" in item
        
        # Test filtering by decision maker
        if decision_samples:
            decision_maker = decision_samples[0].decision_maker
            filtered_history = registry.get_decision_history({"decision_maker": decision_maker})
            
            assert len(filtered_history) > 0
            for item in filtered_history:
                assert item["decision_maker"] == decision_maker

    def test_build_decision_graph(self, temp_data_dir, decision_samples):
        """Test building a graph of related decisions."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        
        # Need at least 2 decisions with relationships
        if len(decision_samples) < 2:
            # Create more decisions if needed
            for i in range(2 - len(decision_samples)):
                new_decision = Decision(
                    id=uuid4(),
                    title=f"New Decision {i}",
                    description=f"A new decision {i} for testing",
                    context="Test context",
                    problem_statement="Test problem",
                    decision_date=datetime.datetime.now(),
                    decision_maker="Test Maker",
                    chosen_alternative=str(uuid4()),
                    alternatives=[],
                    rationale="Test rationale",
                    success_criteria=["Test criterion"]
                )
                decision_samples.append(new_decision)
        
        registry.add_decision(decision_samples)
        
        # Link decisions
        registry.link_related_decisions(
            str(decision_samples[0].id),
            [str(decision_samples[1].id)]
        )
        
        # Build graph
        graph = registry.build_decision_graph()
        
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) == len(decision_samples)
        assert len(graph["edges"]) > 0
        
        # Verify graph structure
        for node in graph["nodes"]:
            assert "id" in node
            assert "label" in node
            assert "date" in node
            assert "status" in node
        
        for edge in graph["edges"]:
            assert "source" in edge
            assert "target" in edge
            
            # Verify nodes exist for both source and target
            source_exists = any(node["id"] == edge["source"] for node in graph["nodes"])
            target_exists = any(node["id"] == edge["target"] for node in graph["nodes"])
            assert source_exists and target_exists

    def test_analyze_alternatives(self, temp_data_dir, decision_samples):
        """Test analyzing alternatives for a decision."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        if decision_samples and decision_samples[0].alternatives:
            decision_id = str(decision_samples[0].id)
            
            # Analyze alternatives
            analysis = registry.analyze_alternatives(decision_id)
            
            assert "decision_id" in analysis
            assert "alternatives" in analysis
            assert "chosen_alternative" in analysis
            assert "score_range" in analysis
            assert "cost_range" in analysis
            assert "benefit_range" in analysis
            assert "risk_range" in analysis
            
            assert len(analysis["alternatives"]) == len(decision_samples[0].alternatives)
            
            # Verify alternative structure
            for alt in analysis["alternatives"]:
                assert "id" in alt
                assert "name" in alt
                assert "score" in alt
                assert "cost" in alt
                assert "benefit" in alt
                assert "risk" in alt
                assert "pros_count" in alt
                assert "cons_count" in alt
                assert "is_chosen" in alt
            
            # Verify chosen alternative is identified
            chosen_alt = next((a for a in analysis["alternatives"] if a["is_chosen"]), None)
            assert chosen_alt is not None
            assert analysis["chosen_alternative"] == chosen_alt
            
            # Test with non-existent decision
            with pytest.raises(ValueError):
                registry.analyze_alternatives("non-existent-id")

    def test_generate_decision_template(self, temp_data_dir):
        """Test generating decision templates."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        
        # Generate templates for different types
        template_types = ["standard", "urgent", "technical", "strategic"]
        
        for template_type in template_types:
            template = registry.generate_decision_template(template_type)
            
            # Verify common template structure
            assert "title" in template
            assert "description" in template
            assert "context" in template
            assert "problem_statement" in template
            assert "decision_date" in template
            assert "decision_maker" in template
            assert "alternatives" in template
            assert "rationale" in template
            assert "success_criteria" in template
            assert "status" in template
            
            # Verify alternatives structure
            assert len(template["alternatives"]) > 0
            for alt in template["alternatives"]:
                assert "name" in alt
                assert "description" in alt
                assert "pros" in alt
                assert "cons" in alt
            
            # Verify template type-specific content
            if template_type == "urgent":
                assert "URGENT DECISION" in template["context"]
            elif template_type == "technical":
                assert "Technical" in template["context"]
            elif template_type == "strategic":
                assert "Strategic" in template["context"]

    def test_export_decision(self, temp_data_dir, decision_samples):
        """Test exporting a decision in different formats."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        if decision_samples:
            decision_id = str(decision_samples[0].id)
            
            # Test exporting in different formats
            formats = ["text", "markdown", "json"]
            
            for format in formats:
                exported = registry.export_decision(decision_id, format)
                
                assert exported is not None
                assert isinstance(exported, str)
                assert len(exported) > 0
                
                # Verify format-specific content
                if format == "json":
                    assert exported.startswith("{")
                    assert exported.endswith("}")
                    assert "id" in exported
                    assert "title" in exported
                
                elif format == "markdown":
                    assert exported.startswith("# ")
                    assert "**Decision Date:**" in exported
                    assert "## Alternatives Considered" in exported
                
                else:  # text
                    assert exported.startswith("DECISION: ")
                    assert "Date: " in exported
                    assert "ALTERNATIVES CONSIDERED" in exported
            
            # Test with non-existent decision
            with pytest.raises(ValueError):
                registry.export_decision("non-existent-id", "text")

    def test_calculate_decision_stats(self, temp_data_dir, decision_samples):
        """Test calculating statistics about decisions."""
        registry = DecisionRegistry(storage_dir=temp_data_dir)
        registry.add_decision(decision_samples)
        
        # Calculate stats
        stats = registry.calculate_decision_stats()
        
        assert "total_decisions" in stats
        assert "status_counts" in stats
        assert "alternatives_stats" in stats
        assert "has_outcome_assessment" in stats
        assert "has_related_decisions" in stats
        assert "decision_makers" in stats
        
        assert stats["total_decisions"] == len(decision_samples)
        
        # Verify alternatives stats structure
        alt_stats = stats["alternatives_stats"]
        assert "avg" in alt_stats
        assert "min" in alt_stats
        assert "max" in alt_stats
        
        # Verify decision makers structure
        for maker in stats["decision_makers"]:
            assert "name" in maker
            assert "count" in maker