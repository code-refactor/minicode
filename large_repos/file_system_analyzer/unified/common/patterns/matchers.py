"""
Pattern matchers for the File System Analyzer unified library.

This module provides specialized matchers for different types of patterns.
"""

import re
import fnmatch
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path

from ..core.base import BasePatternMatcher
from ..core.types import Match, PatternDefinition, DatabaseEngine, FileCategory, ComplianceCategory, FilePath
from .engine import PatternEngine, CompiledPattern


class RegexMatcher(BasePatternMatcher):
    """Regex pattern matcher."""
    
    def __init__(self):
        super().__init__()
        self._patterns: Dict[str, re.Pattern] = {}
        
    def match(self, content: str) -> List[Match]:
        """Match regex patterns in content."""
        matches = []
        for name, pattern in self._patterns.items():
            for match_obj in pattern.finditer(content):
                match = Match(
                    pattern_name=name,
                    matched_content=match_obj.group(),
                    file_path=Path(""),
                    byte_offset=match_obj.start()
                )
                matches.append(match)
        return matches
        
    def add_pattern(self, pattern: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a regex pattern."""
        name = metadata.get('name', f'pattern_{len(self._patterns)}') if metadata else f'pattern_{len(self._patterns)}'
        self._patterns[name] = re.compile(pattern)
        
    def remove_pattern(self, pattern: str) -> bool:
        """Remove a pattern by name."""
        if pattern in self._patterns:
            del self._patterns[pattern]
            return True
        return False


class GlobMatcher(BasePatternMatcher):
    """Glob pattern matcher for file paths."""
    
    def __init__(self):
        super().__init__()
        self._patterns: Dict[str, str] = {}
        
    def match(self, content: str) -> List[Match]:
        """Match glob patterns against content (typically file paths)."""
        matches = []
        for name, pattern in self._patterns.items():
            if fnmatch.fnmatch(content, pattern):
                match = Match(
                    pattern_name=name,
                    matched_content=content,
                    file_path=Path(content)
                )
                matches.append(match)
        return matches
        
    def add_pattern(self, pattern: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a glob pattern."""
        name = metadata.get('name', f'glob_{len(self._patterns)}') if metadata else f'glob_{len(self._patterns)}'
        self._patterns[name] = pattern
        
    def remove_pattern(self, pattern: str) -> bool:
        """Remove a pattern by name."""
        if pattern in self._patterns:
            del self._patterns[pattern]
            return True
        return False


class DatabasePatternMatcher:
    """Specialized matcher for database file patterns."""
    
    def __init__(self):
        self.patterns = self._load_database_patterns()
        
    def _load_database_patterns(self) -> Dict[DatabaseEngine, Dict[FileCategory, List[str]]]:
        """Load predefined database file patterns."""
        return {
            DatabaseEngine.MYSQL: {
                FileCategory.DATA: [r".*\.ibd$", r".*\.MYD$"],
                FileCategory.LOG: [r".*bin\.([0-9]+)$", r"ib_logfile[0-9]+$"],
                FileCategory.CONFIG: [r".*\.cnf$", r"my\.cnf$"]
            },
            DatabaseEngine.POSTGRESQL: {
                FileCategory.DATA: [r"[0-9]+$", r"[0-9]+\.[0-9]+$"],
                FileCategory.LOG: [r"postgresql-.*\.log$", r"pg_wal/.*$"],
                FileCategory.CONFIG: [r"postgresql\.conf$", r"pg_hba\.conf$"]
            }
        }
        
    def match_file_path(self, file_path: FilePath) -> List[Match]:
        """Match database patterns against a file path."""
        matches = []
        path_str = str(file_path)
        
        for engine, categories in self.patterns.items():
            for category, patterns in categories.items():
                for pattern in patterns:
                    if re.search(pattern, path_str):
                        match = Match(
                            pattern_name=f"{engine.value}_{category.value}",
                            matched_content=path_str,
                            file_path=Path(file_path),
                            category=ComplianceCategory.OTHER  # Database patterns aren't compliance-related
                        )
                        matches.append(match)
                        
        return matches


class SensitiveDataMatcher:
    """Specialized matcher for sensitive data patterns."""
    
    def __init__(self):
        self.engine = PatternEngine()
        self._load_sensitive_patterns()
        
    def _load_sensitive_patterns(self):
        """Load predefined sensitive data patterns."""
        from ..core.types import PatternDefinition, MatchType, SensitivityLevel, ComplianceCategory
        
        patterns = [
            PatternDefinition(
                name="ssn",
                description="US Social Security Number",
                pattern=r"\b(?!000|666|9\d{2})([0-8]\d{2}|7([0-6]\d))-(?!00)(\d{2})-(?!0000)(\d{4})\b",
                match_type=MatchType.REGEX,
                sensitivity=SensitivityLevel.HIGH,
                category=ComplianceCategory.PII
            ),
            PatternDefinition(
                name="credit_card",
                description="Credit card number",
                pattern=r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
                match_type=MatchType.REGEX,
                sensitivity=SensitivityLevel.HIGH,
                category=ComplianceCategory.PCI
            ),
            PatternDefinition(
                name="email",
                description="Email address",
                pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                match_type=MatchType.REGEX,
                sensitivity=SensitivityLevel.MEDIUM,
                category=ComplianceCategory.PII
            )
        ]
        
        for pattern in patterns:
            self.engine.add_pattern(pattern)
            
    def match(self, content: str, file_path: Optional[FilePath] = None) -> List[Match]:
        """Match sensitive data patterns in content."""
        results = self.engine.match_content(content, file_path)
        
        all_matches = []
        for result in results:
            all_matches.extend(result.matches)
            
        return all_matches


class CompositeMatcher(BasePatternMatcher):
    """Composite matcher that combines multiple matchers."""
    
    def __init__(self):
        super().__init__()
        self._matchers: List[BasePatternMatcher] = []
        
    def add_matcher(self, matcher: BasePatternMatcher):
        """Add a matcher to the composite."""
        self._matchers.append(matcher)
        
    def remove_matcher(self, matcher: BasePatternMatcher):
        """Remove a matcher from the composite."""
        if matcher in self._matchers:
            self._matchers.remove(matcher)
            
    def match(self, content: str) -> List[Match]:
        """Match using all registered matchers."""
        all_matches = []
        for matcher in self._matchers:
            try:
                matches = matcher.match(content)
                all_matches.extend(matches)
            except Exception as e:
                self.logger.error(f"Error in matcher {type(matcher).__name__}: {e}")
                continue
        return all_matches
        
    def add_pattern(self, pattern: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add pattern to the first available matcher."""
        if self._matchers:
            self._matchers[0].add_pattern(pattern, metadata)
            
    def remove_pattern(self, pattern: str) -> bool:
        """Remove pattern from all matchers."""
        removed = False
        for matcher in self._matchers:
            if matcher.remove_pattern(pattern):
                removed = True
        return removed