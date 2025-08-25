"""
Result classes for the File System Analyzer unified library.

This module provides concrete result classes that extend the base result classes
with specific functionality for different types of analysis.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set
from dataclasses import dataclass, field, asdict

from .types import (
    ScanStatus, Priority, SensitivityLevel, FileCategory, DatabaseEngine, 
    ComplianceCategory, AnalysisType, FileInfo, Match, Recommendation, FilePath
)
from .base import BaseResult, BaseScanResult, BaseAnalysisResult, BaseFileInfo


@dataclass
class DatabaseFileInfo(BaseFileInfo):
    """File information specific to database files."""
    engine: DatabaseEngine = DatabaseEngine.UNKNOWN
    category: FileCategory = FileCategory.UNKNOWN
    growth_rate_bytes_per_day: Optional[float] = None
    access_frequency: Optional[float] = None
    is_compressed: bool = False
    tablespace_name: Optional[str] = None
    table_name: Optional[str] = None
    index_name: Optional[str] = None
    estimated_rows: Optional[int] = None
    
    def get_database_metadata(self) -> Dict[str, Any]:
        """Get database-specific metadata."""
        return {
            "engine": self.engine.value,
            "category": self.category.value,
            "growth_rate_bytes_per_day": self.growth_rate_bytes_per_day,
            "access_frequency": self.access_frequency,
            "is_compressed": self.is_compressed,
            "tablespace_name": self.tablespace_name,
            "table_name": self.table_name,
            "index_name": self.index_name,
            "estimated_rows": self.estimated_rows,
        }


@dataclass
class SecurityFileInfo(BaseFileInfo):
    """File information specific to security analysis."""
    hash_sha256: Optional[str] = None
    hash_md5: Optional[str] = None
    digital_signature: Optional[str] = None
    certificate_info: Optional[Dict[str, Any]] = None
    encryption_status: Optional[str] = None
    access_permissions: Optional[str] = None
    acl_entries: List[str] = field(default_factory=list)
    
    def get_security_metadata(self) -> Dict[str, Any]:
        """Get security-specific metadata."""
        return {
            "hash_sha256": self.hash_sha256,
            "hash_md5": self.hash_md5,
            "digital_signature": self.digital_signature,
            "certificate_info": self.certificate_info,
            "encryption_status": self.encryption_status,
            "access_permissions": self.access_permissions,
            "acl_entries": self.acl_entries,
        }


@dataclass
class SensitiveDataMatch(Match):
    """A match for sensitive data with additional validation information."""
    pattern_description: str = ""
    context_before: str = ""
    context_after: str = ""
    validation_errors: List[str] = field(default_factory=list)
    risk_level: Priority = Priority.MEDIUM
    compliance_categories: List[ComplianceCategory] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if the match passed validation."""
        return self.validation_status and len(self.validation_errors) == 0
    
    def get_full_context(self) -> str:
        """Get the full context around the match."""
        return f"{self.context_before}{self.matched_content}{self.context_after}"


@dataclass  
class DatabaseMatch(Match):
    """A match for database-related patterns."""
    engine: DatabaseEngine = DatabaseEngine.UNKNOWN
    file_category: FileCategory = FileCategory.UNKNOWN
    table_references: List[str] = field(default_factory=list)
    schema_references: List[str] = field(default_factory=list)
    estimated_impact_bytes: Optional[int] = None


class SensitiveDataScanResult(BaseScanResult):
    """Result of a sensitive data scan."""
    
    def __init__(
        self,
        file_info: Union[SecurityFileInfo, BaseFileInfo],
        sensitive_matches: Optional[List[SensitiveDataMatch]] = None,
        **kwargs
    ):
        """Initialize the sensitive data scan result."""
        matches = sensitive_matches or []
        super().__init__(file_info=file_info, matches=matches, **kwargs)
        self.sensitive_matches = sensitive_matches or []
        
    @property
    def highest_sensitivity(self) -> Optional[SensitivityLevel]:
        """Get the highest sensitivity level found."""
        if not self.sensitive_matches:
            return None
            
        sensitivity_values = {
            SensitivityLevel.LOW: 1,
            SensitivityLevel.MEDIUM: 2,
            SensitivityLevel.HIGH: 3,
            SensitivityLevel.CRITICAL: 4
        }
        
        max_match = max(
            self.sensitive_matches, 
            key=lambda m: sensitivity_values.get(m.sensitivity, 0)
        )
        return max_match.sensitivity
        
    def get_matches_by_category(self) -> Dict[ComplianceCategory, List[SensitiveDataMatch]]:
        """Group matches by compliance category."""
        categorized = {}
        for match in self.sensitive_matches:
            for category in match.compliance_categories:
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(match)
        return categorized
        
    def get_matches_by_sensitivity(self) -> Dict[SensitivityLevel, List[SensitiveDataMatch]]:
        """Group matches by sensitivity level."""
        grouped = {}
        for match in self.sensitive_matches:
            if match.sensitivity not in grouped:
                grouped[match.sensitivity] = []
            grouped[match.sensitivity].append(match)
        return grouped


class DatabaseFileScanResult(BaseScanResult):
    """Result of a database file scan."""
    
    def __init__(
        self,
        file_info: Union[DatabaseFileInfo, BaseFileInfo],
        database_matches: Optional[List[DatabaseMatch]] = None,
        **kwargs
    ):
        """Initialize the database file scan result."""
        matches = database_matches or []
        super().__init__(file_info=file_info, matches=matches, **kwargs)
        self.database_matches = database_matches or []
        
    def get_matches_by_engine(self) -> Dict[DatabaseEngine, List[DatabaseMatch]]:
        """Group matches by database engine."""
        grouped = {}
        for match in self.database_matches:
            if match.engine not in grouped:
                grouped[match.engine] = []
            grouped[match.engine].append(match)
        return grouped
        
    def get_matches_by_category(self) -> Dict[FileCategory, List[DatabaseMatch]]:
        """Group matches by file category."""
        grouped = {}
        for match in self.database_matches:
            if match.file_category not in grouped:
                grouped[match.file_category] = []
            grouped[match.file_category].append(match)
        return grouped


class SensitiveDataAnalysisResult(BaseAnalysisResult):
    """Result of sensitive data analysis."""
    
    def __init__(
        self,
        scan_results: Optional[List[SensitiveDataScanResult]] = None,
        **kwargs
    ):
        """Initialize the sensitive data analysis result."""
        super().__init__(analysis_type=AnalysisType.SENSITIVE_DATA_DETECTION, **kwargs)
        self.scan_results = scan_results or []
        
    def get_compliance_summary(self) -> Dict[ComplianceCategory, Dict[str, int]]:
        """Get summary of compliance violations by category."""
        summary = {}
        
        for result in self.scan_results:
            if not result.has_findings:
                continue
                
            categories = result.get_matches_by_category()
            for category, matches in categories.items():
                if category not in summary:
                    summary[category] = {"files": 0, "violations": 0}
                    
                summary[category]["files"] += 1
                summary[category]["violations"] += len(matches)
                
        return summary
        
    def get_risk_summary(self) -> Dict[Priority, Dict[str, int]]:
        """Get summary of risks by priority level."""
        summary = {}
        
        for result in self.scan_results:
            for match in result.sensitive_matches:
                risk = match.risk_level
                if risk not in summary:
                    summary[risk] = {"files": set(), "violations": 0}
                    
                summary[risk]["files"].add(str(result.file_info.path))
                summary[risk]["violations"] += 1
                
        # Convert sets to counts
        for risk in summary:
            summary[risk]["files"] = len(summary[risk]["files"])
            
        return summary


class DatabaseAnalysisResult(BaseAnalysisResult):
    """Result of database file analysis."""
    
    def __init__(
        self,
        detected_files: Optional[List[DatabaseFileInfo]] = None,
        scan_results: Optional[List[DatabaseFileScanResult]] = None,
        **kwargs
    ):
        """Initialize the database analysis result."""
        super().__init__(analysis_type=AnalysisType.DATABASE_FILE_RECOGNITION, **kwargs)
        self.detected_files = detected_files or []
        self.scan_results = scan_results or []
        
    def get_engine_summary(self) -> Dict[DatabaseEngine, Dict[str, Any]]:
        """Get summary of detected files by database engine."""
        summary = {}
        
        for file_info in self.detected_files:
            engine = file_info.engine
            if engine not in summary:
                summary[engine] = {
                    "file_count": 0,
                    "total_size_bytes": 0,
                    "categories": {},
                    "growth_rate_bytes_per_day": 0,
                }
                
            summary[engine]["file_count"] += 1
            summary[engine]["total_size_bytes"] += file_info.size_bytes
            
            if file_info.growth_rate_bytes_per_day:
                summary[engine]["growth_rate_bytes_per_day"] += file_info.growth_rate_bytes_per_day
                
            # Track categories
            category = file_info.category
            if category not in summary[engine]["categories"]:
                summary[engine]["categories"][category] = 0
            summary[engine]["categories"][category] += 1
            
        return summary
        
    def get_category_summary(self) -> Dict[FileCategory, Dict[str, Any]]:
        """Get summary of detected files by category."""
        summary = {}
        
        for file_info in self.detected_files:
            category = file_info.category
            if category not in summary:
                summary[category] = {
                    "file_count": 0,
                    "total_size_bytes": 0,
                    "engines": set(),
                }
                
            summary[category]["file_count"] += 1
            summary[category]["total_size_bytes"] += file_info.size_bytes
            summary[category]["engines"].add(file_info.engine)
            
        # Convert engine sets to lists for JSON serialization
        for category in summary:
            summary[category]["engines"] = list(summary[category]["engines"])
            
        return summary


class OptimizationRecommendation(Recommendation):
    """Extended recommendation for database optimization."""
    
    def __init__(
        self,
        optimization_type: str,
        potential_savings_bytes: Optional[int] = None,
        performance_impact_percent: Optional[float] = None,
        implementation_effort: Optional[str] = None,
        **kwargs
    ):
        """Initialize the optimization recommendation."""
        super().__init__(**kwargs)
        self.optimization_type = optimization_type
        self.potential_savings_bytes = potential_savings_bytes
        self.performance_impact_percent = performance_impact_percent
        self.implementation_effort = implementation_effort


class ComplianceRecommendation(Recommendation):
    """Extended recommendation for compliance issues."""
    
    def __init__(
        self,
        compliance_framework: ComplianceCategory,
        violation_type: str,
        remediation_urgency: Priority = Priority.MEDIUM,
        **kwargs
    ):
        """Initialize the compliance recommendation."""
        super().__init__(**kwargs)
        self.compliance_framework = compliance_framework
        self.violation_type = violation_type
        self.remediation_urgency = remediation_urgency


class AnalysisSummary:
    """Summary of multiple analysis results."""
    
    def __init__(self, results: List[BaseAnalysisResult]):
        """Initialize the analysis summary."""
        self.results = results
        self.timestamp = datetime.now()
        
    def get_overall_summary(self) -> Dict[str, Any]:
        """Get an overall summary of all analyses."""
        total_files = sum(r.total_files_processed for r in self.results)
        total_findings = sum(r.total_findings for r in self.results)
        files_with_findings = sum(r.files_with_findings for r in self.results)
        
        analysis_types = [r.analysis_type.value for r in self.results]
        
        all_recommendations = []
        for result in self.results:
            all_recommendations.extend(result.recommendations)
            
        critical_recommendations = [
            r for r in all_recommendations if r.priority == Priority.CRITICAL
        ]
        
        return {
            "timestamp": self.timestamp.isoformat(),
            "analysis_types": analysis_types,
            "total_files_processed": total_files,
            "files_with_findings": files_with_findings,
            "total_findings": total_findings,
            "total_recommendations": len(all_recommendations),
            "critical_recommendations": len(critical_recommendations),
            "success_rate": len([r for r in self.results if r.is_successful()]) / len(self.results),
        }
        
    def get_recommendations_by_priority(self) -> Dict[Priority, List[Recommendation]]:
        """Group all recommendations by priority."""
        grouped = {}
        
        for result in self.results:
            for rec in result.recommendations:
                if rec.priority not in grouped:
                    grouped[rec.priority] = []
                grouped[rec.priority].append(rec)
                
        return grouped
        
    def export_summary(self, output_path: FilePath, format: str = "json") -> bool:
        """
        Export the analysis summary.
        
        Args:
            output_path: Path to export the summary to
            format: Export format (json, yaml, etc.)
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            summary_data = {
                "overall_summary": self.get_overall_summary(),
                "recommendations_by_priority": {
                    k.value: [asdict(r) for r in v] 
                    for k, v in self.get_recommendations_by_priority().items()
                },
                "detailed_results": [
                    {
                        "analysis_type": r.analysis_type.value,
                        "summary": r.get_summary(),
                    }
                    for r in self.results
                ]
            }
            
            output_path = Path(output_path)
            
            if format.lower() == "json":
                with open(output_path, 'w') as f:
                    json.dump(summary_data, f, indent=2, default=str)
                return True
                
            # Add other formats as needed
            return False
            
        except Exception:
            return False