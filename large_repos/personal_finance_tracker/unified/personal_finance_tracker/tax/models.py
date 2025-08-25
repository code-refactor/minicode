"""Tax management models for freelancers."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4
from decimal import Decimal

from pydantic import BaseModel, Field, validator

# Import from common library
from common import (
    Money,
    Currency,
    ValidationMixin,
    AuditMixin,
    FinancialConfiguration,
)

from personal_finance_tracker.models.common import TaxRate, TaxPayment, TaxDeduction


class FilingStatus(str, Enum):
    """Tax filing status."""

    SINGLE = "single"
    MARRIED_JOINT = "married_filing_jointly"
    MARRIED_SEPARATE = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"


class TaxJurisdiction(str, Enum):
    """Tax jurisdiction types."""

    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"


class QuarterInfo(BaseModel):
    """Information about a tax quarter."""

    year: int
    quarter: int
    start_date: datetime
    end_date: datetime
    due_date: datetime
    description: str


class TaxBracket(BaseModel, ValidationMixin):
    """Tax bracket for a specific jurisdiction and filing status with Money support."""

    jurisdiction: TaxJurisdiction
    filing_status: FilingStatus
    tax_year: int
    income_thresholds: List[Money]  # Lower bounds of each bracket using Money
    rates: List[float]  # Rates for each bracket (as percentage: 10 = 10%)
    
    def __init__(self, **data):
        # Handle legacy float income thresholds by converting to Money
        if 'income_thresholds' in data:
            new_thresholds = []
            for threshold in data['income_thresholds']:
                if not isinstance(threshold, Money):
                    if isinstance(threshold, (int, float, Decimal)):
                        threshold = Money.from_float(float(threshold))
                    else:
                        threshold = Money.from_string(str(threshold))
                new_thresholds.append(threshold)
            data['income_thresholds'] = new_thresholds
        
        super().__init__(**data)

    @validator("rates")
    def validate_rates(cls, v, values):
        """Validate that rates are between 0 and 100 and match income thresholds."""
        if any(r < 0 or r > 100 for r in v):
            raise ValueError("Rates must be between 0 and 100")

        if "income_thresholds" in values and len(v) != len(values["income_thresholds"]):
            raise ValueError("Number of rates must match number of income thresholds")

        return v


class TaxLiability(BaseModel):
    """Calculated tax liability for a jurisdiction and period."""

    jurisdiction: TaxJurisdiction
    tax_year: int
    income: float
    deductions: float
    taxable_income: float
    tax_amount: float
    effective_rate: float  # As percentage
    marginal_rate: float  # As percentage
    filing_status: FilingStatus
    calculation_date: datetime = Field(default_factory=datetime.now)
    breakdown: Dict[str, float] = Field(default_factory=dict)  # Detailed breakdown

    @validator("effective_rate", "marginal_rate")
    def validate_rates(cls, v):
        """Validate that rates are between 0 and 100."""
        if v < 0 or v > 100:
            raise ValueError("Rates must be between 0 and 100")
        return v


class EstimatedPayment(BaseModel):
    """Estimated tax payment calculation."""

    tax_year: int
    quarter: int
    jurisdiction: TaxJurisdiction
    due_date: datetime
    payment_amount: float  # Use this field instead of suggested_amount
    suggested_amount: Optional[float] = None  # Keep for backwards compatibility
    minimum_required: float
    safe_harbor_amount: Optional[float] = None
    year_to_date_liability: float
    previous_payments: float
    federal_tax: Optional[float] = None  # Added for test compatibility
    self_employment_tax: Optional[float] = None  # Added for test compatibility
    state_tax: Optional[float] = None  # Added for test compatibility
    calculation_date: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None


class TaxYearSummary(BaseModel):
    """Summary of tax obligations for a tax year."""

    tax_year: int
    total_income: float
    total_expenses: float
    total_deductions: float
    taxable_income: float
    total_tax: float
    effective_tax_rate: float
    federal_tax: float
    state_tax: float
    self_employment_tax: float
    total_paid: float
    balance_due: float
    calculation_date: datetime = Field(default_factory=datetime.now)
    deductions: List[TaxDeduction] = Field(default_factory=list)
    payments: List[TaxPayment] = Field(default_factory=list)

    @validator("effective_tax_rate")
    def validate_rate(cls, v):
        """Validate that rate is between 0 and 100."""
        if v < 0 or v > 100:
            raise ValueError("Rate must be between 0 and 100")
        return v
