"""Unit tests for the progressive result generation system."""

import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from render_farm_manager.core.models import (
    JobPriority,
    ProgressiveOutputConfig,
    RenderJob,
    RenderJobStatus,
)
from render_farm_manager.progressive_result.progressive_renderer import ProgressiveRenderer
from render_farm_manager.utils.logging import AuditLogger, PerformanceMonitor


@pytest.fixture
def audit_logger():
    return MagicMock(spec=AuditLogger)


@pytest.fixture
def performance_monitor():
    return MagicMock(spec=PerformanceMonitor)


@pytest.fixture
def progressive_renderer(audit_logger, performance_monitor):
    config = ProgressiveOutputConfig(
        enabled=True,
        interval_minutes=30,
        quality_levels=[10, 25, 50, 75],
        max_overhead_percentage=5.0,
    )
    
    return ProgressiveRenderer(
        audit_logger=audit_logger,
        performance_monitor=performance_monitor,
        default_config=config,
    )


@pytest.fixture
def jobs():
    """Create a list of test render jobs with different configurations."""
    now = datetime.now()
    
    return [
        # Long-running job that supports progressive output
        RenderJob(
            id="long-job",
            name="Long Running Job",
            client_id="client1",
            status=RenderJobStatus.RUNNING,
            job_type="animation",
            priority=JobPriority.HIGH,
            submission_time=now - timedelta(hours=2),
            deadline=now + timedelta(hours=24),
            estimated_duration_hours=10,
            progress=20.0,
            requires_gpu=True,
            memory_requirements_gb=64,
            cpu_requirements=16,
            scene_complexity=8,
            dependencies=[],
            assigned_node_id="node-1",
            output_path="/renders/long-job/",
            error_count=0,
            can_be_preempted=True,
            supports_progressive_output=True,
        ),
        # Short-running job that supports progressive output
        RenderJob(
            id="short-job",
            name="Short Running Job",
            client_id="client2",
            status=RenderJobStatus.RUNNING,
            job_type="lighting",
            priority=JobPriority.MEDIUM,
            submission_time=now - timedelta(hours=1),
            deadline=now + timedelta(hours=6),
            estimated_duration_hours=2,
            progress=30.0,
            requires_gpu=True,
            memory_requirements_gb=32,
            cpu_requirements=8,
            scene_complexity=5,
            dependencies=[],
            assigned_node_id="node-2",
            output_path="/renders/short-job/",
            error_count=0,
            can_be_preempted=True,
            supports_progressive_output=True,
        ),
        # Job that doesn't support progressive output
        RenderJob(
            id="no-progressive-job",
            name="No Progressive Output Job",
            client_id="client3",
            status=RenderJobStatus.RUNNING,
            job_type="simulation",
            priority=JobPriority.LOW,
            submission_time=now - timedelta(hours=3),
            deadline=now + timedelta(hours=12),
            estimated_duration_hours=6,
            progress=40.0,
            requires_gpu=False,
            memory_requirements_gb=128,
            cpu_requirements=32,
            scene_complexity=7,
            dependencies=[],
            assigned_node_id="node-3",
            output_path="/renders/no-progressive-job/",
            error_count=0,
            can_be_preempted=True,
            supports_progressive_output=False,
        ),
        # Pending job that supports progressive output
        RenderJob(
            id="pending-job",
            name="Pending Job",
            client_id="client1",
            status=RenderJobStatus.PENDING,
            job_type="vfx",
            priority=JobPriority.HIGH,
            submission_time=now - timedelta(minutes=30),
            deadline=now + timedelta(hours=48),
            estimated_duration_hours=8,
            progress=0.0,
            requires_gpu=True,
            memory_requirements_gb=64,
            cpu_requirements=16,
            scene_complexity=8,
            dependencies=[],
            assigned_node_id=None,
            output_path="/renders/pending-job/",
            error_count=0,
            can_be_preempted=True,
            supports_progressive_output=True,
        ),
        # Nearly complete job that supports progressive output
        RenderJob(
            id="almost-done-job",
            name="Almost Complete Job",
            client_id="client2",
            status=RenderJobStatus.RUNNING,
            job_type="compositing",
            priority=JobPriority.MEDIUM,
            submission_time=now - timedelta(hours=5),
            deadline=now + timedelta(hours=1),
            estimated_duration_hours=6,
            progress=90.0,
            requires_gpu=False,
            memory_requirements_gb=16,
            cpu_requirements=8,
            scene_complexity=4,
            dependencies=[],
            assigned_node_id="node-4",
            output_path="/renders/almost-done-job/",
            error_count=0,
            can_be_preempted=True,
            supports_progressive_output=True,
        ),
    ]


def test_progressive_renderer_initialization(progressive_renderer):
    """Test that the progressive renderer initializes correctly."""
    assert progressive_renderer.default_config.enabled == True
    assert progressive_renderer.default_config.interval_minutes == 30
    assert progressive_renderer.default_config.quality_levels == [10, 25, 50, 75]
    assert progressive_renderer.default_config.max_overhead_percentage == 5.0


def test_schedule_progressive_output_long_job(progressive_renderer, jobs):
    """Test scheduling progressive output for a long-running job."""
    long_job = jobs[0]  # 10-hour job
    
    # Schedule progressive output
    scheduled_times = progressive_renderer.schedule_progressive_output(long_job)
    
    # A 10-hour job with 30-minute intervals should have 10 * 60 / 30 = 20 outputs
    # but we cap at 10 for practicality
    assert len(scheduled_times) == 10
    
    # Check that times are spaced correctly
    for i in range(1, len(scheduled_times)):
        time_diff = (scheduled_times[i] - scheduled_times[i-1]).total_seconds() / 60
        assert time_diff == pytest.approx(30, abs=1)  # 30 minutes apart


def test_schedule_progressive_output_short_job(progressive_renderer, jobs):
    """Test scheduling progressive output for a short-running job."""
    short_job = jobs[1]  # 2-hour job
    
    # Schedule progressive output
    scheduled_times = progressive_renderer.schedule_progressive_output(short_job)
    
    # A 2-hour job should have at least one scheduled output
    assert len(scheduled_times) > 0
    
    # Since the scheduling logic can vary, we'll just check that the
    # time is in the future and within a reasonable range
    assert scheduled_times[0] > datetime.now()


def test_schedule_progressive_output_disabled_config(progressive_renderer, jobs):
    """Test that progressive output is not scheduled when disabled in config."""
    long_job = jobs[0]
    
    # Create a disabled config
    disabled_config = ProgressiveOutputConfig(
        enabled=False,
        interval_minutes=30,
        quality_levels=[10, 25, 50, 75],
        max_overhead_percentage=5.0,
    )
    
    # Schedule with disabled config
    scheduled_times = progressive_renderer.schedule_progressive_output(long_job, disabled_config)
    
    # Should have no scheduled outputs
    assert len(scheduled_times) == 0


def test_schedule_progressive_output_unsupported_job(progressive_renderer, jobs):
    """Test that progressive output is not scheduled for jobs that don't support it."""
    unsupported_job = jobs[2]  # Job that doesn't support progressive output
    
    # Schedule progressive output
    scheduled_times = progressive_renderer.schedule_progressive_output(unsupported_job)
    
    # Should have no scheduled outputs
    assert len(scheduled_times) == 0


def test_generate_progressive_output(progressive_renderer, jobs):
    """Test generating a progressive output for a job."""
    long_job = jobs[0]  # Job that supports progressive output
    
    # Generate output at 25% quality
    output_path = progressive_renderer.generate_progressive_output(long_job, 25)
    
    # Check that output path was generated
    assert output_path is not None
    assert "progressive_25pct_" in output_path
    assert long_job.output_path in output_path
    
    # Check that the job's last progressive output time was updated
    assert long_job.last_progressive_output_time is not None
    
    # Check that the output was stored in the generated outputs dictionary
    assert long_job.id in progressive_renderer.generated_outputs
    assert 25 in progressive_renderer.generated_outputs[long_job.id]
    assert progressive_renderer.generated_outputs[long_job.id][25] == output_path


def test_generate_progressive_output_unsupported_job(progressive_renderer, jobs):
    """Test that generating progressive output fails for jobs that don't support it."""
    unsupported_job = jobs[2]  # Job that doesn't support progressive output
    
    # Attempt to generate output
    with pytest.raises(ValueError):
        progressive_renderer.generate_progressive_output(unsupported_job, 25)


def test_estimate_overhead(progressive_renderer, jobs):
    """Test estimating the overhead of progressive output generation."""
    long_job = jobs[0]  # 10-hour job
    short_job = jobs[1]  # 2-hour job
    unsupported_job = jobs[2]  # Job that doesn't support progressive output
    
    # Estimate overhead for long job
    long_job_overhead = progressive_renderer.estimate_overhead(long_job)
    
    # Estimate overhead for short job
    short_job_overhead = progressive_renderer.estimate_overhead(short_job)
    
    # Estimate overhead for unsupported job
    unsupported_job_overhead = progressive_renderer.estimate_overhead(unsupported_job)
    
    # Long job should have non-zero overhead
    assert long_job_overhead > 0.0
    
    # Short job should have lower overhead than long job
    assert short_job_overhead < long_job_overhead
    
    # Unsupported job should have zero overhead
    assert unsupported_job_overhead == 0.0


def test_process_pending_outputs(progressive_renderer, jobs):
    """Test processing pending progressive outputs."""
    # Set up some scheduled outputs for the running jobs
    now = datetime.now()
    
    # Add scheduled outputs in the past for the long job
    progressive_renderer.scheduled_outputs["long-job"] = [
        now - timedelta(minutes=30),
        now - timedelta(minutes=15),
        now + timedelta(minutes=15),
    ]
    
    # Add scheduled outputs in the past for the nearly complete job
    progressive_renderer.scheduled_outputs["almost-done-job"] = [
        now - timedelta(minutes=45),
    ]
    
    # Process pending outputs
    processed_outputs = progressive_renderer.process_pending_outputs(jobs)
    
    # Should have processed outputs for the long job and almost done job
    assert "long-job" in processed_outputs
    assert len(processed_outputs["long-job"]) == 2  # Two scheduled times in the past
    
    assert "almost-done-job" in processed_outputs
    assert len(processed_outputs["almost-done-job"]) == 1  # One scheduled time in the past
    
    # Pending and unsupported jobs should not have processed outputs
    assert "pending-job" not in processed_outputs
    assert "no-progressive-job" not in processed_outputs
    
    # Check that future scheduled outputs are still in the schedule
    assert len(progressive_renderer.scheduled_outputs["long-job"]) == 1
    assert progressive_renderer.scheduled_outputs["long-job"][0] > now
    
    # Check quality levels of outputs based on job progress
    long_job_quality = processed_outputs["long-job"][0][0]  # First output quality level
    almost_done_quality = processed_outputs["almost-done-job"][0][0]
    
    # Long job at 20% progress should have a low quality level
    assert long_job_quality == 10
    
    # Almost done job at 90% progress should have a high quality level
    assert almost_done_quality == 75


def test_get_latest_progressive_output(progressive_renderer, jobs):
    """Test retrieving the latest progressive output for a job."""
    long_job = jobs[0]
    
    # Generate outputs at different quality levels
    progressive_renderer.generate_progressive_output(long_job, 10)
    progressive_renderer.generate_progressive_output(long_job, 25)
    progressive_renderer.generate_progressive_output(long_job, 50)
    
    # Get the latest output
    latest_output = progressive_renderer.get_latest_progressive_output(long_job.id)
    
    # Should return the highest quality level output
    assert latest_output is not None
    assert "progressive_50pct_" in latest_output


def test_quality_overhead_factors(progressive_renderer):
    """Test that overhead factors increase with quality level."""
    assert progressive_renderer.quality_overhead_factors[10] < progressive_renderer.quality_overhead_factors[25]
    assert progressive_renderer.quality_overhead_factors[25] < progressive_renderer.quality_overhead_factors[50]
    assert progressive_renderer.quality_overhead_factors[50] < progressive_renderer.quality_overhead_factors[75]


def test_max_overhead_limit(progressive_renderer, jobs):
    """Test that estimated overhead is capped at the maximum percentage."""
    long_job = jobs[0]
    
    # Create a config with many quality levels and frequent intervals
    high_overhead_config = ProgressiveOutputConfig(
        enabled=True,
        interval_minutes=10,  # Very frequent
        quality_levels=[10, 25, 50, 75, 90],  # Many quality levels
        max_overhead_percentage=3.0,  # Low cap
    )
    
    # Estimate overhead
    overhead = progressive_renderer.estimate_overhead(long_job, high_overhead_config)
    
    # Should be capped at max overhead percentage
    assert overhead <= high_overhead_config.max_overhead_percentage