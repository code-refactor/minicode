"""Tests for the policy enforcement engine."""

from unittest.mock import Mock, patch

import pytest

from privacy_query_interpreter.access_logging.logger import AccessLogger
from privacy_query_interpreter.pii_detection.detector import PIIDetector
from privacy_query_interpreter.policy_enforcement.enforcer import PolicyEnforcer
from privacy_query_interpreter.policy_enforcement.policy import (
    DataPolicy, PolicySet, PolicyType, PolicyAction, FieldCategory,
    FieldCombination
)


class TestPolicyEnforcer:
    """Test cases for the PolicyEnforcer class."""
    
    def test_initialization(self):
        """Test enforcer initialization with defaults."""
        enforcer = PolicyEnforcer()
        assert enforcer.policies is not None
        assert enforcer.policies.name == "Default"
        assert len(enforcer.policies.policies) == 0
        assert enforcer.pii_detector is None
        assert enforcer.access_logger is None
        assert enforcer.field_categories == {}
        
        # Test with custom components
        policies = PolicySet(name="Test Policies", policies=[])
        detector = PIIDetector()
        logger = AccessLogger(log_file="/tmp/test.log")
        field_categories = {"name": [FieldCategory.DIRECT_IDENTIFIER]}
        
        custom_enforcer = PolicyEnforcer(
            policies=policies,
            pii_detector=detector,
            access_logger=logger,
            field_categories=field_categories
        )
        
        assert custom_enforcer.policies == policies
        assert custom_enforcer.pii_detector == detector
        assert custom_enforcer.access_logger == logger
        assert custom_enforcer.field_categories == field_categories
    
    def test_enforce_query(self):
        """Test enforcing policies on a query."""
        # Create test policies
        test_policies = [
            # Policy requiring specific role
            DataPolicy(
                id="role_policy",
                name="Role Restriction",
                description="Requires specific role",
                policy_type=PolicyType.FIELD_ACCESS,
                action=PolicyAction.DENY,
                allowed_roles=["data_privacy_officer"]
            ),
            # Policy requiring specific purpose
            DataPolicy(
                id="purpose_policy",
                name="Purpose Restriction",
                description="Requires specific purpose",
                policy_type=PolicyType.PURPOSE_LIMITATION,
                action=PolicyAction.MINIMIZE,
                required_purpose=["compliance_audit"]
            ),
            # Policy restricting field combinations
            DataPolicy(
                id="combination_policy",
                name="Field Combination Restriction",
                description="Prevents sensitive combinations",
                policy_type=PolicyType.DATA_COMBINATION,
                action=PolicyAction.ANONYMIZE,
                prohibited_combinations=[
                    FieldCombination(
                        fields=["name", "ssn", "health_condition"],
                        threshold=3
                    )
                ]
            )
        ]
        
        policy_set = PolicySet(
            name="Test Policies",
            description="Test policy set",
            policies=test_policies
        )
        
        # Create mock logger
        mock_logger = Mock(spec=AccessLogger)
        
        # Create the enforcer
        enforcer = PolicyEnforcer(
            policies=policy_set,
            access_logger=mock_logger
        )
        
        # Test with appropriate role and purpose
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        # Query accessing a safe combination of fields
        is_allowed, action, policy, reason = enforcer.enforce_query(
            query_text="SELECT name, email FROM customers",
            fields=["name", "email"],
            data_sources=["customers"],
            joins=[],
            user_context=user_context
        )
        
        # Should be allowed
        assert is_allowed is True
        assert action == PolicyAction.ALLOW
        assert policy is None
        assert reason is None
        
        # Test with a sensitive combination of fields
        is_allowed, action, policy, reason = enforcer.enforce_query(
            query_text="SELECT name, ssn, health_condition FROM customers JOIN health_data",
            fields=["name", "ssn", "health_condition"],
            data_sources=["customers", "health_data"],
            joins=[("customers", "health_data")],
            user_context=user_context
        )
        
        # Should trigger the combination policy
        assert is_allowed is False
        assert action == PolicyAction.ANONYMIZE
        assert policy is not None
        assert policy.id == "combination_policy"
        assert reason is not None
        assert "name, ssn, health_condition" in reason
        
        # Verify that the violation was logged
        mock_logger.log_policy_violation.assert_called_once()
        
        # Test with missing required role
        user_context = {
            "user_id": "user456",
            "roles": ["data_analyst"],
            "purpose": "compliance_audit"
        }
        
        is_allowed, action, policy, reason = enforcer.enforce_query(
            query_text="SELECT name, email FROM customers",
            fields=["name", "email"],
            data_sources=["customers"],
            joins=[],
            user_context=user_context
        )
        
        # Should be denied by the role policy
        assert is_allowed is False
        assert action == PolicyAction.DENY
        assert policy is not None
        assert policy.id == "role_policy"
        assert reason is not None
        assert "roles" in reason
    
    def test_enforce_field_access(self):
        """Test enforcing field-level access policies."""
        # Create test policies for field access
        test_policies = [
            # Policy restricting specific fields
            DataPolicy(
                id="field_policy",
                name="Sensitive Field Restriction",
                description="Restricts sensitive fields",
                policy_type=PolicyType.FIELD_ACCESS,
                action=PolicyAction.DENY,
                restricted_fields=["ssn", "credit_card"]
            ),
            # Policy requiring anonymization for certain fields
            DataPolicy(
                id="anonymization_policy",
                name="Field Anonymization",
                description="Requires anonymization for certain fields",
                policy_type=PolicyType.FIELD_ACCESS,
                action=PolicyAction.ANONYMIZE,
                restricted_fields=["phone", "address"]
            )
        ]
        
        policy_set = PolicySet(
            name="Test Policies",
            description="Test policy set",
            policies=test_policies
        )
        
        # Create the enforcer
        enforcer = PolicyEnforcer(policies=policy_set)
        
        # Test with a list of fields
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        fields = ["name", "email", "ssn", "credit_card", "phone", "address"]
        
        allowed_fields, denied_fields, action, reason = enforcer.enforce_field_access(
            fields=fields,
            data_source="customers",
            user_context=user_context
        )
        
        # Should apply the most restrictive policy (DENY takes precedence over ANONYMIZE)
        assert action == PolicyAction.DENY
        assert reason is not None
        assert "denied" in reason
        
        # Check field categorization
        assert "name" in allowed_fields
        assert "email" in allowed_fields
        assert "ssn" in denied_fields
        assert "credit_card" in denied_fields
        assert "phone" in denied_fields
        assert "address" in denied_fields
    
    def test_enforce_data_combination(self):
        """Test enforcing data combination policies."""
        # Create test policies for data combinations
        test_policies = [
            # Policy restricting combinations of direct identifiers and sensitive data
            DataPolicy(
                id="combination_policy",
                name="Sensitive Combination Restriction",
                description="Prevents combining identifiers with sensitive data",
                policy_type=PolicyType.DATA_COMBINATION,
                action=PolicyAction.DENY,
                prohibited_combinations=[
                    FieldCombination(
                        categories=[FieldCategory.DIRECT_IDENTIFIER, FieldCategory.HEALTH],
                        threshold=2
                    )
                ]
            ),
            # Policy limiting the number of sensitive fields
            DataPolicy(
                id="sensitive_limit_policy",
                name="Sensitive Field Limit",
                description="Limits the number of sensitive fields",
                policy_type=PolicyType.DATA_COMBINATION,
                action=PolicyAction.MINIMIZE,
                max_sensitive_fields=2,
                sensitive_fields=["ssn", "credit_card", "health_condition", "income"]
            )
        ]
        
        policy_set = PolicySet(
            name="Test Policies",
            description="Test policy set",
            policies=test_policies
        )
        
        # Create field category mappings
        field_categories = {
            "name": [FieldCategory.DIRECT_IDENTIFIER],
            "email": [FieldCategory.DIRECT_IDENTIFIER],
            "health_condition": [FieldCategory.HEALTH, FieldCategory.SENSITIVE],
            "treatment": [FieldCategory.HEALTH]
        }
        
        # Create the enforcer
        enforcer = PolicyEnforcer(
            policies=policy_set,
            field_categories=field_categories
        )
        
        # Test with safe combination of fields
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        is_allowed, action, reason = enforcer.enforce_data_combination(
            fields=["name", "email"],
            user_context=user_context
        )
        
        # Should be allowed (all within same category)
        assert is_allowed is True
        assert action == PolicyAction.ALLOW
        assert reason is None
        
        # Test with prohibited combination of categories
        is_allowed, action, reason = enforcer.enforce_data_combination(
            fields=["name", "health_condition"],
            user_context=user_context
        )
        
        # Should be denied by the combination policy
        assert is_allowed is False
        assert action == PolicyAction.DENY
        assert reason is not None
        assert "combination" in reason
        
        # Test with too many sensitive fields
        is_allowed, action, reason = enforcer.enforce_data_combination(
            fields=["ssn", "credit_card", "health_condition"],
            user_context=user_context
        )
        
        # Should be minimized by the sensitive limit policy
        assert is_allowed is False
        assert action == PolicyAction.MINIMIZE
        assert reason is not None
        assert "sensitive fields" in reason
    
    def test_enforce_data_source_access(self):
        """Test enforcing data source access and join policies."""
        # Create test policies for data source access
        test_policies = [
            # Policy restricting specific data sources
            DataPolicy(
                id="source_policy",
                name="Data Source Restriction",
                description="Restricts certain data sources",
                policy_type=PolicyType.QUERY_SCOPE,
                action=PolicyAction.DENY,
                prohibited_data_sources=["confidential_data"]
            ),
            # Policy restricting specific joins
            DataPolicy(
                id="join_policy",
                name="Join Restriction",
                description="Prevents joining certain tables",
                policy_type=PolicyType.QUERY_SCOPE,
                action=PolicyAction.DENY,
                prohibited_joins=[("customers", "health_data")]
            )
        ]
        
        policy_set = PolicySet(
            name="Test Policies",
            description="Test policy set",
            policies=test_policies
        )
        
        # Create the enforcer
        enforcer = PolicyEnforcer(policies=policy_set)
        
        # Test with allowed data sources
        user_context = {
            "user_id": "user123",
            "roles": ["data_privacy_officer"],
            "purpose": "compliance_audit"
        }
        
        is_allowed, action, reason = enforcer.enforce_data_source_access(
            data_sources=["customers", "orders"],
            joins=[("customers", "orders")],
            user_context=user_context
        )
        
        # Should be allowed
        assert is_allowed is True
        assert action == PolicyAction.ALLOW
        assert reason is None
        
        # Test with prohibited data source
        is_allowed, action, reason = enforcer.enforce_data_source_access(
            data_sources=["customers", "confidential_data"],
            joins=[("customers", "confidential_data")],
            user_context=user_context
        )
        
        # Should be denied by the source policy
        assert is_allowed is False
        assert action == PolicyAction.DENY
        assert reason is not None
        assert "confidential_data" in reason
        
        # Test with prohibited join
        is_allowed, action, reason = enforcer.enforce_data_source_access(
            data_sources=["customers", "health_data"],
            joins=[("customers", "health_data")],
            user_context=user_context
        )
        
        # Should be denied by the join policy
        assert is_allowed is False
        assert action == PolicyAction.DENY
        assert reason is not None
        assert "customers" in reason and "health_data" in reason
    
    def test_categorize_fields(self):
        """Test field categorization with PII detector integration."""
        # Create a mock PII detector
        mock_detector = Mock(spec=PIIDetector)
        
        # Configure the mock to categorize fields
        def mock_is_pii_field(field, *args):
            if field == "name":
                return True, "full_name", 0.9
            elif field == "email":
                return True, "email", 0.9
            elif field == "phone":
                return True, "phone_number", 0.9
            elif field == "ssn":
                return True, "ssn", 0.9
            else:
                return False, "", 0.0
                
        mock_detector.is_pii_field.side_effect = mock_is_pii_field
        
        # Configure the mock to return pattern info
        def mock_get_pattern_info(pattern_name):
            patterns = {
                "full_name": {"category": "direct_identifier"},
                "email": {"category": "contact"},
                "phone_number": {"category": "contact"},
                "ssn": {"category": "government_id"}
            }
            return patterns.get(pattern_name)
            
        mock_detector.get_pattern_info.side_effect = mock_get_pattern_info
        
        # Create initial field categories
        field_categories = {
            "customer_id": [FieldCategory.DIRECT_IDENTIFIER]
        }
        
        # Create the enforcer
        enforcer = PolicyEnforcer(
            pii_detector=mock_detector,
            field_categories=field_categories
        )
        
        # Test categorizing fields
        fields = ["name", "email", "phone", "ssn", "customer_id", "product"]
        categories = enforcer.categorize_fields(fields)
        
        # Check the results
        assert "name" in categories
        assert FieldCategory.DIRECT_IDENTIFIER in categories["name"]
        
        assert "email" in categories
        assert FieldCategory.CONTACT in categories["email"]
        
        assert "phone" in categories
        assert FieldCategory.CONTACT in categories["phone"]
        
        assert "ssn" in categories
        assert FieldCategory.GOVERNMENT_ID in categories["ssn"]
        
        assert "customer_id" in categories
        assert FieldCategory.DIRECT_IDENTIFIER in categories["customer_id"]
        
        assert "product" in categories
        assert categories["product"] == []
    
    def test_add_field_category(self):
        """Test adding a field category."""
        enforcer = PolicyEnforcer()
        
        # Add a category
        enforcer.add_field_category("test_field", FieldCategory.SENSITIVE)
        
        # Verify the category was added
        assert "test_field" in enforcer.field_categories
        assert FieldCategory.SENSITIVE in enforcer.field_categories["test_field"]
        
        # Add another category to the same field
        enforcer.add_field_category("test_field", FieldCategory.FINANCIAL)
        
        # Verify both categories are present
        assert len(enforcer.field_categories["test_field"]) == 2
        assert FieldCategory.SENSITIVE in enforcer.field_categories["test_field"]
        assert FieldCategory.FINANCIAL in enforcer.field_categories["test_field"]
        
        # Adding the same category again should not duplicate it
        enforcer.add_field_category("test_field", FieldCategory.SENSITIVE)
        
        # Verify no duplication
        assert len(enforcer.field_categories["test_field"]) == 2
    
    def test_add_policy(self):
        """Test adding a policy to the enforcer."""
        enforcer = PolicyEnforcer()
        
        # Create a policy
        policy = DataPolicy(
            id="test_policy",
            name="Test Policy",
            description="Test policy description",
            policy_type=PolicyType.FIELD_ACCESS,
            action=PolicyAction.DENY
        )
        
        # Add the policy
        enforcer.add_policy(policy)
        
        # Verify the policy was added
        assert len(enforcer.policies.policies) == 1
        assert enforcer.policies.get_policy("test_policy") is not None
    
    def test_load_policies(self):
        """Test loading a complete policy set."""
        enforcer = PolicyEnforcer()
        
        # Create a policy set
        policies = [
            DataPolicy(
                id="policy1",
                name="Policy 1",
                description="Test policy 1",
                policy_type=PolicyType.FIELD_ACCESS,
                action=PolicyAction.DENY
            ),
            DataPolicy(
                id="policy2",
                name="Policy 2",
                description="Test policy 2",
                policy_type=PolicyType.DATA_COMBINATION,
                action=PolicyAction.ANONYMIZE
            )
        ]
        
        policy_set = PolicySet(
            name="Test Policy Set",
            description="Test policy set description",
            policies=policies
        )
        
        # Load the policies
        enforcer.load_policies(policy_set)
        
        # Verify the policies were loaded
        assert enforcer.policies == policy_set
        assert len(enforcer.policies.policies) == 2
        assert enforcer.policies.get_policy("policy1") is not None
        assert enforcer.policies.get_policy("policy2") is not None