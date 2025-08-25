"""Tests for the PII detection module."""

import pandas as pd
import pytest

from privacy_query_interpreter.pii_detection.detector import PIIDetector, PIIMatch
from privacy_query_interpreter.pii_detection.patterns import PII_PATTERNS, PIIPattern


class TestPIIDetector:
    """Test cases for the PIIDetector class."""
    
    def test_initialization(self):
        """Test detector initialization with defaults."""
        detector = PIIDetector()
        assert detector.patterns is not None
        assert detector.confidence_threshold == 0.7
        assert detector.max_sample_size == 1000
        
        # Test with custom parameters
        custom_detector = PIIDetector(confidence_threshold=0.9, max_sample_size=500)
        assert custom_detector.confidence_threshold == 0.9
        assert custom_detector.max_sample_size == 500
    
    def test_detect_in_string(self):
        """Test PII detection in a single string."""
        detector = PIIDetector()
        
        # Test with valid email
        email = "test.user@example.com"
        matches = detector.detect_in_string(email, "user_email")
        assert len(matches) > 0
        assert any(match.pii_type == "email" for match in matches)
        
        # Test with valid SSN
        ssn = "123-45-6789"
        matches = detector.detect_in_string(ssn, "social_security")
        assert len(matches) > 0
        assert any(match.pii_type == "ssn" for match in matches)
        
        # Test with valid credit card
        cc = "4111-1111-1111-1111"
        matches = detector.detect_in_string(cc, "payment_info")
        assert len(matches) > 0
        assert any(match.pii_type == "credit_card" for match in matches)
        
        # Test with non-PII string
        non_pii = "This is a regular string"
        matches = detector.detect_in_string(non_pii, "description")
        assert len(matches) == 0
    
    def test_detect_in_series(self, sample_data):
        """Test PII detection in a pandas Series."""
        detector = PIIDetector()
        
        # Test with email series
        emails = sample_data["customers"]["email"]
        matches = detector._detect_in_series(emails, "email")
        assert len(matches) > 0
        assert any(match.pii_type == "email" for match in matches)
        
        # Test with SSN series
        ssns = sample_data["customers"]["ssn"]
        matches = detector._detect_in_series(ssns, "ssn")
        assert len(matches) > 0
        assert any(match.pii_type == "ssn" for match in matches)
        
        # Test with non-PII series
        non_pii = sample_data["customers"]["customer_segment"]
        matches = detector._detect_in_series(non_pii, "segment")
        assert len(matches) == 0
    
    def test_detect_in_dataframe(self, sample_data):
        """Test PII detection in a pandas DataFrame."""
        detector = PIIDetector()
        
        # Test with customers dataframe
        matches = detector.detect_in_dataframe(sample_data["customers"])
        assert len(matches) > 0
        
        # Check that we found expected PII types
        pii_types = {match.pii_type for match in matches}
        assert "email" in pii_types
        assert "phone_number" in pii_types
        assert "ssn" in pii_types
        assert "credit_card" in pii_types
        
        # Check confidence scores
        for match in matches:
            assert match.confidence >= detector.confidence_threshold
    
    def test_detect_in_dict(self):
        """Test PII detection in a dictionary."""
        detector = PIIDetector()
        
        # Test with dictionary containing PII
        data = {
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "+1-555-123-4567",
            "account_id": "AC123456",
            "notes": "Customer reported an issue with their order"
        }
        
        matches = detector.detect_in_dict(data)
        assert len(matches) > 0
        
        # Check that we found expected PII types
        pii_types = {match.pii_type for match in matches}
        assert "email" in pii_types
        assert "phone_number" in pii_types
        assert "full_name" in pii_types
    
    def test_is_pii_field(self):
        """Test PII field detection based on name and sample."""
        detector = PIIDetector()
        
        # Test with obvious field names
        is_pii, pii_type, confidence = detector.is_pii_field("email")
        assert is_pii is True
        assert pii_type == "email"
        assert confidence > 0.7
        
        is_pii, pii_type, confidence = detector.is_pii_field("phone_number")
        assert is_pii is True
        assert pii_type == "phone_number"
        assert confidence > 0.7
        
        # Test with field name and sample value
        is_pii, pii_type, confidence = detector.is_pii_field(
            "contact", "john.doe@example.com")
        assert is_pii is True
        assert pii_type == "email"
        assert confidence > 0.7
        
        # Test with non-PII field
        is_pii, pii_type, confidence = detector.is_pii_field("product_category")
        assert is_pii is False
    
    def test_luhn_check(self):
        """Test credit card Luhn check algorithm."""
        from privacy_query_interpreter.pii_detection.patterns import luhn_check
        
        # Valid credit card numbers
        assert luhn_check("4111111111111111") is True
        assert luhn_check("4111-1111-1111-1111") is True
        assert luhn_check("5555 5555 5555 4444") is True
        
        # Invalid credit card numbers
        assert luhn_check("1234567890123456") is False
        assert luhn_check("1111-2222-3333-4444") is False
        
        # Non-numeric input
        assert luhn_check("ABCDEFG") is False
        
        # Wrong length
        assert luhn_check("12345") is False
    
    def test_field_context_scores(self):
        """Test context score calculation based on field names."""
        detector = PIIDetector()
        
        # Test with exact match
        scores = detector._calculate_field_context_scores("email")
        assert scores["email"] == 1.0
        
        # Test with partial match
        scores = detector._calculate_field_context_scores("user_email")
        assert scores["email"] > 0.5
        
        # Test with no match
        scores = detector._calculate_field_context_scores("product_category")
        assert scores["email"] == 0.0
    
    def test_custom_patterns(self):
        """Test detector with custom patterns."""
        # Create a custom pattern
        from privacy_query_interpreter.pii_detection.patterns import PIICategory
        import re
        
        custom_pattern = PIIPattern(
            name="employee_id",
            category=PIICategory.DIRECT_IDENTIFIER,
            description="Employee ID",
            regex=re.compile(r"EMP-\d{6}"),
            context_keywords=["employee", "employee_id", "emp_id", "worker"],
            sensitivity_level=2
        )
        
        custom_patterns = {"employee_id": custom_pattern}
        detector = PIIDetector(custom_patterns=custom_patterns)
        
        # Test with matching data
        matches = detector.detect_in_string("EMP-123456", "employee_id")
        assert len(matches) > 0
        assert any(match.pii_type == "employee_id" for match in matches)
        
        # Test adding a pattern after initialization
        detector.add_custom_pattern(PIIPattern(
            name="project_id",
            category=PIICategory.QUASI_IDENTIFIER,
            description="Project ID",
            regex=re.compile(r"PRJ-\d{4}"),
            context_keywords=["project", "project_id"],
            sensitivity_level=1
        ))
        
        matches = detector.detect_in_string("PRJ-1234", "project_id")
        assert len(matches) > 0
        assert any(match.pii_type == "project_id" for match in matches)
    
    def test_get_pattern_info(self):
        """Test retrieving pattern information."""
        detector = PIIDetector()
        
        # Get info for existing pattern
        email_info = detector.get_pattern_info("email")
        assert email_info is not None
        assert email_info["name"] == "email"
        assert email_info["category"] == "contact"
        
        # Attempt to get info for non-existent pattern
        invalid_info = detector.get_pattern_info("nonexistent_pattern")
        assert invalid_info is None
    
    def test_get_all_patterns(self):
        """Test retrieving all pattern information."""
        detector = PIIDetector()
        
        patterns = detector.get_all_patterns()
        assert len(patterns) > 0
        assert "email" in patterns
        assert "ssn" in patterns
        assert "credit_card" in patterns
        
        # Check pattern properties
        assert "name" in patterns["email"]
        assert "category" in patterns["email"]
        assert "description" in patterns["email"]