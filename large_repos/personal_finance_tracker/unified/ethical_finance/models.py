"""Common data models for the ethical finance package."""

from typing import Dict, List, Optional, Any, Union
from datetime import date as date_type, datetime
from dataclasses import dataclass, field
from decimal import Decimal

# Import from common library
from common import (
    BasePortfolio,
    BaseTransaction,
    TransactionType,
    Money,
    Currency,
    ValidationMixin,
    AuditMixin,
    BaseConfiguration,
)


@dataclass
class ESGRating:
    """Environmental, Social, and Governance ratings for an investment."""
    
    environmental: int
    social: int
    governance: int
    overall: int
    
    def __post_init__(self):
        """Validate that the overall score is consistent with component scores."""
        # Check if overall is within a reasonable range of the average
        component_avg = (self.environmental + self.social + self.governance) / 3
        if abs(self.overall - component_avg) > 15:  # Allow some variation in methodology
            raise ValueError(f"Overall score {self.overall} is too different from component average {component_avg:.1f}")


@dataclass
class Investment(ValidationMixin, AuditMixin):
    """Model representing an investment opportunity with ESG attributes and common library support."""
    
    id: str
    name: str
    sector: str
    industry: str
    market_cap: Money  # Use Money for precision
    price: Money  # Use Money for precision
    esg_ratings: Union[ESGRating, Dict[str, Any]]
    carbon_footprint: float
    renewable_energy_use: float
    diversity_score: float
    board_independence: float
    controversies: List[str] = field(default_factory=list)
    positive_practices: List[str] = field(default_factory=list)
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        """Initialize audit fields and convert dictionary esg_ratings to ESGRating object if necessary."""
        # Initialize audit fields
        self.__init_audit__()
        
        # Handle legacy float values by converting to Money
        if not isinstance(self.market_cap, Money):
            if isinstance(self.market_cap, (int, float, Decimal)):
                self.market_cap = Money.from_float(float(self.market_cap))
            else:
                self.market_cap = Money.from_string(str(self.market_cap))
        
        if not isinstance(self.price, Money):
            if isinstance(self.price, (int, float, Decimal)):
                self.price = Money.from_float(float(self.price))
            else:
                self.price = Money.from_string(str(self.price))
        
        # Convert dictionary esg_ratings to ESGRating object if necessary
        if isinstance(self.esg_ratings, dict):
            self.esg_ratings = ESGRating(
                environmental=self.esg_ratings["environmental"],
                social=self.esg_ratings["social"],
                governance=self.esg_ratings["governance"],
                overall=self.esg_ratings["overall"]
            )
    
    @property
    def has_major_controversies(self) -> bool:
        """Check if the investment has major controversies."""
        major_issues = ["human_rights", "fraud", "corruption", "environmental_disaster"]
        return any(issue in self.controversies for issue in major_issues)


@dataclass
class InvestmentHolding(ValidationMixin, AuditMixin):
    """A specific holding of an investment in a portfolio with Money support."""
    
    investment_id: str
    shares: float
    purchase_price: Money  # Use Money for precision
    purchase_date: date_type
    current_price: Money  # Use Money for precision
    current_value: Money  # Use Money for precision
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        """Initialize audit fields and validate that current_value = shares * current_price."""
        # Initialize audit fields
        self.__init_audit__()
        
        # Handle legacy float values by converting to Money
        money_fields = ['purchase_price', 'current_price', 'current_value']
        for field_name in money_fields:
            field_value = getattr(self, field_name)
            if not isinstance(field_value, Money):
                if isinstance(field_value, (int, float, Decimal)):
                    setattr(self, field_name, Money.from_float(float(field_value)))
                else:
                    setattr(self, field_name, Money.from_string(str(field_value)))
        
        # Validate that current_value = shares * current_price
        expected_value = self.current_price * self.shares
        if abs(float(self.current_value.amount) - float(expected_value.amount)) > 0.01:  # Allow for small rounding errors
            raise ValueError(f"Current value {self.current_value} does not match shares * price {expected_value}")
    
    @property
    def return_percentage(self) -> float:
        """Calculate the percentage return on this holding using Money arithmetic."""
        if self.purchase_price.is_zero():
            return 0.0
        price_ratio = float(self.current_price.amount) / float(self.purchase_price.amount)
        return (price_ratio - 1) * 100


@dataclass
class Portfolio(BasePortfolio):
    """A collection of investment holdings extending common portfolio functionality."""
    
    portfolio_id: str = ""
    holdings: List[Union[InvestmentHolding, Dict[str, Any]]] = field(default_factory=list)
    total_value: Money = field(default_factory=lambda: Money.from_float(0.0))  # Use Money for precision
    cash_balance: Money = field(default_factory=lambda: Money.from_float(0.0))  # Use Money for precision
    creation_date: date_type = field(default_factory=date_type.today)
    last_updated: date_type = field(default_factory=date_type.today)
    
    def __post_init__(self):
        """Initialize and validate portfolio, converting legacy data and dict holdings to proper objects."""
        # Initialize with name from portfolio_id if not set
        if not hasattr(self, 'name') or not self.name:
            self.name = self.portfolio_id
        
        # Handle legacy float values by converting to Money
        if not isinstance(self.total_value, Money):
            if isinstance(self.total_value, (int, float, Decimal)):
                self.total_value = Money.from_float(float(self.total_value))
            else:
                self.total_value = Money.from_string(str(self.total_value))
        
        if not isinstance(self.cash_balance, Money):
            if isinstance(self.cash_balance, (int, float, Decimal)):
                self.cash_balance = Money.from_float(float(self.cash_balance))
            else:
                self.cash_balance = Money.from_string(str(self.cash_balance))
        
        # Convert dictionary holdings to InvestmentHolding objects
        for i, holding in enumerate(self.holdings):
            if isinstance(holding, dict):
                # Convert any string dates to date objects
                if isinstance(holding.get("purchase_date"), str):
                    holding["purchase_date"] = date.fromisoformat(holding["purchase_date"])
                
                self.holdings[i] = InvestmentHolding(**holding)
        
        # Now validate total value using Money arithmetic
        if self.holdings:
            holdings_amounts = [holding.current_value for holding in self.holdings]
            holdings_sum = holdings_amounts[0]
            for amount in holdings_amounts[1:]:
                holdings_sum = holdings_sum + amount
        else:
            holdings_sum = Money.zero()
            
        if abs(float(self.total_value.amount) - float(holdings_sum.amount)) > 0.01:  # Allow for small rounding errors
            raise ValueError(f"Total value {self.total_value} does not match holdings sum {holdings_sum}")
    
    @property
    def total_assets(self) -> Money:
        """Calculate total assets including cash using Money arithmetic."""
        return self.total_value + self.cash_balance
    
    # Implementation of abstract methods from BasePortfolio
    def get_total_value(self) -> Money:
        """Calculate total portfolio value."""
        return self.total_value
    
    def get_holdings(self) -> List[InvestmentHolding]:
        """Get list of portfolio holdings."""
        return self.holdings
    
    def add_holding(self, holding: InvestmentHolding) -> None:
        """Add a holding to the portfolio."""
        self.holdings.append(holding)
        # Recalculate total value
        if self.holdings:
            holdings_amounts = [h.current_value for h in self.holdings]
            self.total_value = holdings_amounts[0]
            for amount in holdings_amounts[1:]:
                self.total_value = self.total_value + amount
    
    def remove_holding(self, holding_id: str) -> bool:
        """Remove a holding from the portfolio."""
        for i, holding in enumerate(self.holdings):
            if holding.investment_id == holding_id:
                del self.holdings[i]
                # Recalculate total value
                if self.holdings:
                    holdings_amounts = [h.current_value for h in self.holdings]
                    self.total_value = holdings_amounts[0]
                    for amount in holdings_amounts[1:]:
                        self.total_value = self.total_value + amount
                else:
                    self.total_value = Money.zero()
                return True
        return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio performance metrics."""
        if not self.holdings:
            return {"total_return_percentage": 0.0, "holdings_count": 0}
        
        total_return_value = Money.zero()
        total_cost_basis = Money.zero()
        
        for holding in self.holdings:
            cost_basis = holding.purchase_price * holding.shares
            total_cost_basis = total_cost_basis + cost_basis
            total_return_value = total_return_value + holding.current_value
        
        if total_cost_basis.is_positive():
            return_percentage = (float(total_return_value.amount) / float(total_cost_basis.amount) - 1) * 100
        else:
            return_percentage = 0.0
        
        return {
            "total_return_percentage": return_percentage,
            "holdings_count": len(self.holdings),
            "total_value": self.total_value,
            "cash_balance": self.cash_balance,
        }


@dataclass
class ShareholderResolution:
    """Model representing a shareholder resolution with voting results."""
    
    company_id: str
    resolution_id: str
    year: int
    title: str
    category: str
    subcategory: str
    proposed_by: str
    status: str
    votes_for: Optional[float] = None
    votes_against: Optional[float] = None
    abstentions: Optional[float] = None
    company_recommendation: Optional[str] = None
    outcome: Optional[str] = None
    
    def __post_init__(self):
        """Validate that vote percentages sum to approximately 1."""
        if all(val is not None for val in [self.votes_for, self.votes_against, self.abstentions]):
            vote_sum = self.votes_for + self.votes_against + self.abstentions
            if abs(vote_sum - 1.0) > 0.01:  # Allow for small rounding errors
                raise ValueError(f"Vote percentages sum to {vote_sum}, expected 1.0")


class Transaction(BaseTransaction):
    """Model representing a personal financial transaction extending common functionality."""
    
    def __init__(self, id: str, date: Union[datetime, date_type], amount: Union[Money, float, int, Decimal], description: str, vendor: str, category: str, tags: List[str] = None):
        """Initialize transaction."""
        self.id = id
        self.vendor = vendor
        
        # Convert amount to Money if needed
        if not isinstance(amount, Money):
            if isinstance(amount, (int, float, Decimal)):
                self._money_amount = Money.from_float(float(amount))
            else:
                self._money_amount = Money.from_string(str(amount))
        else:
            self._money_amount = amount
        
        # Convert date to datetime if needed
        if isinstance(date, date_type) and not isinstance(date, datetime):
            date = datetime.combine(date, datetime.min.time())
        
        # Initialize base transaction - determine transaction type from amount
        transaction_type = TransactionType.EXPENSE if float(self._money_amount.amount) > 0 else TransactionType.INCOME
        
        # Call parent constructor with numeric amount
        super().__init__(
            amount=float(self._money_amount.amount),
            date=date,
            description=description or f"{vendor} - {category}",
            transaction_type=transaction_type,
            category=category,
            tags=tags or []
        )
        
        # After parent init, override amount to be Money object
        self.amount = self._money_amount
    
    def validate(self) -> bool:
        """Validate transaction according to business rules."""
        if not self.vendor.strip():
            raise ValueError("Vendor cannot be empty")
        if not self.category.strip():
            raise ValueError("Category cannot be empty")
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary representation."""
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "amount": float(self.amount.amount),
            "vendor": self.vendor,
            "category": self.category,
            "description": self.description,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create transaction from dictionary representation."""
        # Handle amount conversion
        if 'amount' in data and not isinstance(data['amount'], Money):
            if isinstance(data['amount'], (int, float, Decimal)):
                data['amount'] = Money.from_float(float(data['amount']))
            else:
                data['amount'] = Money.from_string(str(data['amount']))
        
        # Handle date conversion
        if 'date' in data and isinstance(data['date'], str):
            data['date'] = datetime.fromisoformat(data['date'])
        
        return cls(**data)


@dataclass
class EthicalCriteria:
    """Customizable ethical screening criteria for investments extending common configuration."""
    
    criteria_id: str
    name: str  # Add name field
    environmental: Dict[str, Any]
    social: Dict[str, Any]
    governance: Dict[str, Any]
    min_overall_score: float
    exclusions: List[str] = field(default_factory=list)
    inclusions: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate criteria after initialization."""
        self._validate_criteria_post_init()
    
    def _validate_criteria_post_init(self):
        """Validate that criteria weights are included and sum approximately to 1."""
        # Check that each criteria includes a weight
        for field_name in ['environmental', 'social', 'governance']:
            field_value = getattr(self, field_name)
            if 'weight' not in field_value:
                raise ValueError(f"{field_name} criteria must include a weight")
            
            # Ensure weight is between 0 and 1
            if field_value['weight'] < 0 or field_value['weight'] > 1:
                raise ValueError(f"{field_name} weight must be between 0 and 1")
        
        # Check that weights sum to approximately 1
        weights_sum = (
            self.environmental.get('weight', 0) + 
            self.social.get('weight', 0) + 
            self.governance.get('weight', 0)
        )
        if abs(weights_sum - 1.0) > 0.01:  # Allow for small rounding errors
            raise ValueError(f"Criteria weights sum to {weights_sum}, expected 1.0")
    
    def validate_settings(self) -> bool:
        """Validate configuration settings."""
        self._validate_criteria_post_init()
        return True
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default configuration settings."""
        return {
            "environmental": {"weight": 0.4, "min_score": 60},
            "social": {"weight": 0.3, "min_score": 60},
            "governance": {"weight": 0.3, "min_score": 60},
            "min_overall_score": 65.0,
            "exclusions": ["tobacco", "weapons"],
            "inclusions": ["renewable_energy", "healthcare"],
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "criteria_id": self.criteria_id,
            "name": self.name,
            "environmental": self.environmental,
            "social": self.social,
            "governance": self.governance,
            "min_overall_score": self.min_overall_score,
            "exclusions": self.exclusions,
            "inclusions": self.inclusions,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EthicalCriteria':
        """Create configuration from dictionary."""
        return cls(**data)


@dataclass
class ImpactMetric:
    """Model for defining and tracking impact metrics."""
    
    metric_id: str
    name: str
    category: str
    unit: str
    description: str
    higher_is_better: bool
    data_source: str


@dataclass
class ImpactData:
    """Impact data for a specific investment in a specific year."""
    
    investment_id: str
    year: int
    metrics: Dict[str, float]
    # Additional fields allowed for future extensibility