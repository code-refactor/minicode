"""
Core modules for the File System Analyzer unified library.

This package provides the foundational classes, types, and abstractions
used throughout the file system analyzer.
"""

# Core types and enums
from .types import (
    ScanStatus, Priority, SensitivityLevel, FileCategory, DatabaseEngine,
    ComplianceCategory, MatchType, ExportFormat, HashAlgorithm,
    AnalysisType, FileInfo, PatternDefinition, Match, Recommendation,
    FilePath, DEFAULT_MAX_FILE_SIZE, DEFAULT_CONTEXT_LINES, DEFAULT_MAX_DEPTH,
    DEFAULT_THREAD_POOL_SIZE, COMMON_IGNORE_PATTERNS, FILE_EXTENSIONS
)

# Base classes
from .base import (
    BaseComponent, BaseScanner, BaseAnalyzer, BasePatternMatcher,
    BaseExporter, BaseResult, BaseFileInfo, BaseScanResult, 
    BaseAnalysisResult, ConfigurableComponent
)

# Result classes
from .results import (
    DatabaseFileInfo, SecurityFileInfo, SensitiveDataMatch, DatabaseMatch,
    SensitiveDataScanResult, DatabaseFileScanResult, SensitiveDataAnalysisResult,
    DatabaseAnalysisResult, OptimizationRecommendation, ComplianceRecommendation,
    AnalysisSummary
)

# Configuration options
from .options import (
    BaseOptions, ScanOptions, PatternMatchingOptions, SensitiveDataScanOptions,
    DatabaseScanOptions, ExportOptions, CacheOptions, NotificationOptions,
    ComprehensiveOptions, PresetConfigurations
)

__all__ = [
    # Types
    'ScanStatus', 'Priority', 'SensitivityLevel', 'FileCategory', 'DatabaseEngine',
    'ComplianceCategory', 'MatchType', 'ExportFormat', 'HashAlgorithm',
    'AnalysisType', 'FileInfo', 'PatternDefinition', 'Match', 'Recommendation',
    'FilePath', 'DEFAULT_MAX_FILE_SIZE', 'DEFAULT_CONTEXT_LINES', 'DEFAULT_MAX_DEPTH',
    'DEFAULT_THREAD_POOL_SIZE', 'COMMON_IGNORE_PATTERNS', 'FILE_EXTENSIONS',
    
    # Base classes
    'BaseComponent', 'BaseScanner', 'BaseAnalyzer', 'BasePatternMatcher',
    'BaseExporter', 'BaseResult', 'BaseFileInfo', 'BaseScanResult', 
    'BaseAnalysisResult', 'ConfigurableComponent',
    
    # Results
    'DatabaseFileInfo', 'SecurityFileInfo', 'SensitiveDataMatch', 'DatabaseMatch',
    'SensitiveDataScanResult', 'DatabaseFileScanResult', 'SensitiveDataAnalysisResult',
    'DatabaseAnalysisResult', 'OptimizationRecommendation', 'ComplianceRecommendation',
    'AnalysisSummary',
    
    # Options
    'BaseOptions', 'ScanOptions', 'PatternMatchingOptions', 'SensitiveDataScanOptions',
    'DatabaseScanOptions', 'ExportOptions', 'CacheOptions', 'NotificationOptions',
    'ComprehensiveOptions', 'PresetConfigurations',
]
