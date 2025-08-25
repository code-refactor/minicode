"""
Currency formatting utilities for financial display.

This module provides functions for formatting currency amounts,
exchange rates, and financial values according to various
locales and display preferences.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, Union
from enum import Enum
import re

# Import from our models
from ..models.money import Money, Currency

# Type alias
Numeric = Union[int, float, Decimal, Money]


class CurrencyFormat(Enum):
    """Currency formatting styles."""
    SYMBOL_BEFORE = "symbol_before"  # $1,234.56
    SYMBOL_AFTER = "symbol_after"   # 1,234.56 USD
    CODE_BEFORE = "code_before"     # USD 1,234.56
    CODE_AFTER = "code_after"       # 1,234.56 USD
    ACCOUNTING = "accounting"       # (1,234.56) for negatives
    COMPACT = "compact"             # $1.2K, $1.2M


class CurrencySymbols:
    """Currency symbols and formatting information."""
    
    SYMBOLS = {
        Currency.USD: {"symbol": "$", "name": "US Dollar", "decimal_places": 2},
        Currency.EUR: {"symbol": "€", "name": "Euro", "decimal_places": 2},
        Currency.GBP: {"symbol": "£", "name": "British Pound", "decimal_places": 2},
        Currency.JPY: {"symbol": "¥", "name": "Japanese Yen", "decimal_places": 0},
        Currency.CAD: {"symbol": "C$", "name": "Canadian Dollar", "decimal_places": 2},
        Currency.AUD: {"symbol": "A$", "name": "Australian Dollar", "decimal_places": 2},
        Currency.CHF: {"symbol": "CHF", "name": "Swiss Franc", "decimal_places": 2},
        Currency.CNY: {"symbol": "¥", "name": "Chinese Yuan", "decimal_places": 2},
        Currency.INR: {"symbol": "₹", "name": "Indian Rupee", "decimal_places": 2},
        Currency.BRL: {"symbol": "R$", "name": "Brazilian Real", "decimal_places": 2},
    }
    
    @classmethod
    def get_symbol(cls, currency: Currency) -> str:
        """Get symbol for currency."""
        return cls.SYMBOLS.get(currency, {}).get("symbol", currency.value)
    
    @classmethod
    def get_decimal_places(cls, currency: Currency) -> int:
        """Get decimal places for currency."""
        return cls.SYMBOLS.get(currency, {}).get("decimal_places", 2)
    
    @classmethod
    def get_name(cls, currency: Currency) -> str:
        """Get full name for currency."""
        return cls.SYMBOLS.get(currency, {}).get("name", currency.value)


def format_currency(
    amount: Numeric,
    currency: Optional[Currency] = None,
    format_style: CurrencyFormat = CurrencyFormat.SYMBOL_BEFORE,
    decimal_places: Optional[int] = None,
    show_thousands_separator: bool = True,
    thousands_separator: str = ",",
    decimal_separator: str = ".",
    negative_style: str = "minus"  # "minus", "parentheses", "red"
) -> str:
    """
    Format a currency amount for display.
    
    Args:
        amount: Amount to format
        currency: Currency (required if amount is not Money)
        format_style: Style of formatting
        decimal_places: Number of decimal places (overrides currency default)
        show_thousands_separator: Whether to show thousands separator
        thousands_separator: Character for thousands separator
        decimal_separator: Character for decimal separator
        negative_style: How to display negative amounts
        
    Returns:
        Formatted currency string
        
    Raises:
        ValueError: If currency is missing for non-Money amounts
    """
    # Extract amount and currency
    if isinstance(amount, Money):
        decimal_amount = amount.amount
        curr = amount.currency
    else:
        if currency is None:
            raise ValueError("Currency must be specified for non-Money amounts")
        decimal_amount = Decimal(str(amount))
        curr = currency
    
    # Determine decimal places
    if decimal_places is None:
        decimal_places = CurrencySymbols.get_decimal_places(curr)
    
    # Round to specified decimal places
    if decimal_places == 0:
        rounded_amount = decimal_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    else:
        quantizer = Decimal('0.' + '0' * decimal_places)
        rounded_amount = decimal_amount.quantize(quantizer, rounding=ROUND_HALF_UP)
    
    # Handle negative amounts
    is_negative = rounded_amount < 0
    abs_amount = abs(rounded_amount)
    
    # Format the numeric part
    if decimal_places == 0:
        amount_str = f"{abs_amount:.0f}"
    else:
        amount_str = f"{abs_amount:.{decimal_places}f}"
    
    # Replace decimal separator if needed
    if decimal_separator != ".":
        amount_str = amount_str.replace(".", decimal_separator)
    
    # Add thousands separator
    if show_thousands_separator and len(amount_str.split(decimal_separator)[0]) > 3:
        parts = amount_str.split(decimal_separator)
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else ""
        
        # Add thousands separators to integer part
        formatted_integer = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_integer = thousands_separator + formatted_integer
            formatted_integer = digit + formatted_integer
        
        amount_str = formatted_integer
        if decimal_part:
            amount_str += decimal_separator + decimal_part
    
    # Get currency symbol/code
    symbol = CurrencySymbols.get_symbol(curr)
    code = curr.value
    
    # Apply format style
    if format_style == CurrencyFormat.SYMBOL_BEFORE:
        formatted = f"{symbol}{amount_str}"
    elif format_style == CurrencyFormat.SYMBOL_AFTER:
        formatted = f"{amount_str} {symbol}"
    elif format_style == CurrencyFormat.CODE_BEFORE:
        formatted = f"{code} {amount_str}"
    elif format_style == CurrencyFormat.CODE_AFTER:
        formatted = f"{amount_str} {code}"
    elif format_style == CurrencyFormat.COMPACT:
        formatted = _format_compact(abs_amount, symbol)
    else:
        formatted = f"{symbol}{amount_str}"
    
    # Apply negative styling
    if is_negative:
        if negative_style == "parentheses" or format_style == CurrencyFormat.ACCOUNTING:
            formatted = f"({formatted})"
        elif negative_style == "minus":
            formatted = f"-{formatted}"
        elif negative_style == "red":
            formatted = f"-{formatted}"  # Color would be handled by UI layer
    
    return formatted


def format_compact_currency(
    amount: Numeric,
    currency: Optional[Currency] = None,
    precision: int = 1
) -> str:
    """
    Format currency in compact notation (K, M, B, T).
    
    Args:
        amount: Amount to format
        currency: Currency (required if amount is not Money)
        precision: Number of decimal places for compact notation
        
    Returns:
        Compact formatted currency string
    """
    # Extract amount and currency
    if isinstance(amount, Money):
        decimal_amount = amount.amount
        curr = amount.currency
    else:
        if currency is None:
            raise ValueError("Currency must be specified for non-Money amounts")
        decimal_amount = Decimal(str(amount))
        curr = currency
    
    return _format_compact(decimal_amount, CurrencySymbols.get_symbol(curr), precision)


def _format_compact(amount: Decimal, symbol: str, precision: int = 1) -> str:
    """Helper function for compact formatting."""
    abs_amount = abs(amount)
    is_negative = amount < 0
    
    if abs_amount >= Decimal('1000000000000'):  # Trillion
        compact_amount = abs_amount / Decimal('1000000000000')
        suffix = "T"
    elif abs_amount >= Decimal('1000000000'):  # Billion
        compact_amount = abs_amount / Decimal('1000000000')
        suffix = "B"
    elif abs_amount >= Decimal('1000000'):  # Million
        compact_amount = abs_amount / Decimal('1000000')
        suffix = "M"
    elif abs_amount >= Decimal('1000'):  # Thousand
        compact_amount = abs_amount / Decimal('1000')
        suffix = "K"
    else:
        # No compacting needed
        if abs_amount == abs_amount.to_integral_value():
            formatted_amount = f"{abs_amount:.0f}"
        else:
            formatted_amount = f"{abs_amount:.2f}".rstrip('0').rstrip('.')
        
        result = f"{symbol}{formatted_amount}"
        return f"-{result}" if is_negative else result
    
    # Format compact amount
    format_str = f"{{:.{precision}f}}"
    formatted_amount = format_str.format(float(compact_amount)).rstrip('0').rstrip('.')
    
    result = f"{symbol}{formatted_amount}{suffix}"
    return f"-{result}" if is_negative else result


def format_exchange_rate(
    rate: Numeric,
    from_currency: Currency,
    to_currency: Currency,
    precision: int = 4,
    style: str = "rate"  # "rate", "conversion"
) -> str:
    """
    Format an exchange rate for display.
    
    Args:
        rate: Exchange rate value
        from_currency: Source currency
        to_currency: Target currency
        precision: Number of decimal places
        style: Format style ("rate" or "conversion")
        
    Returns:
        Formatted exchange rate string
    """
    decimal_rate = Decimal(str(rate))
    quantizer = Decimal('0.' + '0' * precision)
    rounded_rate = decimal_rate.quantize(quantizer, rounding=ROUND_HALF_UP)
    
    if style == "rate":
        return f"1 {from_currency.value} = {rounded_rate} {to_currency.value}"
    elif style == "conversion":
        return f"{from_currency.value}/{to_currency.value}: {rounded_rate}"
    else:
        return str(rounded_rate)


def format_percentage(
    value: Numeric,
    decimal_places: int = 2,
    include_sign: bool = True,
    style: str = "percent"  # "percent", "basis_points"
) -> str:
    """
    Format a percentage value for display.
    
    Args:
        value: Percentage value (as decimal, e.g., 0.15 = 15%)
        decimal_places: Number of decimal places
        include_sign: Whether to include + for positive values
        style: Format style ("percent" or "basis_points")
        
    Returns:
        Formatted percentage string
    """
    decimal_value = Decimal(str(value))
    
    if style == "basis_points":
        # Convert to basis points (10,000 basis points = 100%)
        bp_value = decimal_value * 10000
        quantizer = Decimal('0.01')
        rounded_value = bp_value.quantize(quantizer, rounding=ROUND_HALF_UP)
        
        sign = "+" if include_sign and rounded_value > 0 else ""
        return f"{sign}{rounded_value} bp"
    
    else:  # percent
        # Convert to percentage
        percent_value = decimal_value * 100
        quantizer = Decimal('0.' + '0' * decimal_places)
        rounded_value = percent_value.quantize(quantizer, rounding=ROUND_HALF_UP)
        
        sign = "+" if include_sign and rounded_value > 0 else ""
        return f"{sign}{rounded_value}%"


def parse_currency_string(
    currency_str: str,
    default_currency: Optional[Currency] = None
) -> Dict[str, Any]:
    """
    Parse a currency string to extract amount and currency.
    
    Args:
        currency_str: Currency string to parse (e.g., "$1,234.56", "EUR 100.50")
        default_currency: Default currency if none detected
        
    Returns:
        Dictionary with 'amount' and 'currency' keys
        
    Raises:
        ValueError: If string cannot be parsed
    """
    # Remove whitespace
    cleaned = currency_str.strip()
    
    if not cleaned:
        raise ValueError("Empty currency string")
    
    # Try to detect currency from symbols/codes
    detected_currency = None
    amount_part = cleaned
    
    # Check for currency symbols/codes
    for currency, info in CurrencySymbols.SYMBOLS.items():
        symbol = info["symbol"]
        code = currency.value
        
        # Check if string starts with symbol or code
        if cleaned.startswith(symbol):
            detected_currency = currency
            amount_part = cleaned[len(symbol):].strip()
            break
        elif cleaned.startswith(code):
            detected_currency = currency
            amount_part = cleaned[len(code):].strip()
            break
        
        # Check if string ends with symbol or code
        elif cleaned.endswith(f" {symbol}"):
            detected_currency = currency
            amount_part = cleaned[:-len(f" {symbol}")].strip()
            break
        elif cleaned.endswith(f" {code}"):
            detected_currency = currency
            amount_part = cleaned[:-len(f" {code}")].strip()
            break
    
    # Use default currency if none detected
    if detected_currency is None:
        detected_currency = default_currency
    
    # Clean up amount string
    # Remove common formatting characters
    amount_clean = amount_part.replace(",", "").replace(" ", "")
    
    # Handle parentheses for negative amounts
    is_negative = False
    if amount_clean.startswith("(") and amount_clean.endswith(")"):
        amount_clean = amount_clean[1:-1]
        is_negative = True
    
    # Parse the amount
    try:
        amount = Decimal(amount_clean)
        if is_negative:
            amount = -amount
    except (ValueError, TypeError):
        raise ValueError(f"Cannot parse amount from '{amount_part}'")
    
    return {
        "amount": amount,
        "currency": detected_currency,
        "original_string": currency_str
    }


def format_currency_list(
    amounts: list[Numeric],
    currency: Optional[Currency] = None,
    format_style: CurrencyFormat = CurrencyFormat.SYMBOL_BEFORE,
    total_label: str = "Total"
) -> str:
    """
    Format a list of currency amounts with a total.
    
    Args:
        amounts: List of amounts to format
        currency: Currency (required if amounts are not Money)
        format_style: Formatting style
        total_label: Label for total line
        
    Returns:
        Multi-line formatted currency list
    """
    if not amounts:
        return ""
    
    lines = []
    total = Decimal('0')
    
    # Format individual amounts
    for i, amount in enumerate(amounts, 1):
        if isinstance(amount, Money):
            curr = amount.currency
            decimal_amount = amount.amount
        else:
            if currency is None:
                raise ValueError("Currency must be specified for non-Money amounts")
            curr = currency
            decimal_amount = Decimal(str(amount))
        
        formatted = format_currency(decimal_amount, curr, format_style)
        lines.append(f"{i:2d}. {formatted}")
        total += decimal_amount
    
    # Add separator and total
    if len(lines) > 1:
        lines.append("-" * 20)
        total_formatted = format_currency(
            total,
            amounts[0].currency if isinstance(amounts[0], Money) else currency,
            format_style
        )
        lines.append(f"{total_label}: {total_formatted}")
    
    return "\n".join(lines)


def get_currency_formatting_info(currency: Currency) -> Dict[str, Any]:
    """
    Get formatting information for a currency.
    
    Args:
        currency: Currency to get info for
        
    Returns:
        Dictionary with formatting information
    """
    info = CurrencySymbols.SYMBOLS.get(currency, {})
    
    return {
        "currency": currency,
        "code": currency.value,
        "symbol": info.get("symbol", currency.value),
        "name": info.get("name", currency.value),
        "decimal_places": info.get("decimal_places", 2),
        "symbol_before": True,  # Most currencies show symbol before
        "thousands_separator": ",",
        "decimal_separator": "."
    }