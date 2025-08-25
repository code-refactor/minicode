"""Tax management engine for freelancers."""

import calendar
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union

import pandas as pd
from pydantic import BaseModel

from personal_finance_tracker.models.common import (
    Transaction,
    TransactionType,
    TaxPayment,
    TaxRate,
    TaxDeduction,
)

from personal_finance_tracker.tax.models import (
    FilingStatus,
    TaxJurisdiction,
    QuarterInfo,
    TaxBracket,
    TaxLiability,
    EstimatedPayment,
    TaxYearSummary,
)


class TaxManager:
    """
    Tax management engine for freelancers.

    This class handles tax calculations, estimated payment scheduling,
    and tax optimization for freelancers.
    """

    def __init__(self, filing_status: FilingStatus = FilingStatus.SINGLE):
        """
        Initialize the tax manager.

        Args:
            filing_status: Tax filing status
        """
        self.filing_status = filing_status
        self._tax_brackets = {}  # Cache for tax brackets
        self._se_tax_rate = 15.3  # Self-employment tax rate (percentage)
        self._se_tax_income_limit = 147000  # For 2022 (Social Security wage base)
        self._standard_deduction = {
            2022: {
                FilingStatus.SINGLE: 12950,
                FilingStatus.MARRIED_JOINT: 25900,
                FilingStatus.MARRIED_SEPARATE: 12950,
                FilingStatus.HEAD_OF_HOUSEHOLD: 19400,
            }
        }

    def set_tax_brackets(self, brackets: List[TaxBracket]) -> None:
        """
        Set tax brackets for calculations.

        Args:
            brackets: List of tax brackets
        """
        # Index brackets by jurisdiction, year, and filing status
        for bracket in brackets:
            key = (bracket.jurisdiction, bracket.tax_year, bracket.filing_status)
            self._tax_brackets[key] = bracket

    def get_tax_brackets(
        self,
        jurisdiction: TaxJurisdiction,
        tax_year: int,
        filing_status: Optional[FilingStatus] = None,
    ) -> Optional[TaxBracket]:
        """
        Get tax brackets for a specific jurisdiction and year.

        Args:
            jurisdiction: Tax jurisdiction
            tax_year: Tax year
            filing_status: Filing status (defaults to instance filing status)

        Returns:
            Tax bracket if found, None otherwise
        """
        status = filing_status or self.filing_status
        key = (jurisdiction, tax_year, status)
        return self._tax_brackets.get(key)

    def load_default_brackets(self) -> None:
        """Load default tax brackets for common jurisdictions."""
        # 2022 federal tax brackets (simplified example)
        federal_single = TaxBracket(
            jurisdiction=TaxJurisdiction.FEDERAL,
            filing_status=FilingStatus.SINGLE,
            tax_year=2022,
            income_thresholds=[0, 10275, 41775, 89075, 170050, 215950, 539900],
            rates=[10, 12, 22, 24, 32, 35, 37],
        )

        federal_married_joint = TaxBracket(
            jurisdiction=TaxJurisdiction.FEDERAL,
            filing_status=FilingStatus.MARRIED_JOINT,
            tax_year=2022,
            income_thresholds=[0, 20550, 83550, 178150, 340100, 431900, 647850],
            rates=[10, 12, 22, 24, 32, 35, 37],
        )

        self.set_tax_brackets([federal_single, federal_married_joint])

    def calculate_tax_quarters(self, tax_year: int) -> List[QuarterInfo]:
        """
        Calculate tax quarter information for a specific year.

        Args:
            tax_year: Tax year

        Returns:
            List of tax quarter information
        """
        quarters = []

        # First quarter: January 1 - March 31, due April 15
        q1_start = datetime(tax_year, 1, 1)
        q1_end = datetime(tax_year, 3, 31)
        q1_due = datetime(tax_year, 4, 15)

        # Second quarter: April 1 - May 31, due June 15
        q2_start = datetime(tax_year, 4, 1)
        q2_end = datetime(tax_year, 5, 31)
        q2_due = datetime(tax_year, 6, 15)

        # Third quarter: June 1 - August 31, due September 15
        q3_start = datetime(tax_year, 6, 1)
        q3_end = datetime(tax_year, 8, 31)
        q3_due = datetime(tax_year, 9, 15)

        # Fourth quarter: September 1 - December 31, due January 15 of next year
        q4_start = datetime(tax_year, 9, 1)
        q4_end = datetime(tax_year, 12, 31)
        q4_due = datetime(tax_year + 1, 1, 15)

        quarters = [
            QuarterInfo(
                year=tax_year,
                quarter=1,
                start_date=q1_start,
                end_date=q1_end,
                due_date=q1_due,
                description=f"Q1 {tax_year} (Jan-Mar)",
            ),
            QuarterInfo(
                year=tax_year,
                quarter=2,
                start_date=q2_start,
                end_date=q2_end,
                due_date=q2_due,
                description=f"Q2 {tax_year} (Apr-May)",
            ),
            QuarterInfo(
                year=tax_year,
                quarter=3,
                start_date=q3_start,
                end_date=q3_end,
                due_date=q3_due,
                description=f"Q3 {tax_year} (Jun-Aug)",
            ),
            QuarterInfo(
                year=tax_year,
                quarter=4,
                start_date=q4_start,
                end_date=q4_end,
                due_date=q4_due,
                description=f"Q4 {tax_year} (Sep-Dec)",
            ),
        ]

        return quarters

    def get_current_quarter(self) -> QuarterInfo:
        """
        Get the current tax quarter information.

        Returns:
            Information about the current tax quarter
        """
        today = datetime.now()
        year = today.year

        quarters = self.calculate_tax_quarters(year)

        # Find the current quarter
        for quarter in quarters:
            if quarter.start_date <= today <= quarter.end_date:
                return quarter

        # If not found (shouldn't happen), return the last quarter of the year
        return quarters[-1]

    def calculate_taxable_income(
        self,
        transactions: List[Transaction],
        tax_year: int,
        deductions: List[TaxDeduction] = None,
    ) -> Tuple[float, float, float]:
        """
        Calculate taxable income for a tax year.

        Args:
            transactions: List of all transactions
            tax_year: Tax year to calculate for
            deductions: List of tax deductions

        Returns:
            Tuple of (total income, total deductions, taxable income)
        """
        # Filter transactions to the tax year
        year_start = datetime(tax_year, 1, 1)
        year_end = datetime(tax_year, 12, 31, 23, 59, 59)

        year_transactions = [
            t for t in transactions if year_start <= t.date <= year_end
        ]

        # Calculate total income
        income_transactions = [
            t for t in year_transactions if t.transaction_type == TransactionType.INCOME
        ]
        total_income = sum(t.amount for t in income_transactions)

        # Calculate business expenses
        expense_transactions = [
            t
            for t in year_transactions
            if (
                t.transaction_type == TransactionType.EXPENSE
                and t.category is not None
                and t.category.name != "PERSONAL"
                and t.business_use_percentage is not None
            )
        ]

        total_expenses = sum(
            t.amount * (t.business_use_percentage / 100) for t in expense_transactions
        )

        # Add additional deductions
        additional_deductions = 0.0
        if deductions:
            additional_deductions = sum(d.amount for d in deductions)

        # Get standard deduction
        std_deduction = self._standard_deduction.get(tax_year, {}).get(
            self.filing_status,
            12950,  # Default to 2022 single
        )

        # Calculate total deductions (greater of itemized or standard)
        total_deductions = max(total_expenses + additional_deductions, std_deduction)

        # Calculate taxable income
        taxable_income = max(0, total_income - total_deductions)

        return total_income, total_deductions, taxable_income

    def calculate_federal_tax(
        self,
        taxable_income: float,
        tax_year: int,
        filing_status: Optional[FilingStatus] = None,
    ) -> float:
        """
        Calculate federal income tax.

        Args:
            taxable_income: Taxable income amount
            tax_year: Tax year
            filing_status: Filing status (defaults to instance filing status)

        Returns:
            Federal tax amount
        """
        # Get tax brackets
        status = filing_status or self.filing_status
        brackets = self.get_tax_brackets(TaxJurisdiction.FEDERAL, tax_year, status)

        if not brackets:
            raise ValueError(f"No federal tax brackets for {tax_year} and {status}")

        # Calculate tax
        tax = 0.0
        prev_threshold = 0.0

        for i, threshold in enumerate(brackets.income_thresholds):
            rate = brackets.rates[i] / 100  # Convert percentage to decimal

            if taxable_income <= threshold:
                tax += (taxable_income - prev_threshold) * rate
                break
            else:
                tax += (threshold - prev_threshold) * rate

            prev_threshold = threshold

            # If this is the last bracket, calculate tax on remaining income
            if i == len(brackets.income_thresholds) - 1:
                tax += (taxable_income - threshold) * rate

        return tax

    def calculate_self_employment_tax(self, net_business_income: float) -> float:
        """
        Calculate self-employment tax.

        Args:
            net_business_income: Net business income

        Returns:
            Self-employment tax amount
        """
        # SE tax is calculated on 92.35% of net business income
        taxable_income = net_business_income * 0.9235

        # Social Security portion (12.4%) is subject to wage base limit
        social_security_portion = min(taxable_income, self._se_tax_income_limit) * 0.124

        # Medicare portion (2.9%) applies to all income
        medicare_portion = taxable_income * 0.029

        # Additional Medicare Tax (0.9%) on income above threshold
        # (simplified - would normally depend on filing status)
        additional_medicare = max(0, taxable_income - 200000) * 0.009

        return social_security_portion + medicare_portion + additional_medicare

    def calculate_tax_liability(
        self,
        income: Optional[float] = None,
        transactions: Optional[List[Transaction]] = None,
        tax_year: int = datetime.now().year,
        deductions: List[TaxDeduction] = None,
        include_state: bool = True,
        jurisdiction: TaxJurisdiction = TaxJurisdiction.FEDERAL,
    ) -> TaxLiability:
        """
        Calculate total tax liability.

        Args:
            transactions: List of all transactions
            tax_year: Tax year to calculate for
            deductions: List of tax deductions
            include_state: Whether to include state tax calculations

        Returns:
            TaxLiability object with detailed tax information
        """
        # Performance measurement
        start_time = time.time()

        # Calculate taxable income
        if income is not None:
            # Direct income provided
            total_income = income
            # Use standard deduction as default
            std_deduction = self._standard_deduction.get(tax_year, {}).get(
                self.filing_status,
                12950,  # Default to 2022 single
            )
            total_deductions = std_deduction
            taxable_income = max(0, total_income - total_deductions)
        elif transactions is not None:
            # Calculate from transactions
            total_income, total_deductions, taxable_income = self.calculate_taxable_income(
                transactions, tax_year, deductions
            )
        else:
            raise ValueError("Either income or transactions must be provided")

        # Calculate federal income tax
        federal_tax = self.calculate_federal_tax(taxable_income, tax_year)

        # Calculate self-employment tax
        # For this example, assume all income is business income
        self_employment_tax = self.calculate_self_employment_tax(
            total_income - total_deductions
        )

        # Calculate state tax (simplified example)
        state_tax = 0.0
        if include_state:
            # Simplified: assume 5% flat state tax
            state_tax = taxable_income * 0.05

        # Calculate total tax
        total_tax = federal_tax + self_employment_tax + state_tax

        # Calculate effective and marginal rates
        effective_rate = 0.0
        if total_income > 0:
            effective_rate = (total_tax / total_income) * 100

        # Get federal brackets to determine marginal rate
        brackets = self.get_tax_brackets(
            TaxJurisdiction.FEDERAL, tax_year, self.filing_status
        )
        marginal_rate = 0.0

        if brackets:
            for i, threshold in enumerate(brackets.income_thresholds):
                if i < len(brackets.income_thresholds) - 1:
                    if taxable_income < brackets.income_thresholds[i + 1]:
                        marginal_rate = brackets.rates[i]
                        break
                else:
                    marginal_rate = brackets.rates[i]

        # Create detailed breakdown
        breakdown = {
            "federal_income_tax": federal_tax,
            "self_employment_tax": self_employment_tax,
            "state_tax": state_tax,
            "total_tax": total_tax,
        }

        # Create tax liability object
        liability = TaxLiability(
            jurisdiction=TaxJurisdiction.FEDERAL,  # Primary jurisdiction
            tax_year=tax_year,
            income=total_income,
            deductions=total_deductions,
            taxable_income=taxable_income,
            tax_amount=total_tax,
            effective_rate=effective_rate,
            marginal_rate=marginal_rate,
            filing_status=self.filing_status,
            breakdown=breakdown,
        )

        # Verify performance requirement
        elapsed_time = time.time() - start_time
        if elapsed_time > 1.0:
            print(
                f"Warning: Tax liability calculation took {elapsed_time:.2f} seconds, which exceeds the 1 second requirement"
            )

        return liability

    def calculate_quarterly_tax_payment(
        self,
        quarterly_taxable_income: float,
        ytd_taxable_income: float,
        tax_year: int,
        quarter: int,
        prior_payments: float = 0.0,
    ) -> EstimatedPayment:
        """
        Calculate estimated quarterly tax payment.

        Args:
            quarterly_taxable_income: Taxable income for the quarter
            ytd_taxable_income: Year-to-date taxable income
            tax_year: Tax year
            quarter: Quarter number (1-4)
            prior_payments: Sum of prior payments made this year

        Returns:
            EstimatedPayment object with payment details
        """
        # Get quarter information
        quarters = self.calculate_tax_quarters(tax_year)
        quarter_info = next((q for q in quarters if q.quarter == quarter), None)
        
        if not quarter_info:
            raise ValueError(f"Invalid quarter: {quarter}")
            
        # Calculate federal tax on YTD income
        ytd_federal_tax = self.calculate_federal_tax(ytd_taxable_income, tax_year)
        
        # Calculate self-employment tax on YTD income (simplified)
        ytd_se_tax = ytd_taxable_income * 0.15  # Approximate SE tax rate
        
        # Total YTD liability
        ytd_liability = ytd_federal_tax + ytd_se_tax
        
        # Calculate payment based on quarter
        if quarter == 1:
            # First quarter - pay 25% of projected annual tax
            payment_amount = ytd_liability * 0.25
        else:
            # For later quarters, adjust for prior payments
            remaining_liability = ytd_liability - prior_payments
            remaining_quarters = 5 - quarter  # Quarters remaining including current
            
            if remaining_quarters <= 0:
                # Last quarter or past end of year
                payment_amount = remaining_liability
            else:
                payment_amount = remaining_liability / remaining_quarters
                
        # Calculate safe harbor amount (simplified)
        safe_harbor = ytd_liability * 0.225  # 90% of annual tax / 4
        
        # Create estimated payment object with federal tax component for test compatibility
        payment = EstimatedPayment(
            tax_year=tax_year,
            quarter=quarter,
            jurisdiction=TaxJurisdiction.FEDERAL,
            due_date=quarter_info.due_date,
            payment_amount=max(0, payment_amount),
            minimum_required=max(0, min(payment_amount, safe_harbor)),
            safe_harbor_amount=safe_harbor,
            year_to_date_liability=ytd_liability,
            previous_payments=prior_payments,
            federal_tax=ytd_federal_tax * (quarter/4),
            self_employment_tax=ytd_se_tax * (quarter/4),
            notes=f"Estimated Q{quarter} tax payment for {tax_year}",
        )
        
        return payment
    
    def calculate_estimated_payment(
        self,
        transactions: List[Transaction],
        payments: List[TaxPayment],
        tax_year: int,
        quarter: int,
        deductions: List[TaxDeduction] = None,
    ) -> EstimatedPayment:
        """
        Calculate estimated quarterly tax payment.

        Args:
            transactions: List of all transactions
            payments: Previous tax payments
            tax_year: Tax year
            quarter: Quarter number (1-4)
            deductions: List of tax deductions

        Returns:
            EstimatedPayment object with payment details
        """
        # Get quarter information
        quarters = self.calculate_tax_quarters(tax_year)
        quarter_info = next((q for q in quarters if q.quarter == quarter), None)

        if not quarter_info:
            raise ValueError(f"Invalid quarter: {quarter}")

        # Calculate year-to-date liability
        ytd_transactions = [
            t
            for t in transactions
            if t.date.year == tax_year and t.date <= quarter_info.end_date
        ]

        liability = self.calculate_tax_liability(ytd_transactions, tax_year, deductions)

        # Get previous payments for this year
        previous_payments_total = sum(
            p.amount for p in payments if p.tax_year == tax_year and p.quarter < quarter
        )

        # Calculate required payment
        # Basic rule: Pay 25% of annual liability each quarter
        annual_projection = liability.tax_amount * (4 / quarter)  # Simple extrapolation

        # Simplistic approach for safe harbor (for illustration)
        # Safe harbor is typically 100% of previous year tax or 90% of current year
        safe_harbor = (
            annual_projection * 0.9 / 4
        )  # 90% of projected annual tax divided by 4

        # Required payment is remaining liability divided by remaining quarters
        remaining_liability = liability.tax_amount - previous_payments_total
        remaining_quarters = 5 - quarter  # Quarters remaining including current

        if remaining_quarters <= 0:
            # Last quarter or past end of year
            suggested_amount = remaining_liability
        else:
            suggested_amount = remaining_liability / remaining_quarters

        # Create estimated payment object
        payment = EstimatedPayment(
            tax_year=tax_year,
            quarter=quarter,
            jurisdiction=TaxJurisdiction.FEDERAL,
            due_date=quarter_info.due_date,
            suggested_amount=max(0, suggested_amount),
            minimum_required=max(0, min(suggested_amount, safe_harbor)),
            safe_harbor_amount=safe_harbor,
            year_to_date_liability=liability.tax_amount,
            previous_payments=previous_payments_total,
            notes=f"Estimated Q{quarter} tax payment for {tax_year}",
        )

        return payment

    def record_tax_payment(self, payment: TaxPayment) -> TaxPayment:
        """
        Record a tax payment.

        Args:
            payment: Tax payment to record

        Returns:
            The recorded payment
        """
        # In a real implementation, this would store the payment in a database
        # For this example, we just return the payment
        return payment

    def get_tax_summary(
        self,
        transactions: List[Transaction],
        payments: List[TaxPayment],
        tax_year: int,
        deductions: List[TaxDeduction] = None,
    ) -> TaxYearSummary:
        """
        Generate a summary of tax obligations for a year.

        Args:
            transactions: List of all transactions
            payments: List of tax payments
            tax_year: Tax year
            deductions: List of tax deductions

        Returns:
            TaxYearSummary object with detailed tax information
        """
        # Calculate liability
        liability = self.calculate_tax_liability(transactions, tax_year, deductions)

        # Filter to business transactions for the year
        year_start = datetime(tax_year, 1, 1)
        year_end = datetime(tax_year, 12, 31, 23, 59, 59)

        year_transactions = [
            t for t in transactions if year_start <= t.date <= year_end
        ]

        # Calculate income and expenses
        income_transactions = [
            t for t in year_transactions if t.transaction_type == TransactionType.INCOME
        ]
        total_income = sum(t.amount for t in income_transactions)

        expense_transactions = [
            t
            for t in year_transactions
            if (
                t.transaction_type == TransactionType.EXPENSE
                and t.category is not None
                and t.category.name != "PERSONAL"
                and t.business_use_percentage is not None
            )
        ]
        total_expenses = sum(
            t.amount * (t.business_use_percentage / 100) for t in expense_transactions
        )

        # Get total payments
        year_payments = [p for p in payments if p.tax_year == tax_year]
        total_paid = sum(p.amount for p in year_payments)

        # Create summary
        summary = TaxYearSummary(
            tax_year=tax_year,
            total_income=total_income,
            total_expenses=total_expenses,
            total_deductions=liability.deductions,
            taxable_income=liability.taxable_income,
            total_tax=liability.tax_amount,
            effective_tax_rate=liability.effective_rate,
            federal_tax=liability.breakdown["federal_income_tax"],
            state_tax=liability.breakdown.get("state_tax", 0.0),
            self_employment_tax=liability.breakdown["self_employment_tax"],
            total_paid=total_paid,
            balance_due=max(0, liability.tax_amount - total_paid),
            deductions=deductions or [],
            payments=year_payments,
        )

        return summary

    def compare_tax_years(
        self,
        transactions: List[Transaction],
        payments: List[TaxPayment],
        tax_year1: int,
        tax_year2: int,
        deductions1: List[TaxDeduction] = None,
        deductions2: List[TaxDeduction] = None,
    ) -> Dict[str, float]:
        """
        Compare tax obligations between two years.

        Args:
            transactions: List of all transactions
            payments: List of all payments
            tax_year1: First tax year
            tax_year2: Second tax year
            deductions1: Deductions for first year
            deductions2: Deductions for second year

        Returns:
            Dictionary with comparison metrics
        """
        # Get summaries for both years
        summary1 = self.get_tax_summary(transactions, payments, tax_year1, deductions1)
        summary2 = self.get_tax_summary(transactions, payments, tax_year2, deductions2)

        # Calculate differences
        income_change = summary2.total_income - summary1.total_income
        income_change_pct = (
            (income_change / summary1.total_income * 100)
            if summary1.total_income > 0
            else 0
        )

        expense_change = summary2.total_expenses - summary1.total_expenses
        expense_change_pct = (
            (expense_change / summary1.total_expenses * 100)
            if summary1.total_expenses > 0
            else 0
        )

        tax_change = summary2.total_tax - summary1.total_tax
        tax_change_pct = (
            (tax_change / summary1.total_tax * 100) if summary1.total_tax > 0 else 0
        )

        effective_rate_change = (
            summary2.effective_tax_rate - summary1.effective_tax_rate
        )

        # Create comparison result
        comparison = {
            "income_change": income_change,
            "income_change_pct": income_change_pct,
            "expense_change": expense_change,
            "expense_change_pct": expense_change_pct,
            "tax_change": tax_change,
            "tax_change_pct": tax_change_pct,
            "effective_rate_change": effective_rate_change,
            "year1": summary1.tax_year,
            "year2": summary2.tax_year,
            "year1_tax": summary1.total_tax,
            "year2_tax": summary2.total_tax,
        }

        return comparison

    def optimize_deductions(
        self,
        transactions: List[Transaction],
        potential_deductions: List[TaxDeduction],
        tax_year: int,
        target_liability: Optional[float] = None,
    ) -> List[TaxDeduction]:
        """
        Optimize tax deductions to minimize tax liability.

        Args:
            transactions: List of all transactions
            potential_deductions: List of potential deductions to consider
            tax_year: Tax year
            target_liability: Optional target tax liability

        Returns:
            List of optimized deductions
        """
        # Start with base liability without extra deductions
        base_liability = self.calculate_tax_liability(transactions, tax_year)

        # If no target, simply use all deductions
        if target_liability is None:
            return potential_deductions

        # Sort deductions by amount (largest first)
        sorted_deductions = sorted(
            potential_deductions, key=lambda d: d.amount, reverse=True
        )

        # Start with no deductions
        selected_deductions = []
        current_liability = base_liability.tax_amount

        # Add deductions until target is reached
        for deduction in sorted_deductions:
            # Calculate liability with this deduction
            test_deductions = selected_deductions + [deduction]
            test_liability = self.calculate_tax_liability(
                transactions, tax_year, test_deductions
            )

            # If this reduces liability closer to target, add it
            if abs(test_liability.tax_amount - target_liability) < abs(
                current_liability - target_liability
            ):
                selected_deductions.append(deduction)
                current_liability = test_liability.tax_amount

            # If we've reached or gone below target, stop
            if current_liability <= target_liability:
                break

        return selected_deductions
