"""
Compliance report generation.

This module provides tools for generating compliance reports mapped to 
specific regulatory frameworks.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union, Type

from pydantic import BaseModel, Field

# Import from common library
from common.export.base import BaseExporter
from common.export.multi_format import MultiFormatExporter
from common.core.types import ExportFormat
from common.core.results import BaseResult

from file_system_analyzer.detection.scanner import ScanResult, ScanSummary, SensitiveDataMatch
from file_system_analyzer.detection.patterns import ComplianceCategory, SensitivityLevel
from file_system_analyzer.reporting.frameworks import (
    ComplianceFramework, 
    ComplianceRequirement,
    RiskLevel,
    FrameworkRegistry
)
from file_system_analyzer.utils.crypto import CryptoProvider


class FindingStatus(str, Enum):
    """Status of a compliance finding."""
    NEW = "new"
    KNOWN = "known"
    REMEDIATED = "remediated"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"


class ComplianceFinding(BaseModel):
    """A compliance finding related to a specific regulatory requirement."""
    finding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requirement_id: str
    file_path: str
    matched_content: str
    context: str
    risk_level: RiskLevel
    sensitivity: SensitivityLevel
    category: ComplianceCategory
    status: FindingStatus = FindingStatus.NEW
    remediation_guidance: str
    related_matches: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ComplianceReport(BaseModel):
    """A report of compliance findings for a specific regulatory framework."""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    framework_id: str
    framework_name: str
    generation_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scan_summary: ScanSummary
    findings: Dict[str, List[ComplianceFinding]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    verification_info: Optional[Dict[str, Any]] = None
    
    @property
    def total_findings(self) -> int:
        """Get the total number of findings in the report."""
        return sum(len(findings) for findings in self.findings.values())
    
    @property
    def findings_by_risk(self) -> Dict[RiskLevel, int]:
        """Get a count of findings by risk level."""
        result = {level: 0 for level in RiskLevel}
        for req_findings in self.findings.values():
            for finding in req_findings:
                result[finding.risk_level] += 1
        return result
    
    @property
    def findings_by_status(self) -> Dict[FindingStatus, int]:
        """Get a count of findings by status."""
        result = {status: 0 for status in FindingStatus}
        for req_findings in self.findings.values():
            for finding in req_findings:
                result[finding.status] += 1
        return result
    
    def sign(self, crypto_provider: CryptoProvider) -> None:
        """Sign the report with cryptographic verification."""
        # Create a canonical representation of the report
        report_data = self.model_dump(exclude={"verification_info"})
        report_json = json.dumps(report_data, sort_keys=True, default=str).encode()
        
        # Create a hash of the report
        report_hash = crypto_provider.secure_hash(report_json)
        
        # Create a timestamped signature
        signature = crypto_provider.timestamp_signature(report_json)
        
        self.verification_info = {
            "report_hash": report_hash,
            "signature": signature,
            "verification_method": "crypto_provider",
            "key_id": crypto_provider.key_id
        }
    
    def verify(self, crypto_provider: CryptoProvider) -> bool:
        """Verify the cryptographic signature of the report."""
        if not self.verification_info:
            return False
            
        # Recreate the report data without verification_info
        report_data = self.model_dump(exclude={"verification_info"})
        report_json = json.dumps(report_data, sort_keys=True, default=str).encode()
        
        # Verify the hash
        calculated_hash = crypto_provider.secure_hash(report_json)
        stored_hash = self.verification_info.get("report_hash")
        if calculated_hash != stored_hash:
            return False
            
        # Verify the signature
        signature = self.verification_info.get("signature", {})
        return crypto_provider.verify_timestamped_signature(report_json, signature)
    
    def to_json(self) -> str:
        """Convert the report to a JSON string."""
        return json.dumps(self.model_dump(), default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o))
    
    def save(self, file_path: str, verify: bool = False, crypto_provider: Optional[CryptoProvider] = None) -> None:
        """Save the report to a file, optionally with verification."""
        if verify and crypto_provider and not self.verification_info:
            self.sign(crypto_provider)
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(self.to_json())


class ReportGenerator:
    """Generator for compliance reports from scan results."""
    
    def __init__(self, framework_id: str):
        """Initialize with a specific compliance framework."""
        self.framework = FrameworkRegistry.get_framework(framework_id)
    
    def _match_to_findings(
        self, 
        match: SensitiveDataMatch, 
        file_path: str
    ) -> List[ComplianceFinding]:
        """Convert a sensitive data match to compliance findings."""
        findings = []
        
        # Find all requirements that relate to this match's category
        requirements = self.framework.get_requirements_for_category(match.category)
        
        for req in requirements:
            # Determine risk level for this requirement
            risk_level = req.get_risk_level(match.category, match.sensitivity)
            
            finding = ComplianceFinding(
                requirement_id=req.id,
                file_path=file_path,
                matched_content=match.matched_content,
                context=match.context,
                risk_level=risk_level,
                sensitivity=match.sensitivity,
                category=match.category,
                remediation_guidance=req.remediation_guidance,
                related_matches=[match.matched_content]
            )
            
            findings.append(finding)
            
        return findings
    
    def generate_report(self, scan_results: List[ScanResult], scan_summary: ScanSummary) -> ComplianceReport:
        """Generate a compliance report from scan results."""
        # Initialize the report
        report = ComplianceReport(
            framework_id=self.framework.id,
            framework_name=self.framework.name,
            scan_summary=scan_summary,
            metadata={
                "framework_version": self.framework.version,
                "framework_description": self.framework.description
            }
        )
        
        # Initialize findings dictionary with empty lists for each requirement
        report.findings = {req_id: [] for req_id in self.framework.requirements}
        
        # Process each scan result
        for result in scan_results:
            if result.has_sensitive_data:
                for match in result.matches:
                    # Convert match to findings
                    findings = self._match_to_findings(match, result.file_metadata.file_path)
                    
                    # Add findings to the report
                    for finding in findings:
                        if finding.requirement_id in report.findings:
                            report.findings[finding.requirement_id].append(finding)
        
        return report