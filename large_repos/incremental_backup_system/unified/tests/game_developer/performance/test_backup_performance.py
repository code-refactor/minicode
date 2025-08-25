"""
Performance tests for the backup engine.

This module contains tests that verify the backup engine meets the
performance requirements specified in the requirements.
"""

import os
import random
import shutil
import tempfile
import time
from pathlib import Path

import pytest

from gamevault.backup_engine.engine import BackupEngine
from gamevault.models import GameVersionType


def create_test_file(path, size_kb, binary=False):
    """Create a test file of the specified size."""
    path = Path(path)
    path.parent.mkdir(exist_ok=True, parents=True)
    
    mode = "wb" if binary else "w"
    with open(path, mode) as f:
        if binary:
            # Create a file with a repeating pattern for good compression
            pattern_size = min(size_kb * 1024, 16 * 1024)  # Max 16KB pattern
            pattern = bytes(random.randint(0, 255) for _ in range(pattern_size))
            
            remaining = size_kb * 1024
            while remaining > 0:
                to_write = min(remaining, pattern_size)
                f.write(pattern[:to_write])
                remaining -= to_write
        else:
            # Create a text file with repeating lines
            line = "This is a test line with some variation " + str(random.random()) + "\n"
            lines_needed = (size_kb * 1024) // len(line) + 1
            
            for _ in range(lines_needed):
                f.write(line)


def create_test_project(project_dir, file_count, avg_size_kb, binary_ratio=0.5):
    """Create a test project with the specified number and size of files."""
    folders = ["src", "assets", "docs", "config", "assets/textures", "assets/models", "assets/audio"]
    
    # Create folder structure
    for folder in folders:
        os.makedirs(project_dir / folder, exist_ok=True)
    
    # Create files
    binary_count = int(file_count * binary_ratio)
    text_count = file_count - binary_count
    
    # Create text files
    for i in range(text_count):
        folder = random.choice(["src", "docs", "config"])
        if folder == "src":
            extension = random.choice([".cpp", ".h", ".py", ".js"])
        elif folder == "docs":
            extension = random.choice([".md", ".txt", ".html"])
        else:
            extension = random.choice([".json", ".xml", ".yaml"])
        
        filename = f"file_{i}{extension}"
        file_size = random.randint(1, avg_size_kb * 2)  # Vary file size
        create_test_file(project_dir / folder / filename, file_size, binary=False)
    
    # Create binary files
    for i in range(binary_count):
        folder = random.choice(["assets/textures", "assets/models", "assets/audio"])
        
        if folder == "assets/textures":
            extension = random.choice([".png", ".jpg", ".tga"])
        elif folder == "assets/models":
            extension = random.choice([".fbx", ".obj", ".blend"])
        else:
            extension = random.choice([".wav", ".mp3", ".ogg"])
        
        filename = f"asset_{i}{extension}"
        file_size = random.randint(avg_size_kb // 2, avg_size_kb * 3)  # Vary file size
        create_test_file(project_dir / folder / filename, file_size, binary=True)


@pytest.fixture
def large_test_project():
    """Create a large test project for performance testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "large_project"
        project_dir.mkdir()
        
        # Create a project with 1000 files (500MB total)
        # This is a scaled-down version for testing purposes
        # In a real benchmark, you'd use much larger values
        create_test_project(project_dir, file_count=1000, avg_size_kb=500)
        
        yield project_dir


@pytest.fixture
def backup_engine(large_test_project):
    """Create a BackupEngine for the large test project."""
    with tempfile.TemporaryDirectory() as temp_dir:
        engine = BackupEngine(
            project_name="perf_test",
            project_path=large_test_project,
            storage_dir=temp_dir
        )
        yield engine


def make_project_changes(project_dir, change_ratio=0.1):
    """Make changes to a percentage of files in the project."""
    # Collect all files in the project
    all_files = list(project_dir.glob("**/*"))
    all_files = [f for f in all_files if f.is_file()]
    
    # Determine number of files to change
    change_count = max(1, int(len(all_files) * change_ratio))
    files_to_change = random.sample(all_files, change_count)
    
    # Make changes
    for file_path in files_to_change:
        is_binary = any(ext in file_path.suffix.lower() for ext in [".png", ".jpg", ".fbx", ".wav", ".mp3"])
        
        if is_binary:
            # For binary files, append a small amount of random data
            with open(file_path, "ab") as f:
                f.write(os.urandom(100))
        else:
            # For text files, append a new line
            with open(file_path, "a") as f:
                f.write(f"\n// Modified at {time.time()}\n")


@pytest.mark.parametrize("file_count,avg_size_kb", [
    (100, 100),  # Small project (~10 MB)
    (500, 200),  # Medium project (~100 MB)
])
def test_initial_backup_performance(file_count, avg_size_kb):
    """Test performance of initial backup for different project sizes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / "test_project"
        project_dir.mkdir()
        
        # Create test project
        create_test_project(project_dir, file_count, avg_size_kb)
        
        # Create backup engine
        engine = BackupEngine(
            project_name="perf_test",
            project_path=project_dir,
            storage_dir=Path(temp_dir) / "storage"
        )
        
        # Measure initial backup time
        start_time = time.time()
        version = engine.create_backup(
            name="Initial Backup",
            version_type=GameVersionType.DEVELOPMENT
        )
        elapsed_time = time.time() - start_time
        
        # Calculate approx project size in GB
        project_size_gb = (file_count * avg_size_kb) / (1024 * 1024)
        
        # Calculate extrapolated time for 200GB
        extrapolated_time_hours = (elapsed_time / project_size_gb) * 200 / 3600
        
        # Requirement: Initial backup of 200GB project must complete in under 2 hours
        # We can't test with an actual 200GB project, so we extrapolate
        print(f"Project size: {project_size_gb:.2f} GB")
        print(f"Backup time: {elapsed_time:.2f} seconds")
        print(f"Extrapolated time for 200GB: {extrapolated_time_hours:.2f} hours")
        
        # Verify requirement is met
        assert extrapolated_time_hours < 2.0, "Initial backup would exceed 2 hour requirement for 200GB project"


def test_incremental_backup_performance(backup_engine, large_test_project):
    """Test performance of incremental backup after making changes."""
    # Create initial backup
    initial_backup_start = time.time()
    initial_version = backup_engine.create_backup(
        name="Initial Backup",
        version_type=GameVersionType.DEVELOPMENT
    )
    initial_backup_time = time.time() - initial_backup_start
    
    # Make changes to ~10% of files
    make_project_changes(large_test_project, change_ratio=0.1)
    
    # Create incremental backup
    incremental_start = time.time()
    incremental_version = backup_engine.create_backup(
        name="Incremental Backup",
        version_type=GameVersionType.DEVELOPMENT
    )
    incremental_time = time.time() - incremental_start
    
    # Requirement: Incremental backup must complete in under 10 minutes
    print(f"Initial backup time: {initial_backup_time:.2f} seconds")
    print(f"Incremental backup time: {incremental_time:.2f} seconds")
    print(f"Ratio: {incremental_time / initial_backup_time:.2f}")
    
    # Convert to minutes
    incremental_minutes = incremental_time / 60
    
    # Verify requirement is met
    assert incremental_minutes < 10.0, "Incremental backup exceeded 10 minute requirement"


def test_asset_optimization_efficiency(backup_engine, large_test_project):
    """Test storage efficiency for binary asset files."""
    # Create initial backup
    version = backup_engine.create_backup(
        name="Optimization Test",
        version_type=GameVersionType.DEVELOPMENT
    )
    
    # Get total size of binary assets in project
    binary_extensions = [".png", ".jpg", ".tga", ".fbx", ".obj", ".blend", ".wav", ".mp3", ".ogg"]
    binary_files = []
    
    for ext in binary_extensions:
        binary_files.extend(large_test_project.glob(f"**/*{ext}"))
    
    original_size = sum(os.path.getsize(f) for f in binary_files)
    
    # Get storage stats
    storage_stats = backup_engine.get_storage_stats()
    
    # Calculate storage efficiency
    if original_size > 0:
        storage_ratio = original_size / storage_stats["total"]
    else:
        storage_ratio = 1.0
    
    # Requirement: Asset optimization must achieve at least 70% storage reduction
    required_ratio = 1.0 / 0.3  # 70% reduction means storage is 30% of original
    
    print(f"Original size: {original_size} bytes")
    print(f"Storage size: {storage_stats['total']} bytes")
    print(f"Storage ratio: {storage_ratio:.2f}x")
    
    # Verify requirement is met
    assert storage_ratio >= required_ratio, f"Storage optimization below requirement: {storage_ratio:.2f}x < {required_ratio:.2f}x"


def test_build_feedback_correlation_performance(backup_engine):
    """Test performance of correlating build feedback."""
    # This is a simplified test to verify that the correlation system
    # can handle the required processing rate
    
    from gamevault.feedback_system.manager import FeedbackManager
    
    # Create a feedback manager with the same storage dir
    feedback_manager = FeedbackManager(
        "perf_test",
        storage_dir=backup_engine.storage_dir
    )
    
    # Create a test version
    version = backup_engine.create_backup(
        name="Feedback Test",
        version_type=GameVersionType.DEVELOPMENT
    )
    
    # Generate test feedback data
    feedback_count = 1000  # Requirement: 1000 records per minute
    feedback_records = []
    
    for i in range(feedback_count):
        feedback = {
            "player_id": f"player_{i % 100}",
            "version_id": version.id,
            "category": random.choice(["bug", "suggestion", "praise"]),
            "content": f"Feedback #{i}: This is a test feedback with some content.",
            "metadata": {"severity": random.choice(["low", "medium", "high"])},
            "tags": [f"tag_{i % 10}", "test"]
        }
        feedback_records.append(feedback)
    
    # Measure time to process all feedback
    start_time = time.time()
    
    for record in feedback_records:
        feedback_manager.add_feedback(
            player_id=record["player_id"],
            version_id=record["version_id"],
            category=record["category"],
            content=record["content"],
            metadata=record["metadata"],
            tags=record["tags"]
        )
    
    elapsed_time = time.time() - start_time
    records_per_minute = (feedback_count / elapsed_time) * 60
    
    # Requirement: Process 1000 records per minute
    print(f"Processed {feedback_count} records in {elapsed_time:.2f} seconds")
    print(f"Processing rate: {records_per_minute:.2f} records per minute")
    
    # Verify requirement is met
    assert records_per_minute >= 1000, f"Processing rate below requirement: {records_per_minute:.2f} < 1000 records/minute"


def test_milestone_snapshot_performance(backup_engine, large_test_project):
    """Test performance of creating milestone snapshots."""
    from gamevault.milestone_management.manager import MilestoneManager
    
    # Create a milestone manager
    milestone_manager = MilestoneManager(
        "perf_test",
        backup_engine=backup_engine,
        storage_dir=backup_engine.storage_dir
    )
    
    # Measure time to create a milestone
    start_time = time.time()
    
    milestone = milestone_manager.create_milestone(
        name="Performance Test Milestone",
        version_type=GameVersionType.ALPHA,
        description="Testing milestone performance",
        annotations={"test": "value", "performance": "good"},
        tags=["performance", "test"]
    )
    
    elapsed_time = time.time() - start_time
    
    # Calculate project size in GB
    total_size = sum(os.path.getsize(f) for f in large_test_project.glob("**/*") if os.path.isfile(f))
    project_size_gb = total_size / (1024 * 1024 * 1024)
    
    # Calculate processing rate in GB/minute
    processing_rate = (project_size_gb / elapsed_time) * 60
    
    # Requirement: Process at least 1GB/minute
    print(f"Project size: {project_size_gb:.6f} GB")
    print(f"Processing time: {elapsed_time:.2f} seconds")
    print(f"Processing rate: {processing_rate:.2f} GB/minute")
    
    # Verify requirement is met
    assert processing_rate >= 1.0, f"Processing rate below requirement: {processing_rate:.2f} < 1.0 GB/minute"


def test_platform_config_comparison_performance():
    """Test performance of comparing platform configurations."""
    from gamevault.models import PlatformConfig, PlatformType
    from gamevault.platform_config.manager import PlatformConfigManager
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a platform config manager
        manager = PlatformConfigManager("perf_test", temp_dir)
        
        # Create configurations with many settings
        def create_large_config(platform_type, settings_count=1000):
            settings = {}
            build_flags = {}
            required_features = set()
            disabled_features = set()
            
            for i in range(settings_count):
                settings[f"setting_{i}"] = f"value_{i}"
                
                if i % 10 == 0:
                    build_flags[f"FLAG_{i}"] = "1"
                
                if i % 20 == 0:
                    required_features.add(f"feature_{i}")
                
                if i % 25 == 0:
                    disabled_features.add(f"feature_{i+5}")
            
            return PlatformConfig(
                platform=platform_type,
                settings=settings,
                build_flags=build_flags,
                required_features=required_features,
                disabled_features=disabled_features
            )
        
        # Create configs for different platforms
        pc_config = create_large_config(PlatformType.PC)
        mobile_config = create_large_config(PlatformType.MOBILE)
        
        # Save configs
        manager.save_config(pc_config, "v1.0")
        manager.save_config(mobile_config, "v1.0")
        
        # Measure time to compare configurations
        start_time = time.time()
        comparison = manager.compare_configs(
            PlatformType.PC, "v1.0",
            PlatformType.MOBILE, "v1.0"
        )
        elapsed_time = time.time() - start_time
        
        # Requirement: Configuration comparison must complete in under 10 seconds
        print(f"Comparison time: {elapsed_time:.2f} seconds")
        
        # Verify requirement is met
        assert elapsed_time < 10.0, f"Configuration comparison time exceeded requirement: {elapsed_time:.2f} > 10.0 seconds"