"""
Tests for the storage module of the backup engine.
"""

import os
import tempfile
from pathlib import Path

import pytest

from gamevault.backup_engine.storage import StorageManager
from gamevault.utils import get_file_hash


@pytest.fixture
def storage_manager():
    """Create a StorageManager with a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield StorageManager(temp_dir)


@pytest.fixture
def sample_file():
    """Create a sample file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Sample file content for testing")
    
    try:
        yield temp_file.name
    finally:
        os.unlink(temp_file.name)


@pytest.fixture
def sample_chunks():
    """Create sample chunks for testing."""
    chunks = [
        b"Chunk 1 data",
        b"Chunk 2 data with more content",
        b"Another chunk with different content"
    ]
    
    return chunks


def test_store_file(storage_manager, sample_file):
    """Test storing a file in the storage manager."""
    # Store the file
    file_id, storage_path = storage_manager.store_file(sample_file)
    
    # Verify the file was stored
    assert storage_manager.file_exists(file_id)
    assert Path(storage_path).exists()
    
    # Verify the file ID
    assert file_id == get_file_hash(sample_file)


def test_retrieve_file(storage_manager, sample_file):
    """Test retrieving a stored file."""
    # Store the file
    file_id, _ = storage_manager.store_file(sample_file)
    
    # Retrieve the file to a new location
    with tempfile.NamedTemporaryFile(delete=False) as output_file:
        output_path = output_file.name
    
    try:
        storage_manager.retrieve_file(file_id, output_path)
        
        # Verify the file content matches
        with open(sample_file, "rb") as f:
            original_content = f.read()
        
        with open(output_path, "rb") as f:
            retrieved_content = f.read()
        
        assert retrieved_content == original_content
    finally:
        os.unlink(output_path)


def test_store_and_retrieve_chunks(storage_manager, sample_chunks):
    """Test storing and retrieving chunks."""
    # Store the chunks
    chunk_ids = []
    for chunk in sample_chunks:
        chunk_id = storage_manager.store_chunk(chunk)
        chunk_ids.append(chunk_id)
    
    # Verify the chunks were stored
    for chunk_id in chunk_ids:
        assert storage_manager.chunk_exists(chunk_id)
    
    # Retrieve and verify each chunk
    for i, chunk_id in enumerate(chunk_ids):
        retrieved_chunk = storage_manager.retrieve_chunk(chunk_id)
        assert retrieved_chunk == sample_chunks[i]


def test_remove_file(storage_manager, sample_file):
    """Test removing a stored file."""
    # Store the file
    file_id, _ = storage_manager.store_file(sample_file)
    
    # Verify it exists
    assert storage_manager.file_exists(file_id)
    
    # Remove the file
    result = storage_manager.remove_file(file_id)
    
    # Verify it was removed
    assert result is True
    assert not storage_manager.file_exists(file_id)
    
    # Try to remove a non-existent file
    result = storage_manager.remove_file("nonexistent")
    assert result is False


def test_remove_chunk(storage_manager, sample_chunks):
    """Test removing a stored chunk."""
    # Store a chunk
    chunk_id = storage_manager.store_chunk(sample_chunks[0])
    
    # Verify it exists
    assert storage_manager.chunk_exists(chunk_id)
    
    # Remove the chunk
    result = storage_manager.remove_chunk(chunk_id)
    
    # Verify it was removed
    assert result is True
    assert not storage_manager.chunk_exists(chunk_id)
    
    # Try to remove a non-existent chunk
    result = storage_manager.remove_chunk("nonexistent")
    assert result is False


def test_get_storage_size(storage_manager, sample_file, sample_chunks):
    """Test getting storage size information."""
    # Initially, storage should be empty
    sizes = storage_manager.get_storage_size()
    assert sizes["files"] == 0
    assert sizes["chunks"] == 0
    assert sizes["total"] == 0
    
    # Store a file
    storage_manager.store_file(sample_file)
    
    # Store some chunks
    for chunk in sample_chunks:
        storage_manager.store_chunk(chunk)
    
    # Get updated sizes
    sizes = storage_manager.get_storage_size()
    
    # Verify sizes are non-zero
    assert sizes["files"] > 0
    assert sizes["chunks"] > 0
    assert sizes["total"] == sizes["files"] + sizes["chunks"]


def test_file_not_found(storage_manager):
    """Test behavior when attempting to retrieve a non-existent file."""
    with pytest.raises(FileNotFoundError):
        storage_manager.retrieve_file("nonexistent", "output.txt")


def test_chunk_not_found(storage_manager):
    """Test behavior when attempting to retrieve a non-existent chunk."""
    with pytest.raises(FileNotFoundError):
        storage_manager.retrieve_chunk("nonexistent")


def test_idempotent_storage(storage_manager, sample_file):
    """Test that storing the same file multiple times is idempotent."""
    # Store the file twice
    file_id1, storage_path1 = storage_manager.store_file(sample_file)
    file_id2, storage_path2 = storage_manager.store_file(sample_file)
    
    # Both operations should return the same file ID and path
    assert file_id1 == file_id2
    assert storage_path1 == storage_path2