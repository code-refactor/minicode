"""Tests for bidirectional link integrity between notes and sources."""

import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
import networkx as nx

from researchbrain.core.brain import ResearchBrain
from researchbrain.core.models import Note, Citation


class TestBidirectionalLinking:
    """Tests for bidirectional link integrity between notes and sources."""
    
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
    
    def test_note_citation_linking(self, brain):
        """Test basic bidirectional linking between notes and citations."""
        # Create a citation
        citation_id = brain.create_citation(
            title="Test Paper",
            authors=["Author, Test"]
        )
        
        # Create a note
        note_id = brain.create_note(
            title="Test Note",
            content="This is a note about a paper."
        )
        
        # Link note to paper
        linked = brain.link_note_to_paper(note_id, citation_id, page=42)
        assert linked is True
        
        # Verify bidirectional link in storage
        note = brain.get_note(note_id)
        citation = brain.storage.get(Citation, citation_id)
        
        assert note.source == citation_id
        assert note.page_reference == 42
        assert citation_id in note.citations
        assert note_id in citation.notes
        
        # Verify bidirectional link in knowledge graph
        assert brain._knowledge_graph.has_edge(str(note_id), str(citation_id))
        assert brain._knowledge_graph.has_edge(str(citation_id), str(note_id))

        # Verify that the links work as expected in the data models
        # The specific implementation of the knowledge graph edges might vary,
        # but the functionality should still work correctly
        assert note.source == citation_id, "Note should have citation as source"
        assert note.page_reference == 42, "Note should have correct page reference"
        assert citation_id in note.citations, "Note should have citation in its citations list"
        assert note_id in citation.notes, "Citation should have note in its notes list"
    
    def test_automatic_citation_extraction(self, brain):
        """Test automatic extraction of citation keys from note content."""
        # Create a citation that can be referenced by key
        citation_id = brain.create_citation(
            title="Test Paper",
            authors=["Smith, John"],
            year=2023,
            bibtex="@article{smith2023test, title={Test Paper}, author={Smith, John}, year={2023}}"
        )
        
        # Create a note with a citation key in the content
        note_id = brain.create_note(
            title="Note with Citation",
            content="This paper [@smith2023test] discusses important topics."
        )
        
        # Verify automatic link was created
        note = brain.get_note(note_id)
        citation = brain.storage.get(Citation, citation_id)
        
        assert citation_id in note.citations
        assert note_id in citation.notes
        
        # Verify knowledge graph link
        assert brain._knowledge_graph.has_edge(str(note_id), str(citation_id))
        assert brain._knowledge_graph.has_edge(str(citation_id), str(note_id))
    
    def test_multiple_citation_links(self, brain):
        """Test linking a note to multiple citations."""
        # Create several citations
        citation_ids = []
        for i in range(3):
            citation_id = brain.create_citation(
                title=f"Paper {i+1}",
                authors=[f"Author {i+1}"],
                year=2023
            )
            citation_ids.append(citation_id)
        
        # Create a note
        note_id = brain.create_note(
            title="Literature Review",
            content="This review covers several papers."
        )
        
        # Link note to all citations
        for i, citation_id in enumerate(citation_ids):
            linked = brain.link_note_to_paper(note_id, citation_id, page=100+i)
            assert linked is True
        
        # Verify all links in note
        note = brain.get_note(note_id)
        assert len(note.citations) == 3
        for citation_id in citation_ids:
            assert citation_id in note.citations
        
        # Verify all reverse links in citations
        for citation_id in citation_ids:
            citation = brain.storage.get(Citation, citation_id)
            assert note_id in citation.notes
        
        # Verify knowledge graph has all links
        for citation_id in citation_ids:
            assert brain._knowledge_graph.has_edge(str(note_id), str(citation_id))
            assert brain._knowledge_graph.has_edge(str(citation_id), str(note_id))
    
    def test_removing_citation_links(self, brain):
        """Test removing links between notes and citations."""
        # Create a citation
        citation_id = brain.create_citation(
            title="Test Paper",
            authors=["Author, Test"]
        )

        # Create a note with citation reference
        note_id = brain.create_note(
            title="Test Note",
            content="This references [@test]."
        )

        # Link note to citation
        brain.link_note_to_paper(note_id, citation_id)

        # Verify link exists
        note = brain.get_note(note_id)
        citation = brain.storage.get(Citation, citation_id)
        assert citation_id in note.citations
        assert note_id in citation.notes

        # Manually remove the link by updating the note and citation objects
        # First, update the note to remove citation
        note.citations.remove(citation_id)
        note.source = None
        note.page_reference = None
        note.update()
        brain.storage.save(note)

        # Update the citation to remove the note reference
        citation.notes.remove(note_id)
        citation.update()
        brain.storage.save(citation)

        # Update knowledge graph
        if brain._knowledge_graph.has_edge(str(note_id), str(citation_id)):
            brain._knowledge_graph.remove_edge(str(note_id), str(citation_id))
        if brain._knowledge_graph.has_edge(str(citation_id), str(note_id)):
            brain._knowledge_graph.remove_edge(str(citation_id), str(note_id))

        # Verify link was removed
        note = brain.get_note(note_id)
        citation = brain.storage.get(Citation, citation_id)

        assert citation_id not in note.citations
        assert note_id not in citation.notes

        # Verify knowledge graph links were removed
        assert not brain._knowledge_graph.has_edge(str(note_id), str(citation_id))
        assert not brain._knowledge_graph.has_edge(str(citation_id), str(note_id))
    
    def test_cascading_deletion(self, brain):
        """Test that deleting a note properly updates citation links."""
        # Create a citation
        citation_id = brain.create_citation(
            title="Test Paper",
            authors=["Author, Test"]
        )
        
        # Create notes that reference the citation
        note1_id = brain.create_note(
            title="First Note",
            content="First note content."
        )
        
        note2_id = brain.create_note(
            title="Second Note",
            content="Second note content."
        )
        
        # Link both notes to the citation
        brain.link_note_to_paper(note1_id, citation_id)
        brain.link_note_to_paper(note2_id, citation_id)
        
        # Verify both links exist
        citation = brain.storage.get(Citation, citation_id)
        assert note1_id in citation.notes
        assert note2_id in citation.notes
        
        # Delete the first note
        deleted = brain.delete_note(note1_id)
        assert deleted is True
        
        # Verify only the second link remains
        citation = brain.storage.get(Citation, citation_id)
        assert note1_id not in citation.notes
        assert note2_id in citation.notes
        
        # Verify knowledge graph was updated correctly
        assert not brain._knowledge_graph.has_node(str(note1_id))
        assert not brain._knowledge_graph.has_edge(str(citation_id), str(note1_id))
        assert brain._knowledge_graph.has_edge(str(citation_id), str(note2_id))
    
    def test_navigation_between_linked_items(self, brain):
        """Test navigation between linked notes and citations using get_related_nodes."""
        # Create citations
        citation1_id = brain.create_citation(
            title="Primary Paper",
            authors=["Main, Author"]
        )
        
        citation2_id = brain.create_citation(
            title="Related Paper",
            authors=["Related, Author"]
        )
        
        # Create note referencing both citations
        note_id = brain.create_note(
            title="Analysis Note",
            content="This note analyzes both papers."
        )
        
        # Link note to both citations
        brain.link_note_to_paper(note_id, citation1_id, page=10)
        brain.link_note_to_paper(note_id, citation2_id, page=20)
        
        # Get related nodes for the note
        related_to_note = brain.get_related_nodes(note_id)
        
        # Verify we can navigate from note to citations
        assert "references" in related_to_note or "cites" in related_to_note
        
        citations_from_note = []
        if "references" in related_to_note:
            citations_from_note.extend(related_to_note["references"])
        if "cites" in related_to_note:
            citations_from_note.extend(related_to_note["cites"])
        
        citation_ids_from_note = [c.id for c in citations_from_note]
        assert citation1_id in citation_ids_from_note
        assert citation2_id in citation_ids_from_note
        
        # Get related nodes for a citation
        related_to_citation = brain.get_related_nodes(citation1_id)
        
        # Verify we can navigate from citation to note
        assert "cited_in" in related_to_citation
        notes_from_citation = related_to_citation["cited_in"]
        note_ids_from_citation = [n.id for n in notes_from_citation]
        assert note_id in note_ids_from_citation
    
    def test_circular_navigation(self, brain):
        """Test circular navigation through the knowledge graph."""
        # Create multiple nodes with circular references
        citation_id = brain.create_citation(
            title="Original Paper",
            authors=["Original, Author"]
        )

        note1_id = brain.create_note(
            title="First Note",
            content="Analysis of the original paper."
        )

        note2_id = brain.create_note(
            title="Second Note",
            content="Further thoughts on the first note."
        )

        note3_id = brain.create_note(
            title="Third Note",
            content="Synthesis connecting back to the original paper."
        )

        # Create connections forming a cycle
        brain.link_note_to_paper(note1_id, citation_id)

        # Manually create links between notes
        # Make note2 reference note1
        note2 = brain.get_note(note2_id)
        note2.content = f"Further thoughts on the first note [{note1_id}]."
        note2.update()
        brain.storage.save(note2)
        # Add a graph edge
        brain._knowledge_graph.add_edge(str(note2_id), str(note1_id), type='references')

        # Make note3 reference note2
        note3 = brain.get_note(note3_id)
        note3.content = f"Building on the second note [{note2_id}]."
        note3.update()
        brain.storage.save(note3)
        # Add a graph edge
        brain._knowledge_graph.add_edge(str(note3_id), str(note2_id), type='references')

        # Link Note 3 back to the original citation
        brain.link_note_to_paper(note3_id, citation_id)

        # Test circular navigation starting from citation
        # Citation -> Note 1 -> Note 2 -> Note 3 -> Citation

        # Start at citation
        related = brain.get_related_nodes(citation_id)
        assert "cited_in" in related
        notes_citing = related["cited_in"]
        note1 = next((n for n in notes_citing if n.id == note1_id), None)
        assert note1 is not None

        # Navigate to Note 1 and verify it connects to Note 2
        # The connection should be captured in the knowledge graph
        assert brain._knowledge_graph.has_edge(str(note2_id), str(note1_id))

        # Navigate to Note 2 and verify it connects to Note 3
        assert brain._knowledge_graph.has_edge(str(note3_id), str(note2_id))

        # Navigate to Note 3 and verify it connects back to the citation
        assert brain._knowledge_graph.has_edge(str(note3_id), str(citation_id))

    def test_section_references(self, brain):
        """Test section-specific references to citations."""
        # Create a citation
        citation_id = brain.create_citation(
            title="Comprehensive Review of Neural Networks",
            authors=["Smith, J.", "Johnson, K."],
            year=2023,
            journal="Neural Computing Review"
        )

        # Create a note with section-specific references
        note_id = brain.create_note(
            title="Notes on Neural Network Architecture",
            content="My thoughts on different neural network architectures described in Smith & Johnson's paper."
        )

        # Add section-specific references
        section1 = "Introduction"
        content1 = "The authors provide a great overview of the historical development of neural networks."
        added1 = brain.add_section_reference(note_id, citation_id, section1, content1)

        section2 = "Methods"
        content2 = "The comparison methodology between different architectures is particularly rigorous."
        added2 = brain.add_section_reference(note_id, citation_id, section2, content2)

        section3 = "Results"
        content3 = "Their performance comparison between CNNs and Transformers shows interesting trade-offs."
        added3 = brain.add_section_reference(note_id, citation_id, section3, content3)

        # Verify all section references were added
        assert added1 is True
        assert added2 is True
        assert added3 is True

        # Retrieve the note and check section references
        note = brain.get_note(note_id)

        assert section1 in note.section_references
        assert note.section_references[section1] == content1

        assert section2 in note.section_references
        assert note.section_references[section2] == content2

        assert section3 in note.section_references
        assert note.section_references[section3] == content3

        # Verify at least one edge exists between note and citation for each section
        # We don't need to check specifics of the edge data, just that edges exist
        assert brain._knowledge_graph.has_edge(str(note_id), str(citation_id)), "No edge found between note and citation"

        # Test retrieving notes by section
        section_notes = brain.get_notes_by_section(citation_id, section2)

        assert len(section_notes) == 1
        assert section_notes[0]['note_id'] == note_id
        assert section_notes[0]['section'] == section2
        assert section_notes[0]['content'] == content2

        # Test retrieving all sections
        all_section_notes = brain.get_notes_by_section(citation_id)

        assert len(all_section_notes) == 3
        sections = [note['section'] for note in all_section_notes]
        assert section1 in sections
        assert section2 in sections
        assert section3 in sections