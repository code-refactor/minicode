"""Project profitability analysis models."""

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
    percentage_change,
    compound_growth_rate,
)

from personal_finance_tracker.models.common import Project, TimeEntry, Transaction


class ProjectMetricType(str, Enum):
    """Types of project profitability metrics."""

    HOURLY_RATE = "hourly_rate"
    TOTAL_PROFIT = "total_profit"
    PROFIT_MARGIN = "profit_margin"
    ROI = "roi"  # Return on investment


class ProfitabilityMetric(BaseModel, AuditMixin):
    """Profitability metric for a project with audit support."""

    project_id: str
    metric_type: ProjectMetricType
    value: Union[float, Money]  # Support both numeric and Money values
    calculation_date: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = None
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __init__(self, **data):
        # Handle Money conversion for monetary metrics
        if 'value' in data and data.get('metric_type') in [ProjectMetricType.TOTAL_PROFIT]:
            if not isinstance(data['value'], Money) and isinstance(data['value'], (int, float, Decimal)):
                data['value'] = Money.from_float(float(data['value']))
        
        super().__init__(**data)
        self.__init_audit__()


class ProjectProfitability(BaseModel, ValidationMixin):
    """Project profitability analysis result with Money support and validation."""

    project_id: str
    project_name: str
    client_id: str
    start_date: datetime
    end_date: Optional[datetime] = None
    total_hours: float
    total_revenue: Money  # Use Money for precision
    total_expenses: Money  # Use Money for precision
    total_profit: Money  # Use Money for precision
    effective_hourly_rate: Money  # Use Money for precision
    profit_margin: float  # Percentage
    roi: float  # Return on investment
    is_completed: bool
    calculation_date: datetime = Field(default_factory=datetime.now)
    metrics: List[ProfitabilityMetric] = Field(default_factory=list)
    
    def __init__(self, **data):
        # Handle legacy float values by converting to Money
        money_fields = ['total_revenue', 'total_expenses', 'total_profit', 'effective_hourly_rate']
        for field in money_fields:
            if field in data and not isinstance(data[field], Money):
                if isinstance(data[field], (int, float, Decimal)):
                    data[field] = Money.from_float(float(data[field]))
                else:
                    data[field] = Money.from_string(str(data[field]))
        
        super().__init__(**data)

    def calculate_derived_metrics(self):
        """Calculate derived metrics using Money arithmetic."""
        # Calculate effective hourly rate
        if self.total_hours > 0:
            self.effective_hourly_rate = self.total_revenue / self.total_hours
        else:
            self.effective_hourly_rate = Money.zero()
        
        # Calculate total profit
        self.total_profit = self.total_revenue - self.total_expenses
        
        # Calculate profit margin percentage
        if self.total_revenue.is_positive():
            profit_ratio = float(self.total_profit.amount) / float(self.total_revenue.amount)
            self.profit_margin = profit_ratio * 100
        else:
            self.profit_margin = 0.0
        
        # Calculate ROI
        if self.total_expenses.is_positive():
            roi_ratio = float(self.total_profit.amount) / float(self.total_expenses.amount)
            self.roi = roi_ratio * 100
        else:
            self.roi = 0.0


class ClientProfitability(BaseModel, ValidationMixin):
    """Client profitability analysis result with Money support and validation."""

    client_id: str
    client_name: str
    number_of_projects: int
    total_hours: float
    total_revenue: Money  # Use Money for precision
    total_expenses: Money  # Use Money for precision
    total_profit: Money  # Use Money for precision
    average_hourly_rate: Money  # Use Money for precision
    average_profit_margin: float
    average_invoice_payment_days: Optional[float] = None
    projects: List[ProjectProfitability] = Field(default_factory=list)
    calculation_date: datetime = Field(default_factory=datetime.now)
    
    def __init__(self, **data):
        # Handle legacy float values by converting to Money
        money_fields = ['total_revenue', 'total_expenses', 'total_profit', 'average_hourly_rate']
        for field in money_fields:
            if field in data and not isinstance(data[field], Money):
                if isinstance(data[field], (int, float, Decimal)):
                    data[field] = Money.from_float(float(data[field]))
                else:
                    data[field] = Money.from_string(str(data[field]))
        
        super().__init__(**data)


class TrendPoint(BaseModel):
    """Point in a trend analysis with Money support."""

    date: datetime
    value: Union[float, Money]  # Support both numeric and Money values
    
    def __init__(self, **data):
        # Convert float to Money if needed based on context
        super().__init__(**data)


class TrendAnalysis(BaseModel):
    """Trend analysis for project profitability over time."""

    metric_type: ProjectMetricType
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    period: str  # "weekly", "monthly", "quarterly", "yearly"
    start_date: datetime
    end_date: datetime
    data_points: List[TrendPoint] = Field(default_factory=list)
    calculation_date: datetime = Field(default_factory=datetime.now)
    description: Optional[str] = None
