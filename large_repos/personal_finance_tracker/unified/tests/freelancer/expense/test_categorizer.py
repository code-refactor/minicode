"""Tests for the expense categorization system."""

from datetime import datetime, timedelta
import time
import uuid

import pytest
import pandas as pd
import numpy as np

from personal_finance_tracker.models.common import (
    ExpenseCategory,
    Transaction,
    TransactionType,
)

from personal_finance_tracker.expense.models import (
    CategorizationRule,
    MixedUseItem,
    CategorizationResult,
)

from personal_finance_tracker.expense.categorizer import ExpenseCategorizer


class TestExpenseCategorizer:
    """Test suite for the ExpenseCategorizer class."""

    def test_init(self):
        """Test initialization of the expense categorizer."""
        categorizer = ExpenseCategorizer()
        assert categorizer.rules == []
        assert categorizer.mixed_use_items == []
        assert categorizer.audit_trail == []
        assert categorizer._categorization_cache == {}

    def test_add_categorization_rule(self):
        """Test adding a categorization rule."""
        categorizer = ExpenseCategorizer()

        # Create a rule
        rule = CategorizationRule(
            name="Office Supplies Rule",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            keyword_patterns=["office", "supplies", "paper", "ink", "toner"],
            business_use_percentage=100.0,
            priority=10,
        )

        # Add the rule
        added_rule = categorizer.add_categorization_rule(rule)

        # Verify the rule was added
        assert added_rule.id == rule.id
        assert len(categorizer.rules) == 1
        assert categorizer.rules[0] == rule

        # Add another rule with lower priority
        rule2 = CategorizationRule(
            name="Software Rule",
            category=ExpenseCategory.SOFTWARE,
            keyword_patterns=["software", "license", "subscription"],
            business_use_percentage=100.0,
            priority=5,
        )

        # Add the second rule
        categorizer.add_categorization_rule(rule2)

        # Verify rules are sorted by priority (highest first)
        assert len(categorizer.rules) == 2
        assert categorizer.rules[0] == rule  # Higher priority should be first
        assert categorizer.rules[1] == rule2

        # Test adding a duplicate rule (should raise error)
        with pytest.raises(ValueError):
            categorizer.add_categorization_rule(rule)

    def test_update_categorization_rule(self):
        """Test updating a categorization rule."""
        categorizer = ExpenseCategorizer()

        # Create and add a rule
        rule = CategorizationRule(
            name="Original Rule",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            keyword_patterns=["original"],
            business_use_percentage=100.0,
            priority=10,
        )

        categorizer.add_categorization_rule(rule)

        # Create an updated version
        updated_rule = CategorizationRule(
            id=rule.id,  # Same ID
            name="Updated Rule",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            keyword_patterns=["updated"],
            business_use_percentage=90.0,
            priority=20,
        )

        # Update the rule
        result = categorizer.update_categorization_rule(updated_rule)

        # Verify the update
        assert result.id == rule.id
        assert result.name == "Updated Rule"
        assert result.keyword_patterns == ["updated"]
        assert result.business_use_percentage == 90.0
        assert result.priority == 20
        assert result.updated_at is not None

        # Verify the rule in the categorizer was updated
        assert categorizer.rules[0].name == "Updated Rule"

        # Test updating a non-existent rule
        non_existent = CategorizationRule(
            id=uuid.uuid4(),  # Different ID
            name="Non-existent",
            category=ExpenseCategory.OTHER,
            keyword_patterns=["test"],
            business_use_percentage=100.0,
        )

        with pytest.raises(ValueError):
            categorizer.update_categorization_rule(non_existent)

    def test_remove_categorization_rule(self):
        """Test removing a categorization rule."""
        categorizer = ExpenseCategorizer()

        # Create and add rules
        rule1 = CategorizationRule(
            name="Rule 1",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            keyword_patterns=["rule1"],
            business_use_percentage=100.0,
        )

        rule2 = CategorizationRule(
            name="Rule 2",
            category=ExpenseCategory.SOFTWARE,
            keyword_patterns=["rule2"],
            business_use_percentage=100.0,
        )

        categorizer.add_categorization_rule(rule1)
        categorizer.add_categorization_rule(rule2)

        # Remove rule1
        result = categorizer.remove_categorization_rule(rule1.id)

        # Verify removal
        assert result is True
        assert len(categorizer.rules) == 1
        assert categorizer.rules[0].id == rule2.id

        # Try to remove non-existent rule
        result = categorizer.remove_categorization_rule(uuid.uuid4())
        assert result is False

    def test_add_mixed_use_item(self):
        """Test adding a mixed-use item."""
        categorizer = ExpenseCategorizer()

        # Create a mixed-use item
        item = MixedUseItem(
            name="Home Internet",
            category=ExpenseCategory.INTERNET,
            business_use_percentage=70.0,
            description="Internet used for both business and personal",
        )

        # Add the item
        added_item = categorizer.add_mixed_use_item(item)

        # Verify the item was added
        assert added_item.id == item.id
        assert len(categorizer.mixed_use_items) == 1
        assert categorizer.mixed_use_items[0] == item

        # Test adding a duplicate item
        with pytest.raises(ValueError):
            categorizer.add_mixed_use_item(item)

    def test_categorize_transaction(self, sample_transactions):
        """Test categorizing a transaction."""
        categorizer = ExpenseCategorizer()

        # Add some rules
        rules = [
            CategorizationRule(
                name="Software Rule",
                category=ExpenseCategory.SOFTWARE,
                keyword_patterns=["software", "subscription"],
                business_use_percentage=100.0,
                priority=10,
            ),
            CategorizationRule(
                name="Office Supplies Rule",
                category=ExpenseCategory.BUSINESS_SUPPLIES,
                keyword_patterns=["supplies", "office"],
                business_use_percentage=100.0,
                priority=5,
            ),
            CategorizationRule(
                name="Meal Rule",
                category=ExpenseCategory.MEALS,
                keyword_patterns=["meal", "restaurant", "food"],
                business_use_percentage=50.0,  # 50% business use
                priority=3,
            ),
        ]

        for rule in rules:
            categorizer.add_categorization_rule(rule)

        # Add a mixed-use item
        mixed_item = MixedUseItem(
            name="Internet",
            category=ExpenseCategory.INTERNET,
            business_use_percentage=80.0,
            description="Home internet used for business and personal",
        )

        categorizer.add_mixed_use_item(mixed_item)

        # Test transactions
        # 1. Software transaction matching a rule
        software_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 5, 15),
            amount=50.0,
            description="Monthly software subscription",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )

        result = categorizer.categorize_transaction(software_transaction)

        # Verify categorization
        assert result.transaction_id == software_transaction.id
        assert result.assigned_category == ExpenseCategory.SOFTWARE
        assert result.business_use_percentage == 100.0
        assert result.matched_rule is not None
        assert result.matched_rule.name == "Software Rule"
        assert result.confidence_score > 0.7

        # 2. Mixed-use item transaction
        internet_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 5, 20),
            amount=80.0,
            description="Monthly Internet bill",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )

        result = categorizer.categorize_transaction(internet_transaction)

        # Verify mixed-use categorization
        assert result.assigned_category == ExpenseCategory.INTERNET
        assert result.business_use_percentage == 80.0
        assert result.is_mixed_use is True

        # 3. Transaction with no matching rule (should default to personal)
        personal_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 5, 25),
            amount=100.0,
            description="Groceries",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )

        result = categorizer.categorize_transaction(personal_transaction)

        # Verify fallback categorization
        assert result.assigned_category == ExpenseCategory.PERSONAL
        assert result.business_use_percentage == 0.0
        assert result.matched_rule is None

        # 4. Test with an already categorized transaction
        categorized_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 5, 30),
            amount=200.0,
            description="Already categorized expense",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.MARKETING,
            business_use_percentage=100.0,
        )

        result = categorizer.categorize_transaction(categorized_transaction)

        # Verify existing categorization is respected
        assert result.assigned_category == ExpenseCategory.MARKETING
        assert result.business_use_percentage == 100.0
        assert result.confidence_score == 1.0

        # 5. Force recategorization
        result = categorizer.categorize_transaction(
            categorized_transaction, recategorize=True
        )

        # Verify recategorization happened
        assert result.confidence_score < 1.0

    def test_categorize_transactions(self):
        """Test categorizing multiple transactions at once."""
        categorizer = ExpenseCategorizer()

        # Add rules
        rule = CategorizationRule(
            name="Office Supplies Rule",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            keyword_patterns=["office", "supplies"],
            business_use_percentage=100.0,
        )

        categorizer.add_categorization_rule(rule)

        # Create test transactions
        transactions = [
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 6, 1),
                amount=50.0,
                description="Office supplies purchase",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 6, 2),
                amount=100.0,
                description="Personal expense",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 6, 3),
                amount=75.0,
                description="More office supplies",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
            ),
        ]

        # Categorize all transactions
        results = categorizer.categorize_transactions(transactions)

        # Verify results
        assert len(results) == 3

        # First and third transactions should match the rule
        assert results[0].assigned_category == ExpenseCategory.BUSINESS_SUPPLIES
        assert results[0].business_use_percentage == 100.0

        assert results[2].assigned_category == ExpenseCategory.BUSINESS_SUPPLIES
        assert results[2].business_use_percentage == 100.0

        # Second transaction should be personal
        assert results[1].assigned_category == ExpenseCategory.PERSONAL
        assert results[1].business_use_percentage == 0.0

    def test_apply_categorization(self):
        """Test applying a categorization result to a transaction."""
        categorizer = ExpenseCategorizer()

        # Create a transaction
        transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 7, 1),
            amount=100.0,
            description="Test transaction",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )

        # Create a categorization result

        result = CategorizationResult(
            transaction_id=transaction.id,
            original_transaction=transaction,
            assigned_category=ExpenseCategory.SOFTWARE,
            business_use_percentage=80.0,
            confidence_score=0.9,
            is_mixed_use=True,
        )

        # Apply the categorization
        updated_transaction = categorizer.apply_categorization(transaction, result)

        # Verify the transaction was updated
        assert updated_transaction.category == ExpenseCategory.SOFTWARE
        assert updated_transaction.business_use_percentage == 80.0

        # Verify audit trail was recorded
        assert len(categorizer.audit_trail) == 1
        assert categorizer.audit_trail[0].transaction_id == transaction.id
        assert categorizer.audit_trail[0].action == "apply_categorization"

    def test_generate_expense_summary(self, sample_transactions):
        """Test generating an expense summary."""
        categorizer = ExpenseCategorizer()

        # Add rules for test categories
        rules = [
            CategorizationRule(
                name="Software Rule",
                category=ExpenseCategory.SOFTWARE,
                keyword_patterns=["software"],
                business_use_percentage=100.0,
            ),
            CategorizationRule(
                name="Internet Rule",
                category=ExpenseCategory.INTERNET,
                keyword_patterns=["internet"],
                business_use_percentage=80.0,
            ),
        ]

        for rule in rules:
            categorizer.add_categorization_rule(rule)

        # Set date range
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Generate summary
        summary = categorizer.generate_expense_summary(
            sample_transactions, start_date, end_date
        )

        # Verify summary
        assert summary.period_start == start_date
        assert summary.period_end == end_date
        assert summary.total_expenses > 0
        assert summary.business_expenses >= 0
        assert summary.personal_expenses >= 0
        assert (
            abs(
                summary.business_expenses
                + summary.personal_expenses
                - summary.total_expenses
            )
            < 0.01
        )

        # Check category breakdown
        assert len(summary.by_category) > 0
        total_by_category = sum(summary.by_category.values())
        assert abs(total_by_category - summary.total_expenses) < 0.01

    def test_get_audit_trail(self):
        """Test retrieving the audit trail."""
        categorizer = ExpenseCategorizer()

        # Create a transaction
        transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 8, 1),
            amount=100.0,
            description="Test transaction",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )

        # Create a categorization result

        result = CategorizationResult(
            transaction_id=transaction.id,
            original_transaction=transaction,
            assigned_category=ExpenseCategory.SOFTWARE,
            business_use_percentage=100.0,
            confidence_score=0.9,
        )

        # Perform multiple actions to generate audit records
        categorizer.apply_categorization(transaction, result)

        # Change category
        result.assigned_category = ExpenseCategory.MARKETING
        categorizer.apply_categorization(transaction, result)

        # Attach receipt
        categorizer.attach_receipt(transaction, "/path/to/receipt.pdf")

        # Get the audit trail
        audit_trail = categorizer.get_audit_trail()

        # Verify audit records
        assert len(audit_trail) == 3

        # Records should be sorted by timestamp (newest first)
        assert audit_trail[0].action == "attach_receipt"
        assert audit_trail[1].action == "apply_categorization"
        assert audit_trail[2].action == "apply_categorization"

        # Test filtering by transaction ID
        filtered_trail = categorizer.get_audit_trail(transaction_id=transaction.id)
        assert len(filtered_trail) == 3

        # Test limit
        limited_trail = categorizer.get_audit_trail(limit=2)
        assert len(limited_trail) == 2

    def test_correct_categorization(self):
        """Test correcting the categorization of a transaction."""
        categorizer = ExpenseCategorizer()

        # Create a transaction with initial categorization
        transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 9, 1),
            amount=200.0,
            description="Initially miscategorized expense",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            category=ExpenseCategory.PERSONAL,
            business_use_percentage=0.0,
        )

        # Correct the categorization
        updated_transaction = categorizer.correct_categorization(
            transaction,
            new_category=ExpenseCategory.MARKETING,
            new_business_percentage=100.0,
        )

        # Verify the correction
        assert updated_transaction.category == ExpenseCategory.MARKETING
        assert updated_transaction.business_use_percentage == 100.0

        # Verify audit trail
        assert len(categorizer.audit_trail) == 1
        assert categorizer.audit_trail[0].action == "correct_categorization"
        assert (
            categorizer.audit_trail[0].previous_state["category"]
            == ExpenseCategory.PERSONAL
        )
        assert (
            categorizer.audit_trail[0].new_state["category"]
            == ExpenseCategory.MARKETING
        )

    def test_rule_matching(self):
        """Test rule matching logic in more detail."""
        categorizer = ExpenseCategorizer()

        # Create rules with different conditions
        rules = [
            # Rule with keyword patterns only
            CategorizationRule(
                name="Keyword Rule",
                category=ExpenseCategory.SOFTWARE,
                keyword_patterns=["software", "subscription"],
                business_use_percentage=100.0,
                priority=10,
            ),
            # Rule with merchant patterns only
            CategorizationRule(
                name="Merchant Rule",
                category=ExpenseCategory.MEALS,
                merchant_patterns=["restaurant", "cafe"],
                business_use_percentage=50.0,
                priority=8,
            ),
            # Rule with amount range only
            CategorizationRule(
                name="Amount Rule",
                category=ExpenseCategory.EQUIPMENT,
                amount_min=500.0,
                amount_max=2000.0,
                business_use_percentage=100.0,
                priority=5,
            ),
            # Rule with multiple conditions
            CategorizationRule(
                name="Complex Rule",
                category=ExpenseCategory.MARKETING,
                keyword_patterns=["marketing", "advertising"],
                merchant_patterns=["facebook", "google"],
                amount_max=300.0,
                business_use_percentage=100.0,
                priority=15,
            ),
        ]

        for rule in rules:
            categorizer.add_categorization_rule(rule)

        # Test transactions for each rule type

        # 1. Test keyword matching
        keyword_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 10, 1),
            amount=50.0,
            description="Monthly software subscription",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )

        result = categorizer.categorize_transaction(keyword_transaction)
        assert result.assigned_category == ExpenseCategory.SOFTWARE
        assert result.matched_rule.name == "Keyword Rule"

        # 2. Test merchant matching (via tags)
        merchant_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 10, 2),
            amount=75.0,
            description="Business lunch",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            tags=["restaurant", "client meeting"],
        )

        result = categorizer.categorize_transaction(merchant_transaction)
        assert result.assigned_category == ExpenseCategory.MEALS
        assert result.matched_rule.name == "Merchant Rule"
        assert result.business_use_percentage == 50.0

        # 3. Test amount range matching
        amount_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 10, 3),
            amount=1200.0,
            description="New equipment purchase",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )

        result = categorizer.categorize_transaction(amount_transaction)
        assert result.assigned_category == ExpenseCategory.EQUIPMENT
        assert result.matched_rule.name == "Amount Rule"

        # 4. Test complex rule matching
        complex_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 10, 4),
            amount=200.0,
            description="Facebook marketing campaign",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            tags=["facebook", "ads"],
        )

        result = categorizer.categorize_transaction(complex_transaction)
        assert result.assigned_category == ExpenseCategory.MARKETING
        assert result.matched_rule.name == "Complex Rule"

        # 5. Test rule priority
        # This transaction matches both Keyword and Complex rule,
        # but Complex rule has higher priority
        priority_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 10, 5),
            amount=150.0,
            description="Software subscription for marketing",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
            tags=["facebook"],
        )

        result = categorizer.categorize_transaction(priority_transaction)
        assert result.assigned_category == ExpenseCategory.MARKETING
        assert result.matched_rule.name == "Complex Rule"
