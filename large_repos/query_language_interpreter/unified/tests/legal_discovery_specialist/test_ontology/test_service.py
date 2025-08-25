"""Tests for the ontology service."""

import pytest
import tempfile
import os
import json
from legal_discovery_interpreter.ontology.models import (
    TermRelationType,
    TermRelation,
    LegalTerm,
    LegalOntology
)
from legal_discovery_interpreter.ontology.service import OntologyService


@pytest.fixture
def ontology_service():
    """Create a sample ontology service for testing."""
    return OntologyService()


@pytest.fixture
def sample_ontology_file():
    """Create a sample ontology file for testing."""
    ontology_data = {
        "ontology_id": "contracts",
        "name": "Contract Law Ontology",
        "description": "Ontology for contract law terminology",
        "version": "1.0",
        "practice_area": "contract law",
        "jurisdiction": "US",
        "terms": {
            "contract": {
                "term": "contract",
                "definition": "A legally binding agreement between parties",
                "practice_areas": ["commercial law", "contract law"],
                "jurisdictions": ["US", "UK"],
                "relations": [
                    {
                        "from_term": "contract",
                        "to_term": "agreement",
                        "relation_type": "synonym",
                        "confidence": 0.9,
                        "source": "legal dictionary"
                    }
                ]
            },
            "agreement": {
                "term": "agreement",
                "definition": "A mutual understanding between parties",
                "practice_areas": ["commercial law", "contract law"],
                "jurisdictions": ["US", "UK"],
                "relations": []
            }
        }
    }
    
    # Create a temporary file
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(ontology_data, f)
        yield path
    finally:
        os.remove(path)


def test_ontology_service_initialization(ontology_service):
    """Test initializing an ontology service."""
    assert ontology_service.ontology_collection is not None
    assert len(ontology_service.ontology_collection.ontologies) == 0
    assert isinstance(ontology_service._term_expansion_cache, dict)


def test_create_simple_ontology(ontology_service):
    """Test creating a simple ontology from a term mapping."""
    term_mapping = {
        "liability": {"indemnification", "responsibility", "obligation"},
        "settlement": {"resolution", "agreement", "compromise"},
        "litigation": {"lawsuit", "legal action", "court case"}
    }
    
    ontology = ontology_service.create_simple_ontology(
        ontology_id="simple",
        name="Simple Legal Ontology",
        term_mapping=term_mapping
    )
    
    assert ontology.ontology_id == "simple"
    assert ontology.name == "Simple Legal Ontology"
    assert ontology.version == "1.0"
    assert len(ontology.terms) == 3
    
    # Check that the ontology was added to the service
    assert "simple" in ontology_service.ontology_collection.ontologies
    
    # Check term relations
    liability_term = ontology.get_term("liability")
    assert liability_term is not None
    assert len(liability_term.relations) == 3
    
    # Check that related terms are correctly set
    related_terms = set(rel.to_term for rel in liability_term.relations)
    assert "indemnification" in related_terms
    assert "responsibility" in related_terms
    assert "obligation" in related_terms


def test_load_ontology_from_file(ontology_service, sample_ontology_file):
    """Test loading an ontology from a file."""
    ontology = ontology_service.load_ontology_from_file(sample_ontology_file)
    
    assert ontology is not None
    assert ontology.ontology_id == "contracts"
    assert ontology.name == "Contract Law Ontology"
    assert ontology.description == "Ontology for contract law terminology"
    assert len(ontology.terms) == 2
    
    # Check that the ontology was added to the service
    assert "contracts" in ontology_service.ontology_collection.ontologies
    
    # Check term relations
    contract_term = ontology.get_term("contract")
    assert contract_term is not None
    assert len(contract_term.relations) == 1
    assert contract_term.relations[0].to_term == "agreement"


def test_expand_terms(ontology_service):
    """Test expanding search terms using ontologies."""
    # Create a simple ontology
    term_mapping = {
        "liability": {"indemnification", "responsibility", "obligation"},
        "settlement": {"resolution", "agreement", "compromise"},
        "litigation": {"lawsuit", "legal action", "court case"}
    }
    
    ontology_service.create_simple_ontology(
        ontology_id="simple",
        name="Simple Legal Ontology",
        term_mapping=term_mapping
    )
    
    # Test expanding a term
    expanded_terms = ontology_service.expand_terms("liability")
    
    assert len(expanded_terms) == 4  # Original term + 3 related terms
    assert "liability" in expanded_terms
    assert "indemnification" in expanded_terms
    assert "responsibility" in expanded_terms
    assert "obligation" in expanded_terms
    
    # Test caching
    # The expansion should be cached, so the second call should be faster
    expanded_terms_again = ontology_service.expand_terms("liability")
    
    assert expanded_terms == expanded_terms_again
    
    # Test expanding a term that doesn't exist
    expanded_terms = ontology_service.expand_terms("nonexistent")
    
    assert len(expanded_terms) == 1  # Only the original term
    assert "nonexistent" in expanded_terms


def test_expand_query(ontology_service):
    """Test expanding a query string using ontologies."""
    # Create a simple ontology
    term_mapping = {
        "liability": {"indemnification", "responsibility", "obligation"},
        "settlement": {"resolution", "agreement", "compromise"},
        "litigation": {"lawsuit", "legal action", "court case"}
    }
    
    ontology_service.create_simple_ontology(
        ontology_id="simple",
        name="Simple Legal Ontology",
        term_mapping=term_mapping
    )
    
    # Test expanding a query
    expanded_query = ontology_service.expand_query("liability AND settlement")
    
    # Check that the query was expanded properly
    assert "(" in expanded_query  # Should have grouping
    assert "OR" in expanded_query  # Should have OR operators
    assert "AND" in expanded_query  # Should preserve the original AND
    
    # The expanded query should contain all related terms
    assert "liability" in expanded_query
    assert "indemnification" in expanded_query
    assert "settlement" in expanded_query
    assert "agreement" in expanded_query


def test_get_related_documents(ontology_service):
    """Test finding documents related to a term using ontology-based expansion."""
    # Create a simple ontology
    term_mapping = {
        "liability": {"indemnification", "responsibility", "obligation"},
        "settlement": {"resolution", "agreement", "compromise"},
        "litigation": {"lawsuit", "legal action", "court case"}
    }
    
    ontology_service.create_simple_ontology(
        ontology_id="simple",
        name="Simple Legal Ontology",
        term_mapping=term_mapping
    )
    
    # Create sample documents
    documents = [
        {
            "id": "doc1",
            "content": "This document discusses liability and indemnification clauses."
        },
        {
            "id": "doc2",
            "content": "This document discusses responsibility for damages."
        },
        {
            "id": "doc3",
            "content": "This document discusses settlement of claims."
        },
        {
            "id": "doc4",
            "content": "This document does not contain any relevant terms."
        }
    ]
    
    # Test finding documents related to "liability"
    related_docs = ontology_service.get_related_documents("liability", documents)
    
    assert len(related_docs) == 2
    assert related_docs[0]["id"] == "doc1"  # Contains "liability"
    assert related_docs[1]["id"] == "doc2"  # Contains "responsibility"