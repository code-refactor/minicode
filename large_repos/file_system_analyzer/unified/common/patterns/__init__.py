"""
Pattern matching modules for the File System Analyzer unified library.

This package provides pattern matching engines, validators, and matchers
for both database file patterns and sensitive data detection.
"""

from .engine import (
    PatternEngine,
    CompiledPattern,
    PatternMatchResult
)

from .validators import (
    PatternValidator,
    SSNValidator,
    CreditCardValidator,
    EmailValidator,
    PhoneValidator,
    ValidationResult
)

from .matchers import (
    RegexMatcher,
    GlobMatcher,
    DatabasePatternMatcher,
    SensitiveDataMatcher,
    CompositeMatcher
)

__all__ = [
    # Engine
    'PatternEngine',
    'CompiledPattern',
    'PatternMatchResult',
    
    # Validators
    'PatternValidator',
    'SSNValidator',
    'CreditCardValidator',
    'EmailValidator',
    'PhoneValidator',
    'ValidationResult',
    
    # Matchers
    'RegexMatcher',
    'GlobMatcher',
    'DatabasePatternMatcher',
    'SensitiveDataMatcher',
    'CompositeMatcher',
]