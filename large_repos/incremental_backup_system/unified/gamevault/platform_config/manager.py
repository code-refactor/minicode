"""
Platform Configuration Tracker module for GameVault.

This module manages tracking of game configurations across different platforms.
"""

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from gamevault.config import get_config
from gamevault.models import PlatformConfig, PlatformType
from gamevault.utils import generate_timestamp


class PlatformConfigManager:
    """
    Manager for tracking platform-specific configurations.
    
    This class provides functionality for managing and comparing game settings
    across different target platforms.
    """
    
    def __init__(
        self,
        project_name: str,
        storage_dir: Optional[Union[str, Path]] = None
    ):
        """
        Initialize the platform configuration manager.
        
        Args:
            project_name: Name of the project
            storage_dir: Directory where configuration data will be stored. If None, uses the default from config.
        """
        config = get_config()
        self.project_name = project_name
        self.storage_dir = Path(storage_dir) if storage_dir else config.backup_dir
        
        # Directory for configuration storage
        self.config_dir = self.storage_dir / "platforms" / project_name
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Metadata file
        self.metadata_file = self.config_dir / "metadata.json"
        self._init_metadata()
    
    def _init_metadata(self) -> None:
        """
        Initialize or load metadata.
        """
        if self.metadata_file.exists():
            with open(self.metadata_file, "r") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "project": self.project_name,
                "platforms": [],
                "versions": [],
                "created_at": generate_timestamp(),
                "updated_at": generate_timestamp()
            }
            self._save_metadata()
    
    def _save_metadata(self) -> None:
        """
        Save metadata to disk.
        """
        self.metadata["updated_at"] = generate_timestamp()
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)
    
    def _get_config_path(self, platform: Union[str, PlatformType], version: str) -> Path:
        """
        Get the path to a platform configuration file.
        
        Args:
            platform: Platform identifier
            version: Configuration version
            
        Returns:
            Path: Path to the configuration file
        """
        if isinstance(platform, PlatformType):
            platform = platform.value
        
        return self.config_dir / f"{platform}_{version}.json"
    
    def list_platforms(self) -> List[str]:
        """
        List available platforms.
        
        Returns:
            List[str]: List of platform identifiers
        """
        return self.metadata.get("platforms", [])
    
    def list_versions(self, platform: Optional[Union[str, PlatformType]] = None) -> List[Dict[str, Any]]:
        """
        List available configuration versions.
        
        Args:
            platform: Filter by platform
            
        Returns:
            List[Dict[str, Any]]: List of version information
        """
        versions = self.metadata.get("versions", [])
        
        if platform:
            if isinstance(platform, PlatformType):
                platform = platform.value
            
            versions = [v for v in versions if platform in v.get("platforms", [])]
        
        return versions
    
    def save_config(
        self,
        config: PlatformConfig,
        version: str,
        description: Optional[str] = None
    ) -> str:
        """
        Save a platform configuration.
        
        Args:
            config: Platform configuration
            version: Configuration version
            description: Optional description of the configuration
            
        Returns:
            str: Path to the saved configuration file
        """
        platform = config.platform.value if isinstance(config.platform, PlatformType) else config.platform
        
        # Update metadata
        if platform not in self.metadata["platforms"]:
            self.metadata["platforms"].append(platform)
        
        # Check if version exists
        version_exists = False
        for v in self.metadata["versions"]:
            if v["version"] == version:
                version_exists = True
                if platform not in v["platforms"]:
                    v["platforms"].append(platform)
                break
        
        if not version_exists:
            self.metadata["versions"].append({
                "version": version,
                "platforms": [platform],
                "timestamp": generate_timestamp(),
                "description": description
            })
        
        self._save_metadata()
        
        # Save configuration
        config_path = self._get_config_path(platform, version)
        with open(config_path, "w") as f:
            # Convert the model to a dict and ensure sets are converted to lists for JSON serialization
            config_dict = config.model_dump()
            if "required_features" in config_dict and isinstance(config_dict["required_features"], set):
                config_dict["required_features"] = list(config_dict["required_features"])
            if "disabled_features" in config_dict and isinstance(config_dict["disabled_features"], set):
                config_dict["disabled_features"] = list(config_dict["disabled_features"])
            json.dump(config_dict, f, indent=2)
        
        return str(config_path)
    
    def get_config(
        self,
        platform: Union[str, PlatformType],
        version: str
    ) -> Optional[PlatformConfig]:
        """
        Get a platform configuration.
        
        Args:
            platform: Platform identifier
            version: Configuration version
            
        Returns:
            Optional[PlatformConfig]: The platform configuration, or None if not found
        """
        if isinstance(platform, PlatformType):
            platform = platform.value
        
        config_path = self._get_config_path(platform, version)
        
        if not config_path.exists():
            return None
        
        with open(config_path, "r") as f:
            config_data = json.load(f)
        
        return PlatformConfig.model_validate(config_data)
    
    def compare_configs(
        self,
        platform1: Union[str, PlatformType],
        version1: str,
        platform2: Union[str, PlatformType],
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two platform configurations.
        
        Args:
            platform1: First platform identifier
            version1: First configuration version
            platform2: Second platform identifier
            version2: Second configuration version
            
        Returns:
            Dict[str, Any]: Comparison results
            
        Raises:
            ValueError: If either configuration doesn't exist
        """
        # Get configurations
        config1 = self.get_config(platform1, version1)
        config2 = self.get_config(platform2, version2)
        
        if config1 is None:
            raise ValueError(f"Configuration for {platform1} version {version1} not found")
        
        if config2 is None:
            raise ValueError(f"Configuration for {platform2} version {version2} not found")
        
        # Convert platform to string if needed
        if isinstance(platform1, PlatformType):
            platform1 = platform1.value
        
        if isinstance(platform2, PlatformType):
            platform2 = platform2.value
        
        # Compare settings
        settings1 = config1.settings
        settings2 = config2.settings
        
        # Find differences
        common_keys = set(settings1.keys()) & set(settings2.keys())
        only_in_1 = set(settings1.keys()) - set(settings2.keys())
        only_in_2 = set(settings2.keys()) - set(settings1.keys())
        
        different_values = {}
        for key in common_keys:
            if settings1[key] != settings2[key]:
                different_values[key] = {
                    platform1: settings1[key],
                    platform2: settings2[key]
                }
        
        # Compare build flags
        flags1 = config1.build_flags
        flags2 = config2.build_flags
        
        common_flags = set(flags1.keys()) & set(flags2.keys())
        only_in_1_flags = set(flags1.keys()) - set(flags2.keys())
        only_in_2_flags = set(flags2.keys()) - set(flags1.keys())
        
        different_flags = {}
        for key in common_flags:
            if flags1[key] != flags2[key]:
                different_flags[key] = {
                    platform1: flags1[key],
                    platform2: flags2[key]
                }
        
        # Compare features
        required1 = config1.required_features
        required2 = config2.required_features
        
        common_required = required1 & required2
        only_in_1_required = required1 - required2
        only_in_2_required = required2 - required1
        
        disabled1 = config1.disabled_features
        disabled2 = config2.disabled_features
        
        common_disabled = disabled1 & disabled2
        only_in_1_disabled = disabled1 - disabled2
        only_in_2_disabled = disabled2 - disabled1
        
        # Compare resolution and performance targets
        resolution_diff = {}
        if config1.resolution and config2.resolution:
            for key in set(config1.resolution.keys()) | set(config2.resolution.keys()):
                val1 = config1.resolution.get(key)
                val2 = config2.resolution.get(key)
                if val1 != val2:
                    resolution_diff[key] = {
                        platform1: val1,
                        platform2: val2
                    }
        elif config1.resolution or config2.resolution:
            resolution_diff = {
                "missing_in": platform2 if config1.resolution else platform1
            }
        
        performance_diff = {}
        if config1.performance_targets and config2.performance_targets:
            for key in set(config1.performance_targets.keys()) | set(config2.performance_targets.keys()):
                val1 = config1.performance_targets.get(key)
                val2 = config2.performance_targets.get(key)
                if val1 != val2:
                    performance_diff[key] = {
                        platform1: val1,
                        platform2: val2
                    }
        elif config1.performance_targets or config2.performance_targets:
            performance_diff = {
                "missing_in": platform2 if config1.performance_targets else platform1
            }
        
        return {
            "platforms": {
                "platform1": {
                    "id": platform1,
                    "version": version1,
                },
                "platform2": {
                    "id": platform2,
                    "version": version2,
                }
            },
            "settings": {
                "common_count": len(common_keys),
                "only_in_platform1_count": len(only_in_1),
                "only_in_platform2_count": len(only_in_2),
                "different_values_count": len(different_values),
                "only_in_platform1": list(only_in_1),
                "only_in_platform2": list(only_in_2),
                "different_values": different_values
            },
            "build_flags": {
                "common_count": len(common_flags),
                "only_in_platform1_count": len(only_in_1_flags),
                "only_in_platform2_count": len(only_in_2_flags),
                "different_values_count": len(different_flags),
                "only_in_platform1": list(only_in_1_flags),
                "only_in_platform2": list(only_in_2_flags),
                "different_values": different_flags
            },
            "features": {
                "required": {
                    "common_count": len(common_required),
                    "only_in_platform1_count": len(only_in_1_required),
                    "only_in_platform2_count": len(only_in_2_required),
                    "common": list(common_required),
                    "only_in_platform1": list(only_in_1_required),
                    "only_in_platform2": list(only_in_2_required)
                },
                "disabled": {
                    "common_count": len(common_disabled),
                    "only_in_platform1_count": len(only_in_1_disabled),
                    "only_in_platform2_count": len(only_in_2_disabled),
                    "common": list(common_disabled),
                    "only_in_platform1": list(only_in_1_disabled),
                    "only_in_platform2": list(only_in_2_disabled)
                }
            },
            "resolution": resolution_diff,
            "performance_targets": performance_diff,
            "total_differences": (
                len(different_values) + 
                len(only_in_1) + 
                len(only_in_2) + 
                len(different_flags) + 
                len(only_in_1_flags) + 
                len(only_in_2_flags) + 
                len(only_in_1_required) + 
                len(only_in_2_required) + 
                len(only_in_1_disabled) + 
                len(only_in_2_disabled) + 
                len(resolution_diff) + 
                len(performance_diff)
            )
        }
    
    def compare_platforms(
        self,
        version: str,
        platforms: Optional[List[Union[str, PlatformType]]] = None
    ) -> Dict[str, Any]:
        """
        Compare configurations across multiple platforms for the same version.
        
        Args:
            version: Configuration version
            platforms: List of platforms to compare. If None, compares all available platforms.
            
        Returns:
            Dict[str, Any]: Comparison results
            
        Raises:
            ValueError: If fewer than two platforms are available for comparison
        """
        # Determine platforms to compare
        if platforms:
            # Convert PlatformType to string if needed
            platform_ids = [p.value if isinstance(p, PlatformType) else p for p in platforms]
        else:
            # Find all platforms for this version
            version_info = None
            for v in self.metadata["versions"]:
                if v["version"] == version:
                    version_info = v
                    break
            
            if not version_info:
                raise ValueError(f"Version {version} not found")
            
            platform_ids = version_info["platforms"]
        
        if len(platform_ids) < 2:
            raise ValueError("At least two platforms are required for comparison")
        
        # Get configurations
        configs = {}
        for platform in platform_ids:
            config = self.get_config(platform, version)
            if config:
                configs[platform] = config
        
        if len(configs) < 2:
            raise ValueError("At least two valid platform configurations are required for comparison")
        
        # Pairwise comparisons
        comparisons = {}
        for i, platform1 in enumerate(configs.keys()):
            for platform2 in list(configs.keys())[i+1:]:
                comparison_key = f"{platform1}_vs_{platform2}"
                comparisons[comparison_key] = self.compare_configs(platform1, version, platform2, version)
        
        # Find common settings across all platforms
        all_settings = {}
        for platform, config in configs.items():
            all_settings[platform] = config.settings
        
        common_settings = set.intersection(*(set(settings.keys()) for settings in all_settings.values()))
        
        # Check if common settings have the same value
        uniform_settings = {}
        for key in common_settings:
            values = {platform: settings[key] for platform, settings in all_settings.items()}
            if len(set(values.values())) == 1:
                uniform_settings[key] = next(iter(values.values()))
        
        # Find common build flags across all platforms
        all_flags = {}
        for platform, config in configs.items():
            all_flags[platform] = config.build_flags
        
        common_flags = set.intersection(*(set(flags.keys()) for flags in all_flags.values()))
        
        # Check if common flags have the same value
        uniform_flags = {}
        for key in common_flags:
            values = {platform: flags[key] for platform, flags in all_flags.items()}
            if len(set(values.values())) == 1:
                uniform_flags[key] = next(iter(values.values()))
        
        # Find features required/disabled by all platforms
        all_required = {}
        all_disabled = {}
        for platform, config in configs.items():
            all_required[platform] = config.required_features
            all_disabled[platform] = config.disabled_features
        
        common_required = set.intersection(*(features for features in all_required.values()))
        common_disabled = set.intersection(*(features for features in all_disabled.values()))
        
        return {
            "version": version,
            "platforms": list(configs.keys()),
            "platform_count": len(configs),
            "pairwise_comparisons": comparisons,
            "common_settings_count": len(common_settings),
            "uniform_settings_count": len(uniform_settings),
            "uniform_settings": uniform_settings,
            "common_flags_count": len(common_flags),
            "uniform_flags_count": len(uniform_flags),
            "uniform_flags": uniform_flags,
            "common_required_features": list(common_required),
            "common_disabled_features": list(common_disabled)
        }
    
    def get_version_history(
        self,
        platform: Union[str, PlatformType]
    ) -> List[Dict[str, Any]]:
        """
        Get the configuration history for a platform.
        
        Args:
            platform: Platform identifier
            
        Returns:
            List[Dict[str, Any]]: List of configuration versions
        """
        if isinstance(platform, PlatformType):
            platform = platform.value
        
        versions = []
        
        for version_info in self.metadata["versions"]:
            if platform in version_info["platforms"]:
                version_data = deepcopy(version_info)
                config = self.get_config(platform, version_info["version"])
                
                if config:
                    version_data["setting_count"] = len(config.settings)
                    version_data["flag_count"] = len(config.build_flags)
                    version_data["required_feature_count"] = len(config.required_features)
                    version_data["disabled_feature_count"] = len(config.disabled_features)
                
                versions.append(version_data)
        
        # Sort by timestamp (newest first)
        versions.sort(key=lambda v: v["timestamp"], reverse=True)
        
        return versions
    
    def compare_versions(
        self,
        platform: Union[str, PlatformType],
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare configurations across different versions for the same platform.
        
        Args:
            platform: Platform identifier
            version1: First configuration version
            version2: Second configuration version
            
        Returns:
            Dict[str, Any]: Comparison results
            
        Raises:
            ValueError: If either configuration doesn't exist
        """
        # Same function as compare_configs but emphasizing version differences
        return self.compare_configs(platform, version1, platform, version2)
    
    def delete_config(
        self,
        platform: Union[str, PlatformType],
        version: str
    ) -> bool:
        """
        Delete a platform configuration.
        
        Args:
            platform: Platform identifier
            version: Configuration version
            
        Returns:
            bool: True if the configuration was deleted, False if it doesn't exist
        """
        if isinstance(platform, PlatformType):
            platform = platform.value
        
        config_path = self._get_config_path(platform, version)
        
        if not config_path.exists():
            return False
        
        # Remove from metadata
        for i, v in enumerate(self.metadata["versions"]):
            if v["version"] == version:
                if platform in v["platforms"]:
                    v["platforms"].remove(platform)
                
                # Remove version entirely if no platforms left
                if not v["platforms"]:
                    self.metadata["versions"].pop(i)
                break
        
        # Remove platform entirely if no versions left
        platform_in_use = False
        for v in self.metadata["versions"]:
            if platform in v["platforms"]:
                platform_in_use = True
                break
        
        if not platform_in_use and platform in self.metadata["platforms"]:
            self.metadata["platforms"].remove(platform)
        
        self._save_metadata()
        
        # Delete configuration file
        os.remove(config_path)
        
        return True
    
    def create_config_template(
        self,
        platform: Union[str, PlatformType]
    ) -> PlatformConfig:
        """
        Create a template configuration for a platform.
        
        Args:
            platform: Platform identifier
            
        Returns:
            PlatformConfig: Template configuration
        """
        if isinstance(platform, str):
            try:
                platform = PlatformType(platform)
            except ValueError:
                platform = PlatformType.OTHER
        
        # Create different templates based on platform
        if platform == PlatformType.PC:
            return PlatformConfig(
                platform=platform,
                settings={
                    "graphics_quality": "high",
                    "vsync": True,
                    "fullscreen": True,
                    "resolution_width": 1920,
                    "resolution_height": 1080,
                    "texture_quality": "high",
                    "shadow_quality": "high",
                    "anti_aliasing": "msaa_4x",
                    "post_processing": "high"
                },
                build_flags={
                    "ENABLE_STEAM": "1",
                    "TARGET_WINDOWS": "1",
                    "USE_DX11": "1"
                },
                resolution={
                    "width": 1920,
                    "height": 1080,
                    "aspect_ratio": 1.78
                },
                performance_targets={
                    "target_fps": 60.0,
                    "min_fps": 30.0,
                    "target_loading_time": 5.0
                },
                required_features={"keyboard_mouse_support", "steam_integration", "dx11_support"},
                disabled_features={"touch_controls", "motion_controls"}
            )
        
        elif platform == PlatformType.MOBILE:
            return PlatformConfig(
                platform=platform,
                settings={
                    "graphics_quality": "medium",
                    "vsync": True,
                    "fullscreen": True,
                    "resolution_scale": 1.0,
                    "texture_quality": "medium",
                    "shadow_quality": "low",
                    "anti_aliasing": "fxaa",
                    "post_processing": "medium",
                    "battery_saver": False
                },
                build_flags={
                    "ENABLE_TOUCH": "1",
                    "TARGET_MOBILE": "1",
                    "USE_GLES3": "1",
                    "OPTIMIZE_MEMORY": "1"
                },
                resolution={
                    "width": 1080,
                    "height": 1920,
                    "aspect_ratio": 0.5625
                },
                performance_targets={
                    "target_fps": 30.0,
                    "min_fps": 24.0,
                    "target_loading_time": 3.0,
                    "max_memory_usage": 1024.0
                },
                required_features={"touch_controls", "mobile_optimizations", "landscape_portrait_support"},
                disabled_features={"steam_integration", "dx11_support", "high_end_shadows"}
            )
        
        elif platform == PlatformType.CONSOLE:
            return PlatformConfig(
                platform=platform,
                settings={
                    "graphics_quality": "high",
                    "vsync": True,
                    "fullscreen": True,
                    "texture_quality": "high",
                    "shadow_quality": "high",
                    "anti_aliasing": "taa",
                    "post_processing": "high",
                    "hdr_enabled": True
                },
                build_flags={
                    "TARGET_CONSOLE": "1",
                    "ENABLE_GAMEPAD": "1",
                    "OPTIMIZE_FOR_CONSOLE": "1"
                },
                resolution={
                    "width": 3840,
                    "height": 2160,
                    "aspect_ratio": 1.78
                },
                performance_targets={
                    "target_fps": 60.0,
                    "min_fps": 30.0,
                    "target_loading_time": 8.0
                },
                required_features={"gamepad_support", "console_certification", "tv_mode"},
                disabled_features={"keyboard_mouse_support", "touch_controls", "windowed_mode"}
            )
        
        else:
            # Generic template
            return PlatformConfig(
                platform=platform,
                settings={
                    "graphics_quality": "medium",
                    "vsync": True,
                    "fullscreen": True,
                    "texture_quality": "medium",
                    "shadow_quality": "medium",
                    "anti_aliasing": "fxaa",
                    "post_processing": "medium"
                },
                build_flags={},
                resolution={
                    "width": 1280,
                    "height": 720,
                    "aspect_ratio": 1.78
                },
                performance_targets={
                    "target_fps": 30.0,
                    "min_fps": 24.0
                },
                required_features=set(),
                disabled_features=set()
            )
    
    def copy_config(
        self,
        source_platform: Union[str, PlatformType],
        source_version: str,
        target_platform: Union[str, PlatformType],
        target_version: str,
        override_settings: Optional[Dict[str, Any]] = None
    ) -> Optional[PlatformConfig]:
        """
        Copy a configuration from one platform/version to another.
        
        Args:
            source_platform: Source platform identifier
            source_version: Source configuration version
            target_platform: Target platform identifier
            target_version: Target configuration version
            override_settings: Settings to override in the copied configuration
            
        Returns:
            Optional[PlatformConfig]: The copied configuration, or None if source doesn't exist
            
        Raises:
            ValueError: If source configuration doesn't exist
        """
        # Get source configuration
        source_config = self.get_config(source_platform, source_version)
        
        if source_config is None:
            raise ValueError(f"Configuration for {source_platform} version {source_version} not found")
        
        # Clone configuration
        config_dict = source_config.model_dump()
        
        # Update platform
        if isinstance(target_platform, PlatformType):
            config_dict["platform"] = target_platform
        else:
            try:
                config_dict["platform"] = PlatformType(target_platform)
            except ValueError:
                config_dict["platform"] = target_platform
        
        # Apply overrides
        if override_settings:
            for key, value in override_settings.items():
                # Add or update the setting in the configuration
                config_dict["settings"][key] = value
        
        # Create new configuration
        config = PlatformConfig.model_validate(config_dict)
        
        # Save it
        self.save_config(config, target_version)
        
        return config