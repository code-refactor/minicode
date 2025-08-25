"""Tests for the document models."""

import pytest
from datetime import datetime
from legal_discovery_interpreter.core.document import (
    DocumentMetadata,
    Document,
    EmailDocument,
    DocumentCollection
)


def test_document_metadata_creation():
    """Test creating document metadata."""
    metadata = DocumentMetadata(
        document_id="doc001",
        title="Test Document",
        document_type="contract",
        date_created=datetime(2020, 1, 1)
    )
    
    assert metadata.document_id == "doc001"
    assert metadata.title == "Test Document"
    assert metadata.document_type == "contract"
    assert metadata.date_created == datetime(2020, 1, 1)
    assert metadata.author is None  # Optional field


def test_document_creation():
    """Test creating a document."""
    metadata = DocumentMetadata(
        document_id="doc001",
        title="Test Document",
        document_type="contract",
        date_created=datetime(2020, 1, 1)
    )
    
    document = Document(
        metadata=metadata,
        content="This is a test document content."
    )
    
    assert document.metadata.document_id == "doc001"
    assert document.content == "This is a test document content."
    assert document.relevance_score is None  # Optional field


def test_document_get_content_preview():
    """Test getting a preview of document content."""
    metadata = DocumentMetadata(
        document_id="doc001",
        title="Test Document",
        document_type="contract",
        date_created=datetime(2020, 1, 1)
    )
    
    # Short content
    document = Document(
        metadata=metadata,
        content="This is a short content."
    )
    
    assert document.get_content_preview() == "This is a short content."
    
    # Long content
    long_content = "This is a very long content that exceeds the default maximum length for a preview. " * 10
    document = Document(
        metadata=metadata,
        content=long_content
    )
    
    preview = document.get_content_preview()
    assert len(preview) <= 200 + 3  # Max length plus ellipsis
    assert preview.endswith("...")


def test_email_document_creation():
    """Test creating an email document."""
    metadata = DocumentMetadata(
        document_id="email001",
        title="Test Email",
        document_type="email",
        date_created=datetime(2020, 1, 1)
    )
    
    email = EmailDocument(
        metadata=metadata,
        content="This is an email content.",
        sender="sender@example.com",
        recipients=["recipient1@example.com", "recipient2@example.com"],
        subject="Test Email Subject",
        sent_date=datetime(2020, 1, 1, 10, 30)
    )
    
    assert email.metadata.document_id == "email001"
    assert email.content == "This is an email content."
    assert email.sender == "sender@example.com"
    assert len(email.recipients) == 2
    assert email.recipients[0] == "recipient1@example.com"
    assert email.subject == "Test Email Subject"
    assert email.sent_date == datetime(2020, 1, 1, 10, 30)
    assert email.cc is None  # Optional field
    assert email.bcc is None  # Optional field


def test_document_collection():
    """Test document collection operations."""
    # Create some documents
    metadata1 = DocumentMetadata(
        document_id="doc001",
        title="Document 1",
        document_type="contract",
        date_created=datetime(2020, 1, 1)
    )
    
    document1 = Document(
        metadata=metadata1,
        content="This is document 1 content."
    )
    
    metadata2 = DocumentMetadata(
        document_id="doc002",
        title="Document 2",
        document_type="memo",
        date_created=datetime(2020, 1, 2)
    )
    
    document2 = Document(
        metadata=metadata2,
        content="This is document 2 content."
    )
    
    # Create a collection
    collection = DocumentCollection(
        collection_id="col001",
        name="Test Collection"
    )
    
    # Add documents
    collection.add_document(document1)
    collection.add_document(document2)
    
    # Check collection contents
    assert collection.collection_id == "col001"
    assert collection.name == "Test Collection"
    assert collection.count() == 2
    assert "doc001" in collection.documents
    assert "doc002" in collection.documents
    
    # Get a document
    doc = collection.get_document("doc001")
    assert doc.metadata.document_id == "doc001"
    assert doc.content == "This is document 1 content."
    
    # Remove a document
    collection.remove_document("doc001")
    assert collection.count() == 1
    assert "doc001" not in collection.documents
    assert "doc002" in collection.documents