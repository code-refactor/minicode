"""Common data models for the personal finance tracker."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4
from decimal import Decimal

from pydantic import BaseModel, Field, validator

# Import from common library core modules directly to avoid circular imports
from common.core.models.base import (
    BaseTransaction as CommonBaseTransaction, 
    ValidationMixin, 
    AuditMixin,
    TransactionType as CommonTransactionType
)
from common.core.models.money import Money, Currency


# Extend the common TransactionType with persona-specific types
class TransactionType(str, Enum):
    """Transaction type enum with freelancer-specific additions."""

    # Import common transaction types
    INCOME = CommonTransactionType.INCOME.value
    EXPENSE = CommonTransactionType.EXPENSE.value
    TRANSFER = CommonTransactionType.TRANSFER.value
    
    # Add freelancer-specific types
    TAX_PAYMENT = "tax_payment"


class AccountType(str, Enum):
    """Account type enum."""

    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    CASH = "cash"


class ExpenseCategory(str, Enum):
    """Expense category enum."""

    BUSINESS_SUPPLIES = "business_supplies"
    SOFTWARE = "software"
    MARKETING = "marketing"
    OFFICE_RENT = "office_rent"
    UTILITIES = "utilities"
    TRAVEL = "travel"
    MEALS = "meals"
    EQUIPMENT = "equipment"
    PROFESSIONAL_DEVELOPMENT = "professional_development"
    PROFESSIONAL_SERVICES = "professional_services"
    HEALTH_INSURANCE = "health_insurance"
    RETIREMENT = "retirement"
    PHONE = "phone"
    INTERNET = "internet"
    CAR = "car"
    HOME_OFFICE = "home_office"
    PERSONAL = "personal"
    OTHER = "other"


class AccountBalance(BaseModel, AuditMixin):
    """Account balance model with audit trail."""

    account_id: str
    account_name: str
    account_type: AccountType
    balance: Money  # Use Money for precision
    as_of_date: datetime
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __init__(self, **data):
        # Handle legacy float balance by converting to Money
        if 'balance' in data and not isinstance(data['balance'], Money):
            if isinstance(data['balance'], (int, float, Decimal)):
                data['balance'] = Money.from_float(float(data['balance']))
            else:
                data['balance'] = Money.from_string(str(data['balance']))
        
        super().__init__(**data)
        self.__init_audit__()


class Transaction(BaseModel, ValidationMixin, AuditMixin):
    """Transaction model extending common transaction functionality."""

    id: UUID = Field(default_factory=uuid4)
    date: datetime
    amount: Money  # Use Money type for proper precision
    description: str
    transaction_type: TransactionType
    account_id: str
    category: Optional[ExpenseCategory] = None
    business_use_percentage: Optional[float] = None
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    invoice_id: Optional[str] = None
    receipt_path: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Audit fields from mixin
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __init__(self, **data):
        # Handle legacy float amounts by converting to Money
        if 'amount' in data and not isinstance(data['amount'], Money):
            if isinstance(data['amount'], (int, float, Decimal)):
                data['amount'] = Money.from_float(float(data['amount']))
            else:
                data['amount'] = Money.from_string(str(data['amount']))
        
        super().__init__(**data)
        self.__init_audit__()

    @validator("business_use_percentage")
    def validate_business_percentage(cls, v):
        """Validate that business use percentage is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Business use percentage must be between 0 and 100")
        return v
    
    def validate(self) -> bool:
        """Validate transaction according to business rules."""
        # Use validation mixin methods
        self.validate_non_empty_string(self.description, "description")
        if self.amount.is_zero():
            raise ValueError("Transaction amount cannot be zero")
        return True
    
    def to_dict(self) -> Dict:
        """Convert transaction to dictionary."""
        data = self.dict()
        # Convert Money to float for backward compatibility
        data['amount'] = float(data['amount'].amount)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        """Create transaction from dictionary."""
        return cls(**data)


class Client(BaseModel):
    """Client model."""

    id: str
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    active: bool = True


class Project(BaseModel, AuditMixin):
    """Project model with audit trail and Money support."""

    id: str
    name: str
    client_id: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str  # e.g., "active", "completed", "on_hold"
    hourly_rate: Optional[Money] = None  # Use Money for precision
    fixed_price: Optional[Money] = None  # Use Money for precision
    estimated_hours: Optional[float] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __init__(self, **data):
        # Handle legacy float rates/prices by converting to Money
        for field in ['hourly_rate', 'fixed_price']:
            if field in data and data[field] is not None and not isinstance(data[field], Money):
                if isinstance(data[field], (int, float, Decimal)):
                    data[field] = Money.from_float(float(data[field]))
                else:
                    data[field] = Money.from_string(str(data[field]))
        
        super().__init__(**data)
        self.__init_audit__()


class TimeEntry(BaseModel):
    """Time entry model for tracking hours worked on projects."""

    id: UUID = Field(default_factory=uuid4)
    project_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[float] = None
    description: str
    billable: bool = True
    tags: List[str] = Field(default_factory=list)

    @validator("duration_minutes", always=True)
    def calculate_duration(cls, v, values):
        """Calculate duration from start and end time if not provided."""
        if v is not None:
            return v
        if (
            "start_time" in values
            and "end_time" in values
            and values["end_time"] is not None
        ):
            delta = values["end_time"] - values["start_time"]
            return delta.total_seconds() / 60
        return None


class Invoice(BaseModel, AuditMixin):
    """Invoice model with audit trail and Money support."""

    id: str
    client_id: str
    project_id: Optional[str] = None
    issue_date: datetime
    due_date: datetime
    amount: Money  # Use Money for precision
    status: str  # e.g., "draft", "sent", "paid", "overdue"
    payment_date: Optional[datetime] = None
    description: Optional[str] = None
    line_items: List[Dict] = Field(default_factory=list)
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __init__(self, **data):
        # Handle legacy float amount by converting to Money
        if 'amount' in data and not isinstance(data['amount'], Money):
            if isinstance(data['amount'], (int, float, Decimal)):
                data['amount'] = Money.from_float(float(data['amount']))
            else:
                data['amount'] = Money.from_string(str(data['amount']))
        
        super().__init__(**data)
        self.__init_audit__()


class TaxPayment(BaseModel, AuditMixin):
    """Tax payment model with audit trail and Money support."""

    id: UUID = Field(default_factory=uuid4)
    date: datetime
    amount: Money  # Use Money for precision
    tax_year: int
    quarter: int
    payment_method: str
    confirmation_number: Optional[str] = None
    notes: Optional[str] = None
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __init__(self, **data):
        # Handle legacy float amount by converting to Money
        if 'amount' in data and not isinstance(data['amount'], Money):
            if isinstance(data['amount'], (int, float, Decimal)):
                data['amount'] = Money.from_float(float(data['amount']))
            else:
                data['amount'] = Money.from_string(str(data['amount']))
        
        super().__init__(**data)
        self.__init_audit__()


class TaxRate(BaseModel):
    """Tax rate for a specific income bracket."""

    bracket_min: Money  # Use Money for precision
    bracket_max: Optional[Money] = None  # Use Money for precision
    rate: float  # Percentage (0-100)
    tax_year: int
    jurisdiction: str = "federal"  # e.g., "federal", "state", "local"
    
    def __init__(self, **data):
        # Handle legacy float brackets by converting to Money
        for field in ['bracket_min', 'bracket_max']:
            if field in data and data[field] is not None and not isinstance(data[field], Money):
                if isinstance(data[field], (int, float, Decimal)):
                    data[field] = Money.from_float(float(data[field]))
                else:
                    data[field] = Money.from_string(str(data[field]))
        
        super().__init__(**data)


class TaxDeduction(BaseModel, AuditMixin):
    """Tax deduction model with audit trail and Money support."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    amount: Money  # Use Money for precision
    tax_year: int
    category: str
    description: Optional[str] = None
    receipt_path: Optional[str] = None
    
    # Audit fields
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __init__(self, **data):
        # Handle legacy float amount by converting to Money
        if 'amount' in data and not isinstance(data['amount'], Money):
            if isinstance(data['amount'], (int, float, Decimal)):
                data['amount'] = Money.from_float(float(data['amount']))
            else:
                data['amount'] = Money.from_string(str(data['amount']))
        
        super().__init__(**data)
        self.__init_audit__()
