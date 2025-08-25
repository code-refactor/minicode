"""Logging utilities for the legal discovery interpreter."""

import logging
import os
import json
import datetime
from typing import Dict, Any, Optional


class LegalDiscoveryLogger:
    """Logger for legal discovery operations.
    
    This logger ensures that all operations are properly logged for transparency
    and defensibility in court proceedings.
    """
    
    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        file_level: int = logging.INFO,
        console_level: int = logging.WARNING,
        format_string: Optional[str] = None,
    ):
        """Initialize the logger.
        
        Args:
            name: Logger name
            log_dir: Directory to store log files
            file_level: Logging level for file handler
            console_level: Logging level for console handler
            format_string: Custom format string for log messages
        """
        self.name = name
        self.log_dir = log_dir
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Capture all levels
        
        # Create the log directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Set the format string
        if format_string is None:
            format_string = (
                "%(asctime)s [%(levelname)s] %(name)s - "
                "%(message)s (%(filename)s:%(lineno)d)"
            )
        
        formatter = logging.Formatter(format_string)
        
        # Add a file handler
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"{name}-{timestamp}.log")
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Add a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Add a special handler for audit logging
        audit_handler = logging.FileHandler(
            os.path.join(log_dir, f"{name}-audit-{timestamp}.log")
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(formatter)
        self.audit_logger = logging.getLogger(f"{name}.audit")
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.addHandler(audit_handler)
    
    def debug(self, message: str) -> None:
        """Log a debug message.
        
        Args:
            message: Message to log
        """
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log an info message.
        
        Args:
            message: Message to log
        """
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log a warning message.
        
        Args:
            message: Message to log
        """
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """Log an error message.
        
        Args:
            message: Message to log
        """
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """Log a critical message.
        
        Args:
            message: Message to log
        """
        self.logger.critical(message)
    
    def audit(self, action: str, details: Dict[str, Any], user: Optional[str] = None) -> None:
        """Log an audit event.
        
        Args:
            action: Action being audited
            details: Details of the action
            user: User performing the action
        """
        audit_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "action": action,
            "user": user,
            "details": details,
        }
        
        self.audit_logger.info(json.dumps(audit_data))


def get_logger(name: str, **kwargs) -> LegalDiscoveryLogger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        **kwargs: Additional arguments for LegalDiscoveryLogger
        
    Returns:
        Logger instance
    """
    return LegalDiscoveryLogger(name, **kwargs)