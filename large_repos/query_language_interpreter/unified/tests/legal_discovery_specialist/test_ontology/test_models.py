"""Tests for the ontology models."""

import pytest
from legal_discovery_interpreter.ontology.models import (
    TermRelationType,
    TermRelation,
    LegalTerm,
    LegalOntology,
    OntologyCollection
)


def test_term_relation():
    """Test creating a term relation."""
    relation = TermRelation(
        from_term="contract",
        to_term="agreement",
        relation_type=TermRelationType.SYNONYM,
        confidence=0.9,
        source="legal dictionary"
    )
    
    assert relation.from_term == "contract"
    assert relation.to_term == "agreement"
    assert relation.relation_type == TermRelationType.SYNONYM
    assert relation.confidence == 0.9
    assert relation.source == "legal dictionary"


def test_legal_term():
    """Test creating a legal term."""
    term = LegalTerm(
        term="contract",
        definition="A legally binding agreement between parties",
        practice_areas=["commercial law", "contract law"],
        jurisdictions=["US", "UK"]
    )
    
    assert term.term == "contract"
    assert term.definition == "A legally binding agreement between parties"
    assert term.practice_areas == ["commercial law", "contract law"]
    assert term.jurisdictions == ["US", "UK"]
    assert len(term.relations) == 0
    
    # Add a relation
    relation = TermRelation(
        from_term="contract",
        to_term="agreement",
        relation_type=TermRelationType.SYNONYM
    )
    
    term.relations.append(relation)
    
    assert len(term.relations) == 1
    assert term.relations[0].from_term == "contract"
    assert term.relations[0].to_term == "agreement"


def test_legal_ontology():
    """Test creating and using a legal ontology."""
    ontology = LegalOntology(
        ontology_id="contracts",
        name="Contract Law Ontology",
        description="Ontology for contract law terminology",
        version="1.0",
        practice_area="contract law",
        jurisdiction="US"
    )
    
    assert ontology.ontology_id == "contracts"
    assert ontology.name == "Contract Law Ontology"
    assert ontology.description == "Ontology for contract law terminology"
    assert ontology.version == "1.0"
    assert ontology.practice_area == "contract law"
    assert ontology.jurisdiction == "US"
    assert len(ontology.terms) == 0
    
    # Add terms
    term1 = LegalTerm(term="contract")
    term2 = LegalTerm(term="agreement")
    
    ontology.add_term(term1)
    ontology.add_term(term2)
    
    assert len(ontology.terms) == 2
    assert "contract" in ontology.terms
    assert "agreement" in ontology.terms
    
    # Add a term by string
    ontology.add_term("consideration")
    
    assert len(ontology.terms) == 3
    assert "consideration" in ontology.terms
    assert isinstance(ontology.terms["consideration"], LegalTerm)
    
    # Get a term
    term = ontology.get_term("contract")
    
    assert term is not None
    assert term.term == "contract"
    
    # Case insensitive get
    term = ontology.get_term("CONTRACT")
    
    assert term is not None
    assert term.term == "contract"
    
    # Add a relation
    ontology.add_relation(
        from_term="contract",
        to_term="agreement",
        relation_type=TermRelationType.SYNONYM,
        confidence=0.9,
        source="legal dictionary"
    )
    
    # Get related terms
    related_terms = ontology.get_related_terms("contract")
    
    assert len(related_terms) == 1
    assert "agreement" in related_terms
    assert len(related_terms["agreement"]) == 1
    assert related_terms["agreement"][0].relation_type == TermRelationType.SYNONYM
    
    # Count terms
    assert ontology.count_terms() == 3


def test_ontology_collection():
    """Test creating and using an ontology collection."""
    collection = OntologyCollection()
    
    assert len(collection.ontologies) == 0
    
    # Create ontologies
    ontology1 = LegalOntology(
        ontology_id="contracts",
        name="Contract Law Ontology",
        version="1.0",
        practice_area="contract law"
    )
    
    ontology2 = LegalOntology(
        ontology_id="litigation",
        name="Litigation Ontology",
        version="1.0",
        practice_area="litigation"
    )
    
    # Add ontologies
    collection.add_ontology(ontology1)
    collection.add_ontology(ontology2)
    
    assert len(collection.ontologies) == 2
    assert "contracts" in collection.ontologies
    assert "litigation" in collection.ontologies
    
    # Get an ontology
    ontology = collection.get_ontology("contracts")
    
    assert ontology is not None
    assert ontology.ontology_id == "contracts"
    assert ontology.name == "Contract Law Ontology"
    
    # Get ontologies by practice area
    practice_ontologies = collection.get_ontology_by_practice_area("contract law")
    
    assert len(practice_ontologies) == 1
    assert practice_ontologies[0].ontology_id == "contracts"
    
    # Get ontologies by jurisdiction
    jurisdiction_ontologies = collection.get_ontology_by_jurisdiction("US")
    
    assert len(jurisdiction_ontologies) == 0  # No jurisdictions set