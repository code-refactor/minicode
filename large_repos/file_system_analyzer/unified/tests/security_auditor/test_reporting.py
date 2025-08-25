"""
Tests for the Regulatory Compliance Reporting System.

This module contains tests for compliance framework definitions, report generation,
and report verification.
"""

import os
import json
import pytest
from datetime import datetime

from file_system_analyzer.reporting.frameworks import (
    ComplianceFramework,
    ComplianceRequirement,
    FrameworkRegistry,
    GDPRFramework,
    HIPAAFramework,
    PCIDSSFramework,
    SOXFramework,
    RiskLevel
)
from file_system_analyzer.reporting.reports import (
    ReportGenerator,
    ComplianceReport,
    ComplianceFinding,
    FindingStatus
)
from file_system_analyzer.detection.patterns import (
    ComplianceCategory,
    SensitivityLevel
)
from file_system_analyzer.detection.scanner import (
    ScanResult,
    ScanSummary,
    FileMetadata,
    SensitiveDataMatch
)
from file_system_analyzer.utils.crypto import CryptoProvider


class TestComplianceFrameworks:
    """Tests for compliance framework definitions."""
    
    def test_framework_registry(self):
        """Test the framework registry."""
        # Get all frameworks
        frameworks = FrameworkRegistry.get_all_frameworks()
        assert len(frameworks) >= 4  # GDPR, HIPAA, PCI-DSS, SOX
        
        # Check individual frameworks
        gdpr = FrameworkRegistry.get_framework("gdpr")
        assert gdpr.id == "gdpr"
        assert gdpr.name == "General Data Protection Regulation"
        
        hipaa = FrameworkRegistry.get_framework("hipaa")
        assert hipaa.id == "hipaa"
        assert hipaa.name == "Health Insurance Portability and Accountability Act"
        
        pci = FrameworkRegistry.get_framework("pci-dss")
        assert pci.id == "pci-dss"
        assert pci.name == "Payment Card Industry Data Security Standard"
        
        sox = FrameworkRegistry.get_framework("sox")
        assert sox.id == "sox"
        assert sox.name == "Sarbanes-Oxley Act"
        
        # Test invalid framework ID
        with pytest.raises(ValueError):
            FrameworkRegistry.get_framework("invalid-framework")
    
    def test_gdpr_framework(self):
        """Test the GDPR framework."""
        gdpr = GDPRFramework()
        
        # Check requirements
        assert len(gdpr.requirements) > 0
        assert "art5" in gdpr.requirements
        assert "art32" in gdpr.requirements
        
        # Check categories
        pii_requirements = gdpr.get_requirements_for_category(ComplianceCategory.PII)
        assert len(pii_requirements) > 0
        assert all(ComplianceCategory.PII in req.related_categories for req in pii_requirements)
        
        # Check risk mapping
        art5 = gdpr.requirements["art5"]
        risk = art5.get_risk_level(ComplianceCategory.PII, SensitivityLevel.HIGH)
        assert risk == RiskLevel.HIGH
    
    def test_hipaa_framework(self):
        """Test the HIPAA framework."""
        hipaa = HIPAAFramework()
        
        # Check requirements
        assert len(hipaa.requirements) > 0
        assert "privacy-rule" in hipaa.requirements
        assert "security-rule" in hipaa.requirements
        
        # Check categories
        phi_requirements = hipaa.get_requirements_for_category(ComplianceCategory.PHI)
        assert len(phi_requirements) > 0
        assert all(ComplianceCategory.PHI in req.related_categories for req in phi_requirements)
    
    def test_pci_dss_framework(self):
        """Test the PCI DSS framework."""
        pci = PCIDSSFramework()
        
        # Check requirements
        assert len(pci.requirements) > 0
        assert "req3" in pci.requirements
        assert "req4" in pci.requirements
        
        # Check categories
        pci_requirements = pci.get_requirements_for_category(ComplianceCategory.PCI)
        assert len(pci_requirements) > 0
        assert all(ComplianceCategory.PCI in req.related_categories for req in pci_requirements)
    
    def test_sox_framework(self):
        """Test the SOX framework."""
        sox = SOXFramework()
        
        # Check requirements
        assert len(sox.requirements) > 0
        assert "sec302" in sox.requirements
        assert "sec404" in sox.requirements
        
        # Check categories
        financial_requirements = sox.get_requirements_for_category(ComplianceCategory.FINANCIAL)
        assert len(financial_requirements) > 0
        assert all(ComplianceCategory.FINANCIAL in req.related_categories for req in financial_requirements)
    
    def test_frameworks_for_category(self):
        """Test getting frameworks for a specific category."""
        # PII should be in multiple frameworks
        pii_frameworks = FrameworkRegistry.get_frameworks_for_category(ComplianceCategory.PII)
        assert len(pii_frameworks) >= 2
        
        # PHI should be in HIPAA
        phi_frameworks = FrameworkRegistry.get_frameworks_for_category(ComplianceCategory.PHI)
        assert len(phi_frameworks) >= 1
        assert any(f.id == "hipaa" for f in phi_frameworks)
        
        # PCI should be in PCI-DSS
        pci_frameworks = FrameworkRegistry.get_frameworks_for_category(ComplianceCategory.PCI)
        assert len(pci_frameworks) >= 1
        assert any(f.id == "pci-dss" for f in pci_frameworks)


class TestReportGeneration:
    """Tests for compliance report generation."""
    
    @pytest.fixture
    def sample_scan_results(self):
        """Create sample scan results for testing."""
        # Create file metadata
        metadata1 = FileMetadata(
            file_path="/test/path/file1.txt",
            file_size=1024,
            file_type="text/plain",
            mime_type="text/plain",
            modification_time=datetime.now(),
            hash_sha256="abc123"
        )
        
        metadata2 = FileMetadata(
            file_path="/test/path/file2.txt",
            file_size=2048,
            file_type="text/plain",
            mime_type="text/plain",
            modification_time=datetime.now(),
            hash_sha256="def456"
        )
        
        # Create sensitive data matches
        match1 = SensitiveDataMatch(
            pattern_name="Social Security Number",
            pattern_description="US Social Security Number",
            matched_content="123-45-6789",
            context="Context around the SSN",
            line_number=10,
            category=ComplianceCategory.PII,
            sensitivity=SensitivityLevel.HIGH
        )
        
        match2 = SensitiveDataMatch(
            pattern_name="Credit Card Number",
            pattern_description="Credit card number",
            matched_content="4111111111111111",
            context="Context around the credit card",
            line_number=20,
            category=ComplianceCategory.PCI,
            sensitivity=SensitivityLevel.HIGH
        )
        
        # Create scan results
        result1 = ScanResult(
            file_metadata=metadata1,
            matches=[match1],
            scan_time=datetime.now(),
            scan_duration=0.5
        )
        
        result2 = ScanResult(
            file_metadata=metadata2,
            matches=[match2],
            scan_time=datetime.now(),
            scan_duration=0.7
        )
        
        # Create scan summary
        summary = ScanSummary(
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.2,
            total_files=2,
            files_with_sensitive_data=2,
            total_matches=2,
            files_with_errors=0,
            categorized_matches={
                ComplianceCategory.PII: 1,
                ComplianceCategory.PCI: 1
            },
            sensitivity_breakdown={
                SensitivityLevel.HIGH: 2
            }
        )
        
        return [result1, result2], summary
    
    def test_report_generator_gdpr(self, sample_scan_results):
        """Test generating a GDPR compliance report."""
        results, summary = sample_scan_results
        
        # Create GDPR report generator
        generator = ReportGenerator("gdpr")
        
        # Generate report
        report = generator.generate_report(results, summary)
        
        # Check report fields
        assert report.framework_id == "gdpr"
        assert report.framework_name == "General Data Protection Regulation"
        assert report.scan_summary == summary
        assert len(report.findings) > 0
        
        # PII findings should be mapped to GDPR requirements
        has_pii_findings = False
        for req_id, findings in report.findings.items():
            for finding in findings:
                if finding.category == ComplianceCategory.PII:
                    has_pii_findings = True
                    break
            if has_pii_findings:
                break
        
        assert has_pii_findings, "No PII findings mapped to GDPR requirements"
    
    def test_report_generator_pci(self, sample_scan_results):
        """Test generating a PCI-DSS compliance report."""
        results, summary = sample_scan_results
        
        # Create PCI-DSS report generator
        generator = ReportGenerator("pci-dss")
        
        # Generate report
        report = generator.generate_report(results, summary)
        
        # Check report fields
        assert report.framework_id == "pci-dss"
        assert report.framework_name == "Payment Card Industry Data Security Standard"
        assert report.scan_summary == summary
        assert len(report.findings) > 0
        
        # PCI findings should be mapped to PCI-DSS requirements
        has_pci_findings = False
        for req_id, findings in report.findings.items():
            for finding in findings:
                if finding.category == ComplianceCategory.PCI:
                    has_pci_findings = True
                    break
            if has_pci_findings:
                break
        
        assert has_pci_findings, "No PCI findings mapped to PCI-DSS requirements"
    
    def test_report_metrics(self, sample_scan_results):
        """Test report metrics calculations."""
        results, summary = sample_scan_results
        
        # Create report generator
        generator = ReportGenerator("gdpr")
        
        # Generate report
        report = generator.generate_report(results, summary)
        
        # Test metrics
        assert report.total_findings > 0
        assert len(report.findings_by_risk) > 0
        assert len(report.findings_by_status) > 0
        assert FindingStatus.NEW in report.findings_by_status
    
    def test_report_serialization(self, sample_scan_results):
        """Test report serialization and deserialization."""
        results, summary = sample_scan_results
        
        # Create report generator
        generator = ReportGenerator("gdpr")
        
        # Generate report
        report = generator.generate_report(results, summary)
        
        # Serialize to JSON
        report_json = report.to_json()
        
        # Deserialize from JSON
        report_dict = json.loads(report_json)
        
        # Check fields
        assert report_dict["framework_id"] == report.framework_id
        assert report_dict["framework_name"] == report.framework_name
        assert isinstance(report_dict["generation_time"], str)
    
    def test_report_signing_and_verification(self, sample_scan_results):
        """Test report signing and verification."""
        results, summary = sample_scan_results
        
        # Create crypto provider
        crypto_provider = CryptoProvider.generate()
        
        # Create report generator
        generator = ReportGenerator("gdpr")
        
        # Generate report
        report = generator.generate_report(results, summary)
        
        # Sign the report
        report.sign(crypto_provider)
        
        # Verify the report
        assert report.verification_info is not None
        assert "report_hash" in report.verification_info
        assert "signature" in report.verification_info
        
        # Verify signature
        assert report.verify(crypto_provider) is True
        
        # Tamper with the report
        original_framework_name = report.framework_name
        report.framework_name = "Tampered Framework"
        
        # Verification should fail
        assert report.verify(crypto_provider) is False
        
        # Restore original value
        report.framework_name = original_framework_name
        
        # Verification should succeed again
        assert report.verify(crypto_provider) is True
    
    def test_report_saving(self, sample_scan_results, tmp_path):
        """Test report saving."""
        results, summary = sample_scan_results
        
        # Create crypto provider
        crypto_provider = CryptoProvider.generate()
        
        # Create report generator
        generator = ReportGenerator("gdpr")
        
        # Generate report
        report = generator.generate_report(results, summary)
        
        # Save the report
        report_path = tmp_path / "test_report.json"
        report.save(str(report_path), verify=True, crypto_provider=crypto_provider)
        
        # Check file exists
        assert os.path.exists(report_path)
        
        # Check content
        with open(report_path, 'r') as f:
            report_data = json.load(f)
            
        assert report_data["framework_id"] == "gdpr"
        assert "verification_info" in report_data