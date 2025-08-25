"""
Configuration module for GameVault.

This module contains configuration classes and constants used throughout the system.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field


class GameVaultConfig(BaseModel):
    """Main configuration for the GameVault backup system."""
    
    # Base directory where all backups will be stored
    backup_dir: Path = Field(
        default_factory=lambda: Path.home() / ".gamevault",
        description="Directory where all backups will be stored"
    )
    
    # Maximum chunk size for binary files (in bytes)
    max_chunk_size: int = Field(
        default=4 * 1024 * 1024,  # 4MB
        description="Maximum chunk size for binary files in bytes"
    )
    
    # Minimum chunk size for binary files (in bytes)
    min_chunk_size: int = Field(
        default=64 * 1024,  # 64KB
        description="Minimum chunk size for binary files in bytes"
    )
    
    # Compression level (0-22 for zstd)
    compression_level: int = Field(
        default=3,
        ge=0,
        le=22,
        description="Compression level for stored data (0-22 for zstd)"
    )
    
    # File patterns to ignore
    ignore_patterns: List[str] = Field(
        default_factory=lambda: [
            "*.tmp", "*.temp", "*.log", "*.bak",
            ".git/*", ".svn/*", ".vscode/*", ".idea/*",
            "__pycache__/*", "*.pyc",
            "Temp/*", "Library/PackageCache/*",  # Unity specific
            "Saved/*", "Intermediate/*"  # Unreal specific
        ],
        description="File patterns to ignore during backup"
    )
    
    # File extensions to treat as binary
    binary_extensions: Set[str] = Field(
        default_factory=lambda: {
            # Images
            ".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".psd", ".tif", ".tiff",
            # 3D Models
            ".fbx", ".obj", ".blend", ".dae", ".3ds", ".max",
            # Audio
            ".wav", ".mp3", ".ogg", ".flac", ".aif", ".aiff",
            # Video
            ".mp4", ".avi", ".mov", ".wmv", ".webm",
            # Game Engines
            ".unity", ".uasset", ".umap",  # Unity and Unreal
            # Other Binary Formats
            ".zip", ".rar", ".7z", ".tar", ".gz", ".exe", ".dll",
            # Game-specific binary assets
            ".asset", ".prefab", ".controller", ".anim",  # Unity
            ".pak", ".cube", ".upk"  # Unreal and others
        },
        description="File extensions to treat as binary files"
    )
    
    # Default platforms to track
    default_platforms: List[str] = Field(
        default_factory=lambda: ["pc", "mobile", "console"],
        description="Default platforms to track for configuration management"
    )


# Singleton instance that can be imported and used throughout the codebase
default_config = GameVaultConfig()


def get_config() -> GameVaultConfig:
    """
    Get the current configuration.
    
    Returns:
        GameVaultConfig: The current configuration instance
    """
    return default_config


def configure(config_dict: Dict) -> GameVaultConfig:
    """
    Update the configuration with new values.
    
    Args:
        config_dict: Dictionary of configuration values to update
    
    Returns:
        GameVaultConfig: The updated configuration instance
    """
    global default_config
    default_config = GameVaultConfig(**{**default_config.model_dump(), **config_dict})
    
    # Ensure backup directory exists
    os.makedirs(default_config.backup_dir, exist_ok=True)
    
    return default_config