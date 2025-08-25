"""
Money handling with proper precision and currency support.

This module provides the Money class for accurate financial calculations
using Decimal arithmetic and proper currency handling.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Optional
from dataclasses import dataclass
from enum import Enum


class Currency(Enum):
    """Supported currencies with their standard codes."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    CNY = "CNY"
    INR = "INR"
    BRL = "BRL"


@dataclass(frozen=True)
class Money:
    """
    Immutable Money class with precise decimal arithmetic.
    
    Handles currency amounts with proper precision to avoid
    floating-point rounding errors in financial calculations.
    """
    
    amount: Decimal
    currency: Currency = Currency.USD
    
    def __post_init__(self):
        """Validate money object after initialization."""
        if not isinstance(self.amount, Decimal):
            # Convert to Decimal if not already
            try:
                object.__setattr__(self, 'amount', Decimal(str(self.amount)))
            except (ValueError, TypeError, InvalidOperation):
                raise ValueError(f"Invalid amount: {self.amount}")
        
        # Round to appropriate precision (2 decimal places for most currencies, 0 for JPY)
        precision = 0 if self.currency == Currency.JPY else 2
        rounded_amount = self.amount.quantize(
            Decimal('0.01' if precision == 2 else '1'),
            rounding=ROUND_HALF_UP
        )
        object.__setattr__(self, 'amount', rounded_amount)
    
    @classmethod
    def from_float(cls, amount: float, currency: Currency = Currency.USD) -> 'Money':
        """
        Create Money from float with proper conversion.
        
        Args:
            amount: Float amount to convert
            currency: Currency for the money
            
        Returns:
            Money instance
            
        Raises:
            ValueError: If amount cannot be converted
        """
        try:
            return cls(Decimal(str(amount)), currency)
        except (ValueError, TypeError, InvalidOperation) as e:
            raise ValueError(f"Cannot convert {amount} to Money: {e}")
    
    @classmethod
    def from_string(cls, amount_str: str, currency: Currency = Currency.USD) -> 'Money':
        """
        Create Money from string representation.
        
        Args:
            amount_str: String amount to convert (e.g., "123.45", "1,234.56")
            currency: Currency for the money
            
        Returns:
            Money instance
            
        Raises:
            ValueError: If string cannot be parsed
        """
        # Remove common formatting characters
        cleaned = amount_str.replace(',', '').replace(' ', '').strip()
        
        # Handle negative amounts
        is_negative = cleaned.startswith('-') or cleaned.startswith('(') and cleaned.endswith(')')
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = cleaned[1:-1]  # Remove parentheses
        
        try:
            amount = Decimal(cleaned)
            if is_negative and amount > 0:
                amount = -amount
            return cls(amount, currency)
        except (ValueError, TypeError, InvalidOperation) as e:
            raise ValueError(f"Cannot parse '{amount_str}' as Money: {e}")
    
    @classmethod
    def zero(cls, currency: Currency = Currency.USD) -> 'Money':
        """Create zero money in specified currency."""
        return cls(Decimal('0'), currency)
    
    def __add__(self, other: Union['Money', int, float]) -> 'Money':
        """Add two Money objects or add a number to Money."""
        if isinstance(other, (int, float)):
            # Support sum() which starts with 0
            if other == 0:
                return self
            # Otherwise add as Money
            return Money(self.amount + Decimal(str(other)), self.currency)
        
        if not isinstance(other, Money):
            raise TypeError(f"Cannot add Money and {type(other)}")
        
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency.value} and {other.currency.value}")
        
        return Money(self.amount + other.amount, self.currency)
    
    def __radd__(self, other: Union['Money', int, float]) -> 'Money':
        """Support reverse addition for Money (especially for sum())."""
        if isinstance(other, (int, float)):
            if other == 0:
                return self
            return Money(Decimal(str(other)) + self.amount, self.currency)
        return self.__add__(other)
    
    def __sub__(self, other: 'Money') -> 'Money':
        """Subtract two Money objects (must have same currency)."""
        if not isinstance(other, Money):
            raise TypeError(f"Cannot subtract {type(other)} from Money")
        
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency.value} from {self.currency.value}")
        
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, multiplier: Union[int, float, Decimal]) -> 'Money':
        """Multiply Money by a scalar."""
        if not isinstance(multiplier, (int, float, Decimal)):
            raise TypeError(f"Cannot multiply Money by {type(multiplier)}")
        
        if not isinstance(multiplier, Decimal):
            multiplier = Decimal(str(multiplier))
        
        return Money(self.amount * multiplier, self.currency)
    
    def __rmul__(self, multiplier: Union[int, float, Decimal]) -> 'Money':
        """Right multiplication (scalar * Money)."""
        return self.__mul__(multiplier)
    
    def __truediv__(self, divisor: Union[int, float, Decimal]) -> 'Money':
        """Divide Money by a scalar."""
        if not isinstance(divisor, (int, float, Decimal)):
            raise TypeError(f"Cannot divide Money by {type(divisor)}")
        
        if divisor == 0:
            raise ZeroDivisionError("Cannot divide Money by zero")
        
        if not isinstance(divisor, Decimal):
            divisor = Decimal(str(divisor))
        
        return Money(self.amount / divisor, self.currency)
    
    def __floordiv__(self, divisor: Union[int, float, Decimal]) -> 'Money':
        """Floor division of Money by a scalar."""
        result = self.__truediv__(divisor)
        return Money(result.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP), self.currency)
    
    def __neg__(self) -> 'Money':
        """Negate Money amount."""
        return Money(-self.amount, self.currency)
    
    def __abs__(self) -> 'Money':
        """Get absolute value of Money amount."""
        return Money(abs(self.amount), self.currency)
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another Money object or numeric value."""
        if isinstance(other, (int, float)):
            # Compare with numeric value (assumes same currency)
            return float(self.amount) == other
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency
    
    def __lt__(self, other: Union['Money', int, float]) -> bool:
        """Less than comparison."""
        if isinstance(other, (int, float)):
            # Compare with numeric value (assumes same currency)
            return float(self.amount) < other
        
        if not isinstance(other, Money):
            raise TypeError(f"Cannot compare Money and {type(other)}")
        
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare {self.currency.value} and {other.currency.value}")
        
        return self.amount < other.amount
    
    def __le__(self, other: Union['Money', int, float]) -> bool:
        """Less than or equal comparison."""
        if isinstance(other, (int, float)):
            return float(self.amount) <= other
        return self.__eq__(other) or self.__lt__(other)
    
    def __gt__(self, other: Union['Money', int, float]) -> bool:
        """Greater than comparison."""
        if isinstance(other, (int, float)):
            return float(self.amount) > other
        return not self.__le__(other)
    
    def __ge__(self, other: Union['Money', int, float]) -> bool:
        """Greater than or equal comparison."""
        if isinstance(other, (int, float)):
            return float(self.amount) >= other
        return not self.__lt__(other)
    
    def __hash__(self) -> int:
        """Hash function for use in sets and dicts."""
        return hash((self.amount, self.currency))
    
    def __str__(self) -> str:
        """String representation with currency symbol."""
        return self.format()
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Money({self.amount}, {self.currency})"
    
    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > 0
    
    def is_negative(self) -> bool:
        """Check if amount is negative."""
        return self.amount < 0
    
    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == 0
    
    def format(self, include_currency: bool = True, currency_symbol: bool = True) -> str:
        """
        Format money as string with proper currency display.
        
        Args:
            include_currency: Whether to include currency information
            currency_symbol: Whether to use symbol ($) or code (USD)
            
        Returns:
            Formatted money string
        """
        # Currency symbols mapping
        symbols = {
            Currency.USD: "$",
            Currency.EUR: "€",
            Currency.GBP: "£",
            Currency.JPY: "¥",
            Currency.CAD: "C$",
            Currency.AUD: "A$",
            Currency.CHF: "CHF ",
            Currency.CNY: "¥",
            Currency.INR: "₹",
            Currency.BRL: "R$",
        }
        
        # Format the amount with appropriate decimal places
        if self.currency == Currency.JPY:
            amount_str = f"{self.amount:,.0f}"
        else:
            amount_str = f"{self.amount:,.2f}"
        
        if not include_currency:
            return amount_str
        
        if currency_symbol and self.currency in symbols:
            symbol = symbols[self.currency]
            if symbol.endswith(' '):  # CHF case
                return f"{symbol}{amount_str}"
            else:
                return f"{symbol}{amount_str}"
        else:
            return f"{amount_str} {self.currency.value}"
    
    def to_major_units(self) -> Decimal:
        """
        Convert to major currency units (dollars, euros, etc.).
        
        Returns:
            Decimal amount in major units
        """
        return self.amount
    
    def to_minor_units(self) -> int:
        """
        Convert to minor currency units (cents, pence, etc.).
        
        Returns:
            Integer amount in minor units
        """
        if self.currency == Currency.JPY:
            # JPY doesn't have minor units
            return int(self.amount)
        else:
            # Convert to cents/pence (multiply by 100)
            return int(self.amount * 100)
    
    @classmethod
    def from_minor_units(cls, minor_units: int, currency: Currency = Currency.USD) -> 'Money':
        """
        Create Money from minor currency units.
        
        Args:
            minor_units: Amount in minor units (cents, pence, etc.)
            currency: Currency for the money
            
        Returns:
            Money instance
        """
        if currency == Currency.JPY:
            # JPY doesn't have minor units
            return cls(Decimal(minor_units), currency)
        else:
            # Convert from cents/pence (divide by 100)
            return cls(Decimal(minor_units) / 100, currency)
    
    def allocate(self, ratios: list[Union[int, float, Decimal]]) -> list['Money']:
        """
        Allocate money according to given ratios.
        
        Useful for splitting amounts proportionally while avoiding
        rounding errors by ensuring the total equals the original amount.
        
        Args:
            ratios: List of ratios for allocation
            
        Returns:
            List of Money objects that sum to original amount
            
        Raises:
            ValueError: If ratios are invalid
        """
        if not ratios:
            raise ValueError("Ratios list cannot be empty")
        
        if any(r < 0 for r in ratios):
            raise ValueError("Ratios cannot be negative")
        
        total_ratio = sum(Decimal(str(r)) for r in ratios)
        if total_ratio == 0:
            raise ValueError("Sum of ratios cannot be zero")
        
        # Convert ratios to Decimal for precision
        decimal_ratios = [Decimal(str(r)) for r in ratios]
        
        # Calculate allocated amounts
        allocated = []
        remainder = self.amount
        
        for i, ratio in enumerate(decimal_ratios):
            if i == len(decimal_ratios) - 1:
                # Last allocation gets the remainder to avoid rounding errors
                allocated.append(Money(remainder, self.currency))
            else:
                amount = (self.amount * ratio / total_ratio).quantize(
                    Decimal('0.01' if self.currency != Currency.JPY else '1'),
                    rounding=ROUND_HALF_UP
                )
                allocated.append(Money(amount, self.currency))
                remainder -= amount
        
        return allocated


def sum_money(money_list: list[Money]) -> Money:
    """
    Sum a list of Money objects.
    
    Args:
        money_list: List of Money objects to sum
        
    Returns:
        Money object with the sum
        
    Raises:
        ValueError: If currencies don't match or list is empty
    """
    if not money_list:
        raise ValueError("Cannot sum empty list of Money")
    
    # Check that all currencies match
    first_currency = money_list[0].currency
    if not all(m.currency == first_currency for m in money_list):
        raise ValueError("All Money objects must have the same currency")
    
    total = Money.zero(first_currency)
    for money in money_list:
        total = total + money
    
    return total


def average_money(money_list: list[Money]) -> Money:
    """
    Calculate average of Money objects.
    
    Args:
        money_list: List of Money objects to average
        
    Returns:
        Money object with the average
        
    Raises:
        ValueError: If currencies don't match or list is empty
    """
    if not money_list:
        raise ValueError("Cannot average empty list of Money")
    
    total = sum_money(money_list)
    return total / len(money_list)