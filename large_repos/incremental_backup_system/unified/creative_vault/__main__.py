"""
Main entry point for the CreativeVault backup system.

This module ties together all the components of the CreativeVault system
and provides a central interface for interacting with the system.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from creative_vault.backup_engine.incremental_backup import DeltaBackupEngine
from creative_vault.visual_diff.diff_generator import CreativeVisualDiffGenerator
from creative_vault.timeline.timeline_manager import CreativeTimelineManager
from creative_vault.element_extraction.extractor import CreativeElementExtractor
from creative_vault.asset_tracker.reference_tracker import CreativeAssetReferenceTracker
from creative_vault.workspace_capture.environment_capture import CreativeEnvironmentCapture
from creative_vault.utils import BackupConfig


class CreativeVault:
    """Main interface for the CreativeVault backup system."""
    
    def __init__(self, repository_path: Optional[Path] = None):
        """Initialize the CreativeVault system.
        
        Args:
            repository_path: Path to the repository for storing backups and metadata
        """
        self.repository_path = repository_path or Path("creative_vault_repo")
        self.repository_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize configuration
        self.config = BackupConfig(repository_path=self.repository_path)
        
        # Initialize components
        self.backup_engine = DeltaBackupEngine(self.config)
        
        # Ensure repository is initialized
        self.backup_engine.initialize_repository(self.repository_path)
        
        self.diff_generator = CreativeVisualDiffGenerator(
            output_directory=self.repository_path / "diffs"
        )
        
        self.timeline_manager = CreativeTimelineManager(
            repository_path=self.repository_path,
            diff_generator=self.diff_generator
        )
        
        self.element_extractor = CreativeElementExtractor(
            output_directory=self.repository_path / "extracted_elements"
        )
        
        self.asset_tracker = CreativeAssetReferenceTracker(
            repository_path=self.repository_path
        )
        
        self.workspace_capture = CreativeEnvironmentCapture(
            workspace_path=self.repository_path / "workspaces"
        )
    
    def backup_project(self, project_path: Path, capture_workspace: bool = False) -> Dict[str, Any]:
        """Backup a project directory.
        
        Args:
            project_path: Path to the project directory
            capture_workspace: Whether to capture the application workspace state
            
        Returns:
            Dictionary with backup results
        """
        # Create a snapshot
        snapshot_id = self.backup_engine.create_snapshot(project_path)
        
        # Get snapshot info
        snapshot_info = self.backup_engine.get_snapshot_info(snapshot_id)
        
        results = {
            "snapshot_id": snapshot_id,
            "timestamp": snapshot_info["timestamp"],
            "files_count": snapshot_info["files_count"],
            "total_size": snapshot_info["total_size"],
            "new_files": len(snapshot_info["new_files"]),
            "modified_files": len(snapshot_info["modified_files"]),
            "deleted_files": len(snapshot_info["deleted_files"])
        }
        
        # Track project references
        if project_path.exists():
            try:
                reference_results = self.asset_tracker.scan_project(project_path)
                results["reference_tracking"] = {
                    "asset_count": len(reference_results["file_categories"]["asset_files"]),
                    "reference_count": sum(len(refs) for refs in reference_results["references"]["projects_to_assets"].values())
                }
            except Exception as e:
                results["reference_tracking"] = {"error": str(e)}
        
        # Capture workspace state if requested
        if capture_workspace:
            workspace_results = []
            
            # Try to capture workspace for supported applications
            for app_name in self.workspace_capture.get_supported_applications():
                try:
                    workspace_path = self.workspace_capture.capture_workspace(app_name)
                    workspace_results.append({
                        "application": app_name,
                        "workspace_path": str(workspace_path),
                        "success": True
                    })
                except Exception as e:
                    workspace_results.append({
                        "application": app_name,
                        "error": str(e),
                        "success": False
                    })
            
            results["workspace_capture"] = workspace_results
        
        return results
    
    def restore_project(
        self, 
        snapshot_id: str, 
        target_path: Path, 
        restore_workspace: bool = False
    ) -> Dict[str, Any]:
        """Restore a project from a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to restore
            target_path: Path where the project will be restored
            restore_workspace: Whether to restore application workspace states
            
        Returns:
            Dictionary with restore results
        """
        # Restore the snapshot
        success = self.backup_engine.restore_snapshot(snapshot_id, target_path)
        
        results = {
            "snapshot_id": snapshot_id,
            "target_path": str(target_path),
            "success": success
        }
        
        # Restore workspace state if requested
        if restore_workspace and success:
            workspace_results = []
            
            # Get workspaces captured around the same time as the snapshot
            workspaces = self.workspace_capture.list_workspace_states()
            
            if workspaces:
                # Just restore the most recent workspace for each application
                restored_apps = set()
                
                for workspace in workspaces:
                    app_name = workspace.get("application_name")
                    if app_name and app_name not in restored_apps:
                        try:
                            workspace_path = Path(workspace["file_path"])
                            restore_success = self.workspace_capture.restore_workspace(workspace_path)
                            
                            workspace_results.append({
                                "application": app_name,
                                "workspace_id": workspace.get("id"),
                                "success": restore_success
                            })
                            
                            restored_apps.add(app_name)
                        except Exception as e:
                            workspace_results.append({
                                "application": app_name,
                                "error": str(e),
                                "success": False
                            })
            
            results["workspace_restore"] = workspace_results
        
        return results
    
    def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """Compare two versions of a file.
        
        Args:
            version_id_1: ID of the first version
            version_id_2: ID of the second version
            
        Returns:
            Dictionary with comparison results
        """
        return self.timeline_manager.compare_versions(version_id_1, version_id_2)
    
    def extract_element(
        self, 
        file_path: Path, 
        element_id: str, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Extract a specific element from a file.
        
        Args:
            file_path: Path to the file
            element_id: ID of the element to extract
            output_path: Optional path to save the extracted element
            
        Returns:
            Path to the extracted element
        """
        return self.element_extractor.extract_element(file_path, element_id, output_path)
    
    def deduplicate_assets(self, project_path: Path) -> Dict[str, Any]:
        """Deduplicate assets in a project.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with deduplication results
        """
        return self.asset_tracker.deduplicate_assets(project_path)
    
    def get_project_timeline(self, project_path: Path) -> Dict[str, Any]:
        """Get the timeline of versions for all files in a project.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with timeline information
        """
        results = {
            "project_path": str(project_path),
            "files": {}
        }
        
        # Scan the project files
        for file_path in project_path.glob("**/*"):
            if file_path.is_file():
                try:
                    file_timeline = self.timeline_manager.get_file_timeline(file_path)
                    if file_timeline:
                        rel_path = str(file_path.relative_to(project_path))
                        results["files"][rel_path] = file_timeline
                except Exception:
                    pass
        
        return results
    
    def get_snapshots(self) -> List[Dict[str, Any]]:
        """Get a list of all snapshots.
        
        Returns:
            List of dictionaries containing snapshot information
        """
        return self.backup_engine.list_snapshots()


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="CreativeVault Backup System")
    parser.add_argument("--repository", type=str, help="Path to the repository directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup a project")
    backup_parser.add_argument("project_path", type=str, help="Path to the project directory")
    backup_parser.add_argument("--capture-workspace", action="store_true", help="Capture application workspace state")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a project")
    restore_parser.add_argument("snapshot_id", type=str, help="ID of the snapshot to restore")
    restore_parser.add_argument("target_path", type=str, help="Path where the project will be restored")
    restore_parser.add_argument("--restore-workspace", action="store_true", help="Restore application workspace state")
    
    # List snapshots command
    _ = subparsers.add_parser("list-snapshots", help="List all snapshots")
    
    # Compare versions command
    compare_parser = subparsers.add_parser("compare", help="Compare two versions of a file")
    compare_parser.add_argument("version_id_1", type=str, help="ID of the first version")
    compare_parser.add_argument("version_id_2", type=str, help="ID of the second version")
    
    # Extract element command
    extract_parser = subparsers.add_parser("extract", help="Extract a specific element from a file")
    extract_parser.add_argument("file_path", type=str, help="Path to the file")
    extract_parser.add_argument("element_id", type=str, help="ID of the element to extract")
    extract_parser.add_argument("--output", type=str, help="Path to save the extracted element")
    
    # Deduplicate assets command
    deduplicate_parser = subparsers.add_parser("deduplicate", help="Deduplicate assets in a project")
    deduplicate_parser.add_argument("project_path", type=str, help="Path to the project directory")
    
    args = parser.parse_args()
    
    # Create the CreativeVault instance
    vault = CreativeVault(
        repository_path=Path(args.repository) if args.repository else None
    )
    
    # Execute the requested command
    if args.command == "backup":
        result = vault.backup_project(
            project_path=Path(args.project_path),
            capture_workspace=args.capture_workspace
        )
        print(json.dumps(result, indent=2))
    
    elif args.command == "restore":
        result = vault.restore_project(
            snapshot_id=args.snapshot_id,
            target_path=Path(args.target_path),
            restore_workspace=args.restore_workspace
        )
        print(json.dumps(result, indent=2))
    
    elif args.command == "list-snapshots":
        snapshots = vault.get_snapshots()
        print(json.dumps(snapshots, indent=2))
    
    elif args.command == "compare":
        result = vault.compare_versions(args.version_id_1, args.version_id_2)
        print(json.dumps(result, indent=2))
    
    elif args.command == "extract":
        output_path = vault.extract_element(
            file_path=Path(args.file_path),
            element_id=args.element_id,
            output_path=Path(args.output) if args.output else None
        )
        print(f"Element extracted to: {output_path}")
    
    elif args.command == "deduplicate":
        result = vault.deduplicate_assets(Path(args.project_path))
        print(json.dumps(result, indent=2))
    
    else:
        parser.print_help()