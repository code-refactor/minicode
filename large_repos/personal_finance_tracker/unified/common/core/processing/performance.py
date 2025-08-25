"""
Performance monitoring utilities for financial applications.

This module provides tools for measuring, monitoring, and analyzing
the performance of financial data processing operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union, ContextManager
from dataclasses import dataclass, field
import datetime
from datetime import timedelta
from contextlib import contextmanager
from functools import wraps
import time
import threading
import psutil
import gc
from collections import defaultdict, deque
import statistics
import logging

# Factory function for default datetime
def _now():
    return datetime.datetime.now()

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Represents a single performance measurement."""
    name: str
    value: float
    unit: str
    timestamp: datetime.datetime = field(default_factory=_now)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimingResult:
    """Result of a timing measurement."""
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_milliseconds(self) -> float:
        """Get duration in milliseconds."""
        return self.duration_seconds * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "duration_milliseconds": self.duration_milliseconds,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


class PerformanceTracker:
    """
    Thread-safe performance tracking utility.
    
    Collects timing measurements and system metrics for analysis.
    """
    
    def __init__(self, max_history: int = 10000):
        """
        Initialize performance tracker.
        
        Args:
            max_history: Maximum number of timing results to keep in history
        """
        self.max_history = max_history
        self._timing_results: deque = deque(maxlen=max_history)
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.Lock()
        self._start_time = datetime.datetime.now()
    
    def record_timing(self, result: TimingResult) -> None:
        """Record a timing result."""
        with self._lock:
            self._timing_results.append(result)
    
    def record_metric(self, name: str, value: float, unit: str = "", tags: Dict[str, str] = None) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            tags=tags or {}
        )
        
        with self._lock:
            self._metrics[name].append(metric)
    
    @contextmanager
    def time_operation(self, operation_name: str, metadata: Dict[str, Any] = None) -> ContextManager[TimingResult]:
        """
        Context manager for timing operations.
        
        Args:
            operation_name: Name of the operation being timed
            metadata: Optional metadata to include in the result
            
        Yields:
            TimingResult object that gets populated during execution
        """
        start_time = datetime.datetime.now()
        result = TimingResult(
            operation_name=operation_name,
            start_time=start_time,
            end_time=start_time,  # Will be updated
            duration_seconds=0.0,
            metadata=metadata or {}
        )
        
        try:
            yield result
            result.success = True
        except Exception as e:
            result.success = False
            result.error = str(e)
            raise
        finally:
            result.end_time = datetime.datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            self.record_timing(result)
    
    def get_timing_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get timing statistics for operations.
        
        Args:
            operation_name: Optional operation name to filter by
            
        Returns:
            Dictionary of timing statistics
        """
        with self._lock:
            results = list(self._timing_results)
        
        if operation_name:
            results = [r for r in results if r.operation_name == operation_name]
        
        if not results:
            return {"error": "No timing data available"}
        
        durations = [r.duration_seconds for r in results if r.success]
        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count
        
        stats = {
            "operation_name": operation_name or "all_operations",
            "total_calls": len(results),
            "success_calls": success_count,
            "error_calls": error_count,
            "success_rate": (success_count / len(results)) * 100 if results else 0,
        }
        
        if durations:
            stats.update({
                "avg_duration_seconds": statistics.mean(durations),
                "min_duration_seconds": min(durations),
                "max_duration_seconds": max(durations),
                "median_duration_seconds": statistics.median(durations),
                "total_duration_seconds": sum(durations),
                "calls_per_second": len(durations) / sum(durations) if sum(durations) > 0 else 0
            })
            
            if len(durations) > 1:
                stats["stddev_duration_seconds"] = statistics.stdev(durations)
        
        return stats
    
    def get_recent_timings(self, count: int = 100, operation_name: Optional[str] = None) -> List[TimingResult]:
        """
        Get recent timing results.
        
        Args:
            count: Number of recent results to return
            operation_name: Optional operation name to filter by
            
        Returns:
            List of recent timing results
        """
        with self._lock:
            results = list(self._timing_results)
        
        if operation_name:
            results = [r for r in results if r.operation_name == operation_name]
        
        return results[-count:] if results else []
    
    def get_metric_history(self, metric_name: str, count: int = 100) -> List[PerformanceMetric]:
        """
        Get recent metric history.
        
        Args:
            metric_name: Name of the metric
            count: Number of recent metrics to return
            
        Returns:
            List of recent performance metrics
        """
        with self._lock:
            metrics = list(self._metrics.get(metric_name, []))
        
        return metrics[-count:] if metrics else []
    
    def get_all_operation_names(self) -> List[str]:
        """Get list of all tracked operation names."""
        with self._lock:
            return list(set(r.operation_name for r in self._timing_results))
    
    def clear_history(self, operation_name: Optional[str] = None) -> None:
        """
        Clear timing history.
        
        Args:
            operation_name: Optional operation name to clear (clears all if None)
        """
        with self._lock:
            if operation_name:
                # Remove only specific operations
                filtered_results = [
                    r for r in self._timing_results 
                    if r.operation_name != operation_name
                ]
                self._timing_results.clear()
                self._timing_results.extend(filtered_results)
            else:
                # Clear all
                self._timing_results.clear()
                self._metrics.clear()


class SystemMonitor:
    """
    Monitor system resources during operation.
    
    Tracks CPU, memory, and other system metrics.
    """
    
    def __init__(self, sample_interval: float = 1.0):
        """
        Initialize system monitor.
        
        Args:
            sample_interval: Interval between samples in seconds
        """
        self.sample_interval = sample_interval
        self._process = psutil.Process()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._samples: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def start_monitoring(self) -> None:
        """Start monitoring system resources."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop monitoring system resources."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            # Process metrics
            process_info = self._process.as_dict([
                'pid', 'cpu_percent', 'memory_percent', 'memory_info',
                'num_threads', 'create_time'
            ])
            
            # System metrics
            system_cpu = psutil.cpu_percent(interval=0.1)
            system_memory = psutil.virtual_memory()
            
            return {
                "timestamp": datetime.datetime.now().isoformat(),
                "process": {
                    "pid": process_info['pid'],
                    "cpu_percent": process_info['cpu_percent'],
                    "memory_percent": process_info['memory_percent'],
                    "memory_rss_mb": process_info['memory_info'].rss / (1024 * 1024),
                    "memory_vms_mb": process_info['memory_info'].vms / (1024 * 1024),
                    "num_threads": process_info['num_threads'],
                    "uptime_seconds": time.time() - process_info['create_time']
                },
                "system": {
                    "cpu_percent": system_cpu,
                    "memory_percent": system_memory.percent,
                    "memory_available_gb": system_memory.available / (1024 ** 3),
                    "memory_used_gb": system_memory.used / (1024 ** 3),
                    "memory_total_gb": system_memory.total / (1024 ** 3)
                }
            }
        except Exception as e:
            logger.warning(f"Error collecting system metrics: {e}")
            return {"error": str(e)}
    
    def get_sample_history(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent sample history."""
        with self._lock:
            return self._samples[-count:] if self._samples else []
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                metrics = self.get_current_metrics()
                
                with self._lock:
                    self._samples.append(metrics)
                    # Keep only recent samples (last 1000)
                    if len(self._samples) > 1000:
                        self._samples = self._samples[-1000:]
                
                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.sample_interval)


class PerformanceMonitor:
    """
    Comprehensive performance monitoring for financial applications.
    
    Combines timing tracking and system monitoring with analysis capabilities.
    """
    
    def __init__(
        self,
        enable_system_monitoring: bool = True,
        system_sample_interval: float = 5.0
    ):
        """
        Initialize performance monitor.
        
        Args:
            enable_system_monitoring: Whether to enable system resource monitoring
            system_sample_interval: Interval for system monitoring in seconds
        """
        self.tracker = PerformanceTracker()
        self.system_monitor = SystemMonitor(system_sample_interval) if enable_system_monitoring else None
        
        if self.system_monitor:
            self.system_monitor.start_monitoring()
    
    def time_operation(self, operation_name: str, metadata: Dict[str, Any] = None):
        """Context manager for timing operations."""
        return self.tracker.time_operation(operation_name, metadata)
    
    def record_metric(self, name: str, value: float, unit: str = "", tags: Dict[str, str] = None) -> None:
        """Record a performance metric."""
        self.tracker.record_metric(name, value, unit, tags)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.
        
        Returns:
            Dictionary containing performance analysis
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "timing_stats": {},
            "system_metrics": None,
            "summary": {}
        }
        
        # Get timing statistics for all operations
        operation_names = self.tracker.get_all_operation_names()
        for op_name in operation_names:
            report["timing_stats"][op_name] = self.tracker.get_timing_stats(op_name)
        
        # Get overall timing stats
        if operation_names:
            report["timing_stats"]["overall"] = self.tracker.get_timing_stats()
        
        # Get system metrics if available
        if self.system_monitor:
            report["system_metrics"] = self.system_monitor.get_current_metrics()
        
        # Generate summary
        if report["timing_stats"]:
            overall_stats = report["timing_stats"].get("overall", {})
            report["summary"] = {
                "total_operations": overall_stats.get("total_calls", 0),
                "success_rate": overall_stats.get("success_rate", 0),
                "avg_response_time_ms": overall_stats.get("avg_duration_seconds", 0) * 1000,
                "operations_per_second": overall_stats.get("calls_per_second", 0),
                "tracked_operations": len(operation_names)
            }
        
        return report
    
    def identify_performance_issues(self) -> List[Dict[str, Any]]:
        """
        Identify potential performance issues.
        
        Returns:
            List of identified issues with recommendations
        """
        issues = []
        
        # Check each operation for issues
        for op_name in self.tracker.get_all_operation_names():
            stats = self.tracker.get_timing_stats(op_name)
            
            # High error rate
            if stats.get("error_calls", 0) > 0:
                error_rate = (stats["error_calls"] / stats["total_calls"]) * 100
                if error_rate > 5:  # More than 5% errors
                    issues.append({
                        "type": "high_error_rate",
                        "operation": op_name,
                        "error_rate": error_rate,
                        "recommendation": f"Investigate errors in {op_name} operation",
                        "severity": "high" if error_rate > 20 else "medium"
                    })
            
            # Slow operations
            avg_duration = stats.get("avg_duration_seconds", 0)
            if avg_duration > 1.0:  # Slower than 1 second
                issues.append({
                    "type": "slow_operation",
                    "operation": op_name,
                    "avg_duration_seconds": avg_duration,
                    "recommendation": f"Optimize {op_name} operation performance",
                    "severity": "high" if avg_duration > 5.0 else "medium"
                })
            
            # High variability
            if "stddev_duration_seconds" in stats:
                cv = stats["stddev_duration_seconds"] / avg_duration if avg_duration > 0 else 0
                if cv > 0.5:  # Coefficient of variation > 50%
                    issues.append({
                        "type": "high_variability",
                        "operation": op_name,
                        "coefficient_of_variation": cv,
                        "recommendation": f"Investigate timing variability in {op_name}",
                        "severity": "medium"
                    })
        
        # Check system resource issues
        if self.system_monitor:
            current_metrics = self.system_monitor.get_current_metrics()
            
            if "process" in current_metrics:
                process_metrics = current_metrics["process"]
                
                # High memory usage
                if process_metrics.get("memory_percent", 0) > 80:
                    issues.append({
                        "type": "high_memory_usage",
                        "memory_percent": process_metrics["memory_percent"],
                        "recommendation": "Monitor memory usage and consider optimization",
                        "severity": "high" if process_metrics["memory_percent"] > 95 else "medium"
                    })
                
                # High CPU usage
                if process_metrics.get("cpu_percent", 0) > 80:
                    issues.append({
                        "type": "high_cpu_usage",
                        "cpu_percent": process_metrics["cpu_percent"],
                        "recommendation": "Monitor CPU usage and consider optimization",
                        "severity": "high" if process_metrics["cpu_percent"] > 95 else "medium"
                    })
        
        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 2))
        
        return issues
    
    def cleanup(self) -> None:
        """Clean up monitoring resources."""
        if self.system_monitor:
            self.system_monitor.stop_monitoring()


def timed(operation_name: str = None, monitor: PerformanceMonitor = None):
    """
    Decorator for timing function execution.
    
    Args:
        operation_name: Name for the operation (defaults to function name)
        monitor: Performance monitor to use (creates default if None)
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        nonlocal monitor
        if monitor is None:
            monitor = PerformanceMonitor(enable_system_monitoring=False)
        
        op_name = operation_name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            with monitor.time_operation(op_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_global_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


@contextmanager
def memory_profiling():
    """
    Context manager for memory profiling.
    
    Tracks memory usage before and after a block of code.
    """
    import psutil
    
    process = psutil.Process()
    
    # Force garbage collection before measurement
    gc.collect()
    
    # Get initial memory usage
    initial_memory = process.memory_info()
    start_time = time.time()
    
    try:
        yield
    finally:
        # Get final memory usage
        gc.collect()  # Force garbage collection after operation
        final_memory = process.memory_info()
        end_time = time.time()
        
        # Calculate differences
        rss_diff = final_memory.rss - initial_memory.rss
        vms_diff = final_memory.vms - initial_memory.vms
        
        logger.info(
            f"Memory usage: RSS {rss_diff/1024/1024:.2f}MB change, "
            f"VMS {vms_diff/1024/1024:.2f}MB change, "
            f"Duration: {end_time - start_time:.3f}s"
        )


# Convenience decorators using global monitor
def time_financial_operation(operation_name: str = None):
    """Decorator for timing financial operations using global monitor."""
    return timed(operation_name, get_global_monitor())