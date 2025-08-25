"""Financial projection models for freelancers."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class SpendingLevel(str, Enum):
    """Spending level for cash runway projections."""

    MINIMAL = "minimal"  # Essential expenses only
    REDUCED = "reduced"  # Reduced discretionary spending
    NORMAL = "normal"  # Normal spending patterns
    INCREASED = "increased"  # Higher than normal spending


class ProjectionScenario(str, Enum):
    """Scenario types for financial projections."""

    PESSIMISTIC = "pessimistic"
    CONSERVATIVE = "conservative"
    EXPECTED = "expected"
    OPTIMISTIC = "optimistic"


class RevenueSource(BaseModel):
    """Revenue source for cash flow projections."""

    name: str
    amount: float
    probability: float = 100.0  # Percentage probability of receiving this income
    expected_date: Optional[datetime] = None
    recurring: bool = False
    recurrence_frequency: Optional[str] = None  # e.g., "monthly", "quarterly"
    notes: Optional[str] = None

    @validator("probability")
    def validate_probability(cls, v):
        """Validate probability is between 0 and 100."""
        if v < 0 or v > 100:
            raise ValueError("Probability must be between 0 and 100")
        return v


class ExpenseItem(BaseModel):
    """Expense item for cash flow projections."""

    name: str
    amount: float
    category: str
    due_date: Optional[datetime] = None
    recurring: bool = False
    recurrence_frequency: Optional[str] = None  # e.g., "monthly", "quarterly"
    essential: bool = False  # Whether this is an essential expense
    notes: Optional[str] = None


class CashFlowProjection(BaseModel):
    """Cash flow projection for a specific timeframe."""

    id: UUID = Field(default_factory=uuid4)
    start_date: datetime
    end_date: datetime
    scenario: ProjectionScenario = ProjectionScenario.EXPECTED
    starting_balance: float
    ending_balance: float
    total_income: float
    total_expenses: float
    net_cash_flow: float
    monthly_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    confidence_interval: float = 0.8  # 80% confidence interval by default
    notes: Optional[str] = None

    @validator("confidence_interval")
    def validate_confidence(cls, v):
        """Validate confidence interval is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError("Confidence interval must be between 0 and 1")
        return v


class RunwayProjection(BaseModel):
    """Cash runway projection showing how long funds will last."""

    id: UUID = Field(default_factory=uuid4)
    calculation_date: datetime = Field(default_factory=datetime.now)
    starting_balance: float
    spending_level: SpendingLevel
    monthly_expense_rate: float
    expected_income: Dict[str, float] = Field(default_factory=dict)  # Month -> amount
    runway_months: float
    depletion_date: Optional[datetime] = None
    confidence_level: float = 0.8
    notes: Optional[str] = None

    @validator("confidence_level")
    def validate_confidence(cls, v):
        """Validate confidence level is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError("Confidence level must be between 0 and 1")
        return v


class ScenarioParameter(BaseModel):
    """Parameter for what-if scenario analysis."""

    name: str
    description: Optional[str] = None
    current_value: float
    min_value: float
    max_value: float
    step_size: float = 1.0
    unit: Optional[str] = None  # e.g., "$", "%", "hours"


class WhatIfScenario(BaseModel):
    """What-if scenario for financial planning."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    base_scenario: ProjectionScenario
    parameters: List[ScenarioParameter] = Field(default_factory=list)
    result_metrics: Dict[str, float] = Field(default_factory=dict)
    creation_date: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None


class EmergencyFundAssessment(BaseModel):
    """Assessment of emergency fund adequacy."""

    id: UUID = Field(default_factory=uuid4)
    assessment_date: datetime = Field(default_factory=datetime.now)
    current_fund_balance: float
    monthly_essential_expenses: float
    recommended_months_coverage: float = 6.0
    recommended_fund_size: float
    current_coverage_months: float
    adequacy_level: str  # e.g., "inadequate", "minimal", "adequate", "excellent"
    funding_plan: Optional[str] = None
    notes: Optional[str] = None
