"""Service for legal term ontology integration."""

import json
import os
from typing import Dict, List, Set, Optional, Union, Any
import logging
import asyncio

# Common library imports
from common.services.base_services import BaseService, ServiceConfig
from common.core.base_models import ExecutionContext
from common.core.exceptions import ServiceError
from common.utils.logging import get_logger

# Legal-specific imports
from .models import (
    LegalOntology,
    LegalTerm,
    TermRelation,
    TermRelationType,
    OntologyCollection
)


class OntologyService(BaseService):
    """Service for legal term ontology integration.
    
    This service provides functionality for loading, managing, and using
    legal term ontologies to expand searches with specialized terminology.
    """
    
    def __init__(self, config: Optional[ServiceConfig] = None, logger=None):
        """Initialize the ontology service.
        
        Args:
            config: Service configuration
            logger: Logger instance
        """
        # Initialize with default config if none provided
        if config is None:
            config = ServiceConfig(
                service_name="ontology_service",
                service_type="service",
                enabled=True,
                config={}
            )
        
        super().__init__(config)
        
        self.logger = logger or get_logger(__name__)
        self.ontology_collection = OntologyCollection()
        
        # Cache for expanded terms to improve performance
        self._term_expansion_cache: Dict[str, Set[str]] = {}
    
    def load_ontology_from_file(self, file_path: str) -> Optional[LegalOntology]:
        """Load an ontology from a JSON file.
        
        Args:
            file_path: Path to the ontology file
            
        Returns:
            The loaded ontology, or None if loading failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                ontology_data = json.load(f)
            
            ontology = LegalOntology.parse_obj(ontology_data)
            self.ontology_collection.add_ontology(ontology)
            self.logger.info(f"Loaded ontology {ontology.ontology_id} with {ontology.count_terms()} terms")
            
            # Clear the expansion cache when loading new ontologies
            self._term_expansion_cache = {}
            
            return ontology
        except Exception as e:
            self.logger.error(f"Failed to load ontology from {file_path}: {e}")
            return None
    
    def load_ontology_from_dict(self, ontology_data: Dict[str, Any]) -> Optional[LegalOntology]:
        """Load an ontology from a dictionary.
        
        Args:
            ontology_data: Ontology data as a dictionary
            
        Returns:
            The loaded ontology, or None if loading failed
        """
        try:
            ontology = LegalOntology.parse_obj(ontology_data)
            self.ontology_collection.add_ontology(ontology)
            self.logger.info(f"Loaded ontology {ontology.ontology_id} with {ontology.count_terms()} terms")
            
            # Clear the expansion cache when loading new ontologies
            self._term_expansion_cache = {}
            
            return ontology
        except Exception as e:
            self.logger.error(f"Failed to load ontology from dictionary: {e}")
            return None
    
    def load_ontologies_from_directory(self, directory_path: str) -> int:
        """Load all ontology files from a directory.
        
        Args:
            directory_path: Path to the directory containing ontology files
            
        Returns:
            Number of successfully loaded ontologies
        """
        loaded_count = 0
        
        try:
            for filename in os.listdir(directory_path):
                if filename.endswith('.json'):
                    file_path = os.path.join(directory_path, filename)
                    if self.load_ontology_from_file(file_path):
                        loaded_count += 1
        except Exception as e:
            self.logger.error(f"Failed to load ontologies from directory {directory_path}: {e}")
        
        return loaded_count
    
    def create_simple_ontology(self, ontology_id: str, name: str, term_mapping: Dict[str, Set[str]],
                              version: str = "1.0") -> LegalOntology:
        """Create a simple ontology from a term mapping.
        
        Args:
            ontology_id: Unique identifier for the ontology
            name: Name of the ontology
            term_mapping: Mapping from terms to related terms
            version: Version of the ontology
            
        Returns:
            The created ontology
        """
        ontology = LegalOntology(
            ontology_id=ontology_id,
            name=name,
            version=version
        )
        
        for term, related_terms in term_mapping.items():
            legal_term = LegalTerm(term=term.lower())
            ontology.terms[term.lower()] = legal_term
            
            for related_term in related_terms:
                relation = TermRelation(
                    from_term=term.lower(),
                    to_term=related_term.lower(),
                    relation_type=TermRelationType.RELATED
                )
                legal_term.relations.append(relation)
        
        self.ontology_collection.add_ontology(ontology)
        
        # Clear the expansion cache when creating new ontologies
        self._term_expansion_cache = {}
        
        return ontology
    
    def expand_terms(self, term: str, max_expansion: int = 50, 
                    relation_types: Optional[List[TermRelationType]] = None,
                    min_confidence: float = 0.5) -> Set[str]:
        """Expand a search term using the loaded ontologies.
        
        Args:
            term: Term to expand
            max_expansion: Maximum number of expanded terms to return
            relation_types: Types of relationships to include (None for all)
            min_confidence: Minimum confidence for relationships
            
        Returns:
            Set of expanded terms, including the original term
        """
        term = term.lower()
        
        # Check the cache first
        cache_key = f"{term}_{max_expansion}_{'-'.join(rt.value for rt in relation_types) if relation_types else 'all'}_{min_confidence}"
        if cache_key in self._term_expansion_cache:
            return self._term_expansion_cache[cache_key]
        
        # Always include the original term
        expanded_terms = {term}
        
        # Expand the term using all ontologies
        for ontology in self.ontology_collection.ontologies.values():
            term_obj = ontology.get_term(term)
            if not term_obj:
                continue
            
            # Get related terms
            related_terms = ontology.get_related_terms(term, relation_types, min_confidence)
            
            # Add related terms to the expanded set
            for related_term in related_terms:
                expanded_terms.add(related_term.lower())
                
                # Stop if we've reached the maximum number of expanded terms
                if len(expanded_terms) >= max_expansion:
                    break
            
            # Stop if we've reached the maximum number of expanded terms
            if len(expanded_terms) >= max_expansion:
                break
        
        # Cache the result
        self._term_expansion_cache[cache_key] = expanded_terms
        
        return expanded_terms
    
    def expand_query(self, query: str, max_terms_per_expansion: int = 10) -> str:
        """Expand a query string using the loaded ontologies.
        
        Args:
            query: Query string to expand
            max_terms_per_expansion: Maximum number of expanded terms per original term
            
        Returns:
            Expanded query string
        """
        # This is a simplified implementation for demonstration purposes
        # A full implementation would need to parse the query properly
        
        terms = query.split()
        expanded_query_parts = []
        
        for term in terms:
            # Skip common operators and punctuation
            if term.upper() in ("AND", "OR", "NOT", "NEAR", "WITHIN") or term in ("(", ")", ",", ";"):
                expanded_query_parts.append(term)
                continue
            
            # Expand the term
            expanded_terms = self.expand_terms(term, max_expansion=max_terms_per_expansion)
            
            # Add the expanded terms to the query
            if len(expanded_terms) == 1:
                # If there's only one term (the original), just add it
                expanded_query_parts.append(term)
            else:
                # Otherwise, add the expanded terms as an OR group
                expanded_terms_str = " OR ".join(expanded_terms)
                expanded_query_parts.append(f"({expanded_terms_str})")
        
        return " ".join(expanded_query_parts)
    
    def get_related_documents(self, term: str, documents: List[Dict[str, Any]], 
                            content_field: str = "content", max_expansion: int = 20) -> List[Dict[str, Any]]:
        """Find documents related to a term using ontology-based expansion.
        
        Args:
            term: Term to search for
            documents: List of documents to search in
            content_field: Field in the documents containing the content to search
            max_expansion: Maximum number of expanded terms to use
            
        Returns:
            List of related documents
        """
        expanded_terms = self.expand_terms(term, max_expansion=max_expansion)
        
        related_documents = []
        for document in documents:
            content = document.get(content_field, "").lower()
            
            # Check if any expanded term is in the content
            if any(expanded_term in content for expanded_term in expanded_terms):
                related_documents.append(document)
        
        return related_documents
    
    # Implement BaseService abstract methods
    async def initialize(self) -> None:
        """Initialize the ontology service.
        
        Raises:
            ServiceError: If initialization fails
        """
        try:
            # Clear any existing data
            self.ontology_collection = OntologyCollection()
            self._term_expansion_cache.clear()
            
            # Load default ontologies if specified in config
            default_ontologies = self.config.config.get("default_ontologies", [])
            for ontology_path in default_ontologies:
                if os.path.exists(ontology_path):
                    self.load_ontology_from_file(ontology_path)
                else:
                    self.logger.warning(f"Default ontology file not found: {ontology_path}")
            
            self.logger.info("Ontology service initialized successfully")
        except Exception as e:
            raise ServiceError(f"Failed to initialize ontology service: {str(e)}", 
                             service_name=self.config.service_name, operation="initialize")
    
    async def shutdown(self) -> None:
        """Shutdown the ontology service.
        
        Raises:
            ServiceError: If shutdown fails
        """
        try:
            # Clear resources
            self.ontology_collection = OntologyCollection()
            self._term_expansion_cache.clear()
            
            self.logger.info("Ontology service shutdown successfully")
        except Exception as e:
            raise ServiceError(f"Failed to shutdown ontology service: {str(e)}", 
                             service_name=self.config.service_name, operation="shutdown")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the ontology service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            ontologies_count = len(self.ontology_collection.ontologies)
            total_terms = sum(len(ontology.terms) for ontology in self.ontology_collection.ontologies.values())
            total_relations = sum(len(ontology.relations) for ontology in self.ontology_collection.ontologies.values())
            
            return {
                "healthy": True,
                "ontologies_count": ontologies_count,
                "total_terms": total_terms,
                "total_relations": total_relations,
                "cache_size": len(self._term_expansion_cache)
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }