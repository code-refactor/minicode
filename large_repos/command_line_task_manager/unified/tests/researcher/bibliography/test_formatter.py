from datetime import datetime

import pytest

from researchtrack.bibliography.formatter import ReferenceFormatter
from researchtrack.bibliography.models import (
    Author,
    AuthorType,
    CitationStyle,
    Reference,
    ReferenceType,
)


class TestReferenceFormatter:
    def setup_method(self):
        """Set up test references that will be used by multiple tests."""
        # Create some author instances to use in test references
        self.single_author = [
            Author(
                type=AuthorType.PERSON,
                first_name="John",
                last_name="Smith",
            )
        ]
        
        self.two_authors = [
            Author(
                type=AuthorType.PERSON,
                first_name="John",
                last_name="Smith",
            ),
            Author(
                type=AuthorType.PERSON,
                first_name="Jane",
                last_name="Doe",
            ),
        ]
        
        self.multiple_authors = [
            Author(
                type=AuthorType.PERSON,
                first_name="John",
                last_name="Smith",
            ),
            Author(
                type=AuthorType.PERSON,
                first_name="Jane",
                last_name="Doe",
            ),
            Author(
                type=AuthorType.PERSON,
                first_name="Robert",
                last_name="Johnson",
            ),
            Author(
                type=AuthorType.PERSON,
                first_name="Emily",
                last_name="Wilson",
            ),
        ]
        
        self.organization_author = [
            Author(
                type=AuthorType.ORGANIZATION,
                organization_name="National Science Foundation",
            )
        ]
        
        # Create references of different types
        self.journal_article = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Climate Change Impacts on Coastal Ecosystems",
            authors=self.two_authors,
            year=2022,
            journal_name="Journal of Environmental Science",
            volume="45",
            issue="3",
            pages="123-145",
            doi="10.1234/jes.2022.12345",
        )
        
        self.book = Reference(
            type=ReferenceType.BOOK,
            title="Advanced Data Analysis Techniques",
            authors=self.single_author,
            year=2019,
            publisher="Academic Press",
            isbn="978-1234567890",
            edition="2nd",
        )
        
        self.website = Reference(
            type=ReferenceType.WEBSITE,
            title="Climate Data Online",
            authors=self.organization_author,
            url="https://www.ncdc.noaa.gov/cdo-web/",
            accessed_date=datetime(2023, 5, 15),
            year=2023,
        )
    
    def test_apa_formatting(self):
        # Test APA formatting for different reference types
        
        # Journal article
        formatted = ReferenceFormatter.format_citation(
            self.journal_article, CitationStyle.APA
        )
        assert "Smith, John & Doe, Jane" in formatted
        assert "(2022)" in formatted
        assert "Climate Change Impacts on Coastal Ecosystems" in formatted
        assert "Journal of Environmental Science" in formatted
        assert "45(3), 123-145" in formatted
        
        # Book
        formatted = ReferenceFormatter.format_citation(
            self.book, CitationStyle.APA
        )
        assert "Smith, John" in formatted
        assert "(2019)" in formatted
        assert "Advanced Data Analysis Techniques" in formatted
        assert "Academic Press" in formatted
        
        # Website
        formatted = ReferenceFormatter.format_citation(
            self.website, CitationStyle.APA
        )
        assert "National Science Foundation" in formatted
        assert "(2023)" in formatted
        assert "Climate Data Online" in formatted
        assert "https://www.ncdc.noaa.gov/cdo-web/" in formatted
        assert "May 15, 2023" in formatted  # Accessed date
    
    def test_mla_formatting(self):
        # Test MLA formatting for different reference types
        
        # Journal article
        formatted = ReferenceFormatter.format_citation(
            self.journal_article, CitationStyle.MLA
        )
        assert "Smith, John, and Jane Doe" in formatted
        assert '"Climate Change Impacts on Coastal Ecosystems."' in formatted
        assert "Journal of Environmental Science" in formatted
        assert "vol. 45" in formatted
        assert "2022" in formatted
        assert "pp. 123-145" in formatted
        
        # Book
        formatted = ReferenceFormatter.format_citation(
            self.book, CitationStyle.MLA
        )
        assert "Smith, John" in formatted
        assert "Advanced Data Analysis Techniques" in formatted
        assert "Academic Press" in formatted
        assert "2019" in formatted
    
    def test_harvard_formatting(self):
        # Test Harvard formatting
        
        # Journal article
        formatted = ReferenceFormatter.format_citation(
            self.journal_article, CitationStyle.HARVARD
        )
        assert "Smith, J & Doe, J" in formatted
        assert "(2022)" in formatted
        assert "'Climate Change Impacts on Coastal Ecosystems'" in formatted
        assert "Journal of Environmental Science" in formatted
        assert "45(3)" in formatted
        assert "pp. 123-145" in formatted
    
    def test_ieee_formatting(self):
        # Test IEEE formatting
        
        # Journal article
        formatted = ReferenceFormatter.format_citation(
            self.journal_article, CitationStyle.IEEE
        )
        assert "Smith, J & Doe, J" in formatted
        assert '"Climate Change Impacts on Coastal Ecosystems,"' in formatted
        assert "Journal of Environmental Science" in formatted
        assert "vol. 45, no. 3, pp. 123-145, 2022" in formatted
    
    def test_in_text_citations(self):
        # Test in-text citations for different styles
        
        # APA in-text citation
        in_text = ReferenceFormatter.format_in_text_citation(
            self.journal_article, CitationStyle.APA
        )
        assert in_text == "(Smith & Doe, 2022)"
        
        # MLA in-text citation
        in_text = ReferenceFormatter.format_in_text_citation(
            self.journal_article, CitationStyle.MLA
        )
        assert in_text == "(Smith et al. 123-145)" or in_text == "(Smith et al.)"
        
        # Harvard in-text citation
        in_text = ReferenceFormatter.format_in_text_citation(
            self.journal_article, CitationStyle.HARVARD
        )
        assert in_text == "(Smith and Doe, 2022)"
        
        # IEEE in-text citation (placeholder implementation)
        in_text = ReferenceFormatter.format_in_text_citation(
            self.journal_article, CitationStyle.IEEE
        )
        assert "[" in in_text and "]" in in_text  # Check for numbered citation format
    
    def test_generate_bibliography(self):
        # Test bibliography generation with multiple references
        
        # Create a list of references
        references = [
            self.journal_article,
            self.book,
            self.website,
        ]
        
        # Generate bibliography in APA style
        bibliography = ReferenceFormatter.generate_bibliography(
            references, CitationStyle.APA
        )
        
        # Verify that it contains all references
        assert "Smith, John & Doe, Jane" in bibliography
        assert "Climate Change Impacts on Coastal Ecosystems" in bibliography
        assert "Advanced Data Analysis Techniques" in bibliography
        assert "Climate Data Online" in bibliography
        
        # Verify order (should be alphabetical by author last name)
        assert bibliography.index("National Science Foundation") < bibliography.index("Smith, John &")
        assert bibliography.index("Smith, John &") < bibliography.index("Smith, John. (2019)")
        
        # Test with empty list
        empty_bibliography = ReferenceFormatter.generate_bibliography([], CitationStyle.APA)
        assert empty_bibliography == ""
    
    def test_author_formatting(self):
        # Test author formatting with different numbers of authors
        
        # Test with single author
        single_author_ref = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Single Author Paper",
            authors=self.single_author,
            year=2020,
        )
        
        formatted = ReferenceFormatter.format_citation(
            single_author_ref, CitationStyle.APA
        )
        assert "Smith, John" in formatted
        
        # Test with two authors
        two_authors_ref = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Two Authors Paper",
            authors=self.two_authors,
            year=2020,
        )
        
        formatted = ReferenceFormatter.format_citation(
            two_authors_ref, CitationStyle.APA
        )
        assert "Smith, John & Doe, Jane" in formatted
        
        # Test with multiple authors
        multiple_authors_ref = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Multiple Authors Paper",
            authors=self.multiple_authors,
            year=2020,
        )
        
        formatted = ReferenceFormatter.format_citation(
            multiple_authors_ref, CitationStyle.APA
        )
        assert "Smith, John" in formatted
        assert "Doe, Jane" in formatted
        assert "Johnson, Robert" in formatted
        assert "Wilson, Emily" in formatted
        
        # Test with organization author
        org_author_ref = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="Organization Author Paper",
            authors=self.organization_author,
            year=2020,
        )
        
        formatted = ReferenceFormatter.format_citation(
            org_author_ref, CitationStyle.APA
        )
        assert "National Science Foundation" in formatted
        
        # Test with no authors
        no_authors_ref = Reference(
            type=ReferenceType.JOURNAL_ARTICLE,
            title="No Authors Paper",
            authors=[],
            year=2020,
        )
        
        formatted = ReferenceFormatter.format_citation(
            no_authors_ref, CitationStyle.APA
        )
        assert "Unknown Author" in formatted