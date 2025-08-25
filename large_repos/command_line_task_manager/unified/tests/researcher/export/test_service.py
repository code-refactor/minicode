import pytest
import os
from uuid import UUID
import tempfile

from researchtrack.export.models import (
    Document, Section, TextBlock, ImageBlock, JournalFormat
)
from researchtrack.export.storage import InMemoryExportStorage
from researchtrack.export.service import ExportService


@pytest.fixture
def storage():
    return InMemoryExportStorage()


@pytest.fixture
def service(storage):
    return ExportService(storage)


def test_create_document(service):
    """Test creating a document through the service."""
    document = service.create_document(
        title="Test Document",
        authors=["Test Author"],
        affiliations=["Test University"],
        corresponding_email="test@example.com",
        keywords=["test", "research"]
    )
    
    assert isinstance(document.id, UUID)
    assert document.title == "Test Document"
    assert document.authors == ["Test Author"]
    assert document.affiliations == ["Test University"]
    assert document.corresponding_email == "test@example.com"
    assert document.keywords == ["test", "research"]
    assert document.format == JournalFormat.DEFAULT
    assert len(document.sections) == 0


def test_get_document(service):
    """Test retrieving a document through the service."""
    document = service.create_document(title="Test Document")
    retrieved = service.get_document(document.id)
    
    assert retrieved is not None
    assert retrieved.id == document.id
    assert retrieved.title == "Test Document"


def test_update_document(service):
    """Test updating a document through the service."""
    document = service.create_document(title="Original Title")
    document.title = "Updated Title"
    updated = service.update_document(document)
    
    assert updated.title == "Updated Title"
    
    # Verify the update is persisted
    retrieved = service.get_document(document.id)
    assert retrieved.title == "Updated Title"


def test_delete_document(service):
    """Test deleting a document through the service."""
    document = service.create_document(title="Test Document")
    result = service.delete_document(document.id)
    
    assert result is True
    assert service.get_document(document.id) is None


def test_add_section(service):
    """Test adding a section to a document."""
    document = service.create_document(title="Test Document")
    section = service.add_section(document.id, "Test Section")
    
    assert section is not None
    assert section.title == "Test Section"
    
    # Verify the section was added to the document
    updated_doc = service.get_document(document.id)
    assert len(updated_doc.sections) == 1
    assert updated_doc.sections[0].title == "Test Section"


def test_add_section_with_order(service):
    """Test adding a section with a specific order."""
    document = service.create_document(title="Test Document")
    section1 = service.add_section(document.id, "First Section")
    section2 = service.add_section(document.id, "Third Section")
    
    # Add a section between the existing ones
    section3 = service.add_section(document.id, "Second Section", order=1)
    
    # Verify the sections are in the correct order
    updated_doc = service.get_document(document.id)
    assert len(updated_doc.sections) == 3
    assert updated_doc.sections[0].title == "First Section"
    assert updated_doc.sections[1].title == "Second Section"
    assert updated_doc.sections[2].title == "Third Section"


def test_add_content_block(service):
    """Test adding a content block to a section."""
    document = service.create_document(title="Test Document")
    section = service.add_section(document.id, "Test Section")
    
    text_block = service.create_text_block("This is a test paragraph.")
    added_block = service.add_content_block(document.id, 0, text_block)
    
    assert added_block is not None
    assert added_block.content == "This is a test paragraph."
    
    # Verify the block was added to the section
    updated_doc = service.get_document(document.id)
    assert len(updated_doc.sections[0].content_blocks) == 1
    assert updated_doc.sections[0].content_blocks[0].content == "This is a test paragraph."


def test_create_content_blocks(service):
    """Test creating various content blocks."""
    text_block = service.create_text_block("Test text")
    assert text_block.content == "Test text"
    
    image_block = service.create_image_block(
        path="/path/to/image.png",
        caption="Test caption",
        width=800
    )
    assert image_block.path == "/path/to/image.png"
    assert image_block.caption == "Test caption"
    assert image_block.width == 800
    
    table_block = service.create_table_block(
        data=[["A", "1"], ["B", "2"]],
        headers=["Name", "Value"],
        caption="Test table"
    )
    assert table_block.headers == ["Name", "Value"]
    assert table_block.data == [["A", "1"], ["B", "2"]]
    assert table_block.caption == "Test table"
    
    code_block = service.create_code_block(
        code="print('Hello')",
        language="python"
    )
    assert code_block.code == "print('Hello')"
    assert code_block.language == "python"
    
    equation_block = service.create_equation_block("E = mc^2")
    assert equation_block.equation == "E = mc^2"
    
    citation_block = service.create_citation_block(
        reference_ids=["smith2020"],
        context="as seen in"
    )
    assert citation_block.reference_ids == ["smith2020"]
    assert citation_block.context == "as seen in"


def test_generate_markdown(service):
    """Test generating markdown for a document."""
    document = service.create_document(
        title="Test Document",
        authors=["Test Author"],
        format=JournalFormat.DEFAULT
    )
    
    section = service.add_section(document.id, "Test Section")
    text_block = service.create_text_block("This is a test paragraph.")
    service.add_content_block(document.id, 0, text_block)
    
    markdown = service.generate_markdown(document.id)
    
    assert "# Test Document" in markdown
    assert "Test Author" in markdown
    assert "## Test Section" in markdown
    assert "This is a test paragraph." in markdown


def test_export_to_file(service):
    """Test exporting a document to a file."""
    document = service.create_document(
        title="Test Document",
        authors=["Test Author"]
    )
    
    section = service.add_section(document.id, "Test Section")
    text_block = service.create_text_block("This is a test paragraph.")
    service.add_content_block(document.id, 0, text_block)
    
    # Use a temporary file for testing
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        result = service.export_to_file(document.id, temp_path)
        assert result is True
        
        # Verify the file contents
        with open(temp_path, "r") as f:
            content = f.read()
            assert "# Test Document" in content
            assert "Test Author" in content
            assert "## Test Section" in content
            assert "This is a test paragraph." in content
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)