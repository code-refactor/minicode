"""
Application Environment Capture for creative applications.

This module provides functionality for capturing and restoring application states,
workspace layouts, and tool configurations from major creative software.
"""

import json
import os
import platform
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, cast

import psutil
from pydantic import BaseModel

from creative_vault.interfaces import WorkspaceCapture
from creative_vault.utils import create_unique_id, load_json, save_json


class ApplicationConfig(BaseModel):
    """Configuration for a creative application."""
    
    name: str
    display_name: str
    config_paths: Dict[str, List[str]]
    workspace_paths: Dict[str, List[str]]
    tool_preset_paths: Dict[str, List[str]]
    is_supported: bool = True


class WorkspaceState(BaseModel):
    """Serializable representation of a workspace state."""
    
    id: str
    application_name: str
    capture_time: float
    platform: str
    os_version: str
    config_files: List[str]
    workspace_files: List[str]
    tool_preset_files: List[str]
    metadata: Dict[str, Any] = {}


class CreativeEnvironmentCapture(WorkspaceCapture):
    """Implementation of the application environment capture."""
    
    def __init__(self, workspace_path: Optional[Path] = None):
        """Initialize the environment capture.
        
        Args:
            workspace_path: Optional path for storing workspace states
        """
        self.workspace_path = workspace_path or Path("workspace_states")
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize application configs
        self.applications = self._initialize_application_configs()
    
    def capture_workspace(
        self, 
        application_name: str, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Capture the current workspace state of an application.
        
        Args:
            application_name: Name of the application
            output_path: Optional path to save the workspace state
            
        Returns:
            Path to the saved workspace state
            
        Raises:
            ValueError: If the application is not supported
        """
        # Check if the application is supported
        if application_name not in self.applications:
            raise ValueError(f"Application {application_name} not supported")
        
        app_config = self.applications[application_name]
        if not app_config.is_supported:
            raise ValueError(f"Application {application_name} is supported but not configured for your platform")
        
        # Create a unique ID for this workspace state
        workspace_id = create_unique_id(f"{application_name}-")
        
        # Determine the output path
        if output_path is None:
            output_path = self.workspace_path / f"{workspace_id}.zip"
        
        # Get system information
        os_info = self._get_os_info()
        
        # Create a temp directory to collect files
        temp_dir = self.workspace_path / f"temp_{workspace_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Dictionary to store file paths
            collected_files = {
                "config_files": [],
                "workspace_files": [],
                "tool_preset_files": []
            }
            
            # Get platform-specific paths
            platform_name = os_info["platform"].lower()
            
            # Collect configuration files
            self._collect_files(
                app_config.config_paths.get(platform_name, []),
                temp_dir / "config",
                collected_files["config_files"]
            )
            
            # Collect workspace files
            self._collect_files(
                app_config.workspace_paths.get(platform_name, []),
                temp_dir / "workspace",
                collected_files["workspace_files"]
            )
            
            # Collect tool preset files
            self._collect_files(
                app_config.tool_preset_paths.get(platform_name, []),
                temp_dir / "presets",
                collected_files["tool_preset_files"]
            )
            
            # Create workspace state metadata
            workspace_state = WorkspaceState(
                id=workspace_id,
                application_name=application_name,
                capture_time=time.time(),
                platform=os_info["platform"],
                os_version=os_info["version"],
                config_files=collected_files["config_files"],
                workspace_files=collected_files["workspace_files"],
                tool_preset_files=collected_files["tool_preset_files"],
                metadata={
                    "display_name": app_config.display_name,
                    "capture_date": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            
            # Save metadata
            metadata_path = temp_dir / "metadata.json"
            save_json(workspace_state.model_dump(), metadata_path)
            
            # Create a zip archive
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add metadata
                zipf.write(metadata_path, "metadata.json")
                
                # Add all collected files
                for section in ["config", "workspace", "presets"]:
                    section_dir = temp_dir / section
                    if section_dir.exists():
                        for path in section_dir.glob("**/*"):
                            if path.is_file():
                                rel_path = path.relative_to(temp_dir)
                                zipf.write(path, str(rel_path))
            
            return output_path
        
        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def restore_workspace(
        self, 
        workspace_path: Path, 
        application_name: Optional[str] = None
    ) -> bool:
        """Restore a workspace state to an application.
        
        Args:
            workspace_path: Path to the workspace state file
            application_name: Optional name of the application
            
        Returns:
            bool: True if restore was successful
            
        Raises:
            ValueError: If the workspace file is invalid or application is not supported
            FileNotFoundError: If the workspace file does not exist
        """
        if not workspace_path.exists():
            raise FileNotFoundError(f"Workspace file not found: {workspace_path}")
        
        # Create a temp directory to extract files
        workspace_id = workspace_path.stem
        temp_dir = self.workspace_path / f"restore_{workspace_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Extract the workspace file
            with zipfile.ZipFile(workspace_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Load metadata
            metadata_path = temp_dir / "metadata.json"
            if not metadata_path.exists():
                raise ValueError(f"Invalid workspace file: missing metadata.json")
            
            try:
                metadata = load_json(metadata_path)
                workspace_state = WorkspaceState(**metadata)
            except Exception as e:
                raise ValueError(f"Invalid workspace metadata: {e}")
            
            # Check the application name
            if application_name is None:
                application_name = workspace_state.application_name
            elif application_name != workspace_state.application_name:
                print(f"Warning: Requested application ({application_name}) differs from workspace application ({workspace_state.application_name})")
            
            # Check if the application is supported
            if application_name not in self.applications:
                raise ValueError(f"Application {application_name} not supported")
            
            app_config = self.applications[application_name]
            if not app_config.is_supported:
                raise ValueError(f"Application {application_name} is supported but not configured for your platform")
            
            # Restore files
            success = True
            
            # Get platform-specific paths
            platform_name = platform.system().lower()
            
            # Restore configuration files
            success = success and self._restore_files(
                temp_dir / "config",
                app_config.config_paths.get(platform_name, [])
            )
            
            # Restore workspace files
            success = success and self._restore_files(
                temp_dir / "workspace",
                app_config.workspace_paths.get(platform_name, [])
            )
            
            # Restore tool preset files
            success = success and self._restore_files(
                temp_dir / "presets",
                app_config.tool_preset_paths.get(platform_name, [])
            )
            
            return success
        
        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def get_supported_applications(self) -> List[str]:
        """Get a list of applications supported by the workspace capture system.
        
        Returns:
            List of supported application names
        """
        return [name for name, config in self.applications.items() if config.is_supported]
    
    def get_application_info(self, application_name: str) -> Dict[str, Any]:
        """Get information about a supported application.
        
        Args:
            application_name: Name of the application
            
        Returns:
            Dictionary with information about the application
            
        Raises:
            ValueError: If the application is not supported
        """
        if application_name not in self.applications:
            raise ValueError(f"Application {application_name} not supported")
        
        app_config = self.applications[application_name]
        
        return {
            "name": app_config.name,
            "display_name": app_config.display_name,
            "is_supported": app_config.is_supported,
            "platform": platform.system()
        }
    
    def list_workspace_states(self, application_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all saved workspace states.
        
        Args:
            application_name: Optional application name to filter by
            
        Returns:
            List of dictionaries with information about workspace states
        """
        result = []
        
        for path in self.workspace_path.glob("*.zip"):
            try:
                # Extract metadata from the zip file
                with zipfile.ZipFile(path, 'r') as zipf:
                    if "metadata.json" in zipf.namelist():
                        with zipf.open("metadata.json") as f:
                            metadata = json.load(f)
                        
                        # Filter by application if specified
                        if application_name is None or metadata.get("application_name") == application_name:
                            metadata["file_path"] = str(path)
                            result.append(metadata)
            except Exception as e:
                print(f"Failed to read workspace state {path}: {e}")
        
        # Sort by capture time, newest first
        result.sort(key=lambda x: x.get("capture_time", 0), reverse=True)
        
        return result
    
    def _initialize_application_configs(self) -> Dict[str, ApplicationConfig]:
        """Initialize configuration for supported applications.
        
        Returns:
            Dictionary mapping application names to their configurations
        """
        # Dictionary to store application configs
        configs = {}
        
        # Define paths for each application on different platforms
        
        # Adobe Photoshop
        configs["photoshop"] = ApplicationConfig(
            name="photoshop",
            display_name="Adobe Photoshop",
            config_paths={
                "windows": [
                    "%APPDATA%\\Adobe\\Adobe Photoshop *\\Preferences",
                    "%USERPROFILE%\\AppData\\Roaming\\Adobe\\Adobe Photoshop *\\Presets"
                ],
                "darwin": [
                    "~/Library/Preferences/Adobe/Adobe Photoshop *",
                    "~/Library/Application Support/Adobe/Adobe Photoshop *"
                ],
                "linux": []  # Not available on Linux
            },
            workspace_paths={
                "windows": [
                    "%APPDATA%\\Adobe\\Adobe Photoshop *\\Workspaces"
                ],
                "darwin": [
                    "~/Library/Preferences/Adobe/Adobe Photoshop */Workspaces"
                ],
                "linux": []
            },
            tool_preset_paths={
                "windows": [
                    "%APPDATA%\\Adobe\\Adobe Photoshop *\\Presets\\Tools"
                ],
                "darwin": [
                    "~/Library/Application Support/Adobe/Adobe Photoshop */Presets/Tools"
                ],
                "linux": []
            }
        )
        
        # Adobe Illustrator
        configs["illustrator"] = ApplicationConfig(
            name="illustrator",
            display_name="Adobe Illustrator",
            config_paths={
                "windows": [
                    "%APPDATA%\\Adobe\\Adobe Illustrator *\\Preferences",
                    "%USERPROFILE%\\AppData\\Roaming\\Adobe\\Adobe Illustrator *"
                ],
                "darwin": [
                    "~/Library/Preferences/Adobe Illustrator *",
                    "~/Library/Application Support/Adobe/Adobe Illustrator *"
                ],
                "linux": []  # Not available on Linux
            },
            workspace_paths={
                "windows": [
                    "%APPDATA%\\Adobe\\Adobe Illustrator *\\Workspaces"
                ],
                "darwin": [
                    "~/Library/Preferences/Adobe Illustrator */Workspaces"
                ],
                "linux": []
            },
            tool_preset_paths={
                "windows": [
                    "%APPDATA%\\Adobe\\Adobe Illustrator *\\Presets"
                ],
                "darwin": [
                    "~/Library/Application Support/Adobe/Adobe Illustrator */Presets"
                ],
                "linux": []
            }
        )
        
        # Blender
        configs["blender"] = ApplicationConfig(
            name="blender",
            display_name="Blender",
            config_paths={
                "windows": [
                    "%APPDATA%\\Blender Foundation\\Blender\\*\\config"
                ],
                "darwin": [
                    "~/Library/Application Support/Blender/*/config"
                ],
                "linux": [
                    "~/.config/blender/*/config"
                ]
            },
            workspace_paths={
                "windows": [
                    "%APPDATA%\\Blender Foundation\\Blender\\*\\config\\workspaces"
                ],
                "darwin": [
                    "~/Library/Application Support/Blender/*/config/workspaces"
                ],
                "linux": [
                    "~/.config/blender/*/config/workspaces"
                ]
            },
            tool_preset_paths={
                "windows": [
                    "%APPDATA%\\Blender Foundation\\Blender\\*\\config\\presets"
                ],
                "darwin": [
                    "~/Library/Application Support/Blender/*/config/presets"
                ],
                "linux": [
                    "~/.config/blender/*/config/presets"
                ]
            }
        )
        
        # Maya
        configs["maya"] = ApplicationConfig(
            name="maya",
            display_name="Autodesk Maya",
            config_paths={
                "windows": [
                    "%USERPROFILE%\\Documents\\maya\\*\\prefs"
                ],
                "darwin": [
                    "~/Library/Preferences/Autodesk/maya/*"
                ],
                "linux": [
                    "~/maya/*/prefs"
                ]
            },
            workspace_paths={
                "windows": [
                    "%USERPROFILE%\\Documents\\maya\\*\\workspaces"
                ],
                "darwin": [
                    "~/Library/Preferences/Autodesk/maya/*/workspaces"
                ],
                "linux": [
                    "~/maya/*/workspaces"
                ]
            },
            tool_preset_paths={
                "windows": [
                    "%USERPROFILE%\\Documents\\maya\\*\\presets"
                ],
                "darwin": [
                    "~/Library/Preferences/Autodesk/maya/*/presets"
                ],
                "linux": [
                    "~/maya/*/presets"
                ]
            }
        )
        
        # Check which applications are supported on the current platform
        current_platform = platform.system().lower()
        
        for app_name, config in configs.items():
            if current_platform not in config.config_paths or not config.config_paths[current_platform]:
                config.is_supported = False
        
        return configs
    
    def _get_os_info(self) -> Dict[str, str]:
        """Get information about the operating system.
        
        Returns:
            Dictionary with platform and version information
        """
        return {
            "platform": platform.system(),
            "version": platform.version()
        }
    
    def _collect_files(
        self, 
        path_patterns: List[str], 
        target_dir: Path, 
        collected_paths: List[str]
    ) -> None:
        """Collect files matching the specified patterns.
        
        Args:
            path_patterns: List of path patterns to collect
            target_dir: Directory to store collected files
            collected_paths: List to add collected file paths to
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Expand environment variables in paths
        expanded_patterns = []
        for pattern in path_patterns:
            # Handle both Windows and Unix-style paths
            if platform.system() == "Windows":
                # For Windows, expand environment variables with %VAR%
                parts = pattern.split("%")
                expanded = ""
                for i, part in enumerate(parts):
                    if i % 2 == 1:  # Odd index means it's inside %VAR%
                        expanded += os.environ.get(part, f"%{part}%")
                    else:
                        expanded += part
                expanded_patterns.append(expanded)
            else:
                # For Unix-like systems, expand ~ and $VAR
                expanded = os.path.expanduser(pattern)
                expanded = os.path.expandvars(expanded)
                expanded_patterns.append(expanded)
        
        # Collect files for each pattern
        for pattern in expanded_patterns:
            # Support for globs in the pattern
            for path in Path().glob(pattern):
                if path.exists():
                    if path.is_file():
                        # Copy the file to the target directory
                        rel_path = path.name
                        target_path = target_dir / rel_path
                        
                        try:
                            shutil.copy2(path, target_path)
                            collected_paths.append(str(path))
                        except Exception as e:
                            print(f"Failed to copy {path}: {e}")
                    
                    elif path.is_dir():
                        # Recursively copy the directory contents
                        for file_path in path.glob("**/*"):
                            if file_path.is_file():
                                rel_path = file_path.relative_to(path.parent)
                                target_path = target_dir / rel_path
                                target_path.parent.mkdir(parents=True, exist_ok=True)
                                
                                try:
                                    shutil.copy2(file_path, target_path)
                                    collected_paths.append(str(file_path))
                                except Exception as e:
                                    print(f"Failed to copy {file_path}: {e}")
    
    def _restore_files(self, source_dir: Path, target_patterns: List[str]) -> bool:
        """Restore files to their original locations.
        
        Args:
            source_dir: Directory containing the files to restore
            target_patterns: List of target path patterns
            
        Returns:
            bool: True if all files were restored successfully
        """
        if not source_dir.exists() or not source_dir.is_dir():
            return True  # Nothing to restore
        
        success = True
        
        # Expand environment variables in target patterns
        expanded_targets = []
        for pattern in target_patterns:
            # Handle both Windows and Unix-style paths
            if platform.system() == "Windows":
                # For Windows, expand environment variables with %VAR%
                parts = pattern.split("%")
                expanded = ""
                for i, part in enumerate(parts):
                    if i % 2 == 1:  # Odd index means it's inside %VAR%
                        expanded += os.environ.get(part, f"%{part}%")
                    else:
                        expanded += part
                expanded_targets.append(expanded)
            else:
                # For Unix-like systems, expand ~ and $VAR
                expanded = os.path.expanduser(pattern)
                expanded = os.path.expandvars(expanded)
                expanded_targets.append(expanded)
        
        # Find the most specific target pattern that exists
        target_base = None
        for pattern in expanded_targets:
            # Remove glob patterns
            base_path = pattern.split("*")[0].rstrip("/\\")
            test_path = Path(base_path)
            
            if test_path.exists() and test_path.is_dir():
                target_base = test_path
                break
        
        if target_base is None:
            # If no target directory exists, try to create one using the first pattern
            if expanded_targets:
                base_path = expanded_targets[0].split("*")[0].rstrip("/\\")
                target_base = Path(base_path)
                target_base.mkdir(parents=True, exist_ok=True)
            else:
                return False  # No valid target
        
        # Copy all files from source to target
        for source_path in source_dir.glob("**/*"):
            if source_path.is_file():
                rel_path = source_path.relative_to(source_dir)
                target_path = target_base / rel_path
                
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                except Exception as e:
                    print(f"Failed to restore {source_path} to {target_path}: {e}")
                    success = False
        
        return success