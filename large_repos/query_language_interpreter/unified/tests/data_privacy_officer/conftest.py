"""Shared test fixtures for privacy-focused query language interpreter."""

import json
import os
import tempfile
from typing import Dict, List, Any

import pandas as pd
import pytest


@pytest.fixture
def sample_data() -> Dict[str, pd.DataFrame]:
    """Create sample dataframes with various types of data including PII."""
    customers = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": [
            "John Smith", 
            "Jane Doe", 
            "Robert Johnson", 
            "Sarah Williams", 
            "Michael Brown"
        ],
        "email": [
            "john.smith@example.com",
            "jane.doe@example.com",
            "robert.j@example.com",
            "sarah.w@example.com",
            "michael.brown@example.com"
        ],
        "phone": [
            "+1-555-123-4567",
            "+1-555-234-5678",
            "+1-555-345-6789",
            "+1-555-456-7890",
            "+1-555-567-8901"
        ],
        "ssn": [
            "123-45-6789",
            "234-56-7890",
            "345-67-8901",
            "456-78-9012",
            "567-89-0123"
        ],
        "address": [
            "123 Main St, Anytown, CA 90210",
            "456 Oak Ave, Somecity, NY 10001",
            "789 Pine Rd, Othercity, TX 75001",
            "101 Elm Blvd, Anothercity, FL 33101",
            "202 Cedar Ln, Lastcity, WA 98101"
        ],
        "credit_card": [
            "4111-1111-1111-1111",
            "5555-5555-5555-4444",
            "3782-822463-10005",
            "6011-1111-1111-1117",
            "3530-1113-3330-0000"
        ],
        "customer_segment": ["Premium", "Standard", "Premium", "Standard", "Premium"],
        "join_date": ["2020-01-15", "2020-03-20", "2020-02-10", "2021-01-05", "2021-04-22"],
    })
    
    orders = pd.DataFrame({
        "order_id": [101, 102, 103, 104, 105, 106, 107],
        "customer_id": [1, 2, 1, 3, 4, 5, 2],
        "order_date": [
            "2022-01-10", 
            "2022-01-15", 
            "2022-02-05", 
            "2022-02-10", 
            "2022-03-01", 
            "2022-03-15",
            "2022-04-01"
        ],
        "product": [
            "Laptop", 
            "Smartphone", 
            "Tablet", 
            "Monitor", 
            "Printer", 
            "Scanner",
            "Headphones"
        ],
        "amount": [1200.00, 800.00, 500.00, 300.00, 250.00, 200.00, 150.00],
        "payment_method": ["Credit Card", "PayPal", "Credit Card", "Credit Card", "PayPal", "Credit Card", "PayPal"],
        "shipping_address": [
            "123 Main St, Anytown, CA 90210",
            "456 Oak Ave, Somecity, NY 10001",
            "123 Main St, Anytown, CA 90210",
            "789 Pine Rd, Othercity, TX 75001",
            "101 Elm Blvd, Anothercity, FL 33101",
            "202 Cedar Ln, Lastcity, WA 98101",
            "456 Oak Ave, Somecity, NY 10001"
        ],
        "transaction_id": [
            "TXN-12345-ABCDE",
            "TXN-23456-BCDEF",
            "TXN-34567-CDEFG",
            "TXN-45678-DEFGH",
            "TXN-56789-EFGHI",
            "TXN-67890-FGHIJ",
            "TXN-78901-GHIJK"
        ]
    })
    
    sensitive_data = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "health_condition": [
            "Hypertension", 
            "Diabetes", 
            "Asthma", 
            "Arthritis", 
            "Migraine"
        ],
        "income": [75000, 85000, 95000, 65000, 105000],
        "religion": ["Christian", "Jewish", "Muslim", "Hindu", "Buddhist"],
        "political_affiliation": ["Republican", "Democrat", "Independent", "Republican", "Democrat"],
        "biometric_id": ["BIO-12345", "BIO-23456", "BIO-34567", "BIO-45678", "BIO-56789"],
        "genetic_data": ["GEN-12345", "GEN-23456", "GEN-34567", "GEN-45678", "GEN-56789"],
        "patient_id": [123, 234, 345, 456, 567]
    })
    
    return {
        "customers": customers,
        "orders": orders,
        "sensitive_data": sensitive_data
    }


@pytest.fixture
def user_context() -> Dict[str, Any]:
    """Create a sample user context for testing."""
    return {
        "user_id": "user123",
        "username": "privacy_officer",
        "roles": ["data_privacy_officer", "compliance_auditor"],
        "permissions": [
            "view_pii", 
            "view_sensitive_data", 
            "run_privacy_queries", 
            "generate_compliance_reports"
        ],
        "department": "Compliance",
        "purpose": "compliance_audit",
        "data_access_level": "high"
    }


@pytest.fixture
def temp_log_path() -> str:
    """Provide a temporary path for testing logging functionality."""
    fd, path = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_queries() -> Dict[str, str]:
    """Provide sample queries for testing."""
    return {
        "standard": "SELECT name, email FROM customers WHERE customer_segment = 'Premium'",
        "sensitive": "SELECT name, ssn, credit_card FROM customers",
        "complex": """
            SELECT c.name, c.email, c.ssn, o.product, o.amount, s.health_condition, s.income 
            FROM customers c
            JOIN orders o ON c.id = o.customer_id
            JOIN sensitive_data s ON c.id = s.id
        """,
        "minimized": "SELECT name, email FROM customers",
        "anonymized": "SELECT ANONYMIZE(name), ANONYMIZE(email) FROM customers",
        "policy_violating": """
            SELECT c.name, c.ssn, c.credit_card, s.health_condition, s.genetic_data 
            FROM customers c
            JOIN sensitive_data s ON c.id = s.id
        """
    }


@pytest.fixture
def sample_policies() -> List[Dict[str, Any]]:
    """Provide sample data access policies for testing."""
    return [
        {
            "id": "policy1",
            "name": "No sensitive health data with identifiers",
            "description": "Prevents joining health conditions with directly identifying information",
            "prohibited_combinations": [
                {
                    "fields": ["name", "email", "ssn", "health_condition", "genetic_data"],
                    "threshold": 3,
                    "categories": ["direct_identifier", "health_data"]
                }
            ],
            "required_purpose": ["compliance_audit", "data_subject_request"],
            "allowed_roles": ["data_privacy_officer"]
        },
        {
            "id": "policy2",
            "name": "No financial data export",
            "description": "Prevents exporting full financial information",
            "prohibited_combinations": [
                {
                    "fields": ["credit_card", "ssn", "income"],
                    "threshold": 2,
                    "categories": ["financial_data"]
                }
            ],
            "required_purpose": ["fraud_investigation"],
            "allowed_roles": ["fraud_investigator", "security_officer"]
        },
        {
            "id": "policy3",
            "name": "Sensitive data field limit",
            "description": "Limits the number of sensitive fields that can be accessed in one query",
            "max_sensitive_fields": 3,
            "sensitive_fields": [
                "ssn", "credit_card", "health_condition", "income", 
                "religion", "political_affiliation", "genetic_data"
            ],
            "required_purpose": ["compliance_audit"],
            "allowed_roles": ["data_privacy_officer", "compliance_auditor"]
        }
    ]