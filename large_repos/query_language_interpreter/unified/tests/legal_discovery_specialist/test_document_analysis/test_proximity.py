"""Tests for the proximity search functionality."""

import pytest
from legal_discovery_interpreter.document_analysis.proximity import ProximitySearchEngine


@pytest.fixture
def proximity_engine():
    """Create a sample proximity search engine for testing."""
    return ProximitySearchEngine()


@pytest.fixture
def sample_text():
    """Sample text for testing proximity search."""
    return """
    This agreement is made between Party A and Party B. Both parties agree to the terms and conditions
    outlined in this document. In case of a breach of contract, the liable party shall be responsible
    for all damages.
    
    The statute of limitations for any claims arising from this agreement shall be two years from the
    effective date. The governing law of this agreement is the law of the State of New York.
    
    This agreement contains a confidentiality clause. All parties must maintain the confidentiality
    of any proprietary information exchanged during the course of this agreement.
    """


def test_tokenize_document(proximity_engine, sample_text):
    """Test tokenizing a document into words, sentences, and paragraphs."""
    tokenized = proximity_engine.tokenize_document(sample_text)
    
    assert 'words' in tokenized
    assert 'sentences' in tokenized
    assert 'paragraphs' in tokenized
    assert 'paragraph_boundaries' in tokenized
    assert 'sentence_boundaries' in tokenized
    
    # Check that we have some tokens
    assert len(tokenized['words']) > 0
    assert len(tokenized['sentences']) > 0
    assert len(tokenized['paragraphs']) > 0
    
    # Check specific words
    words = [word.lower() for word in tokenized['words']]
    assert 'agreement' in words
    assert 'breach' in words
    assert 'contract' in words
    assert 'statute' in words
    assert 'limitations' in words


def test_calculate_word_positions(proximity_engine):
    """Test calculating positions of words in a document."""
    words = ['the', 'quick', 'brown', 'fox', 'jumps', 'over', 'the', 'lazy', 'dog']
    positions = proximity_engine.calculate_word_positions(words)
    
    assert 'the' in positions
    assert 'quick' in positions
    assert 'fox' in positions
    
    assert positions['the'] == [0, 6]  # 'the' appears at positions 0 and 6
    assert positions['quick'] == [1]  # 'quick' appears at position 1
    assert positions['fox'] == [3]  # 'fox' appears at position 3


def test_within_distance(proximity_engine):
    """Test finding positions within a certain distance."""
    positions1 = [1, 5, 10]
    positions2 = [3, 8, 15]

    # Distance of 2
    matches = proximity_engine._within_distance(positions1, positions2, 2)
    assert len(matches) >= 2
    assert (1, 3) in matches  # 3 - 1 = 2, within distance
    assert (5, 3) in matches  # 5 - 3 = 2, within distance

    # Distance of 3
    matches = proximity_engine._within_distance(positions1, positions2, 3)
    # Should have at least two matches
    assert len(matches) >= 2
    assert (5, 8) in matches  # 8 - 5 = 3, within distance


def test_within_distance_ordered(proximity_engine):
    """Test finding positions where the second follows the first within a distance."""
    positions1 = [1, 5, 10]
    positions2 = [3, 8, 15]
    
    # Distance of 2, ordered
    matches = proximity_engine._within_distance_ordered(positions1, positions2, 2)
    assert len(matches) == 1
    assert (1, 3) in matches  # 3 - 1 = 2, within distance and ordered
    
    # Distance of 3, ordered
    matches = proximity_engine._within_distance_ordered(positions1, positions2, 3)
    assert len(matches) == 2
    assert (1, 3) in matches  # 3 - 1 = 2, within distance and ordered
    assert (5, 8) in matches  # 8 - 5 = 3, within distance and ordered


def test_positions_to_unit(proximity_engine, sample_text):
    """Test converting word positions to unit indices."""
    tokenized = proximity_engine.tokenize_document(sample_text)
    positions = [5, 10, 20]
    
    # Convert to words
    word_units = proximity_engine._positions_to_unit(positions, "WORDS", tokenized)
    assert word_units == set(positions)
    
    # Convert to sentences
    sentence_units = proximity_engine._positions_to_unit(positions, "SENTENCES", tokenized)
    assert isinstance(sentence_units, set)
    assert len(sentence_units) > 0
    
    # Convert to paragraphs
    paragraph_units = proximity_engine._positions_to_unit(positions, "PARAGRAPHS", tokenized)
    assert isinstance(paragraph_units, set)
    assert len(paragraph_units) > 0


def test_calculate_proximity_basic(proximity_engine):
    """Test basic proximity search functionality."""
    content = "The quick brown fox jumps over the lazy dog."
    
    # Terms next to each other
    assert proximity_engine.calculate_proximity(content, ["quick", "brown"], 1, "WORDS", False) is True
    
    # Terms with one word between
    assert proximity_engine.calculate_proximity(content, ["quick", "fox"], 2, "WORDS", False) is True
    
    # Terms not close enough
    assert proximity_engine.calculate_proximity(content, ["quick", "dog"], 3, "WORDS", False) is False
    
    # Ordered terms
    assert proximity_engine.calculate_proximity(content, ["quick", "fox"], 2, "WORDS", True) is True
    assert proximity_engine.calculate_proximity(content, ["fox", "quick"], 2, "WORDS", True) is False
    
    # Single term
    assert proximity_engine.calculate_proximity(content, ["quick"], 1, "WORDS", False) is True
    assert proximity_engine.calculate_proximity(content, ["missing"], 1, "WORDS", False) is False


def test_calculate_proximity_legal_terms(proximity_engine, sample_text):
    """Test proximity search with legal terminology."""
    # Terms in the same sentence
    assert proximity_engine.calculate_proximity(sample_text, ["breach", "contract"], 3, "WORDS", False) is True
    
    # Terms in the same paragraph but not close enough for the word distance
    assert proximity_engine.calculate_proximity(
        sample_text, ["breach", "contract"], 1, "WORDS", False) is False
    assert proximity_engine.calculate_proximity(
        sample_text, ["breach", "contract"], 1, "PARAGRAPHS", False) is True
    
    # Terms in different paragraphs
    assert proximity_engine.calculate_proximity(
        sample_text, ["breach", "confidentiality"], 10, "WORDS", False) is False
    assert proximity_engine.calculate_proximity(
        sample_text, ["breach", "confidentiality"], 3, "PARAGRAPHS", False) is True
    
    # Terms that appear in order
    assert proximity_engine.calculate_proximity(
        sample_text, ["statute", "limitations"], 2, "WORDS", True) is True
    assert proximity_engine.calculate_proximity(
        sample_text, ["limitations", "statute"], 2, "WORDS", True) is False


def test_find_proximity_matches(proximity_engine, sample_text):
    """Test finding occurrences of terms in proximity."""
    # Find matches for "breach" and "contract"
    matches = proximity_engine.find_proximity_matches(sample_text, ["breach", "contract"], 3, "WORDS", False)
    
    assert len(matches) > 0
    assert "breach" in matches[0]["content"]
    assert "contract" in matches[0]["content"]
    
    # Find matches for "statute" and "limitations" in order
    matches = proximity_engine.find_proximity_matches(sample_text, ["statute", "limitations"], 2, "WORDS", True)
    
    assert len(matches) > 0
    assert "statute" in matches[0]["content"]
    assert "limitations" in matches[0]["content"]
    
    # Find matches for terms in the same paragraph
    matches = proximity_engine.find_proximity_matches(sample_text, ["breach", "liable"], 1, "PARAGRAPHS", False)
    
    assert len(matches) > 0
    assert "breach" in matches[0]["content"]
    assert "liable" in matches[0]["content"]


def test_highlight_proximity_matches(proximity_engine, sample_text):
    """Test highlighting occurrences of terms in proximity."""
    # Highlight "breach" and "contract"
    highlighted = proximity_engine.highlight_proximity_matches(
        sample_text, ["breach", "contract"], 3, "WORDS", False)
    
    assert "[HIGHLIGHT]" in highlighted
    assert "[/HIGHLIGHT]" in highlighted
    assert "breach" in highlighted
    assert "contract" in highlighted
    
    # Highlight a paragraph
    highlighted = proximity_engine.highlight_proximity_matches(
        sample_text, ["breach", "liable"], 1, "PARAGRAPHS", False)
    
    assert "[HIGHLIGHT]" in highlighted
    assert "[/HIGHLIGHT]" in highlighted
    assert "breach" in highlighted
    assert "liable" in highlighted