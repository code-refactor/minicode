"""
Pattern validators for the File System Analyzer unified library.

This module provides validators for common sensitive data patterns.
"""

import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..core.types import SensitivityLevel, ComplianceCategory


@dataclass
class ValidationResult:
    """Result of pattern validation."""
    is_valid: bool
    confidence: float = 1.0
    normalized_value: Optional[str] = None
    validation_info: Optional[Dict[str, Any]] = None


class PatternValidator(ABC):
    """Abstract base class for pattern validators."""
    
    @abstractmethod
    def validate(self, value: str) -> ValidationResult:
        """Validate a pattern match."""
        pass


class SSNValidator(PatternValidator):
    """Social Security Number validator."""
    
    def validate(self, value: str) -> ValidationResult:
        """Validate an SSN."""
        # Remove formatting
        ssn = re.sub(r'[\s-]', '', value)
        
        if not re.match(r'^\d{9}$', ssn):
            return ValidationResult(False, 0.0)
            
        # Check for invalid patterns
        if (ssn[0:3] in ['000', '666'] or 
            ssn[0:3].startswith('9') or
            ssn[3:5] == '00' or 
            ssn[5:9] == '0000'):
            return ValidationResult(False, 0.0)
            
        return ValidationResult(
            True, 
            0.9, 
            normalized_value=f"{ssn[0:3]}-{ssn[3:5]}-{ssn[5:9]}"
        )


class CreditCardValidator(PatternValidator):
    """Credit card number validator using Luhn algorithm."""
    
    def validate(self, value: str) -> ValidationResult:
        """Validate a credit card number."""
        # Remove non-digits
        cc = re.sub(r'\D', '', value)
        
        if not cc.isdigit() or not (13 <= len(cc) <= 19):
            return ValidationResult(False, 0.0)
            
        # Luhn algorithm
        digits = [int(d) for d in cc]
        checksum = sum(digits[-1::-2])
        for d in digits[-2::-2]:
            doubled = d * 2
            checksum += doubled if doubled < 10 else doubled - 9
            
        is_valid = checksum % 10 == 0
        return ValidationResult(is_valid, 0.9 if is_valid else 0.0)


class EmailValidator(PatternValidator):
    """Email address validator."""
    
    def validate(self, value: str) -> ValidationResult:
        """Validate an email address."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        is_valid = bool(re.match(pattern, value))
        return ValidationResult(is_valid, 0.8 if is_valid else 0.0)


class PhoneValidator(PatternValidator):
    """Phone number validator."""
    
    def validate(self, value: str) -> ValidationResult:
        """Validate a phone number."""
        # Remove formatting
        phone = re.sub(r'[\s\-\(\)\.]', '', value)
        
        if phone.startswith('+1'):
            phone = phone[2:]
        elif phone.startswith('1') and len(phone) == 11:
            phone = phone[1:]
            
        if len(phone) == 10 and phone.isdigit():
            return ValidationResult(True, 0.8)
        return ValidationResult(False, 0.0)