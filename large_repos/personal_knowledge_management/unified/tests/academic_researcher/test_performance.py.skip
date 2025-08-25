"""Performance tests for the ResearchBrain system."""

import os
import shutil
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import pytest

from researchbrain.core.brain import ResearchBrain
from researchbrain.core.models import (
    Citation, EvidenceStrength, EvidenceType, Note, ResearchQuestion
)


class TestPerformance:
    """Performance tests for the ResearchBrain system."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Fixture that creates a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def brain_with_data(self, temp_data_dir):
        """Fixture that creates a ResearchBrain instance with test data."""
        brain = ResearchBrain(temp_data_dir)
        
        # Create test data
        self._create_test_data(brain, note_count=100, citation_count=50, question_count=20)
        
        return brain
    
    def _create_test_data(self, brain, note_count=100, citation_count=50, question_count=20):
        """Create test data for performance testing.
        
        Args:
            brain: ResearchBrain instance.
            note_count: Number of notes to create.
            citation_count: Number of citations to create.
            question_count: Number of research questions to create.
        """
        # Create citations
        citation_ids = []
        for i in range(citation_count):
            citation_id = brain.create_citation(
                title=f"Citation {i}",
                authors=[f"Author {i}", "Collaborator"],
                year=2020 + (i % 5),
                journal=f"Journal {i % 10}",
                abstract=f"Abstract for citation {i}" * 10  # Make it longer
            )
            citation_ids.append(citation_id)
        
        # Create notes
        note_ids = []
        for i in range(note_count):
            # Link to random citations
            citations = []
            for j in range(min(5, citation_count)):
                if (i + j) % citation_count < len(citation_ids):
                    citations.append(citation_ids[(i + j) % citation_count])
            
            note_id = brain.create_note(
                title=f"Note {i}",
                content=f"Content for note {i}\n" * 20,  # Make it longer
                tags={f"tag{i % 10}", f"category{i % 5}"}
            )
            note_ids.append(note_id)
            
            # Link notes to citations
            for citation_id in citations:
                brain.link_note_to_paper(note_id, citation_id)
        
        # Create research questions
        question_ids = []
        for i in range(question_count):
            question_id = brain.create_research_question(
                question=f"Research question {i}?",
                description=f"Description for research question {i}" * 5,
                priority=i % 10
            )
            question_ids.append(question_id)
            
            # Add evidence
            for j in range(min(5, note_count)):
                if (i + j) % note_count < len(note_ids):
                    note_id = note_ids[(i + j) % note_count]
                    
                    evidence_type = EvidenceType.SUPPORTING if j % 3 != 0 else EvidenceType.CONTRADICTING
                    strength = EvidenceStrength.STRONG if j % 2 == 0 else EvidenceStrength.MODERATE
                    
                    brain.add_evidence_to_question(
                        question_id=question_id,
                        note_id=note_id,
                        evidence_type=evidence_type,
                        strength=strength,
                        description=f"Evidence {j} for question {i}"
                    )
    
    def test_note_creation_performance(self, brain_with_data):
        """Test performance of note creation."""
        # Measure time to create 100 notes
        start_time = time.time()
        
        for i in range(100):
            brain_with_data.create_note(
                title=f"Performance Test Note {i}",
                content=f"Content for performance test note {i}\n" * 10,
                tags={f"perf{i % 10}", "test"}
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print performance metrics
        print(f"\nCreated 100 notes in {duration:.2f} seconds ({duration/100:.4f} seconds per note)")
        
        # Check performance requirement (500ms per note)
        assert duration / 100 < 0.5, f"Note creation too slow: {duration/100:.4f} seconds per note (should be < 0.5)"
    
    def test_search_performance(self, brain_with_data):
        """Test performance of search operations."""
        # Measure time for full-text search
        start_time = time.time()
        
        results = brain_with_data.search("Content")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print performance metrics
        print(f"\nFull-text search completed in {duration:.4f} seconds")
        
        # Check performance requirement (under 2 seconds)
        assert duration < 2.0, f"Search too slow: {duration:.4f} seconds (should be < 2.0)"
        
        # Count results
        total_results = sum(len(items) for items in results.values())
        print(f"Found {total_results} results across {len(results)} categories")
    
    def test_citation_linking_performance(self, brain_with_data):
        """Test performance of citation linking operations."""
        # Create test data
        citation_ids = []
        for i in range(100):
            citation_id = brain_with_data.create_citation(
                title=f"Performance Citation {i}",
                authors=[f"Test Author {i}"],
                year=2023
            )
            citation_ids.append(citation_id)
        
        note_id = brain_with_data.create_note(
            title="Citation Link Performance Test",
            content="Test note for citation linking performance"
        )
        
        # Measure time to link 100 citations
        start_time = time.time()
        
        for citation_id in citation_ids:
            brain_with_data.link_note_to_paper(note_id, citation_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print performance metrics
        print(f"\nLinked 100 citations in {duration:.2f} seconds ({duration/100:.4f} seconds per link)")
        
        # Check performance requirement (500ms per linking operation)
        assert duration / 100 < 0.5, f"Citation linking too slow: {duration/100:.4f} seconds per link (should be < 0.5)"
    
    def test_large_graph_performance(self, temp_data_dir):
        """Test performance with a large knowledge graph (10,000+ nodes)."""
        # Always run the test
        
        # Initialize brain
        brain = ResearchBrain(temp_data_dir)
        
        # Create test data with large counts
        start_time = time.time()
        self._create_test_data(brain, note_count=8000, citation_count=2000, question_count=200)
        creation_time = time.time() - start_time
        
        print(f"\nCreated large knowledge graph (10,200+ nodes) in {creation_time:.2f} seconds")
        
        # Measure graph operations time
        start_time = time.time()
        
        # Perform some operations on the large graph
        results = brain.search("research")
        total_results = sum(len(items) for items in results.values())
        
        # Get related nodes for a random note
        notes = brain.storage.list_all(Note)
        if notes:
            related = brain.get_related_nodes(notes[0].id)
        
        operation_time = time.time() - start_time
        
        print(f"Performed operations on large graph in {operation_time:.2f} seconds")
        print(f"Found {total_results} search results")
        
        # Check performance requirement for large graphs
        assert operation_time < 10.0, f"Large graph operations too slow: {operation_time:.2f} seconds (should be < 10.0)"
    
    def test_export_performance(self, brain_with_data, temp_data_dir):
        """Test performance of exporting data."""
        # Create a grant proposal with many items
        grant_id = brain_with_data.create_grant_proposal(
            title="Performance Test Grant",
            funding_agency="Test Agency",
            description="Grant proposal for performance testing"
        )
        
        # Add items to the grant
        notes = brain_with_data.storage.list_all(Note)[:50]  # Add 50 notes
        questions = brain_with_data.storage.list_all(ResearchQuestion)[:20]  # Add 20 questions
        
        brain_with_data.add_to_grant_workspace(
            grant_id=grant_id,
            note_ids=[note.id for note in notes],
            question_ids=[q.id for q in questions]
        )
        
        # Measure export time
        start_time = time.time()
        
        export_path = Path(temp_data_dir) / "export_test.md"
        brain_with_data.export_grant_proposal(grant_id, export_path)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print performance metrics
        print(f"\nExported grant proposal with {len(notes) + len(questions)} items in {duration:.2f} seconds")
        
        # Check file exists and has reasonable size
        assert export_path.exists()
        file_size = export_path.stat().st_size
        print(f"Export file size: {file_size/1024:.1f} KB")
        
        # Check performance requirement (reasonable export time)
        assert duration < 5.0, f"Export too slow: {duration:.2f} seconds (should be < 5.0)"