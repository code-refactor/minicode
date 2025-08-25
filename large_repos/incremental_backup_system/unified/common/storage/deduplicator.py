"""Deduplication management for the storage system."""

from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
import json


class Deduplicator:
    """Manages deduplication with reference counting."""
    
    def __init__(self, index_path: Optional[Path] = None):
        """
        Initialize deduplicator.
        
        Args:
            index_path: Optional path to persist the index
        """
        self.index_path = index_path
        self._references: Dict[str, Set[str]] = {}  # hash -> set of sources
        self._reverse_index: Dict[str, Set[str]] = {}  # source -> set of hashes
        
        if index_path and index_path.exists():
            self._load_index()
    
    def add_reference(self, hash_key: str, source: str) -> None:
        """
        Add a reference to a content hash.
        
        Args:
            hash_key: Content hash
            source: Source identifier (e.g., file path or snapshot ID)
        """
        if hash_key not in self._references:
            self._references[hash_key] = set()
        self._references[hash_key].add(source)
        
        if source not in self._reverse_index:
            self._reverse_index[source] = set()
        self._reverse_index[source].add(hash_key)
        
        self._save_index()
    
    def remove_reference(self, hash_key: str, source: str) -> bool:
        """
        Remove a reference to a content hash.
        
        Args:
            hash_key: Content hash
            source: Source identifier
        
        Returns:
            True if this was the last reference (content can be deleted)
        """
        if hash_key in self._references:
            self._references[hash_key].discard(source)
            if not self._references[hash_key]:
                del self._references[hash_key]
                
        if source in self._reverse_index:
            self._reverse_index[source].discard(hash_key)
            if not self._reverse_index[source]:
                del self._reverse_index[source]
        
        self._save_index()
        return hash_key not in self._references
    
    def remove_source(self, source: str) -> List[str]:
        """
        Remove all references from a source.
        
        Args:
            source: Source identifier
        
        Returns:
            List of hashes that can be deleted (no more references)
        """
        deletable = []
        
        if source in self._reverse_index:
            hashes = list(self._reverse_index[source])
            for hash_key in hashes:
                if self.remove_reference(hash_key, source):
                    deletable.append(hash_key)
        
        return deletable
    
    def get_reference_count(self, hash_key: str) -> int:
        """
        Get the reference count for a content hash.
        
        Args:
            hash_key: Content hash
        
        Returns:
            Number of references
        """
        return len(self._references.get(hash_key, set()))
    
    def get_sources(self, hash_key: str) -> Set[str]:
        """
        Get all sources referencing a content hash.
        
        Args:
            hash_key: Content hash
        
        Returns:
            Set of source identifiers
        """
        return self._references.get(hash_key, set()).copy()
    
    def get_hashes(self, source: str) -> Set[str]:
        """
        Get all hashes referenced by a source.
        
        Args:
            source: Source identifier
        
        Returns:
            Set of content hashes
        """
        return self._reverse_index.get(source, set()).copy()
    
    def find_duplicates(self) -> Dict[str, List[str]]:
        """
        Find content that is referenced by multiple sources.
        
        Returns:
            Dictionary mapping hashes to list of sources (only duplicates)
        """
        duplicates = {}
        for hash_key, sources in self._references.items():
            if len(sources) > 1:
                duplicates[hash_key] = list(sources)
        return duplicates
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get deduplication statistics.
        
        Returns:
            Statistics dictionary
        """
        total_hashes = len(self._references)
        total_sources = len(self._reverse_index)
        total_references = sum(len(sources) for sources in self._references.values())
        duplicates = self.find_duplicates()
        
        return {
            'unique_content_items': total_hashes,
            'total_sources': total_sources,
            'total_references': total_references,
            'deduplicated_items': len(duplicates),
            'space_saving_factor': total_references / max(total_hashes, 1)
        }
    
    def cleanup_orphaned(self) -> List[str]:
        """
        Find content with no references.
        
        Returns:
            List of orphaned content hashes
        """
        return [hash_key for hash_key, sources in self._references.items() 
                if not sources]
    
    def _save_index(self) -> None:
        """Save index to disk if path is configured."""
        if self.index_path:
            index_data = {
                'references': {k: list(v) for k, v in self._references.items()},
                'reverse_index': {k: list(v) for k, v in self._reverse_index.items()}
            }
            
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.index_path, 'w') as f:
                json.dump(index_data, f, indent=2)
    
    def _load_index(self) -> None:
        """Load index from disk."""
        if self.index_path and self.index_path.exists():
            with open(self.index_path, 'r') as f:
                index_data = json.load(f)
            
            self._references = {k: set(v) for k, v in index_data.get('references', {}).items()}
            self._reverse_index = {k: set(v) for k, v in index_data.get('reverse_index', {}).items()}