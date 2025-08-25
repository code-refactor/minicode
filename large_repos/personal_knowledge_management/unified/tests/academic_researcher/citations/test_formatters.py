"""Tests for citation formatters."""

import pytest

from researchbrain.core.models import Citation, CitationFormat, CitationType
from researchbrain.citations.formatters import (
    format_author_list, format_citation, _format_apa, _format_mla,
    _format_chicago, _format_harvard, _format_ieee, _format_vancouver,
    _format_bibtex, _format_ris
)


class TestCitationFormatters:
    """Tests for citation formatting utilities."""
    
    @pytest.fixture
    def sample_citation(self):
        """Fixture that creates a sample citation for testing."""
        return Citation(
            title="Example Paper Title",
            authors=["Smith, John", "Doe, Jane"],
            year=2023,
            doi="10.1234/example",
            url="https://example.com/paper",
            journal="Journal of Examples",
            volume="10",
            issue="2",
            pages="123-145",
            publisher="Example Publisher",
            citation_type=CitationType.ARTICLE,
            abstract="This is an example abstract.",
            keywords=["keyword1", "keyword2"]
        )
    
    @pytest.fixture
    def book_citation(self):
        """Fixture that creates a book citation for testing."""
        return Citation(
            title="Example Book Title",
            authors=["Jones, Robert"],
            year=2022,
            publisher="Book Publisher",
            citation_type=CitationType.BOOK
        )
    
    def test_format_author_list(self):
        """Test formatting author lists in different citation styles."""
        # Test single author
        single_author = ["Smith, John"]
        
        assert format_author_list(single_author, CitationFormat.APA) == "Smith, John"
        assert format_author_list(single_author, CitationFormat.MLA) == "Smith, John"
        assert format_author_list(single_author, CitationFormat.CHICAGO) == "Smith, John"
        assert format_author_list(single_author, CitationFormat.HARVARD) == "Smith, John"
        assert format_author_list(single_author, CitationFormat.IEEE) == "Smith, John"
        assert format_author_list(single_author, CitationFormat.VANCOUVER) == "Smith, John"
        
        # Test two authors
        two_authors = ["Smith, John", "Doe, Jane"]
        
        assert format_author_list(two_authors, CitationFormat.APA) == "Smith, John & Doe, Jane"
        assert format_author_list(two_authors, CitationFormat.MLA) == "Smith, John and Doe, Jane"
        assert format_author_list(two_authors, CitationFormat.CHICAGO) == "Smith, John, and Doe, Jane"
        assert format_author_list(two_authors, CitationFormat.HARVARD) == "Smith, John and Doe, Jane"
        assert format_author_list(two_authors, CitationFormat.IEEE) == "Smith, John and Doe, Jane"
        assert format_author_list(two_authors, CitationFormat.VANCOUVER) == "Smith, John, Doe, Jane"
        
        # Test multiple authors
        multiple_authors = ["Smith, John", "Doe, Jane", "Brown, Robert", "Wilson, Mary"]
        
        assert format_author_list(multiple_authors, CitationFormat.APA) == "Smith, John, Doe, Jane, Brown, Robert, & Wilson, Mary"
        assert format_author_list(multiple_authors, CitationFormat.MLA) == "Smith, John et al."
        assert format_author_list(multiple_authors, CitationFormat.CHICAGO) == "Smith, John et al."
        assert format_author_list(multiple_authors, CitationFormat.HARVARD) == "Smith, John et al."
        assert format_author_list(multiple_authors, CitationFormat.IEEE) == "Smith, John et al."
        assert format_author_list(multiple_authors, CitationFormat.VANCOUVER) == "Smith, John, Doe, Jane, Brown, Robert, Wilson, Mary"
    
    def test_format_citation_apa(self, sample_citation):
        """Test APA citation formatting."""
        formatted = format_citation(sample_citation, CitationFormat.APA)
        
        assert "Smith, John & Doe, Jane" in formatted
        assert "(2023)" in formatted
        assert "Example Paper Title" in formatted
        assert "<em>Journal of Examples</em>" in formatted
        assert "10(2)" in formatted
        assert "123-145" in formatted
        assert "https://doi.org/10.1234/example" in formatted
    
    def test_format_citation_mla(self, sample_citation):
        """Test MLA citation formatting."""
        formatted = format_citation(sample_citation, CitationFormat.MLA)
        
        assert "Smith, John and Doe, Jane" in formatted
        assert '"Example Paper Title."' in formatted
        assert "<em>Journal of Examples</em>" in formatted
        assert "vol. 10" in formatted
        assert "no. 2" in formatted
        assert "2023" in formatted
        assert "pp. 123-145" in formatted
        assert "DOI: 10.1234/example" in formatted
    
    def test_format_citation_chicago(self, sample_citation):
        """Test Chicago citation formatting."""
        formatted = format_citation(sample_citation, CitationFormat.CHICAGO)
        
        assert "Smith, John, and Doe, Jane" in formatted
        assert '"Example Paper Title."' in formatted
        assert "<em>Journal of Examples</em>" in formatted
        assert "10" in formatted
        assert "no. 2" in formatted
        assert "(2023)" in formatted
        assert "123-145" in formatted
        assert "https://doi.org/10.1234/example" in formatted
    
    def test_format_citation_harvard(self, sample_citation):
        """Test Harvard citation formatting."""
        formatted = format_citation(sample_citation, CitationFormat.HARVARD)
        
        assert "Smith, John and Doe, Jane" in formatted
        assert "(2023)" in formatted
        assert "'Example Paper Title'" in formatted
        assert "<em>Journal of Examples</em>" in formatted
        assert "10(2)" in formatted
        assert "pp. 123-145" in formatted
        assert "Available at: https://doi.org/10.1234/example" in formatted
    
    def test_format_citation_ieee(self, sample_citation):
        """Test IEEE citation formatting."""
        formatted = format_citation(sample_citation, CitationFormat.IEEE)
        
        assert "Smith, John and Doe, Jane" in formatted
        assert '"Example Paper Title,"' in formatted
        assert "<em>Journal of Examples</em>" in formatted
        assert "vol. 10" in formatted
        assert "no. 2" in formatted
        assert "pp. 123-145" in formatted
        assert "2023" in formatted
        assert "doi: 10.1234/example" in formatted
    
    def test_format_citation_vancouver(self, sample_citation):
        """Test Vancouver citation formatting."""
        formatted = format_citation(sample_citation, CitationFormat.VANCOUVER)
        
        assert "Smith, John, Doe, Jane" in formatted
        assert "Example Paper Title" in formatted
        assert "Journal of Examples" in formatted
        assert "2023" in formatted
        assert "10(2)" in formatted
        assert "123-145" in formatted
        assert "doi: 10.1234/example" in formatted
    
    def test_format_citation_bibtex(self, sample_citation):
        """Test BibTeX citation formatting."""
        formatted = format_citation(sample_citation, CitationFormat.BIBTEX)
        
        assert "@article{" in formatted
        assert "title = {Example Paper Title}" in formatted
        assert "author = {Smith, John and Doe, Jane}" in formatted
        assert "year = {2023}" in formatted
        assert "journal = {Journal of Examples}" in formatted
        assert "volume = {10}" in formatted
        assert "number = {2}" in formatted
        assert "pages = {123-145}" in formatted
        assert "publisher = {Example Publisher}" in formatted
        assert "doi = {10.1234/example}" in formatted
        assert "url = {https://example.com/paper}" in formatted
        assert "abstract = {This is an example abstract.}" in formatted
        assert "keywords = {keyword1, keyword2}" in formatted
    
    def test_format_citation_ris(self, sample_citation):
        """Test RIS citation formatting."""
        formatted = format_citation(sample_citation, CitationFormat.RIS)
        
        assert "TY  - JOUR" in formatted
        assert "TI  - Example Paper Title" in formatted
        assert "AU  - Smith, John" in formatted
        assert "AU  - Doe, Jane" in formatted
        assert "PY  - 2023" in formatted
        assert "JO  - Journal of Examples" in formatted
        assert "VL  - 10" in formatted
        assert "IS  - 2" in formatted
        assert "SP  - 123" in formatted
        assert "EP  - 145" in formatted
        assert "DO  - 10.1234/example" in formatted
        assert "UR  - https://example.com/paper" in formatted
        assert "AB  - This is an example abstract" in formatted
        assert "KW  - keyword1" in formatted
        assert "KW  - keyword2" in formatted
        assert "ER  - " in formatted
    
    def test_format_book_citation(self, book_citation):
        """Test formatting a book citation in different styles."""
        # APA style
        apa = format_citation(book_citation, CitationFormat.APA)
        assert "Jones, Robert" in apa
        assert "(2022)" in apa
        assert "Example Book Title" in apa
        assert "Book Publisher" in apa
        
        # MLA style
        mla = format_citation(book_citation, CitationFormat.MLA)
        assert "Jones, Robert" in mla
        assert "<em>Example Book Title</em>" in mla
        assert "Book Publisher" in mla
        assert "2022" in mla
        
        # Chicago style
        chicago = format_citation(book_citation, CitationFormat.CHICAGO)
        assert "Jones, Robert" in chicago
        assert "<em>Example Book Title</em>" in chicago
        assert "Book Publisher" in chicago
        assert "2022" in chicago
    
    def test_format_missing_fields(self):
        """Test formatting citations with missing fields."""
        # Citation with minimal fields
        minimal_citation = Citation(
            title="Minimal Example",
            authors=["Author, Test"]
        )
        
        # APA style should handle missing year
        apa = format_citation(minimal_citation, CitationFormat.APA)
        assert "Author, Test" in apa
        assert "(n.d.)" in apa  # n.d. for no date
        assert "Minimal Example" in apa
        
        # MLA style
        mla = format_citation(minimal_citation, CitationFormat.MLA)
        assert "Author, Test" in mla
        assert "Minimal Example" in mla
        assert "n.d." in mla  # n.d. for no date
        
        # Chicago style
        chicago = format_citation(minimal_citation, CitationFormat.CHICAGO)
        assert "Author, Test" in chicago
        assert "Minimal Example" in chicago
        assert "n.d." in chicago  # n.d. for no date