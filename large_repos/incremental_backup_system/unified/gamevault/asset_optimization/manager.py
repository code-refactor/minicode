"""
Asset Optimization Manager for GameVault.

This module provides the main interface for optimizing game assets.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from gamevault.asset_optimization.chunking import AssetChunkerFactory
from gamevault.asset_optimization.compressor import (AssetCompressorFactory,
                                                    DeltaCompressor)
from gamevault.asset_optimization.deduplication import AssetDeduplicator
from gamevault.backup_engine.storage import StorageManager
from gamevault.config import get_config
from gamevault.models import FileInfo
from gamevault.utils import get_file_hash, is_binary_file


class AssetOptimizationManager:
    """
    Manager for optimizing game assets.
    
    This class orchestrates the various asset optimization techniques,
    including compression, chunking, and deduplication.
    """
    
    def __init__(
        self,
        storage_manager: Optional[StorageManager] = None,
        storage_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the asset optimization manager.
        
        Args:
            storage_manager: Storage manager instance. If None, a new one will be created.
            storage_dir: Directory where optimized assets will be stored. If None, uses the default from config.
        """
        config = get_config()
        
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir
        self.storage_manager = storage_manager or StorageManager(self.storage_dir)
        
        # Initialize components
        self.deduplicator = AssetDeduplicator()
        self.delta_compressor = DeltaCompressor()
        
        # Settings
        self.min_chunk_size = config.min_chunk_size
        self.max_chunk_size = config.max_chunk_size
        self.binary_extensions = config.binary_extensions
    
    def optimize_asset(
        self,
        file_path: Union[str, Path],
        prev_version: Optional[FileInfo] = None
    ) -> FileInfo:
        """
        Optimize a game asset for storage.
        
        Args:
            file_path: Path to the asset file
            prev_version: Previous version of the file (if available)
            
        Returns:
            FileInfo: Information about the optimized asset
        """
        file_path = Path(file_path)
        rel_path = file_path.name
        is_binary = is_binary_file(file_path, self.binary_extensions)
        
        # Check if it's a binary file
        if not is_binary:
            # For text files, use standard storage
            file_hash, storage_path = self.storage_manager.store_file(file_path)
            
            return FileInfo(
                path=rel_path,
                size=os.path.getsize(file_path),
                hash=file_hash,
                modified_time=os.path.getmtime(file_path),
                is_binary=False,
                storage_path=storage_path
            )
        
        # For binary files, apply optimization strategies
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Calculate file hash
        file_hash = get_file_hash(file_path)
        
        # Check if we can use delta compression
        if prev_version and prev_version.is_binary and prev_version.chunks:
            # Try to use delta compression
            try:
                # Reconstruct the previous version
                prev_data = self._reconstruct_from_chunks(prev_version.chunks)
                
                # Create delta
                delta = self.delta_compressor.create_delta(prev_data, data)
                
                # Check if delta is significantly smaller
                if len(delta) < len(data) * 0.7:  # At least 30% smaller
                    # Compress the delta
                    compressed_delta = self.delta_compressor.compress_delta(delta)
                    
                    # Store the compressed delta
                    delta_hash = self.storage_manager.store_chunk(compressed_delta)
                    
                    # Create file info with delta reference
                    return FileInfo(
                        path=rel_path,
                        size=os.path.getsize(file_path),
                        hash=file_hash,
                        modified_time=os.path.getmtime(file_path),
                        is_binary=True,
                        chunks=[delta_hash],
                        metadata={
                            "delta": "true",
                            "base_version": prev_version.hash
                        }
                    )
            except Exception:
                # If delta compression fails, fall back to regular chunking
                pass
        
        # Apply chunking based on file type
        file_extension = file_path.suffix
        chunker = AssetChunkerFactory.get_chunker(file_extension)
        chunks = chunker.chunk_file(data, file_extension)
        
        # Apply compression to each chunk
        compressor = AssetCompressorFactory.get_compressor(file_extension)
        compressed_chunks = [compressor.compress(chunk) for chunk in chunks]
        
        # Store chunks and apply deduplication
        chunk_hashes = []
        for chunk in compressed_chunks:
            chunk_id = self.storage_manager.store_chunk(chunk)
            chunk_hashes.append(chunk_id)
        
        # Deduplicate chunks
        if prev_version and prev_version.is_binary and prev_version.chunks:
            deduplicated_hashes = self.deduplicator.deduplicate_file(
                file_hash, compressed_chunks, prev_version.chunks
            )
        else:
            deduplicated_hashes = self.deduplicator.deduplicate_file(
                file_hash, compressed_chunks
            )
        
        # Create file info
        return FileInfo(
            path=rel_path,
            size=os.path.getsize(file_path),
            hash=file_hash,
            modified_time=os.path.getmtime(file_path),
            is_binary=True,
            chunks=chunk_hashes
        )
    
    def _reconstruct_from_chunks(self, chunk_ids: List[str]) -> bytes:
        """
        Reconstruct file data from chunks.
        
        Args:
            chunk_ids: List of chunk IDs
            
        Returns:
            bytes: Reconstructed file data
        """
        data = b""
        
        for chunk_id in chunk_ids:
            chunk_data = self.storage_manager.retrieve_chunk(chunk_id)
            data += chunk_data
        
        return data
    
    def restore_asset(
        self,
        file_info: FileInfo,
        output_path: Union[str, Path]
    ) -> None:
        """
        Restore an optimized asset.
        
        Args:
            file_info: Information about the asset
            output_path: Path where the asset should be restored
        """
        output_path = Path(output_path)
        
        # Create parent directories
        os.makedirs(output_path.parent, exist_ok=True)
        
        if not file_info.is_binary:
            # For text files, use standard retrieval
            self.storage_manager.retrieve_file(file_info.hash, output_path)
            return
        
        # For binary files, handle chunks and delta compression
        if "delta" in file_info.metadata and file_info.metadata["delta"] == "true":
            # This is a delta-compressed file
            base_version_hash = file_info.metadata["base_version"]
            
            # Get the base version
            # In a real system, you would retrieve this from your version history
            # For this example, we'll assume it's not available and handle the error
            try:
                base_file_info = self._get_base_version(base_version_hash)
                base_data = self._reconstruct_from_chunks(base_file_info.chunks)
                
                # Get the delta
                compressed_delta = self.storage_manager.retrieve_chunk(file_info.chunks[0])
                
                # Decompress the delta
                delta = self.delta_compressor.decompress_delta(compressed_delta)
                
                # Apply the delta
                data = self.delta_compressor.apply_delta(base_data, delta)
                
                # Write the file
                with open(output_path, "wb") as f:
                    f.write(data)
            except Exception:
                # If delta restoration fails, try to restore from regular chunks
                self._restore_from_chunks(file_info.chunks, output_path)
        else:
            # Regular chunked file
            self._restore_from_chunks(file_info.chunks, output_path)
    
    def _get_base_version(self, base_version_hash: str) -> FileInfo:
        """
        Get the base version for a delta-compressed file.
        
        Retrieves the FileInfo of a previous version based on its hash.
        
        Args:
            base_version_hash: Hash of the base version
            
        Returns:
            FileInfo: Information about the base version
            
        Raises:
            ValueError: If the base version can't be found
        """
        # Search for the file in the storage system by its hash
        try:
            # Check if the file exists in storage
            file_path = self.storage_manager.get_file_path_by_hash(base_version_hash)
            if file_path:
                # Create basic FileInfo from the stored file
                file_size = os.path.getsize(file_path)
                chunks = self.storage_manager.get_chunks_for_file(base_version_hash)
                
                return FileInfo(
                    path=os.path.basename(file_path),
                    size=file_size,
                    hash=base_version_hash,
                    modified_time=os.path.getmtime(file_path),
                    is_binary=True,
                    chunks=chunks or []
                )
            
            # If no direct file is found, try looking for chunks
            chunks = self.storage_manager.get_chunks_for_file(base_version_hash)
            if chunks:
                # Return FileInfo with just the chunks
                return FileInfo(
                    path="unknown",  # Path is not critical for reconstruction
                    size=0,  # Size will be determined after reconstruction
                    hash=base_version_hash,
                    modified_time=0,  # Not critical for reconstruction
                    is_binary=True,
                    chunks=chunks
                )
                
            raise ValueError(f"Base version {base_version_hash} not found")
        except Exception as e:
            raise ValueError(f"Failed to retrieve base version {base_version_hash}: {str(e)}")
    
    def _restore_from_chunks(
        self,
        chunk_ids: List[str],
        output_path: Path
    ) -> None:
        """
        Restore a file from chunks.
        
        Args:
            chunk_ids: List of chunk IDs
            output_path: Path where the file should be restored
        """
        # Fetch and decompress chunks
        with open(output_path, "wb") as f:
            for chunk_id in chunk_ids:
                chunk_data = self.storage_manager.retrieve_chunk(chunk_id)
                f.write(chunk_data)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        Get statistics on asset optimization.
        
        Returns:
            Dict[str, Any]: Optimization statistics
        """
        dedup_stats = self.deduplicator.get_deduplication_stats()
        storage_stats = self.storage_manager.get_storage_size()
        
        return {
            "deduplication": dedup_stats,
            "storage": storage_stats,
            "total_savings": dedup_stats.get("saved_size", 0)
        }
    
    def get_shared_asset_analysis(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get analysis of assets with shared content.
        
        Args:
            limit: Maximum number of assets to include
            
        Returns:
            List[Dict[str, Any]]: Analysis of shared assets
        """
        return self.deduplicator.get_most_shared_files(limit)