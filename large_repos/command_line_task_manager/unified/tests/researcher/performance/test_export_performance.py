"""
Performance tests for the Academic Markdown Export module.

These tests verify that the export functionality meets performance
requirements for document generation.
"""

import pytest
import time
import random
import string
from uuid import uuid4

from researchtrack.export import (
    ExportService, InMemoryExportStorage,
    Document, Section, TextBlock, TableBlock, ImageBlock, CodeBlock
)


@pytest.fixture
def export_service():
    """Create an export service for testing."""
    return ExportService(InMemoryExportStorage())


def random_string(length=10):
    """Generate a random string of fixed length."""
    return ''.join(random.choices(string.ascii_letters, k=length))


def create_large_document(service, num_sections=10, blocks_per_section=20):
    """Create a large document with many sections and blocks."""
    document = service.create_document(
        title=f"Large Test Document with {num_sections} sections",
        authors=[f"Author {i}" for i in range(5)],
        affiliations=[f"University {i}" for i in range(3)],
        corresponding_email="test@example.com",
        keywords=["test", "performance", "large document"]
    )
    
    # Create sections with many content blocks
    for i in range(num_sections):
        section = service.add_section(
            document_id=document.id,
            title=f"Section {i+1}: {random_string(20)}"
        )
        
        # Add mixed content blocks
        for j in range(blocks_per_section):
            block_type = j % 4  # Cycle through different block types
            
            if block_type == 0:
                # Text block with substantial text
                block = service.create_text_block(
                    content=f"This is paragraph {j+1} in section {i+1}. " + 
                           f"{random_string(200)} " * 3
                )
            elif block_type == 1:
                # Table block
                headers = [f"Column {k}" for k in range(5)]
                data = [
                    [f"Row {m}, Col {n}" for n in range(5)]
                    for m in range(5)
                ]
                block = service.create_table_block(
                    data=data,
                    headers=headers,
                    caption=f"Table {j+1} in Section {i+1}"
                )
            elif block_type == 2:
                # Image block
                block = service.create_image_block(
                    path=f"/path/to/image_{i}_{j}.png",
                    caption=f"Image {j+1} in Section {i+1}",
                    width=800
                )
            else:
                # Code block
                code = "\n".join([
                    f"def function_{i}_{j}():",
                    f"    # This is function {i}_{j}",
                    f"    print('Hello from function {i}_{j}')",
                    f"    return {i} * {j}"
                ])
                block = service.create_code_block(
                    code=code,
                    language="python"
                )
            
            service.add_content_block(document.id, i, block)
    
    return document


def test_document_creation_performance(export_service):
    """Test the performance of creating a document with many sections and blocks."""
    start_time = time.time()
    
    document = create_large_document(
        export_service, 
        num_sections=10, 
        blocks_per_section=20
    )
    
    end_time = time.time()
    creation_time = end_time - start_time
    
    # Document creation should be relatively fast
    assert creation_time < 1.0, f"Document creation took {creation_time:.2f}s, expected < 1.0s"
    
    # Verify document structure
    document = export_service.get_document(document.id)
    assert len(document.sections) == 10
    assert all(len(section.content_blocks) == 20 for section in document.sections)


def test_markdown_generation_performance(export_service):
    """Test the performance of generating markdown from a large document."""
    document = create_large_document(
        export_service,
        num_sections=10,
        blocks_per_section=20
    )
    
    start_time = time.time()
    
    markdown = export_service.generate_markdown(document.id)
    
    end_time = time.time()
    generation_time = end_time - start_time
    
    # Markdown generation should be efficient
    assert generation_time < 0.5, f"Markdown generation took {generation_time:.2f}s, expected < 0.5s"
    
    # Verify markdown content
    assert document.title in markdown
    for author in document.authors:
        assert author in markdown
    for i in range(10):
        assert f"Section {i+1}:" in markdown


def test_file_export_performance(export_service, tmp_path):
    """Test the performance of exporting a document to a file."""
    document = create_large_document(
        export_service,
        num_sections=10,
        blocks_per_section=20
    )
    
    file_path = tmp_path / "test_document.md"
    
    start_time = time.time()
    
    result = export_service.export_to_file(document.id, str(file_path))
    
    end_time = time.time()
    export_time = end_time - start_time
    
    # File export should be efficient
    assert export_time < 0.5, f"File export took {export_time:.2f}s, expected < 0.5s"
    
    # Verify export result
    assert result is True
    assert file_path.exists()
    
    # Check file content
    content = file_path.read_text()
    assert document.title in content
    for author in document.authors:
        assert author in content


def test_large_document_performance(export_service):
    """Test performance with a very large document."""
    start_time = time.time()
    
    document = create_large_document(
        export_service,
        num_sections=20,
        blocks_per_section=50
    )
    
    creation_time = time.time() - start_time
    
    start_time = time.time()
    markdown = export_service.generate_markdown(document.id)
    generation_time = time.time() - start_time
    
    # Log performance metrics
    print(f"Large document creation time: {creation_time:.2f}s")
    print(f"Large document markdown generation time: {generation_time:.2f}s")
    print(f"Total content blocks: {20 * 50}")
    
    # Very large document processing should still be reasonable
    assert creation_time < 2.0, f"Large document creation took {creation_time:.2f}s, expected < 2.0s"
    assert generation_time < 1.0, f"Large document markdown generation took {generation_time:.2f}s, expected < 1.0s"