"""Tests for the anonymization functions."""

import re
import pandas as pd
import pytest

from privacy_query_interpreter.anonymization.anonymizer import (
    DataAnonymizer, AnonymizationMethod
)
from privacy_query_interpreter.pii_detection.detector import PIIDetector


class TestDataAnonymizer:
    """Test cases for the DataAnonymizer class."""
    
    def test_initialization(self):
        """Test anonymizer initialization with defaults."""
        anonymizer = DataAnonymizer()
        assert anonymizer.hmac_key is not None
        assert anonymizer.pseudonym_salt is not None
        assert anonymizer.pii_detector is None
        assert anonymizer.default_methods is not None
        assert anonymizer.method_handlers is not None
        assert anonymizer.field_patterns is not None
        
        # Test with custom parameters
        hmac_key = "test_key"
        pseudonym_salt = "test_salt"
        detector = PIIDetector()
        
        custom_anonymizer = DataAnonymizer(
            hmac_key=hmac_key,
            pseudonym_salt=pseudonym_salt,
            pii_detector=detector
        )
        
        assert custom_anonymizer.hmac_key == hmac_key.encode('utf-8')
        assert custom_anonymizer.pseudonym_salt == pseudonym_salt
        assert custom_anonymizer.pii_detector == detector
    
    def test_anonymization_method_enum(self):
        """Test the AnonymizationMethod enum values."""
        assert AnonymizationMethod.HASH == "hash"
        assert AnonymizationMethod.PSEUDONYMIZE == "pseudonymize"
        assert AnonymizationMethod.MASK == "mask"
        assert AnonymizationMethod.REDACT == "redact"
        assert AnonymizationMethod.GENERALIZE == "generalize"
        assert AnonymizationMethod.PERTURB == "perturb"
        assert AnonymizationMethod.TOKENIZE == "tokenize"
        assert AnonymizationMethod.DIFFERENTIAL == "differential"
    
    def test_hash_value(self):
        """Test hashing values."""
        anonymizer = DataAnonymizer()
        
        # Test various inputs
        text = "sensitive data"
        email = "test@example.com"
        number = 12345
        
        # Default SHA-256 with 16 chars
        hashed_text = anonymizer.hash_value(text)
        assert len(hashed_text) == 16
        assert re.match(r'^[0-9a-f]+$', hashed_text)
        
        # Test with different algorithms
        sha1_hash = anonymizer.hash_value(text, algorithm="sha1")
        md5_hash = anonymizer.hash_value(text, algorithm="md5")
        
        # Should produce different hashes
        assert sha1_hash != md5_hash
        
        # Test with different digest sizes
        short_hash = anonymizer.hash_value(text, digest_size=8)
        long_hash = anonymizer.hash_value(text, digest_size=32)
        
        assert len(short_hash) == 8
        assert len(long_hash) == 32
        
        # Test with numeric input
        number_hash = anonymizer.hash_value(number)
        assert len(number_hash) == 16
        assert re.match(r'^[0-9a-f]+$', number_hash)
        
        # Same input should produce same hash
        repeat_hash = anonymizer.hash_value(text)
        assert repeat_hash == hashed_text
    
    def test_pseudonymize_value(self):
        """Test pseudonymizing values."""
        anonymizer = DataAnonymizer(pseudonym_salt="fixed_salt_for_tests")
        
        # Test basic pseudonymization
        text = "John Smith"
        pseudonym = anonymizer.pseudonymize_value(text)
        
        # Should produce a consistent replacement
        assert pseudonym != text
        assert len(pseudonym) == 12  # Default length
        assert anonymizer.pseudonymize_value(text) == pseudonym  # Consistency check
        
        # Test with different field types
        email_pseudonym = anonymizer.pseudonymize_value("john@example.com", field_type="email")
        assert "@" in email_pseudonym  # Should look like an email
        
        phone_pseudonym = anonymizer.pseudonymize_value("+1-555-123-4567", field_type="phone")
        assert "-" in phone_pseudonym  # Should look like a phone number
        
        name_pseudonym = anonymizer.pseudonymize_value("Alice Johnson", field_type="name")
        assert "User-" in name_pseudonym  # Should have the User prefix
        
        # Test with prefix parameter
        prefixed = anonymizer.pseudonymize_value("test data", prefix="ANON")
        assert prefixed.startswith("ANON-")
    
    def test_mask_value(self):
        """Test masking values."""
        anonymizer = DataAnonymizer()
        
        # Test basic masking
        text = "sensitive data"
        masked = anonymizer.mask_value(text)
        
        # Should mask the middle portion
        assert masked != text
        assert "*" in masked
        
        # Test with different reveal parameters
        masked_reveal = anonymizer.mask_value(text, reveal_first=1, reveal_last=1)
        assert masked_reveal[0] == text[0]  # First character revealed
        assert masked_reveal[-1] == text[-1]  # Last character revealed
        assert all(c == "*" for c in masked_reveal[1:-1])  # Rest masked
        
        # Test specific field types
        email = "test@example.com"
        masked_email = anonymizer.mask_value(email, field_type="email")
        # Username should be masked, domain preserved
        assert "@example.com" in masked_email
        assert "test@" not in masked_email
        
        cc = "4111-1111-1111-1111"
        masked_cc = anonymizer.mask_value(cc, field_type="credit_card")
        # Should show only last 4 digits
        assert masked_cc.endswith("1111")
        assert masked_cc.startswith("************")
        
        phone = "+1-555-123-4567"
        masked_phone = anonymizer.mask_value(phone, field_type="phone")
        # Should mask middle digits
        assert masked_phone.startswith("+1")
        assert masked_phone.endswith("4567")
        
        ssn = "123-45-6789"
        masked_ssn = anonymizer.mask_value(ssn, field_type="ssn")
        # Should format as XXX-XX-1234
        assert masked_ssn == "XXX-XX-6789"
    
    def test_redact_value(self):
        """Test redacting values."""
        anonymizer = DataAnonymizer()
        
        # Test default redaction
        text = "sensitive data"
        redacted = anonymizer.redact_value(text)
        assert redacted == "[REDACTED]"
        
        # Test with custom replacement
        custom_redacted = anonymizer.redact_value(text, replacement="[REMOVED]")
        assert custom_redacted == "[REMOVED]"
        
        # Test with various field types (should all be the same)
        assert anonymizer.redact_value("test@example.com", field_type="email") == "[REDACTED]"
        assert anonymizer.redact_value(12345, field_type="id") == "[REDACTED]"
    
    def test_generalize_value(self):
        """Test generalizing values."""
        anonymizer = DataAnonymizer()
        
        # Test date generalization
        date = "2023-04-15"
        generalized_date = anonymizer.generalize_value(date, field_type="date")
        assert generalized_date == "2023-04"  # Reduced to year-month
        
        # Test zip code generalization
        zip_code = "12345"
        generalized_zip = anonymizer.generalize_value(zip_code, field_type="zip_code")
        assert generalized_zip == "12000"  # First 2 digits preserved
        
        # Test address generalization
        address = "123 Main St, Anytown, NY 10001"
        generalized_address = anonymizer.generalize_value(address, field_type="address")
        assert "123 Main St" not in generalized_address  # Street number removed
        assert "Anytown, NY" in generalized_address  # City/state preserved
        
        # Test age generalization
        age = "35"
        generalized_age = anonymizer.generalize_value(age, field_type="age")
        assert generalized_age == "30-39"  # Converted to range
    
    def test_perturb_value(self):
        """Test perturbing numeric values."""
        anonymizer = DataAnonymizer()
        
        # Test with integer
        value = 100
        perturbed = anonymizer.perturb_value(value)
        
        # Should be different but within range
        assert perturbed != value
        assert 90 <= perturbed <= 110  # Default noise_range is 0.1 (10%)
        
        # Test with float
        value = 100.0
        perturbed = anonymizer.perturb_value(value)
        
        # Should be different but within range
        assert perturbed != value
        assert 90.0 <= perturbed <= 110.0
        
        # Test with custom noise range
        value = 100
        perturbed = anonymizer.perturb_value(value, noise_range=0.5)
        
        # Should be different but within larger range
        assert perturbed != value
        assert 50 <= perturbed <= 150  # 50% noise range
        
        # Test with non-numeric value
        text = "not a number"
        perturbed = anonymizer.perturb_value(text)
        assert perturbed == text  # Should return unchanged
    
    def test_tokenize_value(self):
        """Test tokenizing values."""
        anonymizer = DataAnonymizer()
        
        # Test basic tokenization
        text = "sensitive data"
        token = anonymizer.tokenize_value(text)
        
        # Should produce a random token
        assert token != text
        assert len(token) == 10  # Default length
        
        # Same input should produce different tokens
        another_token = anonymizer.tokenize_value(text)
        assert another_token != token
        
        # Test with custom token length
        long_token = anonymizer.tokenize_value(text, token_length=20)
        assert len(long_token) == 20
    
    def test_anonymize_value(self):
        """Test anonymizing a single value with specified method."""
        anonymizer = DataAnonymizer()
        
        # Test various methods
        text = "sensitive data"
        
        # Hash method
        hashed = anonymizer.anonymize_value(text, AnonymizationMethod.HASH)
        assert hashed != text
        assert len(hashed) == 16
        
        # Pseudonymize method
        pseudonym = anonymizer.anonymize_value(text, AnonymizationMethod.PSEUDONYMIZE)
        assert pseudonym != text
        assert len(pseudonym) == 12
        
        # Mask method
        masked = anonymizer.anonymize_value(text, AnonymizationMethod.MASK)
        assert masked != text
        assert "*" in masked
        
        # Redact method
        redacted = anonymizer.anonymize_value(text, AnonymizationMethod.REDACT)
        assert redacted == "[REDACTED]"
        
        # Test with method as string
        string_method = anonymizer.anonymize_value(text, "mask")
        assert string_method != text
        assert "*" in string_method
    
    def test_anonymize_dataframe(self, sample_data):
        """Test anonymizing a pandas DataFrame."""
        anonymizer = DataAnonymizer()
        
        # Create a columns configuration
        columns_config = {
            "name": AnonymizationMethod.PSEUDONYMIZE,
            "email": AnonymizationMethod.MASK,
            "phone": AnonymizationMethod.MASK,
            "ssn": AnonymizationMethod.REDACT,
            "credit_card": {
                "method": AnonymizationMethod.MASK,
                "reveal_last": 4
            }
        }
        
        # Anonymize the customers dataframe
        result_df = anonymizer.anonymize_dataframe(
            sample_data["customers"].head(2),
            columns_config
        )
        
        # Check that the original dataframe is unchanged
        assert sample_data["customers"].iloc[0]["name"] != result_df.iloc[0]["name"]
        
        # Check that each column was anonymized according to its method
        for i in range(2):
            # Name should be pseudonymized
            assert result_df.iloc[i]["name"] != sample_data["customers"].iloc[i]["name"]
            
            # Email should be masked but still contain @
            assert "@" in result_df.iloc[i]["email"]
            assert result_df.iloc[i]["email"] != sample_data["customers"].iloc[i]["email"]
            
            # Phone should be masked
            assert result_df.iloc[i]["phone"] != sample_data["customers"].iloc[i]["phone"]
            
            # SSN should be redacted
            assert result_df.iloc[i]["ssn"] == "[REDACTED]"
            
            # Credit card should mask all but last 4 digits
            cc = result_df.iloc[i]["credit_card"]
            assert cc.endswith(sample_data["customers"].iloc[i]["credit_card"][-4:])
            assert cc != sample_data["customers"].iloc[i]["credit_card"]
        
        # Non-configured columns should be unchanged
        assert result_df["customer_segment"].equals(sample_data["customers"].head(2)["customer_segment"])
    
    def test_anonymize_dict(self):
        """Test anonymizing a dictionary."""
        anonymizer = DataAnonymizer()
        
        # Create a test dictionary
        data = {
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "+1-555-123-4567",
            "ssn": "123-45-6789",
            "customer_id": "C123456"
        }
        
        # Create a fields configuration
        fields_config = {
            "name": AnonymizationMethod.PSEUDONYMIZE,
            "email": AnonymizationMethod.MASK,
            "phone": AnonymizationMethod.MASK,
            "ssn": AnonymizationMethod.REDACT
        }
        
        # Anonymize the dictionary
        result = anonymizer.anonymize_dict(data, fields_config)
        
        # Check that each field was anonymized according to its method
        assert result["name"] != data["name"]
        assert "@" in result["email"]
        assert result["email"] != data["email"]
        assert result["phone"] != data["phone"]
        assert result["ssn"] == "[REDACTED]"
        
        # Non-configured fields should be unchanged
        assert result["customer_id"] == data["customer_id"]
    
    def test_anonymize_list_of_dicts(self):
        """Test anonymizing a list of dictionaries."""
        anonymizer = DataAnonymizer()
        
        # Create a test list of dictionaries
        data = [
            {
                "name": "John Smith",
                "email": "john.smith@example.com",
                "ssn": "123-45-6789"
            },
            {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "ssn": "234-56-7890"
            }
        ]
        
        # Create a fields configuration
        fields_config = {
            "name": AnonymizationMethod.PSEUDONYMIZE,
            "email": AnonymizationMethod.MASK,
            "ssn": AnonymizationMethod.REDACT
        }
        
        # Anonymize the list of dictionaries
        result = anonymizer.anonymize_list_of_dicts(data, fields_config)
        
        # Check that each field was anonymized according to its method
        for i in range(2):
            assert result[i]["name"] != data[i]["name"]
            assert "@" in result[i]["email"]
            assert result[i]["email"] != data[i]["email"]
            assert result[i]["ssn"] == "[REDACTED]"
    
    def test_auto_anonymize_dataframe(self, sample_data):
        """Test auto-anonymizing a DataFrame using PII detection."""
        # Create a PII detector
        detector = PIIDetector()
        anonymizer = DataAnonymizer(pii_detector=detector)
        
        # Auto-anonymize the customers dataframe
        result_df, applied_methods = anonymizer.auto_anonymize_dataframe(
            sample_data["customers"].head(2)
        )
        
        # Should detect and anonymize PII fields
        assert len(applied_methods) > 0
        assert any(column in applied_methods for column in [
            "name", "email", "phone", "ssn", "credit_card", "address"
        ])
        
        # Check that at least some fields were anonymized
        anonymized = False
        for column in applied_methods:
            if not result_df[column].equals(sample_data["customers"].head(2)[column]):
                anonymized = True
                break
        
        assert anonymized
        
        # Test with no PII detector
        no_detector_anonymizer = DataAnonymizer()
        with pytest.raises(ValueError):
            no_detector_anonymizer.auto_anonymize_dataframe(sample_data["customers"].head(2))
    
    def test_get_field_type(self):
        """Test field type detection based on name and sample."""
        anonymizer = DataAnonymizer()
        
        # Test with field names
        assert anonymizer.get_field_type("email") == "email"
        assert anonymizer.get_field_type("user_email") == "email"
        assert anonymizer.get_field_type("phone_number") == "phone"
        assert anonymizer.get_field_type("ssn") == "ssn"
        assert anonymizer.get_field_type("credit_card") == "credit_card"
        assert anonymizer.get_field_type("address") == "address"
        assert anonymizer.get_field_type("zip_code") == "zip_code"
        assert anonymizer.get_field_type("full_name") == "name"
        assert anonymizer.get_field_type("date_of_birth") == "date"
        assert anonymizer.get_field_type("age") == "age"
        
        # Test with sample values
        assert anonymizer.get_field_type("contact", "john.doe@example.com") == "email"
        assert anonymizer.get_field_type("contact", "+1-555-123-4567") == "phone"
        assert anonymizer.get_field_type("id_number", "123-45-6789") == "ssn"
        
        # Test with unknown field
        assert anonymizer.get_field_type("unknown_field") is None
    
    def test_guess_anonymization_method(self):
        """Test guessing the best anonymization method for a field."""
        anonymizer = DataAnonymizer()
        
        # Test with different field types
        assert anonymizer.guess_anonymization_method("email", "email") == AnonymizationMethod.MASK
        assert anonymizer.guess_anonymization_method("phone", "phone") == AnonymizationMethod.MASK
        assert anonymizer.guess_anonymization_method("ssn", "ssn") == AnonymizationMethod.MASK
        assert anonymizer.guess_anonymization_method("credit_card", "credit_card") == AnonymizationMethod.MASK
        assert anonymizer.guess_anonymization_method("address", "address") == AnonymizationMethod.GENERALIZE
        assert anonymizer.guess_anonymization_method("zip_code", "zip_code") == AnonymizationMethod.GENERALIZE
        assert anonymizer.guess_anonymization_method("name", "name") == AnonymizationMethod.PSEUDONYMIZE
        assert anonymizer.guess_anonymization_method("date_of_birth", "date") == AnonymizationMethod.GENERALIZE
        assert anonymizer.guess_anonymization_method("age", "age") == AnonymizationMethod.GENERALIZE
        
        # Test with field name and sample
        assert anonymizer.guess_anonymization_method("user_contact", None, "john.doe@example.com") == AnonymizationMethod.MASK
        
        # Test with PII detector
        detector = PIIDetector()
        with_detector = DataAnonymizer(pii_detector=detector)
        
        # Should use detector to categorize fields
        method = with_detector.guess_anonymization_method("email_address")
        assert method == AnonymizationMethod.MASK