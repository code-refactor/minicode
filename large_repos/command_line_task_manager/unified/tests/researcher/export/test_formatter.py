import pytest
import re

from researchtrack.export.models import (
    Document, Section, TextBlock, ImageBlock, TableBlock, 
    CodeBlock, EquationBlock, CitationBlock, JournalFormat
)
from researchtrack.export.formatter import ExportFormatter


@pytest.fixture
def formatter():
    """Create a formatter instance for testing."""
    return ExportFormatter()


@pytest.fixture
def sample_document():
    """Create a sample document with various content types."""
    return Document(
        title="Sample Research Paper",
        authors=["John Doe", "Jane Smith"],
        affiliations=["University A", "University B"],
        corresponding_email="john@example.com",
        keywords=["research", "methods", "academic"],
        sections=[
            Section(
                title="Introduction",
                content_blocks=[
                    TextBlock(content="This is the introduction."),
                    CitationBlock(reference_ids=["smith2020"], context="as seen in")
                ]
            ),
            Section(
                title="Methods",
                content_blocks=[
                    TextBlock(content="These are our methods."),
                    EquationBlock(equation="E = mc^2"),
                    CodeBlock(code="print('Hello')", language="python"),
                    ImageBlock(path="/path/to/image.png", caption="Sample image"),
                    TableBlock(
                        headers=["Name", "Value"],
                        data=[["A", "1"], ["B", "2"]],
                        caption="Sample table"
                    )
                ]
            )
        ]
    )


def test_format_document_default(formatter, sample_document):
    """Test formatting a document with default journal format."""
    markdown = formatter.format_document(sample_document)
    
    # Title should be an h1
    assert "# Sample Research Paper" in markdown
    
    # Authors should be included
    assert "John Doe" in markdown
    assert "Jane Smith" in markdown
    
    # Sections should be included
    assert "## Introduction" in markdown
    assert "## Methods" in markdown
    
    # Content blocks should be formatted
    assert "This is the introduction." in markdown
    assert "These are our methods." in markdown
    
    # Citations should be formatted
    assert "[smith2020]" in markdown
    
    # Equation should be formatted
    assert "E = mc^2" in markdown
    
    # Code block should be formatted with language
    assert "```python" in markdown
    assert "print('Hello')" in markdown
    
    # Image should be formatted
    assert "![Sample image](/path/to/image.png)" in markdown
    
    # Table should be formatted
    assert "| Name | Value |" in markdown
    assert "| A | 1 |" in markdown
    assert "| B | 2 |" in markdown


def test_format_document_nature(formatter, sample_document):
    """Test formatting a document with Nature journal format."""
    sample_document.format = JournalFormat.NATURE
    markdown = formatter.format_document(sample_document)
    
    # Nature format specifics
    assert "# Sample Research Paper" in markdown
    # Check for a specific Nature format feature like the abstract marker or author format
    assert re.search(r'Authors?: .*John Doe.*, .*Jane Smith', markdown, re.MULTILINE)


def test_format_document_science(formatter, sample_document):
    """Test formatting a document with Science journal format."""
    sample_document.format = JournalFormat.SCIENCE
    markdown = formatter.format_document(sample_document)
    
    # Science format specifics
    assert "# Sample Research Paper" in markdown


def test_format_document_plos(formatter, sample_document):
    """Test formatting a document with PLOS journal format."""
    sample_document.format = JournalFormat.PLOS
    markdown = formatter.format_document(sample_document)
    
    # PLOS format specifics
    assert "# Sample Research Paper" in markdown


def test_format_section(formatter):
    """Test formatting a section."""
    section = Section(
        title="Test Section",
        content_blocks=[
            TextBlock(content="Test content.")
        ]
    )
    
    markdown = formatter.format_section(section)
    
    assert "## Test Section" in markdown
    assert "Test content." in markdown


def test_format_text_block(formatter):
    """Test formatting a text block."""
    block = TextBlock(content="This is a paragraph with **bold** and *italic* text.")
    markdown = formatter.format_text_block(block)
    
    assert "This is a paragraph with **bold** and *italic* text." in markdown


def test_format_image_block(formatter):
    """Test formatting an image block."""
    block = ImageBlock(
        path="/path/to/image.png",
        caption="Sample image caption",
        width=800
    )
    markdown = formatter.format_image_block(block)
    
    assert "![Sample image caption](/path/to/image.png)" in markdown


def test_format_table_block(formatter):
    """Test formatting a table block."""
    block = TableBlock(
        headers=["Name", "Age", "Occupation"],
        data=[
            ["John", "30", "Researcher"],
            ["Jane", "28", "Professor"]
        ],
        caption="Sample table"
    )
    markdown = formatter.format_table_block(block)
    
    assert "| Name | Age | Occupation |" in markdown
    assert "| John | 30 | Researcher |" in markdown
    assert "| Jane | 28 | Professor |" in markdown
    assert "Table: Sample table" in markdown


def test_format_code_block(formatter):
    """Test formatting a code block."""
    code = """
def hello():
    print('Hello, world!')
"""
    block = CodeBlock(code=code, language="python")
    markdown = formatter.format_code_block(block)
    
    assert "```python" in markdown
    assert "def hello():" in markdown
    assert "print('Hello, world!')" in markdown
    assert "```" in markdown


def test_format_equation_block(formatter):
    """Test formatting an equation block."""
    block = EquationBlock(equation="E = mc^2")
    markdown = formatter.format_equation_block(block)
    
    assert "$E = mc^2$" in markdown


def test_format_citation_block(formatter):
    """Test formatting a citation block."""
    block = CitationBlock(
        reference_ids=["smith2020", "jones2021"],
        context="as demonstrated by"
    )
    markdown = formatter.format_citation_block(block)
    
    assert "as demonstrated by" in markdown
    assert "[smith2020]" in markdown
    assert "[jones2021]" in markdown