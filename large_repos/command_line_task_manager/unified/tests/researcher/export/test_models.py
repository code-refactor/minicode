import pytest
from datetime import datetime
from uuid import UUID

from researchtrack.export.models import (
    Document, Section, TextBlock, ImageBlock, TableBlock,
    CodeBlock, EquationBlock, CitationBlock, JournalFormat
)


def test_document_creation():
    """Test creating a document with basic attributes."""
    doc = Document(
        title="Research Methods",
        authors=["John Doe", "Jane Smith"],
        affiliations=["University A", "University B"],
        corresponding_email="john@example.com",
        keywords=["research", "methods", "academic"]
    )
    
    assert isinstance(doc.id, UUID)
    assert doc.title == "Research Methods"
    assert doc.authors == ["John Doe", "Jane Smith"]
    assert doc.affiliations == ["University A", "University B"]
    assert doc.corresponding_email == "john@example.com"
    assert doc.keywords == ["research", "methods", "academic"]
    assert isinstance(doc.created_at, datetime)
    assert isinstance(doc.updated_at, datetime)
    assert doc.format == JournalFormat.DEFAULT
    assert len(doc.sections) == 0


def test_section_creation():
    """Test creating a section with content blocks."""
    text_block = TextBlock(content="This is a sample text.")
    code_block = CodeBlock(code="print('Hello, world!')", language="python")
    
    section = Section(
        title="Introduction",
        content_blocks=[text_block, code_block]
    )
    
    assert isinstance(section.id, UUID)
    assert section.title == "Introduction"
    assert len(section.content_blocks) == 2
    assert isinstance(section.content_blocks[0], TextBlock)
    assert isinstance(section.content_blocks[1], CodeBlock)


def test_text_block():
    """Test creating and validating a text block."""
    block = TextBlock(content="This is a sample text.")
    
    assert isinstance(block.id, UUID)
    assert block.content == "This is a sample text."
    assert block.type == "text"


def test_image_block():
    """Test creating and validating an image block."""
    block = ImageBlock(
        path="/path/to/image.png",
        caption="Sample image caption",
        width=800
    )
    
    assert isinstance(block.id, UUID)
    assert block.path == "/path/to/image.png"
    assert block.caption == "Sample image caption"
    assert block.width == 800
    assert block.type == "image"


def test_table_block():
    """Test creating and validating a table block."""
    headers = ["Name", "Age", "Occupation"]
    data = [
        ["John", "30", "Researcher"],
        ["Jane", "28", "Professor"]
    ]
    block = TableBlock(
        data=data,
        headers=headers,
        caption="Sample table caption"
    )
    
    assert isinstance(block.id, UUID)
    assert block.headers == headers
    assert block.data == data
    assert block.caption == "Sample table caption"
    assert block.type == "table"


def test_code_block():
    """Test creating and validating a code block."""
    code = """
def hello():
    print('Hello, world!')
"""
    block = CodeBlock(code=code, language="python")
    
    assert isinstance(block.id, UUID)
    assert block.code == code
    assert block.language == "python"
    assert block.type == "code"


def test_equation_block():
    """Test creating and validating an equation block."""
    equation = "E = mc^2"
    block = EquationBlock(equation=equation)
    
    assert isinstance(block.id, UUID)
    assert block.equation == equation
    assert block.type == "equation"


def test_citation_block():
    """Test creating and validating a citation block."""
    reference_ids = ["ref1", "ref2"]
    context = "as seen in previous studies"
    block = CitationBlock(reference_ids=reference_ids, context=context)
    
    assert isinstance(block.id, UUID)
    assert block.reference_ids == reference_ids
    assert block.context == context
    assert block.type == "citation"


def test_document_with_sections_and_blocks():
    """Test creating a complete document with sections and blocks."""
    # Create content blocks
    intro_text = TextBlock(content="This paper describes our research methods.")
    equation = EquationBlock(equation="F = ma")
    citation = CitationBlock(reference_ids=["smith2020"], context="as demonstrated by")
    
    # Create sections
    intro_section = Section(
        title="Introduction",
        content_blocks=[intro_text, citation]
    )
    methods_section = Section(
        title="Methods",
        content_blocks=[
            TextBlock(content="We used the following equation:"),
            equation
        ]
    )
    
    # Create document
    doc = Document(
        title="Research Paper",
        authors=["John Doe"],
        sections=[intro_section, methods_section]
    )
    
    # Assertions
    assert len(doc.sections) == 2
    assert doc.sections[0].title == "Introduction"
    assert len(doc.sections[0].content_blocks) == 2
    assert doc.sections[1].title == "Methods"
    assert len(doc.sections[1].content_blocks) == 2
    assert isinstance(doc.sections[1].content_blocks[1], EquationBlock)