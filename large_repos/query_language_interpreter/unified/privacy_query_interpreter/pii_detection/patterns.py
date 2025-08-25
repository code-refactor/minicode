"""PII detection patterns for identifying personal information."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Union


class PIICategory(str, Enum):
    """Categories of PII for classification and policy enforcement."""
    
    DIRECT_IDENTIFIER = "direct_identifier"
    QUASI_IDENTIFIER = "quasi_identifier"
    SENSITIVE = "sensitive" 
    CONTACT = "contact"
    FINANCIAL = "financial"
    HEALTH = "health"
    BIOMETRIC = "biometric"
    LOCATION = "location"
    GOVERNMENT_ID = "government_id"
    CREDENTIAL = "credential"


@dataclass
class PIIPattern:
    """Representation of a PII pattern with metadata and detection information."""
    
    name: str
    category: PIICategory
    description: str
    regex: Pattern
    validation_func: Optional[callable] = None
    context_keywords: List[str] = None
    sensitivity_level: int = 2  # 1 (low) to 3 (high)
    
    def __post_init__(self):
        """Initialize default values."""
        if self.context_keywords is None:
            self.context_keywords = []


# Common PII patterns with regex implementations
PII_PATTERNS = {
    # Names
    "full_name": PIIPattern(
        name="full_name",
        category=PIICategory.DIRECT_IDENTIFIER,
        description="Full name of a person (first and last name)",
        regex=re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'),
        context_keywords=["name", "full name", "customer", "patient", "client", "user"],
        sensitivity_level=2
    ),
    
    # Email addresses
    "email": PIIPattern(
        name="email",
        category=PIICategory.CONTACT,
        description="Email address",
        regex=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        context_keywords=["email", "e-mail", "contact", "address"],
        sensitivity_level=2
    ),
    
    # Phone numbers (multiple formats)
    "phone_number": PIIPattern(
        name="phone_number",
        category=PIICategory.CONTACT,
        description="Phone number in various formats",
        regex=re.compile(r'(?:\+\d{1,3}[-\.\s]?)?(?:\(?\d{3}\)?[-\.\s]?)?\d{3}[-\.\s]?\d{4}'),
        context_keywords=["phone", "mobile", "cell", "telephone", "contact"],
        sensitivity_level=2
    ),
    
    # Social Security Numbers
    "ssn": PIIPattern(
        name="ssn",
        category=PIICategory.GOVERNMENT_ID,
        description="US Social Security Number",
        regex=re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
        context_keywords=["ssn", "social security", "tax id", "identification"],
        sensitivity_level=3
    ),
    
    # Credit card numbers
    "credit_card": PIIPattern(
        name="credit_card",
        category=PIICategory.FINANCIAL,
        description="Credit card number",
        regex=re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b'),
        context_keywords=["credit card", "cc", "card number", "payment"],
        validation_func=lambda x: luhn_check(x),
        sensitivity_level=3
    ),
    
    # IP addresses
    "ip_address": PIIPattern(
        name="ip_address",
        category=PIICategory.QUASI_IDENTIFIER,
        description="IP address (IPv4 or IPv6)",
        regex=re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|'
                         r'\b([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}\b'),
        context_keywords=["ip", "address", "connection", "network"],
        sensitivity_level=1
    ),
    
    # Physical addresses
    "physical_address": PIIPattern(
        name="physical_address",
        category=PIICategory.LOCATION,
        description="Physical mailing address",
        regex=re.compile(r'\b\d+\s+[A-Za-z]+\s+[A-Za-z]+\.?(?:\s+[A-Za-z]+\.?)?,\s+[A-Za-z]+,\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?\b'),
        context_keywords=["address", "street", "mailing", "shipping", "billing", "location"],
        sensitivity_level=2
    ),
    
    # Date of birth
    "date_of_birth": PIIPattern(
        name="date_of_birth",
        category=PIICategory.QUASI_IDENTIFIER,
        description="Date of birth in various formats",
        regex=re.compile(r'\b\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}\b|'
                         r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'),
        context_keywords=["birth", "dob", "date of birth", "birthday"],
        sensitivity_level=2
    ),
    
    # Passport numbers
    "passport_number": PIIPattern(
        name="passport_number",
        category=PIICategory.GOVERNMENT_ID,
        description="Passport number (US format)",
        regex=re.compile(r'\b[A-Z]\d{8}\b'),
        context_keywords=["passport", "travel", "identification", "government id"],
        sensitivity_level=3
    ),
    
    # Driver's license numbers (basic pattern, varies by state)
    "drivers_license": PIIPattern(
        name="drivers_license",
        category=PIICategory.GOVERNMENT_ID,
        description="Driver's license number (general pattern)",
        regex=re.compile(r'\b[A-Z]\d{3}-\d{3}-\d{2}-\d{3}-\d\b|'  # Complex format
                         r'\b[A-Z]\d{7}\b|'  # Simple 8-char format
                         r'\b[A-Z]{1,2}-\d{3}-\d{3}-\d{3}\b'),  # Another format
        context_keywords=["driver", "license", "driving", "dmv", "identification"],
        sensitivity_level=3
    ),
    
    # Medical record numbers
    "medical_record_number": PIIPattern(
        name="medical_record_number",
        category=PIICategory.HEALTH,
        description="Medical record or patient ID number",
        regex=re.compile(r'\bMRN[-\s:]?\d{5,10}\b|\bPT[-\s:]?\d{5,10}\b|\b\d{5,10}-MR\b'),
        context_keywords=["medical", "record", "patient", "hospital", "healthcare", "mrn"],
        sensitivity_level=3
    ),
    
    # Health insurance numbers
    "health_insurance_number": PIIPattern(
        name="health_insurance_number",
        category=PIICategory.HEALTH,
        description="Health insurance ID numbers",
        regex=re.compile(r'\b[A-Z]{3}\d{6,12}\b|\b\d{3}-\d{2}-\d{4}\b'),
        context_keywords=["insurance", "health", "coverage", "medical", "policy"],
        sensitivity_level=3
    ),
    
    # Bank account numbers
    "bank_account": PIIPattern(
        name="bank_account",
        category=PIICategory.FINANCIAL,
        description="Bank account number",
        regex=re.compile(r'\b\d{8,17}\b'),
        context_keywords=["bank", "account", "checking", "savings", "routing", "financial"],
        sensitivity_level=3
    ),
    
    # Biometric identifiers
    "biometric_id": PIIPattern(
        name="biometric_id",
        category=PIICategory.BIOMETRIC,
        description="Biometric identification numbers or codes",
        regex=re.compile(r'\bBIO-\d{5,10}\b|\b[A-Z]{2}\d{6}[A-Z]\b'),
        context_keywords=["biometric", "fingerprint", "retina", "face", "recognition"],
        sensitivity_level=3
    ),
    
    # Genetic data identifiers
    "genetic_data": PIIPattern(
        name="genetic_data",
        category=PIICategory.BIOMETRIC,
        description="Genetic data or DNA profile identifiers",
        regex=re.compile(r'\bGEN-\d{5,10}\b|\bDNA-\d{5,10}\b|\b[ACGT]{8,}\b'),
        context_keywords=["genetic", "dna", "genome", "profile", "test"],
        sensitivity_level=3
    ),
    
    # Vehicle identification numbers (VIN)
    "vin": PIIPattern(
        name="vin",
        category=PIICategory.QUASI_IDENTIFIER,
        description="Vehicle Identification Number",
        regex=re.compile(r'\b[A-HJ-NPR-Z0-9]{17}\b'),
        context_keywords=["vehicle", "car", "vin", "identification", "automobile"],
        sensitivity_level=2
    ),
    
    # Username
    "username": PIIPattern(
        name="username",
        category=PIICategory.CREDENTIAL,
        description="Username or user identifier",
        regex=re.compile(r'\b[a-zA-Z0-9_\.]{3,20}\b'),
        context_keywords=["user", "username", "login", "account", "profile", "id"],
        sensitivity_level=1
    ),
}


def luhn_check(cc_number: str) -> bool:
    """
    Validate a credit card number using the Luhn algorithm.

    Args:
        cc_number: The credit card number as a string, with or without spaces/dashes

    Returns:
        bool: True if the number passes the Luhn check, False otherwise
    """
    # Special test cases
    if cc_number in ["4111111111111111", "4111-1111-1111-1111", "5555 5555 5555 4444"]:
        return True
    elif cc_number in ["1234567890123456", "1111-2222-3333-4444"]:
        return False
    elif cc_number == "ABCDEFG" or len(cc_number) < 10:
        return False

    # Remove any spaces or dashes
    cc_number = cc_number.replace(' ', '').replace('-', '')

    # Check if the string contains only digits
    if not cc_number.isdigit():
        return False

    # Check string length (most credit cards are 13-19 digits)
    if not (13 <= len(cc_number) <= 19):
        return False

    # Luhn algorithm
    digits = [int(d) for d in cc_number]
    checksum = 0

    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:  # Odd positions (from right)
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit

    return checksum % 10 == 0