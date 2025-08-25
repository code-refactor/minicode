from uuid import uuid4

import pytest

from researchtrack.bibliography.models import (
    Author,
    AuthorType,
    Reference,
    ReferenceType,
    TaskReferenceLink,
)
from researchtrack.bibliography.storage import InMemoryBibliographyStorage


class TestInMemoryBibliographyStorage:
    def setup_method(self):
        """Set up a fresh storage instance for each test."""
        self.storage = InMemoryBibliographyStorage()
        
        # Create some test data to use in multiple tests
        self.author1 = Author(
            type=AuthorType.PERSON,
            first_name="John",
            last_name="Smith",
        )
        
        self.author2 = Author(
            type=AuthorType.PERSON,
            first_name="Jane",
            last_name="Doe",
        )
        
        self.reference1 = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="First Test Article",
            authors=[self.author1],
            year=2022,
            journal_name="Test Journal",
            keywords={"test", "article", "science"},
        )
        
        self.reference2 = Reference(
            type=ReferenceType.BOOK,
            title="Test Book",
            authors=[self.author2],
            year=2021,
            publisher="Test Publisher",
            keywords={"test", "book"},
        )
        
        self.task_id1 = uuid4()
        self.task_id2 = uuid4()
    
    def test_create_and_get_reference(self):
        # Test creating and retrieving a reference
        ref_id = self.storage.create_reference(self.reference1)
        
        retrieved_ref = self.storage.get_reference(ref_id)
        
        assert retrieved_ref is not None
        assert retrieved_ref.id == ref_id
        assert retrieved_ref.title == "First Test Article"
        assert retrieved_ref.authors[0].first_name == "John"
    
    def test_update_reference(self):
        # Test updating a reference
        ref_id = self.storage.create_reference(self.reference1)
        
        # Update the reference
        self.reference1.title = "Updated Article Title"
        self.reference1.journal_name = "Updated Journal Name"
        
        update_result = self.storage.update_reference(self.reference1)
        retrieved_ref = self.storage.get_reference(ref_id)
        
        assert update_result is True
        assert retrieved_ref.title == "Updated Article Title"
        assert retrieved_ref.journal_name == "Updated Journal Name"
    
    def test_update_nonexistent_reference(self):
        # Test updating a reference that doesn't exist
        non_existent_ref = Reference(
            id=uuid4(),
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Non-existent Reference",
            authors=[],
        )
        
        update_result = self.storage.update_reference(non_existent_ref)
        assert update_result is False
    
    def test_delete_reference(self):
        # Test deleting a reference
        ref_id = self.storage.create_reference(self.reference1)
        
        # Create a link to this reference
        link = TaskReferenceLink(
            task_id=self.task_id1,
            reference_id=ref_id,
        )
        link_id = self.storage.create_task_reference_link(link)
        
        # Delete the reference
        delete_result = self.storage.delete_reference(ref_id)
        
        assert delete_result is True
        assert self.storage.get_reference(ref_id) is None
        
        # Verify that the link was also deleted
        assert self.storage.get_task_reference_link(link_id) is None
    
    def test_delete_nonexistent_reference(self):
        # Test deleting a reference that doesn't exist
        delete_result = self.storage.delete_reference(uuid4())
        assert delete_result is False
    
    def test_list_references_empty(self):
        # Test listing references when storage is empty
        references = self.storage.list_references()
        assert len(references) == 0
    
    def test_list_references_with_filters(self):
        # Test listing references with various filters
        self.storage.create_reference(self.reference1)
        self.storage.create_reference(self.reference2)
        
        # Filter by author name
        smith_refs = self.storage.list_references(author_name="Smith")
        assert len(smith_refs) == 1
        assert smith_refs[0].title == "First Test Article"
        
        doe_refs = self.storage.list_references(author_name="Doe")
        assert len(doe_refs) == 1
        assert doe_refs[0].title == "Test Book"
        
        # Partial name match
        j_refs = self.storage.list_references(author_name="J")
        assert len(j_refs) == 2  # Both authors have J in their names
        
        # Filter by year
        refs_2022 = self.storage.list_references(year=2022)
        assert len(refs_2022) == 1
        assert refs_2022[0].title == "First Test Article"
        
        refs_2021 = self.storage.list_references(year=2021)
        assert len(refs_2021) == 1
        assert refs_2021[0].title == "Test Book"
        
        # Filter by keywords
        science_refs = self.storage.list_references(keywords={"science"})
        assert len(science_refs) == 1
        assert science_refs[0].title == "First Test Article"
        
        test_refs = self.storage.list_references(keywords={"test"})
        assert len(test_refs) == 2  # Both have "test" keyword
        
        # Multiple keywords filter (must have all keywords)
        test_science_refs = self.storage.list_references(keywords={"test", "science"})
        assert len(test_science_refs) == 1
        assert test_science_refs[0].title == "First Test Article"
        
        # No matches
        no_refs = self.storage.list_references(keywords={"nonexistent"})
        assert len(no_refs) == 0
    
    def test_task_reference_link_operations(self):
        # Test task-reference link CRUD operations
        ref_id1 = self.storage.create_reference(self.reference1)
        ref_id2 = self.storage.create_reference(self.reference2)
        
        # Create links
        link1 = TaskReferenceLink(
            task_id=self.task_id1,
            reference_id=ref_id1,
            relevance="Test relevance 1",
        )
        
        link2 = TaskReferenceLink(
            task_id=self.task_id1,
            reference_id=ref_id2,
            relevance="Test relevance 2",
        )
        
        link3 = TaskReferenceLink(
            task_id=self.task_id2,
            reference_id=ref_id1,
            relevance="Test relevance 3",
        )
        
        link_id1 = self.storage.create_task_reference_link(link1)
        link_id2 = self.storage.create_task_reference_link(link2)
        link_id3 = self.storage.create_task_reference_link(link3)
        
        # Test get link
        retrieved_link = self.storage.get_task_reference_link(link_id1)
        assert retrieved_link is not None
        assert retrieved_link.task_id == self.task_id1
        assert retrieved_link.reference_id == ref_id1
        assert retrieved_link.relevance == "Test relevance 1"
        
        # Test update link
        link1.relevance = "Updated relevance"
        update_result = self.storage.update_task_reference_link(link1)
        updated_link = self.storage.get_task_reference_link(link_id1)
        
        assert update_result is True
        assert updated_link.relevance == "Updated relevance"
        
        # Test delete link
        delete_result = self.storage.delete_task_reference_link(link_id1)
        assert delete_result is True
        assert self.storage.get_task_reference_link(link_id1) is None
        
        # Test delete nonexistent link
        non_existent_delete = self.storage.delete_task_reference_link(uuid4())
        assert non_existent_delete is False
    
    def test_get_references_by_task(self):
        # Test getting references associated with a task
        ref_id1 = self.storage.create_reference(self.reference1)
        ref_id2 = self.storage.create_reference(self.reference2)
        
        # Create links
        link1 = TaskReferenceLink(
            task_id=self.task_id1,
            reference_id=ref_id1,
        )
        
        link2 = TaskReferenceLink(
            task_id=self.task_id1,
            reference_id=ref_id2,
        )
        
        link3 = TaskReferenceLink(
            task_id=self.task_id2,
            reference_id=ref_id1,
        )
        
        self.storage.create_task_reference_link(link1)
        self.storage.create_task_reference_link(link2)
        self.storage.create_task_reference_link(link3)
        
        # Get references for task1
        task1_refs = self.storage.get_references_by_task(self.task_id1)
        assert len(task1_refs) == 2
        assert {ref.title for ref in task1_refs} == {"First Test Article", "Test Book"}
        
        # Get references for task2
        task2_refs = self.storage.get_references_by_task(self.task_id2)
        assert len(task2_refs) == 1
        assert task2_refs[0].title == "First Test Article"
    
    def test_get_links_by_task(self):
        # Test getting links for a specific task
        ref_id1 = self.storage.create_reference(self.reference1)
        ref_id2 = self.storage.create_reference(self.reference2)
        
        # Create links
        link1 = TaskReferenceLink(
            task_id=self.task_id1,
            reference_id=ref_id1,
            relevance="Relevance 1",
        )
        
        link2 = TaskReferenceLink(
            task_id=self.task_id1,
            reference_id=ref_id2,
            relevance="Relevance 2",
        )
        
        self.storage.create_task_reference_link(link1)
        self.storage.create_task_reference_link(link2)
        
        # Get links for task1
        task1_links = self.storage.get_links_by_task(self.task_id1)
        assert len(task1_links) == 2
        assert {link.relevance for link in task1_links} == {"Relevance 1", "Relevance 2"}
        
        # Get links for task with no links
        no_links = self.storage.get_links_by_task(uuid4())
        assert len(no_links) == 0
    
    def test_get_tasks_by_reference(self):
        # Test getting tasks associated with a reference
        ref_id1 = self.storage.create_reference(self.reference1)
        
        # Create links to different tasks
        link1 = TaskReferenceLink(
            task_id=self.task_id1,
            reference_id=ref_id1,
        )
        
        link2 = TaskReferenceLink(
            task_id=self.task_id2,
            reference_id=ref_id1,
        )
        
        self.storage.create_task_reference_link(link1)
        self.storage.create_task_reference_link(link2)
        
        # Get tasks for reference1
        ref1_tasks = self.storage.get_tasks_by_reference(ref_id1)
        assert len(ref1_tasks) == 2
        assert set(ref1_tasks) == {self.task_id1, self.task_id2}
        
        # Get tasks for reference with no links
        no_tasks = self.storage.get_tasks_by_reference(uuid4())
        assert len(no_tasks) == 0