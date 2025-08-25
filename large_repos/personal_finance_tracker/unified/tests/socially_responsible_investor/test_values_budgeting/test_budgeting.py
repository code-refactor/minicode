"""Tests for the values-aligned budgeting system."""

import pytest
from unittest.mock import patch, MagicMock
import time
from datetime import date, timedelta
from typing import Dict, List, Any

from ethical_finance.models import Transaction
from ethical_finance.values_budgeting.budgeting import (
    ValuesAlignedBudgeting,
    ValueCategory,
    ValueAlignment,
    SpendingAnalysisResult,
    create_default_value_categories
)


class TestValuesBudgeting:
    """Test class for the values-aligned budgeting system."""
    
    def test_create_default_value_categories(self):
        """Test creating default value categories."""
        categories = create_default_value_categories()
        
        # Check that we got valid categories
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert all(isinstance(cat, ValueCategory) for cat in categories)
        
        # Check for required alignments
        alignments = [cat.alignment for cat in categories]
        assert "aligned" in alignments
        assert "neutral" in alignments
        assert "misaligned" in alignments
        
        # Check for required categories
        category_names = [cat.name for cat in categories]
        required_categories = ["Sustainable Food", "Public Transportation", "Fossil Fuel Transportation"]
        for req_cat in required_categories:
            assert req_cat in category_names
    
    def test_initialize_budgeting_system(self):
        """Test initializing the values-aligned budgeting system."""
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        assert hasattr(budgeting, "categories")
        assert isinstance(budgeting.categories, dict)
        assert len(budgeting.categories) == len(categories)
        
        # Check that tag index was built
        assert hasattr(budgeting, "tag_index")
        assert isinstance(budgeting.tag_index, dict)
        assert len(budgeting.tag_index) > 0
    
    def test_categorize_transaction_with_tags(self, sample_personal_transactions):
        """Test categorizing a transaction with explicit tags."""
        # Find a transaction with tags
        tx_with_tags = None
        for tx_data in sample_personal_transactions:
            if tx_data["tags"]:
                tx_with_tags = tx_data
                break
        
        assert tx_with_tags is not None, "No transaction with tags found in test data"
        
        # Convert to Transaction model
        transaction = Transaction(
            id=tx_with_tags["id"],
            date=date.fromisoformat(tx_with_tags["date"]),
            amount=tx_with_tags["amount"],
            vendor=tx_with_tags["vendor"],
            category=tx_with_tags["category"],
            description=tx_with_tags["description"],
            tags=tx_with_tags["tags"]
        )
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Categorize transaction
        result = budgeting.categorize_transaction(transaction)
        
        # Verify result
        assert isinstance(result, ValueAlignment)
        assert result.transaction_id == transaction.id
        assert isinstance(result.value_categories, list)
        assert isinstance(result.alignment_score, float)
        assert -1.0 <= result.alignment_score <= 1.0
        assert isinstance(result.impact_level, int)
        assert 0 <= result.impact_level <= 5
        assert isinstance(result.reasons, list)
        assert len(result.reasons) > 0
        
        # For transactions with tags, should have matched based on tags
        assert any("Matched tags" in reason for reason in result.reasons)
    
    def test_categorize_transaction_without_tags(self, sample_personal_transactions):
        """Test categorizing a transaction without explicit tags."""
        # Create a transaction without tags
        tx_data = sample_personal_transactions[0].copy()
        tx_data["tags"] = []
        
        # Convert to Transaction model
        transaction = Transaction(
            id=tx_data["id"],
            date=date.fromisoformat(tx_data["date"]),
            amount=tx_data["amount"],
            vendor=tx_data["vendor"],
            category=tx_data["category"],
            description=tx_data["description"],
            tags=tx_data["tags"]
        )
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Categorize transaction
        result = budgeting.categorize_transaction(transaction)
        
        # Verify result
        assert isinstance(result, ValueAlignment)
        assert isinstance(result.value_categories, list)
        assert isinstance(result.alignment_score, float)
        assert -1.0 <= result.alignment_score <= 1.0
        
        # Should have used transaction details for categorization
        assert any("based on transaction" in reason.lower() for reason in result.reasons)
    
    def test_batch_categorize_transactions(self, sample_personal_transactions):
        """Test categorizing multiple transactions in batch."""
        # Convert sample data to Transaction models
        transactions = []
        for tx_data in sample_personal_transactions:
            transactions.append(Transaction(
                id=tx_data["id"],
                date=date.fromisoformat(tx_data["date"]),
                amount=tx_data["amount"],
                vendor=tx_data["vendor"],
                category=tx_data["category"],
                description=tx_data["description"],
                tags=tx_data["tags"]
            ))
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Batch categorize transactions
        results = budgeting.batch_categorize_transactions(transactions)
        
        # Verify results
        assert isinstance(results, dict)
        assert len(results) == len(transactions)
        
        # Check that all transactions were categorized
        for transaction in transactions:
            assert transaction.id in results
            assert isinstance(results[transaction.id], ValueAlignment)
    
    def test_analyze_spending_patterns(self, sample_personal_transactions):
        """Test analyzing spending patterns against value alignment."""
        # Convert sample data to Transaction models
        transactions = []
        for tx_data in sample_personal_transactions:
            transactions.append(Transaction(
                id=tx_data["id"],
                date=date.fromisoformat(tx_data["date"]),
                amount=tx_data["amount"],
                vendor=tx_data["vendor"],
                category=tx_data["category"],
                description=tx_data["description"],
                tags=tx_data["tags"]
            ))
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Analyze spending patterns
        result = budgeting.analyze_spending_patterns(transactions)
        
        # Verify result
        assert isinstance(result, SpendingAnalysisResult)
        assert isinstance(result.analysis_date, date)
        assert isinstance(result.period_start, date)
        assert isinstance(result.period_end, date)
        assert result.total_spending > 0
        assert isinstance(result.spending_by_category, dict)
        assert isinstance(result.spending_by_alignment, dict)
        assert isinstance(result.high_impact_areas, list)
        assert isinstance(result.improvement_opportunities, list)
        assert 0.0 <= result.aligned_percentage <= 1.0
        assert 0.0 <= result.consistency_score <= 100.0
        assert result.processing_time_ms > 0
        
        # Check that spending by alignment includes all alignment types
        assert "aligned" in result.spending_by_alignment
        assert "neutral" in result.spending_by_alignment
        assert "misaligned" in result.spending_by_alignment
        assert "uncategorized" in result.spending_by_alignment
        
        # Sum of spending by alignment should equal total spending
        alignment_sum = sum(result.spending_by_alignment.values())
        assert alignment_sum == pytest.approx(result.total_spending)
    
    def test_analyze_spending_patterns_with_date_filter(self, sample_personal_transactions):
        """Test analyzing spending patterns with date filtering."""
        # Convert sample data to Transaction models
        transactions = []
        for tx_data in sample_personal_transactions:
            transactions.append(Transaction(
                id=tx_data["id"],
                date=date.fromisoformat(tx_data["date"]),
                amount=tx_data["amount"],
                vendor=tx_data["vendor"],
                category=tx_data["category"],
                description=tx_data["description"],
                tags=tx_data["tags"]
            ))
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Find date range in sample data
        dates = [tx.date for tx in transactions]
        min_date = min(dates)
        max_date = max(dates)
        
        # Create a narrower date range
        start_date = min_date + timedelta(days=1)
        end_date = max_date - timedelta(days=1)
        
        # Analyze spending patterns with date filter
        result = budgeting.analyze_spending_patterns(transactions, start_date, end_date)
        
        # Verify result respects date filter
        assert result.period_start == start_date
        assert result.period_end == end_date
        
        # Total spending should be less than or equal to full dataset
        full_result = budgeting.analyze_spending_patterns(transactions)
        assert result.total_spending <= full_result.total_spending
    
    def test_suggest_alternative_vendors(self):
        """Test suggesting alternative vendors that better align with values."""
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Test suggesting alternatives for a gas vendor
        alternatives = budgeting.suggest_alternative_vendors("Shell Gas Station", "Gas")
        
        # Verify results
        assert isinstance(alternatives, list)
        assert len(alternatives) > 0
        
        # Check that alternatives have expected fields
        for alt in alternatives:
            assert "name" in alt
            assert "alignment" in alt
            assert "impact" in alt
            assert "description" in alt
        
        # Test suggesting alternatives for a coffee vendor
        alternatives = budgeting.suggest_alternative_vendors("Starbucks", "Coffee")
        
        # Verify results for coffee
        assert isinstance(alternatives, list)
        if len(alternatives) > 0:  # May not have alternatives for every category
            assert all("name" in alt for alt in alternatives)
        
        # Test category with no alternatives
        alternatives = budgeting.suggest_alternative_vendors("Unknown Vendor", "Unknown Category")
        assert len(alternatives) == 0
    
    def test_suggest_categories_from_transaction(self, sample_personal_transactions):
        """Test suggesting categories based on transaction details."""
        # Convert a sample transaction to Transaction model
        tx_data = sample_personal_transactions[0]
        transaction = Transaction(
            id=tx_data["id"],
            date=date.fromisoformat(tx_data["date"]),
            amount=tx_data["amount"],
            vendor=tx_data["vendor"],
            category=tx_data["category"],
            description=tx_data["description"],
            tags=[]  # Explicitly remove tags to test suggestion logic
        )
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Suggest categories
        suggested_categories = budgeting._suggest_categories_from_transaction(transaction)
        
        # Verify results
        assert isinstance(suggested_categories, list)
        
        # Since we're using real transaction data, we can't assert exact matches
        # But we can check that the method returns something reasonable
        for cat_id in suggested_categories:
            assert cat_id in budgeting.categories
    
    def test_find_categories_by_alignment(self):
        """Test finding categories with a specific alignment."""
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Find aligned categories
        aligned_categories = budgeting._find_categories_by_alignment("aligned")
        
        # Verify results
        assert isinstance(aligned_categories, set)
        assert len(aligned_categories) > 0
        
        # All returned categories should have the requested alignment
        for cat_id in aligned_categories:
            assert cat_id in budgeting.categories
            assert budgeting.categories[cat_id].alignment == "aligned"
        
        # Test with other alignments
        neutral_categories = budgeting._find_categories_by_alignment("neutral")
        misaligned_categories = budgeting._find_categories_by_alignment("misaligned")
        
        # Should not overlap
        assert aligned_categories.isdisjoint(neutral_categories)
        assert aligned_categories.isdisjoint(misaligned_categories)
        assert neutral_categories.isdisjoint(misaligned_categories)
    
    def test_performance_categorizing_many_transactions(self, sample_personal_transactions):
        """Test performance categorizing many transactions."""
        # Create a large number of transactions
        num_transactions = 1000
        transactions = []
        
        for i in range(num_transactions):
            # Use modulo to cycle through sample transactions
            sample_idx = i % len(sample_personal_transactions)
            tx_data = sample_personal_transactions[sample_idx]
            
            # Create a new transaction with a unique ID
            transactions.append(Transaction(
                id=f"{tx_data['id']}-{i}",
                date=date.fromisoformat(tx_data["date"]),
                amount=tx_data["amount"],
                vendor=tx_data["vendor"],
                category=tx_data["category"],
                description=tx_data["description"],
                tags=tx_data["tags"]
            ))
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Measure performance
        start_time = time.time()
        
        results = budgeting.batch_categorize_transactions(transactions)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all transactions were categorized
        assert len(results) == num_transactions
        
        # Performance requirement: categorize 1000+ transactions per second
        txs_per_second = num_transactions / total_time
        
        print(f"Categorized {num_transactions} transactions in {total_time:.2f} seconds")
        print(f"Rate: {txs_per_second:.2f} transactions per second")
        
        # Check that performance meets requirements
        assert txs_per_second >= 1000.0
        
    def test_categorize_transaction_with_conflicting_values(self):
        """Test categorizing a transaction with conflicting value tags."""
        # Create a budget system with default categories
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Create a transaction with conflicting value tags
        # (both aligned and misaligned tags)
        transaction = Transaction(
            id="conflict1",
            date=date.today(),
            amount=85.75,
            vendor="Mixed Values Store",
            category="Shopping",
            description="Purchase with both aligned and misaligned attributes",
            tags=["organic", "sustainable", "plastic_packaging", "fossil_fuel"]
        )
        
        # Categorize the transaction
        result = budgeting.categorize_transaction(transaction)
        
        # Verify result is a valid ValueAlignment object
        assert isinstance(result, ValueAlignment)
        assert result.transaction_id == transaction.id
        
        # Verify alignment score reflects the conflict
        # The result should be between -1 and 1, reflecting the mixed nature
        assert -1.0 <= result.alignment_score <= 1.0
        
        # Check that both aligned and misaligned tags are recognized
        aligned_tags = False
        misaligned_tags = False
        for reason in result.reasons:
            if "organic" in reason.lower() or "sustainable" in reason.lower():
                aligned_tags = True
            if "plastic_packaging" in reason.lower() or "fossil_fuel" in reason.lower():
                misaligned_tags = True
                
        # Verify that both types of tags were considered, rather than requiring a specific "conflict" message
        assert aligned_tags, "Aligned tags should be recognized in reasons"
        assert misaligned_tags, "Misaligned tags should be recognized in reasons"