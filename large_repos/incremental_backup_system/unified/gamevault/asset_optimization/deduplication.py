"""
Asset deduplication module for GameVault.

This module provides functionality for detecting and eliminating duplicate
asset data across a game project.
"""

import hashlib
import os
from typing import Dict, List, Optional, Set, Tuple, Union, Any

import xxhash

from gamevault.utils import get_file_hash, get_file_xxhash


class ChunkHashIndex:
    """
    Index for tracking and deduplicating chunks.
    
    This class maintains an index of chunk hashes to enable deduplication
    of redundant data chunks.
    """
    
    def __init__(self):
        """
        Initialize the chunk hash index.
        """
        # Map of chunk hash to reference count and size
        self.chunk_refs: Dict[str, Tuple[int, int]] = {}
        
        # Map of chunk hash to set of file IDs containing that chunk
        self.chunk_files: Dict[str, Set[str]] = {}
        
        # Map of file ID to list of chunk hashes
        self.file_chunks: Dict[str, List[str]] = {}
    
    def add_chunk(self, chunk_hash: str, chunk_size: int, file_id: str) -> None:
        """
        Add a chunk to the index.
        
        Args:
            chunk_hash: Hash of the chunk
            chunk_size: Size of the chunk in bytes
            file_id: ID of the file containing the chunk
        """
        # Update chunk references
        if chunk_hash in self.chunk_refs:
            ref_count, _ = self.chunk_refs[chunk_hash]
            self.chunk_refs[chunk_hash] = (ref_count + 1, chunk_size)
        else:
            self.chunk_refs[chunk_hash] = (1, chunk_size)
        
        # Update chunk files
        if chunk_hash not in self.chunk_files:
            self.chunk_files[chunk_hash] = set()
        self.chunk_files[chunk_hash].add(file_id)
        
        # Update file chunks
        if file_id not in self.file_chunks:
            self.file_chunks[file_id] = []
        self.file_chunks[file_id].append(chunk_hash)
    
    def remove_chunk(self, chunk_hash: str, file_id: str) -> bool:
        """
        Remove a chunk reference from the index.
        
        Args:
            chunk_hash: Hash of the chunk
            file_id: ID of the file containing the chunk
            
        Returns:
            bool: True if the chunk was removed, False otherwise
        """
        if chunk_hash not in self.chunk_refs:
            return False
        
        # Update chunk references
        ref_count, chunk_size = self.chunk_refs[chunk_hash]
        if ref_count > 1:
            self.chunk_refs[chunk_hash] = (ref_count - 1, chunk_size)
        else:
            del self.chunk_refs[chunk_hash]
        
        # Update chunk files
        if chunk_hash in self.chunk_files:
            self.chunk_files[chunk_hash].discard(file_id)
            if not self.chunk_files[chunk_hash]:
                del self.chunk_files[chunk_hash]
        
        # Update file chunks
        if file_id in self.file_chunks:
            self.file_chunks[file_id] = [c for c in self.file_chunks[file_id] if c != chunk_hash]
            if not self.file_chunks[file_id]:
                del self.file_chunks[file_id]
        
        return True
    
    def remove_file(self, file_id: str) -> int:
        """
        Remove all chunks for a file from the index.
        
        Args:
            file_id: ID of the file
            
        Returns:
            int: Number of chunks removed
        """
        if file_id not in self.file_chunks:
            return 0
        
        # Get chunks for the file
        chunks = self.file_chunks[file_id].copy()
        
        # Remove each chunk
        removed_count = 0
        for chunk_hash in chunks:
            if self.remove_chunk(chunk_hash, file_id):
                removed_count += 1
        
        return removed_count
    
    def get_duplicate_chunks(self, min_refs: int = 2) -> Dict[str, Tuple[int, int]]:
        """
        Get chunks that appear in multiple files.
        
        Args:
            min_refs: Minimum number of references to consider a chunk as duplicate
            
        Returns:
            Dict[str, Tuple[int, int]]: Map of chunk hash to (reference count, chunk size)
        """
        return {
            chunk_hash: (ref_count, size)
            for chunk_hash, (ref_count, size) in self.chunk_refs.items()
            if ref_count >= min_refs
        }
    
    def get_storage_savings(self, min_refs: int = 2) -> Dict[str, int]:
        """
        Calculate storage savings from deduplication.
        
        Args:
            min_refs: Minimum number of references to consider a chunk as duplicate
            
        Returns:
            Dict[str, int]: Dictionary of storage statistics
        """
        total_logical_size = 0
        total_physical_size = 0
        duplicate_size = 0
        
        for chunk_hash, (ref_count, size) in self.chunk_refs.items():
            logical_size = size * ref_count
            physical_size = size
            
            total_logical_size += logical_size
            total_physical_size += physical_size
            
            if ref_count >= min_refs:
                duplicate_size += size * (ref_count - 1)
        
        if total_logical_size == 0:
            dedup_ratio = 1.0
        else:
            dedup_ratio = total_logical_size / total_physical_size
        
        return {
            "total_logical_size": total_logical_size,
            "total_physical_size": total_physical_size,
            "duplicate_size": duplicate_size,
            "saved_size": total_logical_size - total_physical_size,
            "dedup_ratio": dedup_ratio
        }
    
    def get_file_sharing_stats(self, file_id: str) -> Dict[str, Any]:
        """
        Get statistics on how a file shares chunks with other files.
        
        Args:
            file_id: ID of the file
            
        Returns:
            Dict[str, Any]: Sharing statistics
        """
        if file_id not in self.file_chunks:
            return {"file_id": file_id, "shared_chunks": 0, "unique_chunks": 0, "sharing_files": []}
        
        # Get chunks for the file
        chunks = self.file_chunks[file_id]
        
        # Count shared and unique chunks
        shared_chunks = 0
        unique_chunks = 0
        
        for chunk_hash in chunks:
            ref_count, _ = self.chunk_refs[chunk_hash]
            if ref_count > 1:
                shared_chunks += 1
            else:
                unique_chunks += 1
        
        # Find files that share chunks
        sharing_files = {}
        
        for chunk_hash in chunks:
            for other_file_id in self.chunk_files.get(chunk_hash, set()):
                if other_file_id != file_id:
                    sharing_files[other_file_id] = sharing_files.get(other_file_id, 0) + 1
        
        # Sort by number of shared chunks
        sharing_files_list = [
            {"file_id": other_file_id, "shared_chunks": count}
            for other_file_id, count in sharing_files.items()
        ]
        sharing_files_list.sort(key=lambda x: x["shared_chunks"], reverse=True)
        
        return {
            "file_id": file_id,
            "total_chunks": len(chunks),
            "shared_chunks": shared_chunks,
            "unique_chunks": unique_chunks,
            "sharing_files": sharing_files_list
        }


class AssetDeduplicator:
    """
    Manages deduplication of game assets.
    
    This class detects and eliminates duplicate asset data to optimize storage.
    """
    
    def __init__(self):
        """
        Initialize the asset deduplicator.
        """
        self.chunk_index = ChunkHashIndex()
    
    def deduplicate_file(
        self,
        file_id: str,
        chunks: List[bytes],
        existing_chunks: Optional[List[str]] = None
    ) -> List[str]:
        """
        Deduplicate a file's chunks.
        
        Args:
            file_id: ID of the file
            chunks: List of file chunks
            existing_chunks: List of existing chunk hashes (if updating)
            
        Returns:
            List[str]: List of chunk hashes after deduplication
        """
        # Remove existing chunks if updating
        if existing_chunks:
            for chunk_hash in existing_chunks:
                self.chunk_index.remove_chunk(chunk_hash, file_id)
        else:
            # Remove any existing file data
            self.chunk_index.remove_file(file_id)
        
        # Calculate and index new chunks
        chunk_hashes = []
        
        for chunk in chunks:
            # Hash the chunk
            hasher = xxhash.xxh64()
            hasher.update(chunk)
            chunk_hash = hasher.hexdigest()
            
            # Add to index
            self.chunk_index.add_chunk(chunk_hash, len(chunk), file_id)
            
            # Add to result
            chunk_hashes.append(chunk_hash)
        
        return chunk_hashes
    
    def get_deduplication_stats(self) -> Dict[str, Any]:
        """
        Get statistics on deduplication.
        
        Returns:
            Dict[str, Any]: Deduplication statistics
        """
        savings = self.chunk_index.get_storage_savings()
        duplicates = self.chunk_index.get_duplicate_chunks()
        
        return {
            **savings,
            "duplicate_chunks": len(duplicates),
            "total_chunks": len(self.chunk_index.chunk_refs)
        }
    
    def get_most_shared_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get files with the most shared chunks.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List[Dict[str, Any]]: List of files and their sharing stats
        """
        file_stats = []
        
        for file_id in self.chunk_index.file_chunks:
            stats = self.chunk_index.get_file_sharing_stats(file_id)
            file_stats.append(stats)
        
        # Sort by number of shared chunks
        file_stats.sort(key=lambda x: x["shared_chunks"], reverse=True)
        
        return file_stats[:limit]