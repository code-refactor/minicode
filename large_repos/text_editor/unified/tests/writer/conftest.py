"""Test configuration and shared fixtures."""

import pytest
from unittest.mock import MagicMock

# Add any custom configuration for pytest here


@pytest.fixture(autouse=True)
def mock_spacy(monkeypatch):
    """Mock spaCy to avoid external dependencies during tests."""
    # Mock spacy.load to return a mock NLP model
    nlp_mock = MagicMock()
    doc_mock = MagicMock()
    
    # Mock entities and tokens for NER
    entities = [
        MagicMock(text="Sarah", label_="PERSON"),
        MagicMock(text="John", label_="PERSON"),
        MagicMock(text="Emily", label_="PERSON"),
        MagicMock(text="Castle", label_="LOC")
    ]
    doc_mock.ents = entities
    
    # Mock tokens
    tokens = []
    for name in ["Sarah", "John", "Emily"]:
        token_mock = MagicMock()
        token_mock.is_alpha = True
        token_mock.is_title = True
        token_mock.pos_ = "PROPN"
        token_mock.text = name
        token_mock.head.pos_ = "PROPN"
        token_mock.head.subtree = [token_mock]
        tokens.append(token_mock)
    
    doc_mock.__iter__ = lambda self: iter(tokens)
    nlp_mock.return_value = doc_mock
    
    # Patch spacy.load
    spacy_mock = MagicMock()
    spacy_mock.load.return_value = nlp_mock
    monkeypatch.setattr("writer_text_editor.narrative.spacy", spacy_mock)


@pytest.fixture(autouse=True)
def mock_textstat(monkeypatch):
    """Mock textstat to avoid external dependencies during tests."""
    textstat_mock = MagicMock()
    
    # Mock reading level metrics to return reasonable values
    textstat_mock.flesch_kincaid_grade.return_value = 8.5
    textstat_mock.flesch_reading_ease.return_value = 70.5
    textstat_mock.gunning_fog.return_value = 10.2
    textstat_mock.smog_index.return_value = 9.8
    textstat_mock.automated_readability_index.return_value = 8.7
    textstat_mock.coleman_liau_index.return_value = 9.1
    textstat_mock.linsear_write_formula.return_value = 8.9
    textstat_mock.dale_chall_readability_score.return_value = 7.8
    
    monkeypatch.setattr("writer_text_editor.statistics.textstat", textstat_mock)