from datetime import datetime
from uuid import uuid4

import pytest

from researchtrack.bibliography.models import (
    Author,
    AuthorType,
    CitationStyle,
    Reference,
    ReferenceType,
)
from researchtrack.bibliography.service import BibliographyService
from researchtrack.bibliography.storage import InMemoryBibliographyStorage


class TestBibliographyService:
    def setup_method(self):
        """Set up a fresh service instance for each test."""
        self.storage = InMemoryBibliographyStorage()
        self.service = BibliographyService(self.storage)
        
        # Create some task IDs to use in tests
        self.task_id1 = uuid4()
        self.task_id2 = uuid4()
    
    def test_create_author_methods(self):
        # Test the author creation helper methods
        
        # Create person author
        person_author = self.service.create_person_author(
            first_name="John",
            last_name="Smith",
            orcid_id="0000-0001-2345-6789",
        )
        
        assert person_author.type == AuthorType.PERSON
        assert person_author.first_name == "John"
        assert person_author.last_name == "Smith"
        assert person_author.orcid_id == "0000-0001-2345-6789"
        
        # Create organization author
        org_author = self.service.create_organization_author(
            organization_name="National Science Foundation",
        )
        
        assert org_author.type == AuthorType.ORGANIZATION
        assert org_author.organization_name == "National Science Foundation"
    
    def test_create_journal_article(self):
        # Test creating a journal article reference
        author1 = self.service.create_person_author("John", "Smith")
        author2 = self.service.create_person_author("Jane", "Doe")
        
        ref_id = self.service.create_journal_article(
            title="Test Journal Article",
            authors=[author1, author2],
            journal_name="Test Journal",
            year=2022,
            volume="10",
            issue="2",
            pages="123-145",
            doi="10.1234/test.2022.12345",
            abstract="This is a test article",
            keywords={"test", "article"},
        )
        
        ref = self.service.get_reference(ref_id)
        
        assert ref is not None
        assert ref.type == ReferenceType.JOURNAL_ARTICLE
        assert ref.title == "Test Journal Article"
        assert len(ref.authors) == 2
        assert ref.journal_name == "Test Journal"
        assert ref.year == 2022
        assert ref.volume == "10"
        assert ref.issue == "2"
        assert ref.pages == "123-145"
        assert ref.doi == "10.1234/test.2022.12345"
        assert ref.abstract == "This is a test article"
        assert ref.keywords == {"test", "article"}
    
    def test_create_book(self):
        # Test creating a book reference
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_book(
            title="Test Book",
            authors=[author],
            publisher="Test Publisher",
            year=2021,
            isbn="978-1234567890",
            edition="2nd",
            abstract="This is a test book",
            keywords={"test", "book"},
        )
        
        ref = self.service.get_reference(ref_id)
        
        assert ref is not None
        assert ref.type == ReferenceType.BOOK
        assert ref.title == "Test Book"
        assert len(ref.authors) == 1
        assert ref.authors[0].last_name == "Smith"
        assert ref.publisher == "Test Publisher"
        assert ref.year == 2021
        assert ref.isbn == "978-1234567890"
        assert ref.edition == "2nd"
        assert ref.abstract == "This is a test book"
        assert ref.keywords == {"test", "book"}
    
    def test_create_website(self):
        # Test creating a website reference
        org_author = self.service.create_organization_author("Test Organization")
        accessed_date = datetime.now()
        
        ref_id = self.service.create_website(
            title="Test Website",
            authors=[org_author],
            url="https://example.com",
            accessed_date=accessed_date,
            year=2023,
            abstract="This is a test website",
            keywords={"test", "website"},
        )
        
        ref = self.service.get_reference(ref_id)
        
        assert ref is not None
        assert ref.type == ReferenceType.WEBSITE
        assert ref.title == "Test Website"
        assert len(ref.authors) == 1
        assert ref.authors[0].organization_name == "Test Organization"
        assert ref.url == "https://example.com"
        assert ref.accessed_date == accessed_date
        assert ref.year == 2023
        assert ref.abstract == "This is a test website"
        assert ref.keywords == {"test", "website"}
    
    def test_create_generic_reference(self):
        # Test creating a generic reference
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_generic_reference(
            type=ReferenceType.CONFERENCE_PAPER,
            title="Test Conference Paper",
            authors=[author],
            year=2022,
            conference_name="Test Conference",
            conference_location="Test Location",
            abstract="This is a test conference paper",
            keywords={"test", "conference"},
        )
        
        ref = self.service.get_reference(ref_id)
        
        assert ref is not None
        assert ref.type == ReferenceType.CONFERENCE_PAPER
        assert ref.title == "Test Conference Paper"
        assert len(ref.authors) == 1
        assert ref.year == 2022
        assert ref.conference_name == "Test Conference"
        assert ref.conference_location == "Test Location"
        assert ref.abstract == "This is a test conference paper"
        assert ref.keywords == {"test", "conference"}
    
    def test_update_reference(self):
        # Test updating a reference
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_book(
            title="Original Title",
            authors=[author],
            publisher="Original Publisher",
            year=2020,
        )
        
        ref = self.service.get_reference(ref_id)
        
        # Update fields
        ref.title = "Updated Title"
        ref.publisher = "Updated Publisher"
        ref.year = 2021
        
        update_result = self.service.update_reference(ref)
        
        updated_ref = self.service.get_reference(ref_id)
        
        assert update_result is True
        assert updated_ref.title == "Updated Title"
        assert updated_ref.publisher == "Updated Publisher"
        assert updated_ref.year == 2021
    
    def test_update_nonexistent_reference(self):
        # Test updating a nonexistent reference
        ref = Reference(
            id=uuid4(),
            type=ReferenceType.BOOK,
            title="Nonexistent Reference",
            authors=[],
        )
        
        with pytest.raises(ValueError, match="Reference .* does not exist"):
            self.service.update_reference(ref)
    
    def test_delete_reference(self):
        # Test deleting a reference
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_book(
            title="Book to Delete",
            authors=[author],
            publisher="Test Publisher",
        )
        
        # Verify reference exists
        assert self.service.get_reference(ref_id) is not None
        
        # Delete reference
        delete_result = self.service.delete_reference(ref_id)
        
        assert delete_result is True
        assert self.service.get_reference(ref_id) is None
    
    def test_search_references(self):
        # Test searching for references
        
        # Create some references to search
        author1 = self.service.create_person_author("John", "Smith")
        author2 = self.service.create_person_author("Jane", "Doe")
        
        self.service.create_journal_article(
            title="Climate Change Effects",
            authors=[author1],
            journal_name="Environmental Science",
            year=2022,
            keywords={"climate", "environment"},
        )
        
        self.service.create_book(
            title="Data Analysis Methods",
            authors=[author2],
            publisher="Academic Press",
            year=2021,
            keywords={"data", "analysis"},
        )
        
        self.service.create_journal_article(
            title="Advanced Climate Models",
            authors=[author1, author2],
            journal_name="Climate Research",
            year=2022,
            keywords={"climate", "modeling"},
        )
        
        # Search by author name
        smith_refs = self.service.search_references(author_name="Smith")
        assert len(smith_refs) == 2
        assert {ref.title for ref in smith_refs} == {"Climate Change Effects", "Advanced Climate Models"}
        
        doe_refs = self.service.search_references(author_name="Doe")
        assert len(doe_refs) == 2
        assert {ref.title for ref in doe_refs} == {"Data Analysis Methods", "Advanced Climate Models"}
        
        # Search by keywords
        climate_refs = self.service.search_references(keywords={"climate"})
        assert len(climate_refs) == 2
        assert {ref.title for ref in climate_refs} == {"Climate Change Effects", "Advanced Climate Models"}
        
        analysis_refs = self.service.search_references(keywords={"data", "analysis"})
        assert len(analysis_refs) == 1
        assert analysis_refs[0].title == "Data Analysis Methods"
        
        # Search by year
        refs_2022 = self.service.search_references(year=2022)
        assert len(refs_2022) == 2
        assert {ref.title for ref in refs_2022} == {"Climate Change Effects", "Advanced Climate Models"}
        
        refs_2021 = self.service.search_references(year=2021)
        assert len(refs_2021) == 1
        assert refs_2021[0].title == "Data Analysis Methods"
        
        # Combine filters
        smith_climate_refs = self.service.search_references(
            author_name="Smith", keywords={"climate"}
        )
        assert len(smith_climate_refs) == 2
        assert {ref.title for ref in smith_climate_refs} == {"Climate Change Effects", "Advanced Climate Models"}
    
    def test_reference_modification_methods(self):
        # Test methods for modifying reference attributes
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_journal_article(
            title="Test Article",
            authors=[author],
            journal_name="Test Journal",
            year=2022,
        )
        
        # Add new author
        new_author = self.service.create_person_author("Jane", "Doe")
        self.service.add_author_to_reference(ref_id, new_author)
        
        # Add keyword
        self.service.add_keyword_to_reference(ref_id, "test")
        self.service.add_keyword_to_reference(ref_id, "research")
        
        # Add note
        self.service.add_note_to_reference(ref_id, "This is an important article")
        
        # Check modifications
        ref = self.service.get_reference(ref_id)
        
        assert len(ref.authors) == 2
        assert ref.authors[1].last_name == "Doe"
        assert ref.keywords == {"test", "research"}
        assert len(ref.notes) == 1
        assert ref.notes[0] == "This is an important article"
        
        # Remove keyword
        self.service.remove_keyword_from_reference(ref_id, "test")
        
        ref = self.service.get_reference(ref_id)
        assert ref.keywords == {"research"}
    
    def test_link_task_to_reference(self):
        # Test linking tasks and references
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_journal_article(
            title="Test Article",
            authors=[author],
            journal_name="Test Journal",
            year=2022,
        )
        
        # Create a link
        link_id = self.service.link_task_to_reference(
            task_id=self.task_id1,
            reference_id=ref_id,
            relevance="This article provides the methodology for the task",
        )
        
        # Get the link
        link = self.service.get_task_reference_link(link_id)
        
        assert link is not None
        assert link.task_id == self.task_id1
        assert link.reference_id == ref_id
        assert link.relevance == "This article provides the methodology for the task"
    
    def test_link_to_nonexistent_reference(self):
        # Test linking to a nonexistent reference
        with pytest.raises(ValueError, match="Reference .* does not exist"):
            self.service.link_task_to_reference(
                task_id=self.task_id1,
                reference_id=uuid4(),
            )
    
    def test_update_task_reference_link(self):
        # Test updating a task-reference link
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_journal_article(
            title="Test Article",
            authors=[author],
            journal_name="Test Journal",
        )
        
        # Create a link
        link_id = self.service.link_task_to_reference(
            task_id=self.task_id1,
            reference_id=ref_id,
            relevance="Original relevance",
        )
        
        # Update the link
        update_result = self.service.update_task_reference_link(
            link_id=link_id,
            relevance="Updated relevance",
        )
        
        link = self.service.get_task_reference_link(link_id)
        
        assert update_result is True
        assert link.relevance == "Updated relevance"
    
    def test_add_note_to_link(self):
        # Test adding a note to a task-reference link
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_journal_article(
            title="Test Article",
            authors=[author],
            journal_name="Test Journal",
        )
        
        # Create a link
        link_id = self.service.link_task_to_reference(
            task_id=self.task_id1,
            reference_id=ref_id,
        )
        
        # Add a note
        self.service.add_note_to_link(link_id, "Important connection between task and reference")
        
        link = self.service.get_task_reference_link(link_id)
        
        assert len(link.notes) == 1
        assert link.notes[0] == "Important connection between task and reference"
    
    def test_get_references_by_task(self):
        # Test getting references associated with a task
        author1 = self.service.create_person_author("John", "Smith")
        author2 = self.service.create_person_author("Jane", "Doe")
        
        ref_id1 = self.service.create_journal_article(
            title="First Article",
            authors=[author1],
            journal_name="Journal One",
        )
        
        ref_id2 = self.service.create_book(
            title="First Book",
            authors=[author2],
            publisher="Publisher One",
        )
        
        # Link both references to task1
        self.service.link_task_to_reference(self.task_id1, ref_id1)
        self.service.link_task_to_reference(self.task_id1, ref_id2)
        
        # Link only the first reference to task2
        self.service.link_task_to_reference(self.task_id2, ref_id1)
        
        # Get references for task1
        task1_refs = self.service.get_references_by_task(self.task_id1)
        
        assert len(task1_refs) == 2
        assert {ref.title for ref in task1_refs} == {"First Article", "First Book"}
        
        # Get references for task2
        task2_refs = self.service.get_references_by_task(self.task_id2)
        
        assert len(task2_refs) == 1
        assert task2_refs[0].title == "First Article"
    
    def test_get_tasks_by_reference(self):
        # Test getting tasks associated with a reference
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_journal_article(
            title="Test Article",
            authors=[author],
            journal_name="Test Journal",
        )
        
        # Link reference to both tasks
        self.service.link_task_to_reference(self.task_id1, ref_id)
        self.service.link_task_to_reference(self.task_id2, ref_id)
        
        # Get tasks for the reference
        tasks = self.service.get_tasks_by_reference(ref_id)
        
        assert len(tasks) == 2
        assert set(tasks) == {self.task_id1, self.task_id2}
    
    def test_delete_task_reference_link(self):
        # Test deleting a task-reference link
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_journal_article(
            title="Test Article",
            authors=[author],
            journal_name="Test Journal",
        )
        
        # Create a link
        link_id = self.service.link_task_to_reference(self.task_id1, ref_id)
        
        # Verify link exists
        assert self.service.get_task_reference_link(link_id) is not None
        
        # Delete link
        delete_result = self.service.delete_task_reference_link(link_id)
        
        assert delete_result is True
        assert self.service.get_task_reference_link(link_id) is None
    
    def test_citation_formatting(self):
        # Test citation formatting through the service
        author1 = self.service.create_person_author("John", "Smith")
        author2 = self.service.create_person_author("Jane", "Doe")
        
        ref_id = self.service.create_journal_article(
            title="Test Article for Citation",
            authors=[author1, author2],
            journal_name="Test Journal",
            year=2022,
            volume="10",
            issue="2",
            pages="123-145",
        )
        
        # Format citation in different styles
        apa_citation = self.service.format_citation(ref_id, CitationStyle.APA)
        mla_citation = self.service.format_citation(ref_id, CitationStyle.MLA)
        chicago_citation = self.service.format_citation(ref_id, CitationStyle.CHICAGO)
        
        # Check that all styles contain the core information
        assert "Smith" in apa_citation and "Doe" in apa_citation
        assert "2022" in apa_citation
        assert "Test Article for Citation" in apa_citation
        assert "Test Journal" in apa_citation
        
        assert "Smith" in mla_citation and "Doe" in mla_citation
        assert "Test Article for Citation" in mla_citation
        assert "Test Journal" in mla_citation
        
        assert "Smith" in chicago_citation and "Doe" in chicago_citation
        assert "Test Article for Citation" in chicago_citation
        assert "Test Journal" in chicago_citation
    
    def test_in_text_citation_formatting(self):
        # Test in-text citation formatting
        author = self.service.create_person_author("John", "Smith")
        
        ref_id = self.service.create_book(
            title="Test Book for Citation",
            authors=[author],
            publisher="Test Publisher",
            year=2021,
        )
        
        # Format in-text citations in different styles
        apa_in_text = self.service.format_in_text_citation(ref_id, CitationStyle.APA)
        mla_in_text = self.service.format_in_text_citation(ref_id, CitationStyle.MLA)
        harvard_in_text = self.service.format_in_text_citation(ref_id, CitationStyle.HARVARD)
        
        assert "Smith" in apa_in_text
        assert "2021" in apa_in_text
        
        assert "Smith" in mla_in_text
        
        assert "Smith" in harvard_in_text
        assert "2021" in harvard_in_text
    
    def test_generate_task_bibliography(self):
        # Test generating a bibliography for a task
        author1 = self.service.create_person_author("Alice", "Johnson")
        author2 = self.service.create_person_author("Bob", "Williams")
        author3 = self.service.create_person_author("Carol", "Davis")
        
        # Create three references
        ref_id1 = self.service.create_journal_article(
            title="First Test Article",
            authors=[author1],
            journal_name="Journal One",
            year=2022,
        )
        
        ref_id2 = self.service.create_book(
            title="Test Book",
            authors=[author2],
            publisher="Publisher One",
            year=2020,
        )
        
        ref_id3 = self.service.create_journal_article(
            title="Second Test Article",
            authors=[author3],
            journal_name="Journal Two",
            year=2021,
        )
        
        # Link all references to task1
        self.service.link_task_to_reference(self.task_id1, ref_id1)
        self.service.link_task_to_reference(self.task_id1, ref_id2)
        self.service.link_task_to_reference(self.task_id1, ref_id3)
        
        # Generate bibliography
        bibliography = self.service.generate_task_bibliography(self.task_id1, CitationStyle.APA)
        
        # Check that all references are included
        assert "Johnson" in bibliography
        assert "Williams" in bibliography
        assert "Davis" in bibliography
        assert "First Test Article" in bibliography
        assert "Test Book" in bibliography
        assert "Second Test Article" in bibliography
        
        # Check alphabetical order (by author last name)
        assert bibliography.index("Davis") < bibliography.index("Johnson")
        assert bibliography.index("Johnson") < bibliography.index("Williams")
        
        # Generate bibliography for a task with no references
        empty_bibliography = self.service.generate_task_bibliography(uuid4(), CitationStyle.APA)
        assert empty_bibliography == ""