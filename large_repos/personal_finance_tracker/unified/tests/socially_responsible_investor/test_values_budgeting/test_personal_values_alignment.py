"""Tests for personal values alignment in budgeting and spending."""

import pytest
from datetime import date, timedelta
from typing import Dict, List, Any
import random

from ethical_finance.models import Transaction
from ethical_finance.values_budgeting.budgeting import (
    ValuesAlignedBudgeting,
    ValueCategory,
    ValueAlignment,
    SpendingAnalysisResult,
    create_default_value_categories
)


class TestPersonalValuesAlignment:
    """Test class for advanced personal values alignment features."""
    
    def test_values_consistency_across_spending_categories(self, sample_personal_transactions):
        """Test analyzing values consistency across different spending categories."""
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
        
        # Group transactions by category
        transactions_by_category = {}
        for transaction in transactions:
            if transaction.category not in transactions_by_category:
                transactions_by_category[transaction.category] = []
            transactions_by_category[transaction.category].append(transaction)
        
        # Analyze values consistency across categories
        result = budgeting.analyze_values_consistency_across_categories(transactions_by_category)
        
        # Verify result
        assert isinstance(result, dict)
        assert "category_alignment" in result
        assert "consistency_score" in result
        assert "value_conflicts" in result
        assert "aligned_categories" in result
        assert "misaligned_categories" in result
        
        # Check category alignment
        for category, alignment in result["category_alignment"].items():
            assert category in transactions_by_category
            assert "alignment_score" in alignment
            assert "transaction_count" in alignment
            assert "total_amount" in alignment
            assert -1.0 <= alignment["alignment_score"] <= 1.0
            
        # Check consistency score
        assert 0 <= result["consistency_score"] <= 100
        
        # Check aligned and misaligned categories
        assert isinstance(result["aligned_categories"], list)
        assert isinstance(result["misaligned_categories"], list)
        assert set(result["aligned_categories"]).issubset(set(transactions_by_category.keys()))
        assert set(result["misaligned_categories"]).issubset(set(transactions_by_category.keys()))
        
    def test_values_drift_over_time(self, sample_personal_transactions):
        """Test detecting values drift in spending patterns over time."""
        # Convert sample data to Transaction models
        transactions = []
        for tx_data in sample_personal_transactions:
            # Parse the existing date
            tx_date = date.fromisoformat(tx_data["date"])
            
            # Create multiple copies of each transaction spanning different months
            for i in range(6):  # 6 months of data
                # Create a copy with adjusted date going back i months
                new_date = tx_date - timedelta(days=30 * i)
                
                # Add random variation to amounts
                amount_variation = tx_data["amount"] * (0.8 + (random.random() * 0.4))  # 80% to 120% variation
                
                # For transactions 3+ months ago, reduce the number of ethical tags
                # to simulate a drift in values over time
                tags = tx_data["tags"].copy()
                if i >= 3 and "sustainable" in tags:
                    tags.remove("sustainable")
                if i >= 4 and "organic" in tags:
                    tags.remove("organic")
                if i >= 5 and "local" in tags:
                    tags.remove("local")
                
                # Add non-aligned tags to older transactions
                if i >= 3:
                    if random.random() > 0.7 and "fossil_fuel" not in tags:
                        tags.append("fossil_fuel")
                    if random.random() > 0.8 and "chain_business" not in tags:
                        tags.append("chain_business")
                
                transactions.append(Transaction(
                    id=f"{tx_data['id']}-{i}",
                    date=new_date,
                    amount=amount_variation,
                    vendor=tx_data["vendor"],
                    category=tx_data["category"],
                    description=tx_data["description"],
                    tags=tags
                ))
        
        # Sort transactions by date
        transactions.sort(key=lambda tx: tx.date)
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Group transactions by month
        today = date.today()
        start_date = today - timedelta(days=180)  # 6 months ago
        
        # Analyze values drift over time
        result = budgeting.analyze_values_drift_over_time(transactions, start_date, today)
        
        # Verify result
        assert isinstance(result, dict)
        assert "trend_analysis" in result
        assert "monthly_alignment" in result
        assert "drift_detected" in result
        assert "drift_magnitude" in result
        assert "recommendations" in result
        
        # Check monthly alignment data
        for month_str, data in result["monthly_alignment"].items():
            assert "alignment_score" in data
            assert "transaction_count" in data
            assert "total_spent" in data
            assert "aligned_percentage" in data
            assert "misaligned_percentage" in data
            assert "neutral_percentage" in data
            assert 0 <= data["aligned_percentage"] <= 100
            assert 0 <= data["misaligned_percentage"] <= 100
            assert 0 <= data["neutral_percentage"] <= 100
            assert abs(data["aligned_percentage"] + data["misaligned_percentage"] + data["neutral_percentage"] - 100) < 0.01
        
        # Check drift magnitude
        if result["drift_detected"]:
            assert "direction" in result["drift_magnitude"]
            assert "percentage_change" in result["drift_magnitude"]
            assert result["drift_magnitude"]["direction"] in ["improving", "worsening"]
        
        # Check trend analysis
        assert "slope" in result["trend_analysis"]
        assert "correlation" in result["trend_analysis"]
        assert "is_significant" in result["trend_analysis"]
        
    def test_vendor_value_profile_analysis(self, sample_personal_transactions):
        """Test creating value profiles for vendors based on transaction history."""
        # Convert sample data to Transaction models with additional synthetic vendors
        base_transactions = []
        for tx_data in sample_personal_transactions:
            base_transactions.append(Transaction(
                id=tx_data["id"],
                date=date.fromisoformat(tx_data["date"]),
                amount=tx_data["amount"],
                vendor=tx_data["vendor"],
                category=tx_data["category"],
                description=tx_data["description"],
                tags=tx_data["tags"]
            ))
            
        # Create more transactions for specific vendors to establish patterns
        transactions = base_transactions.copy()
        
        # Add more transactions for Whole Foods (consistently sustainable)
        sustainable_tags = ["organic", "sustainable", "local", "fair_trade"]
        for i in range(10):
            transactions.append(Transaction(
                id=f"wf-{i}",
                date=date.today() - timedelta(days=random.randint(1, 90)),
                amount=random.uniform(50, 150),
                vendor="Whole Foods Market",
                category="Groceries",
                description=f"Sustainable grocery shopping {i}",
                tags=random.sample(sustainable_tags, k=min(len(sustainable_tags), random.randint(1, 3)))
            ))
            
        # Add more transactions for Shell (consistently non-sustainable)
        non_sustainable_tags = ["fossil_fuel", "non_renewable", "chain_business"]
        for i in range(8):
            transactions.append(Transaction(
                id=f"shell-{i}",
                date=date.today() - timedelta(days=random.randint(1, 90)),
                amount=random.uniform(30, 70),
                vendor="Shell Gas Station",
                category="Transportation",
                description=f"Gas refill {i}",
                tags=random.sample(non_sustainable_tags, k=min(len(non_sustainable_tags), random.randint(1, 2)))
            ))
            
        # Add transactions for a vendor with mixed sustainability (Starbucks)
        mixed_tags = ["chain_business", "fair_trade", "disposable_cups", "ethical_sourcing"]
        for i in range(12):
            # Slightly bias toward less sustainable
            if random.random() < 0.6:
                tags = random.sample(mixed_tags[:2], k=min(2, random.randint(1, 2)))
            else:
                tags = random.sample(mixed_tags[2:], k=min(2, random.randint(1, 2)))
                
            transactions.append(Transaction(
                id=f"sbux-{i}",
                date=date.today() - timedelta(days=random.randint(1, 90)),
                amount=random.uniform(4, 15),
                vendor="Starbucks",
                category="Dining",
                description=f"Coffee and snacks {i}",
                tags=tags
            ))
        
        # Initialize budgeting system
        categories = create_default_value_categories()
        budgeting = ValuesAlignedBudgeting(categories)
        
        # Analyze vendor value profiles
        result = budgeting.analyze_vendor_value_profiles(transactions)
        
        # Verify result
        assert isinstance(result, dict)
        assert "vendor_profiles" in result
        assert "vendor_rankings" in result
        assert "recommended_alternatives" in result
        
        # Check vendor profiles
        for vendor, profile in result["vendor_profiles"].items():
            assert "transaction_count" in profile
            assert "total_spent" in profile
            assert "alignment_score" in profile
            assert "common_tags" in profile
            assert "value_consistency" in profile
            assert "recommendation" in profile
            assert isinstance(profile["common_tags"], list)
            assert -1.0 <= profile["alignment_score"] <= 1.0
            assert 0.0 <= profile["value_consistency"] <= 1.0
            
        # Verify specific vendors that should be present
        assert "Whole Foods Market" in result["vendor_profiles"]
        assert "Shell Gas Station" in result["vendor_profiles"]
        assert "Starbucks" in result["vendor_profiles"]
        
        # Verify rankings structure
        assert "most_aligned" in result["vendor_rankings"]
        assert "least_aligned" in result["vendor_rankings"]
        assert isinstance(result["vendor_rankings"]["most_aligned"], list)
        assert isinstance(result["vendor_rankings"]["least_aligned"], list)
        
        # Check recommended alternatives
        for vendor, alternatives in result["recommended_alternatives"].items():
            if alternatives:  # Some vendors might not have alternatives
                assert isinstance(alternatives, list)
                for alt in alternatives:
                    assert "name" in alt
                    assert "alignment_score" in alt
                    assert "reason" in alt