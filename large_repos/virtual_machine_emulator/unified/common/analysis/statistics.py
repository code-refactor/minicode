"""Statistics collection and analysis framework."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import defaultdict
import time


@dataclass
class Metric:
    """Single metric measurement."""
    
    name: str
    value: float
    unit: str = ""
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def __repr__(self) -> str:
        """String representation."""
        unit_str = f" {self.unit}" if self.unit else ""
        return f"{self.name}: {self.value}{unit_str}"


class StatisticsCollector:
    """Collect and analyze performance statistics."""
    
    def __init__(self):
        """Initialize statistics collector."""
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.start_time = time.time()
        
    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        self.counters[name] += value
    
    def decrement(self, name: str, value: int = 1) -> None:
        """Decrement a counter."""
        self.counters[name] -= value
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        self.gauges[name] = value
    
    def record_value(self, name: str, value: float) -> None:
        """Record a value in a histogram."""
        self.histograms[name].append(value)
    
    def record_time(self, name: str, duration: float) -> None:
        """Record a time duration."""
        self.timers[name].append(duration)
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> Optional[float]:
        """Get gauge value."""
        return self.gauges.get(name)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        values = self.histograms.get(name, [])
        if not values:
            return {}
        
        sorted_values = sorted(values)
        n = len(values)
        
        return {
            'count': n,
            'min': sorted_values[0],
            'max': sorted_values[-1],
            'mean': sum(values) / n,
            'median': sorted_values[n // 2],
            'p90': sorted_values[int(n * 0.9)] if n > 0 else 0,
            'p99': sorted_values[int(n * 0.99)] if n > 0 else 0
        }
    
    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """Get timer statistics."""
        times = self.timers.get(name, [])
        if not times:
            return {}
        
        sorted_times = sorted(times)
        n = len(times)
        
        return {
            'count': n,
            'total': sum(times),
            'min': sorted_times[0],
            'max': sorted_times[-1],
            'mean': sum(times) / n,
            'median': sorted_times[n // 2],
            'p90': sorted_times[int(n * 0.9)] if n > 0 else 0,
            'p99': sorted_times[int(n * 0.99)] if n > 0 else 0
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all statistics."""
        stats = {
            'runtime': time.time() - self.start_time,
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms': {},
            'timers': {}
        }
        
        for name in self.histograms:
            stats['histograms'][name] = self.get_histogram_stats(name)
        
        for name in self.timers:
            stats['timers'][name] = self.get_timer_stats(name)
        
        return stats
    
    def reset(self) -> None:
        """Reset all statistics."""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()
        self.start_time = time.time()
    
    def merge(self, other: 'StatisticsCollector') -> None:
        """Merge statistics from another collector."""
        # Merge counters
        for name, value in other.counters.items():
            self.counters[name] += value
        
        # Update gauges (take latest value)
        self.gauges.update(other.gauges)
        
        # Merge histograms
        for name, values in other.histograms.items():
            self.histograms[name].extend(values)
        
        # Merge timers
        for name, times in other.timers.items():
            self.timers[name].extend(times)
    
    def __repr__(self) -> str:
        """String representation."""
        return (f"StatisticsCollector({len(self.counters)} counters, "
                f"{len(self.gauges)} gauges, {len(self.histograms)} histograms)")


class PerformanceMonitor:
    """Monitor performance metrics over time."""
    
    def __init__(self, window_size: int = 100):
        """Initialize performance monitor."""
        self.window_size = window_size
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.collector = StatisticsCollector()
        
    def record(self, name: str, value: float, unit: str = "") -> None:
        """Record a metric."""
        metric = Metric(name, value, unit)
        self.metrics[name].append(metric)
        
        # Maintain window size
        if len(self.metrics[name]) > self.window_size:
            self.metrics[name].pop(0)
        
        # Also record in statistics collector
        self.collector.record_value(name, value)
    
    def get_latest(self, name: str) -> Optional[Metric]:
        """Get latest metric value."""
        if name in self.metrics and self.metrics[name]:
            return self.metrics[name][-1]
        return None
    
    def get_average(self, name: str, last_n: Optional[int] = None) -> Optional[float]:
        """Get average of recent metrics."""
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        values = self.metrics[name]
        if last_n is not None:
            values = values[-last_n:]
        
        return sum(m.value for m in values) / len(values)
    
    def get_rate(self, name: str) -> Optional[float]:
        """Get rate of change for metric."""
        if name not in self.metrics or len(self.metrics[name]) < 2:
            return None
        
        first = self.metrics[name][0]
        last = self.metrics[name][-1]
        
        time_diff = last.timestamp - first.timestamp
        if time_diff == 0:
            return None
        
        return (last.value - first.value) / time_diff
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        summary = {}
        
        for name in self.metrics:
            latest = self.get_latest(name)
            summary[name] = {
                'latest': latest.value if latest else None,
                'average': self.get_average(name),
                'rate': self.get_rate(name),
                'count': len(self.metrics[name])
            }
        
        return summary