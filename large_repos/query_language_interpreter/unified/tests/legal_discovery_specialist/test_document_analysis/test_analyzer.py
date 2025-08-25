"""Tests for the document analyzer."""

import pytest
from datetime import datetime
from legal_discovery_interpreter.core.document import (
    DocumentMetadata,
    Document,
    DocumentCollection
)
from legal_discovery_interpreter.document_analysis.proximity import ProximitySearchEngine
from legal_discovery_interpreter.document_analysis.analyzer import DocumentAnalyzer


@pytest.fixture
def proximity_engine():
    """Create a sample proximity search engine for testing."""
    return ProximitySearchEngine()


@pytest.fixture
def document_analyzer(proximity_engine):
    """Create a sample document analyzer for testing."""
    return DocumentAnalyzer(proximity_engine=proximity_engine)


@pytest.fixture
def sample_document_collection():
    """Create a sample document collection for testing."""
    collection = DocumentCollection(
        collection_id="test_collection",
        name="Test Collection"
    )
    
    # Document 1
    metadata1 = DocumentMetadata(
        document_id="doc001",
        title="Contract Agreement",
        document_type="contract",
        date_created=datetime(2020, 5, 15, 10, 30)
    )
    
    document1 = Document(
        metadata=metadata1,
        content="""
        This agreement is made between Party A and Party B. Both parties agree to the terms 
        outlined in Sections 1-5. The liability clause mentioned in Section 3 shall be binding.
        """
    )
    
    # Document 2
    metadata2 = DocumentMetadata(
        document_id="doc002",
        title="Meeting Minutes",
        document_type="minutes",
        date_created=datetime(2020, 7, 10, 14, 0)
    )
    
    document2 = Document(
        metadata=metadata2,
        content="""
        The board convened on July 10, 2020 to discuss the pending litigation. 
        The CEO expressed concerns about the statute of limitations. 
        The general counsel advised on next steps.
        """
    )
    
    # Document 3
    metadata3 = DocumentMetadata(
        document_id="doc003",
        title="Legal Memorandum",
        document_type="memorandum",
        date_created=datetime(2020, 9, 22, 9, 15)
    )
    
    document3 = Document(
        metadata=metadata3,
        content="""
        CONFIDENTIAL: ATTORNEY-CLIENT PRIVILEGED COMMUNICATION.
        This memorandum analyzes the legal risks associated with the proposed merger.
        Based on our research, we recommend proceeding with caution.
        """
    )
    
    collection.add_document(document1)
    collection.add_document(document2)
    collection.add_document(document3)
    
    return collection


def test_document_analyzer_initialization(document_analyzer, proximity_engine):
    """Test initializing a document analyzer."""
    assert document_analyzer.proximity_engine == proximity_engine
    assert document_analyzer.logger is not None
    assert isinstance(document_analyzer.document_index, dict)
    assert isinstance(document_analyzer.inverted_index, dict)
    assert isinstance(document_analyzer.similarity_cache, dict)


def test_index_document(document_analyzer, sample_document_collection):
    """Test indexing a document."""
    document = sample_document_collection.get_document("doc001")
    document_analyzer.index_document(document)
    
    assert "doc001" in document_analyzer.document_index
    assert len(document_analyzer.document_index["doc001"]) > 0
    
    # Check that terms were added to the inverted index
    assert "agreement" in document_analyzer.inverted_index
    assert "doc001" in document_analyzer.inverted_index["agreement"]
    
    assert "liability" in document_analyzer.inverted_index
    assert "doc001" in document_analyzer.inverted_index["liability"]


def test_index_collection(document_analyzer, sample_document_collection):
    """Test indexing a collection of documents."""
    document_analyzer.index_collection(sample_document_collection)
    
    assert "doc001" in document_analyzer.document_index
    assert "doc002" in document_analyzer.document_index
    assert "doc003" in document_analyzer.document_index
    
    # Check that terms from all documents were indexed
    assert "agreement" in document_analyzer.inverted_index
    assert "doc001" in document_analyzer.inverted_index["agreement"]
    
    assert "litigation" in document_analyzer.inverted_index
    assert "doc002" in document_analyzer.inverted_index["litigation"]
    
    assert "confidential" in document_analyzer.inverted_index
    assert "doc003" in document_analyzer.inverted_index["confidential"]


def test_search(document_analyzer, sample_document_collection):
    """Test searching for documents matching a query."""
    document_analyzer.index_collection(sample_document_collection)
    
    # Search for a single term
    results = document_analyzer.search("agreement")
    assert len(results) == 1
    assert "doc001" in results
    
    # Search for multiple terms
    results = document_analyzer.search("litigation statute")
    assert len(results) == 1
    assert "doc002" in results
    
    # Search for a term that doesn't exist
    results = document_analyzer.search("nonexistent")
    assert len(results) == 0


def test_calculate_proximity(document_analyzer, sample_document_collection):
    """Test calculating if terms appear within a specified distance of each other."""
    document = sample_document_collection.get_document("doc001")
    
    # Terms that are close
    assert document_analyzer.calculate_proximity(
        document.content, ["liability", "clause"], 2, "WORDS", False) is True
    
    # Terms that are not close
    assert document_analyzer.calculate_proximity(
        document.content, ["agreement", "liability"], 3, "WORDS", False) is False
    
    # Terms in the same paragraph
    assert document_analyzer.calculate_proximity(
        document.content, ["agreement", "liability"], 1, "PARAGRAPHS", False) is True


def test_search_proximity(document_analyzer, sample_document_collection):
    """Test searching for documents with terms in proximity."""
    # Search for documents with "liability" and "clause" within 2 words
    results = document_analyzer.search_proximity(
        sample_document_collection, ["liability", "clause"], 2, "WORDS", False)
    
    assert len(results) == 1
    assert "doc001" in results
    
    # Search for documents with "statute" and "limitations" within 2 words
    results = document_analyzer.search_proximity(
        sample_document_collection, ["statute", "limitations"], 2, "WORDS", False)
    
    assert len(results) == 1
    assert "doc002" in results
    
    # Search for documents with "agreement" and "binding" in the same paragraph
    results = document_analyzer.search_proximity(
        sample_document_collection, ["agreement", "binding"], 1, "PARAGRAPHS", False)
    
    assert len(results) == 1
    assert "doc001" in results


def test_calculate_similarity(document_analyzer, sample_document_collection):
    """Test calculating similarity between documents."""
    document_analyzer.index_collection(sample_document_collection)

    # Calculate similarity between doc001 and doc002
    similarity = document_analyzer.calculate_similarity("doc001", "doc002")

    assert 0 <= similarity <= 1

    # Calculate similarity between doc001 and itself (should be close to 1.0)
    similarity = document_analyzer.calculate_similarity("doc001", "doc001")

    assert abs(similarity - 1.0) < 1e-10

    # Check caching
    assert "doc001" in document_analyzer.similarity_cache

    # The document might be cached in either direction
    assert "doc002" in document_analyzer.similarity_cache.get("doc001", {}) or \
           "doc001" in document_analyzer.similarity_cache.get("doc002", {})


def test_find_similar_documents(document_analyzer, sample_document_collection):
    """Test finding documents similar to a given document."""
    document_analyzer.index_collection(sample_document_collection)
    
    # Find documents similar to doc001
    similar_docs = document_analyzer.find_similar_documents("doc001", sample_document_collection, threshold=0.1)
    
    assert isinstance(similar_docs, list)
    # Should have at least one similar document (other than itself)
    assert len(similar_docs) > 0
    
    # Each similarity should be between 0 and 1
    for doc_id, similarity in similar_docs:
        assert 0 <= similarity <= 1


def test_extract_metadata(document_analyzer, sample_document_collection):
    """Test extracting metadata from a document."""
    document = sample_document_collection.get_document("doc001")
    document_analyzer.index_document(document)
    
    metadata = document_analyzer.extract_metadata(document)
    
    assert metadata["document_id"] == "doc001"
    assert metadata["title"] == "Contract Agreement"
    assert metadata["document_type"] == "contract"
    assert "content_hash" in metadata  # Should have a content hash
    assert "term_count" in metadata  # Should have term counts if the document is indexed
    assert "unique_term_count" in metadata


def test_classify_content(document_analyzer, sample_document_collection):
    """Test classifying document content by type."""
    document1 = sample_document_collection.get_document("doc001")
    document2 = sample_document_collection.get_document("doc003")
    
    # Classify a contract
    classification1 = document_analyzer.classify_content(document1.content)
    
    assert isinstance(classification1, dict)
    assert "contract" in classification1
    assert classification1["contract"] > 0  # Should have some confidence for contract
    
    # Classify a memo
    classification2 = document_analyzer.classify_content(document2.content)
    
    assert isinstance(classification2, dict)
    assert "memo" in classification2
    assert classification2["memo"] > 0  # Should have some confidence for memo