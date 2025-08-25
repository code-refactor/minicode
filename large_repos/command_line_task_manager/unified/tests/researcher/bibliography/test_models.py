from datetime import datetime
from uuid import UUID

import pytest

from researchtrack.bibliography.models import (
    Author,
    AuthorType,
    Reference,
    ReferenceType,
    TaskReferenceLink,
)


class TestAuthor:
    def test_create_person_author(self):
        # Test basic creation of a person author
        author = Author(
            type=AuthorType.PERSON,
            first_name="Jane",
            last_name="Smith",
            orcid_id="0000-0002-1234-5678",
        )
        
        assert isinstance(author.id, UUID)
        assert author.type == AuthorType.PERSON
        assert author.first_name == "Jane"
        assert author.last_name == "Smith"
        assert author.orcid_id == "0000-0002-1234-5678"
        assert author.organization_name is None
    
    def test_create_organization_author(self):
        # Test basic creation of an organization author
        author = Author(
            type=AuthorType.ORGANIZATION,
            organization_name="National Oceanic and Atmospheric Administration",
        )
        
        assert isinstance(author.id, UUID)
        assert author.type == AuthorType.ORGANIZATION
        assert author.organization_name == "National Oceanic and Atmospheric Administration"
        assert author.first_name is None
        assert author.last_name is None
        assert author.orcid_id is None
    
    def test_author_full_name_person(self):
        # Test full_name() method for person author
        author = Author(
            type=AuthorType.PERSON,
            first_name="Jane",
            last_name="Smith",
        )
        
        assert author.full_name() == "Smith, Jane"
        
        # Test with only last name
        author = Author(
            type=AuthorType.PERSON,
            last_name="Smith",
        )
        
        assert author.full_name() == "Smith"
        
        # Test with only first name
        author = Author(
            type=AuthorType.PERSON,
            first_name="Jane",
        )
        
        assert author.full_name() == "Jane"
        
        # Test with no name
        author = Author(type=AuthorType.PERSON)
        
        assert author.full_name() == "Unknown Author"
    
    def test_author_full_name_organization(self):
        # Test full_name() method for organization author
        author = Author(
            type=AuthorType.ORGANIZATION,
            organization_name="National Science Foundation",
        )
        
        assert author.full_name() == "National Science Foundation"
        
        # Test with no organization name
        author = Author(type=AuthorType.ORGANIZATION)
        
        assert author.full_name() == "Unknown Organization"


class TestReference:
    def test_create_journal_article(self):
        # Test creating a journal article reference
        author1 = Author(
            type=AuthorType.PERSON,
            first_name="John",
            last_name="Doe",
        )
        author2 = Author(
            type=AuthorType.PERSON,
            first_name="Jane",
            last_name="Smith",
        )
        
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Climate Change Impacts on Coastal Ecosystems",
            authors=[author1, author2],
            year=2022,
            journal_name="Journal of Environmental Science",
            volume="45",
            issue="3",
            pages="123-145",
            doi="10.1234/jes.2022.12345",
            abstract="This study examines the impacts of climate change on coastal ecosystems...",
            keywords={"climate change", "coastal", "ecosystems"},
        )
        
        assert isinstance(reference.id, UUID)
        assert reference.type == ReferenceType.JOURNAL_ARTICLE
        assert reference.title == "Climate Change Impacts on Coastal Ecosystems"
        assert len(reference.authors) == 2
        assert reference.authors[0].first_name == "John"
        assert reference.authors[1].first_name == "Jane"
        assert reference.year == 2022
        assert reference.journal_name == "Journal of Environmental Science"
        assert reference.volume == "45"
        assert reference.issue == "3"
        assert reference.pages == "123-145"
        assert reference.doi == "10.1234/jes.2022.12345"
        assert reference.abstract == "This study examines the impacts of climate change on coastal ecosystems..."
        assert reference.keywords == {"climate change", "coastal", "ecosystems"}
        assert len(reference.notes) == 0
        assert isinstance(reference.created_at, datetime)
        assert isinstance(reference.updated_at, datetime)
    
    def test_create_book(self):
        # Test creating a book reference
        author = Author(
            type=AuthorType.PERSON,
            first_name="Robert",
            last_name="Johnson",
        )
        
        reference = Reference(
            type=ReferenceType.BOOK,
            title="Advanced Data Analysis Techniques",
            authors=[author],
            year=2019,
            publisher="Academic Press",
            isbn="978-1234567890",
            edition="2nd",
        )
        
        assert reference.type == ReferenceType.BOOK
        assert reference.title == "Advanced Data Analysis Techniques"
        assert len(reference.authors) == 1
        assert reference.authors[0].last_name == "Johnson"
        assert reference.year == 2019
        assert reference.publisher == "Academic Press"
        assert reference.isbn == "978-1234567890"
        assert reference.edition == "2nd"
    
    def test_create_website(self):
        # Test creating a website reference
        author = Author(
            type=AuthorType.ORGANIZATION,
            organization_name="National Oceanic and Atmospheric Administration",
        )
        
        accessed_date = datetime.now()
        
        reference = Reference(
            type=ReferenceType.WEBSITE,
            title="Climate Data Online",
            authors=[author],
            url="https://www.ncdc.noaa.gov/cdo-web/",
            accessed_date=accessed_date,
            year=2023,
        )
        
        assert reference.type == ReferenceType.WEBSITE
        assert reference.title == "Climate Data Online"
        assert len(reference.authors) == 1
        assert reference.authors[0].organization_name == "National Oceanic and Atmospheric Administration"
        assert reference.url == "https://www.ncdc.noaa.gov/cdo-web/"
        assert reference.accessed_date == accessed_date
        assert reference.year == 2023
    
    def test_update_reference(self):
        # Test updating reference fields
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Original Title",
            authors=[],
            journal_name="Original Journal",
        )
        
        original_updated_at = reference.updated_at
        
        # Update fields
        reference.update(
            title="Updated Title",
            journal_name="Updated Journal",
            volume="10",
            issue="2",
        )
        
        assert reference.title == "Updated Title"
        assert reference.journal_name == "Updated Journal"
        assert reference.volume == "10"
        assert reference.issue == "2"
        assert reference.updated_at > original_updated_at
    
    def test_add_author(self):
        # Test adding an author
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Multi-author Paper",
            authors=[],
        )
        
        author1 = Author(
            type=AuthorType.PERSON,
            first_name="First",
            last_name="Author",
        )
        
        author2 = Author(
            type=AuthorType.PERSON,
            first_name="Second",
            last_name="Author",
        )
        
        original_updated_at = reference.updated_at
        
        reference.add_author(author1)
        reference.add_author(author2)
        
        assert len(reference.authors) == 2
        assert reference.authors[0].first_name == "First"
        assert reference.authors[1].first_name == "Second"
        assert reference.updated_at > original_updated_at
    
    def test_remove_author(self):
        # Test removing an author
        author1 = Author(
            type=AuthorType.PERSON,
            first_name="First",
            last_name="Author",
        )
        
        author2 = Author(
            type=AuthorType.PERSON,
            first_name="Second",
            last_name="Author",
        )
        
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Multi-author Paper",
            authors=[author1, author2],
        )
        
        original_updated_at = reference.updated_at
        
        # Remove existing author
        result = reference.remove_author(author1.id)
        
        assert result is True
        assert len(reference.authors) == 1
        assert reference.authors[0].first_name == "Second"
        assert reference.updated_at > original_updated_at
        
        # Try to remove non-existent author
        non_existent_result = reference.remove_author(author1.id)
        
        assert non_existent_result is False
    
    def test_keywords(self):
        # Test adding and removing keywords
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Paper with Keywords",
            authors=[],
        )
        
        original_updated_at = reference.updated_at
        
        reference.add_keyword("climate")
        reference.add_keyword("modeling")
        reference.add_keyword("statistics")
        
        assert reference.keywords == {"climate", "modeling", "statistics"}
        assert reference.updated_at > original_updated_at
        
        # Adding duplicate keyword shouldn't change the set
        previous_updated_at = reference.updated_at
        reference.add_keyword("climate")
        assert reference.keywords == {"climate", "modeling", "statistics"}
        assert reference.updated_at > previous_updated_at
        
        # Remove keyword
        reference.remove_keyword("modeling")
        
        assert reference.keywords == {"climate", "statistics"}
        
        # Try to remove non-existent keyword
        previous_updated_at = reference.updated_at
        reference.remove_keyword("nonexistent")
        assert reference.updated_at == previous_updated_at
    
    def test_notes(self):
        # Test adding notes
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Paper with Notes",
            authors=[],
        )
        
        original_updated_at = reference.updated_at
        
        reference.add_note("First note about methodology")
        reference.add_note("Second note about results")
        
        assert len(reference.notes) == 2
        assert reference.notes[0] == "First note about methodology"
        assert reference.notes[1] == "Second note about results"
        assert reference.updated_at > original_updated_at
    
    def test_custom_fields(self):
        # Test custom fields
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Paper with Custom Fields",
            authors=[],
        )
        
        original_updated_at = reference.updated_at
        
        reference.update_custom_field("dataset_url", "https://example.com/data")
        reference.update_custom_field("funding_source", "NSF Grant #12345")
        
        assert reference.custom_fields["dataset_url"] == "https://example.com/data"
        assert reference.custom_fields["funding_source"] == "NSF Grant #12345"
        assert reference.updated_at > original_updated_at
        
        # Update existing field
        previous_updated_at = reference.updated_at
        reference.update_custom_field("dataset_url", "https://newexample.com/data")
        
        assert reference.custom_fields["dataset_url"] == "https://newexample.com/data"
        assert reference.updated_at > previous_updated_at
        
        # Remove field
        result = reference.remove_custom_field("funding_source")
        
        assert result is True
        assert "funding_source" not in reference.custom_fields
        
        # Try to remove non-existent field
        non_existent_result = reference.remove_custom_field("nonexistent")
        
        assert non_existent_result is False
    
    def test_author_names_formatted(self):
        # Test author_names_formatted method
        
        # Single author
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Single Author Paper",
            authors=[
                Author(first_name="John", last_name="Smith", type=AuthorType.PERSON)
            ],
        )
        
        assert reference.author_names_formatted() == "Smith, John"
        
        # Two authors
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Two Authors Paper",
            authors=[
                Author(first_name="John", last_name="Smith", type=AuthorType.PERSON),
                Author(first_name="Jane", last_name="Doe", type=AuthorType.PERSON),
            ],
        )
        
        assert reference.author_names_formatted() == "Smith, John and Doe, Jane"
        
        # Multiple authors
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Multi-author Paper",
            authors=[
                Author(first_name="John", last_name="Smith", type=AuthorType.PERSON),
                Author(first_name="Jane", last_name="Doe", type=AuthorType.PERSON),
                Author(first_name="Bob", last_name="Johnson", type=AuthorType.PERSON),
            ],
        )
        
        assert reference.author_names_formatted() == "Smith, John et al."
        
        # No authors
        reference = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="No Authors Paper",
            authors=[],
        )
        
        assert reference.author_names_formatted() == "Unknown Author"


class TestTaskReferenceLink:
    def test_create_task_reference_link(self):
        # Test basic creation of a task-reference link
        task_id = UUID('12345678-1234-5678-1234-567812345678')
        reference_id = UUID('87654321-8765-4321-8765-432187654321')
        
        link = TaskReferenceLink(
            task_id=task_id,
            reference_id=reference_id,
            relevance="This paper provides the methodology used in the analysis",
        )
        
        assert isinstance(link.id, UUID)
        assert link.task_id == task_id
        assert link.reference_id == reference_id
        assert link.relevance == "This paper provides the methodology used in the analysis"
        assert len(link.notes) == 0
        assert isinstance(link.created_at, datetime)
        assert isinstance(link.updated_at, datetime)
    
    def test_update_link(self):
        # Test updating link fields
        task_id = UUID('12345678-1234-5678-1234-567812345678')
        reference_id = UUID('87654321-8765-4321-8765-432187654321')
        
        link = TaskReferenceLink(
            task_id=task_id,
            reference_id=reference_id,
            relevance="Original relevance",
        )
        
        original_updated_at = link.updated_at
        
        link.update(relevance="Updated relevance description")
        
        assert link.relevance == "Updated relevance description"
        assert link.updated_at > original_updated_at
    
    def test_add_note(self):
        # Test adding notes to a link
        link = TaskReferenceLink(
            task_id=UUID('12345678-1234-5678-1234-567812345678'),
            reference_id=UUID('87654321-8765-4321-8765-432187654321'),
        )
        
        original_updated_at = link.updated_at
        
        link.add_note("First note about how this reference applies to the task")
        link.add_note("Second note with additional details")
        
        assert len(link.notes) == 2
        assert link.notes[0] == "First note about how this reference applies to the task"
        assert link.notes[1] == "Second note with additional details"
        assert link.updated_at > original_updated_at