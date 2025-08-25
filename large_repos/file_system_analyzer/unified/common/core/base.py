"""
Base classes and abstract interfaces for the File System Analyzer unified library.

This module provides the foundational abstract classes that define the common
interfaces for scanners, analyzers, and other components.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Iterator, Any, TypeVar, Generic

from .types import (
    ScanStatus, Priority, FileInfo, Match, Recommendation, 
    AnalysisType, FilePath, MetadataDict
)

# Type variables for generic base classes
T = TypeVar('T')
R = TypeVar('R')

logger = logging.getLogger(__name__)


class BaseComponent(ABC):
    """Base class for all analyzer components."""
    
    def __init__(self, name: Optional[str] = None):
        """Initialize the component with an optional name."""
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        
    @property
    def version(self) -> str:
        """Return the component version."""
        return "1.0.0"
        
    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Validate the component configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
        
    def get_info(self) -> Dict[str, Any]:
        """
        Get component information.
        
        Returns:
            Dictionary containing component metadata
        """
        return {
            "name": self.name,
            "class": self.__class__.__name__,
            "version": self.version,
            "module": self.__class__.__module__,
        }


class BaseScanner(BaseComponent, Generic[T]):
    """Abstract base class for file scanners."""
    
    def __init__(self, name: Optional[str] = None):
        """Initialize the scanner."""
        super().__init__(name)
        self._scan_status = ScanStatus.PENDING
        self._scan_start_time: Optional[datetime] = None
        self._scan_end_time: Optional[datetime] = None
        
    @property
    def scan_status(self) -> ScanStatus:
        """Get the current scan status."""
        return self._scan_status
        
    @property
    def scan_duration(self) -> Optional[float]:
        """Get the scan duration in seconds."""
        if self._scan_start_time and self._scan_end_time:
            return (self._scan_end_time - self._scan_start_time).total_seconds()
        return None
        
    def _set_scan_status(self, status: ScanStatus):
        """Set the scan status and update timestamps."""
        self._scan_status = status
        
        if status == ScanStatus.IN_PROGRESS:
            self._scan_start_time = datetime.now()
            self._scan_end_time = None
        elif status in [ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]:
            self._scan_end_time = datetime.now()
            
    @abstractmethod
    def should_process_file(self, file_path: FilePath) -> bool:
        """
        Determine if a file should be processed.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file should be processed, False otherwise
        """
        pass
        
    @abstractmethod
    def scan_file(self, file_path: FilePath) -> T:
        """
        Scan a single file.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            Scan result of type T
        """
        pass
        
    def scan_directory(
        self, 
        directory_path: FilePath,
        recursive: bool = True,
        max_depth: Optional[int] = None,
        follow_symlinks: bool = False
    ) -> Iterator[T]:
        """
        Scan a directory for files.
        
        Args:
            directory_path: Path to the directory to scan
            recursive: Whether to scan recursively
            max_depth: Maximum directory depth to scan
            follow_symlinks: Whether to follow symbolic links
            
        Yields:
            Scan results of type T for each processed file
        """
        try:
            self._set_scan_status(ScanStatus.IN_PROGRESS)
            directory = Path(directory_path)
            
            if not directory.exists() or not directory.is_dir():
                self.logger.error(f"Directory {directory_path} does not exist or is not a directory")
                self._set_scan_status(ScanStatus.FAILED)
                return
                
            current_depth = 0
            
            for root, dirs, files in directory.walk():
                # Check max depth
                if max_depth is not None and current_depth >= max_depth:
                    dirs.clear()  # Don't recurse further
                    
                # Handle symlinks
                if not follow_symlinks:
                    dirs[:] = [d for d in dirs if not (root / d).is_symlink()]
                    
                # Process files
                for file_name in files:
                    file_path = root / file_name
                    
                    # Skip symlinks if not following them
                    if not follow_symlinks and file_path.is_symlink():
                        continue
                        
                    if self.should_process_file(file_path):
                        try:
                            result = self.scan_file(file_path)
                            yield result
                        except Exception as e:
                            self.logger.error(f"Error scanning file {file_path}: {e}")
                            continue
                            
                # Break if not recursive
                if not recursive:
                    break
                    
                current_depth += 1
                
            self._set_scan_status(ScanStatus.COMPLETED)
            
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory_path}: {e}")
            self._set_scan_status(ScanStatus.FAILED)
            raise


class BaseAnalyzer(BaseComponent, Generic[T, R]):
    """Abstract base class for data analyzers."""
    
    def __init__(self, analysis_type: AnalysisType, name: Optional[str] = None):
        """Initialize the analyzer."""
        super().__init__(name)
        self.analysis_type = analysis_type
        
    @abstractmethod
    def analyze(self, data: T) -> R:
        """
        Analyze the provided data.
        
        Args:
            data: Data to analyze of type T
            
        Returns:
            Analysis result of type R
        """
        pass
        
    def batch_analyze(self, data_items: List[T]) -> List[R]:
        """
        Analyze multiple data items.
        
        Args:
            data_items: List of data items to analyze
            
        Returns:
            List of analysis results
        """
        results = []
        for item in data_items:
            try:
                result = self.analyze(item)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error analyzing item: {e}")
                continue
        return results


class BasePatternMatcher(BaseComponent):
    """Abstract base class for pattern matchers."""
    
    @abstractmethod
    def match(self, content: str) -> List[Match]:
        """
        Match patterns in the provided content.
        
        Args:
            content: Content to search for patterns
            
        Returns:
            List of matches found
        """
        pass
        
    @abstractmethod
    def add_pattern(self, pattern: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a new pattern to the matcher.
        
        Args:
            pattern: Pattern to add
            metadata: Optional metadata for the pattern
        """
        pass
        
    @abstractmethod
    def remove_pattern(self, pattern: str) -> bool:
        """
        Remove a pattern from the matcher.
        
        Args:
            pattern: Pattern to remove
            
        Returns:
            True if pattern was removed, False if not found
        """
        pass


class BaseExporter(BaseComponent):
    """Abstract base class for data exporters."""
    
    @abstractmethod
    def export(
        self, 
        data: Any, 
        output_path: FilePath,
        **kwargs
    ) -> bool:
        """
        Export data to the specified path.
        
        Args:
            data: Data to export
            output_path: Path to export the data to
            **kwargs: Additional export options
            
        Returns:
            True if export was successful, False otherwise
        """
        pass
        
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported export formats.
        
        Returns:
            List of supported format identifiers
        """
        pass


class BaseResult(BaseComponent):
    """Base class for analysis results."""
    
    def __init__(
        self,
        timestamp: Optional[datetime] = None,
        duration: Optional[float] = None,
        status: ScanStatus = ScanStatus.COMPLETED,
        error_message: Optional[str] = None,
        metadata: Optional[MetadataDict] = None
    ):
        """
        Initialize the result.
        
        Args:
            timestamp: When the analysis was performed
            duration: Duration of the analysis in seconds
            status: Status of the analysis
            error_message: Error message if analysis failed
            metadata: Additional metadata
        """
        super().__init__()
        self.timestamp = timestamp or datetime.now()
        self.duration = duration
        self.status = status
        self.error_message = error_message
        self.metadata = metadata or {}
        
    def is_successful(self) -> bool:
        """Check if the result represents a successful operation."""
        return self.status == ScanStatus.COMPLETED and self.error_message is None
        
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the result."""
        self.metadata[key] = value
        
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key."""
        return self.metadata.get(key, default)


class BaseFileInfo(FileInfo):
    """Extended file information with analysis capabilities."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the file info."""
        super().__init__(*args, **kwargs)
        self._analysis_cache: Dict[str, Any] = {}
        
    def cache_analysis_result(self, analysis_type: str, result: Any) -> None:
        """Cache an analysis result for this file."""
        self._analysis_cache[analysis_type] = result
        
    def get_cached_analysis(self, analysis_type: str) -> Optional[Any]:
        """Get a cached analysis result."""
        return self._analysis_cache.get(analysis_type)
        
    def clear_analysis_cache(self) -> None:
        """Clear all cached analysis results."""
        self._analysis_cache.clear()


class BaseScanResult(BaseResult):
    """Base class for file scan results."""
    
    def __init__(
        self,
        file_info: BaseFileInfo,
        matches: Optional[List[Match]] = None,
        recommendations: Optional[List[Recommendation]] = None,
        **kwargs
    ):
        """
        Initialize the scan result.
        
        Args:
            file_info: Information about the scanned file
            matches: List of matches found in the file
            recommendations: List of recommendations for the file
            **kwargs: Additional arguments for BaseResult
        """
        super().__init__(**kwargs)
        self.file_info = file_info
        self.matches = matches or []
        self.recommendations = recommendations or []
        
    @property
    def has_findings(self) -> bool:
        """Check if the scan found any matches."""
        return len(self.matches) > 0
        
    @property
    def highest_priority(self) -> Optional[Priority]:
        """Get the highest priority finding."""
        if not self.matches:
            return None
            
        priority_values = {
            Priority.INFORMATIONAL: 0,
            Priority.LOW: 1,
            Priority.MEDIUM: 2,
            Priority.HIGH: 3,
            Priority.CRITICAL: 4
        }
        
        max_priority = max(self.matches, key=lambda m: priority_values.get(m.priority, 0))
        return max_priority.priority
        
    def add_match(self, match: Match) -> None:
        """Add a match to the results."""
        self.matches.append(match)
        
    def add_recommendation(self, recommendation: Recommendation) -> None:
        """Add a recommendation to the results."""
        self.recommendations.append(recommendation)


class BaseAnalysisResult(BaseResult):
    """Base class for analysis results."""
    
    def __init__(
        self,
        analysis_type: AnalysisType,
        total_files_processed: int = 0,
        files_with_findings: int = 0,
        total_findings: int = 0,
        recommendations: Optional[List[Recommendation]] = None,
        **kwargs
    ):
        """
        Initialize the analysis result.
        
        Args:
            analysis_type: Type of analysis performed
            total_files_processed: Total number of files processed
            files_with_findings: Number of files with findings
            total_findings: Total number of findings
            recommendations: List of recommendations from analysis
            **kwargs: Additional arguments for BaseResult
        """
        super().__init__(**kwargs)
        self.analysis_type = analysis_type
        self.total_files_processed = total_files_processed
        self.files_with_findings = files_with_findings
        self.total_findings = total_findings
        self.recommendations = recommendations or []
        
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the analysis results."""
        return {
            "analysis_type": self.analysis_type.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration,
            "status": self.status.value,
            "total_files_processed": self.total_files_processed,
            "files_with_findings": self.files_with_findings,
            "total_findings": self.total_findings,
            "total_recommendations": len(self.recommendations),
            "has_critical_findings": any(
                r.priority == Priority.CRITICAL for r in self.recommendations
            ),
            "error_message": self.error_message,
        }


class ConfigurableComponent(BaseComponent):
    """Base class for components that can be configured."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize the configurable component.
        
        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration parameters
        """
        super().__init__(**kwargs)
        self.config = config or {}
        self.config.update(kwargs)
        
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
        
    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
        
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update the configuration with new values.
        
        Args:
            new_config: New configuration values
        """
        self.config.update(new_config)
        
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self.config.copy()