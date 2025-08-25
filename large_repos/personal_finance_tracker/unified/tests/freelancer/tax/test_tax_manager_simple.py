"""Simplified tests for the tax management engine."""

from datetime import datetime
import uuid

import pytest

from personal_finance_tracker.tax.models import (
    FilingStatus,
    TaxJurisdiction,
    TaxBracket,
)

from personal_finance_tracker.tax.tax_manager import TaxManager


class TestTaxManagerSimple:
    """Simplified test suite for the TaxManager class."""

    def test_init(self):
        """Test initialization with different filing statuses."""
        # Default initialization
        manager = TaxManager()
        assert manager.filing_status == FilingStatus.SINGLE

        # Initialize with different filing status
        manager = TaxManager(FilingStatus.MARRIED_JOINT)
        assert manager.filing_status == FilingStatus.MARRIED_JOINT

    def test_calculate_tax_quarters(self):
        """Test calculation of tax quarters for a year."""
        manager = TaxManager()

        # Test for 2022
        quarters_2022 = manager.calculate_tax_quarters(2022)

        # Verify we get 4 quarters
        assert len(quarters_2022) == 4

        # Verify each quarter has the expected dates
        assert quarters_2022[0].quarter == 1
        assert quarters_2022[0].start_date == datetime(2022, 1, 1)
        assert quarters_2022[0].end_date == datetime(2022, 3, 31)
        assert quarters_2022[0].due_date == datetime(2022, 4, 15)

        assert quarters_2022[1].quarter == 2
        assert quarters_2022[1].start_date == datetime(2022, 4, 1)
        assert quarters_2022[1].end_date == datetime(2022, 5, 31)
        assert quarters_2022[1].due_date == datetime(2022, 6, 15)

        assert quarters_2022[2].quarter == 3
        assert quarters_2022[2].start_date == datetime(2022, 6, 1)
        assert quarters_2022[2].end_date == datetime(2022, 8, 31)
        assert quarters_2022[2].due_date == datetime(2022, 9, 15)

        assert quarters_2022[3].quarter == 4
        assert quarters_2022[3].start_date == datetime(2022, 9, 1)
        assert quarters_2022[3].end_date == datetime(2022, 12, 31)
        assert quarters_2022[3].due_date == datetime(2023, 1, 15)

    def test_get_current_quarter(self):
        """Test getting the current tax quarter."""
        manager = TaxManager()

        # Since this depends on the current date, we can only verify
        # that it returns a valid quarter
        current_quarter = manager.get_current_quarter()

        assert 1 <= current_quarter.quarter <= 4
        assert current_quarter.year == datetime.now().year

    def test_tax_brackets(self):
        """Test setting and getting tax brackets."""
        manager = TaxManager()

        # Create test brackets
        federal_single = TaxBracket(
            jurisdiction=TaxJurisdiction.FEDERAL,
            filing_status=FilingStatus.SINGLE,
            tax_year=2022,
            income_thresholds=[0, 10000, 40000],
            rates=[10, 15, 25],
        )

        federal_joint = TaxBracket(
            jurisdiction=TaxJurisdiction.FEDERAL,
            filing_status=FilingStatus.MARRIED_JOINT,
            tax_year=2022,
            income_thresholds=[0, 20000, 80000],
            rates=[10, 15, 25],
        )

        # Set brackets
        manager.set_tax_brackets([federal_single, federal_joint])

        # Get and verify brackets
        retrieved_single = manager.get_tax_brackets(
            TaxJurisdiction.FEDERAL, 2022, FilingStatus.SINGLE
        )
        assert retrieved_single == federal_single

        retrieved_joint = manager.get_tax_brackets(
            TaxJurisdiction.FEDERAL, 2022, FilingStatus.MARRIED_JOINT
        )
        assert retrieved_joint == federal_joint

        # Test default filing status
        default_brackets = manager.get_tax_brackets(TaxJurisdiction.FEDERAL, 2022)
        assert default_brackets == federal_single

        # Test non-existent brackets
        non_existent = manager.get_tax_brackets(TaxJurisdiction.STATE, 2022)
        assert non_existent is None

    def test_load_default_brackets(self):
        """Test loading default tax brackets."""
        manager = TaxManager()

        # Load defaults
        manager.load_default_brackets()

        # Verify federal brackets are loaded
        single_brackets = manager.get_tax_brackets(
            TaxJurisdiction.FEDERAL, 2022, FilingStatus.SINGLE
        )
        assert single_brackets is not None
        assert single_brackets.jurisdiction == TaxJurisdiction.FEDERAL
        assert single_brackets.filing_status == FilingStatus.SINGLE
        assert single_brackets.tax_year == 2022
        assert len(single_brackets.income_thresholds) > 0
        assert len(single_brackets.rates) == len(single_brackets.income_thresholds)
