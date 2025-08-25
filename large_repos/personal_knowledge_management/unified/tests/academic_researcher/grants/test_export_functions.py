"""Tests for grant export functionality."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from researchbrain.core.models import (
    Experiment, GrantProposal, Note, ResearchQuestion,
    ExperimentStatus, GrantStatus
)
from researchbrain.grants.export import (
    export_proposal, _export_markdown, _export_yaml
)


class TestGrantExportFunctions:
    """Test grant export functions."""
    
    @pytest.fixture
    def sample_grant(self):
        """Create a sample grant proposal for testing."""
        return GrantProposal(
            id=uuid4(),
            title="Test Grant Proposal",
            funding_agency="Test Agency",
            deadline=datetime(2023, 12, 31),
            status=GrantStatus.DRAFTING,
            amount=125000.00,
            description="This is a test grant proposal description.",
            budget_items={
                "personnel": {
                    "PI": 50000.00,
                    "Research Assistant": 35000.00
                },
                "equipment": {
                    "Computer": 3000.00,
                    "Software": 1500.00
                }
            },
            timeline={
                "year 1": {
                    "q1": "Literature review and planning",
                    "q2": "Pilot study",
                    "q3-q4": "Data collection phase 1"
                },
                "year 2": {
                    "q1-q2": "Data analysis",
                    "q3-q4": "Writing and dissemination"
                }
            }
        )
    
    @pytest.fixture
    def sample_notes(self):
        """Create sample notes for testing."""
        return [
            Note(
                id=uuid4(),
                title="Literature Review Note",
                content="This is a note about relevant literature.",
                tags={"literature", "review"}
            ),
            Note(
                id=uuid4(),
                title="Methodology Note",
                content="This is a note about proposed methodology.",
                tags={"methods", "design"}
            )
        ]
    
    @pytest.fixture
    def sample_experiments(self):
        """Create sample experiments for testing."""
        return [
            Experiment(
                id=uuid4(),
                title="Pilot Experiment",
                hypothesis="Testing the main hypothesis",
                status=ExperimentStatus.PLANNED,
                methodology="This is the methodology for the pilot.",
                variables={"independent": ["var1", "var2"], "dependent": ["outcome1"]}
            ),
            Experiment(
                id=uuid4(),
                title="Main Experiment",
                hypothesis="Full test of the hypothesis",
                status=ExperimentStatus.PLANNED,
                methodology="This is the methodology for the main experiment.",
                variables={"independent": ["var1", "var2", "var3"], "dependent": ["outcome1", "outcome2"]},
                results="No results yet as experiment is planned.",
                conclusion="No conclusion yet."
            )
        ]
    
    @pytest.fixture
    def sample_questions(self):
        """Create sample research questions for testing."""
        return [
            ResearchQuestion(
                id=uuid4(),
                question="What is the effect of X on Y?",
                description="This question explores the relationship between X and Y.",
                status="open",
                priority=8
            ),
            ResearchQuestion(
                id=uuid4(),
                question="How does Z moderate the X-Y relationship?",
                description="This question examines Z as a moderator.",
                status="open",
                priority=6
            )
        ]
    
    def test_export_proposal_markdown(self, sample_grant, sample_notes, sample_experiments, sample_questions):
        """Test exporting a grant proposal to markdown."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Test export
            result = export_proposal(
                sample_grant, sample_notes, sample_experiments, sample_questions, temp_path
            )
            assert result is True
            
            # Verify file exists and has content
            assert temp_path.exists()
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check content includes key elements from the grant, notes, experiments, and questions
            assert "Test Grant Proposal" in content
            assert "Test Agency" in content
            assert "$125,000.00" in content
            assert "Literature Review Note" in content
            assert "Pilot Experiment" in content
            assert "What is the effect of X on Y?" in content
            assert "Budget" in content
            assert "Timeline" in content
            assert "Personnel" in content
            assert "Year 1" in content
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)
    
    def test_export_proposal_yaml(self, sample_grant, sample_notes, sample_experiments, sample_questions):
        """Test exporting a grant proposal to YAML."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Test export
            result = export_proposal(
                sample_grant, sample_notes, sample_experiments, sample_questions, temp_path
            )
            assert result is True
            
            # Verify file exists and has content
            assert temp_path.exists()
            
            with open(temp_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Check data structure includes key elements
            assert data["title"] == "Test Grant Proposal"
            assert data["funding_agency"] == "Test Agency"
            assert data["amount"] == 125000.00
            assert len(data["notes_data"]) == 2
            assert len(data["experiments_data"]) == 2
            assert len(data["questions_data"]) == 2
            assert "budget_items" in data
            assert "timeline" in data
            assert "export_metadata" in data
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)
    
    def test_export_proposal_unknown_extension(self, sample_grant, sample_notes, sample_experiments, sample_questions):
        """Test exporting with an unknown file extension (should default to markdown)."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Test export with unknown extension
            result = export_proposal(
                sample_grant, sample_notes, sample_experiments, sample_questions, temp_path
            )
            assert result is True
            
            # Verify file exists and has content in markdown format
            assert temp_path.exists()
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check for markdown formatting
            assert "# Test Grant Proposal" in content
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)
    
    def test_export_markdown_error_handling(self, sample_grant, sample_notes, sample_experiments, sample_questions, monkeypatch):
        """Test error handling in markdown export."""
        # Mock Template.render to raise an exception
        def mock_render(*args, **kwargs):
            raise Exception("Test exception")
        
        monkeypatch.setattr(
            "researchbrain.grants.export.Template.render", 
            mock_render
        )
        
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Export should return False on error
            result = _export_markdown(
                sample_grant, sample_notes, sample_experiments, sample_questions, temp_path
            )
            assert result is False
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)
    
    def test_export_yaml_error_handling(self, sample_grant, sample_notes, sample_experiments, sample_questions, monkeypatch):
        """Test error handling in YAML export."""
        # Mock yaml.dump to raise an exception
        def mock_dump(*args, **kwargs):
            raise Exception("Test exception")
        
        monkeypatch.setattr(
            "yaml.dump", 
            mock_dump
        )
        
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            # Export should return False on error
            result = _export_yaml(
                sample_grant, sample_notes, sample_experiments, sample_questions, temp_path
            )
            assert result is False
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)