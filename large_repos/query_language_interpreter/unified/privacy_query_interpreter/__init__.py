"""Privacy-Focused Query Language Interpreter."""

__version__ = "0.1.0"

# Import core components with common base classes
from privacy_query_interpreter.query_engine.engine import PrivacyQueryEngine
from privacy_query_interpreter.query_engine.parser import QueryParser, PrivacyQueryParser
from privacy_query_interpreter.pii_detection.detector import PIIDetector
from privacy_query_interpreter.anonymization.anonymizer import DataAnonymizer
from privacy_query_interpreter.policy_enforcement.enforcer import PolicyEnforcer
from privacy_query_interpreter.access_logging.logger import AccessLogger

# Import service registry and management
from privacy_query_interpreter.service_registry import (
    PrivacyServiceRegistry,
    get_privacy_registry
)

# Import policy and pattern definitions
from privacy_query_interpreter.policy_enforcement.policy import (
    DataPolicy, PolicySet, PolicyAction, PolicyType, FieldCategory
)
from privacy_query_interpreter.pii_detection.patterns import (
    PIICategory, PIIPattern, PII_PATTERNS
)
from privacy_query_interpreter.anonymization.anonymizer import AnonymizationMethod

# Import common utilities that privacy components now use
from common.core.base_models import QueryResult, QueryStatus, ExecutionContext
from common.services.base_services import ServiceConfig
from common.utils.validation import QueryValidator
from common.utils.logging import get_logger

__all__ = [
    # Core privacy components
    "PrivacyQueryEngine",
    "QueryParser", 
    "PrivacyQueryParser",
    "PIIDetector",
    "DataAnonymizer", 
    "PolicyEnforcer",
    "AccessLogger",
    
    # Service management
    "PrivacyServiceRegistry",
    "get_privacy_registry",
    
    # Policy and pattern definitions
    "DataPolicy",
    "PolicySet", 
    "PolicyAction",
    "PolicyType",
    "FieldCategory",
    "PIICategory",
    "PIIPattern",
    "PII_PATTERNS",
    "AnonymizationMethod",
    
    # Common models and utilities
    "QueryResult",
    "QueryStatus", 
    "ExecutionContext",
    "ServiceConfig",
    "QueryValidator",
    "get_logger",
]
