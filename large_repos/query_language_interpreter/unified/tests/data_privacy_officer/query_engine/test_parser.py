"""Tests for the SQL query parser with privacy extensions."""

import pytest

from privacy_query_interpreter.query_engine.parser import (
    QueryParser, PrivacyFunction
)


class TestQueryParser:
    """Test cases for the QueryParser class."""
    
    def test_initialization(self):
        """Test parser initialization."""
        parser = QueryParser()
        assert parser.privacy_function_pattern is not None
    
    def test_privacy_function_enum(self):
        """Test the PrivacyFunction enum values."""
        assert PrivacyFunction.ANONYMIZE == "ANONYMIZE"
        assert PrivacyFunction.PSEUDONYMIZE == "PSEUDONYMIZE"
        assert PrivacyFunction.MASK == "MASK"
        assert PrivacyFunction.REDACT == "REDACT"
        assert PrivacyFunction.GENERALIZE == "GENERALIZE"
        assert PrivacyFunction.PERTURB == "PERTURB"
        assert PrivacyFunction.TOKENIZE == "TOKENIZE"
        assert PrivacyFunction.DIFFERENTIAL == "DIFFERENTIAL"
        assert PrivacyFunction.AGGREGATE == "AGGREGATE"
        assert PrivacyFunction.AUDIT == "AUDIT"
        assert PrivacyFunction.CLASSIFY == "CLASSIFY"
        assert PrivacyFunction.MINIMIZEACCESS == "MINIMIZEACCESS"
        assert PrivacyFunction.CHECKPOLICY == "CHECKPOLICY"
    
    def test_parse_simple_query(self):
        """Test parsing a simple SELECT query."""
        parser = QueryParser()
        
        # Parse a simple query
        query = "SELECT name, email FROM customers WHERE customer_segment = 'Premium'"
        result = parser.parse_query(query)
        
        # Check the parsed components
        assert result["query_type"] == "SELECT"
        assert result["tables"] == ["customers"]
        assert len(result["selected_fields"]) == 2
        assert result["selected_fields"][0]["name"] == "name"
        assert result["selected_fields"][1]["name"] == "email"
        assert len(result["where_conditions"]) == 1
        assert "customer_segment = 'Premium'" in result["where_conditions"][0]
        assert result["joins"] == []
        assert result["privacy_functions"] == []
        assert result["group_by"] == []
        assert result["order_by"] == []
        assert result["limit"] is None
        assert result["raw_query"] == query
    
    def test_parse_query_with_join(self):
        """Test parsing a query with JOIN clause."""
        parser = QueryParser()
        
        # Parse a query with a join
        query = """
            SELECT c.name, c.email, o.product, o.amount
            FROM customers c
            JOIN orders o ON c.id = o.customer_id
            WHERE o.amount > 100
        """
        result = parser.parse_query(query)
        
        # Check the parsed tables and joins
        assert set(result["tables"]) == {"customers", "orders"}
        assert len(result["joins"]) == 1
        assert result["joins"][0]["type"] == "JOIN"
        assert result["joins"][0]["table"] == "orders"
        assert "c.id = o.customer_id" in result["joins"][0]["condition"]
        
        # Check the fields with aliases
        assert len(result["selected_fields"]) == 4
        assert any(f["name"] == "name" and f["table"] == "c" for f in result["selected_fields"])
        assert any(f["name"] == "email" and f["table"] == "c" for f in result["selected_fields"])
        assert any(f["name"] == "product" and f["table"] == "o" for f in result["selected_fields"])
        assert any(f["name"] == "amount" and f["table"] == "o" for f in result["selected_fields"])
    
    def test_parse_query_with_privacy_functions(self):
        """Test parsing a query with privacy extension functions."""
        parser = QueryParser()
        
        # Parse a query with privacy functions
        query = """
            SELECT 
                ANONYMIZE(name), 
                MASK(email, reveal_first=3), 
                PSEUDONYMIZE(phone, prefix='PHONE') 
            FROM customers
        """
        result = parser.parse_query(query)
        
        # Check the extracted privacy functions
        assert len(result["privacy_functions"]) == 3
        
        # Check the ANONYMIZE function
        anon_func = next((f for f in result["privacy_functions"] if f["function"] == "ANONYMIZE"), None)
        assert anon_func is not None
        assert anon_func["field"] == "name"
        
        # Check the MASK function with arguments
        mask_func = next((f for f in result["privacy_functions"] if f["function"] == "MASK"), None)
        assert mask_func is not None
        assert mask_func["field"] == "email"
        assert "reveal_first" in mask_func["args"]
        assert mask_func["args"]["reveal_first"] == "3"
        
        # Check the PSEUDONYMIZE function with arguments
        pseudo_func = next((f for f in result["privacy_functions"] if f["function"] == "PSEUDONYMIZE"), None)
        assert pseudo_func is not None
        assert pseudo_func["field"] == "phone"
        assert "prefix" in pseudo_func["args"]
        assert pseudo_func["args"]["prefix"] == "PHONE"
        
        # Also verify has_privacy_func in selected fields
        privacy_fields = [f for f in result["selected_fields"] if f["has_privacy_func"]]
        assert len(privacy_fields) == 3
    
    def test_parse_query_with_various_clauses(self):
        """Test parsing a query with GROUP BY, ORDER BY, and LIMIT clauses."""
        parser = QueryParser()
        
        # Parse a complex query
        query = """
            SELECT 
                customer_segment, 
                COUNT(*) as count, 
                AVG(amount) as avg_amount
            FROM customers c
            JOIN orders o ON c.id = o.customer_id
            WHERE o.amount > 100
            GROUP BY customer_segment
            ORDER BY avg_amount DESC
            LIMIT 10
        """
        result = parser.parse_query(query)
        
        # Check GROUP BY
        assert len(result["group_by"]) == 1
        assert "customer_segment" in result["group_by"][0]
        
        # Check ORDER BY
        assert len(result["order_by"]) == 1
        assert "avg_amount DESC" in result["order_by"][0]
        
        # Check LIMIT
        assert result["limit"] == 10
        
        # Check fields with aliases
        assert len(result["selected_fields"]) == 3
        count_field = next((f for f in result["selected_fields"] if "count" in str(f["name"]).lower()), None)
        assert count_field is not None
        assert count_field["alias"] == "count"
        
        avg_field = next((f for f in result["selected_fields"] if "avg" in str(f["name"]).lower()), None)
        assert avg_field is not None
        assert avg_field["alias"] == "avg_amount"
    
    def test_has_privacy_functions(self):
        """Test detecting privacy functions in a query."""
        parser = QueryParser()
        
        # Query with privacy functions
        query_with_privacy = "SELECT ANONYMIZE(name), MASK(email) FROM customers"
        assert parser.has_privacy_functions(query_with_privacy) is True
        
        # Query without privacy functions
        query_without_privacy = "SELECT name, email FROM customers"
        assert parser.has_privacy_functions(query_without_privacy) is False
    
    def test_extract_table_relationships(self):
        """Test extracting table relationships from JOINs."""
        parser = QueryParser()
        
        # Query with multiple joins
        query = """
            SELECT c.name, o.product, p.payment_method
            FROM customers c
            JOIN orders o ON c.id = o.customer_id
            JOIN payments p ON o.id = p.order_id
        """
        relationships = parser.extract_table_relationships(query)
        
        # Should extract two relationships
        assert len(relationships) == 2
        assert ("c", "o") in relationships
        assert ("o", "p") in relationships
    
    def test_parse_select_star(self):
        """Test parsing a SELECT * query."""
        parser = QueryParser()
        
        # Parse a SELECT * query
        query = "SELECT * FROM customers"
        result = parser.parse_query(query)
        
        # Check the selected fields
        assert len(result["selected_fields"]) == 1
        assert result["selected_fields"][0]["name"] == "*"
    
    def test_parse_query_with_subqueries(self):
        """Test parsing a query with subqueries."""
        parser = QueryParser()
        
        # Parse a query with a subquery
        query = """
            SELECT c.name, c.email
            FROM customers c
            WHERE c.id IN (
                SELECT customer_id 
                FROM orders 
                WHERE amount > 1000
            )
        """
        result = parser.parse_query(query)
        
        # Main query tables
        assert "customers" in result["tables"]
        
        # Subquery tables should also be detected
        assert "orders" in result["tables"]
        
        # Where condition should include the subquery
        assert any("IN" in cond for cond in result["where_conditions"])
    
    def test_parse_query_with_different_join_types(self):
        """Test parsing a query with different types of JOINs."""
        parser = QueryParser()
        
        # Parse a query with different join types
        query = """
            SELECT c.name, o.product, p.payment_method
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id
            INNER JOIN payments p ON o.id = p.order_id
            RIGHT JOIN shipments s ON o.id = s.order_id
        """
        result = parser.parse_query(query)
        
        # Should extract all tables
        assert set(result["tables"]) == {"customers", "orders", "payments", "shipments"}
        
        # Should extract all joins with their types
        assert len(result["joins"]) == 3
        
        join_types = [j["type"] for j in result["joins"]]
        assert "LEFT JOIN" in join_types
        assert "INNER JOIN" in join_types
        assert "RIGHT JOIN" in join_types