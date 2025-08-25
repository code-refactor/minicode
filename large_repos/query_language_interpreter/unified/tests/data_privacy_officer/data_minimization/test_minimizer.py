"""Tests for the data minimization module."""

import pandas as pd
import pytest

from privacy_query_interpreter.data_minimization.minimizer import (
    DataMinimizer, Purpose, DataCategory, FIELD_CATEGORY_MAPPING
)
from privacy_query_interpreter.pii_detection.detector import PIIDetector


class TestDataMinimizer:
    """Test cases for the DataMinimizer class."""
    
    def test_initialization(self):
        """Test minimizer initialization with defaults."""
        minimizer = DataMinimizer()
        assert minimizer.field_categories is not None
        assert minimizer.purpose_categories is not None
        assert minimizer.pii_detector is None
        
        # Test with custom detector
        detector = PIIDetector()
        custom_minimizer = DataMinimizer(pii_detector=detector)
        assert custom_minimizer.pii_detector == detector
        
        # Test with custom field categories
        custom_categories = {
            "custom_field": DataCategory.SENSITIVE
        }
        custom_minimizer = DataMinimizer(custom_field_categories=custom_categories)
        assert "custom_field" in custom_minimizer.field_categories
        assert custom_minimizer.field_categories["custom_field"] == DataCategory.SENSITIVE
    
    def test_get_allowed_fields(self):
        """Test filtering fields based on purpose."""
        minimizer = DataMinimizer()
        
        # Test with compliance audit purpose (allows access to sensitive data)
        fields = [
            "name", "email", "phone", "ssn", "credit_card", 
            "product", "amount", "transaction_id"
        ]
        
        allowed = minimizer.get_allowed_fields(fields, Purpose.COMPLIANCE_AUDIT)
        
        # Check that sensitive fields are allowed for compliance audit
        assert "name" in allowed
        assert "email" in allowed
        assert "phone" in allowed
        assert "ssn" in allowed
        assert "credit_card" in allowed
        
        # Test with marketing purpose (more restricted)
        allowed = minimizer.get_allowed_fields(fields, Purpose.MARKETING)
        
        # Check that sensitive fields are filtered out for marketing
        assert "name" not in allowed or "ssn" not in allowed or "credit_card" not in allowed
        
        # Transactional data should be allowed for analytics but not for marketing
        transactional_fields = ["product", "amount", "transaction_id"]
        allowed_analytics = minimizer.get_allowed_fields(transactional_fields, Purpose.ANALYTICS)
        assert all(field in allowed_analytics for field in transactional_fields)
        
        allowed_marketing = minimizer.get_allowed_fields(transactional_fields, Purpose.MARKETING)
        assert not all(field in allowed_marketing for field in transactional_fields)
    
    def test_apply_to_dataframe(self, sample_data):
        """Test applying data minimization to a DataFrame."""
        minimizer = DataMinimizer()
        
        # Apply minimization for compliance audit
        result_df = minimizer.apply_to_dataframe(
            sample_data["customers"], Purpose.COMPLIANCE_AUDIT)
        
        # Check that sensitive fields are preserved for compliance audit
        assert "name" in result_df.columns
        assert "email" in result_df.columns
        assert "ssn" in result_df.columns
        assert "credit_card" in result_df.columns
        
        # Apply minimization for marketing
        result_df = minimizer.apply_to_dataframe(
            sample_data["customers"], Purpose.MARKETING)
        
        # Marketing should not include highly sensitive fields
        sensitive_fields = ["ssn", "credit_card"]
        for field in sensitive_fields:
            assert field not in result_df.columns
            
        # Marketing should include demographic data
        demographic_fields = ["customer_segment"]
        for field in demographic_fields:
            assert field in result_df.columns
    
    def test_apply_to_dict(self):
        """Test applying data minimization to a dictionary."""
        minimizer = DataMinimizer()
        
        # Create a test dictionary with various field types
        data = {
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "+1-555-123-4567",
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "customer_segment": "Premium",
            "join_date": "2020-01-15",
            "product": "Laptop",
            "amount": 1200.00
        }
        
        # Apply minimization for compliance audit
        result = minimizer.apply_to_dict(data, Purpose.COMPLIANCE_AUDIT)
        
        # Check that sensitive fields are preserved for compliance audit
        assert "name" in result
        assert "email" in result
        assert "ssn" in result
        assert "credit_card" in result
        
        # Apply minimization for marketing
        result = minimizer.apply_to_dict(data, Purpose.MARKETING)
        
        # Marketing should not include highly sensitive fields
        sensitive_fields = ["ssn", "credit_card"]
        for field in sensitive_fields:
            assert field not in result
            
        # Marketing should include demographic data
        demographic_fields = ["customer_segment"]
        for field in demographic_fields:
            assert field in result
    
    def test_apply_to_list_of_dicts(self):
        """Test applying data minimization to a list of dictionaries."""
        minimizer = DataMinimizer()
        
        # Create a test list of dictionaries
        data = [
            {
                "name": "John Smith",
                "email": "john.smith@example.com",
                "ssn": "123-45-6789",
                "customer_segment": "Premium"
            },
            {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "ssn": "234-56-7890",
                "customer_segment": "Standard"
            }
        ]
        
        # Apply minimization for compliance audit
        result = minimizer.apply_to_list_of_dicts(data, Purpose.COMPLIANCE_AUDIT)
        
        # Check that sensitive fields are preserved for compliance audit
        assert "name" in result[0]
        assert "email" in result[0]
        assert "ssn" in result[0]
        
        # Apply minimization for marketing
        result = minimizer.apply_to_list_of_dicts(data, Purpose.MARKETING)
        
        # Marketing should not include highly sensitive fields
        assert "ssn" not in result[0]
        
        # Marketing should include demographic data
        assert "customer_segment" in result[0]
    
    def test_get_field_category(self):
        """Test retrieving the category for a field."""
        minimizer = DataMinimizer()
        
        # Test with known fields
        assert minimizer.get_field_category("email") == DataCategory.CONTACT_INFO
        assert minimizer.get_field_category("credit_card") == DataCategory.FINANCIAL
        assert minimizer.get_field_category("health_condition") == DataCategory.HEALTH
        
        # Test with field containing a known term
        assert minimizer.get_field_category("user_email") == DataCategory.CONTACT_INFO
        assert minimizer.get_field_category("customer_phone") == DataCategory.CONTACT_INFO
        
        # Test with unknown field
        assert minimizer.get_field_category("unknown_field") is None
    
    def test_add_field_category(self):
        """Test adding a new field category mapping."""
        minimizer = DataMinimizer()
        
        # Add a new field category
        minimizer.add_field_category("custom_field", DataCategory.SENSITIVE)
        
        # Verify the category was added
        assert minimizer.get_field_category("custom_field") == DataCategory.SENSITIVE
        
        # Add a category with string input
        minimizer.add_field_category("another_field", "demographic")
        
        # Verify the category was added
        assert minimizer.get_field_category("another_field") == DataCategory.DEMOGRAPHIC
    
    def test_add_purpose_category(self):
        """Test adding a category to a purpose."""
        minimizer = DataMinimizer()
        
        # Check initial state for MARKETING purpose
        allowed_categories = minimizer.purpose_categories[Purpose.MARKETING]
        assert DataCategory.FINANCIAL not in allowed_categories
        
        # Add financial data category to marketing purpose
        minimizer.add_purpose_category(Purpose.MARKETING, DataCategory.FINANCIAL)
        
        # Verify the category was added
        allowed_categories = minimizer.purpose_categories[Purpose.MARKETING]
        assert DataCategory.FINANCIAL in allowed_categories
        
        # Test with string inputs
        minimizer.add_purpose_category("security_monitoring", "financial")
        
        # Verify the category was added
        allowed_categories = minimizer.purpose_categories[Purpose.SECURITY_MONITORING]
        assert DataCategory.FINANCIAL in allowed_categories
    
    def test_set_purpose_categories(self):
        """Test setting the complete list of categories for a purpose."""
        minimizer = DataMinimizer()
        
        # Define a new set of categories for marketing
        categories = [
            DataCategory.DEMOGRAPHIC,
            DataCategory.BEHAVIORAL,
            DataCategory.LOCATION
        ]
        
        # Set the categories
        minimizer.set_purpose_categories(Purpose.MARKETING, categories)
        
        # Verify the categories were set
        allowed_categories = minimizer.purpose_categories[Purpose.MARKETING]
        assert len(allowed_categories) == 3
        assert DataCategory.DEMOGRAPHIC in allowed_categories
        assert DataCategory.BEHAVIORAL in allowed_categories
        assert DataCategory.LOCATION in allowed_categories
        assert DataCategory.FINANCIAL not in allowed_categories
        
        # Test with string inputs
        minimizer.set_purpose_categories("analytics", ["demographic", "behavioral"])
        
        # Verify the categories were set
        allowed_categories = minimizer.purpose_categories[Purpose.ANALYTICS]
        assert len(allowed_categories) == 2
        assert DataCategory.DEMOGRAPHIC in allowed_categories
        assert DataCategory.BEHAVIORAL in allowed_categories
    
    def test_with_pii_detector(self, sample_data):
        """Test integration with PII detector for field categorization."""
        detector = PIIDetector()
        minimizer = DataMinimizer(pii_detector=detector)
        
        # Test with a field that doesn't match by name but contains PII
        fields = ["unknown_1", "unknown_2"]
        
        # First, verify that without samples, these are not minimized
        allowed = minimizer.get_allowed_fields(fields, Purpose.MARKETING)
        assert "unknown_1" in allowed
        assert "unknown_2" in allowed
        
        # Now, with the detector, create context where these fields contain PII
        # and should be detected and minimized
        # This would be detected in a real scenario, but for this test we'll
        # simulate by directly adding some field categorizations
        minimizer.add_field_category("unknown_1", DataCategory.FINANCIAL)
        
        # Now check again
        allowed = minimizer.get_allowed_fields(fields, Purpose.MARKETING)
        assert "unknown_1" not in allowed  # Should be minimized now
        assert "unknown_2" in allowed  # Still allowed
    
    def test_purpose_enum(self):
        """Test the Purpose enum values."""
        # Check that all expected purposes are defined
        assert Purpose.COMPLIANCE_AUDIT == "compliance_audit"
        assert Purpose.DATA_SUBJECT_REQUEST == "data_subject_request"
        assert Purpose.FRAUD_INVESTIGATION == "fraud_investigation"
        assert Purpose.SECURITY_MONITORING == "security_monitoring"
        assert Purpose.PRODUCT_IMPROVEMENT == "product_improvement"
        assert Purpose.ANALYTICS == "analytics"
        assert Purpose.MARKETING == "marketing"
        assert Purpose.CUSTOMER_SUPPORT == "customer_support"
        assert Purpose.REGULATORY_REPORTING == "regulatory_reporting"
        assert Purpose.INTERNAL_OPERATIONS == "internal_operations"
    
    def test_data_category_enum(self):
        """Test the DataCategory enum values."""
        # Check that all expected categories are defined
        assert DataCategory.DIRECT_IDENTIFIERS == "direct_identifiers"
        assert DataCategory.CONTACT_INFO == "contact_info"
        assert DataCategory.FINANCIAL == "financial"
        assert DataCategory.HEALTH == "health"
        assert DataCategory.DEMOGRAPHIC == "demographic"
        assert DataCategory.BEHAVIORAL == "behavioral"
        assert DataCategory.TRANSACTIONAL == "transactional"
        assert DataCategory.TECHNICAL == "technical"
        assert DataCategory.EMPLOYMENT == "employment"
        assert DataCategory.EDUCATION == "education"
        assert DataCategory.BIOMETRIC == "biometric"
        assert DataCategory.LOCATION == "location"
        assert DataCategory.METADATA == "metadata"
        assert DataCategory.SENSITIVE == "sensitive"