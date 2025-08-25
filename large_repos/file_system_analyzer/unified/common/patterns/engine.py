"""
Unified pattern matching engine for the File System Analyzer unified library.

This module provides a comprehensive pattern matching engine that supports
multiple pattern types (regex, glob, exact) and integrates with validation.
"""

import re
import fnmatch
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Pattern, Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from ..core.types import (
    MatchType, PatternDefinition, Match, SensitivityLevel, 
    Priority, ComplianceCategory, FilePath
)
from ..core.base import BasePatternMatcher

logger = logging.getLogger(__name__)


@dataclass
class CompiledPattern:
    """A compiled pattern ready for matching."""
    definition: PatternDefinition
    regex: Optional[Pattern] = None
    glob_pattern: Optional[str] = None
    exact_string: Optional[str] = None
    
    def __post_init__(self):
        """Compile the pattern based on its type."""
        try:
            if self.definition.match_type == MatchType.REGEX:
                flags = 0 if self.definition.case_sensitive else re.IGNORECASE
                self.regex = re.compile(self.definition.pattern, flags)
            elif self.definition.match_type == MatchType.GLOB:
                self.glob_pattern = self.definition.pattern
            elif self.definition.match_type == MatchType.EXACT:
                self.exact_string = self.definition.pattern
                if not self.definition.case_sensitive:
                    self.exact_string = self.exact_string.lower()
            else:
                logger.warning(f"Unknown match type: {self.definition.match_type}")
        except re.error as e:
            logger.error(f"Failed to compile regex pattern '{self.definition.pattern}': {e}")
            self.regex = None


@dataclass
class PatternMatchResult:
    """Result of a pattern match operation."""
    pattern: CompiledPattern
    matches: List[Match] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    
    @property
    def has_matches(self) -> bool:
        """Check if there are any matches."""
        return len(self.matches) > 0
        
    @property
    def match_count(self) -> int:
        """Get the number of matches."""
        return len(self.matches)


class PatternEngine:
    """
    Unified pattern matching engine supporting multiple pattern types.
    """
    
    def __init__(
        self,
        timeout_seconds: float = 5.0,
        max_matches_per_pattern: Optional[int] = None,
        enable_validation: bool = True
    ):
        """
        Initialize the pattern engine.
        
        Args:
            timeout_seconds: Timeout for pattern matching operations
            max_matches_per_pattern: Maximum matches per pattern (None for unlimited)
            enable_validation: Whether to enable pattern validation
        """
        self.timeout_seconds = timeout_seconds
        self.max_matches_per_pattern = max_matches_per_pattern
        self.enable_validation = enable_validation
        self._compiled_patterns: Dict[str, CompiledPattern] = {}
        self._validators: Dict[str, Callable[[str], bool]] = {}
        
    def add_pattern(self, definition: PatternDefinition) -> bool:
        """
        Add a pattern definition to the engine.
        
        Args:
            definition: Pattern definition to add
            
        Returns:
            True if pattern was added successfully, False otherwise
        """
        try:
            compiled_pattern = CompiledPattern(definition)
            
            # Validate that the pattern compiled successfully
            if (definition.match_type == MatchType.REGEX and 
                compiled_pattern.regex is None):
                logger.error(f"Failed to add pattern '{definition.name}' - regex compilation failed")
                return False
                
            self._compiled_patterns[definition.name] = compiled_pattern
            
            # Register validator if specified
            if definition.validation_func and hasattr(self, definition.validation_func):
                validator = getattr(self, definition.validation_func)
                if callable(validator):
                    self._validators[definition.name] = validator
                    
            return True
            
        except Exception as e:
            logger.error(f"Failed to add pattern '{definition.name}': {e}")
            return False
            
    def remove_pattern(self, pattern_name: str) -> bool:
        """
        Remove a pattern from the engine.
        
        Args:
            pattern_name: Name of the pattern to remove
            
        Returns:
            True if pattern was removed, False if not found
        """
        if pattern_name in self._compiled_patterns:
            del self._compiled_patterns[pattern_name]
            if pattern_name in self._validators:
                del self._validators[pattern_name]
            return True
        return False
        
    def get_patterns(self) -> List[str]:
        """Get list of all pattern names."""
        return list(self._compiled_patterns.keys())
        
    def match_content(
        self,
        content: str,
        file_path: Optional[FilePath] = None,
        pattern_filter: Optional[Callable[[PatternDefinition], bool]] = None
    ) -> List[PatternMatchResult]:
        """
        Match patterns against content.
        
        Args:
            content: Content to search for patterns
            file_path: Path to the file being analyzed (for context)
            pattern_filter: Optional filter function for patterns
            
        Returns:
            List of pattern match results
        """
        results = []
        
        for pattern_name, compiled_pattern in self._compiled_patterns.items():
            # Apply pattern filter if specified
            if pattern_filter and not pattern_filter(compiled_pattern.definition):
                continue
                
            try:
                import time
                start_time = time.time()
                
                # Perform the matching
                matches = self._match_single_pattern(
                    compiled_pattern, content, file_path
                )
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                result = PatternMatchResult(
                    pattern=compiled_pattern,
                    matches=matches,
                    execution_time_ms=execution_time_ms
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error matching pattern '{pattern_name}': {e}")
                error_result = PatternMatchResult(
                    pattern=compiled_pattern,
                    matches=[],
                    error=str(e)
                )
                results.append(error_result)
                
        return results
        
    def match_file_path(
        self,
        file_path: FilePath,
        pattern_filter: Optional[Callable[[PatternDefinition], bool]] = None
    ) -> List[PatternMatchResult]:
        """
        Match patterns against a file path (for database file detection).
        
        Args:
            file_path: File path to match against
            pattern_filter: Optional filter function for patterns
            
        Returns:
            List of pattern match results
        """
        path_str = str(file_path)
        return self.match_content(path_str, file_path, pattern_filter)
        
    def _match_single_pattern(
        self,
        compiled_pattern: CompiledPattern,
        content: str,
        file_path: Optional[FilePath] = None
    ) -> List[Match]:
        """
        Match a single compiled pattern against content.
        
        Args:
            compiled_pattern: Compiled pattern to match
            content: Content to search
            file_path: Optional file path for context
            
        Returns:
            List of matches found
        """
        matches = []
        definition = compiled_pattern.definition
        
        if definition.match_type == MatchType.REGEX and compiled_pattern.regex:
            # Regex matching
            for match_obj in compiled_pattern.regex.finditer(content):
                matched_text = match_obj.group()
                
                # Create match object
                match = Match(
                    pattern_name=definition.name,
                    matched_content=matched_text,
                    file_path=file_path or Path(""),
                    line_number=None,  # Could calculate if needed
                    column_number=match_obj.start(),
                    byte_offset=match_obj.start(),
                    category=definition.category,
                    sensitivity=definition.sensitivity,
                    priority=definition.priority
                )
                
                # Validate match if validator is available
                if self.enable_validation and definition.name in self._validators:
                    try:
                        match.validation_status = self._validators[definition.name](matched_text)
                        if not match.validation_status:
                            continue  # Skip invalid matches
                    except Exception as e:
                        logger.warning(f"Validation failed for match '{matched_text}': {e}")
                        match.validation_status = False
                        
                matches.append(match)
                
                # Check max matches limit
                if (self.max_matches_per_pattern and 
                    len(matches) >= self.max_matches_per_pattern):
                    break
                    
        elif definition.match_type == MatchType.GLOB and compiled_pattern.glob_pattern:
            # Glob matching (typically for file paths)
            if fnmatch.fnmatch(content, compiled_pattern.glob_pattern):
                match = Match(
                    pattern_name=definition.name,
                    matched_content=content,
                    file_path=file_path or Path(""),
                    category=definition.category,
                    sensitivity=definition.sensitivity,
                    priority=definition.priority,
                    validation_status=True
                )
                matches.append(match)
                
        elif definition.match_type == MatchType.EXACT and compiled_pattern.exact_string:
            # Exact string matching
            search_content = content if definition.case_sensitive else content.lower()
            
            if compiled_pattern.exact_string in search_content:
                match = Match(
                    pattern_name=definition.name,
                    matched_content=definition.pattern,  # Use original pattern
                    file_path=file_path or Path(""),
                    category=definition.category,
                    sensitivity=definition.sensitivity,
                    priority=definition.priority,
                    validation_status=True
                )
                matches.append(match)
                
        return matches
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        total_patterns = len(self._compiled_patterns)
        patterns_by_type = {}
        patterns_by_sensitivity = {}
        patterns_by_category = {}
        
        for compiled_pattern in self._compiled_patterns.values():
            definition = compiled_pattern.definition
            
            # Count by match type
            match_type = definition.match_type.value
            patterns_by_type[match_type] = patterns_by_type.get(match_type, 0) + 1
            
            # Count by sensitivity
            sensitivity = definition.sensitivity.value
            patterns_by_sensitivity[sensitivity] = patterns_by_sensitivity.get(sensitivity, 0) + 1
            
            # Count by category
            if definition.category:
                category = definition.category.value
                patterns_by_category[category] = patterns_by_category.get(category, 0) + 1
                
        return {
            "total_patterns": total_patterns,
            "patterns_by_type": patterns_by_type,
            "patterns_by_sensitivity": patterns_by_sensitivity,
            "patterns_by_category": patterns_by_category,
            "validators_registered": len(self._validators)
        }
        
    def export_patterns(self, output_path: FilePath) -> bool:
        """
        Export pattern definitions to a file.
        
        Args:
            output_path: Path to export patterns to
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            import json
            from dataclasses import asdict
            
            patterns_data = []
            for compiled_pattern in self._compiled_patterns.values():
                pattern_dict = asdict(compiled_pattern.definition)
                patterns_data.append(pattern_dict)
                
            export_data = {
                "patterns": patterns_data,
                "metadata": {
                    "export_timestamp": str(datetime.now()),
                    "total_patterns": len(patterns_data)
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to export patterns: {e}")
            return False
            
    def import_patterns(self, input_path: FilePath) -> int:
        """
        Import pattern definitions from a file.
        
        Args:
            input_path: Path to import patterns from
            
        Returns:
            Number of patterns imported successfully
        """
        try:
            import json
            
            with open(input_path, 'r') as f:
                data = json.load(f)
                
            imported_count = 0
            patterns_data = data.get("patterns", [])
            
            for pattern_dict in patterns_data:
                try:
                    # Convert back to PatternDefinition
                    definition = PatternDefinition(**pattern_dict)
                    if self.add_pattern(definition):
                        imported_count += 1
                except Exception as e:
                    logger.warning(f"Failed to import pattern: {e}")
                    continue
                    
            logger.info(f"Imported {imported_count} patterns from {input_path}")
            return imported_count
            
        except Exception as e:
            logger.error(f"Failed to import patterns from {input_path}: {e}")
            return 0