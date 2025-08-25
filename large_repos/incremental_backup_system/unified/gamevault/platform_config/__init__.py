"""
Platform Configuration Tracker for GameVault.

This package provides tools for managing and comparing game settings across
different target platforms, making it easier to identify platform-specific issues.
"""

from gamevault.platform_config.manager import PlatformConfigManager

__all__ = [
    'PlatformConfigManager',
]