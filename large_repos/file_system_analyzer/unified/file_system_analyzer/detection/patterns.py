"""
Predefined patterns for sensitive data detection.

This module contains regular expressions and other patterns for detecting
various types of sensitive data, including PII, financial information,
health records, and proprietary business data.
"""

import re
from enum import Enum
from typing import Dict, List, Pattern, Union, Optional
from pydantic import BaseModel, Field

# Import common types
from common.core.types import PatternDefinition, MatchType, ComplianceCategory, SensitivityLevel
from common.patterns.matchers import RegexMatcher

# Legacy types for backward compatibility
class SensitivityLevel(str, Enum):
    """Sensitivity level of detected data."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceCategory(str, Enum):
    """Regulatory compliance categories for detected data."""
    PII = "pii"  # Personally Identifiable Information
    PHI = "phi"  # Protected Health Information
    PCI = "pci"  # Payment Card Industry Data
    FINANCIAL = "financial"
    PROPRIETARY = "proprietary"
    CREDENTIALS = "credentials"
    OTHER = "other"


class SensitiveDataPattern(BaseModel):
    """Definition of a sensitive data pattern."""
    name: str
    description: str
    pattern: str
    regex: Optional[Pattern] = Field(None, exclude=True)
    sensitivity: SensitivityLevel
    category: ComplianceCategory
    context_rules: List[str] = Field(default_factory=list)
    false_positive_examples: List[str] = Field(default_factory=list)
    validation_func: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self.regex = re.compile(self.pattern, re.IGNORECASE)

    def match(self, content: str) -> List[str]:
        """Find all matches of this pattern in the given content."""
        return self.regex.findall(content)


class PatternDefinitions:
    """Predefined patterns for sensitive data detection."""

    # Common PatternDefinition objects for new API
    @classmethod
    def get_common_patterns(cls) -> List[PatternDefinition]:
        """Get patterns in common PatternDefinition format."""
        from common.core.types import ComplianceCategory as CC, SensitivityLevel as SL, Priority
        
        return [
            # Social Security Numbers
            PatternDefinition(
                name="Social Security Number",
                description="US Social Security Number",
                pattern=r"\b(?!000|666|9\d{2})([0-8]\d{2}|7([0-6]\d))-(?!00)(\d{2})-(?!0000)(\d{4})\b",
                match_type=MatchType.REGEX,
                category=CC.PII,
                sensitivity=SL.HIGH,
                priority=Priority.HIGH,
                validation_func="validate_ssn"
            ),
            # Credit Card Numbers
            PatternDefinition(
                name="Credit Card Number",
                description="Credit card number (major brands)",
                pattern=r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",
                match_type=MatchType.REGEX,
                category=CC.PCI,
                sensitivity=SL.HIGH,
                priority=Priority.HIGH,
                validation_func="validate_credit_card"
            ),
            # Email Addresses
            PatternDefinition(
                name="Email Address",
                description="Email address",
                pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                match_type=MatchType.REGEX,
                category=CC.PII,
                sensitivity=SL.MEDIUM,
                priority=Priority.MEDIUM
            ),
            # Phone Numbers
            PatternDefinition(
                name="US Phone Number",
                description="US phone number (various formats)",
                pattern=r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
                match_type=MatchType.REGEX,
                category=CC.PII,
                sensitivity=SL.MEDIUM,
                priority=Priority.MEDIUM
            ),
            # API Keys
            PatternDefinition(
                name="API Key",
                description="Common API key formats",
                pattern=r"\b[A-Za-z0-9_\-]{32,45}\b",
                match_type=MatchType.REGEX,
                category=CC.CREDENTIALS,
                sensitivity=SL.HIGH,
                priority=Priority.HIGH,
                context_rules=["must be near words like key, api, token, secret"]
            ),
            # Password patterns
            PatternDefinition(
                name="Password",
                description="Password in configuration or code",
                pattern=r"(?:password|passwd|pwd)[\s:=]+['\"](.*?)['\"]",
                match_type=MatchType.REGEX,
                category=CC.CREDENTIALS,
                sensitivity=SL.CRITICAL,
                priority=Priority.CRITICAL
            )
        ]

    # Legacy patterns for backward compatibility
    # Social Security Numbers
    SSN = SensitiveDataPattern(
        name="Social Security Number",
        description="US Social Security Number",
        pattern=r"\b(?!000|666|9\d{2})([0-8]\d{2}|7([0-6]\d))-(?!00)(\d{2})-(?!0000)(\d{4})\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.PII,
        validation_func="validate_ssn"
    )

    # Credit Card Numbers
    CREDIT_CARD = SensitiveDataPattern(
        name="Credit Card Number",
        description="Credit card number (major brands)",
        pattern=r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.PCI,
        validation_func="validate_credit_card"
    )

    # Credit Card with separators
    CREDIT_CARD_FORMATTED = SensitiveDataPattern(
        name="Formatted Credit Card Number",
        description="Credit card with dashes or spaces",
        pattern=r"\b(?:4[0-9]{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9](?:[0-9]{2})?|5[1-5][0-9]{2}[\s-]?[0-9]{4}[\s-]?[0-9]{4}[\s-]?[0-9]{4}|3[47][0-9]{2}[\s-]?[0-9]{6}[\s-]?[0-9]{5})\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.PCI,
        validation_func="validate_credit_card"
    )

    # Email Addresses
    EMAIL_ADDRESS = SensitiveDataPattern(
        name="Email Address",
        description="Email address",
        pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        sensitivity=SensitivityLevel.MEDIUM,
        category=ComplianceCategory.PII
    )

    # Phone Numbers
    PHONE_NUMBER_US = SensitiveDataPattern(
        name="US Phone Number",
        description="US phone number (various formats)",
        pattern=r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b",
        sensitivity=SensitivityLevel.MEDIUM,
        category=ComplianceCategory.PII
    )

    # IP Addresses
    IP_ADDRESS = SensitiveDataPattern(
        name="IP Address",
        description="IPv4 address",
        pattern=r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        sensitivity=SensitivityLevel.LOW,
        category=ComplianceCategory.OTHER
    )

    # Date of Birth
    DATE_OF_BIRTH = SensitiveDataPattern(
        name="Date of Birth",
        description="Date of birth in common formats",
        pattern=r"\b(?:(?:0[1-9]|1[0-2])[/.-](?:0[1-9]|[12][0-9]|3[01])[/.-](?:19|20)\d{2}|(?:19|20)\d{2}[/.-](?:0[1-9]|1[0-2])[/.-](?:0[1-9]|[12][0-9]|3[01]))\b",
        sensitivity=SensitivityLevel.MEDIUM,
        category=ComplianceCategory.PII
    )

    # Passport Numbers
    PASSPORT_US = SensitiveDataPattern(
        name="US Passport Number",
        description="US passport number",
        pattern=r"\b[A-Z][0-9]{8}\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.PII
    )

    # Driver's License
    DRIVERS_LICENSE = SensitiveDataPattern(
        name="Driver's License Number",
        description="Driver's license number (common formats)",
        pattern=r"\b[A-Z][0-9]{7}\b|\b[A-Z][0-9]{8}\b|\b[0-9]{9}\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.PII
    )

    # Bank Account Numbers
    BANK_ACCOUNT = SensitiveDataPattern(
        name="Bank Account Number",
        description="Bank account number (common formats)",
        pattern=r"\b[0-9]{9,17}\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.FINANCIAL,
        context_rules=["must be near words like account, routing, bank"]
    )

    # API Keys/Tokens
    API_KEY = SensitiveDataPattern(
        name="API Key",
        description="Common API key formats",
        pattern=r"\b[A-Za-z0-9_\-]{32,45}\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.CREDENTIALS,
        context_rules=["must be near words like key, api, token, secret"]
    )

    # Medical Record Numbers
    MEDICAL_RECORD = SensitiveDataPattern(
        name="Medical Record Number",
        description="Medical record number (common formats)",
        pattern=r"\bMR[0-9]{6,10}\b|\b[A-Z]{2}[0-9]{6,10}\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.PHI
    )

    # Health Insurance Numbers
    HEALTH_INSURANCE = SensitiveDataPattern(
        name="Health Insurance Number",
        description="Health insurance ID number (common formats)",
        pattern=r"\b[A-Z0-9]{6,12}\b",
        sensitivity=SensitivityLevel.HIGH,
        category=ComplianceCategory.PHI,
        context_rules=["must be near words like health, insurance, coverage, plan"]
    )

    # Password patterns
    PASSWORD = SensitiveDataPattern(
        name="Password",
        description="Password in configuration or code",
        pattern=r"(?:password|passwd|pwd)[\s:=]+['\"](.*?)['\"]",
        sensitivity=SensitivityLevel.CRITICAL,
        category=ComplianceCategory.CREDENTIALS
    )

    @classmethod
    def get_all_patterns(cls) -> List[SensitiveDataPattern]:
        """Get all predefined patterns."""
        return [
            getattr(cls, attr) for attr in dir(cls)
            if not attr.startswith('_') and isinstance(getattr(cls, attr), SensitiveDataPattern)
        ]

    @classmethod
    def get_by_category(cls, category: ComplianceCategory) -> List[SensitiveDataPattern]:
        """Get all patterns for a specific compliance category."""
        return [p for p in cls.get_all_patterns() if p.category == category]

    @classmethod
    def get_by_sensitivity(cls, level: SensitivityLevel) -> List[SensitiveDataPattern]:
        """Get all patterns for a specific sensitivity level."""
        return [p for p in cls.get_all_patterns() if p.sensitivity == level]


class PatternValidators:
    """Validation functions for sensitive data patterns."""
    
    @staticmethod
    def validate_ssn(ssn: str) -> bool:
        """Validate a Social Security Number."""
        # Remove any hyphens or spaces
        ssn = re.sub(r'[\s-]', '', ssn)
        
        # Check if it's 9 digits
        if not re.match(r'^\d{9}$', ssn):
            return False
        
        # Check if it's not all zeros in each part
        if ssn[0:3] == '000' or ssn[3:5] == '00' or ssn[5:9] == '0000':
            return False
        
        # Check if first part is not 666 and not between 900-999
        if ssn[0:3] == '666' or int(ssn[0:3]) >= 900:
            return False
            
        return True
    
    @staticmethod
    def validate_credit_card(cc: str) -> bool:
        """Validate a credit card number using the Luhn algorithm."""
        # Remove any non-digit characters
        cc = re.sub(r'\D', '', cc)
        
        if not cc.isdigit():
            return False
            
        # Check length (most cards are between 13-19 digits)
        if not (13 <= len(cc) <= 19):
            return False
            
        # Luhn algorithm
        digits = [int(d) for d in cc]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(divmod(d * 2, 10))
        return checksum % 10 == 0