"""Tests for the policy definition and validation."""

import pytest
from pydantic import ValidationError

from privacy_query_interpreter.policy_enforcement.policy import (
    PolicyType, PolicyAction, FieldCategory, FieldCombination,
    DataPolicy, PolicySet
)


class TestPolicyDefinitions:
    """Test cases for policy data models."""
    
    def test_policy_type_enum(self):
        """Test the PolicyType enum values."""
        assert PolicyType.FIELD_ACCESS == "field_access"
        assert PolicyType.DATA_COMBINATION == "data_combination"
        assert PolicyType.PURPOSE_LIMITATION == "purpose_limitation"
        assert PolicyType.EXPORT_CONTROL == "export_control"
        assert PolicyType.QUERY_SCOPE == "query_scope"
        assert PolicyType.RETENTION == "retention"
        assert PolicyType.USER_ACCESS == "user_access"
        assert PolicyType.ANONYMIZATION == "anonymization"
        assert PolicyType.AGGREGATION == "aggregation"
    
    def test_policy_action_enum(self):
        """Test the PolicyAction enum values."""
        assert PolicyAction.ALLOW == "allow"
        assert PolicyAction.DENY == "deny"
        assert PolicyAction.MINIMIZE == "minimize"
        assert PolicyAction.ANONYMIZE == "anonymize"
        assert PolicyAction.AGGREGATE == "aggregate"
        assert PolicyAction.LOG == "log"
        assert PolicyAction.ALERT == "alert"
    
    def test_field_category_enum(self):
        """Test the FieldCategory enum values."""
        assert FieldCategory.DIRECT_IDENTIFIER == "direct_identifier"
        assert FieldCategory.QUASI_IDENTIFIER == "quasi_identifier"
        assert FieldCategory.SENSITIVE == "sensitive"
        assert FieldCategory.CONTACT == "contact"
        assert FieldCategory.FINANCIAL == "financial"
        assert FieldCategory.HEALTH == "health"
        assert FieldCategory.BIOMETRIC == "biometric"
        assert FieldCategory.LOCATION == "location"
        assert FieldCategory.GOVERNMENT_ID == "government_id"
        assert FieldCategory.CREDENTIAL == "credential"
        assert FieldCategory.DEMOGRAPHICS == "demographics"
        assert FieldCategory.BEHAVIORAL == "behavioral"
        assert FieldCategory.METADATA == "metadata"
    
    def test_field_combination_validation(self):
        """Test validation of FieldCombination."""
        # Test valid combinations
        valid_combinations = [
            # Fields only
            FieldCombination(fields=["name", "ssn"]),
            # Categories only
            FieldCombination(categories=[FieldCategory.DIRECT_IDENTIFIER, FieldCategory.FINANCIAL]),
            # Both fields and categories
            FieldCombination(
                fields=["email"],
                categories=[FieldCategory.FINANCIAL],
                threshold=2
            )
        ]
        
        for combo in valid_combinations:
            assert combo is not None
            
        # Test invalid combinations
        with pytest.raises(ValidationError):
            FieldCombination()  # Neither fields nor categories
    
    def test_data_policy_creation(self):
        """Test creating a DataPolicy."""
        # Create a basic policy
        policy = DataPolicy(
            id="policy1",
            name="No Financial PII",
            description="Prevents access to financial PII",
            policy_type=PolicyType.FIELD_ACCESS,
            action=PolicyAction.DENY,
            restricted_categories=[FieldCategory.FINANCIAL],
            required_purpose=["fraud_investigation"],
            allowed_roles=["fraud_investigator", "compliance_officer"]
        )
        
        # Verify policy attributes
        assert policy.id == "policy1"
        assert policy.name == "No Financial PII"
        assert policy.description == "Prevents access to financial PII"
        assert policy.policy_type == PolicyType.FIELD_ACCESS
        assert policy.action == PolicyAction.DENY
        assert policy.restricted_categories == [FieldCategory.FINANCIAL]
        assert policy.required_purpose == ["fraud_investigation"]
        assert policy.allowed_roles == ["fraud_investigator", "compliance_officer"]
        assert policy.enabled is True  # Default value
        
        # Test with prohibited combinations
        policy_with_combinations = DataPolicy(
            id="policy2",
            name="No PII Combinations",
            description="Prevents combining sensitive data",
            policy_type=PolicyType.DATA_COMBINATION,
            action=PolicyAction.DENY,
            prohibited_combinations=[
                FieldCombination(
                    categories=[FieldCategory.DIRECT_IDENTIFIER, FieldCategory.HEALTH],
                    threshold=2
                ),
                FieldCombination(
                    fields=["ssn", "credit_card", "income"],
                    threshold=2
                )
            ],
            allowed_roles=["data_analyst"]
        )
        
        assert len(policy_with_combinations.prohibited_combinations) == 2
        assert policy_with_combinations.prohibited_combinations[0].categories == [
            FieldCategory.DIRECT_IDENTIFIER, FieldCategory.HEALTH
        ]
        assert policy_with_combinations.prohibited_combinations[0].threshold == 2
        assert policy_with_combinations.prohibited_combinations[1].fields == [
            "ssn", "credit_card", "income"
        ]
    
    def test_data_policy_to_dict(self):
        """Test converting a DataPolicy to a dictionary."""
        policy = DataPolicy(
            id="policy1",
            name="No Financial PII",
            description="Prevents access to financial PII",
            policy_type=PolicyType.FIELD_ACCESS,
            action=PolicyAction.DENY,
            restricted_categories=[FieldCategory.FINANCIAL],
            required_purpose=["fraud_investigation"],
            allowed_roles=["fraud_investigator", "compliance_officer"]
        )
        
        policy_dict = policy.to_dict()
        
        # Verify dictionary representation
        assert policy_dict["id"] == "policy1"
        assert policy_dict["name"] == "No Financial PII"
        assert policy_dict["description"] == "Prevents access to financial PII"
        assert policy_dict["policy_type"] == "field_access"
        assert policy_dict["action"] == "deny"
        assert policy_dict["restricted_categories"] == ["financial"]
        assert policy_dict["required_purpose"] == ["fraud_investigation"]
        assert policy_dict["allowed_roles"] == ["fraud_investigator", "compliance_officer"]
        assert policy_dict["enabled"] is True
    
    def test_data_policy_from_dict(self):
        """Test creating a DataPolicy from a dictionary."""
        policy_dict = {
            "id": "policy1",
            "name": "No Financial PII",
            "description": "Prevents access to financial PII",
            "policy_type": "field_access",
            "action": "deny",
            "restricted_categories": ["financial"],
            "required_purpose": ["fraud_investigation"],
            "allowed_roles": ["fraud_investigator", "compliance_officer"]
        }
        
        policy = DataPolicy.from_dict(policy_dict)
        
        # Verify policy attributes
        assert policy.id == "policy1"
        assert policy.name == "No Financial PII"
        assert policy.description == "Prevents access to financial PII"
        assert policy.policy_type == PolicyType.FIELD_ACCESS
        assert policy.action == PolicyAction.DENY
        assert policy.restricted_categories == [FieldCategory.FINANCIAL]
        assert policy.required_purpose == ["fraud_investigation"]
        assert policy.allowed_roles == ["fraud_investigator", "compliance_officer"]
    
    def test_policy_set_creation(self):
        """Test creating a PolicySet."""
        policies = [
            DataPolicy(
                id="policy1",
                name="No Financial PII",
                description="Prevents access to financial PII",
                policy_type=PolicyType.FIELD_ACCESS,
                action=PolicyAction.DENY,
                restricted_categories=[FieldCategory.FINANCIAL]
            ),
            DataPolicy(
                id="policy2",
                name="No PII Combinations",
                description="Prevents combining sensitive data",
                policy_type=PolicyType.DATA_COMBINATION,
                action=PolicyAction.DENY,
                prohibited_combinations=[
                    FieldCombination(
                        categories=[FieldCategory.DIRECT_IDENTIFIER, FieldCategory.HEALTH],
                        threshold=2
                    )
                ]
            )
        ]
        
        policy_set = PolicySet(
            name="Standard Privacy Policies",
            description="Default policies for privacy protection",
            policies=policies,
            version="1.0"
        )
        
        # Verify policy set attributes
        assert policy_set.name == "Standard Privacy Policies"
        assert policy_set.description == "Default policies for privacy protection"
        assert len(policy_set.policies) == 2
        assert policy_set.version == "1.0"
        
        # Test getting a policy by ID
        policy = policy_set.get_policy("policy1")
        assert policy is not None
        assert policy.id == "policy1"
        assert policy.name == "No Financial PII"
        
        # Test getting a non-existent policy
        policy = policy_set.get_policy("nonexistent")
        assert policy is None
    
    def test_policy_set_to_dict(self):
        """Test converting a PolicySet to a dictionary."""
        policies = [
            DataPolicy(
                id="policy1",
                name="No Financial PII",
                description="Prevents access to financial PII",
                policy_type=PolicyType.FIELD_ACCESS,
                action=PolicyAction.DENY,
                restricted_categories=[FieldCategory.FINANCIAL]
            )
        ]
        
        policy_set = PolicySet(
            name="Standard Privacy Policies",
            description="Default policies for privacy protection",
            policies=policies,
            version="1.0"
        )
        
        policy_set_dict = policy_set.to_dict()
        
        # Verify dictionary representation
        assert policy_set_dict["name"] == "Standard Privacy Policies"
        assert policy_set_dict["description"] == "Default policies for privacy protection"
        assert len(policy_set_dict["policies"]) == 1
        assert policy_set_dict["version"] == "1.0"
        assert policy_set_dict["policies"][0]["id"] == "policy1"
    
    def test_policy_set_from_dict(self):
        """Test creating a PolicySet from a dictionary."""
        policy_set_dict = {
            "name": "Standard Privacy Policies",
            "description": "Default policies for privacy protection",
            "policies": [
                {
                    "id": "policy1",
                    "name": "No Financial PII",
                    "description": "Prevents access to financial PII",
                    "policy_type": "field_access",
                    "action": "deny",
                    "restricted_categories": ["financial"]
                }
            ],
            "version": "1.0"
        }
        
        policy_set = PolicySet.from_dict(policy_set_dict)
        
        # Verify policy set attributes
        assert policy_set.name == "Standard Privacy Policies"
        assert policy_set.description == "Default policies for privacy protection"
        assert len(policy_set.policies) == 1
        assert policy_set.version == "1.0"
        assert policy_set.policies[0].id == "policy1"
        assert policy_set.policies[0].restricted_categories == [FieldCategory.FINANCIAL]
    
    def test_policy_set_add_remove(self):
        """Test adding and removing policies from a PolicySet."""
        # Create an initial policy set
        policy_set = PolicySet(
            name="Test Policies",
            description="Test policy set",
            policies=[
                DataPolicy(
                    id="policy1",
                    name="Initial Policy",
                    description="Initial test policy",
                    policy_type=PolicyType.FIELD_ACCESS,
                    action=PolicyAction.DENY
                )
            ]
        )
        
        # Add a new policy
        new_policy = DataPolicy(
            id="policy2",
            name="New Policy",
            description="New test policy",
            policy_type=PolicyType.DATA_COMBINATION,
            action=PolicyAction.ANONYMIZE
        )
        
        policy_set.add_policy(new_policy)
        
        # Verify policy was added
        assert len(policy_set.policies) == 2
        assert policy_set.get_policy("policy2") is not None
        
        # Replace an existing policy
        updated_policy = DataPolicy(
            id="policy1",
            name="Updated Policy",
            description="Updated test policy",
            policy_type=PolicyType.FIELD_ACCESS,
            action=PolicyAction.MINIMIZE
        )
        
        policy_set.add_policy(updated_policy)
        
        # Verify policy was updated
        assert len(policy_set.policies) == 2
        updated = policy_set.get_policy("policy1")
        assert updated is not None
        assert updated.name == "Updated Policy"
        assert updated.action == PolicyAction.MINIMIZE
        
        # Remove a policy
        result = policy_set.remove_policy("policy2")
        
        # Verify policy was removed
        assert result is True
        assert len(policy_set.policies) == 1
        assert policy_set.get_policy("policy2") is None
        
        # Try to remove a non-existent policy
        result = policy_set.remove_policy("nonexistent")
        
        # Verify operation result
        assert result is False
        assert len(policy_set.policies) == 1
    
    def test_policy_set_get_by_type(self):
        """Test getting policies by type from a PolicySet."""
        # Create a policy set with multiple policy types
        policies = [
            DataPolicy(
                id="policy1",
                name="Field Access Policy",
                description="Test field access policy",
                policy_type=PolicyType.FIELD_ACCESS,
                action=PolicyAction.DENY
            ),
            DataPolicy(
                id="policy2",
                name="Data Combination Policy",
                description="Test data combination policy",
                policy_type=PolicyType.DATA_COMBINATION,
                action=PolicyAction.DENY
            ),
            DataPolicy(
                id="policy3",
                name="Another Field Access Policy",
                description="Another test field access policy",
                policy_type=PolicyType.FIELD_ACCESS,
                action=PolicyAction.ANONYMIZE
            )
        ]
        
        policy_set = PolicySet(
            name="Test Policies",
            description="Test policy set",
            policies=policies
        )
        
        # Get policies by type
        field_access_policies = policy_set.get_policies_by_type(PolicyType.FIELD_ACCESS)
        
        # Verify filtering
        assert len(field_access_policies) == 2
        assert all(p.policy_type == PolicyType.FIELD_ACCESS for p in field_access_policies)
        assert any(p.id == "policy1" for p in field_access_policies)
        assert any(p.id == "policy3" for p in field_access_policies)
        
        # Test with string type
        data_combination_policies = policy_set.get_policies_by_type("data_combination")
        
        # Verify filtering
        assert len(data_combination_policies) == 1
        assert data_combination_policies[0].id == "policy2"
        
        # Test with non-existent type
        retention_policies = policy_set.get_policies_by_type(PolicyType.RETENTION)
        
        # Verify empty result
        assert len(retention_policies) == 0