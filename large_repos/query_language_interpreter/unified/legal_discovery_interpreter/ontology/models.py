"""Models for legal term ontology integration."""

from typing import Dict, List, Set, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


class TermRelationType(str, Enum):
    """Types of relationships between legal terms."""
    
    SYNONYM = "synonym"
    ABBREVIATION = "abbreviation"
    BROADER = "broader"
    NARROWER = "narrower"
    RELATED = "related"
    JARGON = "jargon"
    DEFINITION = "definition"


class TermRelation(BaseModel):
    """Relationship between legal terms."""
    
    from_term: str = Field(..., description="Source term")
    to_term: str = Field(..., description="Target term")
    relation_type: TermRelationType = Field(..., description="Type of relationship")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in the relationship")
    source: Optional[str] = Field(None, description="Source of the relationship")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"


class LegalTerm(BaseModel):
    """Model for a legal term with its relationships."""
    
    term: str = Field(..., description="The legal term")
    definition: Optional[str] = Field(None, description="Definition of the term")
    practice_areas: List[str] = Field(default_factory=list, description="Practice areas where the term is used")
    jurisdictions: List[str] = Field(default_factory=list, description="Jurisdictions where the term is used")
    relations: List[TermRelation] = Field(default_factory=list, description="Relationships to other terms")
    
    class Config:
        """Pydantic model configuration."""
        
        extra = "allow"


class LegalOntology(BaseModel):
    """A legal term ontology mapping common concepts to specialized terminology."""
    
    ontology_id: str = Field(..., description="Unique identifier for the ontology")
    name: str = Field(..., description="Name of the ontology")
    description: Optional[str] = Field(None, description="Description of the ontology")
    version: str = Field(..., description="Version of the ontology")
    practice_area: Optional[str] = Field(None, description="Primary practice area for the ontology")
    jurisdiction: Optional[str] = Field(None, description="Primary jurisdiction for the ontology")
    terms: Dict[str, LegalTerm] = Field(default_factory=dict, description="Terms in the ontology")
    
    def add_term(self, term: Union[LegalTerm, str]) -> None:
        """Add a term to the ontology.
        
        Args:
            term: Term to add
        """
        if isinstance(term, str):
            term = LegalTerm(term=term)
        
        self.terms[term.term] = term
    
    def get_term(self, term: str) -> Optional[LegalTerm]:
        """Get a term from the ontology.
        
        Args:
            term: Term to get
            
        Returns:
            The term, or None if not found
        """
        return self.terms.get(term.lower())
    
    def add_relation(self, from_term: str, to_term: str, relation_type: TermRelationType, 
                     confidence: float = 1.0, source: Optional[str] = None) -> None:
        """Add a relationship between terms.
        
        Args:
            from_term: Source term
            to_term: Target term
            relation_type: Type of relationship
            confidence: Confidence in the relationship
            source: Source of the relationship
        """
        if from_term not in self.terms:
            self.add_term(from_term)
        
        if to_term not in self.terms:
            self.add_term(to_term)
        
        relation = TermRelation(
            from_term=from_term,
            to_term=to_term,
            relation_type=relation_type,
            confidence=confidence,
            source=source
        )
        
        self.terms[from_term].relations.append(relation)
    
    def get_related_terms(self, term: str, relation_types: Optional[List[TermRelationType]] = None,
                          min_confidence: float = 0.0) -> Dict[str, List[TermRelation]]:
        """Get terms related to a given term.
        
        Args:
            term: Term to get related terms for
            relation_types: Types of relationships to include (None for all)
            min_confidence: Minimum confidence for relationships
            
        Returns:
            Dictionary mapping related terms to their relationships
        """
        term_obj = self.get_term(term)
        if not term_obj:
            return {}
        
        related_terms = {}
        for relation in term_obj.relations:
            if relation.confidence < min_confidence:
                continue
            
            if relation_types and relation.relation_type not in relation_types:
                continue
            
            if relation.to_term not in related_terms:
                related_terms[relation.to_term] = []
            
            related_terms[relation.to_term].append(relation)
        
        return related_terms
    
    def count_terms(self) -> int:
        """Count the number of terms in the ontology.
        
        Returns:
            Number of terms
        """
        return len(self.terms)


class OntologyCollection(BaseModel):
    """A collection of legal ontologies."""
    
    ontologies: Dict[str, LegalOntology] = Field(default_factory=dict, description="Ontologies in the collection")
    
    def add_ontology(self, ontology: LegalOntology) -> None:
        """Add an ontology to the collection.
        
        Args:
            ontology: Ontology to add
        """
        self.ontologies[ontology.ontology_id] = ontology
    
    def get_ontology(self, ontology_id: str) -> Optional[LegalOntology]:
        """Get an ontology from the collection.
        
        Args:
            ontology_id: ID of the ontology to get
            
        Returns:
            The ontology, or None if not found
        """
        return self.ontologies.get(ontology_id)
    
    def get_ontology_by_practice_area(self, practice_area: str) -> List[LegalOntology]:
        """Get ontologies for a specific practice area.
        
        Args:
            practice_area: Practice area to filter by
            
        Returns:
            List of matching ontologies
        """
        return [
            ontology for ontology in self.ontologies.values()
            if ontology.practice_area and ontology.practice_area.lower() == practice_area.lower()
        ]
    
    def get_ontology_by_jurisdiction(self, jurisdiction: str) -> List[LegalOntology]:
        """Get ontologies for a specific jurisdiction.
        
        Args:
            jurisdiction: Jurisdiction to filter by
            
        Returns:
            List of matching ontologies
        """
        return [
            ontology for ontology in self.ontologies.values()
            if ontology.jurisdiction and ontology.jurisdiction.lower() == jurisdiction.lower()
        ]