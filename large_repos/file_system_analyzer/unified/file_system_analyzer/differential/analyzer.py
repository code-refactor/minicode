"""
Differential analysis for detecting changes in sensitive data.

This module provides functionality to compare scan results over time
to identify newly added, modified, or removed sensitive content.
"""

import os
import json
import pickle
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union, Tuple

from pydantic import BaseModel, Field

from file_system_analyzer.detection.scanner import ScanResult, SensitiveDataMatch, FileMetadata
from file_system_analyzer.detection.patterns import ComplianceCategory, SensitivityLevel
from file_system_analyzer.utils.crypto import CryptoProvider


class ChangeType(str, Enum):
    """Types of changes detected in differential analysis."""
    NEW_FILE = "new_file"
    MODIFIED_FILE = "modified_file"
    REMOVED_FILE = "removed_file"
    NEW_MATCH = "new_match"
    REMOVED_MATCH = "removed_match"
    FILE_UNCHANGED = "file_unchanged"


class BaselineEntry(BaseModel):
    """Entry in a baseline for a single file."""
    file_path: str
    file_hash: str
    last_modified: datetime
    matches: List[SensitiveDataMatch] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScanBaseline(BaseModel):
    """Baseline of a previous scan for differential analysis."""
    baseline_id: str
    creation_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    description: Optional[str] = None
    files: Dict[str, BaselineEntry] = Field(default_factory=dict)
    verification_info: Optional[Dict[str, Any]] = None
    
    def sign(self, crypto_provider: CryptoProvider) -> None:
        """Sign the baseline with cryptographic verification."""
        # Create a canonical representation of the baseline
        baseline_data = self.model_dump(exclude={"verification_info"})
        baseline_json = json.dumps(baseline_data, sort_keys=True, default=str).encode()
        
        # Create a hash of the baseline
        baseline_hash = crypto_provider.secure_hash(baseline_json)
        
        # Create a timestamped signature
        signature = crypto_provider.timestamp_signature(baseline_json)
        
        self.verification_info = {
            "baseline_hash": baseline_hash,
            "signature": signature,
            "verification_method": "crypto_provider",
            "key_id": crypto_provider.key_id
        }
    
    def verify(self, crypto_provider: CryptoProvider) -> bool:
        """Verify the cryptographic signature of the baseline."""
        if not self.verification_info:
            return False
            
        # Recreate the baseline data without verification_info
        baseline_data = self.model_dump(exclude={"verification_info"})
        baseline_json = json.dumps(baseline_data, sort_keys=True, default=str).encode()
        
        # Verify the hash
        calculated_hash = crypto_provider.secure_hash(baseline_json)
        stored_hash = self.verification_info.get("baseline_hash")
        if calculated_hash != stored_hash:
            return False
            
        # Verify the signature
        signature = self.verification_info.get("signature", {})
        return crypto_provider.verify_timestamped_signature(baseline_json, signature)


class FileChange(BaseModel):
    """Changes detected in a file between baseline and current scan."""
    file_path: str
    change_type: ChangeType
    baseline_hash: Optional[str] = None
    current_hash: Optional[str] = None
    baseline_modified: Optional[datetime] = None
    current_modified: Optional[datetime] = None
    new_matches: List[SensitiveDataMatch] = Field(default_factory=list)
    removed_matches: List[SensitiveDataMatch] = Field(default_factory=list)
    
    @property
    def has_sensitive_changes(self) -> bool:
        """Check if there are sensitive data changes in this file."""
        return len(self.new_matches) > 0 or len(self.removed_matches) > 0


class DifferentialScanResult(BaseModel):
    """Results of a differential scan comparing current results to a baseline."""
    baseline_id: str
    scan_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    changes: List[FileChange] = Field(default_factory=list)
    
    @property
    def new_files(self) -> List[FileChange]:
        """Get all new files."""
        return [c for c in self.changes if c.change_type == ChangeType.NEW_FILE]
    
    @property
    def modified_files(self) -> List[FileChange]:
        """Get all modified files."""
        return [c for c in self.changes if c.change_type == ChangeType.MODIFIED_FILE]
    
    @property
    def removed_files(self) -> List[FileChange]:
        """Get all removed files."""
        return [c for c in self.changes if c.change_type == ChangeType.REMOVED_FILE]
    
    @property
    def unchanged_files(self) -> List[FileChange]:
        """Get all unchanged files."""
        return [c for c in self.changes if c.change_type == ChangeType.FILE_UNCHANGED]
    
    @property
    def files_with_new_matches(self) -> List[FileChange]:
        """Get all files with new sensitive data matches."""
        return [c for c in self.changes if len(c.new_matches) > 0]
    
    @property
    def files_with_removed_matches(self) -> List[FileChange]:
        """Get all files with removed sensitive data matches."""
        return [c for c in self.changes if len(c.removed_matches) > 0]
    
    @property
    def has_sensitive_changes(self) -> bool:
        """Check if there are any sensitive data changes."""
        return any(c.has_sensitive_changes for c in self.changes)
    
    @property
    def total_new_matches(self) -> int:
        """Get the total number of new sensitive data matches."""
        return sum(len(c.new_matches) for c in self.changes)
    
    @property
    def total_removed_matches(self) -> int:
        """Get the total number of removed sensitive data matches."""
        return sum(len(c.removed_matches) for c in self.changes)


class DifferentialAnalyzer:
    """Analyzer for comparing scan results to a baseline."""
    
    def create_baseline(
        self, 
        scan_results: List[ScanResult], 
        name: str, 
        description: Optional[str] = None,
        baseline_id: Optional[str] = None,
        crypto_provider: Optional[CryptoProvider] = None
    ) -> ScanBaseline:
        """Create a baseline from scan results."""
        baseline = ScanBaseline(
            baseline_id=baseline_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            name=name,
            description=description,
            files={}
        )
        
        # Add each file to the baseline
        for result in scan_results:
            file_path = result.file_metadata.file_path
            
            baseline.files[file_path] = BaselineEntry(
                file_path=file_path,
                file_hash=result.file_metadata.hash_sha256,
                last_modified=result.file_metadata.modification_time,
                matches=result.matches,
                metadata={
                    "file_size": result.file_metadata.file_size,
                    "file_type": result.file_metadata.file_type,
                    "mime_type": result.file_metadata.mime_type,
                    "scan_time": result.scan_time.isoformat()
                }
            )
        
        # Sign the baseline if a crypto provider is available
        if crypto_provider:
            baseline.sign(crypto_provider)
            
        return baseline
    
    def save_baseline(self, baseline: ScanBaseline, file_path: str) -> None:
        """Save a baseline to a file."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save as JSON for interoperability
        with open(file_path, 'w') as f:
            f.write(json.dumps(baseline.model_dump(), default=str))
    
    def load_baseline(self, file_path: str) -> ScanBaseline:
        """Load a baseline from a file."""
        with open(file_path, 'r') as f:
            data = json.loads(f.read())
        
        # Convert dates back to datetime objects
        data["creation_time"] = datetime.fromisoformat(data["creation_time"])
        
        # Convert file entries
        files = {}
        for file_path, entry_data in data["files"].items():
            entry_data["last_modified"] = datetime.fromisoformat(entry_data["last_modified"])
            
            # Convert matches
            matches = []
            for match_data in entry_data["matches"]:
                matches.append(SensitiveDataMatch(**match_data))
            
            entry_data["matches"] = matches
            files[file_path] = BaselineEntry(**entry_data)
        
        data["files"] = files
        
        return ScanBaseline(**data)
    
    def compare_to_baseline(
        self, 
        baseline: ScanBaseline, 
        current_results: List[ScanResult]
    ) -> DifferentialScanResult:
        """Compare current scan results to a baseline."""
        diff_result = DifferentialScanResult(
            baseline_id=baseline.baseline_id,
            changes=[]
        )
        
        # Create a mapping of file paths to current results for efficient lookup
        current_files = {r.file_metadata.file_path: r for r in current_results}
        
        # Create sets of file paths for faster comparison
        baseline_paths = set(baseline.files.keys())
        current_paths = set(current_files.keys())
        
        # Find new files
        for file_path in current_paths - baseline_paths:
            result = current_files[file_path]
            
            change = FileChange(
                file_path=file_path,
                change_type=ChangeType.NEW_FILE,
                current_hash=result.file_metadata.hash_sha256,
                current_modified=result.file_metadata.modification_time,
                new_matches=result.matches
            )
            
            diff_result.changes.append(change)
        
        # Find removed files
        for file_path in baseline_paths - current_paths:
            baseline_entry = baseline.files[file_path]
            
            change = FileChange(
                file_path=file_path,
                change_type=ChangeType.REMOVED_FILE,
                baseline_hash=baseline_entry.file_hash,
                baseline_modified=baseline_entry.last_modified,
                removed_matches=baseline_entry.matches
            )
            
            diff_result.changes.append(change)
        
        # Compare common files
        for file_path in baseline_paths & current_paths:
            baseline_entry = baseline.files[file_path]
            current_result = current_files[file_path]
            
            # Determine if the file content has changed
            if baseline_entry.file_hash != current_result.file_metadata.hash_sha256:
                change_type = ChangeType.MODIFIED_FILE
                
                # Compare matches to find new and removed
                baseline_matches = {
                    (m.pattern_name, m.matched_content): m 
                    for m in baseline_entry.matches
                }
                current_matches = {
                    (m.pattern_name, m.matched_content): m 
                    for m in current_result.matches
                }
                
                baseline_keys = set(baseline_matches.keys())
                current_keys = set(current_matches.keys())
                
                new_matches = [current_matches[k] for k in current_keys - baseline_keys]
                removed_matches = [baseline_matches[k] for k in baseline_keys - current_keys]
                
                change = FileChange(
                    file_path=file_path,
                    change_type=change_type,
                    baseline_hash=baseline_entry.file_hash,
                    current_hash=current_result.file_metadata.hash_sha256,
                    baseline_modified=baseline_entry.last_modified,
                    current_modified=current_result.file_metadata.modification_time,
                    new_matches=new_matches,
                    removed_matches=removed_matches
                )
                
                diff_result.changes.append(change)
            else:
                # File hasn't changed, but we still record it
                change = FileChange(
                    file_path=file_path,
                    change_type=ChangeType.FILE_UNCHANGED,
                    baseline_hash=baseline_entry.file_hash,
                    current_hash=current_result.file_metadata.hash_sha256,
                    baseline_modified=baseline_entry.last_modified,
                    current_modified=current_result.file_metadata.modification_time
                )
                
                diff_result.changes.append(change)
        
        return diff_result