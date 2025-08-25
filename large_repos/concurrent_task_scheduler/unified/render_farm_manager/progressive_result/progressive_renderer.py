"""Progressive result generation system for the Render Farm Manager."""

import logging
import math
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from render_farm_manager.core.interfaces import ProgressiveResultInterface
from render_farm_manager.core.models import (
    ProgressiveOutputConfig,
    RenderJob,
    RenderJobStatus,
)
from render_farm_manager.utils.logging import AuditLogger, PerformanceMonitor


class ProgressiveRenderer(ProgressiveResultInterface):
    """
    Progressive result generation system for providing early feedback on renders.
    
    This system allows artists and directors to identify issues early in the rendering
    process without waiting for complete high-resolution frames.
    """
    
    def __init__(
        self,
        audit_logger: AuditLogger,
        performance_monitor: PerformanceMonitor,
        default_config: Optional[ProgressiveOutputConfig] = None,
    ):
        """
        Initialize the progressive renderer.
        
        Args:
            audit_logger: Logger for audit trail events
            performance_monitor: Monitor for tracking renderer performance
            default_config: Default configuration for progressive output generation
        """
        self.audit_logger = audit_logger
        self.performance_monitor = performance_monitor
        self.default_config = default_config or ProgressiveOutputConfig()
        self.logger = logging.getLogger("render_farm.progressive_renderer")
        
        # Dictionary to track scheduled progressive outputs for jobs
        self.scheduled_outputs: Dict[str, List[datetime]] = {}
        
        # Dictionary to track generated progressive outputs for jobs
        self.generated_outputs: Dict[str, Dict[int, str]] = {}
        
        # Overhead factors for different quality levels
        self.quality_overhead_factors: Dict[int, float] = {
            10: 0.02,  # 10% quality adds 2% overhead
            25: 0.03,  # 25% quality adds 3% overhead
            50: 0.05,  # 50% quality adds 5% overhead
            75: 0.08,  # 75% quality adds 8% overhead
        }
    
    def schedule_progressive_output(
        self, job: RenderJob, config: Optional[ProgressiveOutputConfig] = None
    ) -> List[datetime]:
        """
        Schedule progressive output generation for a job.
        
        Args:
            job: The render job
            config: Configuration for progressive output generation
            
        Returns:
            List of scheduled times for progressive output generation
        """
        with self.performance_monitor.time_operation("schedule_progressive_output"):
            # Use provided config or fall back to default
            cfg = config or self.default_config
            
            # Skip if progressive output is disabled or not supported by the job
            if not cfg.enabled or not job.supports_progressive_output:
                self.scheduled_outputs[job.id] = []
                return []
            
            # Calculate job duration in minutes
            job_duration_minutes = job.estimated_duration_hours * 60
            
            # Calculate number of progressive outputs
            if job_duration_minutes <= cfg.interval_minutes:
                # Job is shorter than the interval, schedule one output at halfway point
                num_outputs = 1
                interval = job_duration_minutes / 2
            else:
                # Calculate regular interval outputs
                num_outputs = math.floor(job_duration_minutes / cfg.interval_minutes)
                interval = cfg.interval_minutes
            
            # Limit the number of outputs to something reasonable
            num_outputs = min(num_outputs, 10)
            
            # Calculate start time (assuming the job starts now)
            start_time = datetime.now()
            if job.submission_time > start_time:
                start_time = job.submission_time
            
            # Calculate scheduled times
            scheduled_times = []
            for i in range(1, num_outputs + 1):
                output_time = start_time + timedelta(minutes=i * interval)
                scheduled_times.append(output_time)
            
            # Store scheduled times for this job
            self.scheduled_outputs[job.id] = scheduled_times
            
            # Log the schedule
            self.audit_logger.log_event(
                "progressive_output_scheduled",
                f"Progressive output scheduled for job {job.id} with {num_outputs} outputs",
                job_id=job.id,
                num_outputs=num_outputs,
                interval_minutes=interval,
                scheduled_times=[t.isoformat() for t in scheduled_times],
            )
            
            return scheduled_times
    
    def generate_progressive_output(self, job: RenderJob, quality_level: int) -> str:
        """
        Generate a progressive output for a job at a specific quality level.
        
        Args:
            job: The render job
            quality_level: Quality level for the progressive output
            
        Returns:
            Path to the generated progressive output
        """
        with self.performance_monitor.time_operation("generate_progressive_output"):
            # In a real implementation, this would interact with the rendering engine
            # to generate a progressive output. For this simulation, we'll just create
            # a virtual output path.
            
            # Ensure the job supports progressive output
            if not job.supports_progressive_output:
                error_msg = f"Job {job.id} does not support progressive output"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Create a theoretical output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"progressive_{quality_level}pct_{timestamp}.exr"
            output_path = os.path.join(job.output_path, "progressive", output_filename)
            
            # In a real implementation, we would generate the output here
            # For simulation, we'll just log the event
            
            # Store the output in the generated outputs dictionary
            if job.id not in self.generated_outputs:
                self.generated_outputs[job.id] = {}
            
            self.generated_outputs[job.id][quality_level] = output_path
            
            # Update the job's last progressive output time
            job.last_progressive_output_time = datetime.now()
            
            # Log the generation
            self.audit_logger.log_event(
                "progressive_output_generated",
                f"Progressive output generated for job {job.id} at {quality_level}% quality",
                job_id=job.id,
                quality_level=quality_level,
                output_path=output_path,
                job_progress=job.progress,
            )
            
            return output_path
    
    def estimate_overhead(self, job: RenderJob, config: Optional[ProgressiveOutputConfig] = None) -> float:
        """
        Estimate the overhead of progressive output generation for a job.
        
        Args:
            job: The render job
            config: Configuration for progressive output generation
            
        Returns:
            Estimated overhead as a percentage of total rendering time
        """
        # Use provided config or fall back to default
        cfg = config or self.default_config
        
        # If progressive output is disabled or not supported, there's no overhead
        if not cfg.enabled or not job.supports_progressive_output:
            return 0.0
        
        # Calculate job duration in minutes
        job_duration_minutes = job.estimated_duration_hours * 60
        
        # Calculate number of progressive outputs
        if job_duration_minutes <= cfg.interval_minutes:
            num_outputs = 1
        else:
            num_outputs = math.floor(job_duration_minutes / cfg.interval_minutes)
        
        # Limit the number of outputs to something reasonable
        num_outputs = min(num_outputs, 10)
        
        # Calculate overhead for each quality level
        total_overhead = 0.0
        for quality_level in cfg.quality_levels:
            if quality_level in self.quality_overhead_factors:
                overhead_factor = self.quality_overhead_factors[quality_level]
                total_overhead += overhead_factor
        
        # Multiply by the number of outputs
        total_overhead *= num_outputs
        
        # Cap at the maximum overhead percentage
        total_overhead = min(total_overhead, cfg.max_overhead_percentage)
        
        return total_overhead
    
    def get_latest_progressive_output(self, job_id: str) -> Optional[str]:
        """
        Get the path to the latest progressive output for a job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            Path to the latest progressive output, or None if no output is available
        """
        if job_id not in self.generated_outputs or not self.generated_outputs[job_id]:
            return None
        
        # Find the highest quality level that has been generated
        highest_quality = max(self.generated_outputs[job_id].keys())
        
        return self.generated_outputs[job_id][highest_quality]
    
    def process_pending_outputs(self, jobs: List[RenderJob]) -> Dict[str, List[Tuple[int, str]]]:
        """
        Process any pending progressive outputs that are due.
        
        Args:
            jobs: List of render jobs
            
        Returns:
            Dictionary mapping job IDs to lists of (quality_level, output_path) tuples
        """
        now = datetime.now()
        processed_outputs: Dict[str, List[Tuple[int, str]]] = {}
        
        for job in jobs:
            # Skip if job is not running or doesn't support progressive output
            if job.status != RenderJobStatus.RUNNING or not job.supports_progressive_output:
                continue
            
            # Skip if no scheduled outputs for this job
            if job.id not in self.scheduled_outputs:
                continue
            
            # Get scheduled times that are due
            due_times = [t for t in self.scheduled_outputs[job.id] if t <= now]
            
            if not due_times:
                continue
            
            # Remove due times from the schedule
            self.scheduled_outputs[job.id] = [
                t for t in self.scheduled_outputs[job.id] if t > now
            ]
            
            # Generate outputs for each due time
            job_outputs = []
            for time in due_times:
                # Determine quality level based on job progress
                if job.progress < 25:
                    quality_level = 10
                elif job.progress < 50:
                    quality_level = 25
                elif job.progress < 75:
                    quality_level = 50
                else:
                    quality_level = 75
                
                # Generate the output
                output_path = self.generate_progressive_output(job, quality_level)
                job_outputs.append((quality_level, output_path))
            
            if job_outputs:
                processed_outputs[job.id] = job_outputs
        
        return processed_outputs