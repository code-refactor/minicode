"""Tests for recovery from categorization errors discovered months later."""

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


class TestCategorizationRecovery:
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
        
        # Create transactions for Q1 2022
        transactions = []
        
        # Transaction that should be business but will be miscategorized as personal
        miscategorized_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 1, 15),
            amount=1200.0,
            description="Equipment purchase",  # Contains "equipment" keyword, will be categorized as business
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )
        
        # Correctly categorized transaction
        correct_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 1, 20),
            amount=500.0,
            description="Business supplies purchase",
            transaction_type=TransactionType.EXPENSE,
            account_id="checking123",
        )
        
        # Income transaction
        income_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 1, 10),
            amount=8000.0,
            description="Client payment",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        )
        
        transactions.extend([miscategorized_transaction, correct_transaction, income_transaction])
        
        # Apply initial categorization
        categorization_results = categorizer.categorize_transactions(transactions)
        
        categorized_transactions = []
        for transaction in transactions:
            if transaction.transaction_type == TransactionType.EXPENSE:
                # Find matching result
                for result in categorization_results:
                    if result.transaction_id == transaction.id:
                        transaction = categorizer.apply_categorization(transaction, result)
                        break
            categorized_transactions.append(transaction)
        
        # Verify the transaction is categorized due to matching the 'equipment' keyword
        # The categorizer recognizes 'Equipment' from our business rule and assigns BUSINESS_SUPPLIES
        categorized_tx = next(t for t in categorized_transactions
                            if t.id == miscategorized_transaction.id)
        assert categorized_tx.category == ExpenseCategory.BUSINESS_SUPPLIES
        assert categorized_tx.business_use_percentage == 100.0
        
        # For testing purposes, let's simulate that this transaction was misclassified as personal
        # by manually changing it back - this simulates the scenario in the test name
        misclassified_tx = Transaction(
            id=categorized_tx.id,
            date=categorized_tx.date,
            amount=categorized_tx.amount,
            description=categorized_tx.description,
            transaction_type=categorized_tx.transaction_type,
            account_id=categorized_tx.account_id,
            category=ExpenseCategory.PERSONAL,  # Manually set to personal to simulate miscategorization
            business_use_percentage=0.0,        # Set to 0% business use
        )
        
        # Replace in our list
        updated_categorized_transactions = []
        for transaction in categorized_transactions:
            if transaction.id == misclassified_tx.id:
                updated_categorized_transactions.append(misclassified_tx)
            else:
                updated_categorized_transactions.append(transaction)
        
        # Set up tax manager to calculate initial tax
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # Calculate initial tax (with error)
        initial_income = sum(t.amount for t in updated_categorized_transactions 
                             if t.transaction_type == TransactionType.INCOME)
        initial_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0) 
            for t in updated_categorized_transactions 
            if t.transaction_type == TransactionType.EXPENSE 
            and t.business_use_percentage is not None
        )
        initial_taxable_income = initial_income - initial_expenses
        
        # Calculate tax with the TaxManager
        initial_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=initial_taxable_income,
            ytd_taxable_income=initial_taxable_income,
            tax_year=2022,
            quarter=1
        )
        initial_tax_amount = initial_tax.payment_amount
        
        # Simulate discovering error months later (e.g., during tax preparation)
        # We're now in Q2, reviewing Q1 data
        current_date = datetime(2022, 4, 15)
        
        # Find transactions in Q1 that might be miscategorized
        start_of_q1 = datetime(2022, 1, 1)
        end_of_q1 = datetime(2022, 3, 31)
        
        # Search for potentially miscategorized transactions
        q1_transactions = [t for t in updated_categorized_transactions 
                         if start_of_q1 <= t.date <= end_of_q1]
                         
        # Identify transactions that might need review
        suspicious_transactions = [t for t in q1_transactions 
                                if t.transaction_type == TransactionType.EXPENSE
                                and t.category == ExpenseCategory.PERSONAL
                                and t.amount > 1000.0]
        
        # Verify we identified the miscategorized transaction
        assert len(suspicious_transactions) == 1
        assert suspicious_transactions[0].id == misclassified_tx.id
        
        # Correct the categorization with manual review
        corrected_transaction = categorizer.correct_categorization(
            suspicious_transactions[0],
            new_category=ExpenseCategory.BUSINESS_SUPPLIES,
            new_business_percentage=100.0
        )
        
        # Replace the transaction in our list
        final_transactions = []
        for transaction in updated_categorized_transactions:
            if transaction.id == corrected_transaction.id:
                final_transactions.append(corrected_transaction)
            else:
                final_transactions.append(transaction)
        
        # Recalculate tax with corrected categorization
        corrected_income = sum(t.amount for t in final_transactions 
                              if t.transaction_type == TransactionType.INCOME)
        corrected_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0) 
            for t in final_transactions 
            if t.transaction_type == TransactionType.EXPENSE 
            and t.business_use_percentage is not None
        )
        corrected_taxable_income = corrected_income - corrected_expenses
        
        # Calculate tax with the TaxManager
        corrected_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=corrected_taxable_income,
            ytd_taxable_income=corrected_taxable_income,
            tax_year=2022,
            quarter=1
        )
        corrected_tax_amount = corrected_tax.payment_amount
        
        # Assert that the corrected tax is lower because we're deducting more expenses
        assert corrected_tax_amount < initial_tax_amount
        
        # Verify audit trail records the change
        audit_trail = categorizer.get_audit_trail()
        assert len(audit_trail) >= 3  # Initial categorizations + correction
        
        # Verify the latest audit record is for the correction
        correction_records = [record for record in audit_trail 
                            if record.action == "correct_categorization" 
                            and record.transaction_id == misclassified_tx.id]
        
        assert len(correction_records) == 1
        assert correction_records[0].previous_state["category"] == ExpenseCategory.PERSONAL
        assert correction_records[0].new_state["category"] == ExpenseCategory.BUSINESS_SUPPLIES
        
    def test_recover_from_multiple_categorization_errors(self):
        """Test recovering from multiple categorization errors discovered later."""
        categorizer = ExpenseCategorizer()
        
        # Add categorization rules
        rules = [
            CategorizationRule(
                name="Software Rule",
                category=ExpenseCategory.SOFTWARE,
                keyword_patterns=["software", "subscription"],
                business_use_percentage=100.0,
                priority=10,
            ),
            CategorizationRule(
                name="Marketing Rule",
                category=ExpenseCategory.MARKETING,
                keyword_patterns=["marketing", "advertising", "promotion"],
                business_use_percentage=100.0,
                priority=8,
            ),
            CategorizationRule(
                name="Meal Rule",
                category=ExpenseCategory.MEALS,
                keyword_patterns=["meal", "restaurant", "dining"],
                business_use_percentage=50.0,  # 50% business use for meals
                priority=5,
            ),
        ]
        
        for rule in rules:
            categorizer.add_categorization_rule(rule)
        
        # Create transactions that will be manually miscategorized for testing
        transactions = []
        
        # Two transactions we'll manually miscategorize
        miscategorized_transactions = [
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 2, 10),
                amount=200.0,
                description="Adobe CC subscription",  # Should be SOFTWARE but we'll set as PERSONAL
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.PERSONAL,  # Manually set
                business_use_percentage=0.0,        # Manually set
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 2, 15),
                amount=500.0,
                description="Facebook ads campaign",  # Should be MARKETING but we'll set as PERSONAL
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.PERSONAL,  # Manually set
                business_use_percentage=0.0,        # Manually set
            ),
        ]
        
        # Correctly categorized transactions
        correct_transactions = [
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 2, 5),
                amount=100.0,
                description="Software subscription for design tools",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.SOFTWARE,
                business_use_percentage=100.0,
            ),
            Transaction(
                id=uuid.uuid4(),
                date=datetime(2022, 2, 20),
                amount=80.0,
                description="Client lunch meeting at restaurant",
                transaction_type=TransactionType.EXPENSE,
                account_id="checking123",
                category=ExpenseCategory.MEALS,
                business_use_percentage=50.0,
            ),
        ]
        
        # Income transaction
        income_transaction = Transaction(
            id=uuid.uuid4(),
            date=datetime(2022, 2, 1),
            amount=6000.0,
            description="Client payment",
            transaction_type=TransactionType.INCOME,
            account_id="checking123",
        )
        
        transactions.extend(miscategorized_transactions)
        transactions.extend(correct_transactions)
        transactions.append(income_transaction)
        
        # No need to run categorization since we've manually set the categories
        categorized_transactions = transactions
        
        # Create receipts with correct metadata
        receipts = {
            miscategorized_transactions[0].id: {
                "filename": "adobe_receipt.pdf",
                "merchant": "Adobe Inc.",
                "category": "Software",
                "date": datetime(2022, 2, 10),
            },
            miscategorized_transactions[1].id: {
                "filename": "facebook_ads_receipt.pdf",
                "merchant": "Facebook Ads",
                "category": "Marketing",
                "date": datetime(2022, 2, 15),
            },
        }
        
        # Simulate discovering errors during receipt scanning months later
        # We're now in Q3, reviewing Q1 and Q2 data for tax preparation
        current_date = datetime(2022, 7, 15)
        
        # Process receipts and identify discrepancies
        corrections = []
        
        for transaction in categorized_transactions:
            if transaction.id in receipts:
                receipt_info = receipts[transaction.id]
                
                # Process receipts - both need correction
                if receipt_info["category"] == "Software":
                    corrections.append({
                        "transaction": transaction,
                        "correct_category": ExpenseCategory.SOFTWARE,
                        "business_percentage": 100.0,
                        "receipt": receipt_info["filename"],
                    })
                elif receipt_info["category"] == "Marketing":
                    corrections.append({
                        "transaction": transaction,
                        "correct_category": ExpenseCategory.MARKETING,
                        "business_percentage": 100.0,
                        "receipt": receipt_info["filename"],
                    })
        
        # Verify we identified both miscategorized transactions
        assert len(corrections) == 2
        
        # Apply corrections
        corrected_transactions = []
        for correction in corrections:
            corrected_tx = categorizer.correct_categorization(
                correction["transaction"],
                new_category=correction["correct_category"],
                new_business_percentage=correction["business_percentage"]
            )
            corrected_transactions.append(corrected_tx)
        
        # Update transactions list with corrections
        final_transactions = []
        for transaction in categorized_transactions:
            # Check if this transaction was corrected
            corrected = next((t for t in corrected_transactions if t.id == transaction.id), None)
            if corrected:
                final_transactions.append(corrected)
            else:
                final_transactions.append(transaction)
        
        # Set up tax manager to calculate tax impact
        tax_manager = TaxManager(FilingStatus.SINGLE)
        tax_manager.load_default_brackets()
        
        # Calculate initial tax (with errors)
        initial_income = sum(t.amount for t in categorized_transactions 
                            if t.transaction_type == TransactionType.INCOME)
        initial_business_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0) 
            for t in categorized_transactions 
            if t.transaction_type == TransactionType.EXPENSE 
            and hasattr(t, 'business_use_percentage')
        )
        
        initial_taxable_income = initial_income - initial_business_expenses
        
        # Calculate tax with the TaxManager
        initial_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=initial_taxable_income,
            ytd_taxable_income=initial_taxable_income,
            tax_year=2022,
            quarter=1
        )
        initial_tax_amount = initial_tax.payment_amount
        
        # Calculate corrected tax
        corrected_income = sum(t.amount for t in final_transactions 
                              if t.transaction_type == TransactionType.INCOME)
        corrected_business_expenses = sum(
            t.amount * (t.business_use_percentage / 100.0) 
            for t in final_transactions 
            if t.transaction_type == TransactionType.EXPENSE 
            and hasattr(t, 'business_use_percentage')
        )
        
        corrected_taxable_income = corrected_income - corrected_business_expenses
        
        # Calculate tax with the TaxManager
        corrected_tax = tax_manager.calculate_quarterly_tax_payment(
            quarterly_taxable_income=corrected_taxable_income,
            ytd_taxable_income=corrected_taxable_income,
            tax_year=2022,
            quarter=1
        )
        corrected_tax_amount = corrected_tax.payment_amount
        
        # Assert that the corrected tax is lower or equal
        assert corrected_tax_amount <= initial_tax_amount
        
        # Calculate the tax savings
        tax_savings = initial_tax_amount - corrected_tax_amount
        assert tax_savings >= 0  # May be zero in some edge cases
        
        # Verify audit trail records all corrections
        audit_trail = categorizer.get_audit_trail()
        correction_records = [record for record in audit_trail if record.action == "correct_categorization"]
        
        assert len(correction_records) == 2
        
        # Check if we can find the correct transaction in the final list
        for corrected_tx in corrected_transactions:
            found_tx = next((tx for tx in final_transactions if tx.id == corrected_tx.id), None)
            assert found_tx is not None
            assert found_tx.category == corrected_tx.category
            assert found_tx.business_use_percentage == corrected_tx.business_use_percentage