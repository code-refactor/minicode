"""Core interpreter for the legal discovery query language."""

import uuid
import time
import logging
from typing import Dict, List, Optional, Any, Union, Set, Callable
from datetime import datetime

# Common library imports
from common.core.query_engine import BaseQueryEngine, QueryEngineConfig
from common.core.base_models import (
    BaseQuery,
    QueryResult as CommonQueryResult,
    ExecutionContext,
    QueryStatus
)
from common.core.exceptions import QueryEngineError
from common.services.base_services import ServiceConfig
from common.utils.validation import validate_config
from common.utils.logging import get_logger

# Legal-specific imports
from .query import (
    LegalDiscoveryQuery, 
    QueryResult, 
    QueryClause,
    FullTextQuery,
    MetadataQuery,
    ProximityQuery,
    CommunicationQuery,
    TemporalQuery,
    PrivilegeQuery,
    CompositeQuery
)
from .document import DocumentCollection, Document


from pydantic import Field

class LegalExecutionContext(ExecutionContext):
    """Extended execution context for legal discovery queries."""
    
    # Legal-specific fields
    document_collection: Optional[Any] = Field(None, description="Collection of documents to search")
    expand_terms_func: Optional[Callable] = Field(None, description="Function for term expansion")
    calculate_proximity_func: Optional[Callable] = Field(None, description="Function for proximity calculation")
    analyze_communication_func: Optional[Callable] = Field(None, description="Function for communication analysis")
    resolve_timeframe_func: Optional[Callable] = Field(None, description="Function for timeframe resolution")
    detect_privilege_func: Optional[Callable] = Field(None, description="Function for privilege detection")
    privilege_status: Dict[str, str] = Field(default_factory=dict, description="Document privilege status")
    highlighting: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="Query highlighting")
    
    def __init__(
        self,
        document_collection: DocumentCollection,
        query_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None,
        expand_terms_func: Optional[Callable] = None,
        calculate_proximity_func: Optional[Callable] = None,
        analyze_communication_func: Optional[Callable] = None,
        resolve_timeframe_func: Optional[Callable] = None,
        detect_privilege_func: Optional[Callable] = None,
    ):
        """Initialize the legal execution context.
        
        Args:
            document_collection: Collection of documents to search
            query_id: Unique identifier for the query (generated if not provided)
            user_id: ID of the user executing the query
            user_context: User context information
            expand_terms_func: Function for expanding terms using legal ontology
            calculate_proximity_func: Function for calculating proximity between terms
            analyze_communication_func: Function for analyzing communication patterns
            resolve_timeframe_func: Function for resolving legal timeframes
            detect_privilege_func: Function for detecting privileged content
        """
        # Generate query_id if not provided
        if query_id is None:
            import uuid
            query_id = str(uuid.uuid4())
            
        super().__init__(
            query_id=query_id,
            user_id=user_id,
            user_context=user_context or {},
            document_collection=document_collection,
            expand_terms_func=expand_terms_func,
            calculate_proximity_func=calculate_proximity_func,
            analyze_communication_func=analyze_communication_func,
            resolve_timeframe_func=resolve_timeframe_func,
            detect_privilege_func=detect_privilege_func
        )


# Backward compatibility alias
QueryExecutionContext = LegalExecutionContext


class LegalQueryEngine(BaseQueryEngine):
    """Query engine for legal discovery that extends the common BaseQueryEngine."""
    
    def __init__(
        self,
        document_collection: DocumentCollection,
        ontology_service=None,
        document_analyzer=None,
        communication_analyzer=None,
        temporal_manager=None,
        privilege_detector=None,
        parser=None,
        config: Optional[QueryEngineConfig] = None
    ):
        """Initialize the legal query engine.
        
        Args:
            document_collection: Collection of documents to search
            ontology_service: Service for legal term ontology integration
            document_analyzer: Service for document analysis
            communication_analyzer: Service for communication pattern analysis
            temporal_manager: Service for temporal management
            privilege_detector: Service for privilege detection
            parser: Query parser instance
            config: Engine configuration
        """
        # Initialize the base query engine
        super().__init__(
            parser=parser,
            config=config or QueryEngineConfig(
                max_results=10000,
                enable_query_logging=True,
                enable_performance_monitoring=True
            )
        )
        
        # Legal-specific components
        self.document_collection = document_collection
        self.ontology_service = ontology_service
        self.document_analyzer = document_analyzer
        self.communication_analyzer = communication_analyzer
        self.temporal_manager = temporal_manager
        self.privilege_detector = privilege_detector
        self.logger = get_logger(__name__)
    
    def parse_query(self, query_string: str) -> LegalDiscoveryQuery:
        """Parse a query string into a structured query.
        
        Args:
            query_string: Query string in the legal discovery query language
            
        Returns:
            Structured query object
            
        Raises:
            ValueError: If the query string is invalid
        """
        # This is a placeholder for the actual parsing logic
        # In a real implementation, this would parse the SQL-like query language
        
        self.logger.info(f"Parsing query: {query_string}")
        
        # For simplicity, we'll create a basic query
        query_id = str(uuid.uuid4())
        
        # This is just an example and would be replaced with actual parsing logic
        if "CONTAINS" in query_string.upper():
            # Extract terms from a CONTAINS expression
            start_idx = query_string.upper().find("CONTAINS") + 9
            end_idx = query_string.find(")", start_idx)
            if end_idx == -1:
                end_idx = len(query_string)
            
            contents = query_string[start_idx:end_idx].strip()
            if contents.startswith("("):
                contents = contents[1:]
            
            parts = contents.split(",")
            field = parts[0].strip() if len(parts) > 1 else "content"
            terms = [term.strip().strip("'\"") for term in parts[1:]]
            
            clauses = [
                FullTextQuery(
                    terms=terms,
                    field=field,
                    expand_terms=True
                )
            ]
        elif "NEAR" in query_string.upper():
            # Extract terms from a NEAR expression
            start_idx = query_string.upper().find("NEAR") + 5
            end_idx = query_string.find(")", start_idx)
            if end_idx == -1:
                end_idx = len(query_string)
            
            contents = query_string[start_idx:end_idx].strip()
            if contents.startswith("("):
                contents = contents[1:]
            
            parts = contents.split(",")
            terms = [term.strip().strip("'\"") for term in parts[0:2]]
            distance = int(parts[2].strip()) if len(parts) > 2 else 10
            unit = parts[3].strip().strip("'\"") if len(parts) > 3 else "WORDS"
            
            clauses = [
                ProximityQuery(
                    terms=terms,
                    distance=distance,
                    unit=unit,
                    expand_terms=True
                )
            ]
        else:
            # Default to a simple full text query
            clauses = [
                FullTextQuery(
                    terms=[query_string.strip()],
                    expand_terms=True
                )
            ]
        
        return LegalDiscoveryQuery(
            query_id=query_id,
            clauses=clauses,
            expand_terms=True
        )
    
    def execute_query(
        self,
        query: Union[str, BaseQuery, LegalDiscoveryQuery],
        user_context: Optional[Dict[str, Any]] = None
    ) -> CommonQueryResult:
        """Execute a query and return the results.
        
        Args:
            query: Query string or structured query object
            user_context: User context for the query execution
            
        Returns:
            Query result object
            
        Raises:
            QueryEngineError: If query execution fails
        """
        start_time = time.time()
        query_id = self.generate_query_id()
        
        try:
            # Parse the query if it's a string
            if isinstance(query, str):
                parsed_query = self.parse_query_string(query)
                query = self._create_legal_query(parsed_query, query_id)
            elif isinstance(query, BaseQuery):
                # Convert BaseQuery to LegalDiscoveryQuery
                query = self._convert_to_legal_query(query)
            elif not isinstance(query, LegalDiscoveryQuery):
                raise QueryEngineError(f"Unsupported query type: {type(query)}")
            
            # Ensure query has an ID
            if not hasattr(query, 'query_id') or not query.query_id:
                query.query_id = query_id
            
            # Create execution context
            context = LegalExecutionContext(
                query_id=query.query_id,
                document_collection=self.document_collection,
                user_id=user_context.get('user_id') if user_context else None,
                user_context=user_context,
                expand_terms_func=self.ontology_service.expand_terms if self.ontology_service else None,
                calculate_proximity_func=self.document_analyzer.calculate_proximity if self.document_analyzer else None,
                analyze_communication_func=self.communication_analyzer.analyze_communication if self.communication_analyzer else None,
                resolve_timeframe_func=self.temporal_manager.resolve_timeframe if self.temporal_manager else None,
                detect_privilege_func=self.privilege_detector.detect_privilege if self.privilege_detector else None,
            )
            
            # Execute pre-hooks
            self.execute_pre_hooks(context, query.dict() if hasattr(query, 'dict') else {})
            
            self.logger.info(f"Executing legal query: {query.query_id}")
            
            # Execute each clause
            for clause in query.clauses:
                self._execute_clause(clause, context)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Create and return the result
            result = CommonQueryResult(
                query_id=query.query_id,
                document_ids=list(context.matched_documents),
                total_hits=len(context.matched_documents),
                status=QueryStatus.COMPLETED,
                relevance_scores=context.relevance_scores,
                privilege_status=context.privilege_status,
                execution_time=execution_time,
                executed_at=datetime.now()
            )
            
            # Execute post-hooks
            self.execute_post_hooks(context, result)
            
            # Log query execution
            self.log_query_execution(
                query.query_id,
                str(query),
                execution_time,
                QueryStatus.COMPLETED,
                user_context
            )
            
            # Record performance metrics
            self.record_performance_metric("execution_time", execution_time)
            self.record_performance_metric("total_hits", result.total_hits)
            
            self.logger.info(f"Legal query {query.query_id} executed in {execution_time:.2f}s with {result.total_hits} hits")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Create error context if not already created
            if 'context' not in locals():
                context = LegalExecutionContext(
                    query_id=query_id,
                    document_collection=self.document_collection,
                    user_context=user_context
                )
            
            # Execute error hooks
            self.execute_error_hooks(context, e)
            
            # Log failed query
            self.log_query_execution(
                query_id,
                str(query) if isinstance(query, (LegalDiscoveryQuery, BaseQuery)) else query,
                execution_time,
                QueryStatus.FAILED,
                user_context,
                error=str(e)
            )
            
            self.logger.error(f"Legal query {query_id} failed: {str(e)}")
            
            raise QueryEngineError(f"Legal query execution failed: {str(e)}")
    
    def _execute_clause(self, clause: QueryClause, context: LegalExecutionContext) -> None:
        """Execute a single query clause.
        
        Args:
            clause: Query clause to execute
            context: Query execution context
        """
        if isinstance(clause, FullTextQuery):
            self._execute_full_text_query(clause, context)
        elif isinstance(clause, MetadataQuery):
            self._execute_metadata_query(clause, context)
        elif isinstance(clause, ProximityQuery):
            self._execute_proximity_query(clause, context)
        elif isinstance(clause, CommunicationQuery):
            self._execute_communication_query(clause, context)
        elif isinstance(clause, TemporalQuery):
            self._execute_temporal_query(clause, context)
        elif isinstance(clause, PrivilegeQuery):
            self._execute_privilege_query(clause, context)
        elif isinstance(clause, CompositeQuery):
            self._execute_composite_query(clause, context)
        else:
            self.logger.warning(f"Unknown query clause type: {type(clause)}")
    
    def _execute_full_text_query(self, clause: FullTextQuery, context: LegalExecutionContext) -> None:
        """Execute a full text query clause.
        
        Args:
            clause: Full text query clause
            context: Query execution context
        """
        self.logger.debug(f"Executing full text query: {clause}")
        
        # Expand terms if requested and available
        terms = clause.terms
        if clause.expand_terms and context.expand_terms_func:
            expanded_terms = []
            for term in terms:
                expanded = context.expand_terms_func(term)
                expanded_terms.extend(expanded)
            terms = expanded_terms
        
        # Search for documents containing the terms
        matched_docs = set()
        for doc_id, document in context.document_collection.documents.items():
            # Check if the document contains all/any terms
            content = document.content.lower()
            
            if clause.operator.value == "AND":
                if all(term.lower() in content for term in terms):
                    matched_docs.add(doc_id)
            elif clause.operator.value == "OR":
                if any(term.lower() in content for term in terms):
                    matched_docs.add(doc_id)
            elif clause.operator.value == "NOT":
                if not any(term.lower() in content for term in terms):
                    matched_docs.add(doc_id)
        
        # Update the matched documents in the context
        context.matched_documents.update(matched_docs)
        
        # Calculate relevance scores (simplified)
        for doc_id in matched_docs:
            document = context.document_collection.documents[doc_id]
            content = document.content.lower()
            
            # Simple TF scoring
            score = sum(content.count(term.lower()) for term in terms)
            # Apply the boost
            score *= clause.boost
            
            # Update or set the relevance score
            if doc_id in context.relevance_scores:
                context.relevance_scores[doc_id] += score
            else:
                context.relevance_scores[doc_id] = score
    
    def _execute_metadata_query(self, clause: MetadataQuery, context: LegalExecutionContext) -> None:
        """Execute a metadata query clause.
        
        Args:
            clause: Metadata query clause
            context: Query execution context
        """
        self.logger.debug(f"Executing metadata query: {clause}")
        
        # Search for documents with matching metadata
        matched_docs = set()
        for doc_id, document in context.document_collection.documents.items():
            # Get the metadata value, defaulting to None if not present
            metadata_value = getattr(document.metadata, clause.field, None)
            if metadata_value is None:
                continue
            
            # Compare the value based on the operator
            if clause.operator.value == "EQUALS" and metadata_value == clause.value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "CONTAINS" and isinstance(metadata_value, str) and clause.value in metadata_value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "GREATER_THAN" and metadata_value > clause.value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "LESS_THAN" and metadata_value < clause.value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "GREATER_THAN_EQUALS" and metadata_value >= clause.value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "LESS_THAN_EQUALS" and metadata_value <= clause.value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "IN" and metadata_value in clause.value:
                matched_docs.add(doc_id)
        
        # Update the matched documents in the context
        context.matched_documents.update(matched_docs)
    
    def _execute_proximity_query(self, clause: ProximityQuery, context: LegalExecutionContext) -> None:
        """Execute a proximity query clause.
        
        Args:
            clause: Proximity query clause
            context: Query execution context
        """
        self.logger.debug(f"Executing proximity query: {clause}")
        
        # If a proximity calculation function is available, use it
        if context.calculate_proximity_func:
            matched_docs = set()
            for doc_id, document in context.document_collection.documents.items():
                # Check if terms are within the specified distance
                if context.calculate_proximity_func(
                    document.content,
                    clause.terms,
                    clause.distance,
                    clause.unit.value,
                    clause.ordered
                ):
                    matched_docs.add(doc_id)
            
            # Update the matched documents in the context
            context.matched_documents.update(matched_docs)
        else:
            # Fallback to a simplified implementation
            self._execute_full_text_query(
                FullTextQuery(
                    terms=clause.terms,
                    expand_terms=clause.expand_terms
                ),
                context
            )
    
    def _execute_communication_query(self, clause: CommunicationQuery, context: LegalExecutionContext) -> None:
        """Execute a communication query clause.
        
        Args:
            clause: Communication query clause
            context: Query execution context
        """
        self.logger.debug(f"Executing communication query: {clause}")
        
        # If a communication analysis function is available, use it
        if context.analyze_communication_func and hasattr(self.communication_analyzer, "find_communications"):
            matched_docs = set(
                self.communication_analyzer.find_communications(
                    clause.participants,
                    direction=clause.direction,
                    date_range=clause.date_range,
                    analyze_threads=clause.thread_analysis,
                    include_cc=clause.include_cc,
                    include_bcc=clause.include_bcc
                )
            )
            
            # Update the matched documents in the context
            context.matched_documents.update(matched_docs)
        else:
            # Fallback to a simplified implementation
            matched_docs = set()
            for doc_id, document in context.document_collection.documents.items():
                # Only consider email documents
                if not hasattr(document, "sender") or not hasattr(document, "recipients"):
                    continue
                
                # Check if any participant is in the sender or recipients
                participants = set(clause.participants)
                doc_participants = {document.sender}
                doc_participants.update(document.recipients)
                
                if clause.include_cc and hasattr(document, "cc") and document.cc:
                    doc_participants.update(document.cc)
                
                if clause.include_bcc and hasattr(document, "bcc") and document.bcc:
                    doc_participants.update(document.bcc)
                
                # Check if there's any overlap between participants
                if participants.intersection(doc_participants):
                    matched_docs.add(doc_id)
            
            # Update the matched documents in the context
            context.matched_documents.update(matched_docs)
    
    def _execute_temporal_query(self, clause: TemporalQuery, context: LegalExecutionContext) -> None:
        """Execute a temporal query clause.
        
        Args:
            clause: Temporal query clause
            context: Query execution context
        """
        self.logger.debug(f"Executing temporal query: {clause}")
        
        # If a timeframe resolution function is available and the value is a timeframe, use it
        if isinstance(clause.value, dict) and context.resolve_timeframe_func:
            timeframe_date = context.resolve_timeframe_func(
                clause.timeframe_type,
                jurisdiction=clause.jurisdiction
            )
            value = timeframe_date
        else:
            value = clause.value
        
        # Search for documents with matching date
        matched_docs = set()
        for doc_id, document in context.document_collection.documents.items():
            # Get the date value from the document
            date_value = None
            if clause.date_field == "date_created" and hasattr(document.metadata, "date_created"):
                date_value = document.metadata.date_created
            elif clause.date_field == "date_modified" and hasattr(document.metadata, "date_modified"):
                date_value = document.metadata.date_modified
            elif hasattr(document.metadata, clause.date_field):
                date_value = getattr(document.metadata, clause.date_field)
            
            if date_value is None:
                continue
            
            # Compare the date based on the operator
            if clause.operator.value == "EQUALS" and date_value == value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "GREATER_THAN" and date_value > value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "LESS_THAN" and date_value < value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "GREATER_THAN_EQUALS" and date_value >= value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "LESS_THAN_EQUALS" and date_value <= value:
                matched_docs.add(doc_id)
            elif clause.operator.value == "BETWEEN" and isinstance(value, dict) and "start" in value and "end" in value:
                if value["start"] <= date_value <= value["end"]:
                    matched_docs.add(doc_id)
        
        # Update the matched documents in the context
        context.matched_documents.update(matched_docs)
    
    def _execute_privilege_query(self, clause: PrivilegeQuery, context: LegalExecutionContext) -> None:
        """Execute a privilege query clause.
        
        Args:
            clause: Privilege query clause
            context: Query execution context
        """
        self.logger.debug(f"Executing privilege query: {clause}")
        
        # If a privilege detection function is available, use it
        if context.detect_privilege_func:
            # Get the privilege status for each document
            for doc_id, document in context.document_collection.documents.items():
                privilege_info = context.detect_privilege_func(
                    document,
                    privilege_type=clause.privilege_type,
                    attorneys=clause.attorneys
                )
                
                # Update the privilege status in the context
                context.privilege_status[doc_id] = privilege_info["status"]
                
                # Add to matched documents if the confidence is above the threshold
                if privilege_info["confidence"] >= clause.threshold:
                    if clause.include_potentially_privileged:
                        context.matched_documents.add(doc_id)
                    elif privilege_info["status"] == "PRIVILEGED":
                        context.matched_documents.add(doc_id)
        else:
            # Fallback to a simplified implementation
            matched_docs = set()
            for doc_id, document in context.document_collection.documents.items():
                # Check for privilege indicators in the content
                content = document.content.lower()
                privilege_indicators = [
                    "privileged",
                    "attorney-client",
                    "attorney client",
                    "work product",
                    "legal advice",
                    "confidential"
                ]
                
                # Check if any indicator is in the content
                if any(indicator in content for indicator in privilege_indicators):
                    matched_docs.add(doc_id)
                    context.privilege_status[doc_id] = "POTENTIALLY_PRIVILEGED"
                else:
                    context.privilege_status[doc_id] = "NOT_PRIVILEGED"
            
            # Update the matched documents in the context
            if clause.include_potentially_privileged:
                context.matched_documents.update(matched_docs)
    
    def _execute_composite_query(self, clause: CompositeQuery, context: LegalExecutionContext) -> None:
        """Execute a composite query clause.
        
        Args:
            clause: Composite query clause
            context: Query execution context
        """
        self.logger.debug(f"Executing composite query: {clause}")
        
        # Create a new context for each subclause
        subcontexts = []
        for subclause in clause.clauses:
            subcontext = LegalExecutionContext(
                query_id=context.query_id,
                document_collection=context.document_collection,
                user_id=context.user_id,
                user_context=context.user_context,
                expand_terms_func=context.expand_terms_func,
                calculate_proximity_func=context.calculate_proximity_func,
                analyze_communication_func=context.analyze_communication_func,
                resolve_timeframe_func=context.resolve_timeframe_func,
                detect_privilege_func=context.detect_privilege_func,
            )
            
            # Execute the subclause
            self._execute_clause(subclause, subcontext)
            
            # Add the subcontext to the list
            subcontexts.append(subcontext)
        
        # Combine the results based on the operator
        if clause.operator.value == "AND":
            # Intersection of all matched documents
            if subcontexts:
                matched_docs = subcontexts[0].matched_documents
                for subcontext in subcontexts[1:]:
                    matched_docs.intersection_update(subcontext.matched_documents)
                
                # Update the matched documents in the context
                context.matched_documents.update(matched_docs)
        elif clause.operator.value == "OR":
            # Union of all matched documents
            for subcontext in subcontexts:
                context.matched_documents.update(subcontext.matched_documents)
        elif clause.operator.value == "NOT":
            # Documents in the first subcontext but not in any other subcontext
            if subcontexts:
                matched_docs = subcontexts[0].matched_documents
                for subcontext in subcontexts[1:]:
                    matched_docs.difference_update(subcontext.matched_documents)
                
                # Update the matched documents in the context
                context.matched_documents.update(matched_docs)
        
        # Combine relevance scores and privilege status
        for subcontext in subcontexts:
            # Merge relevance scores (summing them)
            for doc_id, score in subcontext.relevance_scores.items():
                if doc_id in context.relevance_scores:
                    context.relevance_scores[doc_id] += score
                else:
                    context.relevance_scores[doc_id] = score
            
            # Merge privilege status (prioritizing privileged status)
            for doc_id, status in subcontext.privilege_status.items():
                if doc_id not in context.privilege_status or status == "PRIVILEGED":
                    context.privilege_status[doc_id] = status
    
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
        # Legal discovery access validation logic
        user_roles = set(user_context.get('roles', []))
        
        # Basic role-based access control for legal queries
        legal_roles = {'legal_counsel', 'paralegal', 'litigation_support', 'admin'}
        
        if not user_roles.intersection(legal_roles):
            return False, "User does not have legal access roles"
        
        # Check for privilege-related queries
        if self._contains_privilege_queries(parsed_query):
            privileged_roles = {'legal_counsel', 'admin'}
            if not user_roles.intersection(privileged_roles):
                return False, "User does not have access to privilege-related queries"
        
        return True, None
    
    def parse_query_string(self, query_string: str) -> Dict[str, Any]:
        """Parse a query string into a structured format.
        
        Args:
            query_string: Query string to parse
            
        Returns:
            Parsed query structure
        """
        # This is a simplified parsing implementation
        # In a real implementation, this would use a proper SQL-like parser
        parsed = {
            'query_string': query_string,
            'clauses': [],
            'type': 'legal_discovery'
        }
        
        # Basic parsing logic (simplified)
        query_upper = query_string.upper()
        
        if "CONTAINS" in query_upper:
            # Extract the field and search term from CONTAINS(field, 'term')
            import re
            match = re.search(r'CONTAINS\s*\(\s*(\w+)\s*,\s*["\']([^"\']+)["\']\s*\)', query_string, re.IGNORECASE)
            if match:
                field = match.group(1)
                search_term = match.group(2)
                parsed['clauses'].append({
                    'type': 'full_text',
                    'operator': 'CONTAINS',
                    'field': field,
                    'value': search_term
                })
                # Convert to LegalDiscoveryQuery format
                parsed['query_type'] = 'FULL_TEXT'
                parsed['search_term'] = search_term
                parsed['field_restrictions'] = [field] if field != 'content' else None
        
        if "NEAR" in query_upper:
            # Extract terms and distance from NEAR('term1', 'term2', distance, 'unit')
            import re
            match = re.search(r'NEAR\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*,\s*(\d+)\s*,\s*["\'](\w+)["\']\s*\)', query_string, re.IGNORECASE)
            if match:
                term1 = match.group(1)
                term2 = match.group(2)
                distance = int(match.group(3))
                unit = match.group(4)
                parsed['clauses'].append({
                    'type': 'proximity',
                    'operator': 'NEAR',
                    'terms': [term1, term2],
                    'distance': distance,
                    'unit': unit
                })
                # Convert to LegalDiscoveryQuery format
                parsed['query_type'] = 'PROXIMITY'
                parsed['primary_term'] = term1
                parsed['secondary_term'] = term2
                parsed['distance'] = distance
                parsed['unit'] = unit
        
        if "PRIVILEGE" in query_upper:
            parsed['clauses'].append({
                'type': 'privilege',
                'operator': 'PRIVILEGE_CHECK'
            })
        
        return parsed
    
    def _contains_privilege_queries(self, parsed_query: Dict[str, Any]) -> bool:
        """Check if the query contains privilege-related operations.
        
        Args:
            parsed_query: Parsed query structure
            
        Returns:
            True if query contains privilege operations
        """
        if not parsed_query.get('clauses'):
            return False
        
        for clause in parsed_query['clauses']:
            if clause.get('type') == 'privilege':
                return True
        
        return False
    
    def _create_legal_query(self, parsed_query: Dict[str, Any], query_id: str) -> LegalDiscoveryQuery:
        """Create a LegalDiscoveryQuery from parsed query structure.
        
        Args:
            parsed_query: Parsed query structure
            query_id: Query identifier
            
        Returns:
            LegalDiscoveryQuery object
        """
        # This is a simplified implementation
        # Create basic clauses based on parsed structure
        clauses = []
        
        for clause_info in parsed_query.get('clauses', []):
            clause_type = clause_info.get('type')
            
            if clause_type == 'full_text':
                # Create a basic full text query
                # Use the extracted search term if available, otherwise use the value from clause
                search_term = parsed_query.get('search_term') or clause_info.get('value', '')
                if search_term:
                    clauses.append(FullTextQuery(
                        terms=[search_term],
                        expand_terms=True
                    ))
            elif clause_type == 'proximity':
                # Create a basic proximity query
                # Use extracted values from parsed query
                terms = clause_info.get('terms', [])
                if not terms and parsed_query.get('primary_term'):
                    terms = [parsed_query.get('primary_term'), parsed_query.get('secondary_term', '')]
                
                distance = clause_info.get('distance') or parsed_query.get('distance', 10)
                unit = clause_info.get('unit') or parsed_query.get('unit', 'WORDS')
                
                if terms and len(terms) >= 2:
                    clauses.append(ProximityQuery(
                        terms=terms[:2],  # Take first two terms
                        distance=distance,
                        unit=unit,
                        expand_terms=True
                    ))
            elif clause_type == 'privilege':
                # Create a basic privilege query
                clauses.append(PrivilegeQuery(
                    threshold=0.5,
                    include_potentially_privileged=True
                ))
        
        # If no clauses were created, create a default full text query
        if not clauses:
            clauses.append(FullTextQuery(
                terms=[parsed_query.get('query_string', '')],
                expand_terms=True
            ))
        
        return LegalDiscoveryQuery(
            query_id=query_id,
            clauses=clauses,
            expand_terms=True
        )
    
    def _convert_to_legal_query(self, base_query: BaseQuery) -> LegalDiscoveryQuery:
        """Convert a BaseQuery to a LegalDiscoveryQuery.
        
        Args:
            base_query: BaseQuery to convert
            
        Returns:
            LegalDiscoveryQuery object
        """
        # Convert BaseQuery clauses to legal-specific clauses
        legal_clauses = []
        
        for clause in base_query.clauses:
            # This would need more sophisticated conversion logic
            # For now, create basic full text queries
            legal_clauses.append(FullTextQuery(
                terms=["converted_query"],
                expand_terms=True
            ))
        
        return LegalDiscoveryQuery(
            query_id=base_query.query_id,
            clauses=legal_clauses,
            sort=base_query.sort,
            limit=base_query.limit,
            offset=base_query.offset,
            aggregations=base_query.aggregations,
            facets=base_query.facets,
            highlight=base_query.highlight,
            expand_terms=True
        )


# Maintain backward compatibility with the old class name
QueryInterpreter = LegalQueryEngine