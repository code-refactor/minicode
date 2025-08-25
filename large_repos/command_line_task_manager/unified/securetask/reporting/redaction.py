"""Redaction engine for sensitive information in security reports."""

import re
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Union, Pattern, Match, Callable


class RedactionLevel(str, Enum):
    """Redaction levels for different audience types."""
    
    NONE = "none"  # No redaction, full details (for internal security team)
    LOW = "low"  # Minimal redaction (for technical teams)
    MEDIUM = "medium"  # Moderate redaction (for management)
    HIGH = "high"  # Heavy redaction (for clients/external parties)
    MAXIMUM = "maximum"  # Maximum redaction (public disclosure)


class RedactionPattern:
    """Pattern for identifying content to redact."""
    
    def __init__(
        self, 
        name: str,
        pattern: Union[str, Pattern],
        replacement: str = "[REDACTED]",
        description: str = "",
        levels: Set[RedactionLevel] = None
    ):
        """
        Initialize a redaction pattern.
        
        Args:
            name: Name of the pattern
            pattern: Regex pattern to match
            replacement: Text to replace matches with
            description: Description of what this pattern matches
            levels: Redaction levels at which to apply this pattern
        """
        self.name = name
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        self.replacement = replacement
        self.description = description
        
        # Default to applying at medium and higher redaction levels
        if levels is None:
            self.levels = {
                RedactionLevel.MEDIUM, 
                RedactionLevel.HIGH, 
                RedactionLevel.MAXIMUM
            }
        else:
            self.levels = set(levels)
    
    def apply(self, text: str, level: RedactionLevel) -> str:
        """
        Apply redaction to text if the current level requires it.
        
        Args:
            text: Text to potentially redact
            level: Current redaction level
            
        Returns:
            Text with redactions applied if needed
        """
        if level in self.levels:
            return self.pattern.sub(self.replacement, text)
        return text
    
    def matches(self, text: str) -> bool:
        """
        Check if this pattern matches any part of the text.
        
        Args:
            text: Text to check
            
        Returns:
            True if pattern matches, False otherwise
        """
        return bool(self.pattern.search(text))


class RedactionEngine:
    """
    Engine for redacting sensitive information in security reports.
    
    Applies different redaction patterns based on the specified
    redaction level and content types.
    """
    
    def __init__(self):
        """Initialize the redaction engine with default patterns."""
        # Create default redaction patterns
        self.patterns: Dict[str, RedactionPattern] = {}
        
        # Add default patterns
        self._add_default_patterns()
    
    def add_pattern(self, pattern: RedactionPattern) -> None:
        """
        Add a redaction pattern to the engine.
        
        Args:
            pattern: The pattern to add
        """
        self.patterns[pattern.name] = pattern
    
    def remove_pattern(self, name: str) -> bool:
        """
        Remove a redaction pattern from the engine.
        
        Args:
            name: Name of the pattern to remove
            
        Returns:
            True if removed, False if not found
        """
        if name in self.patterns:
            del self.patterns[name]
            return True
        return False
    
    def get_pattern(self, name: str) -> Optional[RedactionPattern]:
        """
        Get a redaction pattern by name.
        
        Args:
            name: Name of the pattern to get
            
        Returns:
            The pattern or None if not found
        """
        return self.patterns.get(name)
    
    def redact_text(self, text: str, level: Union[RedactionLevel, str]) -> str:
        """
        Apply all appropriate redaction patterns to text.
        
        Args:
            text: Text to redact
            level: Redaction level to apply
            
        Returns:
            Redacted text
        """
        # Convert string to enum if needed
        if isinstance(level, str):
            level = RedactionLevel(level)
            
        # No redaction needed
        if level == RedactionLevel.NONE:
            return text
            
        # Apply each pattern
        result = text
        for pattern in self.patterns.values():
            result = pattern.apply(result, level)
            
        return result
    
    def redact_dict(
        self,
        data: Dict[str, Any],
        level: Union[RedactionLevel, str],
        field_specific_levels: Optional[Dict[str, Union[RedactionLevel, str]]] = None
    ) -> Dict[str, Any]:
        """
        Redact all string values in a dictionary.

        Args:
            data: Dictionary with data to redact
            level: Default redaction level to apply
            field_specific_levels: Optional dict mapping field names to redaction levels.
                                  Supports dot notation for nested fields (e.g., "parent.child")

        Returns:
            Dictionary with redacted values
        """
        # Convert string to enum if needed
        if isinstance(level, str):
            level = RedactionLevel(level)

        # No field-specific levels defined
        if field_specific_levels is None:
            field_specific_levels = {}

        # Create a new dictionary with redacted values
        result = {}

        for key, value in data.items():
            # Check if there's a specific redaction level for this field
            field_level = field_specific_levels.get(key, level)
            
            # Convert string to enum if needed
            if isinstance(field_level, str):
                field_level = RedactionLevel(field_level)

            # Special handling for sensitive keys
            if key == "password" and field_level != RedactionLevel.NONE:
                result[key] = "[PASSWORD REDACTED]"
            elif key == "token" and field_level != RedactionLevel.NONE:
                result[key] = "[TOKEN REDACTED]"
            elif key == "api_key" and field_level != RedactionLevel.NONE:
                result[key] = "[API KEY REDACTED]"
            # Apply redaction based on value type
            elif isinstance(value, str):
                result[key] = self.redact_text(value, field_level)
            elif isinstance(value, dict):
                # For nested dictionaries, extract any field-specific levels for children
                # using dot notation (e.g., "parent.child")
                nested_field_levels = {}
                prefix = f"{key}."
                for field_key, field_value in field_specific_levels.items():
                    if field_key.startswith(prefix):
                        # Strip the prefix to get the child key
                        child_key = field_key[len(prefix):]
                        nested_field_levels[child_key] = field_value
                
                result[key] = self.redact_dict(value, field_level, nested_field_levels)
            elif isinstance(value, list):
                result[key] = self.redact_list(value, field_level)
            else:
                # Non-string values are kept as is
                result[key] = value

        return result
    
    def redact_list(
        self, 
        data: List[Any], 
        level: Union[RedactionLevel, str]
    ) -> List[Any]:
        """
        Redact all string values in a list.
        
        Args:
            data: List with data to redact
            level: Redaction level to apply
            
        Returns:
            List with redacted values
        """
        # Convert string to enum if needed
        if isinstance(level, str):
            level = RedactionLevel(level)
            
        # Create a new list with redacted values
        result = []
        
        for item in data:
            if isinstance(item, str):
                result.append(self.redact_text(item, level))
            elif isinstance(item, dict):
                result.append(self.redact_dict(item, level))
            elif isinstance(item, list):
                result.append(self.redact_list(item, level))
            else:
                # Non-string values are kept as is
                result.append(item)
                
        return result
    
    def _add_default_patterns(self) -> None:
        """Add default redaction patterns to the engine."""
        # IP Addresses
        self.add_pattern(RedactionPattern(
            name="ip_address",
            pattern=r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            replacement="[IP REDACTED]",
            description="IP address",
            levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Internal hostnames
        self.add_pattern(RedactionPattern(
            name="internal_hostname",
            pattern=r"\b([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+internal\b",
            replacement="[HOSTNAME REDACTED]",
            description="Internal hostname",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))

        # Domain hostnames
        self.add_pattern(RedactionPattern(
            name="domain_hostname",
            pattern=r"\b([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+example\.com\b",
            replacement="[HOSTNAME REDACTED]",
            description="Domain hostname",
            levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # URLs with credentials
        self.add_pattern(RedactionPattern(
            name="url_credentials",
            pattern=r"(https?|ftp)://[^:]+:[^@]+@",
            replacement="\\1://[CREDENTIALS REDACTED]@",
            description="URL with embedded credentials",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Email addresses
        self.add_pattern(RedactionPattern(
            name="email_address",
            pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            replacement="[EMAIL REDACTED]",
            description="Email address",
            levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # API Keys and Tokens
        self.add_pattern(RedactionPattern(
            name="api_key",
            pattern=r"\b(api[_-]?key|token|secret)[=:]\s*['\"]?[A-Za-z0-9+/=]{16,}['\"]?",
            replacement="\\1=[API KEY REDACTED]",
            description="API key or token",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Passwords in code or config
        self.add_pattern(RedactionPattern(
            name="password_in_code",
            pattern=r"(password|passwd|pwd)\s*[=:]\s*[\"\']?([^\"\'\n}]*)[\"\']?",
            replacement="\\1=[PASSWORD REDACTED]",
            description="Password in code or configuration",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Passwords in JSON
        self.add_pattern(RedactionPattern(
            name="password_in_json",
            pattern=r"\"(password|passwd|pwd)\"\s*:\s*\"([^\"]+)\"",
            replacement="\"\\1\":\"[PASSWORD REDACTED]\"",
            description="Password in JSON data",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Passwords in XML
        self.add_pattern(RedactionPattern(
            name="password_in_xml",
            pattern=r"<(password|passwd|pwd)>(.*?)</(password|passwd|pwd)>",
            replacement="<\\1>[PASSWORD REDACTED]</\\3>",
            description="Password in XML data",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))

        # Passwords in URLs
        self.add_pattern(RedactionPattern(
            name="password_in_url",
            pattern=r"(password|passwd|pwd)=(.*?)(&|$)",
            replacement="\\1=[PASSWORD REDACTED]\\3",
            description="Password in URL",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Private keys in code (SSH, etc.)
        self.add_pattern(RedactionPattern(
            name="private_key",
            pattern=r"-----BEGIN ([A-Z]+ )?PRIVATE KEY-----[\s\S]*?-----END ([A-Z]+ )?PRIVATE KEY-----",
            replacement="[PRIVATE KEY REDACTED]",
            description="Private key block",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Database connection strings
        self.add_pattern(RedactionPattern(
            name="db_connection",
            pattern=r"jdbc:mysql:\/\/.*?user=.*?&password=.*?($|\s)",
            replacement="[DB CONNECTION REDACTED]",
            description="Database connection string",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Credit card numbers
        self.add_pattern(RedactionPattern(
            name="credit_card",
            pattern=r"\b(?:\d{4}[- ]){3}\d{4}\b|\b\d{16}\b",
            replacement="[CREDIT CARD REDACTED]",
            description="Credit card number",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Social Security Numbers
        self.add_pattern(RedactionPattern(
            name="ssn",
            pattern=r"\b\d{3}-\d{2}-\d{4}\b",
            replacement="[SSN REDACTED]",
            description="Social Security Number",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Authentication details
        self.add_pattern(RedactionPattern(
            name="auth_details",
            pattern=r"authorization\s*:\s*\w+\s+[A-Za-z0-9+/=]+",
            replacement="Authorization: [AUTH REDACTED]",
            description="Authorization header",
            levels={RedactionLevel.LOW, RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Customer identifiers
        self.add_pattern(RedactionPattern(
            name="customer_id",
            pattern=r"customer[_-]?id[=:]\s*['\"](.*?)['\"]",
            replacement="customer_id=[CUSTOMER ID REDACTED]",
            description="Customer identifier",
            levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Internal resource paths
        self.add_pattern(RedactionPattern(
            name="internal_path",
            pattern=r"/var/www/.*?/|/home/[^/]+/|/srv/.*?/|/opt/.*?/",
            replacement="[PATH REDACTED]/",
            description="Internal server path",
            levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # Usernames
        self.add_pattern(RedactionPattern(
            name="username",
            pattern=r"username[=:]\s*['\"](.*?)['\"]",
            replacement="username=[USERNAME REDACTED]",
            description="Username in code or configuration",
            levels={RedactionLevel.MEDIUM, RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))
        
        # exploit code
        self.add_pattern(RedactionPattern(
            name="exploit_code",
            pattern=r"(function\s+exploit|def\s+exploit|\bexploit_payload\b|\bshellcode\b)",
            replacement="[EXPLOIT CODE REDACTED]",
            description="Exploit code",
            levels={RedactionLevel.HIGH, RedactionLevel.MAXIMUM}
        ))