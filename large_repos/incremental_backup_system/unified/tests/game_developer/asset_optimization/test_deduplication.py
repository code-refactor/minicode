"""
Tests for the asset deduplication module.
"""

import pytest

from gamevault.asset_optimization.deduplication import (AssetDeduplicator,
                                                      ChunkHashIndex)


@pytest.fixture
def chunk_hash_index():
    """Create a ChunkHashIndex instance."""
    return ChunkHashIndex()


@pytest.fixture
def asset_deduplicator():
    """Create an AssetDeduplicator instance."""
    return AssetDeduplicator()


@pytest.fixture
def sample_chunks():
    """Create sample chunks for testing."""
    return [
        b"Chunk 1 data that will be unique",
        b"Chunk 2 data that will be shared between files",
        b"Chunk 3 data that will be shared between files",
        b"Chunk 4 data that will be unique to another file"
    ]


def test_chunk_hash_index_add_chunk(chunk_hash_index):
    """Test adding chunks to the index."""
    # Add a chunk
    chunk_hash_index.add_chunk("hash1", 100, "file1")
    
    # Verify it was added
    assert "hash1" in chunk_hash_index.chunk_refs
    assert "file1" in chunk_hash_index.file_chunks
    assert "hash1" in chunk_hash_index.chunk_files
    assert "file1" in chunk_hash_index.chunk_files["hash1"]
    
    # Add another chunk for the same file
    chunk_hash_index.add_chunk("hash2", 200, "file1")
    
    # Verify both chunks are associated with the file
    assert len(chunk_hash_index.file_chunks["file1"]) == 2
    assert "hash1" in chunk_hash_index.file_chunks["file1"]
    assert "hash2" in chunk_hash_index.file_chunks["file1"]
    
    # Add a chunk that already exists but for a different file
    chunk_hash_index.add_chunk("hash1", 100, "file2")
    
    # Verify the reference count increased
    assert chunk_hash_index.chunk_refs["hash1"][0] == 2
    
    # Verify both files are associated with the chunk
    assert "file1" in chunk_hash_index.chunk_files["hash1"]
    assert "file2" in chunk_hash_index.chunk_files["hash1"]


def test_chunk_hash_index_remove_chunk(chunk_hash_index):
    """Test removing chunks from the index."""
    # Add chunks
    chunk_hash_index.add_chunk("hash1", 100, "file1")
    chunk_hash_index.add_chunk("hash1", 100, "file2")
    chunk_hash_index.add_chunk("hash2", 200, "file1")
    
    # Remove a chunk from a file
    result = chunk_hash_index.remove_chunk("hash1", "file1")
    
    # Verify removal succeeded
    assert result is True
    
    # Verify reference count decreased
    assert chunk_hash_index.chunk_refs["hash1"][0] == 1
    
    # Verify the file is no longer associated with the chunk
    assert "file1" not in chunk_hash_index.chunk_files["hash1"]
    
    # Verify the chunk is removed from the file's list
    assert "hash1" not in chunk_hash_index.file_chunks["file1"]
    
    # Remove the last reference to a chunk
    result = chunk_hash_index.remove_chunk("hash1", "file2")
    
    # Verify the chunk is completely removed
    assert "hash1" not in chunk_hash_index.chunk_refs
    assert "hash1" not in chunk_hash_index.chunk_files
    
    # Try to remove a non-existent chunk
    result = chunk_hash_index.remove_chunk("nonexistent", "file1")
    assert result is False


def test_chunk_hash_index_remove_file(chunk_hash_index):
    """Test removing all chunks for a file."""
    # Add chunks for multiple files
    chunk_hash_index.add_chunk("hash1", 100, "file1")
    chunk_hash_index.add_chunk("hash2", 200, "file1")
    chunk_hash_index.add_chunk("hash1", 100, "file2")
    
    # Remove all chunks for file1
    removed_count = chunk_hash_index.remove_file("file1")
    
    # Verify chunks were removed
    assert removed_count == 2
    
    # Verify file1 is no longer in the index
    assert "file1" not in chunk_hash_index.file_chunks
    
    # Verify reference counts were updated
    assert chunk_hash_index.chunk_refs["hash1"][0] == 1
    assert "hash2" not in chunk_hash_index.chunk_refs
    
    # Verify file associations were updated
    assert "file1" not in chunk_hash_index.chunk_files["hash1"]
    assert "hash2" not in chunk_hash_index.chunk_files
    
    # Try to remove a non-existent file
    removed_count = chunk_hash_index.remove_file("nonexistent")
    assert removed_count == 0


def test_chunk_hash_index_get_duplicate_chunks(chunk_hash_index):
    """Test identifying duplicate chunks."""
    # Add some unique and shared chunks
    chunk_hash_index.add_chunk("unique1", 100, "file1")
    chunk_hash_index.add_chunk("shared1", 200, "file1")
    chunk_hash_index.add_chunk("shared1", 200, "file2")
    chunk_hash_index.add_chunk("shared2", 300, "file1")
    chunk_hash_index.add_chunk("shared2", 300, "file2")
    chunk_hash_index.add_chunk("shared2", 300, "file3")
    chunk_hash_index.add_chunk("unique2", 400, "file2")
    
    # Get duplicates with default threshold (2)
    duplicates = chunk_hash_index.get_duplicate_chunks()
    
    # Verify only shared chunks are identified
    assert "unique1" not in duplicates
    assert "unique2" not in duplicates
    assert "shared1" in duplicates
    assert "shared2" in duplicates
    
    # Verify reference counts
    assert duplicates["shared1"][0] == 2
    assert duplicates["shared2"][0] == 3
    
    # Get duplicates with higher threshold
    duplicates = chunk_hash_index.get_duplicate_chunks(min_refs=3)
    
    # Verify only chunks with 3+ references are included
    assert "shared1" not in duplicates
    assert "shared2" in duplicates


def test_chunk_hash_index_get_storage_savings(chunk_hash_index):
    """Test calculating storage savings from deduplication."""
    # Add chunks with different reference counts
    chunk_hash_index.add_chunk("unique1", 100, "file1")
    chunk_hash_index.add_chunk("shared1", 200, "file1")
    chunk_hash_index.add_chunk("shared1", 200, "file2")
    chunk_hash_index.add_chunk("shared2", 300, "file1")
    chunk_hash_index.add_chunk("shared2", 300, "file2")
    chunk_hash_index.add_chunk("shared2", 300, "file3")
    
    # Calculate savings
    savings = chunk_hash_index.get_storage_savings()
    
    # Verify logical size
    expected_logical_size = 100 + 200*2 + 300*3
    assert savings["total_logical_size"] == expected_logical_size
    
    # Verify physical size
    expected_physical_size = 100 + 200 + 300
    assert savings["total_physical_size"] == expected_physical_size
    
    # Verify duplicate size
    expected_duplicate_size = 200 + 300*2
    assert savings["duplicate_size"] == expected_duplicate_size
    
    # Verify saved size
    expected_saved_size = expected_logical_size - expected_physical_size
    assert savings["saved_size"] == expected_saved_size
    
    # Verify deduplication ratio
    expected_ratio = expected_logical_size / expected_physical_size
    assert savings["dedup_ratio"] == expected_ratio


def test_chunk_hash_index_get_file_sharing_stats(chunk_hash_index):
    """Test getting file sharing statistics."""
    # Add chunks with sharing between files
    chunk_hash_index.add_chunk("unique1", 100, "file1")
    chunk_hash_index.add_chunk("shared1", 200, "file1")
    chunk_hash_index.add_chunk("shared1", 200, "file2")
    chunk_hash_index.add_chunk("shared2", 300, "file1")
    chunk_hash_index.add_chunk("shared2", 300, "file2")
    chunk_hash_index.add_chunk("unique2", 400, "file2")
    
    # Get sharing stats for file1
    stats = chunk_hash_index.get_file_sharing_stats("file1")
    
    # Verify basic stats
    assert stats["file_id"] == "file1"
    assert stats["total_chunks"] == 3
    assert stats["shared_chunks"] == 2
    assert stats["unique_chunks"] == 1
    
    # Verify sharing files
    assert len(stats["sharing_files"]) == 1
    assert stats["sharing_files"][0]["file_id"] == "file2"
    assert stats["sharing_files"][0]["shared_chunks"] == 2


def test_asset_deduplicator_deduplicate_file(asset_deduplicator):
    """Test deduplicating file chunks."""
    # Create some chunks with same content to ensure they hash to the same value
    chunk1 = b"Chunk 1 data that will be unique"
    chunk2 = b"Chunk 2 data that will be shared between files"
    chunk3 = b"Chunk 3 data that will be shared between files"
    chunk4 = b"Chunk 4 data that will be unique to another file"

    # Use the exact same bytes objects to ensure they hash to the same value

    # Deduplicate first file
    file1_chunks = [chunk1, chunk2, chunk3]
    chunk_hashes1 = asset_deduplicator.deduplicate_file("file1", file1_chunks)

    # Verify hashes were returned
    assert len(chunk_hashes1) == 3

    # Deduplicate second file with some shared chunks
    file2_chunks = [chunk2, chunk3, chunk4]  # Note: using the exact same chunk2 and chunk3 objects
    chunk_hashes2 = asset_deduplicator.deduplicate_file("file2", file2_chunks)

    # Verify hashes were returned
    assert len(chunk_hashes2) == 3

    # Verify that the shared chunks have the same hash
    assert chunk_hashes1[1] == chunk_hashes2[0]  # chunk2
    assert chunk_hashes1[2] == chunk_hashes2[1]  # chunk3

    # Get deduplication stats
    stats = asset_deduplicator.get_deduplication_stats()

    # Verify deduplication metrics make sense
    assert stats["total_chunks"] >= 4  # At least 4 unique chunks across both files

    # Get most shared files
    shared_files = asset_deduplicator.get_most_shared_files()

    # Verify file sharing information
    assert len(shared_files) == 2

    # Update a file with a simpler version (we removed the reference to sample_chunks)
    file1_modified = [chunk1, chunk2]  # Removed chunk3
    chunk_hashes = asset_deduplicator.deduplicate_file(
        "file1", file1_modified, [chunk_hashes1[0], chunk_hashes1[1], chunk_hashes1[2]]
    )
    
    # Verify update worked
    assert len(chunk_hashes) == 2
    
    # Get updated stats
    stats = asset_deduplicator.get_deduplication_stats()
    
    # Should still have 4 total chunks, but different dedup stats
    assert stats["total_chunks"] == 4