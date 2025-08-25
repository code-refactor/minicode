"""
Backup Engine module for GameVault.

This package provides the core backup engine functionality for tracking game versions
and efficiently storing files.
"""

from gamevault.backup_engine.chunker import (ChunkingStrategy, FixedSizeChunker,
                                           GameAssetChunker,
                                           RollingHashChunker)
from gamevault.backup_engine.engine import BackupEngine
from gamevault.backup_engine.storage import StorageManager
from gamevault.backup_engine.version_tracker import VersionTracker

__all__ = [
    'BackupEngine',
    'ChunkingStrategy',
    'FixedSizeChunker',
    'GameAssetChunker',
    'RollingHashChunker',
    'StorageManager',
    'VersionTracker',
]