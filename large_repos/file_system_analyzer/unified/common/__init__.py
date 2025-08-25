"""
File System Analyzer Unified Common Library

This library provides shared functionality for both the Security Auditor and
Database Administrator personas of the File System Analyzer, including:

- Core types, base classes, and abstractions
- File system utilities and operations
- Cryptographic and security functions
- Caching and parallel processing utilities
- Pattern matching and validation engines
- Export capabilities for multiple formats
- Standard interfaces for file system access and APIs

The library is designed to be modular and extensible, allowing both personas
to leverage common functionality while maintaining their specific use cases.
"""

# Core functionality
from .core import (
    # Types and enums
    ScanStatus, Priority, SensitivityLevel, FileCategory, DatabaseEngine,
    ComplianceCategory, MatchType, ExportFormat, HashAlgorithm, AnalysisType,
    FileInfo, PatternDefinition, Match, Recommendation,
    
    # Base classes
    BaseComponent, BaseScanner, BaseAnalyzer, BasePatternMatcher, BaseExporter,
    BaseResult, BaseFileInfo, BaseScanResult, BaseAnalysisResult,
    
    # Result classes
    DatabaseFileInfo, SecurityFileInfo, SensitiveDataMatch, DatabaseMatch,
    SensitiveDataScanResult, DatabaseFileScanResult, SensitiveDataAnalysisResult,
    DatabaseAnalysisResult, OptimizationRecommendation, ComplianceRecommendation,
    
    # Configuration
    ScanOptions, PatternMatchingOptions, SensitiveDataScanOptions,
    DatabaseScanOptions, ExportOptions, CacheOptions, PresetConfigurations
)

# Utilities
from .utils import (
    # File utilities
    get_file_stats, find_files, calculate_directory_size, get_disk_usage,
    estimate_file_growth_rate, is_binary_file, get_mime_type, get_file_category, hash_file, FileSystemWalker,
    
    # Crypto utilities  
    SimpleCryptoProvider, hash_data, generate_secure_id,
    create_signature, verify_signature,
    
    # Cache utilities
    CacheManager, FileCacheBackend, MemoryCacheBackend, CacheEntry,
    
    # Parallel processing
    ParallelProcessor, parallel_map, parallel_filter,
    ThreadPoolManager, ProcessPoolManager
)

# Pattern matching
from .patterns import (
    PatternEngine, CompiledPattern, PatternMatchResult,
    PatternValidator, SSNValidator, CreditCardValidator, EmailValidator,
    RegexMatcher, GlobMatcher, DatabasePatternMatcher, SensitiveDataMatcher
)

# Export functionality
from .export import (
    BaseExporter, JsonExporter, CsvExporter, HtmlExporter, MultiFormatExporter
)

# Interfaces
from .interfaces import (
    FileSystemInterface, EnhancedFileSystemInterface, BaseAPI, AnalysisAPI
)

__version__ = "1.0.0"

__all__ = [
    # Core types and classes
    'ScanStatus', 'Priority', 'SensitivityLevel', 'FileCategory', 'DatabaseEngine',
    'ComplianceCategory', 'MatchType', 'ExportFormat', 'HashAlgorithm', 'AnalysisType',
    'FileInfo', 'PatternDefinition', 'Match', 'Recommendation',
    'BaseComponent', 'BaseScanner', 'BaseAnalyzer', 'BasePatternMatcher', 'BaseExporter',
    'BaseResult', 'BaseFileInfo', 'BaseScanResult', 'BaseAnalysisResult',
    'DatabaseFileInfo', 'SecurityFileInfo', 'SensitiveDataMatch', 'DatabaseMatch',
    'SensitiveDataScanResult', 'DatabaseFileScanResult', 'SensitiveDataAnalysisResult',
    'DatabaseAnalysisResult', 'OptimizationRecommendation', 'ComplianceRecommendation',
    'ScanOptions', 'PatternMatchingOptions', 'SensitiveDataScanOptions',
    'DatabaseScanOptions', 'ExportOptions', 'CacheOptions', 'PresetConfigurations',
    
    # Utilities
    'get_file_stats', 'find_files', 'calculate_directory_size', 'get_disk_usage',
    'estimate_file_growth_rate', 'is_binary_file', 'get_mime_type', 'get_file_category', 'hash_file', 'FileSystemWalker',
    'SimpleCryptoProvider', 'hash_data', 'generate_secure_id',
    'create_signature', 'verify_signature',
    'CacheManager', 'FileCacheBackend', 'MemoryCacheBackend', 'CacheEntry',
    'ParallelProcessor', 'parallel_map', 'parallel_filter',
    'ThreadPoolManager', 'ProcessPoolManager',
    
    # Pattern matching
    'PatternEngine', 'CompiledPattern', 'PatternMatchResult',
    'PatternValidator', 'SSNValidator', 'CreditCardValidator', 'EmailValidator',
    'RegexMatcher', 'GlobMatcher', 'DatabasePatternMatcher', 'SensitiveDataMatcher',
    
    # Export
    'BaseExporter', 'JsonExporter', 'CsvExporter', 'HtmlExporter', 'MultiFormatExporter',
    
    # Interfaces
    'FileSystemInterface', 'EnhancedFileSystemInterface', 'BaseAPI', 'AnalysisAPI',
]
