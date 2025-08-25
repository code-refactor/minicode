"""Factory for selecting appropriate chunking strategies."""

from typing import Dict, Optional
from ..core.interfaces import ChunkingStrategy
from .strategies import FixedSizeChunker, RollingHashChunker, DeltaChunker


class ChunkConfig:
    """Configuration for chunking strategies."""
    
    def __init__(self, strategy: str = "rolling", **kwargs):
        """
        Initialize chunk configuration.
        
        Args:
            strategy: Strategy name (fixed, rolling, delta)
            **kwargs: Strategy-specific parameters
        """
        self.strategy = strategy
        self.params = kwargs


class ChunkerFactory:
    """Factory for creating chunking strategies."""
    
    def __init__(self):
        """Initialize chunker factory."""
        self._strategies: Dict[str, type] = {
            'fixed': FixedSizeChunker,
            'rolling': RollingHashChunker,
            'delta': DeltaChunker
        }
        self._file_type_strategies = {
            # Text files use rolling hash for better deduplication
            'text/plain': 'rolling',
            'text/html': 'rolling',
            'text/css': 'rolling',
            'text/javascript': 'rolling',
            'application/json': 'rolling',
            'application/xml': 'rolling',
            
            # Binary files use fixed size for simplicity
            'application/octet-stream': 'fixed',
            'application/pdf': 'fixed',
            'application/zip': 'fixed',
            
            # Media files use larger fixed chunks
            'image/jpeg': 'fixed',
            'image/png': 'fixed',
            'image/gif': 'fixed',
            'audio/mpeg': 'fixed',
            'audio/wav': 'fixed',
            'video/mp4': 'fixed',
            'video/avi': 'fixed',
            
            # Source code uses rolling hash
            'text/x-python': 'rolling',
            'text/x-java': 'rolling',
            'text/x-c': 'rolling',
            'text/x-cpp': 'rolling'
        }
    
    def register_strategy(self, name: str, strategy_class: type) -> None:
        """
        Register a custom chunking strategy.
        
        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        self._strategies[name] = strategy_class
    
    def get_chunker(self, file_type: Optional[str] = None, 
                   config: Optional[ChunkConfig] = None) -> ChunkingStrategy:
        """
        Get appropriate chunking strategy.
        
        Args:
            file_type: MIME type of the file
            config: Explicit configuration
        
        Returns:
            Chunking strategy instance
        """
        # Use explicit config if provided
        if config:
            return self._create_chunker(config.strategy, config.params)
        
        # Determine strategy from file type
        if file_type:
            strategy = self._file_type_strategies.get(file_type, 'rolling')
            
            # Use larger chunks for media files
            if file_type.startswith('video/'):
                return self._create_chunker('fixed', {'chunk_size': 4 * 1024 * 1024})  # 4MB
            elif file_type.startswith('audio/'):
                return self._create_chunker('fixed', {'chunk_size': 2 * 1024 * 1024})  # 2MB
            elif file_type.startswith('image/'):
                return self._create_chunker('fixed', {'chunk_size': 1024 * 1024})  # 1MB
            else:
                return self._create_chunker(strategy, {})
        
        # Default to rolling hash
        return self._create_chunker('rolling', {})
    
    def _create_chunker(self, strategy: str, params: Dict) -> ChunkingStrategy:
        """
        Create a chunker instance.
        
        Args:
            strategy: Strategy name
            params: Strategy parameters
        
        Returns:
            Chunker instance
        """
        if strategy not in self._strategies:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
        
        strategy_class = self._strategies[strategy]
        return strategy_class(**params)