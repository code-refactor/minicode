"""Privacy-focused query engine for executing queries with privacy safeguards."""

import re
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd

# Common imports
from common.core.query_engine import BaseQueryEngine, QueryEngineConfig, DataSourceManager
from common.core.base_models import QueryResult, QueryStatus, ExecutionContext, DataSourceConfig, BaseQuery
from common.core.exceptions import QueryEngineError

# Privacy-specific imports
from privacy_query_interpreter.access_logging.logger import (
    AccessLogger, AccessOutcome, AccessType
)
from privacy_query_interpreter.anonymization.anonymizer import (
    DataAnonymizer, AnonymizationMethod
)
from privacy_query_interpreter.data_minimization.minimizer import (
    DataMinimizer, Purpose
)
from privacy_query_interpreter.pii_detection.detector import (
    PIIDetector, PIIMatch
)
from privacy_query_interpreter.policy_enforcement.enforcer import (
    PolicyEnforcer
)
from privacy_query_interpreter.policy_enforcement.policy import (
    PolicyAction
)


class PrivacyQueryEngine(BaseQueryEngine):
    """
    Execute and manage SQL queries with privacy controls.
    
    This class integrates all privacy components to execute queries with
    privacy safeguards, including policy enforcement, data minimization,
    access logging, and anonymization.
    """
    
    def __init__(
        self,
        parser: Optional["PrivacyQueryParser"] = None,
        data_source_manager: Optional[DataSourceManager] = None,
        config: Optional[QueryEngineConfig] = None,
        access_logger: Optional[AccessLogger] = None,
        policy_enforcer: Optional[PolicyEnforcer] = None,
        data_minimizer: Optional[DataMinimizer] = None,
        data_anonymizer: Optional[DataAnonymizer] = None,
        pii_detector: Optional[PIIDetector] = None,
        data_sources: Optional[Dict[str, pd.DataFrame]] = None
    ):
        """
        Initialize the privacy query engine.
        
        Args:
            parser: Privacy query parser instance
            data_source_manager: Data source manager (created if not provided)
            config: Engine configuration (default created if not provided)
            access_logger: Logger for recording access
            policy_enforcer: Enforcer for data access policies
            data_minimizer: Minimizer for data minimization
            data_anonymizer: Anonymizer for sensitive data
            pii_detector: Detector for identifying PII
            data_sources: Dictionary mapping table names to DataFrames
        """
        # Initialize with common base
        if parser is None:
            from privacy_query_interpreter.query_engine.parser import PrivacyQueryParser
            parser = PrivacyQueryParser()
        
        super().__init__(parser, data_source_manager, config)
        
        # Privacy-specific services
        self.access_logger = access_logger
        self.policy_enforcer = policy_enforcer
        self.data_minimizer = data_minimizer
        self.data_anonymizer = data_anonymizer
        self.pii_detector = pii_detector
        
        # Legacy data sources support
        self.data_sources = data_sources or {}
        for name, df in self.data_sources.items():
            # Register DataFrames as data sources in the base class
            df_config = DataSourceConfig(
                name=name,
                source_type="dataframe",
                connection_params={"type": "pandas_dataframe"}
            )
            self.data_source_manager.register_data_source(df_config, df)
        
        # Privacy extension modifications
        from privacy_query_interpreter.query_engine.parser import PrivacyFunction
        self.anonymization_extensions = {
            func.value: self._handle_anonymize_function
            for func in [
                PrivacyFunction.ANONYMIZE,
                PrivacyFunction.PSEUDONYMIZE,
                PrivacyFunction.MASK,
                PrivacyFunction.REDACT,
                PrivacyFunction.GENERALIZE,
                PrivacyFunction.PERTURB,
                PrivacyFunction.TOKENIZE,
                PrivacyFunction.DIFFERENTIAL
            ]
        }
    
    def execute_query(
        self,
        query: Union[str, BaseQuery],
        user_context: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute a SQL query with privacy controls.

        Args:
            query: SQL query string or structured query object
            user_context: User context (user_id, roles, purpose, etc.)

        Returns:
            Query result with metadata
            
        Raises:
            QueryEngineError: If query execution fails
        """
        if user_context is None:
            user_context = {}
            
        # Convert query to string if it's a BaseQuery object
        query_string = query if isinstance(query, str) else str(query)
        
        # Generate query ID and execution context
        query_id = self.generate_query_id()
        execution_context = self.create_execution_context(query_id, user_context)
        
        try:
            # Execute pre-hooks
            parsed_query = self.parse_query(query_string)
            self.execute_pre_hooks(execution_context, parsed_query)
            
            # Check access permissions
            is_allowed, reason = self.validate_query_access(parsed_query, user_context)
            if not is_allowed:
                result = self._create_denied_query_result(query_id, query_string, user_context, reason, 0.0)
                self.execute_error_hooks(execution_context, QueryEngineError(reason))
                return result
            
            # Execute the actual query logic (use legacy implementation for now)
            result_dict = self._execute_privacy_query_legacy(query_string, user_context, query_id)
            
            # Convert to QueryResult format
            result = self._convert_to_query_result(result_dict)
            
            # Execute post-hooks
            self.execute_post_hooks(execution_context, result)
            
            # Log the query execution
            execution_time = result_dict.get("execution_time_ms", 0) / 1000.0
            status = QueryStatus(result_dict.get("status", QueryStatus.COMPLETED.value))
            error = result_dict.get("error")
            
            self.log_query_execution(
                query_id, query_string, execution_time, status, user_context, error
            )
            
            return result
            
        except Exception as e:
            # Handle any errors during query execution
            error_result = self._create_error_query_result(query_id, query_string, user_context, str(e), 0.0)
            self.execute_error_hooks(execution_context, e)
            return error_result
    
    def validate_query_access(
        self,
        parsed_query: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate if a user has access to execute a query.
        
        Args:
            parsed_query: Parsed query structure
            user_context: User context for access validation
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        # Privacy-specific access validation
        if self.policy_enforcer:
            tables = parsed_query.get("tables", [])
            fields = [f.get("name", "") for f in parsed_query.get("selected_fields", [])]
            joins = self.parser.extract_table_relationships(parsed_query.get("raw_query", ""))
            
            is_allowed, action, policy, reason = self.policy_enforcer.enforce_query(
                query_text=parsed_query.get("raw_query", ""),
                fields=fields,
                data_sources=tables,
                joins=joins,
                user_context=user_context
            )
            
            if not is_allowed and action == PolicyAction.DENY:
                return False, reason
        
        # Check data source access
        tables = parsed_query.get("tables", [])
        for table in tables:
            if not self.data_source_manager.validate_data_source_access(table, user_context):
                return False, f"Access denied to table: {table}"
        
        return True, None
    
    def _execute_privacy_query_legacy(
        self,
        query: str,
        user_context: Dict[str, Any],
        query_id: str
    ) -> Dict[str, Any]:
        """Execute the privacy-specific query logic (legacy implementation)."""
        # Import the legacy implementation 
        from privacy_query_interpreter.query_engine.engine import PrivacyQueryEngine as LegacyEngine
        
        # Create a temporary legacy engine instance
        legacy_engine = LegacyEngine(
            access_logger=self.access_logger,
            policy_enforcer=self.policy_enforcer,
            data_minimizer=self.data_minimizer,
            data_anonymizer=self.data_anonymizer,
            pii_detector=self.pii_detector,
            data_sources=self.data_sources
        )
        
        # Execute using legacy implementation
        return legacy_engine.execute_query(query, user_context)
    
    def _convert_to_query_result(self, result_dict: Dict[str, Any]) -> QueryResult:
        """Convert legacy result dictionary to QueryResult object."""
        status_str = result_dict.get("status", QueryStatus.COMPLETED.value)
        status = QueryStatus(status_str) if isinstance(status_str, str) else status_str
        
        # Extract document IDs from data if available
        document_ids = []
        if "data" in result_dict and isinstance(result_dict["data"], list):
            document_ids = [str(i) for i in range(len(result_dict["data"]))]
        
        return QueryResult(
            query_id=result_dict.get("query_id", ""),
            document_ids=document_ids,
            total_hits=result_dict.get("row_count", 0),
            status=status,
            execution_time=result_dict.get("execution_time_ms", 0) / 1000.0,
            minimized=result_dict.get("minimized"),
            anonymized=result_dict.get("anonymized"),
            privacy_reason=result_dict.get("privacy_reason"),
            error=result_dict.get("error"),
            reason=result_dict.get("reason")
        )
    
    def _create_denied_query_result(
        self,
        query_id: str,
        query: str,
        user_context: Dict[str, Any],
        reason: str,
        execution_time: float
    ) -> QueryResult:
        """Create a denied query result."""
        return QueryResult(
            query_id=query_id,
            document_ids=[],
            total_hits=0,
            status=QueryStatus.DENIED,
            execution_time=execution_time,
            reason=reason
        )
    
    def _create_error_query_result(
        self,
        query_id: str,
        query: str,
        user_context: Dict[str, Any],
        error: str,
        execution_time: float
    ) -> QueryResult:
        """Create an error query result."""
        return QueryResult(
            query_id=query_id,
            document_ids=[],
            total_hits=0,
            status=QueryStatus.FAILED,
            execution_time=execution_time,
            error=error
        )
    
    def _handle_anonymize_function(
        self,
        df: pd.DataFrame,
        field_name: str,
        args: Dict[str, Any]
    ) -> pd.DataFrame:
        """Handle ANONYMIZE function."""
        if not self.data_anonymizer:
            return df
            
        # Determine method to use
        method = AnonymizationMethod.HASH
        if "method" in args:
            method_name = args["method"].upper()
            try:
                method = AnonymizationMethod(method_name)
            except ValueError:
                # Use default method
                pass
                
        # Apply anonymization
        result = df.copy()
        result[field_name] = result[field_name].apply(
            lambda x: self.data_anonymizer.anonymize_value(x, method, field_name=field_name, **args)
        )
        
        return result
    
    # Legacy support methods for backward compatibility
    def execute_legacy_query(self, query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a query using the legacy interface for backward compatibility."""
        result = self.execute_query(query, user_context)
        
        # Convert QueryResult back to legacy format
        return {
            "query_id": result.query_id,
            "status": result.status.value,
            "execution_time_ms": int(result.execution_time * 1000),
            "row_count": result.total_hits,
            "column_count": len(result.document_ids) if result.document_ids else 0,
            "columns": [],  # Would need to be populated from actual data
            "data": [],     # Would need to be populated from actual data
            "minimized": result.minimized or False,
            "anonymized": result.anonymized or False,
            "privacy_reason": result.privacy_reason,
            "error": result.error,
            "reason": result.reason
        }
    
    # Additional helper methods
    def add_data_source(self, name: str, df: pd.DataFrame) -> None:
        """Add a DataFrame as a data source.
        
        Args:
            name: Name of the data source
            df: DataFrame to use as a data source
        """
        self.data_sources[name] = df
        
        # Register with the common data source manager
        df_config = DataSourceConfig(
            name=name,
            source_type="dataframe",
            connection_params={"type": "pandas_dataframe"}
        )
        self.data_source_manager.register_data_source(df_config, df)
    
    def remove_data_source(self, name: str) -> bool:
        """Remove a data source.
        
        Args:
            name: Name of the data source
            
        Returns:
            True if the data source was removed
        """
        removed = False
        if name in self.data_sources:
            del self.data_sources[name]
            removed = True
        
        # Remove from common data source manager
        if self.data_source_manager.unregister_data_source(name):
            removed = True
        
        return removed
    
    def get_query_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent query history.
        
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of queries to return
            
        Returns:
            List of query history records
        """
        # Use the base class query history
        return super().get_query_history(user_id, limit)