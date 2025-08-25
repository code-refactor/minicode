"""
Asset Optimization Framework for GameVault.

This package provides specialized handling for game assets using content-aware chunking, 
delta compression, and deduplication optimized for common game file formats.
"""

from gamevault.asset_optimization.chunking import (AssetChunker,
                                                 AssetChunkerFactory,
                                                 AudioChunker, ModelChunker,
                                                 TextureChunker)
from gamevault.asset_optimization.compressor import (AssetCompressor,
                                                   AssetCompressorFactory,
                                                   AudioCompressor,
                                                   DeltaCompressor,
                                                   ModelCompressor,
                                                   TextureCompressor)
from gamevault.asset_optimization.deduplication import (AssetDeduplicator,
                                                      ChunkHashIndex)
from gamevault.asset_optimization.manager import AssetOptimizationManager

__all__ = [
    'AssetChunker',
    'AssetChunkerFactory',
    'AudioChunker',
    'ModelChunker',
    'TextureChunker',
    'AssetCompressor',
    'AssetCompressorFactory',
    'AudioCompressor',
    'DeltaCompressor',
    'ModelCompressor',
    'TextureCompressor',
    'AssetDeduplicator',
    'ChunkHashIndex',
    'AssetOptimizationManager',
]