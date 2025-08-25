"""Document analyzer for the legal discovery interpreter."""

import hashlib
import re
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import logging
import asyncio

# Common library imports
from common.services.base_services import BaseAnalyzerService, ServiceConfig
from common.core.base_models import BaseDocument, ExecutionContext
from common.core.exceptions import ServiceError
from common.utils.logging import get_logger

# Legal-specific imports
from ..core.document import Document, DocumentCollection
from .proximity import ProximitySearchEngine


class DocumentAnalyzer(BaseAnalyzerService):
    """Analyzer for legal documents.
    
    This analyzer provides functionality for document analysis, including
    full-text indexing, proximity detection, and content-based similarity
    assessment.
    """
    
    def __init__(self, proximity_engine=None, config: Optional[ServiceConfig] = None, logger=None):
        """Initialize the document analyzer.
        
        Args:
            proximity_engine: ProximitySearchEngine instance
            config: Service configuration
            logger: Logger instance
        """
        # Initialize with default config if none provided
        if config is None:
            config = ServiceConfig(
                service_name="document_analyzer",
                service_type="analyzer",
                enabled=True,
                config={}
            )
        
        super().__init__(config)
        
        self.logger = logger or get_logger(__name__)
        self.proximity_engine = proximity_engine or ProximitySearchEngine(logger=self.logger)
        
        # Document index for full-text search
        self.document_index: Dict[str, Dict[str, int]] = {}
        # Inverted index for term lookup
        self.inverted_index: Dict[str, Set[str]] = {}
        # Document similarity cache
        self.similarity_cache: Dict[str, Dict[str, float]] = {}
    
    def index_document(self, document: Document) -> None:
        """Index a document for search.
        
        Args:
            document: Document to index
        """
        doc_id = document.metadata.document_id
        
        try:
            # Create a term frequency map for the document
            content = document.content.lower()
            terms = re.findall(r'\b\w+\b', content)
            
            term_freq = {}
            for term in terms:
                if term not in term_freq:
                    term_freq[term] = 0
                term_freq[term] += 1
            
            # Add to the document index
            self.document_index[doc_id] = term_freq
            
            # Update the inverted index
            for term in term_freq:
                if term not in self.inverted_index:
                    self.inverted_index[term] = set()
                self.inverted_index[term].add(doc_id)
            
            self.logger.debug(f"Indexed document {doc_id} with {len(term_freq)} unique terms")
        except Exception as e:
            self.logger.error(f"Error indexing document {doc_id}: {e}")
    
    def index_collection(self, collection: DocumentCollection) -> None:
        """Index a collection of documents.
        
        Args:
            collection: Document collection to index
        """
        for doc_id, document in collection.documents.items():
            self.index_document(document)
        
        self.logger.info(f"Indexed {len(collection.documents)} documents with {len(self.inverted_index)} unique terms")
    
    def search(self, query: str) -> List[str]:
        """Search for documents matching a query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching document IDs
        """
        query = query.lower()
        terms = re.findall(r'\b\w+\b', query)
        
        # Find documents containing all query terms
        matching_docs = None
        for term in terms:
            if term in self.inverted_index:
                if matching_docs is None:
                    matching_docs = self.inverted_index[term].copy()
                else:
                    matching_docs.intersection_update(self.inverted_index[term])
            else:
                # If any term is not in the index, return an empty result
                return []
        
        return list(matching_docs) if matching_docs else []
    
    def calculate_proximity(self, content: str, terms: List[str], 
                          distance: int, unit: str, ordered: bool = False) -> bool:
        """Calculate if terms appear within a specified distance of each other.
        
        Args:
            content: Document content
            terms: Terms to search for
            distance: Maximum distance between terms
            unit: Unit of distance measurement (WORDS, SENTENCES, PARAGRAPHS)
            ordered: Whether terms must appear in the specified order
            
        Returns:
            True if terms are within the specified distance, False otherwise
        """
        return self.proximity_engine.calculate_proximity(content, terms, distance, unit, ordered)
    
    def find_proximity_matches(self, content: str, terms: List[str], 
                             distance: int, unit: str, ordered: bool = False) -> List[Dict[str, Any]]:
        """Find occurrences where terms appear within a specified distance.
        
        Args:
            content: Document content
            terms: Terms to search for
            distance: Maximum distance between terms
            unit: Unit of distance measurement (WORDS, SENTENCES, PARAGRAPHS)
            ordered: Whether terms must appear in the specified order
            
        Returns:
            List of match information dictionaries
        """
        return self.proximity_engine.find_proximity_matches(content, terms, distance, unit, ordered)
    
    def search_proximity(self, collection: DocumentCollection, terms: List[str], 
                       distance: int, unit: str, ordered: bool = False) -> List[str]:
        """Search for documents with terms in proximity.
        
        Args:
            collection: Document collection to search
            terms: Terms to search for
            distance: Maximum distance between terms
            unit: Unit of distance measurement (WORDS, SENTENCES, PARAGRAPHS)
            ordered: Whether terms must appear in the specified order
            
        Returns:
            List of matching document IDs
        """
        matching_docs = []
        
        for doc_id, document in collection.documents.items():
            content = document.content
            
            if self.calculate_proximity(content, terms, distance, unit, ordered):
                matching_docs.append(doc_id)
        
        return matching_docs
    
    def calculate_similarity(self, doc_id1: str, doc_id2: str) -> float:
        """Calculate the similarity between two documents.
        
        Args:
            doc_id1: First document ID
            doc_id2: Second document ID
            
        Returns:
            Similarity score between 0 and 1
        """
        # Check if the result is already cached
        if doc_id1 in self.similarity_cache and doc_id2 in self.similarity_cache[doc_id1]:
            return self.similarity_cache[doc_id1][doc_id2]
        
        if doc_id2 in self.similarity_cache and doc_id1 in self.similarity_cache[doc_id2]:
            return self.similarity_cache[doc_id2][doc_id1]
        
        # Make sure both documents are indexed
        if doc_id1 not in self.document_index or doc_id2 not in self.document_index:
            return 0.0
        
        # Calculate cosine similarity between term frequency vectors
        try:
            terms1 = set(self.document_index[doc_id1].keys())
            terms2 = set(self.document_index[doc_id2].keys())
            
            common_terms = terms1.intersection(terms2)
            
            if not common_terms:
                similarity = 0.0
            else:
                # Calculate dot product
                dot_product = sum(
                    self.document_index[doc_id1][term] * self.document_index[doc_id2][term]
                    for term in common_terms
                )
                
                # Calculate magnitudes
                magnitude1 = sum(freq ** 2 for freq in self.document_index[doc_id1].values()) ** 0.5
                magnitude2 = sum(freq ** 2 for freq in self.document_index[doc_id2].values()) ** 0.5
                
                # Calculate cosine similarity
                similarity = dot_product / (magnitude1 * magnitude2) if magnitude1 * magnitude2 > 0 else 0.0
            
            # Cache the result
            if doc_id1 not in self.similarity_cache:
                self.similarity_cache[doc_id1] = {}
            
            self.similarity_cache[doc_id1][doc_id2] = similarity
            
            return similarity
        except Exception as e:
            self.logger.error(f"Error calculating similarity between {doc_id1} and {doc_id2}: {e}")
            return 0.0
    
    def find_similar_documents(self, doc_id: str, collection: DocumentCollection, 
                            threshold: float = 0.7, limit: int = 10) -> List[Tuple[str, float]]:
        """Find documents similar to a given document.
        
        Args:
            doc_id: Document ID to find similar documents for
            collection: Document collection to search
            threshold: Minimum similarity score threshold
            limit: Maximum number of results to return
            
        Returns:
            List of tuples with document ID and similarity score
        """
        if doc_id not in self.document_index:
            return []
        
        similarities = []
        for other_id in collection.documents:
            if other_id == doc_id:
                continue
            
            similarity = self.calculate_similarity(doc_id, other_id)
            if similarity >= threshold:
                similarities.append((other_id, similarity))
        
        # Sort by similarity score in descending order
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:limit]
    
    def extract_metadata(self, document: Document) -> Dict[str, Any]:
        """Extract metadata from a document.
        
        Args:
            document: Document to extract metadata from
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}
        
        # Extract basic metadata
        metadata['document_id'] = document.metadata.document_id
        metadata['title'] = document.metadata.title
        metadata['document_type'] = document.metadata.document_type
        metadata['date_created'] = document.metadata.date_created
        
        # Generate a content hash for integrity verification
        content_hash = hashlib.sha256(document.content.encode()).hexdigest()
        metadata['content_hash'] = content_hash
        
        # Extract term statistics
        if document.metadata.document_id in self.document_index:
            term_counts = self.document_index[document.metadata.document_id]
            metadata['term_count'] = sum(term_counts.values())
            metadata['unique_term_count'] = len(term_counts)
        
        return metadata
    
    def classify_content(self, content: str) -> Dict[str, float]:
        """Classify document content by type.
        
        Args:
            content: Document content
            
        Returns:
            Dictionary with content type confidence scores
        """
        # This is a placeholder implementation
        # A real implementation would use machine learning models for classification
        
        content = content.lower()
        
        # Simple rule-based classification
        classifications = {
            'contract': 0.0,
            'email': 0.0,
            'memo': 0.0,
            'report': 0.0,
            'letter': 0.0
        }
        
        # Contract indicators
        contract_indicators = [
            'agreement', 'contract', 'party', 'parties', 'hereby', 'terms',
            'conditions', 'clause', 'section', 'provisions', 'shall'
        ]
        
        # Email indicators
        email_indicators = [
            'from:', 'to:', 'cc:', 'bcc:', 'subject:', 'sent:',
            'forwarded', 'replied', 'attachment', 'original message'
        ]
        
        # Memo indicators
        memo_indicators = [
            'memorandum', 'memo', 're:', 'reference:', 'date:',
            'subject matter', 'confidential'
        ]
        
        # Report indicators
        report_indicators = [
            'report', 'analysis', 'findings', 'conclusion', 'summary',
            'recommendation', 'examined', 'investigated'
        ]
        
        # Letter indicators
        letter_indicators = [
            'dear', 'sincerely', 'regards', 'yours truly', 'respectfully',
            'address', 'letterhead'
        ]
        
        # Count occurrences of indicators
        for indicator in contract_indicators:
            if indicator in content:
                classifications['contract'] += 0.1
        
        for indicator in email_indicators:
            if indicator in content:
                classifications['email'] += 0.1
        
        for indicator in memo_indicators:
            if indicator in content:
                classifications['memo'] += 0.1
        
        for indicator in report_indicators:
            if indicator in content:
                classifications['report'] += 0.1
        
        for indicator in letter_indicators:
            if indicator in content:
                classifications['letter'] += 0.1
        
        # Normalize scores to a maximum of 1.0
        max_score = max(classifications.values())
        if max_score > 1.0:
            for content_type in classifications:
                classifications[content_type] /= max_score
        
        return classifications
    
    # Implement BaseAnalyzerService abstract methods
    async def initialize(self) -> None:
        """Initialize the document analyzer service.
        
        Raises:
            ServiceError: If initialization fails
        """
        try:
            # Initialize proximity engine if it has an initialization method
            if hasattr(self.proximity_engine, 'initialize'):
                await self.proximity_engine.initialize()
            
            # Clear indexes and caches
            self.document_index.clear()
            self.inverted_index.clear()
            self.similarity_cache.clear()
            
            self.logger.info("Document analyzer service initialized successfully")
        except Exception as e:
            raise ServiceError(f"Failed to initialize document analyzer: {str(e)}", 
                             service_name=self.config.service_name, operation="initialize")
    
    async def shutdown(self) -> None:
        """Shutdown the document analyzer service.
        
        Raises:
            ServiceError: If shutdown fails
        """
        try:
            # Shutdown proximity engine if it has a shutdown method
            if hasattr(self.proximity_engine, 'shutdown'):
                await self.proximity_engine.shutdown()
            
            # Clear resources
            self.document_index.clear()
            self.inverted_index.clear()
            self.similarity_cache.clear()
            
            self.logger.info("Document analyzer service shutdown successfully")
        except Exception as e:
            raise ServiceError(f"Failed to shutdown document analyzer: {str(e)}", 
                             service_name=self.config.service_name, operation="shutdown")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the document analyzer service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            return {
                "healthy": True,
                "indexed_documents": len(self.document_index),
                "inverted_index_terms": len(self.inverted_index),
                "similarity_cache_entries": len(self.similarity_cache),
                "proximity_engine_available": self.proximity_engine is not None
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def analyze(
        self,
        data: Any,
        analysis_type: str,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Analyze document data.
        
        Args:
            data: Data to analyze (Document, DocumentCollection, or content string)
            analysis_type: Type of analysis ('index', 'similarity', 'classify', 'proximity')
            context: Optional execution context
            
        Returns:
            Analysis results
        """
        try:
            if analysis_type == "index":
                if isinstance(data, Document):
                    self.index_document(data)
                    return {"status": "indexed", "document_id": data.metadata.document_id}
                elif isinstance(data, DocumentCollection):
                    indexed_count = 0
                    for doc in data.documents.values():
                        self.index_document(doc)
                        indexed_count += 1
                    return {"status": "indexed", "document_count": indexed_count}
                else:
                    return {"error": "Data must be a Document or DocumentCollection for indexing"}
            
            elif analysis_type == "similarity":
                if isinstance(data, dict) and "doc_id1" in data and "doc_id2" in data:
                    similarity = self.calculate_similarity(data["doc_id1"], data["doc_id2"])
                    return {"similarity_score": similarity, "doc_id1": data["doc_id1"], "doc_id2": data["doc_id2"]}
                else:
                    return {"error": "Data must be a dict with 'doc_id1' and 'doc_id2' for similarity analysis"}
            
            elif analysis_type == "classify":
                if isinstance(data, str):
                    classifications = self.classify_content(data)
                    return {"classifications": classifications}
                elif isinstance(data, Document):
                    classifications = self.classify_content(data.content)
                    return {"classifications": classifications, "document_id": data.metadata.document_id}
                else:
                    return {"error": "Data must be a string or Document for classification"}
            
            elif analysis_type == "proximity":
                if isinstance(data, dict) and "content" in data and "terms" in data:
                    # Use proximity engine for analysis
                    result = self.proximity_engine.search_proximity(
                        data["content"],
                        data["terms"],
                        data.get("distance", 10),
                        data.get("unit", "WORDS"),
                        data.get("ordered", False)
                    )
                    return {"proximity_result": result}
                else:
                    return {"error": "Data must be a dict with 'content' and 'terms' for proximity analysis"}
            
            elif analysis_type == "extract_metadata":
                if isinstance(data, Document):
                    metadata = self.extract_metadata(data)
                    return {"metadata": metadata}
                else:
                    return {"error": "Data must be a Document for metadata extraction"}
            
            else:
                return {"error": f"Unsupported analysis type: {analysis_type}"}
        
        except Exception as e:
            return {"error": str(e)}
    
    async def extract_features(
        self,
        data: Any,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Extract features from document data.
        
        Args:
            data: Data to extract features from
            context: Optional execution context
            
        Returns:
            Extracted features
        """
        try:
            if isinstance(data, Document):
                features = {
                    "document_id": data.metadata.document_id,
                    "document_type": data.metadata.document_type,
                    "content_length": len(data.content),
                    "word_count": len(re.findall(r'\b\w+\b', data.content)),
                    "has_email_structure": any(indicator in data.content.lower() 
                                             for indicator in ['from:', 'to:', 'subject:', 'cc:']),
                    "has_legal_terms": any(term in data.content.lower() 
                                         for term in ['agreement', 'contract', 'hereby', 'shall', 'party']),
                    "classifications": self.classify_content(data.content)
                }
                
                # Add term statistics if document is indexed
                if data.metadata.document_id in self.document_index:
                    term_counts = self.document_index[data.metadata.document_id]
                    features["unique_terms"] = len(term_counts)
                    features["total_terms"] = sum(term_counts.values())
                    features["top_terms"] = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                return features
            
            elif isinstance(data, str):
                return {
                    "content_length": len(data),
                    "word_count": len(re.findall(r'\b\w+\b', data)),
                    "classifications": self.classify_content(data)
                }
            
            else:
                return {"error": f"Unsupported data type for feature extraction: {type(data)}"}
        
        except Exception as e:
            return {"error": str(e)}