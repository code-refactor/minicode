"""
Tests for the application environment capture component.
"""

import os
import platform
from pathlib import Path
import zipfile

import pytest

from creative_vault.workspace_capture.environment_capture import CreativeEnvironmentCapture


def test_get_supported_applications(workspace_capture):
    """Test getting a list of supported applications."""
    # Get supported applications
    applications = workspace_capture.get_supported_applications()
    
    # Check the result
    assert applications is not None
    assert isinstance(applications, list)
    
    # At least some applications should be supported
    # The exact list depends on the platform
    current_platform = platform.system().lower()
    if current_platform in ["windows", "darwin"]:
        assert len(applications) > 0
    

def test_get_application_info(workspace_capture):
    """Test getting information about a supported application."""
    # Get supported applications
    applications = workspace_capture.get_supported_applications()
    
    # Skip the test if no applications are supported
    if not applications:
        pytest.skip("No supported applications on this platform")
    
    # Get info about the first supported application
    app_name = applications[0]
    app_info = workspace_capture.get_application_info(app_name)
    
    # Check the result
    assert app_info is not None
    assert "name" in app_info
    assert "display_name" in app_info
    assert "is_supported" in app_info
    assert "platform" in app_info
    assert app_info["name"] == app_name
    assert app_info["is_supported"] is True


def test_capture_workspace_mock(workspace_capture, temp_dir, monkeypatch):
    """Test capturing a workspace state (mock version since we can't assume any applications are installed)."""
    # Create a mock application name
    app_name = "mock_app"
    
    # Mock the _initialize_application_configs method to include our mock app
    def mock_initialize_configs():
        current_platform = platform.system().lower()
        return {
            app_name: type("ApplicationConfig", (), {
                "name": app_name,
                "display_name": "Mock Application",
                "config_paths": {current_platform: ["mock_config.txt"]},
                "workspace_paths": {current_platform: ["mock_workspace.txt"]},
                "tool_preset_paths": {current_platform: []},
                "is_supported": True
            })
        }
    
    # Mock the _collect_files method to avoid the Path.glob issue
    def mock_collect_files(path_patterns, target_dir, collected_paths):
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a mock config file
        config_file = target_dir / "mock_config.txt"
        with open(config_file, 'w') as f:
            f.write("Mock configuration")
        collected_paths.append(str(config_file))
        
        # Create a mock workspace file
        workspace_file = target_dir / "mock_workspace.txt"
        with open(workspace_file, 'w') as f:
            f.write("Mock workspace")
        collected_paths.append(str(workspace_file))
    
    # Apply the monkey patches
    monkeypatch.setattr(workspace_capture, "_initialize_application_configs", mock_initialize_configs)
    monkeypatch.setattr(workspace_capture, "applications", mock_initialize_configs())
    monkeypatch.setattr(workspace_capture, "_collect_files", mock_collect_files)
    
    # Capture the workspace
    workspace_path = workspace_capture.capture_workspace(app_name)
    
    # Check the result
    assert workspace_path.exists()
    assert workspace_path.suffix == ".zip"
    
    # Check the contents of the zip file
    with zipfile.ZipFile(workspace_path, 'r') as zipf:
        assert "metadata.json" in zipf.namelist()
        assert "config/mock_config.txt" in zipf.namelist()
        assert "workspace/mock_workspace.txt" in zipf.namelist()
        
        # Extract and check the metadata
        metadata = zipf.read("metadata.json").decode('utf-8')
        assert app_name in metadata
        assert "application_name" in metadata
        assert "platform" in metadata


def test_restore_workspace_mock(workspace_capture, temp_dir, monkeypatch):
    """Test restoring a workspace state (mock version)."""
    # Set up the same mocks as in test_capture_workspace_mock
    app_name = "mock_app"
    
    def mock_initialize_configs():
        current_platform = platform.system().lower()
        return {
            app_name: type("ApplicationConfig", (), {
                "name": app_name,
                "display_name": "Mock Application",
                "config_paths": {current_platform: ["mock_config.txt"]},
                "workspace_paths": {current_platform: ["mock_workspace.txt"]},
                "tool_preset_paths": {current_platform: []},
                "is_supported": True
            })
        }
    
    def mock_collect_files(path_patterns, target_dir, collected_paths):
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a mock config file
        config_file = target_dir / "mock_config.txt"
        with open(config_file, 'w') as f:
            f.write("Mock configuration")
        collected_paths.append(str(config_file))
        
        # Create a mock workspace file
        workspace_file = target_dir / "mock_workspace.txt"
        with open(workspace_file, 'w') as f:
            f.write("Mock workspace")
        collected_paths.append(str(workspace_file))
    
    # Override the _restore_files method
    def mock_restore_files(source_dir, target_patterns):
        # Just return success
        return True
    
    # Apply the monkey patches
    monkeypatch.setattr(workspace_capture, "_initialize_application_configs", mock_initialize_configs)
    monkeypatch.setattr(workspace_capture, "applications", mock_initialize_configs())
    monkeypatch.setattr(workspace_capture, "_collect_files", mock_collect_files)
    monkeypatch.setattr(workspace_capture, "_restore_files", mock_restore_files)
    
    # First create a workspace file
    workspace_path = workspace_capture.capture_workspace(app_name)
    
    # Now restore it
    result = workspace_capture.restore_workspace(workspace_path)
    
    # Check the result
    assert result is True


def test_error_handling_for_nonexistent_workspace(workspace_capture, temp_dir):
    """Test error handling when workspace file doesn't exist."""
    non_existent_workspace = temp_dir / "does_not_exist.zip"
    
    # Attempt to restore a non-existent workspace
    with pytest.raises(FileNotFoundError):
        workspace_capture.restore_workspace(non_existent_workspace)


def test_list_workspace_states(workspace_capture, temp_dir, monkeypatch):
    """Test listing all saved workspace states."""
    # Set up the same mocks as in test_capture_workspace_mock
    app_name = "mock_app"
    
    def mock_initialize_configs():
        current_platform = platform.system().lower()
        return {
            app_name: type("ApplicationConfig", (), {
                "name": app_name,
                "display_name": "Mock Application",
                "config_paths": {current_platform: ["mock_config.txt"]},
                "workspace_paths": {current_platform: ["mock_workspace.txt"]},
                "tool_preset_paths": {current_platform: []},
                "is_supported": True
            })
        }
    
    def mock_collect_files(path_patterns, target_dir, collected_paths):
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a mock config file
        config_file = target_dir / "mock_config.txt"
        with open(config_file, 'w') as f:
            f.write("Mock configuration")
        collected_paths.append(str(config_file))
        
        # Create a mock workspace file
        workspace_file = target_dir / "mock_workspace.txt"
        with open(workspace_file, 'w') as f:
            f.write("Mock workspace")
        collected_paths.append(str(workspace_file))
    
    # Apply the monkey patches
    monkeypatch.setattr(workspace_capture, "_initialize_application_configs", mock_initialize_configs)
    monkeypatch.setattr(workspace_capture, "applications", mock_initialize_configs())
    monkeypatch.setattr(workspace_capture, "_collect_files", mock_collect_files)
    
    # Create a mock workspace file
    workspace_path = workspace_capture.capture_workspace(app_name)
    
    # List workspace states
    workspaces = workspace_capture.list_workspace_states()
    
    # Check the result
    assert workspaces is not None
    assert len(workspaces) >= 1
    
    # Check the first workspace
    first_workspace = workspaces[0]
    assert "application_name" in first_workspace
    assert "capture_time" in first_workspace
    assert "file_path" in first_workspace
    assert first_workspace["application_name"] == app_name