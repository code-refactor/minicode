"""Policy definition and validation for data access controls."""

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, root_validator, validator


class PolicyType(str, Enum):
    """Types of privacy policies for different enforcement scenarios."""
    
    FIELD_ACCESS = "field_access"
    DATA_COMBINATION = "data_combination"
    PURPOSE_LIMITATION = "purpose_limitation"
    EXPORT_CONTROL = "export_control"
    QUERY_SCOPE = "query_scope"
    RETENTION = "retention"
    USER_ACCESS = "user_access"
    ANONYMIZATION = "anonymization"
    AGGREGATION = "aggregation"


class PolicyAction(str, Enum):
    """Actions to take when a policy is triggered."""
    
    ALLOW = "allow"
    DENY = "deny"
    MINIMIZE = "minimize"
    ANONYMIZE = "anonymize"
    AGGREGATE = "aggregate"
    LOG = "log"
    ALERT = "alert"


class FieldCategory(str, Enum):
    """Categories of fields for policy rules."""
    
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
    DEMOGRAPHICS = "demographics"
    BEHAVIORAL = "behavioral"
    METADATA = "metadata"


class FieldCombination(BaseModel):
    """Define prohibited or restricted field combinations."""
    
    fields: Optional[List[str]] = None
    categories: Optional[List[FieldCategory]] = None
    threshold: int = Field(default=2, description="Minimum number of fields to trigger the policy")
    
    @root_validator(skip_on_failure=True)
    def check_fields_or_categories(cls, values):
        """Ensure that either fields or categories is specified."""
        fields = values.get("fields")
        categories = values.get("categories")
        if not fields and not categories:
            raise ValueError("Either fields or categories must be specified")
        return values


class DataPolicy(BaseModel):
    """
    Define a data access policy rule.
    
    This model defines a policy for controlling access to data, including
    field access, data combinations, and purpose limitations.
    """
    
    id: str
    name: str
    description: str
    policy_type: PolicyType
    action: PolicyAction = PolicyAction.DENY
    enabled: bool = True
    
    # Field access and combination rules
    prohibited_combinations: Optional[List[FieldCombination]] = None
    restricted_fields: Optional[List[str]] = None
    restricted_categories: Optional[List[FieldCategory]] = None
    max_sensitive_fields: Optional[int] = None
    sensitive_fields: Optional[List[str]] = None
    
    # Purpose and role limitations
    required_purpose: Optional[List[str]] = None
    prohibited_purpose: Optional[List[str]] = None
    allowed_roles: Optional[List[str]] = None
    
    # Data source restrictions
    allowed_data_sources: Optional[List[str]] = None
    prohibited_data_sources: Optional[List[str]] = None
    prohibited_joins: Optional[List[Tuple[str, str]]] = None
    
    # Action parameters
    anonymization_level: Optional[str] = None
    aggregation_minimum: Optional[int] = None
    
    # Metadata
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    version: Optional[str] = None
    
    @validator("prohibited_joins", pre=True)
    def validate_prohibited_joins(cls, v):
        """Convert various input formats to a list of tuples."""
        if v is None:
            return None
            
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, tuple) and len(item) == 2:
                    result.append(item)
                elif isinstance(item, list) and len(item) == 2:
                    result.append(tuple(item))
                elif isinstance(item, dict) and "source1" in item and "source2" in item:
                    result.append((item["source1"], item["source2"]))
                else:
                    raise ValueError(f"Invalid prohibited join format: {item}")
            return result
        else:
            raise ValueError(f"prohibited_joins must be a list, got {type(v)}")
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert the policy to a dictionary."""
        return self.dict(exclude_none=True)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataPolicy":
        """Create a policy from a dictionary."""
        return cls(**data)
        
    def check_field_combination(
        self, 
        fields: List[str],
        field_categories: Optional[Dict[str, List[FieldCategory]]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a combination of fields is allowed by this policy.
        
        Args:
            fields: List of field names to check
            field_categories: Optional mapping of field names to categories
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if not self.prohibited_combinations:
            return (True, None)
            
        field_categories = field_categories or {}
        
        for combo in self.prohibited_combinations:
            # Check against explicit fields
            if combo.fields:
                overlap = set(fields) & set(combo.fields)
                if len(overlap) >= combo.threshold:
                    return (False, f"Prohibited combination of fields: {', '.join(overlap)}")
            
            # Check against field categories
            if combo.categories and field_categories:
                # Count fields that match any of the prohibited categories
                matching_fields = []
                for field in fields:
                    field_cats = field_categories.get(field, [])
                    # Convert any string values to FieldCategory enums
                    field_cats = [
                        c if isinstance(c, FieldCategory) else FieldCategory(c)
                        for c in field_cats
                    ]
                    if any(cat in combo.categories for cat in field_cats):
                        matching_fields.append(field)
                
                if len(matching_fields) >= combo.threshold:
                    return (False, f"Prohibited combination of field categories affecting: {', '.join(matching_fields)}")
        
        return (True, None)
    
    def check_sensitive_field_limit(self, fields: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Check if the number of sensitive fields exceeds the policy limit.
        
        Args:
            fields: List of field names to check
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if not self.max_sensitive_fields or not self.sensitive_fields:
            return (True, None)
            
        # Count sensitive fields
        sensitive_count = sum(1 for f in fields if f in self.sensitive_fields)
        
        if sensitive_count > self.max_sensitive_fields:
            return (
                False, 
                f"Query includes {sensitive_count} sensitive fields, "
                f"exceeding the limit of {self.max_sensitive_fields}"
            )
            
        return (True, None)
    
    def check_purpose(self, purpose: str) -> Tuple[bool, Optional[str]]:
        """
        Check if the specified purpose is allowed by this policy.
        
        Args:
            purpose: Purpose for data access
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Check required purpose
        if self.required_purpose and purpose not in self.required_purpose:
            return (
                False, 
                f"Purpose '{purpose}' is not in the list of required purposes: {', '.join(self.required_purpose)}"
            )
            
        # Check prohibited purpose
        if self.prohibited_purpose and purpose in self.prohibited_purpose:
            return (False, f"Purpose '{purpose}' is prohibited by policy")
            
        return (True, None)
    
    def check_role(self, roles: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Check if the user's roles are allowed by this policy.
        
        Args:
            roles: List of user's roles
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if not self.allowed_roles:
            return (True, None)
            
        # Check if any of the user's roles are in the allowed list
        if not any(role in self.allowed_roles for role in roles):
            return (
                False, 
                f"None of the user's roles {roles} are in the allowed list: {', '.join(self.allowed_roles)}"
            )
            
        return (True, None)
    
    def check_data_sources(self, sources: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Check if the data sources are allowed by this policy.
        
        Args:
            sources: List of data sources
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Check allowed data sources
        if self.allowed_data_sources:
            disallowed = [s for s in sources if s not in self.allowed_data_sources]
            if disallowed:
                return (
                    False, 
                    f"The following data sources are not in the allowed list: {', '.join(disallowed)}"
                )
                
        # Check prohibited data sources
        if self.prohibited_data_sources:
            prohibited = [s for s in sources if s in self.prohibited_data_sources]
            if prohibited:
                return (False, f"The following data sources are prohibited: {', '.join(prohibited)}")
                
        return (True, None)
    
    def check_joins(self, joins: List[Tuple[str, str]]) -> Tuple[bool, Optional[str]]:
        """
        Check if the data source joins are allowed by this policy.
        
        Args:
            joins: List of data source joins (source1, source2)
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if not self.prohibited_joins:
            return (True, None)
            
        # Check each join against prohibited joins
        for join in joins:
            source1, source2 = join
            # Check both directions since order might not matter
            if (source1, source2) in self.prohibited_joins or (source2, source1) in self.prohibited_joins:
                return (False, f"Join between {source1} and {source2} is prohibited")
                
        return (True, None)


class PolicySet(BaseModel):
    """Collection of policies with metadata."""
    
    name: str
    description: Optional[str] = None
    policies: List[DataPolicy]
    version: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the policy set to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "policies": [p.to_dict() for p in self.policies],
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicySet":
        """Create a policy set from a dictionary."""
        # Convert policy dictionaries to DataPolicy objects
        if "policies" in data:
            data["policies"] = [DataPolicy.from_dict(p) for p in data["policies"]]
        return cls(**data)
        
    def get_policy(self, policy_id: str) -> Optional[DataPolicy]:
        """Get a policy by ID."""
        for policy in self.policies:
            if policy.id == policy_id:
                return policy
        return None
        
    def add_policy(self, policy: DataPolicy) -> None:
        """Add a policy to the set."""
        # Check if a policy with this ID already exists
        existing = self.get_policy(policy.id)
        if existing:
            # Replace existing policy
            self.policies = [p for p in self.policies if p.id != policy.id]
        
        self.policies.append(policy)
        
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy from the set."""
        original_count = len(self.policies)
        self.policies = [p for p in self.policies if p.id != policy_id]
        return len(self.policies) < original_count
        
    def get_policies_by_type(self, policy_type: Union[PolicyType, str]) -> List[DataPolicy]:
        """Get all policies of a specific type."""
        if isinstance(policy_type, str):
            policy_type = PolicyType(policy_type)
            
        return [p for p in self.policies if p.policy_type == policy_type]