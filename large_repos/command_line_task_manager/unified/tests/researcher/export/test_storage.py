import pytest
from uuid import UUID

from researchtrack.export.models import Document, Section, TextBlock
from researchtrack.export.storage import InMemoryExportStorage


@pytest.fixture
def storage():
    """Create a fresh in-memory storage for each test."""
    return InMemoryExportStorage()


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    return Document(
        title="Test Document",
        authors=["Test Author"],
        sections=[
            Section(
                title="Test Section",
                content_blocks=[
                    TextBlock(content="Test content")
                ]
            )
        ]
    )


def test_create_document(storage, sample_document):
    """Test creating a document in storage."""
    created = storage.create_document(sample_document)
    
    assert created.id == sample_document.id
    assert created.title == "Test Document"
    assert len(created.sections) == 1
    assert len(created.sections[0].content_blocks) == 1


def test_get_document(storage, sample_document):
    """Test retrieving a document from storage."""
    storage.create_document(sample_document)
    retrieved = storage.get_document(sample_document.id)
    
    assert retrieved is not None
    assert retrieved.id == sample_document.id
    assert retrieved.title == "Test Document"


def test_get_nonexistent_document(storage):
    """Test retrieving a document that doesn't exist."""
    from uuid import uuid4
    non_existent_id = uuid4()
    retrieved = storage.get_document(non_existent_id)
    
    assert retrieved is None


def test_update_document(storage, sample_document):
    """Test updating a document in storage."""
    created = storage.create_document(sample_document)
    created.title = "Updated Title"
    updated = storage.update_document(created)
    
    assert updated.title == "Updated Title"
    
    # Verify the update is persisted
    retrieved = storage.get_document(sample_document.id)
    assert retrieved.title == "Updated Title"


def test_update_nonexistent_document(storage):
    """Test updating a document that doesn't exist."""
    doc = Document(title="Nonexistent Document")
    updated = storage.update_document(doc)
    
    assert updated is None


def test_delete_document(storage, sample_document):
    """Test deleting a document from storage."""
    storage.create_document(sample_document)
    result = storage.delete_document(sample_document.id)
    
    assert result is True
    assert storage.get_document(sample_document.id) is None


def test_delete_nonexistent_document(storage):
    """Test deleting a document that doesn't exist."""
    from uuid import uuid4
    non_existent_id = uuid4()
    result = storage.delete_document(non_existent_id)
    
    assert result is False


def test_list_documents(storage, sample_document):
    """Test listing all documents in storage."""
    storage.create_document(sample_document)
    another_doc = Document(title="Another Document")
    storage.create_document(another_doc)
    
    documents = storage.list_documents()
    
    assert len(documents) == 2
    assert any(d.id == sample_document.id for d in documents)
    assert any(d.id == another_doc.id for d in documents)