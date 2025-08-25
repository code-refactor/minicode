"""Advanced tests for the Report Redaction functionality."""

import re
import json
import uuid
from typing import Dict, Any, List

import pytest

from securetask.reporting.redaction import (
    RedactionEngine, RedactionPattern, RedactionLevel
)


def test_redaction_pattern_complex():
    """Test complex redaction patterns with various regex patterns."""
    patterns = [
        # Credit card numbers with different formats
        RedactionPattern(
            name="credit_card",
            pattern=r"\b(?:\d{4}[- ]){3}\d{4}\b|\b\d{16}\b",
            replacement="[CREDIT CARD REDACTED]",
            description="Credit card number",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
        ),
        
        # Social Security Numbers
        RedactionPattern(
            name="ssn",
            pattern=r"\b\d{3}-\d{2}-\d{4}\b",
            replacement="[SSN REDACTED]",
            description="Social Security Number",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
        ),
        
        # AWS Access Keys
        RedactionPattern(
            name="aws_key",
            pattern=r"(?:AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
            replacement="[AWS KEY REDACTED]",
            description="AWS Access Key",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
        ),
        
        # API keys
        RedactionPattern(
            name="api_key",
            pattern=r"\b(api[_-]?key|token|secret)[=:]\s*['\"]?[A-Za-z0-9+/=]{16,}['\"]?",
            replacement="\\1=[API KEY REDACTED]",
            description="API key",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
        ),
        
        # Password in configuration
        RedactionPattern(
            name="password",
            pattern=r"(password|passwd|pwd)\s*[=:]\s*.*",
            replacement="\\1=[PASSWORD REDACTED]",
            description="Password in configuration",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
        ),
        
        # IPv6 addresses
        RedactionPattern(
            name="ipv6",
            pattern=r"(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}",
            replacement="[IPv6 REDACTED]",
            description="IPv6 address",
            levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH}
        ),
        
        # Internal hostnames
        RedactionPattern(
            name="internal_hostname",
            pattern=r"\b([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+internal\b",
            replacement="[HOSTNAME REDACTED]",
            description="Internal hostname",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
        ),
        
        # Database connection strings
        RedactionPattern(
            name="db_connection",
            pattern=r"jdbc:mysql:\/\/.*?user=.*?&password=.*?($|\s)",
            replacement="[DB CONNECTION REDACTED]",
            description="Database connection string",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
        ),
    ]
    
    # Test individual patterns against test cases
    test_cases = [
        (
            "Credit card: 4111-1111-1111-1111 and another 5555666677778888",
            RedactionLevel.LOW
        ),
        (
            "SSN: 123-45-6789",
            RedactionLevel.LOW
        ),
        (
            "AWS key: AKIAIOSFODNN7EXAMPLE",
            RedactionLevel.LOW
        ),
        (
            "api_key='abcdef1234567890abcdef1234567890'",
            RedactionLevel.LOW
        ),
        (
            "password = supersecret123",
            RedactionLevel.LOW
        ),
        (
            "IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            RedactionLevel.MEDIUM
        ),
        (
            "Internal hostname: server.internal",
            RedactionLevel.LOW
        ),
        (
            "DB: jdbc:mysql://localhost:3306/db?user=root&password=secret",
            RedactionLevel.LOW
        ),
    ]
    
    for pattern in patterns:
        for text, level in test_cases:
            if level in pattern.levels and pattern.matches(text):
                result = pattern.apply(text, level)
                assert result != text, f"Pattern {pattern.name} should have redacted text at {level} level"


def test_redaction_engine_comprehensive():
    """Test the redaction engine with multiple patterns and data types."""
    engine = RedactionEngine()
    
    # Test with complex nested structures
    test_data = {
        "customer": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "payment": {
                "card_number": "4111-1111-1111-1111",
                "expiration": "12/25",
                "billing_address": {
                    "street": "123 Main St",
                    "city": "Anytown",
                    "state": "CA",
                    "zip": "12345"
                }
            }
        },
        "technical_details": {
            "server": "app-server-01.internal",
            "ip_address": "192.168.1.100",
            "database": {
                "connection": "jdbc:mysql://localhost:3306/db?user=root&password=secret",
                "replica": "db-replica.internal"
            },
            "admin_contact": "admin@example.com"
        },
        "access_logs": [
            {
                "timestamp": "2023-01-01T12:34:56Z",
                "user": "admin",
                "ip": "10.0.0.15",
                "action": "login"
            },
            {
                "timestamp": "2023-01-01T12:35:10Z",
                "user": "john.doe@example.com",
                "ip": "192.168.1.50",
                "action": "view_data"
            }
        ],
        "sensitive_values": [
            "4111-1111-1111-1111", 
            "john.doe@example.com",
            "app-server-01.internal",
            "192.168.1.100"
        ]
    }
    
    # Test with LOW redaction
    low_redacted = engine.redact_dict(test_data, RedactionLevel.LOW)
    
    # Check specific redactions
    assert low_redacted["customer"]["email"] == "john.doe@example.com"  # Email not redacted at LOW
    assert "4111-1111-1111-1111" not in json.dumps(low_redacted)  # Card redacted
    assert "app-server-01.internal" not in json.dumps(low_redacted)  # Internal hostname redacted
    assert "192.168.1.100" in json.dumps(low_redacted)  # IP not redacted at LOW
    
    # Test with MEDIUM redaction
    medium_redacted = engine.redact_dict(test_data, RedactionLevel.MEDIUM)
    
    # Check specific redactions
    assert medium_redacted["customer"]["email"] != "john.doe@example.com"  # Email redacted at MEDIUM
    assert "4111-1111-1111-1111" not in json.dumps(medium_redacted)  # Card redacted
    assert "192.168.1.100" not in json.dumps(medium_redacted)  # IP redacted at MEDIUM
    assert "10.0.0.15" not in json.dumps(medium_redacted)  # IP in array redacted
    
    # Field-specific redaction levels - use flattened structure
    field_levels = {
        "customer": RedactionLevel.HIGH,
        "technical_details.ip_address": RedactionLevel.NONE  # Override to not redact IP using dot notation
    }
    
    custom_redacted = engine.redact_dict(test_data, RedactionLevel.MEDIUM, field_levels)
    
    # IP address should NOT be redacted due to specific override
    assert custom_redacted["technical_details"]["ip_address"] == "192.168.1.100"


def test_redaction_pattern_basic():
    """Test basic redaction pattern functionality."""
    # Create a simple redaction pattern
    pattern = RedactionPattern(
        name="test_pattern",
        pattern=r"secret-\d+",
        replacement="[REDACTED]",
        description="Test pattern",
        levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    )
    
    # Test basic match and replacement
    test_text = "This contains secret-123 and secret-456"
    redacted_text = pattern.apply(test_text, RedactionLevel.LOW)
    assert "secret-123" not in redacted_text
    assert "secret-456" not in redacted_text
    assert "[REDACTED]" in redacted_text
    
    # Test match detection
    assert pattern.matches("secret-789") == True
    assert pattern.matches("no match here") == False
    
    # Test different redaction levels
    assert pattern.apply("secret-123", RedactionLevel.LOW) == "[REDACTED]"
    assert pattern.apply("secret-123", RedactionLevel.MEDIUM) == "[REDACTED]"
    assert pattern.apply("secret-123", RedactionLevel.HIGH) == "[REDACTED]"
    assert pattern.apply("secret-123", RedactionLevel.NONE) == "secret-123"  # No redaction
    assert pattern.apply("secret-123", RedactionLevel.MAXIMUM) == "secret-123"  # Not in level set


def test_redaction_engine_basic():
    """Test basic redaction engine functionality."""
    engine = RedactionEngine()
    
    # Create and add pattern
    pattern = RedactionPattern(
        name="test_pattern",
        pattern=r"secret-\d+",
        replacement="[REDACTED]",
        description="Test pattern",
        levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    )
    engine.add_pattern(pattern)
    
    # Test simple text redaction
    test_text = "This contains secret-123 and secret-456"
    redacted_text = engine.redact_text(test_text, RedactionLevel.LOW)
    assert "secret-123" not in redacted_text
    assert "secret-456" not in redacted_text
    assert "[REDACTED]" in redacted_text
    
    # Test simple dictionary redaction
    test_dict = {
        "key1": "secret-123",
        "key2": "no secrets here",
        "nested": {
            "key3": "secret-456"
        }
    }
    
    redacted_dict = engine.redact_dict(test_dict, RedactionLevel.LOW)
    assert redacted_dict["key1"] == "[REDACTED]"
    assert redacted_dict["key2"] == "no secrets here"
    assert redacted_dict["nested"]["key3"] == "[REDACTED]"


def test_redaction_engine_custom_patterns():
    """Test the ability to add, remove, and modify custom redaction patterns."""
    engine = RedactionEngine()
    
    # Add a custom pattern
    custom_pattern = RedactionPattern(
        name="account_number",
        pattern=r"Account\s*#?\s*:\s*(\d{10,12})",
        replacement="[ACCOUNT NUMBER REDACTED]",
        description="Bank account number",
        levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    )
    
    engine.add_pattern(custom_pattern)
    
    # Test the pattern works
    test_text = "Customer account details: Account #: 1234567890"
    redacted = engine.redact_text(test_text, RedactionLevel.LOW)
    assert "1234567890" not in redacted
    assert "[ACCOUNT NUMBER REDACTED]" in redacted
    
    # Remove the pattern
    assert engine.remove_pattern("account_number") == True
    
    # Verify pattern is removed
    redacted_after_removal = engine.redact_text(test_text, RedactionLevel.LOW)
    assert redacted_after_removal == test_text  # No redaction should occur
    
    # Test removal of non-existent pattern
    assert engine.remove_pattern("non_existent") == False


def test_redaction_with_json_and_xml():
    """Test redaction with structured data formats like JSON and XML."""
    engine = RedactionEngine()
    
    # Add custom patterns for this test
    engine.add_pattern(RedactionPattern(
        name="custom_api_key",
        pattern=r'"api_key"\s*:\s*"([a-zA-Z0-9]{16,64})"',
        replacement='"api_key":"[API KEY REDACTED]"',
        description="API key in JSON",
        levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    ))
    
    engine.add_pattern(RedactionPattern(
        name="custom_xml_key",
        pattern=r'<secret_key>(.*?)</secret_key>',
        replacement='<secret_key>[SECRET KEY REDACTED]</secret_key>',
        description="Secret key in XML",
        levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    ))
    
    # Test with JSON string
    json_data = '''
    {
        "api_configuration": {
            "base_url": "https://api.example.com",
            "api_key": "abcdef1234567890abcdef1234567890",
            "timeout": 30
        },
        "auth": {
            "username": "admin",
            "password": "securePassword123"
        }
    }
    '''
    
    redacted_json = engine.redact_text(json_data, RedactionLevel.LOW)
    
    # Verify keys are redacted
    assert "abcdef1234567890abcdef1234567890" not in redacted_json
    assert "securePassword123" not in redacted_json
    
    # Test with XML content
    xml_data = '''
    <configuration>
        <api>
            <base_url>https://api.example.com</base_url>
            <secret_key>xyzabc0987654321xyzabc0987654321</secret_key>
            <timeout>30</timeout>
        </api>
        <auth>
            <username>admin</username>
            <password>securePassword123</password>
        </auth>
    </configuration>
    '''
    
    redacted_xml = engine.redact_text(xml_data, RedactionLevel.LOW)
    
    # Verify keys are redacted
    assert "xyzabc0987654321xyzabc0987654321" not in redacted_xml
    assert "securePassword123" not in redacted_xml
    assert "[SECRET KEY REDACTED]" in redacted_xml


def test_redaction_edge_cases():
    """Test redaction engine with edge cases."""
    engine = RedactionEngine()
    
    # Add a basic pattern
    engine.add_pattern(RedactionPattern(
        name="ip_address",
        pattern=r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        replacement="[IP REDACTED]",
        description="IP address",
        levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH}
    ))
    
    # Test with empty input
    assert engine.redact_text("", RedactionLevel.MEDIUM) == ""
    assert engine.redact_dict({}, RedactionLevel.MEDIUM) == {}
    
    # Test with None values in dictionary
    test_dict = {"ip": None, "name": "Test", "settings": None}
    redacted = engine.redact_dict(test_dict, RedactionLevel.MEDIUM)
    assert redacted["ip"] is None
    assert redacted["name"] == "Test"
    assert redacted["settings"] is None
    
    # Test with non-string values
    mixed_dict = {
        "ip": "192.168.1.1",
        "port": 8080,
        "active": True,
        "count": 42,
        "factors": [1, 2, 3, 4]
    }
    
    redacted_mixed = engine.redact_dict(mixed_dict, RedactionLevel.MEDIUM)
    assert redacted_mixed["ip"] == "[IP REDACTED]"
    assert redacted_mixed["port"] == 8080
    assert redacted_mixed["active"] is True
    assert redacted_mixed["count"] == 42
    assert redacted_mixed["factors"] == [1, 2, 3, 4]
    
    # Test with multiple redaction levels
    test_text = "IP: 192.168.1.1, email: admin@example.com"
    
    # At NONE level, nothing should be redacted
    none_redacted = engine.redact_text(test_text, RedactionLevel.NONE)
    assert none_redacted == test_text
    
    # At LOW level, email should not be redacted but internal hostnames would be
    low_redacted = engine.redact_text(test_text, RedactionLevel.LOW)
    assert "192.168.1.1" in low_redacted
    assert "admin@example.com" in low_redacted
    
    # At MEDIUM level, both IP and email should be redacted
    medium_redacted = engine.redact_text(test_text, RedactionLevel.MEDIUM)
    assert "192.168.1.1" not in medium_redacted
    assert "admin@example.com" not in medium_redacted
    
    # At HIGH level, both IP and email should be redacted
    high_redacted = engine.redact_text(test_text, RedactionLevel.HIGH)
    assert "192.168.1.1" not in high_redacted
    assert "admin@example.com" not in high_redacted
    
    # Test with nested list in dictionary
    nested_list_dict = {
        "servers": [
            {"name": "server1", "ip": "192.168.1.1"},
            {"name": "server2", "ip": "192.168.1.2"}
        ]
    }
    
    redacted_nested_list = engine.redact_dict(nested_list_dict, RedactionLevel.MEDIUM)
    assert redacted_nested_list["servers"][0]["ip"] == "[IP REDACTED]"
    assert redacted_nested_list["servers"][1]["ip"] == "[IP REDACTED]"


def test_redaction_patterns_builtin():
    """Test all built-in redaction patterns."""
    engine = RedactionEngine()
    
    test_cases = [
        # IP Addresses
        ("Internal server IP: 192.168.1.1", RedactionLevel.MEDIUM, "192.168.1.1", False),
        
        # Internal hostnames
        ("Server: app.internal", RedactionLevel.LOW, "app.internal", False),
        
        # Email addresses
        ("Contact: admin@example.com", RedactionLevel.MEDIUM, "admin@example.com", False),
        
        # API Keys
        ("api_key: abcdef1234567890abcdef", RedactionLevel.LOW, "abcdef1234567890abcdef", False),
        
        # Passwords
        ("password = secret123", RedactionLevel.LOW, "secret123", False),
        
        # Private keys
        ("-----BEGIN PRIVATE KEY-----\nMIIEvQIBADAN\n-----END PRIVATE KEY-----", RedactionLevel.LOW, "-----BEGIN PRIVATE KEY-----", False),
        
        # Credit cards
        ("Payment: 4111-1111-1111-1111", RedactionLevel.LOW, "4111-1111-1111-1111", False),
        
        # SSNs
        ("SSN: 123-45-6789", RedactionLevel.LOW, "123-45-6789", False),
        
        # Auth headers
        ("authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", RedactionLevel.LOW, "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", False),
        
        # Internal paths
        ("File: /var/www/html/app/config.php", RedactionLevel.MEDIUM, "/var/www/html", False),
    ]
    
    for text, level, sensitive_data, should_remain in test_cases:
        redacted = engine.redact_text(text, level)
        if should_remain:
            assert sensitive_data in redacted, f"Data should remain at {level} level"
        else:
            assert sensitive_data not in redacted, f"Data should be redacted at {level} level"