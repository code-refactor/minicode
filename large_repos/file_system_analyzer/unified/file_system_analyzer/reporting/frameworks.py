"""
Regulatory compliance framework definitions.

This module contains the definitions of various regulatory frameworks
such as GDPR, HIPAA, and SOX, with mapping between sensitive data types
and specific compliance requirements.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Set, Type
from pydantic import BaseModel, Field

from file_system_analyzer.detection.patterns import ComplianceCategory, SensitivityLevel


class RiskLevel(str, Enum):
    """Risk levels for compliance findings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceRequirement(BaseModel):
    """A specific requirement in a regulatory framework."""
    id: str
    description: str
    related_categories: List[ComplianceCategory]
    sensitivity_mapping: Dict[ComplianceCategory, SensitivityLevel] = Field(default_factory=dict)
    risk_mapping: Dict[SensitivityLevel, RiskLevel] = Field(default_factory=dict)
    remediation_guidance: str
    
    def get_risk_level(self, category: ComplianceCategory, sensitivity: SensitivityLevel) -> RiskLevel:
        """Map a sensitivity level to a risk level for this requirement."""
        # First check if there's a specific mapping for this category
        if category in self.sensitivity_mapping:
            # If the actual sensitivity is higher than the mapped minimum, use the actual
            mapped_min = self.sensitivity_mapping[category]
            sensitivity_value = {
                SensitivityLevel.LOW: 1,
                SensitivityLevel.MEDIUM: 2,
                SensitivityLevel.HIGH: 3,
                SensitivityLevel.CRITICAL: 4
            }
            effective_sensitivity = sensitivity if sensitivity_value[sensitivity] >= sensitivity_value[mapped_min] else mapped_min
        else:
            effective_sensitivity = sensitivity
            
        # Then check the risk mapping for this sensitivity
        if effective_sensitivity in self.risk_mapping:
            return self.risk_mapping[effective_sensitivity]
            
        # Default mapping if not specified
        default_mapping = {
            SensitivityLevel.LOW: RiskLevel.LOW,
            SensitivityLevel.MEDIUM: RiskLevel.MEDIUM,
            SensitivityLevel.HIGH: RiskLevel.HIGH,
            SensitivityLevel.CRITICAL: RiskLevel.CRITICAL
        }
        return default_mapping[effective_sensitivity]


class ComplianceFramework(BaseModel):
    """A regulatory compliance framework with requirements."""
    id: str
    name: str
    description: str
    version: str
    requirements: Dict[str, ComplianceRequirement] = Field(default_factory=dict)
    
    def get_requirements_for_category(self, category: ComplianceCategory) -> List[ComplianceRequirement]:
        """Get all requirements related to a specific compliance category."""
        return [req for req in self.requirements.values() if category in req.related_categories]


class GDPRFramework(ComplianceFramework):
    """General Data Protection Regulation (GDPR) framework."""
    
    def __init__(self):
        """Initialize the GDPR framework."""
        super().__init__(
            id="gdpr",
            name="General Data Protection Regulation",
            description="European Union regulation on data protection and privacy",
            version="2016/679",
            requirements={
                "art5": ComplianceRequirement(
                    id="art5",
                    description="Principles relating to processing of personal data",
                    related_categories=[
                        ComplianceCategory.PII, 
                        ComplianceCategory.FINANCIAL,
                        ComplianceCategory.PHI
                    ],
                    sensitivity_mapping={
                        ComplianceCategory.PII: SensitivityLevel.MEDIUM,
                        ComplianceCategory.PHI: SensitivityLevel.HIGH
                    },
                    risk_mapping={
                        SensitivityLevel.LOW: RiskLevel.LOW,
                        SensitivityLevel.MEDIUM: RiskLevel.MEDIUM,
                        SensitivityLevel.HIGH: RiskLevel.HIGH,
                        SensitivityLevel.CRITICAL: RiskLevel.CRITICAL
                    },
                    remediation_guidance="Ensure personal data is processed lawfully, fairly, and transparently. Implement data minimization practices."
                ),
                "art13": ComplianceRequirement(
                    id="art13",
                    description="Information to be provided where personal data are collected",
                    related_categories=[ComplianceCategory.PII],
                    remediation_guidance="Ensure privacy notices are provided when collecting personal data."
                ),
                "art17": ComplianceRequirement(
                    id="art17",
                    description="Right to erasure ('right to be forgotten')",
                    related_categories=[
                        ComplianceCategory.PII, 
                        ComplianceCategory.FINANCIAL,
                        ComplianceCategory.PHI
                    ],
                    risk_mapping={
                        SensitivityLevel.LOW: RiskLevel.MEDIUM,
                        SensitivityLevel.MEDIUM: RiskLevel.HIGH,
                        SensitivityLevel.HIGH: RiskLevel.HIGH,
                        SensitivityLevel.CRITICAL: RiskLevel.CRITICAL
                    },
                    remediation_guidance="Implement mechanisms to erase personal data upon request when there is no legitimate reason to retain it."
                ),
                "art25": ComplianceRequirement(
                    id="art25",
                    description="Data protection by design and by default",
                    related_categories=[
                        ComplianceCategory.PII, 
                        ComplianceCategory.FINANCIAL,
                        ComplianceCategory.PHI
                    ],
                    remediation_guidance="Implement appropriate technical and organizational measures to protect personal data."
                ),
                "art32": ComplianceRequirement(
                    id="art32",
                    description="Security of processing",
                    related_categories=[
                        ComplianceCategory.PII, 
                        ComplianceCategory.FINANCIAL,
                        ComplianceCategory.PHI,
                        ComplianceCategory.CREDENTIALS
                    ],
                    sensitivity_mapping={
                        ComplianceCategory.CREDENTIALS: SensitivityLevel.HIGH
                    },
                    remediation_guidance="Implement appropriate security measures including encryption and access controls."
                )
            }
        )


class HIPAAFramework(ComplianceFramework):
    """Health Insurance Portability and Accountability Act (HIPAA) framework."""
    
    def __init__(self):
        """Initialize the HIPAA framework."""
        super().__init__(
            id="hipaa",
            name="Health Insurance Portability and Accountability Act",
            description="US regulation for medical information privacy and security",
            version="1996 with updates",
            requirements={
                "privacy-rule": ComplianceRequirement(
                    id="privacy-rule",
                    description="Standards for Privacy of Individually Identifiable Health Information",
                    related_categories=[
                        ComplianceCategory.PHI, 
                        ComplianceCategory.PII
                    ],
                    sensitivity_mapping={
                        ComplianceCategory.PHI: SensitivityLevel.HIGH,
                        ComplianceCategory.PII: SensitivityLevel.MEDIUM
                    },
                    remediation_guidance="Implement controls to protect PHI. Limit uses and disclosures to the minimum necessary."
                ),
                "security-rule": ComplianceRequirement(
                    id="security-rule",
                    description="Security Standards for the Protection of Electronic PHI",
                    related_categories=[
                        ComplianceCategory.PHI, 
                        ComplianceCategory.CREDENTIALS
                    ],
                    sensitivity_mapping={
                        ComplianceCategory.PHI: SensitivityLevel.HIGH,
                        ComplianceCategory.CREDENTIALS: SensitivityLevel.HIGH
                    },
                    risk_mapping={
                        SensitivityLevel.MEDIUM: RiskLevel.HIGH,
                        SensitivityLevel.HIGH: RiskLevel.HIGH,
                        SensitivityLevel.CRITICAL: RiskLevel.CRITICAL
                    },
                    remediation_guidance="Implement administrative, physical, and technical safeguards to ensure the confidentiality, integrity, and security of electronic PHI."
                ),
                "breach-notification": ComplianceRequirement(
                    id="breach-notification",
                    description="Breach Notification Rule",
                    related_categories=[
                        ComplianceCategory.PHI, 
                        ComplianceCategory.PII
                    ],
                    remediation_guidance="Implement procedures to detect and report breaches of unsecured PHI."
                )
            }
        )


class PCIDSSFramework(ComplianceFramework):
    """Payment Card Industry Data Security Standard (PCI DSS) framework."""
    
    def __init__(self):
        """Initialize the PCI DSS framework."""
        super().__init__(
            id="pci-dss",
            name="Payment Card Industry Data Security Standard",
            description="Information security standard for organizations handling payment card data",
            version="4.0",
            requirements={
                "req3": ComplianceRequirement(
                    id="req3",
                    description="Protect stored account data",
                    related_categories=[
                        ComplianceCategory.PCI, 
                        ComplianceCategory.FINANCIAL
                    ],
                    sensitivity_mapping={
                        ComplianceCategory.PCI: SensitivityLevel.HIGH,
                        ComplianceCategory.FINANCIAL: SensitivityLevel.HIGH
                    },
                    risk_mapping={
                        SensitivityLevel.MEDIUM: RiskLevel.HIGH,
                        SensitivityLevel.HIGH: RiskLevel.CRITICAL,
                        SensitivityLevel.CRITICAL: RiskLevel.CRITICAL
                    },
                    remediation_guidance="Use strong encryption for stored cardholder data. Implement data retention policies."
                ),
                "req4": ComplianceRequirement(
                    id="req4",
                    description="Encrypt transmission of cardholder data",
                    related_categories=[ComplianceCategory.PCI],
                    sensitivity_mapping={
                        ComplianceCategory.PCI: SensitivityLevel.HIGH
                    },
                    risk_mapping={
                        SensitivityLevel.MEDIUM: RiskLevel.HIGH,
                        SensitivityLevel.HIGH: RiskLevel.CRITICAL,
                        SensitivityLevel.CRITICAL: RiskLevel.CRITICAL
                    },
                    remediation_guidance="Use strong cryptography and security protocols to safeguard sensitive data during transmission."
                ),
                "req7": ComplianceRequirement(
                    id="req7",
                    description="Restrict access to system components",
                    related_categories=[
                        ComplianceCategory.PCI, 
                        ComplianceCategory.CREDENTIALS
                    ],
                    remediation_guidance="Implement least-privilege access control systems. Restrict access based on job requirements."
                ),
                "req9": ComplianceRequirement(
                    id="req9",
                    description="Restrict physical access to cardholder data",
                    related_categories=[ComplianceCategory.PCI],
                    remediation_guidance="Implement physical access controls to prevent unauthorized access to cardholder data."
                )
            }
        )


class SOXFramework(ComplianceFramework):
    """Sarbanes-Oxley Act (SOX) framework."""
    
    def __init__(self):
        """Initialize the SOX framework."""
        super().__init__(
            id="sox",
            name="Sarbanes-Oxley Act",
            description="US federal law establishing requirements for financial record-keeping and reporting",
            version="2002",
            requirements={
                "sec302": ComplianceRequirement(
                    id="sec302",
                    description="Corporate responsibility for financial reports",
                    related_categories=[
                        ComplianceCategory.FINANCIAL, 
                        ComplianceCategory.PROPRIETARY
                    ],
                    remediation_guidance="Maintain accurate financial records and implement effective internal controls."
                ),
                "sec404": ComplianceRequirement(
                    id="sec404",
                    description="Management assessment of internal controls",
                    related_categories=[
                        ComplianceCategory.FINANCIAL, 
                        ComplianceCategory.CREDENTIALS,
                        ComplianceCategory.PROPRIETARY
                    ],
                    sensitivity_mapping={
                        ComplianceCategory.CREDENTIALS: SensitivityLevel.HIGH
                    },
                    remediation_guidance="Document and test internal controls over financial reporting."
                )
            }
        )


class FrameworkRegistry:
    """Registry of available compliance frameworks."""
    
    _frameworks: Dict[str, ComplianceFramework] = {
        "gdpr": GDPRFramework(),
        "hipaa": HIPAAFramework(),
        "pci-dss": PCIDSSFramework(),
        "sox": SOXFramework()
    }
    
    @classmethod
    def get_framework(cls, framework_id: str) -> ComplianceFramework:
        """Get a compliance framework by ID."""
        if framework_id not in cls._frameworks:
            raise ValueError(f"Unknown compliance framework: {framework_id}")
        return cls._frameworks[framework_id]
    
    @classmethod
    def get_all_frameworks(cls) -> Dict[str, ComplianceFramework]:
        """Get all available compliance frameworks."""
        return cls._frameworks
    
    @classmethod
    def get_frameworks_for_category(cls, category: ComplianceCategory) -> List[ComplianceFramework]:
        """Get all frameworks that include requirements for a specific category."""
        return [
            framework for framework in cls._frameworks.values()
            if any(category in req.related_categories for req in framework.requirements.values())
        ]