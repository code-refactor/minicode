"""Models for the income management system."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4
from decimal import Decimal

from pydantic import BaseModel, Field, validator

# Import from common library
from common import (
    Money,
    Currency,
    ValidationMixin,
    AuditMixin,
    BaseConfiguration,
    FinancialConfiguration,
)

from personal_finance_tracker.models.common import Transaction


class SmoothingMethod(str, Enum):
    """Income smoothing method enum."""

    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    SEASONAL_ADJUSTMENT = "seasonal_adjustment"
    PERCENTILE_BASED = "percentile_based"
    ROLLING_MEDIAN = "rolling_median"


class SmoothingConfig(FinancialConfiguration):
    """Configuration for income smoothing algorithms extending common financial config."""

    method: SmoothingMethod = SmoothingMethod.MOVING_AVERAGE
    window_size: int = 3  # Number of months for moving average
    alpha: float = 0.3  # For exponential smoothing
    seasonal_periods: int = 12  # For seasonal adjustment
    percentile: float = 25.0  # Percentile for percentile-based method
    min_history_months: int = 3  # Minimum months of data required
    target_monthly_income: Optional[Money] = None  # Override calculated smoothed income
    emergency_buffer_months: float = 2.0  # Buffer for lean months
    confidence_interval: float = 0.8  # For prediction intervals
    
    def __init__(self, **data):
        # Handle legacy float target_monthly_income by converting to Money
        if 'target_monthly_income' in data and data['target_monthly_income'] is not None and not isinstance(data['target_monthly_income'], Money):
            if isinstance(data['target_monthly_income'], (int, float, Decimal)):
                data['target_monthly_income'] = Money.from_float(float(data['target_monthly_income']))
            else:
                data['target_monthly_income'] = Money.from_string(str(data['target_monthly_income']))
        
        super().__init__(name="SmoothingConfig", **data)
    
    def get_default_settings(self) -> Dict:
        """Get default configuration settings."""
        return {
            "method": SmoothingMethod.MOVING_AVERAGE,
            "window_size": 3,
            "alpha": 0.3,
            "seasonal_periods": 12,
            "percentile": 25.0,
            "min_history_months": 3,
            "emergency_buffer_months": 2.0,
            "confidence_interval": 0.8,
        }
    
    def validate_settings(self) -> bool:
        """Validate configuration settings."""
        if self.window_size <= 0:
            raise ValueError("Window size must be positive")
        if not (0 <= self.alpha <= 1):
            raise ValueError("Alpha must be between 0 and 1")
        if not (0 <= self.percentile <= 100):
            raise ValueError("Percentile must be between 0 and 100")
        if self.emergency_buffer_months < 0:
            raise ValueError("Emergency buffer months must be non-negative")
        if not (0 <= self.confidence_interval <= 1):
            raise ValueError("Confidence interval must be between 0 and 1")
        return True

    @validator("window_size")
    def validate_window_size(cls, v):
        """Validate window size is positive."""
        if v <= 0:
            raise ValueError("Window size must be positive")
        return v

    @validator("alpha")
    def validate_alpha(cls, v):
        """Validate alpha is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError("Alpha must be between 0 and 1")
        return v

    @validator("percentile")
    def validate_percentile(cls, v):
        """Validate percentile is between 0 and 100."""
        if v < 0 or v > 100:
            raise ValueError("Percentile must be between 0 and 100")
        return v

    @validator("emergency_buffer_months")
    def validate_buffer(cls, v):
        """Validate buffer is non-negative."""
        if v < 0:
            raise ValueError("Emergency buffer months must be non-negative")
        return v

    @validator("confidence_interval")
    def validate_confidence(cls, v):
        """Validate confidence interval is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError("Confidence interval must be between 0 and 1")
        return v


class RevenueForecast(BaseModel, ValidationMixin):
    """Revenue forecast model with Money support and validation."""

    month: datetime
    expected_income: Money  # Use Money for precision
    lower_bound: Money  # Use Money for precision
    upper_bound: Money  # Use Money for precision
    confidence_interval: float
    sources: Dict[str, Money] = Field(default_factory=dict)  # Client/project breakdown with Money
    notes: Optional[str] = None
    
    def __init__(self, **data):
        # Handle legacy float values by converting to Money
        money_fields = ['expected_income', 'lower_bound', 'upper_bound']
        for field in money_fields:
            if field in data and not isinstance(data[field], Money):
                if isinstance(data[field], (int, float, Decimal)):
                    data[field] = Money.from_float(float(data[field]))
                else:
                    data[field] = Money.from_string(str(data[field]))
        
        # Handle sources conversion
        if 'sources' in data:
            new_sources = {}
            for source, amount in data['sources'].items():
                if not isinstance(amount, Money):
                    if isinstance(amount, (int, float, Decimal)):
                        amount = Money.from_float(float(amount))
                    else:
                        amount = Money.from_string(str(amount))
                new_sources[source] = amount
            data['sources'] = new_sources
        
        super().__init__(**data)


class SmoothedIncome(BaseModel):
    """Smoothed income calculation result with Money support and audit trail."""

    period_start: datetime
    period_end: datetime
    actual_income: Money  # Use Money for precision
    smoothed_income: Money  # Use Money for precision
    method: SmoothingMethod
    configuration: SmoothingConfig
    income_deficit: Optional[Money] = None  # When actual < smoothed
    income_surplus: Optional[Money] = None  # When actual > smoothed
    notes: Optional[str] = None
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __init__(self, **data):
        # Handle legacy float values by converting to Money
        money_fields = ['actual_income', 'smoothed_income', 'income_deficit', 'income_surplus']
        for field in money_fields:
            if field in data and data[field] is not None and not isinstance(data[field], Money):
                if isinstance(data[field], (int, float, Decimal)):
                    data[field] = Money.from_float(float(data[field]))
                else:
                    data[field] = Money.from_string(str(data[field]))
        
        super().__init__(**data)
        self.__init_audit__()
        
        # Set defaults if not provided
        if self.income_deficit is None:
            self.income_deficit = Money.zero()
        if self.income_surplus is None:
            self.income_surplus = Money.zero()
