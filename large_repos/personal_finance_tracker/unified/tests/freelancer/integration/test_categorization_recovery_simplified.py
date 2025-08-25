"""Simplified tests for recovery from categorization errors discovered months later."""

from datetime import datetime, timedelta
import uuid

import pytest

from personal_finance_tracker.models.common import (
    ExpenseCategory,
    Transaction,
    TransactionType,
)
from personal_finance_tracker.expense.models import (
    CategorizationRule,
    CategorizationResult,
    AuditRecord,
)
from personal_finance_tracker.expense.categorizer import ExpenseCategorizer
from personal_finance_tracker.tax.tax_manager import TaxManager
from personal_finance_tracker.tax.models import TaxJurisdiction, FilingStatus


class TestCategorizationRecoverySimplified:
    """Test suite for handling recovery from categorization errors."""

    def test_recover_from_delayed_categorization_errors(self):
        """Test finding and correcting categorization errors months later."""
        # Create expense categorizer
        categorizer = ExpenseCategorizer()
        
        # Add rules
        business_rule = CategorizationRule(
            name="Business Expense Rule",
            category=ExpenseCategory.BUSINESS_SUPPLIES,
            keyword_patterns=["business", "supplies", "equipment"],
            business_use_percentage=100.0,
            priority=10,
        )
        
        categorizer.add_categorization_rule(business_rule)
        
        # Create a transaction
        equipment_tx = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 1, 15),
            amount=1200.0,
            description="Equipment purchase",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )
        
        # Apply categorization
        results = categorizer.categorize_transactions([equipment_tx])
        
        # Verify transaction matches rule based on "equipment" keyword
        assert len(results) == 1
        assert results[0].transaction_id == equipment_tx.id
        assert results[0].assigned_category == ExpenseCategory.BUSINESS_SUPPLIES
        assert results[0].business_use_percentage == 100.0
        
        # Apply the categorization
        categorized_tx = categorizer.apply_categorization(equipment_tx, results[0])
        
        # Verify the transaction is now categorized
        assert categorized_tx.category == ExpenseCategory.BUSINESS_SUPPLIES
        assert categorized_tx.business_use_percentage == 100.0
        
        # Simulate misclassification by manually changing it to personal
        misclassified_tx = Transaction(
            id=categorized_tx.id,
            date=categorized_tx.date,
            amount=categorized_tx.amount,
            description=categorized_tx.description,
            transaction_type=categorized_tx.transaction_type,
            account_id=categorized_tx.account_id,
            category=ExpenseCategory.PERSONAL,
            business_use_percentage=0.0,
        )
        
        # Set up tax manager for tax impact comparison
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # Create an income transaction
        income_tx = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 1, 10),
            amount=8000.0,
            description="Client payment",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        )
        
        # Calculate tax with miscategorized transaction
        tax_before = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=income_tx.amount,  # No business expense deduction
            ytd_taxable_income=income_tx.amount,
            tax_year=2022,
            quarter=1,
        )
        
        # Now correct the categorization
        corrected_tx = categorizer.correct_categorization(
            misclassified_tx,
            new_category=ExpenseCategory.BUSINESS_SUPPLIES,
            new_business_percentage=100.0,
        )
        
        # Verify correction worked
        assert corrected_tx.category == ExpenseCategory.BUSINESS_SUPPLIES
        assert corrected_tx.business_use_percentage == 100.0
        
        # Calculate tax after correction
        tax_after = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=income_tx.amount - corrected_tx.amount,  # With business expense deduction
            ytd_taxable_income=income_tx.amount - corrected_tx.amount,
            tax_year=2022,
            quarter=1,
        )
        
        # Tax should be lower after correction
        assert tax_after.payment_amount < tax_before.payment_amount
        
        # Verify audit trail exists
        audit_trail = categorizer.get_audit_trail()
        assert len(audit_trail) >= 1

    def test_recover_from_multiple_categorization_errors(self):
        """Test correcting multiple categorization errors at once."""
        # Create expense categorizer
        categorizer = ExpenseCategorizer()
        
        # Add rules
        rules = [
            CategorizationRule(
                name="Software Rule",
                category=ExpenseCategory.SOFTWARE,
                keyword_patterns=["software", "subscription"],
                business_use_percentage=100.0,
                priority=10,
            ),
            CategorizationRule(
                name="Office Rule",
                category=ExpenseCategory.BUSINESS_SUPPLIES,
                keyword_patterns=["office", "supplies"],
                business_use_percentage=100.0,
                priority=5,
            ),
            CategorizationRule(
                name="Phone Rule",
                category=ExpenseCategory.PHONE,
                keyword_patterns=["phone", "mobile"],
                business_use_percentage=80.0,
                priority=8,
            ),
        ]
        
        for rule in rules:
            categorizer.add_categorization_rule(rule)
        
        # Create several transactions that should be business expenses
        transactions = [
            # Software expense
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 10),
                amount=500.0,
                description="Software subscription renewal",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
            ),
            # Office supplies
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 15),
                amount=300.0,
                description="Office supplies purchase",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
            ),
            # Phone expense
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 1, 20),
                amount=100.0,
                description="Mobile phone bill",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
            ),
        ]
        
        # Categorize transactions
        results = categorizer.categorize_transactions(transactions)
        
        # Apply categorizations
        categorized_txs = []
        for tx in transactions:
            for result in results:
                if result.transaction_id == tx.id:
                    categorized_tx = categorizer.apply_categorization(tx, result)
                    categorized_txs.append(categorized_tx)
                    break
        
        # Verify all transactions were categorized correctly
        assert categorized_txs[0].category == ExpenseCategory.SOFTWARE
        assert categorized_txs[1].category == ExpenseCategory.BUSINESS_SUPPLIES
        assert categorized_txs[2].category == ExpenseCategory.PHONE
        
        # Now simulate that all were miscategorized as personal
        miscategorized_txs = []
        for tx in categorized_txs:
            miscategorized_tx = Transaction(
                id=tx.id,
                date=tx.date,
                amount=tx.amount,
                description=tx.description,
                transaction_type=tx.transaction_type,
                account_id=tx.account_id,
                category=ExpenseCategory.PERSONAL,
                business_use_percentage=0.0,
            )
            miscategorized_txs.append(miscategorized_tx)
        
        # Set up tax manager
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # Create income transaction
        income_tx = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 1, 5),
            amount=10000.0,
            description="Client payment",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        )
        
        # Calculate tax with miscategorized transactions
        taxable_income_before = income_tx.amount  # No deductions
        tax_before = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=taxable_income_before,
            ytd_taxable_income=taxable_income_before,
            tax_year=2022,
            quarter=1,
        )
        
        # Now recategorize each transaction correctly
        corrected_txs = []
        corrected_txs.append(categorizer.correct_categorization(
            miscategorized_txs[0],
            new_category=ExpenseCategory.SOFTWARE,
            new_business_percentage=100.0,
        ))
        
        corrected_txs.append(categorizer.correct_categorization(
            miscategorized_txs[1],
            new_category=ExpenseCategory.BUSINESS_SUPPLIES,
            new_business_percentage=100.0,
        ))
        
        corrected_txs.append(categorizer.correct_categorization(
            miscategorized_txs[2],
            new_category=ExpenseCategory.PHONE,
            new_business_percentage=80.0,
        ))
        
        # Verify all were corrected
        assert corrected_txs[0].category == ExpenseCategory.SOFTWARE
        assert corrected_txs[1].category == ExpenseCategory.BUSINESS_SUPPLIES
        assert corrected_txs[2].category == ExpenseCategory.PHONE
        
        # Calculate business expense deduction
        business_expenses = sum(
            tx.amount * (tx.business_use_percentage / 100.0)
            for tx in corrected_txs
        )
        
        # Calculate tax after correction
        taxable_income_after = income_tx.amount - business_expenses
        tax_after = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=taxable_income_after,
            ytd_taxable_income=taxable_income_after,
            tax_year=2022,
            quarter=1,
        )
        
        # Tax should be lower after correction
        assert tax_after.payment_amount < tax_before.payment_amount
        
        # Generate expense summary to verify categorization
        expense_summary = categorizer.generate_expense_summary(
            corrected_txs,
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 1, 31),
        )
        
        # Verify expense summary
        assert expense_summary.total_expenses > 0
        assert expense_summary.business_expenses > 0
        assert expense_summary.business_expenses < expense_summary.total_expenses  # Due to phone being 80%