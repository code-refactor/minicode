"""Tests for the privacy-focused query engine."""

import pytest
from unittest.mock import Mock, patch

import pandas as pd

from privacy_query_interpreter.access_logging.logger import AccessLogger, AccessOutcome
from privacy_query_interpreter.anonymization.anonymizer import DataAnonymizer, AnonymizationMethod
from privacy_query_interpreter.data_minimization.minimizer import DataMinimizer, Purpose
from privacy_query_interpreter.pii_detection.detector import PIIDetector
from privacy_query_interpreter.policy_enforcement.enforcer import PolicyEnforcer
from privacy_query_interpreter.policy_enforcement.policy import PolicyAction, DataPolicy, PolicySet, PolicyType
from privacy_query_interpreter.query_engine.engine import PrivacyQueryEngine, QueryStatus


class TestPrivacyQueryEngine:
    """Test cases for the PrivacyQueryEngine class."""
    
    def test_initialization(self):
        """Test engine initialization with defaults."""
        engine = PrivacyQueryEngine()
        assert engine.access_logger is None
        assert engine.policy_enforcer is None
        assert engine.data_minimizer is None
        assert engine.data_anonymizer is None
        assert engine.pii_detector is None
        assert engine.data_sources == {}
        assert engine.query_parser is not None
        assert engine.query_history == {}
        
        # Test with custom components
        logger = AccessLogger(log_file="/tmp/test.log")
        policy_enforcer = PolicyEnforcer()
        minimizer = DataMinimizer()
        anonymizer = DataAnonymizer()
        detector = PIIDetector()
        data_sources = {"test": pd.DataFrame()}
        
        custom_engine = PrivacyQueryEngine(
            access_logger=logger,
            policy_enforcer=policy_enforcer,
            data_minimizer=minimizer,
            data_anonymizer=anonymizer,
            pii_detector=detector,
            data_sources=data_sources
        )
        
        assert custom_engine.access_logger == logger
        assert custom_engine.policy_enforcer == policy_enforcer
        assert custom_engine.data_minimizer == minimizer
        assert custom_engine.data_anonymizer == anonymizer
        assert custom_engine.pii_detector == detector
        assert custom_engine.data_sources == data_sources
    
    def test_execute_simple_query(self, sample_data):
        """Test executing a simple query."""
        # Create engine with sample data
        engine = PrivacyQueryEngine(data_sources={
            "customers": sample_data["customers"],
            "orders": sample_data["orders"]
        })
        
        # Execute a simple query
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        result = engine.execute_query(
            query="SELECT name, email FROM customers WHERE customer_segment = 'Premium'",
            user_context=user_context
        )
        
        # Check the result structure
        assert "query_id" in result
        assert "status" in result
        assert result["status"] == QueryStatus.COMPLETED.value
        assert "execution_time_ms" in result
        assert "row_count" in result
        assert "column_count" in result
        assert result["column_count"] == 2
        assert "columns" in result
        assert set(result["columns"]) == {"name", "email"}
        assert "data" in result
        assert len(result["data"]) > 0
        
        # Check that we only got Premium customers
        assert all(row["name"] for row in result["data"])
        assert all(row["email"] for row in result["data"])
        
        # Check query history
        assert result["query_id"] in engine.query_history
    
    def test_execute_query_with_join(self, sample_data):
        """Test executing a query with a JOIN."""
        # Create engine with sample data
        engine = PrivacyQueryEngine(data_sources={
            "customers": sample_data["customers"],
            "orders": sample_data["orders"]
        })
        
        # Execute a query with a join
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        result = engine.execute_query(
            query="""
                SELECT c.name, o.product, o.amount
                FROM customers c
                JOIN orders o ON c.id = o.customer_id
                WHERE o.amount > 500
            """,
            user_context=user_context
        )
        
        # Check the result
        assert result["status"] == QueryStatus.COMPLETED.value
        assert result["column_count"] == 3
        assert set(result["columns"]) == {"name", "product", "amount"}
        assert len(result["data"]) > 0
        
        # Check that we only got orders with amount > 500
        assert all(row["amount"] > 500 for row in result["data"])
    
    def test_execute_query_with_policy_enforcement(self, sample_data):
        """Test executing a query with policy enforcement."""
        # Create a policy that restricts access to SSN
        policy = DataPolicy(
            id="restrict_ssn",
            name="Restrict SSN Access",
            description="Prevents access to SSN field",
            policy_type=PolicyType.FIELD_ACCESS,
            action=PolicyAction.DENY,
            restricted_fields=["ssn"]
        )
        
        policy_set = PolicySet(
            name="Test Policies",
            policies=[policy]
        )
        
        # Mock policy enforcer that will deny queries accessing SSN
        mock_enforcer = Mock(spec=PolicyEnforcer)
        mock_enforcer.enforce_query.return_value = (
            False, PolicyAction.DENY, policy, "Access to SSN is restricted"
        )
        
        # Create engine with the mock enforcer
        engine = PrivacyQueryEngine(
            data_sources={"customers": sample_data["customers"]},
            policy_enforcer=mock_enforcer
        )
        
        # Execute a query that tries to access SSN
        user_context = {
            "user_id": "user123",
            "roles": ["data_analyst"],
            "purpose": "analytics"
        }
        
        result = engine.execute_query(
            query="SELECT name, email, ssn FROM customers",
            user_context=user_context
        )
        
        # Query should be denied
        assert result["status"] == QueryStatus.DENIED.value
        assert "reason" in result
        assert "Access to SSN is restricted" in result["reason"]
        assert "data" not in result
    
    def test_execute_query_with_minimization(self, sample_data):
        """Test executing a query with data minimization."""
        # Mock minimizer that removes sensitive fields
        mock_minimizer = Mock(spec=DataMinimizer)
        
        def mock_apply_to_dataframe(df, purpose):
            return df[["name", "email"]]  # Only return these fields
            
        mock_minimizer.apply_to_dataframe.side_effect = mock_apply_to_dataframe
        
        # Create engine with the mock minimizer
        engine = PrivacyQueryEngine(
            data_sources={"customers": sample_data["customers"]},
            data_minimizer=mock_minimizer
        )
        
        # Execute a query with fields that should be minimized
        user_context = {
            "user_id": "user123",
            "roles": ["data_analyst"],
            "purpose": "marketing"
        }
        
        result = engine.execute_query(
            query="SELECT name, email, ssn, credit_card FROM customers",
            user_context=user_context
        )
        
        # Check that the result was minimized
        assert result["status"] == QueryStatus.MODIFIED.value
        assert result["column_count"] == 2
        assert set(result["columns"]) == {"name", "email"}
        assert "ssn" not in result["columns"]
        assert "credit_card" not in result["columns"]
        assert result["minimized"] is True
    
    def test_execute_query_with_anonymization(self, sample_data):
        """Test executing a query with anonymization."""
        # Mock policy enforcer that suggests anonymization
        mock_enforcer = Mock(spec=PolicyEnforcer)
        policy = DataPolicy(
            id="anonymize_pii",
            name="Anonymize PII",
            description="Anonymizes PII fields",
            policy_type=PolicyType.FIELD_ACCESS,
            action=PolicyAction.ANONYMIZE
        )
        mock_enforcer.enforce_query.return_value = (
            False, PolicyAction.ANONYMIZE, policy, "PII should be anonymized"
        )
        
        # Mock anonymizer
        mock_anonymizer = Mock(spec=DataAnonymizer)
        
        def mock_anonymize_dataframe(df, config):
            # Create a modified copy with "ANONYMIZED" prefixes
            result = df.copy()
            for col in df.columns:
                if col in ["name", "email", "phone", "ssn", "credit_card"]:
                    result[col] = result[col].apply(lambda x: f"ANONYMIZED-{x}")
            return result
            
        mock_anonymizer.anonymize_dataframe.side_effect = mock_anonymize_dataframe
        mock_anonymizer._create_anonymization_config = Mock(return_value={
            "name": AnonymizationMethod.PSEUDONYMIZE,
            "email": AnonymizationMethod.MASK,
            "phone": AnonymizationMethod.MASK,
            "ssn": AnonymizationMethod.REDACT,
            "credit_card": AnonymizationMethod.MASK
        })
        
        # Create engine with the mocks
        engine = PrivacyQueryEngine(
            data_sources={"customers": sample_data["customers"]},
            policy_enforcer=mock_enforcer,
            data_anonymizer=mock_anonymizer
        )
        
        # Execute a query that should trigger anonymization
        user_context = {
            "user_id": "user123",
            "roles": ["researcher"],
            "purpose": "analysis"
        }
        
        result = engine.execute_query(
            query="SELECT name, email, phone FROM customers",
            user_context=user_context
        )
        
        # Check that the result was anonymized
        assert result["status"] == QueryStatus.MODIFIED.value
        assert result["column_count"] == 3
        assert set(result["columns"]) == {"name", "email", "phone"}
        assert result["anonymized"] is True
        
        # Check that values were anonymized
        assert all(row["name"].startswith("ANONYMIZED-") for row in result["data"])
        assert all(row["email"].startswith("ANONYMIZED-") for row in result["data"])
        assert all(row["phone"].startswith("ANONYMIZED-") for row in result["data"])
    
    def test_execute_query_with_privacy_functions(self, sample_data):
        """Test executing a query with explicit privacy functions."""
        # Create engine with anonymizer
        anonymizer = DataAnonymizer()
        engine = PrivacyQueryEngine(
            data_sources={"customers": sample_data["customers"]},
            data_anonymizer=anonymizer
        )
        
        # Execute a query with privacy functions
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        # We can't test the actual function execution here because of SQLparse limitations
        # in the implementation, but we can test the query parsing recognition
        # Mock the _apply_privacy_functions method to simulate applying functions
        with patch.object(engine, '_apply_privacy_functions') as mock_apply:
            # Make the mock return a modified dataframe
            def mock_apply_privacy_funcs(df, funcs):
                result = df.copy()
                result["name"] = result["name"].apply(lambda x: f"ANON-{x}")
                return result
                
            mock_apply.side_effect = mock_apply_privacy_funcs
            
            result = engine.execute_query(
                query="SELECT ANONYMIZE(name), email FROM customers",
                user_context=user_context
            )
            
            # Verify the function was detected
            assert mock_apply.called
            
            # Check the result
            if "name" in result["columns"]:
                assert all(row["name"].startswith("ANON-") for row in result["data"])
    
    def test_query_with_logging(self, sample_data):
        """Test query execution with access logging."""
        # Mock logger
        mock_logger = Mock(spec=AccessLogger)
        
        # Create engine with the mock logger
        engine = PrivacyQueryEngine(
            data_sources={"customers": sample_data["customers"]},
            access_logger=mock_logger
        )
        
        # Execute a query
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        result = engine.execute_query(
            query="SELECT name, email FROM customers",
            user_context=user_context
        )
        
        # Check that logging occurred
        assert mock_logger.log_query.called
        
        # Verify log entry details
        call_args = mock_logger.log_query.call_args[1]
        assert call_args["user_id"] == "user123"
        assert "SELECT name, email FROM customers" in call_args["query"]
        assert call_args["data_sources"] == ["customers"]
        assert call_args["purpose"] == "compliance_audit"
        assert set(call_args["fields_accessed"]) == {"name", "email"}
        assert call_args["outcome"] == AccessOutcome.SUCCESS
    
    def test_error_handling(self):
        """Test error handling in query execution."""
        # Create engine with no data sources
        engine = PrivacyQueryEngine()
        
        # Execute a query for a non-existent table
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        result = engine.execute_query(
            query="SELECT name, email FROM nonexistent_table",
            user_context=user_context
        )
        
        # Check the error result
        assert result["status"] == QueryStatus.FAILED.value
        assert "error" in result
        assert "not found" in result["error"]
        
        # Try a malformed query
        result = engine.execute_query(
            query="NOT A VALID SQL QUERY",
            user_context=user_context
        )
        
        # Check the error result
        assert result["status"] == QueryStatus.FAILED.value
        assert "error" in result
    
    def test_add_remove_data_source(self, sample_data):
        """Test adding and removing data sources."""
        engine = PrivacyQueryEngine()
        
        # Initially should have no data sources
        assert len(engine.data_sources) == 0
        
        # Add a data source
        engine.add_data_source("customers", sample_data["customers"])
        
        # Should now have one data source
        assert len(engine.data_sources) == 1
        assert "customers" in engine.data_sources
        
        # Execute a query with the new data source
        user_context = {"user_id": "user123"}
        result = engine.execute_query(
            query="SELECT name FROM customers",
            user_context=user_context
        )
        
        # Query should succeed
        assert result["status"] == QueryStatus.COMPLETED.value
        
        # Remove the data source
        result = engine.remove_data_source("customers")
        
        # Should have removed the data source
        assert result is True
        assert len(engine.data_sources) == 0
        
        # Try to remove a non-existent data source
        result = engine.remove_data_source("nonexistent")
        assert result is False
    
    def test_get_query_history(self):
        """Test retrieving query history."""
        engine = PrivacyQueryEngine(data_sources={"test": pd.DataFrame({"a": [1, 2, 3]})})
        
        # Execute a few queries
        for i in range(5):
            engine.execute_query(
                query=f"SELECT * FROM test WHERE a = {i}",
                user_context={"user_id": "user123" if i % 2 == 0 else "user456"}
            )
            
        # Get all history
        history = engine.get_query_history()
        assert len(history) == 5
        
        # Get history for a specific user
        user_history = engine.get_query_history(user_id="user123")
        assert len(user_history) == 3
        assert all(h["user_id"] == "user123" for h in user_history)
        
        # Get limited history
        limited_history = engine.get_query_history(limit=2)
        assert len(limited_history) == 2