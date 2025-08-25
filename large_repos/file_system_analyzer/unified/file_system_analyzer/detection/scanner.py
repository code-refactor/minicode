"""
File scanner for sensitive data detection.

This module provides the core scanner functionality to detect sensitive data
patterns in files and directories.
"""

import os
import re
import hashlib
import mimetypes
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Union, Iterator, Tuple

from pydantic import BaseModel, Field

from common.patterns.engine import PatternEngine
from common.patterns.matchers import RegexMatcher
from common.core.types import PatternDefinition, MatchType, ComplianceCategory, SensitivityLevel, Match
from file_system_analyzer.detection.patterns import (
    SensitiveDataPattern,
    PatternDefinitions,
    PatternValidators,
    ComplianceCategory as LegacyComplianceCategory,
    SensitivityLevel as LegacySensitivityLevel
)

# Fallback implementation for python-magic
class Magic:
    @staticmethod
    def from_file(path, mime=False):
        """Get file type using system 'file' command"""
        try:
            if mime:
                cmd = ["file", "--mime-type", "-b", path]
            else:
                cmd = ["file", "-b", path]
            return subprocess.check_output(cmd, universal_newlines=True).strip()
        except Exception:
            if mime:
                mime_type, _ = mimetypes.guess_type(path)
                return mime_type or "application/octet-stream"
            return "unknown"

# Use this as the magic module
magic = Magic


class ScanOptions(BaseModel):
    """Options for configuring a sensitive data scan."""
    recursive: bool = True
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    ignore_extensions: List[str] = Field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", 
        ".mp3", ".mp4", ".avi", ".mov", ".wmv", 
        ".zip", ".tar", ".gz", ".exe", ".dll"
    ])
    ignore_patterns: List[str] = Field(default_factory=lambda: [
        r"^\.git/", r"^node_modules/", r"^__pycache__/"
    ])
    max_archive_depth: int = 2
    context_lines: int = 3
    patterns: List[SensitiveDataPattern] = Field(default_factory=list)
    categories: List[ComplianceCategory] = Field(default_factory=list)
    min_sensitivity: SensitivityLevel = SensitivityLevel.LOW

    def __init__(self, **data):
        super().__init__(**data)
        # If no patterns specified but categories are, load patterns by category
        if not self.patterns and self.categories:
            for category in self.categories:
                self.patterns.extend(PatternDefinitions.get_by_category(category))
        # If neither patterns nor categories specified, load all patterns with min sensitivity
        elif not self.patterns and not self.categories:
            self.patterns = PatternDefinitions.get_by_sensitivity(self.min_sensitivity)


class SensitiveDataMatch(BaseModel):
    """A match of sensitive data found in a file."""
    pattern_name: str
    pattern_description: str
    matched_content: str
    context: str = ""
    line_number: Optional[int] = None
    byte_offset: Optional[int] = None
    category: ComplianceCategory
    sensitivity: SensitivityLevel
    validation_status: bool = True


class FileMetadata(BaseModel):
    """Metadata about a scanned file."""
    file_path: str
    file_size: int
    file_type: str
    mime_type: str
    creation_time: Optional[datetime] = None
    modification_time: datetime
    access_time: Optional[datetime] = None
    owner: Optional[str] = None
    permissions: Optional[str] = None
    hash_sha256: str


class ScanResult(BaseModel):
    """Result of scanning a file for sensitive data."""
    file_metadata: FileMetadata
    matches: List[SensitiveDataMatch] = Field(default_factory=list)
    scan_time: datetime = Field(default_factory=datetime.now)
    scan_duration: float = 0.0
    error: Optional[str] = None
    
    @property
    def has_sensitive_data(self) -> bool:
        """Check if the file contains sensitive data."""
        return len(self.matches) > 0
    
    @property
    def highest_sensitivity(self) -> Optional[SensitivityLevel]:
        """Get the highest sensitivity level found in the file."""
        if not self.matches:
            return None
        return max([match.sensitivity for match in self.matches], 
                 key=lambda s: {
                     SensitivityLevel.LOW: 1, 
                     SensitivityLevel.MEDIUM: 2, 
                     SensitivityLevel.HIGH: 3, 
                     SensitivityLevel.CRITICAL: 4
                 }[s])


class ScanSummary(BaseModel):
    """Summary of a scan operation."""
    start_time: datetime
    end_time: datetime
    duration: float
    total_files: int
    files_with_sensitive_data: int
    total_matches: int
    files_with_errors: int
    categorized_matches: Dict[ComplianceCategory, int] = Field(default_factory=dict)
    sensitivity_breakdown: Dict[SensitivityLevel, int] = Field(default_factory=dict)


class SensitiveDataScanner:
    """Scanner for detecting sensitive data in files."""
    
    def __init__(self, options: Optional[ScanOptions] = None):
        """Initialize scanner with options."""
        self.options = options or ScanOptions()
        self._ignored_patterns = [re.compile(pattern) for pattern in self.options.ignore_patterns]
        self._validators = {
            'validate_ssn': PatternValidators.validate_ssn,
            'validate_credit_card': PatternValidators.validate_credit_card
        }
    
    def should_ignore_file(self, file_path: str) -> bool:
        """Check if a file should be ignored based on options."""
        # Check file extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() in self.options.ignore_extensions:
            return True
        
        # Check ignore patterns
        for pattern in self._ignored_patterns:
            if pattern.search(file_path):
                return True
        
        # Check file size if the file exists
        if os.path.isfile(file_path):
            try:
                if os.path.getsize(file_path) > self.options.max_file_size:
                    return True
            except (OSError, IOError):
                # If we can't check the size, assume we should ignore it
                return True
        
        return False
    
    def get_file_metadata(self, file_path: str) -> FileMetadata:
        """Get metadata for a file."""
        file_stat = os.stat(file_path)
        
        # Get file type using python-magic
        try:
            mime_type = magic.from_file(file_path, mime=True)
            file_type = magic.from_file(file_path)
        except Exception:
            # Fallback to mimetypes if magic fails
            mime_type, _ = mimetypes.guess_type(file_path)
            file_type = mime_type or "unknown"
            mime_type = mime_type or "application/octet-stream"
        
        # Calculate file hash
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return FileMetadata(
            file_path=file_path,
            file_size=file_stat.st_size,
            file_type=file_type,
            mime_type=mime_type,
            modification_time=datetime.fromtimestamp(file_stat.st_mtime),
            creation_time=datetime.fromtimestamp(file_stat.st_ctime),
            access_time=datetime.fromtimestamp(file_stat.st_atime),
            hash_sha256=sha256.hexdigest()
        )
    
    def _get_context(self, lines: List[str], line_idx: int, match_text: str) -> str:
        """Get context lines around a match."""
        start = max(0, line_idx - self.options.context_lines)
        end = min(len(lines), line_idx + self.options.context_lines + 1)
        
        context_lines = []
        for i in range(start, end):
            prefix = ">" if i == line_idx else " "
            # Truncate long lines
            line = lines[i][:1000] + "..." if len(lines[i]) > 1000 else lines[i]
            context_lines.append(f"{prefix} {line}")
        
        return "\n".join(context_lines)
    
    def scan_file(self, file_path: str) -> ScanResult:
        """Scan a single file for sensitive data."""
        if self.should_ignore_file(file_path):
            metadata = self.get_file_metadata(file_path)
            return ScanResult(
                file_metadata=metadata,
                matches=[],
                scan_time=datetime.now(),
                scan_duration=0.0
            )
        
        start_time = datetime.now()
        try:
            metadata = self.get_file_metadata(file_path)
            
            # For binary files, only scan specific MIME types we know how to handle
            if not metadata.mime_type.startswith(('text/', 'application/json', 
                                                'application/xml', 'application/csv')):
                return ScanResult(
                    file_metadata=metadata,
                    matches=[],
                    scan_time=start_time,
                    scan_duration=0.0
                )
            
            matches = []
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                
                # Process the file line by line to maintain context
                for line_idx, line in enumerate(lines):
                    for pattern in self.options.patterns:
                        for match in pattern.match(line):
                            # Validate the match if a validation function is specified
                            validation_status = True
                            if pattern.validation_func and pattern.validation_func in self._validators:
                                validation_status = self._validators[pattern.validation_func](match)
                            
                            # Only include validated matches
                            if validation_status:
                                context = self._get_context(lines, line_idx, match)
                                
                                matches.append(SensitiveDataMatch(
                                    pattern_name=pattern.name,
                                    pattern_description=pattern.description,
                                    matched_content=match,
                                    context=context,
                                    line_number=line_idx + 1,  # 1-based line numbers
                                    byte_offset=None,  # Could calculate, but not needed for text files
                                    category=pattern.category,
                                    sensitivity=pattern.sensitivity,
                                    validation_status=validation_status
                                ))
            except UnicodeDecodeError:
                # If we can't decode as text, skip it
                pass
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return ScanResult(
                file_metadata=metadata,
                matches=matches,
                scan_time=start_time,
                scan_duration=duration
            )
        
        except Exception as e:
            # Catch any errors and include them in the result
            try:
                metadata = self.get_file_metadata(file_path)
            except Exception:
                # If we can't get metadata, create minimal metadata
                metadata = FileMetadata(
                    file_path=file_path,
                    file_size=0,
                    file_type="unknown",
                    mime_type="unknown",
                    modification_time=datetime.now(),
                    hash_sha256=""
                )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return ScanResult(
                file_metadata=metadata,
                matches=[],
                scan_time=start_time,
                scan_duration=duration,
                error=str(e)
            )
    
    def scan_directory(self, directory_path: str) -> Iterator[ScanResult]:
        """Scan a directory for sensitive data, yielding results for each file."""
        for root, dirs, files in os.walk(directory_path):
            # Skip directories that match ignore patterns
            dirs[:] = [d for d in dirs if not self.should_ignore_file(os.path.join(root, d))]
            
            for file in files:
                file_path = os.path.join(root, file)
                if not self.should_ignore_file(file_path):
                    yield self.scan_file(file_path)
            
            # Break if not recursive
            if not self.options.recursive:
                break
    
    def summarize_scan(self, results: List[ScanResult]) -> ScanSummary:
        """Create a summary of scan results."""
        if not results:
            return ScanSummary(
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0.0,
                total_files=0,
                files_with_sensitive_data=0,
                total_matches=0,
                files_with_errors=0
            )
        
        start_time = min(r.scan_time for r in results)
        end_time = max(r.scan_time for r in results)
        duration = sum(r.scan_duration for r in results)
        
        files_with_sensitive_data = sum(1 for r in results if r.has_sensitive_data)
        total_matches = sum(len(r.matches) for r in results)
        files_with_errors = sum(1 for r in results if r.error is not None)
        
        # Categorize matches
        categorized_matches = {}
        sensitivity_breakdown = {}
        
        for result in results:
            for match in result.matches:
                # Count by category
                if match.category in categorized_matches:
                    categorized_matches[match.category] += 1
                else:
                    categorized_matches[match.category] = 1
                
                # Count by sensitivity
                if match.sensitivity in sensitivity_breakdown:
                    sensitivity_breakdown[match.sensitivity] += 1
                else:
                    sensitivity_breakdown[match.sensitivity] = 1
        
        return ScanSummary(
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            total_files=len(results),
            files_with_sensitive_data=files_with_sensitive_data,
            total_matches=total_matches,
            files_with_errors=files_with_errors,
            categorized_matches=categorized_matches,
            sensitivity_breakdown=sensitivity_breakdown
        )