"""
Configuration management patterns for financial applications.

This module provides flexible configuration management with validation,
environment support, and hierarchical configuration loading.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Type, Callable, Set
from dataclasses import dataclass, field, fields
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import json
import os
from pathlib import Path
import logging

# Import from our core modules
from ..core.validation import ValidationResult, validate_required, validate_type
from ..core.models import Currency

# Set up logging
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""
    pass


class Environment(Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ConfigField:
    """Configuration field definition with validation."""
    name: str
    field_type: Type
    required: bool = False
    default: Any = None
    description: str = ""
    validator: Optional[Callable[[Any], bool]] = None
    choices: Optional[List[Any]] = None
    min_value: Optional[Union[int, float, Decimal]] = None
    max_value: Optional[Union[int, float, Decimal]] = None
    
    def validate_value(self, value: Any) -> ValidationResult:
        """Validate a value against this field definition."""
        result = ValidationResult(True)
        
        # Check required
        if self.required and value is None:
            result.add_error(f"Field '{self.name}' is required")
            return result
        
        # Skip other validation if value is None and not required
        if value is None:
            return result
        
        # Check type
        try:
            validate_type(value, self.field_type, self.name)
        except Exception as e:
            result.add_error(str(e))
            return result
        
        # Check choices
        if self.choices is not None and value not in self.choices:
            result.add_error(f"Field '{self.name}' must be one of {self.choices}, got {value}")
        
        # Check numeric ranges
        if isinstance(value, (int, float, Decimal)):
            if self.min_value is not None and value < self.min_value:
                result.add_error(f"Field '{self.name}' must be >= {self.min_value}, got {value}")
            
            if self.max_value is not None and value > self.max_value:
                result.add_error(f"Field '{self.name}' must be <= {self.max_value}, got {value}")
        
        # Custom validator
        if self.validator is not None:
            try:
                if not self.validator(value):
                    result.add_error(f"Field '{self.name}' failed custom validation")
            except Exception as e:
                result.add_error(f"Field '{self.name}' validation error: {e}")
        
        return result


class BaseConfiguration(ABC):
    """
    Abstract base class for application configurations.
    
    Provides common patterns for loading, validating, and managing
    configuration data with environment support.
    """
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration.
        
        Args:
            data: Configuration data dictionary
        """
        self._data = data or {}
        self._fields = self._define_fields()
        self._load_defaults()
    
    @abstractmethod
    def _define_fields(self) -> Dict[str, ConfigField]:
        """Define configuration fields. Override in subclasses."""
        pass
    
    def _load_defaults(self) -> None:
        """Load default values for fields."""
        for field_name, field_def in self._fields.items():
            if field_name not in self._data and field_def.default is not None:
                self._data[field_name] = field_def.default
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value with validation.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Raises:
            ConfigurationError: If validation fails
        """
        if key in self._fields:
            validation_result = self._fields[key].validate_value(value)
            if not validation_result.is_valid:
                raise ConfigurationError(f"Validation failed for {key}: {validation_result.errors}")
        
        self._data[key] = value
        logger.debug(f"Set configuration: {key} = {value}")
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        Update multiple configuration values.
        
        Args:
            data: Dictionary of configuration updates
            
        Raises:
            ConfigurationError: If any validation fails
        """
        # Validate all values first
        errors = []
        for key, value in data.items():
            if key in self._fields:
                validation_result = self._fields[key].validate_value(value)
                if not validation_result.is_valid:
                    errors.extend([f"{key}: {error}" for error in validation_result.errors])
        
        if errors:
            raise ConfigurationError("Configuration validation failed: " + "; ".join(errors))
        
        # Apply updates
        self._data.update(data)
        logger.debug(f"Updated configuration with {len(data)} values")
    
    def validate(self) -> ValidationResult:
        """
        Validate entire configuration.
        
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(True)
        
        # Check all defined fields
        for field_name, field_def in self._fields.items():
            value = self._data.get(field_name)
            field_result = field_def.validate_value(value)
            
            if not field_result.is_valid:
                result.errors.extend([f"{field_name}: {error}" for error in field_result.errors])
                result.is_valid = False
        
        # Check for undefined fields
        undefined_fields = set(self._data.keys()) - set(self._fields.keys())
        for field in undefined_fields:
            result.add_warning(f"Undefined configuration field: {field}")
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self._data.copy()
    
    def get_field_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all configuration fields."""
        field_info = {}
        
        for field_name, field_def in self._fields.items():
            field_info[field_name] = {
                "type": field_def.field_type.__name__,
                "required": field_def.required,
                "default": field_def.default,
                "description": field_def.description,
                "choices": field_def.choices,
                "min_value": field_def.min_value,
                "max_value": field_def.max_value,
                "current_value": self._data.get(field_name)
            }
        
        return field_info
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._data.clear()
        self._load_defaults()
        logger.info("Reset configuration to defaults")


class FinancialConfiguration(BaseConfiguration):
    """
    Configuration for financial applications.
    
    Provides common financial settings like default currency,
    calculation precision, and formatting options.
    """
    
    def _define_fields(self) -> Dict[str, ConfigField]:
        """Define financial configuration fields."""
        return {
            "default_currency": ConfigField(
                name="default_currency",
                field_type=str,
                required=True,
                default="USD",
                description="Default currency for transactions",
                choices=[c.value for c in Currency]
            ),
            
            "decimal_precision": ConfigField(
                name="decimal_precision",
                field_type=int,
                default=2,
                description="Number of decimal places for calculations",
                min_value=0,
                max_value=10
            ),
            
            "tax_year_start_month": ConfigField(
                name="tax_year_start_month",
                field_type=int,
                default=1,
                description="Starting month of tax year (1-12)",
                min_value=1,
                max_value=12
            ),
            
            "fiscal_year_start_month": ConfigField(
                name="fiscal_year_start_month",
                field_type=int,
                default=1,
                description="Starting month of fiscal year (1-12)",
                min_value=1,
                max_value=12
            ),
            
            "enable_caching": ConfigField(
                name="enable_caching",
                field_type=bool,
                default=True,
                description="Enable calculation caching"
            ),
            
            "cache_ttl_seconds": ConfigField(
                name="cache_ttl_seconds",
                field_type=int,
                default=3600,
                description="Cache time-to-live in seconds",
                min_value=60
            ),
            
            "date_format": ConfigField(
                name="date_format",
                field_type=str,
                default="iso",
                description="Default date format for display",
                choices=["iso", "us", "european", "long", "short"]
            ),
            
            "currency_format": ConfigField(
                name="currency_format",
                field_type=str,
                default="symbol_before",
                description="Default currency format for display",
                choices=["symbol_before", "symbol_after", "code_before", "code_after"]
            ),
            
            "batch_size": ConfigField(
                name="batch_size",
                field_type=int,
                default=1000,
                description="Default batch size for processing operations",
                min_value=1,
                max_value=10000
            ),
            
            "max_transaction_amount": ConfigField(
                name="max_transaction_amount",
                field_type=float,
                default=1000000.0,
                description="Maximum allowed transaction amount",
                min_value=0.01
            ),
            
            "default_tax_rate": ConfigField(
                name="default_tax_rate",
                field_type=float,
                default=0.25,
                description="Default tax rate as decimal (0.25 = 25%)",
                min_value=0.0,
                max_value=1.0
            )
        }
    
    @property
    def default_currency(self) -> Currency:
        """Get default currency as Currency enum."""
        return Currency(self.get("default_currency"))
    
    @property
    def decimal_precision(self) -> int:
        """Get decimal precision."""
        return self.get("decimal_precision", 2)
    
    @property
    def tax_year_start_month(self) -> int:
        """Get tax year start month."""
        return self.get("tax_year_start_month", 1)
    
    @property
    def fiscal_year_start_month(self) -> int:
        """Get fiscal year start month."""
        return self.get("fiscal_year_start_month", 1)


class ConfigurationManager:
    """
    Manages multiple configurations with environment support.
    
    Provides hierarchical configuration loading from files,
    environment variables, and programmatic sources.
    """
    
    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        """
        Initialize configuration manager.
        
        Args:
            environment: Current application environment
        """
        self.environment = environment
        self.configurations: Dict[str, BaseConfiguration] = {}
        self._config_paths: List[Path] = []
        self._env_prefix = "APP_"
    
    def set_environment_prefix(self, prefix: str) -> None:
        """Set prefix for environment variables."""
        self._env_prefix = prefix
    
    def add_config_path(self, path: Union[str, Path]) -> None:
        """Add a configuration file path."""
        config_path = Path(path)
        if config_path.exists():
            self._config_paths.append(config_path)
            logger.debug(f"Added config path: {config_path}")
        else:
            logger.warning(f"Config path does not exist: {config_path}")
    
    def register_configuration(self, name: str, config_class: Type[BaseConfiguration]) -> None:
        """
        Register a configuration class.
        
        Args:
            name: Configuration name
            config_class: Configuration class to register
        """
        # Load configuration data
        config_data = self._load_configuration_data(name)
        
        # Create configuration instance
        config = config_class(config_data)
        
        # Validate configuration
        validation_result = config.validate()
        if not validation_result.is_valid:
            logger.warning(f"Configuration validation failed for {name}: {validation_result.errors}")
        
        if validation_result.warnings:
            logger.warning(f"Configuration warnings for {name}: {validation_result.warnings}")
        
        self.configurations[name] = config
        logger.info(f"Registered configuration: {name}")
    
    def get_configuration(self, name: str) -> Optional[BaseConfiguration]:
        """Get configuration by name."""
        return self.configurations.get(name)
    
    def _load_configuration_data(self, config_name: str) -> Dict[str, Any]:
        """Load configuration data from various sources."""
        data = {}
        
        # 1. Load from configuration files
        for config_path in self._config_paths:
            file_data = self._load_from_file(config_path, config_name)
            if file_data:
                data.update(file_data)
        
        # 2. Load environment-specific overrides
        env_data = self._load_environment_specific(config_name)
        if env_data:
            data.update(env_data)
        
        # 3. Load from environment variables
        env_vars = self._load_from_environment_variables(config_name)
        if env_vars:
            data.update(env_vars)
        
        logger.debug(f"Loaded configuration data for {config_name}: {len(data)} settings")
        return data
    
    def _load_from_file(self, config_path: Path, config_name: str) -> Optional[Dict[str, Any]]:
        """Load configuration from a file."""
        try:
            if config_path.suffix.lower() == '.json':
                with open(config_path, 'r') as f:
                    all_config = json.load(f)
                
                # Look for config_name section
                if config_name in all_config:
                    return all_config[config_name]
                elif "default" in all_config:
                    return all_config["default"]
                else:
                    return all_config
            
            else:
                logger.warning(f"Unsupported config file format: {config_path}")
                return None
        
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return None
    
    def _load_environment_specific(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Load environment-specific configuration overrides."""
        env_config_name = f"{config_name}_{self.environment.value}"
        
        for config_path in self._config_paths:
            env_data = self._load_from_file(config_path, env_config_name)
            if env_data:
                logger.debug(f"Loaded environment-specific config for {env_config_name}")
                return env_data
        
        return None
    
    def _load_from_environment_variables(self, config_name: str) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_data = {}
        prefix = f"{self._env_prefix}{config_name.upper()}_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                
                # Try to convert to appropriate type
                converted_value = self._convert_env_value(value)
                env_data[config_key] = converted_value
        
        if env_data:
            logger.debug(f"Loaded {len(env_data)} values from environment variables")
        
        return env_data
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def validate_all(self) -> Dict[str, ValidationResult]:
        """Validate all registered configurations."""
        validation_results = {}
        
        for name, config in self.configurations.items():
            validation_results[name] = config.validate()
        
        return validation_results
    
    def get_all_field_info(self) -> Dict[str, Dict[str, Any]]:
        """Get field information for all configurations."""
        all_info = {}
        
        for name, config in self.configurations.items():
            all_info[name] = config.get_field_info()
        
        return all_info
    
    def export_configuration(self, config_name: str, file_path: Union[str, Path]) -> None:
        """
        Export configuration to file.
        
        Args:
            config_name: Name of configuration to export
            file_path: Path to save configuration file
            
        Raises:
            ConfigurationError: If configuration not found
        """
        config = self.get_configuration(config_name)
        if config is None:
            raise ConfigurationError(f"Configuration not found: {config_name}")
        
        export_path = Path(file_path)
        
        try:
            with open(export_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2, default=str)
            
            logger.info(f"Exported configuration {config_name} to {export_path}")
        
        except Exception as e:
            raise ConfigurationError(f"Failed to export configuration: {e}")


# Global configuration manager instance
_global_config_manager: Optional[ConfigurationManager] = None


def get_global_config_manager() -> ConfigurationManager:
    """Get or create the global configuration manager."""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigurationManager()
    return _global_config_manager


def setup_default_configurations(
    environment: Environment = Environment.DEVELOPMENT,
    config_paths: Optional[List[Union[str, Path]]] = None
) -> ConfigurationManager:
    """
    Set up default configurations for financial applications.
    
    Args:
        environment: Application environment
        config_paths: Optional list of configuration file paths
        
    Returns:
        Configured ConfigurationManager
    """
    config_manager = ConfigurationManager(environment)
    
    # Add default config paths
    if config_paths:
        for path in config_paths:
            config_manager.add_config_path(path)
    else:
        # Look for default config files
        default_paths = [
            Path("config.json"),
            Path("config") / "config.json",
            Path.home() / ".config" / "financial_app" / "config.json"
        ]
        
        for path in default_paths:
            if path.exists():
                config_manager.add_config_path(path)
    
    # Register financial configuration
    config_manager.register_configuration("financial", FinancialConfiguration)
    
    return config_manager


class DynamicConfiguration(BaseConfiguration):
    """
    Configuration that can be modified at runtime.
    
    Supports adding and removing fields dynamically,
    useful for plugin-based architectures.
    """
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._dynamic_fields: Dict[str, ConfigField] = {}
        super().__init__(data)
    
    def _define_fields(self) -> Dict[str, ConfigField]:
        """Base fields - can be extended dynamically."""
        return {}
    
    def add_field(self, field: ConfigField) -> None:
        """
        Add a field dynamically.
        
        Args:
            field: ConfigField to add
        """
        self._dynamic_fields[field.name] = field
        self._fields[field.name] = field
        
        # Set default value if provided and not already set
        if field.default is not None and field.name not in self._data:
            self._data[field.name] = field.default
        
        logger.debug(f"Added dynamic field: {field.name}")
    
    def remove_field(self, field_name: str) -> None:
        """
        Remove a field dynamically.
        
        Args:
            field_name: Name of field to remove
        """
        if field_name in self._dynamic_fields:
            del self._dynamic_fields[field_name]
            del self._fields[field_name]
            
            # Remove value if it exists
            if field_name in self._data:
                del self._data[field_name]
            
            logger.debug(f"Removed dynamic field: {field_name}")
    
    def get_dynamic_fields(self) -> Dict[str, ConfigField]:
        """Get all dynamically added fields."""
        return self._dynamic_fields.copy()