"""Base query parser for the unified query language interpreter."""

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from enum import Enum

import sqlparse
from sqlparse.sql import (
    Identifier, 
    IdentifierList,
    Token, 
    TokenList,
    Function,
    Parenthesis,
    Where,
    Comparison
)
from sqlparse.tokens import Keyword, Name, Punctuation, Wildcard

from .base_models import QueryOperator, QueryClause, BaseQuery


class QueryType(str, Enum):
    """Types of queries supported by the parser."""
    
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"


class ParsedQueryComponent(object):
    """Container for a parsed query component."""
    
    def __init__(self, component_type: str, value: Any, metadata: Optional[Dict[str, Any]] = None):
        self.component_type = component_type
        self.value = value
        self.metadata = metadata or {}


class BaseQueryParser(ABC):
    """Base class for query parsers that can be extended by different implementations."""
    
    def __init__(self):
        """Initialize the base query parser."""
        self._custom_functions: Dict[str, Any] = {}
        self._custom_operators: Dict[str, QueryOperator] = {}
    
    @abstractmethod
    def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse a query string and extract relevant components.
        
        Args:
            query: The query string to parse
            
        Returns:
            Dictionary with parsed query information
            
        Raises:
            ValueError: If the query string is invalid
        """
        pass
    
    @abstractmethod
    def validate_query(self, parsed_query: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate a parsed query structure.
        
        Args:
            parsed_query: Parsed query structure
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    def register_custom_function(self, name: str, handler: Any) -> None:
        """Register a custom function for query parsing.
        
        Args:
            name: Function name
            handler: Function handler
        """
        self._custom_functions[name.upper()] = handler
    
    def register_custom_operator(self, name: str, operator: QueryOperator) -> None:
        """Register a custom operator for query parsing.
        
        Args:
            name: Operator name
            operator: QueryOperator enum value
        """
        self._custom_operators[name.upper()] = operator
    
    def _clean_identifier(self, identifier: Union[str, Identifier]) -> str:
        """Clean an identifier name, removing quotes and aliases.
        
        Args:
            identifier: The identifier to clean
            
        Returns:
            Cleaned identifier string
        """
        if hasattr(identifier, "get_real_name"):
            return identifier.get_real_name()
        return str(identifier).strip('`"[]\'')
    
    def _extract_quoted_string(self, value: str) -> str:
        """Extract content from a quoted string.
        
        Args:
            value: String that may be quoted
            
        Returns:
            String with quotes removed
        """
        value = value.strip()
        if (value.startswith("'") and value.endswith("'")) or \
           (value.startswith('"') and value.endswith('"')):
            return value[1:-1]
        return value


class SQLQueryParser(BaseQueryParser):
    """SQL query parser implementation with extensions support."""
    
    def __init__(self):
        """Initialize the SQL query parser."""
        super().__init__()
        
        # Standard SQL operators mapping
        self._operator_mapping = {
            "=": QueryOperator.EQUALS,
            "!=": QueryOperator.NOT,
            "<>": QueryOperator.NOT,
            ">": QueryOperator.GREATER_THAN,
            "<": QueryOperator.LESS_THAN,
            ">=": QueryOperator.GREATER_THAN_EQUALS,
            "<=": QueryOperator.LESS_THAN_EQUALS,
            "AND": QueryOperator.AND,
            "OR": QueryOperator.OR,
            "NOT": QueryOperator.NOT,
            "IN": QueryOperator.IN,
            "BETWEEN": QueryOperator.BETWEEN,
            "LIKE": QueryOperator.CONTAINS,
            "CONTAINS": QueryOperator.CONTAINS,
            "STARTS_WITH": QueryOperator.STARTS_WITH,
            "ENDS_WITH": QueryOperator.ENDS_WITH,
        }
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """Parse a SQL query string and extract relevant components.
        
        Args:
            query: The SQL query string
            
        Returns:
            Dictionary with parsed query information
        """
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty")
        
        # Parse the query with sqlparse
        try:
            parsed = sqlparse.parse(query)[0]
        except Exception as e:
            raise ValueError(f"Failed to parse query: {str(e)}")
        
        # Initialize result structure
        result = {
            "query_type": self._get_query_type(parsed),
            "tables": self._extract_tables(parsed),
            "selected_fields": self._extract_selected_fields(parsed),
            "where_conditions": self._extract_where_conditions(parsed),
            "joins": self._extract_joins(parsed),
            "custom_functions": self._extract_custom_functions(parsed),
            "group_by": self._extract_group_by(parsed),
            "order_by": self._extract_order_by(parsed),
            "limit": self._extract_limit(parsed),
            "offset": self._extract_offset(parsed),
            "having": self._extract_having(parsed),
            "raw_query": query,
            "parsed_tokens": parsed
        }
        
        return result
    
    def validate_query(self, parsed_query: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate a parsed query structure.
        
        Args:
            parsed_query: Parsed query structure
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic validation rules
        if not parsed_query.get("query_type"):
            return False, "Query type could not be determined"
        
        query_type = parsed_query["query_type"]
        
        # SELECT queries must have at least one field or table
        if query_type == "SELECT":
            if not parsed_query.get("selected_fields") and not parsed_query.get("tables"):
                return False, "SELECT query must specify fields and tables"
        
        # Validate table references
        tables = parsed_query.get("tables", [])
        joins = parsed_query.get("joins", [])
        
        # Check for valid table references in joins
        for join in joins:
            join_table = join.get("table")
            if join_table and join_table not in tables:
                tables.append(join_table)  # Add implicitly referenced tables
        
        return True, None
    
    def _get_query_type(self, parsed) -> str:
        """Extract the query type (SELECT, INSERT, etc.)."""
        for token in parsed.tokens:
            if token.ttype is Keyword.DML:
                return token.value.upper()
        return "UNKNOWN"
    
    def _extract_tables(self, parsed) -> List[str]:
        """Extract table names from the query."""
        tables = []
        query_type = self._get_query_type(parsed)
        
        if query_type == "SELECT":
            # Look for FROM clause
            from_seen = False
            for token in parsed.tokens:
                if from_seen:
                    if token.ttype is Keyword and token.value.upper() not in {"AS"}:
                        # Another clause is starting
                        break
                    if isinstance(token, Identifier):
                        tables.append(self._clean_identifier(token))
                    elif isinstance(token, IdentifierList):
                        for identifier in token.get_identifiers():
                            tables.append(self._clean_identifier(identifier))
                elif token.ttype is Keyword and token.value.upper() == "FROM":
                    from_seen = True
        
        # Extract tables from JOIN clauses
        tables.extend(self._extract_join_tables(parsed))
        
        # Look for subqueries
        tables.extend(self._extract_subquery_tables(parsed))
        
        # Remove duplicates and return
        return list(set(tables))
    
    def _extract_join_tables(self, parsed) -> List[str]:
        """Extract table names from JOIN clauses."""
        tables = []
        join_keywords = {"JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"}
        
        for token in parsed.tokens:
            if isinstance(token, TokenList):
                tables.extend(self._extract_join_tables(token))
            elif token.ttype is Keyword and any(kw in token.value.upper() for kw in join_keywords):
                # Find the next identifier after JOIN keyword
                idx = parsed.token_index(token)
                if idx is not None and idx + 1 < len(parsed.tokens):
                    next_token = parsed.tokens[idx + 1]
                    if isinstance(next_token, Identifier):
                        tables.append(self._clean_identifier(next_token))
        
        return tables
    
    def _extract_subquery_tables(self, parsed) -> List[str]:
        """Extract table names from subqueries."""
        tables = []
        
        for token in parsed.tokens:
            if isinstance(token, Parenthesis):
                # Check if the parenthesis contains a SELECT statement
                subquery_content = str(token)
                if "SELECT" in subquery_content.upper():
                    # Recursively parse the subquery
                    try:
                        subquery = subquery_content[1:-1]  # Remove parentheses
                        sub_parsed = self.parse_query(subquery)
                        tables.extend(sub_parsed.get("tables", []))
                    except Exception:
                        # If subquery parsing fails, skip it
                        pass
            elif isinstance(token, TokenList):
                tables.extend(self._extract_subquery_tables(token))
        
        return tables
    
    def _extract_selected_fields(self, parsed) -> List[Dict[str, Any]]:
        """Extract fields from the SELECT clause."""
        fields = []
        
        # Verify this is a SELECT query
        if self._get_query_type(parsed) != "SELECT":
            return fields
        
        # Find SELECT keyword
        select_token = None
        for token in parsed.tokens:
            if token.ttype is Keyword.DML and token.value.upper() == "SELECT":
                select_token = token
                break
        
        if not select_token:
            return fields
        
        # Get the next token after SELECT
        idx = parsed.token_index(select_token)
        if idx is None or idx + 1 >= len(parsed.tokens):
            return fields
        
        next_token = parsed.tokens[idx + 1]
        
        # Handle SELECT * case
        if next_token.ttype is Wildcard:
            fields.append({
                "name": "*",
                "table": None,
                "alias": None,
                "is_function": False,
                "function_name": None,
                "function_args": None
            })
            return fields
        
        # Handle field list
        if isinstance(next_token, IdentifierList):
            for identifier in next_token.get_identifiers():
                fields.append(self._parse_field(identifier))
        elif isinstance(next_token, (Identifier, Function)):
            fields.append(self._parse_field(next_token))
        else:
            # Try to extract field list manually
            field_list = self._extract_field_list_manually(parsed)
            fields.extend(field_list)
        
        return fields
    
    def _parse_field(self, token) -> Dict[str, Any]:
        """Parse a field identifier and extract name, table, alias, and function info."""
        field_info = {
            "name": None,
            "table": None,
            "alias": None,
            "is_function": False,
            "function_name": None,
            "function_args": None
        }
        
        # Handle function calls
        if isinstance(token, Function):
            field_info["is_function"] = True
            if hasattr(token, 'get_name'):
                field_info["function_name"] = token.get_name()
            else:
                field_info["function_name"] = str(token.tokens[0])
            
            # Extract function arguments
            if hasattr(token, 'get_parameters'):
                params = token.get_parameters()
                if params:
                    field_info["function_args"] = str(params).strip()
            
            field_info["name"] = str(token)
        
        # Handle normal identifiers
        elif isinstance(token, Identifier):
            # Check if the identifier has an alias
            if hasattr(token, 'get_alias'):
                alias = token.get_alias()
                if alias:
                    field_info["alias"] = alias
            
            # Get the real name part
            if hasattr(token, 'get_real_name'):
                name_parts = token.get_real_name().split(".")
            else:
                name_parts = str(token).split(".")
            
            if len(name_parts) > 1:
                field_info["table"] = name_parts[0]
                field_info["name"] = name_parts[1]
            else:
                field_info["name"] = name_parts[0]
        
        else:
            # Fallback for anything else
            field_info["name"] = str(token).strip()
        
        return field_info
    
    def _extract_field_list_manually(self, parsed) -> List[Dict[str, Any]]:
        """Manually extract field list when automatic parsing fails."""
        fields = []
        query_text = str(parsed)
        
        # Extract field list after SELECT
        match = re.search(r'SELECT\s+([^FROM]+)\s+FROM', query_text, re.IGNORECASE)
        if match:
            field_list = match.group(1).strip()
            field_tokens = [f.strip() for f in field_list.split(',')]
            
            for field in field_tokens:
                if field:
                    # Basic field parsing
                    field_info = {
                        "name": field,
                        "table": None,
                        "alias": None,
                        "is_function": False,
                        "function_name": None,
                        "function_args": None
                    }
                    
                    # Check for table prefix
                    if '.' in field and not '(' in field:
                        parts = field.split('.')
                        if len(parts) == 2:
                            field_info["table"] = parts[0]
                            field_info["name"] = parts[1]
                    
                    # Check for function
                    if '(' in field and ')' in field:
                        field_info["is_function"] = True
                        func_match = re.match(r'(\w+)\s*\(', field)
                        if func_match:
                            field_info["function_name"] = func_match.group(1)
                    
                    fields.append(field_info)
        
        return fields
    
    def _extract_where_conditions(self, parsed) -> List[Dict[str, Any]]:
        """Extract conditions from WHERE clause."""
        conditions = []
        
        # Find WHERE clause
        where_clause = None
        for token in parsed.tokens:
            if isinstance(token, Where):
                where_clause = token
                break
        
        if not where_clause:
            return conditions
        
        # Extract conditions from the WHERE clause
        self._parse_conditions(where_clause, conditions)
        
        return conditions
    
    def _parse_conditions(self, clause, conditions: List[Dict[str, Any]]) -> None:
        """Parse conditions from a clause recursively."""
        for token in clause.tokens:
            if isinstance(token, Comparison):
                condition = self._parse_comparison(token)
                if condition:
                    conditions.append(condition)
            elif isinstance(token, TokenList):
                self._parse_conditions(token, conditions)
    
    def _parse_comparison(self, comparison: Comparison) -> Optional[Dict[str, Any]]:
        """Parse a comparison token into a condition dictionary."""
        try:
            tokens = list(comparison.flatten())
            if len(tokens) >= 3:
                left = tokens[0].value.strip()
                operator = tokens[1].value.strip()
                right = tokens[2].value.strip()
                
                # Map SQL operator to QueryOperator
                query_op = self._operator_mapping.get(operator.upper(), QueryOperator.EQUALS)
                
                return {
                    "field": left,
                    "operator": query_op,
                    "value": self._extract_quoted_string(right),
                    "raw_condition": str(comparison).strip()
                }
        except (IndexError, AttributeError):
            pass
        
        return None
    
    def _extract_joins(self, parsed) -> List[Dict[str, Any]]:
        """Extract JOIN clauses and conditions."""
        joins = []
        
        # Look for JOIN tokens
        join_keywords = ["JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "CROSS JOIN"]
        
        for i, token in enumerate(parsed.tokens):
            if token.ttype is Keyword and any(kw in token.value.upper() for kw in join_keywords):
                join_info = {
                    "type": token.value.upper(),
                    "table": None,
                    "condition": None
                }
                
                # Find the table name (next identifier)
                for j in range(i + 1, len(parsed.tokens)):
                    next_token = parsed.tokens[j]
                    if isinstance(next_token, Identifier):
                        join_info["table"] = self._clean_identifier(next_token)
                        break
                
                # Find the ON condition
                for j in range(i + 1, len(parsed.tokens)):
                    next_token = parsed.tokens[j]
                    if next_token.ttype is Keyword and next_token.value.upper() == "ON":
                        if j + 1 < len(parsed.tokens):
                            condition_token = parsed.tokens[j + 1]
                            join_info["condition"] = str(condition_token).strip()
                        break
                
                joins.append(join_info)
        
        return joins
    
    def _extract_custom_functions(self, parsed) -> List[Dict[str, Any]]:
        """Extract custom function calls from the query."""
        functions = []
        
        # Look for function calls in all tokens
        for token in parsed.tokens:
            if isinstance(token, Function):
                func_info = self._parse_function(token)
                if func_info:
                    functions.append(func_info)
            elif isinstance(token, TokenList):
                functions.extend(self._extract_custom_functions_from_tokens(token))
        
        return functions
    
    def _extract_custom_functions_from_tokens(self, token_list: TokenList) -> List[Dict[str, Any]]:
        """Extract custom functions from a token list recursively."""
        functions = []
        
        for token in token_list.tokens:
            if isinstance(token, Function):
                func_info = self._parse_function(token)
                if func_info:
                    functions.append(func_info)
            elif isinstance(token, TokenList):
                functions.extend(self._extract_custom_functions_from_tokens(token))
        
        return functions
    
    def _parse_function(self, function_token: Function) -> Optional[Dict[str, Any]]:
        """Parse a function token into a function info dictionary."""
        try:
            function_name = function_token.get_name() if hasattr(function_token, 'get_name') else str(function_token.tokens[0])
            
            # Check if this is a registered custom function
            if function_name.upper() in self._custom_functions:
                func_info = {
                    "name": function_name.upper(),
                    "args": [],
                    "raw_function": str(function_token)
                }
                
                # Extract parameters
                if hasattr(function_token, 'get_parameters'):
                    params = function_token.get_parameters()
                    if params:
                        param_text = str(params)
                        # Split by comma and clean up
                        args = [arg.strip().strip("'\"") for arg in param_text.split(',')]
                        func_info["args"] = args
                
                return func_info
        except (AttributeError, IndexError):
            pass
        
        return None
    
    def _extract_group_by(self, parsed) -> List[str]:
        """Extract GROUP BY fields."""
        group_by = []
        group_by_seen = False
        
        for token in parsed.tokens:
            if group_by_seen:
                if token.ttype is Keyword and token.value.upper() not in {"GROUP", "BY"}:
                    # Another clause is starting
                    break
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        group_by.append(str(identifier).strip())
                elif isinstance(token, Identifier):
                    group_by.append(str(token).strip())
                elif token.ttype in (Name, Name.Builtin):
                    group_by.append(token.value.strip())
            elif token.ttype is Keyword and token.value.upper() == "GROUP":
                # Look for BY
                idx = parsed.token_index(token)
                if idx is not None and idx + 1 < len(parsed.tokens):
                    next_token = parsed.tokens[idx + 1]
                    if next_token.ttype is Keyword and next_token.value.upper() == "BY":
                        group_by_seen = True
        
        return group_by
    
    def _extract_order_by(self, parsed) -> List[Dict[str, str]]:
        """Extract ORDER BY fields with sort order."""
        order_by = []
        order_by_seen = False
        
        for token in parsed.tokens:
            if order_by_seen:
                if token.ttype is Keyword and token.value.upper() not in {"ORDER", "BY"}:
                    # Another clause is starting (but not ASC/DESC)
                    if token.value.upper() not in {"ASC", "DESC"}:
                        break
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        order_by.append(self._parse_order_field(str(identifier)))
                elif isinstance(token, Identifier):
                    order_by.append(self._parse_order_field(str(token)))
                elif token.ttype in (Name, Name.Builtin):
                    order_by.append(self._parse_order_field(token.value))
            elif token.ttype is Keyword and token.value.upper() == "ORDER":
                # Look for BY
                idx = parsed.token_index(token)
                if idx is not None and idx + 1 < len(parsed.tokens):
                    next_token = parsed.tokens[idx + 1]
                    if next_token.ttype is Keyword and next_token.value.upper() == "BY":
                        order_by_seen = True
        
        return order_by
    
    def _parse_order_field(self, field_text: str) -> Dict[str, str]:
        """Parse an ORDER BY field with optional ASC/DESC."""
        field_text = field_text.strip()
        parts = field_text.split()
        
        field_name = parts[0]
        sort_order = "ASC"  # Default
        
        if len(parts) > 1 and parts[1].upper() in ["ASC", "DESC"]:
            sort_order = parts[1].upper()
        
        return {
            "field": field_name,
            "order": sort_order
        }
    
    def _extract_limit(self, parsed) -> Optional[int]:
        """Extract LIMIT value."""
        limit_seen = False
        
        for token in parsed.tokens:
            if limit_seen:
                if token.ttype is sqlparse.tokens.Number.Integer:
                    try:
                        return int(token.value)
                    except ValueError:
                        pass
            elif token.ttype is Keyword and token.value.upper() == "LIMIT":
                limit_seen = True
        
        return None
    
    def _extract_offset(self, parsed) -> Optional[int]:
        """Extract OFFSET value."""
        offset_seen = False
        
        for token in parsed.tokens:
            if offset_seen:
                if token.ttype is sqlparse.tokens.Number.Integer:
                    try:
                        return int(token.value)
                    except ValueError:
                        pass
            elif token.ttype is Keyword and token.value.upper() == "OFFSET":
                offset_seen = True
        
        return None
    
    def _extract_having(self, parsed) -> List[Dict[str, Any]]:
        """Extract HAVING conditions."""
        conditions = []
        having_seen = False
        
        for token in parsed.tokens:
            if having_seen:
                if token.ttype is Keyword and token.value.upper() != "HAVING":
                    # Another clause is starting
                    break
                if isinstance(token, Comparison):
                    condition = self._parse_comparison(token)
                    if condition:
                        conditions.append(condition)
                elif isinstance(token, TokenList):
                    self._parse_conditions(token, conditions)
            elif token.ttype is Keyword and token.value.upper() == "HAVING":
                having_seen = True
        
        return conditions
    
    def has_custom_functions(self, query: str) -> bool:
        """Check if a query contains registered custom functions.
        
        Args:
            query: SQL query string
            
        Returns:
            True if custom functions are present
        """
        query_upper = query.upper()
        return any(func_name in query_upper for func_name in self._custom_functions.keys())
    
    def extract_table_relationships(self, query: str) -> List[Tuple[str, str]]:
        """Extract relationships between tables from JOIN conditions.
        
        Args:
            query: SQL query string
            
        Returns:
            List of (table1, table2) pairs representing relationships
        """
        parsed_query = self.parse_query(query)
        relationships = []
        
        # Process JOIN conditions
        for join in parsed_query.get("joins", []):
            condition = join.get("condition")
            if condition:
                # Look for patterns like "table1.field = table2.field"
                matches = re.findall(r'(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)', condition)
                for match in matches:
                    table1, field1, table2, field2 = match
                    relationships.append((table1, table2))
        
        return relationships