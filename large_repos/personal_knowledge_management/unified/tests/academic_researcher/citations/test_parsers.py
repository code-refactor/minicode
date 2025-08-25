"""Tests for citation parsers."""

import os
import tempfile
from pathlib import Path

import pytest

from researchbrain.citations.parsers import (
    extract_doi_from_pdf, extract_pdf_metadata, parse_bibtex_file, parse_ris_file
)


class TestCitationParsers:
    """Tests for citation parsing utilities."""
    
    def test_extract_doi_from_pdf(self, monkeypatch):
        """Test extracting DOI from PDF text.
        
        Using monkeypatch to simulate a PDF reader without requiring actual PDF files.
        """
        class MockPdfPage:
            def extract_text(self):
                return "This is a test with a DOI: 10.1234/example.123"
        
        class MockPdfReader:
            def __init__(self):
                self.pages = [MockPdfPage(), MockPdfPage()]
                self.metadata = {"Subject": "Subject with DOI: 10.5678/another.example"}
        
        # Test extracting DOI from text
        pdf_reader = MockPdfReader()
        doi = extract_doi_from_pdf(pdf_reader)
        
        assert doi == "10.1234/example.123"
        
        # Test case with no DOI in text
        class MockPdfPageNoDoi:
            def extract_text(self):
                return "This is a test with no DOI"
        
        pdf_reader.pages = [MockPdfPageNoDoi(), MockPdfPageNoDoi()]
        doi = extract_doi_from_pdf(pdf_reader)
        
        assert doi == "10.5678/another.example"  # Should find in metadata
        
        # Test case with no DOI anywhere
        pdf_reader.metadata = {}
        doi = extract_doi_from_pdf(pdf_reader)
        
        assert doi is None
    
    def test_extract_pdf_metadata(self, monkeypatch):
        """Test extracting metadata from PDF.
        
        Using monkeypatch to simulate PDF operations without requiring actual PDF files.
        """
        class MockPdfPage:
            def extract_text(self):
                return "Title of the Paper\nAbstract: This is the abstract."
        
        class MockPdfReader:
            def __init__(self):
                self.pages = [MockPdfPage()]
                self.metadata = MockMetadata()
        
        class MockMetadata:
            title = "Test Paper Title"
            author = "Smith, John, Doe, Jane"
            subject = "Test paper subject"
        
        # Patch the PdfReader class
        monkeypatch.setattr("researchbrain.citations.parsers.PdfReader", lambda _: MockPdfReader())
        
        # Test with a mock PDF file
        pdf_path = Path("dummy.pdf")
        metadata = extract_pdf_metadata(pdf_path)
        
        assert metadata["title"] == "Test Paper Title"
        assert metadata["authors"] == ["Smith, John", "Doe, Jane"]
        assert metadata["abstract"] == "Test paper subject"
        
        # Test with missing title
        monkeypatch.setattr(MockMetadata, "title", None)
        metadata = extract_pdf_metadata(pdf_path)
        
        assert metadata["title"] == "Title of the Paper"  # Should extract from first page
        
        # Test with missing title and no clear title in content
        monkeypatch.setattr(MockPdfPage, "extract_text", lambda _: "No clear title here")
        metadata = extract_pdf_metadata(pdf_path)
        
        assert metadata["title"] == "Dummy"  # Should use filename
        
        # Test with missing authors
        monkeypatch.setattr(MockMetadata, "author", None)
        metadata = extract_pdf_metadata(pdf_path)
        
        assert metadata["authors"] == ["Unknown Author"]
    
    def test_parse_bibtex_file(self):
        """Test parsing BibTeX files."""
        # Create a temporary BibTeX file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as temp_file:
            temp_file.write("""
@article{smith2023example,
  title={Example Paper Title},
  author={Smith, John and Doe, Jane},
  journal={Journal of Examples},
  volume={10},
  number={2},
  pages={123--456},
  year={2023},
  publisher={Example Publisher},
  doi={10.1234/example},
  abstract={This is an example abstract.},
  keywords={keyword1, keyword2, keyword3}
}

@book{jones2022book,
  title={Example Book Title},
  author={Jones, Robert},
  year={2022},
  publisher={Book Publisher},
  address={New York}
}
            """)
            bibtex_path = Path(temp_file.name)
        
        try:
            # Parse the BibTeX file
            citations = parse_bibtex_file(bibtex_path)
            
            assert len(citations) == 2
            
            # Check first citation (article)
            article = citations[0]
            assert article["title"] == "Example Paper Title"
            assert article["authors"] == ["Smith, John", "Doe, Jane"]
            assert article["year"] == 2023
            assert article["journal"] == "Journal of Examples"
            assert article["volume"] == "10"
            assert article["issue"] == "2"
            assert article["pages"] == "123--456"
            assert article["publisher"] == "Example Publisher"
            assert article["doi"] == "10.1234/example"
            assert article["abstract"] == "This is an example abstract."
            assert article["keywords"] == ["keyword1", "keyword2", "keyword3"]
            assert article["citation_type"] == "article"
            
            # Check second citation (book)
            book = citations[1]
            assert book["title"] == "Example Book Title"
            assert book["authors"] == ["Jones, Robert"]
            assert book["year"] == 2022
            assert book["publisher"] == "Book Publisher"
            assert book["citation_type"] == "book"
            
        finally:
            # Clean up the temporary file
            os.unlink(bibtex_path)
    
    def test_parse_ris_file(self):
        """Test parsing RIS files."""
        # Create a temporary RIS file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ris', delete=False) as temp_file:
            temp_file.write("""
TY  - JOUR
TI  - Example Journal Article
AU  - Smith, John
AU  - Doe, Jane
PY  - 2023
DO  - 10.1234/example
UR  - https://example.com/article
JO  - Journal of Examples
VL  - 10
IS  - 2
SP  - 123
EP  - 456
PB  - Example Publisher
AB  - This is an example abstract.
KW  - keyword1
KW  - keyword2
KW  - keyword3
ER  - 

TY  - BOOK
TI  - Example Book
AU  - Jones, Robert
PY  - 2022
PB  - Book Publisher
ER  - 
            """)
            ris_path = Path(temp_file.name)
        
        try:
            # Parse the RIS file
            citations = parse_ris_file(ris_path)
            
            assert len(citations) == 2
            
            # Check first citation (journal article)
            article = citations[0]
            assert article["title"] == "Example Journal Article"
            assert article["authors"] == ["Smith, John", "Doe, Jane"]
            assert article["year"] == 2023
            assert article["doi"] == "10.1234/example"
            assert article["url"] == "https://example.com/article"
            assert article["journal"] == "Journal of Examples"
            assert article["volume"] == "10"
            assert article["issue"] == "2"
            assert article["pages"] == "123-456"
            assert article["publisher"] == "Example Publisher"
            assert article["abstract"] == "This is an example abstract."
            assert article["keywords"] == ["keyword1", "keyword2", "keyword3"]
            assert article["citation_type"] == "article"
            
            # Check second citation (book)
            book = citations[1]
            assert book["title"] == "Example Book"
            assert book["authors"] == ["Jones, Robert"]
            assert book["year"] == 2022
            assert book["publisher"] == "Book Publisher"
            assert book["citation_type"] == "book"
            
        finally:
            # Clean up the temporary file
            os.unlink(ris_path)
    
    def test_parse_invalid_bibtex(self):
        """Test parsing invalid BibTeX content."""
        # Create a temporary file with invalid BibTeX
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as temp_file:
            temp_file.write("""
This is not a valid BibTeX file.
@article{incomplete
            """)
            invalid_path = Path(temp_file.name)
        
        try:
            # Parse the invalid file
            citations = parse_bibtex_file(invalid_path)
            
            # Should return an empty list, not raise an exception
            assert citations == []
            
        finally:
            # Clean up the temporary file
            os.unlink(invalid_path)
    
    def test_parse_invalid_ris(self):
        """Test parsing invalid RIS content."""
        # Create a temporary file with invalid RIS
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ris', delete=False) as temp_file:
            temp_file.write("""
This is not a valid RIS file.
TY  - JOUR
TI  - Incomplete entry without ER
            """)
            invalid_path = Path(temp_file.name)
        
        try:
            # Parse the invalid file
            citations = parse_ris_file(invalid_path)
            
            # Should return an empty list, not raise an exception
            assert citations == []
            
        finally:
            # Clean up the temporary file
            os.unlink(invalid_path)