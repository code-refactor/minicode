"""Tests for citation parsing accuracy across multiple academic formats."""

import os
import tempfile
from pathlib import Path

import pytest

from researchbrain.core.brain import ResearchBrain
from researchbrain.core.models import Citation, CitationFormat
from researchbrain.citations.parsers import parse_bibtex_file, parse_ris_file


class TestCitationAccuracy:
    """Tests for citation parsing accuracy across multiple academic formats."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Fixture that creates a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def brain(self, temp_data_dir):
        """Fixture that creates a ResearchBrain instance."""
        return ResearchBrain(temp_data_dir)
    
    def test_apa_citation_accuracy(self, brain):
        """Test accuracy of APA citation formatting."""
        # Create a citation with all the fields needed for APA style
        citation_id = brain.create_citation(
            title="The effects of cognitive training on neural plasticity",
            authors=["Smith, John A.", "Johnson, Maria R.", "Williams, Robert P."],
            year=2022,
            journal="Journal of Cognitive Neuroscience",
            volume="37",
            issue="4",
            pages="412-428",
            publisher="Cognitive Science Society",
            doi="10.1234/jcn.2022.37.4.412"
        )
        
        # Generate APA citation
        apa_citation = brain.generate_citation(citation_id, CitationFormat.APA)
        
        # Verify all expected components of APA style are present
        assert "Smith, John A., Johnson, Maria R., & Williams, Robert P." in apa_citation
        assert "(2022)" in apa_citation
        assert "The effects of cognitive training on neural plasticity" in apa_citation
        assert "<em>Journal of Cognitive Neuroscience</em>" in apa_citation
        assert "37" in apa_citation
        assert "4" in apa_citation
        assert "412-428" in apa_citation
        assert "https://doi.org/10.1234/jcn.2022.37.4.412" in apa_citation
    
    def test_mla_citation_accuracy(self, brain):
        """Test accuracy of MLA citation formatting."""
        citation_id = brain.create_citation(
            title="Machine Learning Approaches to Natural Language Processing",
            authors=["Garcia, Ana L.", "Chen, Wei"],
            year=2021,
            journal="Computational Linguistics",
            volume="45",
            issue="2",
            pages="187-215",
            publisher="Association for Computational Linguistics",
            doi="10.1234/cl.2021.45.2.187"
        )
        
        # Generate MLA citation
        mla_citation = brain.generate_citation(citation_id, CitationFormat.MLA)
        
        # Verify MLA style components
        assert "Garcia, Ana L. and Chen, Wei" in mla_citation
        assert '"Machine Learning Approaches to Natural Language Processing."' in mla_citation
        assert "<em>Computational Linguistics</em>" in mla_citation
        assert "vol. 45" in mla_citation
        assert "no. 2" in mla_citation
        assert "2021" in mla_citation
        assert "pp. 187-215" in mla_citation
        assert "DOI: 10.1234/cl.2021.45.2.187" in mla_citation
    
    def test_chicago_citation_accuracy(self, brain):
        """Test accuracy of Chicago citation formatting."""
        citation_id = brain.create_citation(
            title="Climate Change Impact on Marine Ecosystems",
            authors=["Roberts, Emily J.", "Thompson, David S.", "Kumar, Priya"],
            year=2020,
            journal="Marine Biology Research",
            volume="28",
            issue="3",
            pages="298-317",
            publisher="Ocean Science Press",
            doi="10.1234/mbr.2020.28.3.298"
        )
        
        # Generate Chicago citation
        chicago_citation = brain.generate_citation(citation_id, CitationFormat.CHICAGO)
        
        # Verify Chicago style components - all authors are listed rather than using "et al."
        assert "Roberts, Emily J., Thompson, David S., and Kumar, Priya" in chicago_citation
        assert '"Climate Change Impact on Marine Ecosystems."' in chicago_citation
        assert "<em>Marine Biology Research</em>" in chicago_citation
        assert "28" in chicago_citation
        assert "no. 3" in chicago_citation
        assert "(2020)" in chicago_citation
        assert "298-317" in chicago_citation
        assert "https://doi.org/10.1234/mbr.2020.28.3.298" in chicago_citation
    
    def test_bibtex_citation_accuracy(self, brain):
        """Test accuracy of BibTeX citation formatting."""
        # Create a citation
        citation_id = brain.create_citation(
            title="Advances in Quantum Computing Algorithms",
            authors=["Miller, Sarah K.", "Anderson, Thomas J."],
            year=2023,
            journal="Quantum Information Processing",
            volume="12",
            issue="1",
            pages="45-67",
            publisher="Quantum Science Publishers",
            doi="10.1234/qip.2023.12.1.45",
            abstract="This paper presents recent advances in quantum computing algorithms...",
            keywords=["quantum computing", "algorithms", "quantum information"]
        )
        
        # Generate BibTeX citation
        bibtex_citation = brain.generate_citation(citation_id, CitationFormat.BIBTEX)
        
        # Verify BibTeX components
        assert "@article{" in bibtex_citation
        assert "title = {Advances in Quantum Computing Algorithms}" in bibtex_citation
        assert "author = {Miller, Sarah K. and Anderson, Thomas J.}" in bibtex_citation
        assert "year = {2023}" in bibtex_citation
        assert "journal = {Quantum Information Processing}" in bibtex_citation
        assert "volume = {12}" in bibtex_citation
        assert "number = {1}" in bibtex_citation
        assert "pages = {45-67}" in bibtex_citation
        assert "publisher = {Quantum Science Publishers}" in bibtex_citation
        assert "doi = {10.1234/qip.2023.12.1.45}" in bibtex_citation
        assert "abstract = {This paper presents recent advances in quantum computing algorithms...}" in bibtex_citation
        assert "keywords = {quantum computing, algorithms, quantum information}" in bibtex_citation
    
    def test_bibtex_parser_accuracy(self):
        """Test accuracy of BibTeX parsing."""
        # Create a temporary BibTeX file with multiple entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as temp_file:
            temp_file.write("""
@article{smith2022neural,
  title={Neural mechanisms of memory formation},
  author={Smith, A. and Johnson, B. and Davis, C.},
  journal={Neuroscience Reviews},
  volume={15},
  number={3},
  pages={210--225},
  year={2022},
  publisher={Neuroscience Publishers},
  doi={10.1234/neuro.2022.15.3.210}
}

@book{brown2020cognitive,
  title={Cognitive Development in Children},
  author={Brown, D. E.},
  year={2020},
  publisher={Educational Press},
  address={New York},
  isbn={978-1-234567-89-0}
}

@inproceedings{wong2023machine,
  title={Machine Learning for Medical Diagnosis},
  author={Wong, F. and Garcia, H.},
  booktitle={International Conference on Medical Informatics},
  pages={145--158},
  year={2023},
  organization={Medical Informatics Society}
}
            """)
            bibtex_path = Path(temp_file.name)
        
        try:
            # Parse the BibTeX file
            citations = parse_bibtex_file(bibtex_path)
            
            # Verify correct parsing of multiple entry types
            assert len(citations) == 3
            
            # Check article
            article = next((c for c in citations if c["title"] == "Neural mechanisms of memory formation"), None)
            assert article is not None
            assert article["authors"] == ["Smith, A.", "Johnson, B.", "Davis, C."]
            assert article["year"] == 2022
            assert article["journal"] == "Neuroscience Reviews"
            assert article["volume"] == "15"
            assert article["issue"] == "3"
            assert article["pages"] == "210--225"
            assert article["doi"] == "10.1234/neuro.2022.15.3.210"
            assert article["citation_type"] == "article"
            
            # Check book
            book = next((c for c in citations if c["title"] == "Cognitive Development in Children"), None)
            assert book is not None
            assert book["authors"] == ["Brown, D. E."]
            assert book["year"] == 2020
            assert book["publisher"] == "Educational Press"
            assert book["citation_type"] == "book"
            
            # Check conference paper
            conference = next((c for c in citations if c["title"] == "Machine Learning for Medical Diagnosis"), None)
            assert conference is not None
            assert conference["authors"] == ["Wong, F.", "Garcia, H."]
            assert conference["year"] == 2023
            assert conference["journal"] == "International Conference on Medical Informatics"  # booktitle mapped to journal
            assert conference["pages"] == "145--158"
            assert conference["citation_type"] == "conference"
            
        finally:
            # Clean up the temporary file
            os.unlink(bibtex_path)
    
    def test_ris_parser_accuracy(self):
        """Test accuracy of RIS parsing."""
        # Create a temporary RIS file with multiple entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ris', delete=False) as temp_file:
            temp_file.write("""
TY  - JOUR
TI  - Epigenetic regulation in psychiatric disorders
AU  - Rodriguez, M. A.
AU  - Lee, S. H.
PY  - 2021
JO  - Journal of Psychiatric Research
VL  - 42
IS  - 5
SP  - 378
EP  - 395
DO  - 10.1234/jpr.2021.42.5.378
KW  - epigenetics
KW  - psychiatry
KW  - mental health
AB  - This review discusses recent advances in understanding epigenetic mechanisms...
ER  - 

TY  - BOOK
TI  - Statistical Methods for Behavioral Science
AU  - Thompson, L. R.
PY  - 2019
PB  - Academic Publishers
CY  - Boston
SN  - 978-0-123456-78-9
ER  - 

TY  - CONF
TI  - Deep Learning Applications in Robotics
AU  - Chen, W. X.
AU  - Williams, J. K.
PY  - 2023
CY  - San Francisco, CA
PB  - Robotics Society
ER  - 
            """)
            ris_path = Path(temp_file.name)
        
        try:
            # Parse the RIS file
            citations = parse_ris_file(ris_path)
            
            # Verify correct parsing of multiple entry types
            assert len(citations) == 3
            
            # Check journal article
            article = next((c for c in citations if c["title"] == "Epigenetic regulation in psychiatric disorders"), None)
            assert article is not None
            assert article["authors"] == ["Rodriguez, M. A.", "Lee, S. H."]
            assert article["year"] == 2021
            assert article["journal"] == "Journal of Psychiatric Research"
            assert article["volume"] == "42"
            assert article["issue"] == "5"
            assert article["pages"] == "378-395"
            assert article["doi"] == "10.1234/jpr.2021.42.5.378"
            assert article["keywords"] == ["epigenetics", "psychiatry", "mental health"]
            assert article["abstract"] == "This review discusses recent advances in understanding epigenetic mechanisms..."
            assert article["citation_type"] == "article"
            
            # Check book
            book = next((c for c in citations if c["title"] == "Statistical Methods for Behavioral Science"), None)
            assert book is not None
            assert book["authors"] == ["Thompson, L. R."]
            assert book["year"] == 2019
            assert book["publisher"] == "Academic Publishers"
            assert book["citation_type"] == "book"
            
            # Check conference paper
            conference = next((c for c in citations if c["title"] == "Deep Learning Applications in Robotics"), None)
            assert conference is not None
            assert conference["authors"] == ["Chen, W. X.", "Williams, J. K."]
            assert conference["year"] == 2023
            assert conference["publisher"] == "Robotics Society"
            assert conference["citation_type"] == "conference"
            
        finally:
            # Clean up the temporary file
            os.unlink(ris_path)
    
    def test_malformed_citation_handling(self, brain):
        """Test handling of malformed citation data."""
        # Test with minimal information
        minimal_id = brain.create_citation(
            title="Minimal Citation",
            authors=[]  # Empty authors list
        )
        
        minimal_citation = brain.storage.get(Citation, minimal_id)
        assert minimal_citation is not None
        assert minimal_citation.title == "Minimal Citation"
        assert minimal_citation.authors == []
        
        # Format should still work with default/fallback values
        apa_minimal = brain.generate_citation(minimal_id, CitationFormat.APA)
        assert "Minimal Citation" in apa_minimal
        assert "(n.d.)" in apa_minimal  # No date indicator
        
        # Test with extremely long title
        long_title = "A " + "very " * 100 + "long title"
        long_id = brain.create_citation(
            title=long_title,
            authors=["Author, Test"]
        )
        
        # Should handle long title without crashing
        mla_long = brain.generate_citation(long_id, CitationFormat.MLA)
        assert "Author, Test" in mla_long
        assert long_title in mla_long