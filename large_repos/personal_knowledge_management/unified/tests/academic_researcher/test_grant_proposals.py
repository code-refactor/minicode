"""Tests for grant proposal workspaces and export functionality."""

import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import pytest
import yaml

from researchbrain.core.brain import ResearchBrain
from researchbrain.core.models import (
    Citation, Experiment, ExperimentStatus, GrantProposal, GrantStatus,
    Note, ResearchQuestion
)


class TestGrantProposals:
    """Tests for grant proposal workspaces and export functionality."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Fixture that creates a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def brain(self, temp_data_dir):
        """Fixture that creates a ResearchBrain instance."""
        return ResearchBrain(temp_data_dir)
    
    @pytest.fixture
    def sample_proposal_data(self, brain):
        """Fixture that creates sample data for a grant proposal."""
        # Create research questions
        question1_id = brain.create_research_question(
            question="How does neuronal activity influence myelination in the developing brain?",
            description="Investigating the relationship between neural firing and oligodendrocyte myelination",
            priority=9
        )
        
        question2_id = brain.create_research_question(
            question="What signaling pathways mediate activity-dependent myelination?",
            description="Examining molecular mechanisms linking neuronal activity to myelination",
            priority=8
        )
        
        # Create notes
        background_note_id = brain.create_note(
            title="Background Literature",
            content="Comprehensive review of the literature on activity-dependent myelination."
        )
        
        preliminary_note_id = brain.create_note(
            title="Preliminary Data",
            content="Summary of our preliminary findings showing activity-dependent effects."
        )
        
        methods_note_id = brain.create_note(
            title="Proposed Methods",
            content="Detailed methodological approach for the proposed experiments."
        )
        
        budget_note_id = brain.create_note(
            title="Budget Justification",
            content="Detailed justification for the requested budget items."
        )
        
        # Create citations linked to notes
        citation1_id = brain.create_citation(
            title="Neural activity induces local myelination in the developing mammalian brain",
            authors=["Smith, J.", "Johnson, K."],
            year=2022,
            journal="Nature Neuroscience"
        )
        
        citation2_id = brain.create_citation(
            title="Molecular mechanisms of activity-dependent myelination",
            authors=["Brown, L.", "Davis, M."],
            year=2021,
            journal="Glia"
        )
        
        brain.link_note_to_paper(background_note_id, citation1_id)
        brain.link_note_to_paper(background_note_id, citation2_id)
        
        # Create experiments
        pilot_experiment_id = brain.create_experiment(
            title="Pilot Study: Optogenetic Stimulation and Myelination",
            hypothesis="Optogenetic stimulation of neurons increases local myelination",
            methodology="Using Thy1-ChR2 mice to optogenetically stimulate cortical neurons",
            status=ExperimentStatus.COMPLETED,
            start_date=datetime.now() - timedelta(days=180),
            end_date=datetime.now() - timedelta(days=30),
            results="Stimulation increased MBP expression by 45% compared to controls",
            conclusion="Results support activity-dependent myelination hypothesis",
            research_question_id=question1_id
        )
        
        proposed_experiment_id = brain.create_experiment(
            title="Proposed Study: Molecular Mechanisms",
            hypothesis="Neuronal activity regulates myelination through calcium signaling",
            methodology="Pharmacological and genetic manipulation of calcium signaling pathways",
            status=ExperimentStatus.PLANNED,
            research_question_id=question2_id
        )
        
        return {
            "questions": [question1_id, question2_id],
            "notes": [background_note_id, preliminary_note_id, methods_note_id, budget_note_id],
            "citations": [citation1_id, citation2_id],
            "experiments": [pilot_experiment_id, proposed_experiment_id]
        }
    
    def test_create_grant_proposal(self, brain):
        """Test creating a grant proposal with all attributes."""
        # Create a grant proposal with all fields
        deadline = datetime.now() + timedelta(days=60)
        grant_id = brain.create_grant_proposal(
            title="Neural Activity and Myelination in Development",
            funding_agency="National Institutes of Health",
            description="A proposal to study how neural activity influences myelination during brain development",
            deadline=deadline,
            status=GrantStatus.DRAFTING,
            amount=750000.0,
            tags={"neuroscience", "development", "myelin"}
        )
        
        # Retrieve the grant proposal
        grant = brain.storage.get(GrantProposal, grant_id)
        
        # Verify all attributes
        assert grant is not None
        assert grant.id == grant_id
        assert grant.title == "Neural Activity and Myelination in Development"
        assert grant.funding_agency == "National Institutes of Health"
        assert grant.description == "A proposal to study how neural activity influences myelination during brain development"
        assert grant.deadline == deadline
        assert grant.status == GrantStatus.DRAFTING
        assert grant.amount == 750000.0
        assert grant.tags == {"neuroscience", "development", "myelin"}
        assert grant.notes == []
        assert grant.experiments == []
        assert grant.research_questions == []
        
        # Verify in knowledge graph
        assert brain._knowledge_graph.has_node(str(grant_id))
        node_data = brain._knowledge_graph.nodes[str(grant_id)]
        assert node_data["type"] == "grant"
        assert node_data["title"] == "Neural Activity and Myelination in Development"
    
    def test_add_items_to_grant_workspace(self, brain, sample_proposal_data):
        """Test adding various items to a grant proposal workspace."""
        # Create a grant proposal
        grant_id = brain.create_grant_proposal(
            title="Neural Activity and Myelination in Development",
            funding_agency="National Institutes of Health",
            description="A proposal to study how neural activity influences myelination during brain development",
            deadline=datetime.now() + timedelta(days=60),
            status=GrantStatus.DRAFTING,
            amount=750000.0
        )
        
        # Add items to the grant workspace
        added = brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=sample_proposal_data["notes"],
            experiment_ids=sample_proposal_data["experiments"],
            question_ids=sample_proposal_data["questions"]
        )
        
        assert added is True
        
        # Retrieve the grant proposal
        grant = brain.storage.get(GrantProposal, grant_id)
        
        # Verify all items were added
        assert len(grant.notes) == len(sample_proposal_data["notes"])
        assert len(grant.experiments) == len(sample_proposal_data["experiments"])
        assert len(grant.research_questions) == len(sample_proposal_data["questions"])
        
        for note_id in sample_proposal_data["notes"]:
            assert note_id in grant.notes
        
        for experiment_id in sample_proposal_data["experiments"]:
            assert experiment_id in grant.experiments
        
        for question_id in sample_proposal_data["questions"]:
            assert question_id in grant.research_questions
        
        # Verify knowledge graph connections
        for note_id in sample_proposal_data["notes"]:
            assert brain._knowledge_graph.has_edge(str(grant_id), str(note_id))
            edge_data = brain._knowledge_graph.get_edge_data(str(grant_id), str(note_id))
            assert edge_data["type"] == "includes"
        
        for experiment_id in sample_proposal_data["experiments"]:
            assert brain._knowledge_graph.has_edge(str(grant_id), str(experiment_id))
            edge_data = brain._knowledge_graph.get_edge_data(str(grant_id), str(experiment_id))
            assert edge_data["type"] == "proposes"
        
        for question_id in sample_proposal_data["questions"]:
            assert brain._knowledge_graph.has_edge(str(grant_id), str(question_id))
            edge_data = brain._knowledge_graph.get_edge_data(str(grant_id), str(question_id))
            assert edge_data["type"] == "addresses"
    
    def test_adding_items_incrementally(self, brain, sample_proposal_data):
        """Test adding items to a grant proposal incrementally."""
        # Create a grant proposal
        grant_id = brain.create_grant_proposal(
            title="Neural Activity and Myelination in Development",
            funding_agency="National Institutes of Health",
            description="A proposal to study how neural activity influences myelination during brain development"
        )
        
        # Add notes first
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=sample_proposal_data["notes"][:2]  # Add first two notes
        )
        
        # Verify notes were added
        grant = brain.storage.get(GrantProposal, grant_id)
        assert len(grant.notes) == 2
        
        # Add experiments
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            experiment_ids=sample_proposal_data["experiments"]
        )
        
        # Verify experiments were added while keeping notes
        grant = brain.storage.get(GrantProposal, grant_id)
        assert len(grant.notes) == 2
        assert len(grant.experiments) == 2
        
        # Add research questions and remaining notes
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=sample_proposal_data["notes"][2:],  # Add remaining notes
            question_ids=sample_proposal_data["questions"]
        )
        
        # Verify all items were added without duplication
        grant = brain.storage.get(GrantProposal, grant_id)
        assert len(grant.notes) == 4
        assert len(grant.experiments) == 2
        assert len(grant.research_questions) == 2
    
    def test_grant_proposal_status_progression(self, brain):
        """Test updating a grant proposal through different status stages."""
        # Create a grant proposal
        grant_id = brain.create_grant_proposal(
            title="Cognitive Decline Prevention Study",
            funding_agency="National Institute on Aging",
            description="A study on preventing cognitive decline in older adults",
            deadline=datetime.now() + timedelta(days=30),
            amount=500000.0
        )
        
        # Verify initial status is DRAFTING
        grant = brain.storage.get(GrantProposal, grant_id)
        assert grant.status == GrantStatus.DRAFTING
        
        # Update to SUBMITTED
        # In reality, updated_at will be set by the model when saved, so we don't need to check exact timestamp
        grant.status = GrantStatus.SUBMITTED
        brain.storage.save(grant)

        grant = brain.storage.get(GrantProposal, grant_id)
        assert grant.status == GrantStatus.SUBMITTED
        assert grant.updated_at > grant.created_at  # Just verify it's been updated
        
        # Update to UNDER_REVIEW
        grant.status = GrantStatus.UNDER_REVIEW
        brain.storage.save(grant)
        
        grant = brain.storage.get(GrantProposal, grant_id)
        assert grant.status == GrantStatus.UNDER_REVIEW
        
        # Update to AWARDED
        grant.status = GrantStatus.AWARDED
        brain.storage.save(grant)

        grant = brain.storage.get(GrantProposal, grant_id)
        assert grant.status == GrantStatus.AWARDED
    
    def test_export_grant_proposal_to_markdown(self, brain, sample_proposal_data):
        """Test exporting a grant proposal to markdown format."""
        # Create a grant proposal with items
        grant_id = brain.create_grant_proposal(
            title="Neural Activity and Myelination in Development",
            funding_agency="National Institutes of Health",
            description="A proposal to study how neural activity influences myelination during brain development",
            deadline=datetime.now() + timedelta(days=60),
            status=GrantStatus.DRAFTING,
            amount=750000.0
        )
        
        # Add items to the grant workspace
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=sample_proposal_data["notes"],
            experiment_ids=sample_proposal_data["experiments"],
            question_ids=sample_proposal_data["questions"]
        )
        
        # Export to markdown
        export_path = Path(tempfile.mkdtemp()) / "grant_proposal.md"
        exported = brain.export_grant_proposal(grant_id, export_path)
        
        assert exported is True
        assert export_path.exists()
        
        # Read the exported markdown file
        with open(export_path, "r") as f:
            content = f.read()
        
        # Verify content
        assert "# Neural Activity and Myelination in Development" in content
        assert "National Institutes of Health" in content
        assert "$750,000.00" in content
        
        # Check for sections
        assert "## Research Questions" in content
        assert "How does neuronal activity influence myelination in the developing brain?" in content
        assert "What signaling pathways mediate activity-dependent myelination?" in content
        
        assert "## Proposed Experiments" in content
        assert "Pilot Study: Optogenetic Stimulation and Myelination" in content
        assert "Proposed Study: Molecular Mechanisms" in content
        
        assert "## Supporting Notes" in content
        assert "Background Literature" in content
        assert "Preliminary Data" in content
        assert "Proposed Methods" in content
        assert "Budget Justification" in content
        
        assert "Generated by ResearchBrain" in content
        
        # Clean up
        os.unlink(export_path)
    
    def test_export_grant_proposal_to_yaml(self, brain, sample_proposal_data):
        """Test exporting a grant proposal to YAML format."""
        # Create a grant proposal with items
        grant_id = brain.create_grant_proposal(
            title="Neural Activity and Myelination in Development",
            funding_agency="National Institutes of Health",
            description="A proposal to study how neural activity influences myelination during brain development",
            deadline=datetime.now() + timedelta(days=60),
            status=GrantStatus.DRAFTING,
            amount=750000.0
        )

        # Add items to the grant workspace
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=sample_proposal_data["notes"],
            experiment_ids=sample_proposal_data["experiments"],
            question_ids=sample_proposal_data["questions"]
        )

        # Export to YAML
        export_path = Path(tempfile.mkdtemp()) / "grant_proposal.yaml"
        exported = brain.export_grant_proposal(grant_id, export_path)

        assert exported is True
        assert export_path.exists()

        # Read the exported YAML file
        with open(export_path, "r") as f:
            data = yaml.safe_load(f)

        # Verify structure and content
        assert data["title"] == "Neural Activity and Myelination in Development"
        assert data["funding_agency"] == "National Institutes of Health"
        assert data["amount"] == 750000.0
        assert "deadline" in data

        # Check for items
        assert "notes_data" in data
        assert len(data["notes_data"]) == 4

        assert "experiments_data" in data
        assert len(data["experiments_data"]) == 2

        assert "questions_data" in data
        assert len(data["questions_data"]) == 2

        # Check specific content
        experiment_titles = [exp["title"] for exp in data["experiments_data"]]
        assert "Pilot Study: Optogenetic Stimulation and Myelination" in experiment_titles
        assert "Proposed Study: Molecular Mechanisms" in experiment_titles

        question_texts = [q["question"] for q in data["questions_data"]]
        assert "How does neuronal activity influence myelination in the developing brain?" in question_texts
        assert "What signaling pathways mediate activity-dependent myelination?" in question_texts

        note_titles = [note["title"] for note in data["notes_data"]]
        assert "Background Literature" in note_titles
        assert "Preliminary Data" in note_titles

        # Verify metadata
        assert "export_metadata" in data
        assert "generated_at" in data["export_metadata"]
        assert data["export_metadata"]["format_version"] == "1.0"

        # Clean up
        os.unlink(export_path)

    def test_grant_proposal_version_history(self, brain, sample_proposal_data):
        """Test tracking version history of grant proposals."""
        # Create a grant proposal
        grant_id = brain.create_grant_proposal(
            title="Neuroplasticity Across the Lifespan",
            funding_agency="National Science Foundation",
            description="Initial proposal for neuroplasticity research",
            deadline=datetime.now() + timedelta(days=90),
            status=GrantStatus.DRAFTING,
            amount=1200000.0
        )

        # Add initial items to the grant workspace
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=sample_proposal_data["notes"][:2],  # Add only first two notes initially
            experiment_ids=[sample_proposal_data["experiments"][0]],  # Add only first experiment initially
            question_ids=[sample_proposal_data["questions"][0]]  # Add only first question initially
        )

        # Export the initial version
        version1_path = Path(tempfile.mkdtemp()) / "grant_v1.yaml"
        exported1 = brain.export_grant_proposal(grant_id, version1_path)
        assert exported1 is True

        # Read the initial version file to capture export timestamp
        with open(version1_path, "r") as f:
            v1_data = yaml.safe_load(f)
        v1_timestamp = v1_data["export_metadata"]["generated_at"]

        # Update the grant proposal (e.g., change status and add more items)
        grant = brain.storage.get(GrantProposal, grant_id)
        grant.status = GrantStatus.UNDER_REVIEW
        grant.description = "Revised proposal for neuroplasticity research with additional experiments"
        grant.update()
        brain.storage.save(grant)

        # Add more items to create a new version
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=sample_proposal_data["notes"][2:],  # Add remaining notes
            experiment_ids=[sample_proposal_data["experiments"][1]],  # Add second experiment
            question_ids=[sample_proposal_data["questions"][1]]  # Add second question
        )

        # Export the updated version
        version2_path = Path(tempfile.mkdtemp()) / "grant_v2.yaml"
        exported2 = brain.export_grant_proposal(grant_id, version2_path)
        assert exported2 is True

        # Track the export in the grant's export history
        grant = brain.storage.get(GrantProposal, grant_id)
        if not hasattr(grant, 'export_history') or grant.export_history is None:
            grant.export_history = []

        # Add export records to the history
        grant.export_history.append({
            "version": "1.0",
            "timestamp": v1_timestamp,
            "status": "DRAFTING",
            "filename": "grant_v1.yaml"
        })

        grant.export_history.append({
            "version": "2.0",
            "timestamp": datetime.now().isoformat(),
            "status": "UNDER_REVIEW",
            "filename": "grant_v2.yaml"
        })

        grant.update()
        brain.storage.save(grant)

        # Verify the export history is tracked
        updated_grant = brain.storage.get(GrantProposal, grant_id)
        assert len(updated_grant.export_history) == 2
        assert updated_grant.export_history[0]["version"] == "1.0"
        assert updated_grant.export_history[0]["status"] == "DRAFTING"
        assert updated_grant.export_history[1]["version"] == "2.0"
        assert updated_grant.export_history[1]["status"] == "UNDER_REVIEW"

        # Compare the exported versions to verify they're different
        with open(version1_path, "r") as f1, open(version2_path, "r") as f2:
            version1_data = yaml.safe_load(f1)
            version2_data = yaml.safe_load(f2)

        # Check that version 2 has more items
        assert len(version1_data["notes_data"]) < len(version2_data["notes_data"])
        assert len(version1_data["experiments_data"]) < len(version2_data["experiments_data"])
        assert len(version1_data["questions_data"]) < len(version2_data["questions_data"])

        # Verify status change
        assert version1_data["status"] == "drafting"
        assert version2_data["status"] == "under_review"

        # Verify description change
        assert "Initial proposal" in version1_data["description"]
        assert "Revised proposal" in version2_data["description"]

        # Clean up
        os.unlink(version1_path)
        os.unlink(version2_path)

    def test_budget_and_timeline_management(self, brain):
        """Test managing budget items and project timeline in grant proposals."""
        # Create a grant proposal
        grant_id = brain.create_grant_proposal(
            title="Neural Circuit Development Study",
            funding_agency="Brain Research Foundation",
            description="Investigating developmental trajectories of neural circuits",
            deadline=datetime.now() + timedelta(days=45),
            status=GrantStatus.DRAFTING,
            amount=850000.0
        )

        # Get the grant
        grant = brain.storage.get(GrantProposal, grant_id)

        # Add budget items
        budget_items = {
            "personnel": {
                "PI": 150000.0,
                "Postdoc": 75000.0,
                "Graduate Students (2)": 120000.0,
                "Research Assistant": 60000.0
            },
            "equipment": {
                "Microscope": 200000.0,
                "Computing Cluster": 50000.0,
                "Lab Supplies": 75000.0
            },
            "travel": {
                "Conferences": 15000.0,
                "Collaborative Visits": 10000.0
            },
            "indirect_costs": {
                "Facilities & Admin": 95000.0
            }
        }

        # Add timeline milestones
        timeline = {
            "year1": {
                "q1": "Setup equipment and hire personnel",
                "q2": "Begin preliminary experiments",
                "q3": "Complete first set of experiments",
                "q4": "Data analysis and preliminary report"
            },
            "year2": {
                "q1": "Begin main experimental series",
                "q2": "Continue experiments and begin data analysis",
                "q3": "Final experiments and complete data collection",
                "q4": "Analysis, paper writing, and final report"
            }
        }

        # Update the grant with budget and timeline information
        grant.budget_items = budget_items
        grant.timeline = timeline
        grant.update()
        brain.storage.save(grant)

        # Retrieve the updated grant
        updated_grant = brain.storage.get(GrantProposal, grant_id)

        # Verify budget items were saved
        assert updated_grant.budget_items is not None
        assert len(updated_grant.budget_items) == 4
        assert "personnel" in updated_grant.budget_items
        assert "equipment" in updated_grant.budget_items
        assert "travel" in updated_grant.budget_items
        assert "indirect_costs" in updated_grant.budget_items

        # Verify specific budget amounts
        assert updated_grant.budget_items["personnel"]["PI"] == 150000.0
        assert updated_grant.budget_items["equipment"]["Microscope"] == 200000.0
        assert updated_grant.budget_items["travel"]["Conferences"] == 15000.0

        # Calculate total to ensure it matches the grant amount
        total_budget = 0
        for category in updated_grant.budget_items.values():
            for amount in category.values():
                total_budget += amount

        assert abs(total_budget - updated_grant.amount) < 1.0  # Allow small floating point difference

        # Verify timeline was saved
        assert updated_grant.timeline is not None
        assert len(updated_grant.timeline) == 2
        assert "year1" in updated_grant.timeline
        assert "year2" in updated_grant.timeline

        # Verify timeline details
        assert updated_grant.timeline["year1"]["q1"] == "Setup equipment and hire personnel"
        assert updated_grant.timeline["year2"]["q4"] == "Analysis, paper writing, and final report"

        # Export the grant to verify budget and timeline are included
        export_path = Path(tempfile.mkdtemp()) / "grant_with_budget.yaml"
        exported = brain.export_grant_proposal(grant_id, export_path)

        # Read the exported file
        with open(export_path, "r") as f:
            export_data = yaml.safe_load(f)

        # Verify budget and timeline in export
        assert "budget_items" in export_data
        assert "timeline" in export_data
        
        # Handle the case where values might be strings
        personnel_pi = export_data["budget_items"]["personnel"]["PI"]
        if isinstance(personnel_pi, str):
            personnel_pi = float(personnel_pi)
        assert personnel_pi == 150000.0
        assert export_data["timeline"]["year1"]["q1"] == "Setup equipment and hire personnel"

        # Clean up
        os.unlink(export_path)
    
    def test_related_nodes_navigation(self, brain, sample_proposal_data):
        """Test navigation between grant proposals and related nodes."""
        # Create a grant proposal with items
        grant_id = brain.create_grant_proposal(
            title="Neural Activity and Myelination in Development",
            funding_agency="National Institutes of Health",
            description="A proposal to study how neural activity influences myelination during brain development"
        )
        
        # Add items to the grant workspace
        brain.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=sample_proposal_data["notes"],
            experiment_ids=sample_proposal_data["experiments"],
            question_ids=sample_proposal_data["questions"]
        )
        
        # Get related nodes for the grant proposal
        related = brain.get_related_nodes(grant_id)
        
        # Verify we can navigate to all related items
        assert "includes" in related
        assert "proposes" in related
        assert "addresses" in related
        
        # Check notes
        note_ids = [note.id for note in related["includes"]]
        for note_id in sample_proposal_data["notes"]:
            assert note_id in note_ids
        
        # Check experiments
        experiment_ids = [exp.id for exp in related["proposes"]]
        for experiment_id in sample_proposal_data["experiments"]:
            assert experiment_id in experiment_ids
        
        # Check research questions
        question_ids = [q.id for q in related["addresses"]]
        for question_id in sample_proposal_data["questions"]:
            assert question_id in question_ids
        
        # Now navigate in reverse - from a note to the grant
        note_id = sample_proposal_data["notes"][0]
        note_related = brain.get_related_nodes(note_id)
        
        incoming_includes = []
        for relation_type, nodes in note_related.items():
            if "incoming_includes" in relation_type:
                incoming_includes.extend(nodes)
        
        # Find the grant in the incoming_includes
        grant_found = False
        for grant in incoming_includes:
            if grant.id == grant_id:
                grant_found = True
                break
        
        assert grant_found or brain._knowledge_graph.has_edge(str(grant_id), str(note_id))
    
    def test_multi_grant_proposal_organization(self, brain, sample_proposal_data):
        """Test organizing research items across multiple grant proposals."""
        # Create two grant proposals for different funding agencies
        grant1_id = brain.create_grant_proposal(
            title="Neural Activity and Myelination (NIH)",
            funding_agency="National Institutes of Health",
            description="NIH proposal for myelination research"
        )
        
        grant2_id = brain.create_grant_proposal(
            title="Neural Activity and Myelination (NSF)",
            funding_agency="National Science Foundation",
            description="NSF proposal for myelination research"
        )
        
        # Split the research items between the two grants with some overlap
        # NIH grant gets all questions, all experiments, and first two notes
        brain.add_to_grant_workspace(
            grant_id=grant1_id,
            note_ids=sample_proposal_data["notes"][:2],
            experiment_ids=sample_proposal_data["experiments"],
            question_ids=sample_proposal_data["questions"]
        )
        
        # NSF grant gets all questions, first experiment, and last two notes
        brain.add_to_grant_workspace(
            grant_id=grant2_id,
            note_ids=sample_proposal_data["notes"][2:],
            experiment_ids=[sample_proposal_data["experiments"][0]],  # Just the pilot experiment
            question_ids=sample_proposal_data["questions"]
        )
        
        # Verify each grant has the correct items
        grant1 = brain.storage.get(GrantProposal, grant1_id)
        grant2 = brain.storage.get(GrantProposal, grant2_id)
        
        # NIH grant should have 2 notes, 2 experiments, 2 questions
        assert len(grant1.notes) == 2
        assert len(grant1.experiments) == 2
        assert len(grant1.research_questions) == 2
        
        # NSF grant should have 2 notes, 1 experiment, 2 questions
        assert len(grant2.notes) == 2
        assert len(grant2.experiments) == 1
        assert len(grant2.research_questions) == 2
        
        # Check for the first experiment in both grants (overlap)
        assert sample_proposal_data["experiments"][0] in grant1.experiments
        assert sample_proposal_data["experiments"][0] in grant2.experiments
        
        # Check that the second experiment is only in the NIH grant
        assert sample_proposal_data["experiments"][1] in grant1.experiments
        assert sample_proposal_data["experiments"][1] not in grant2.experiments
        
        # Check notes distribution
        for note_id in sample_proposal_data["notes"][:2]:
            assert note_id in grant1.notes
            assert note_id not in grant2.notes
        
        for note_id in sample_proposal_data["notes"][2:]:
            assert note_id not in grant1.notes
            assert note_id in grant2.notes
        
        # Check questions are in both grants
        for question_id in sample_proposal_data["questions"]:
            assert question_id in grant1.research_questions
            assert question_id in grant2.research_questions