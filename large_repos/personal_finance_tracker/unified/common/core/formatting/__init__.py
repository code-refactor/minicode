"""
Formatting utilities for financial data display and serialization.

This package provides formatting functions for currency, dates, and data
serialization that both persona implementations can use for consistent
data presentation and storage.
"""

# Currency formatting
from .currency import (
    CurrencyFormat,
    CurrencySymbols,
    format_currency,
    format_compact_currency,
    format_exchange_rate,
    format_percentage,
    parse_currency_string,
    format_currency_list,
    get_currency_formatting_info,
)

# Date formatting
from .dates import (
    DateFormat,
    TimeFormat,
    format_date,
    format_datetime,
    format_relative_date,
    format_period,
    format_duration,
    format_period_type_name,
    format_business_date_range,
    format_fiscal_period,
    get_quarter_name,
    format_date_list,
)

# Data serialization and formatting
from .data import (
    SerializationFormat,
    DateTimeEncoder,
    datetime_decoder,
    serialize_to_json,
    deserialize_from_json,
    serialize_to_dict,
    flatten_dict,
    serialize_to_csv,
    deserialize_from_csv,
    format_table,
    create_financial_csv_formatter,
    export_data,
    import_data,
)

__all__ = [
    # Currency formatting
    "CurrencyFormat",
    "CurrencySymbols",
    "format_currency",
    "format_compact_currency",
    "format_exchange_rate",
    "format_percentage",
    "parse_currency_string",
    "format_currency_list",
    "get_currency_formatting_info",
    
    # Date formatting
    "DateFormat",
    "TimeFormat",
    "format_date",
    "format_datetime",
    "format_relative_date",
    "format_period",
    "format_duration",
    "format_period_type_name",
    "format_business_date_range",
    "format_fiscal_period",
    "get_quarter_name",
    "format_date_list",
    
    # Data serialization and formatting
    "SerializationFormat",
    "DateTimeEncoder",
    "datetime_decoder",
    "serialize_to_json",
    "deserialize_from_json",
    "serialize_to_dict",
    "flatten_dict",
    "serialize_to_csv",
    "deserialize_from_csv",
    "format_table",
    "create_financial_csv_formatter",
    "export_data",
    "import_data",
]