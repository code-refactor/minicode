"""
API interfaces for the File System Analyzer unified library.

This module provides base API classes and common functionality
for building analysis APIs.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from ..core.types import AnalysisType, ScanStatus, FilePath
from ..core.base import BaseComponent, ConfigurableComponent
from ..core.results import BaseAnalysisResult
from ..utils.cache import CacheManager, MemoryCacheBackend
from ..export.multi_format import MultiFormatExporter
from ..interfaces.filesystem import EnhancedFileSystemInterface

logger = logging.getLogger(__name__)


class BaseAPI(ConfigurableComponent):
    """
    Base API class providing common functionality for analysis APIs.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        # Initialize core components
        self.filesystem = EnhancedFileSystemInterface()
        self.exporter = MultiFormatExporter(self.get_config_value('output_dir'))
        
        # Initialize caching if enabled
        if self.get_config_value('enable_caching', True):
            cache_backend = MemoryCacheBackend(
                max_size=self.get_config_value('cache_max_size', 1000)
            )
            self.cache = CacheManager(
                backend=cache_backend,
                default_ttl=self.get_config_value('cache_ttl', 3600)
            )
        else:
            self.cache = None
            
        # API state
        self._current_analysis: Optional[str] = None
        self._analysis_history: List[Dict[str, Any]] = []
        
    def validate_configuration(self) -> bool:
        """Validate API configuration."""
        required_configs = ['output_dir']
        
        for config_key in required_configs:
            if not self.get_config_value(config_key):
                logger.error(f"Missing required configuration: {config_key}")
                return False
                
        # Validate output directory
        output_dir = Path(self.get_config_value('output_dir'))
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Cannot create output directory {output_dir}: {e}")
            return False
            
        return True
        
    @abstractmethod
    def analyze(self, target: Union[str, Path, Dict[str, Any]], **kwargs) -> BaseAnalysisResult:
        """Perform analysis on the target."""
        pass
        
    def get_analysis_status(self, analysis_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the status of an analysis."""
        if analysis_id is None:
            analysis_id = self._current_analysis
            
        if analysis_id is None:
            return {"status": "no_analysis", "message": "No analysis running"}
            
        # In a real implementation, this would track actual analysis progress
        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
        
    def get_analysis_history(self) -> List[Dict[str, Any]]:
        """Get history of performed analyses."""
        return self._analysis_history.copy()
        
    def export_results(
        self,
        results: BaseAnalysisResult,
        formats: Optional[List[str]] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export analysis results in specified formats."""
        if formats is None:
            formats = ['json']
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{results.analysis_type.value}_{timestamp}"
            
        export_results = {}
        
        for format_name in formats:
            try:
                from ..core.types import ExportFormat
                format_enum = ExportFormat(format_name.lower())
                
                output_path = self.exporter.output_dir / f"{filename}.{format_name}"
                success = self.exporter.exporters[format_enum].export(
                    results, output_path
                )
                
                export_results[format_name] = {
                    "success": success,
                    "path": str(output_path) if success else None
                }
                
            except (ValueError, KeyError) as e:
                export_results[format_name] = {
                    "success": False,
                    "error": f"Unsupported format: {format_name}"
                }
            except Exception as e:
                export_results[format_name] = {
                    "success": False,
                    "error": str(e)
                }
                
        return export_results
        
    def clear_cache(self) -> Dict[str, Any]:
        """Clear analysis cache."""
        if self.cache:
            cleared_count = self.cache.clear()
            return {"cache_cleared": True, "items_cleared": cleared_count}
        return {"cache_cleared": False, "message": "Caching not enabled"}
        
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API statistics."""
        stats = {
            "api_name": self.__class__.__name__,
            "configuration_valid": self.validate_configuration(),
            "analyses_performed": len(self._analysis_history),
            "current_analysis": self._current_analysis,
            "filesystem_stats": self.filesystem.get_cache_stats(),
        }
        
        if self.cache:
            stats["cache_stats"] = self.cache.get_stats()
            
        return stats


class AnalysisAPI(BaseAPI):
    """
    Concrete API implementation for file system analysis.
    
    Provides a unified interface for different types of analysis
    including sensitive data detection and database optimization.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        # Initialize analyzers based on configuration
        self._available_analyzers = {
            AnalysisType.SENSITIVE_DATA_DETECTION: self._analyze_sensitive_data,
            AnalysisType.DATABASE_FILE_RECOGNITION: self._analyze_database_files,
            AnalysisType.FILE_SYSTEM_AUDIT: self._analyze_file_system,
        }
        
    def analyze(
        self,
        target: Union[str, Path, Dict[str, Any]],
        analysis_type: AnalysisType = AnalysisType.FILE_SYSTEM_AUDIT,
        **kwargs
    ) -> BaseAnalysisResult:
        """Perform the specified type of analysis."""
        # Generate analysis ID
        analysis_id = f"{analysis_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._current_analysis = analysis_id
        
        try:
            # Check cache first
            cache_key = f"{analysis_type.value}_{hash(str(target))}"
            if self.cache:
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    logger.info(f"Returning cached result for {analysis_id}")
                    return cached_result
                    
            # Perform analysis
            if analysis_type in self._available_analyzers:
                analyzer_func = self._available_analyzers[analysis_type]
                result = analyzer_func(target, **kwargs)
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")
                
            # Cache result
            if self.cache and result.is_successful():
                self.cache.set(cache_key, result)
                
            # Update history
            self._analysis_history.append({
                "analysis_id": analysis_id,
                "analysis_type": analysis_type.value,
                "timestamp": datetime.now().isoformat(),
                "target": str(target),
                "success": result.is_successful(),
                "findings": result.total_findings
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed: {e}")
            
            # Create error result
            error_result = BaseAnalysisResult(
                analysis_type=analysis_type,
                error_message=str(e),
                status=ScanStatus.FAILED
            )
            
            return error_result
            
        finally:
            self._current_analysis = None
            
    def _analyze_sensitive_data(self, target: Union[str, Path], **kwargs) -> BaseAnalysisResult:
        """Perform sensitive data analysis."""
        # This would integrate with the sensitive data scanner
        # For now, return a mock result
        from ..core.results import SensitiveDataAnalysisResult
        
        result = SensitiveDataAnalysisResult()
        result.total_files_processed = 100
        result.files_with_findings = 5
        result.total_findings = 12
        
        return result
        
    def _analyze_database_files(self, target: Union[str, Path], **kwargs) -> BaseAnalysisResult:
        """Perform database file analysis."""
        # This would integrate with the database file analyzer
        from ..core.results import DatabaseAnalysisResult
        
        result = DatabaseAnalysisResult()
        result.total_files_processed = 50
        result.files_with_findings = 25
        result.total_findings = 25
        
        return result
        
    def _analyze_file_system(self, target: Union[str, Path], **kwargs) -> BaseAnalysisResult:
        """Perform general file system analysis."""
        result = BaseAnalysisResult(
            analysis_type=AnalysisType.FILE_SYSTEM_AUDIT
        )
        
        # Get basic file system information
        if isinstance(target, (str, Path)):
            target_path = Path(target)
            if target_path.exists():
                if target_path.is_file():
                    result.total_files_processed = 1
                elif target_path.is_dir():
                    files = self.filesystem.list_files(target_path)
                    result.total_files_processed = len(files)
                    
        return result
        
    def get_supported_analysis_types(self) -> List[str]:
        """Get list of supported analysis types."""
        return [at.value for at in self._available_analyzers.keys()]