"""API interfaces for the Database Storage Optimization Analyzer."""

from typing import Dict, List, Optional, Union, Any, Tuple
import logging
from datetime import datetime
import json
import uuid
from pathlib import Path

# Import from common library
from common.interfaces.api import BaseAPI
from common.core.types import AnalysisType, ScanStatus
from common.core.results import DatabaseAnalysisResult
from common.export.multi_format import MultiFormatExporter
from common.utils.cache import CacheManager

from ..utils.types import (
    DatabaseEngine, 
    FileCategory, 
    ScanStatus, 
    AnalysisResult,
    OptimizationRecommendation,
)
from ..db_file_recognition.detector import DatabaseFileDetector
from ..transaction_log_analysis.log_analyzer import TransactionLogAnalyzer
from ..index_efficiency.index_analyzer import IndexEfficiencyAnalyzer
from ..tablespace_fragmentation.fragmentation_analyzer import TablespaceFragmentationAnalyzer
from ..backup_compression.compression_analyzer import BackupCompressionAnalyzer
from .export import ExportInterface, NotificationInterface
from .filesystem import FileSystemInterface


logger = logging.getLogger(__name__)


class StorageOptimizerAPI(BaseAPI):
    """
    Main API for the Database Storage Optimization Analyzer.
    
    This class provides a unified API for all analysis capabilities, along
    with result caching, export options, and notification features.
    """

    def __init__(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        cache_results: bool = True,
        cache_ttl_seconds: int = 3600,
        read_only: bool = True,
    ):
        """
        Initialize the Storage Optimizer API.

        Args:
            output_dir: Directory for output files
            cache_results: Whether to cache analysis results
            cache_ttl_seconds: Time-to-live for cached results
            read_only: Enforce read-only operations
        """
        # Initialize base API with configuration
        config = {
            'output_dir': str(output_dir) if output_dir else str(Path.cwd()),
            'enable_caching': cache_results,
            'cache_ttl': cache_ttl_seconds,
            'read_only': read_only
        }
        super().__init__(config=config)
        
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.cache_results = cache_results
        self.cache_ttl_seconds = cache_ttl_seconds
        self.read_only = read_only
        
        # Initialize interfaces
        self.fs_interface = FileSystemInterface(read_only=read_only)
        self.export_interface = ExportInterface(output_dir=output_dir)
        self.notification_interface = NotificationInterface()
        
        # Initialize analyzers
        self.file_detector = DatabaseFileDetector()
        self.log_analyzer = TransactionLogAnalyzer()
        self.index_analyzer = IndexEfficiencyAnalyzer()
        self.fragmentation_analyzer = TablespaceFragmentationAnalyzer()
        self.backup_analyzer = BackupCompressionAnalyzer()
        
        # Initialize results cache
        self.results_cache = {}
        self.cache_timestamps = {}
    
    def analyze(self, target: Union[str, Path, Dict[str, Any]], **kwargs) -> DatabaseAnalysisResult:
        """Perform database analysis on the target."""
        if isinstance(target, (str, Path)):
            # Assume it's a directory path
            return self.analyze_database_files(target, **kwargs)
        elif isinstance(target, dict):
            # Handle different types of data based on the dictionary structure
            if 'log_files' in target:
                return self.analyze_transaction_logs(target['log_files'], **kwargs)
            elif 'indexes' in target:
                return self.analyze_index_efficiency(target['indexes'], **kwargs)
            elif 'tablespaces' in target:
                return self.analyze_tablespace_fragmentation(target['tablespaces'], **kwargs)
            elif 'backups' in target:
                return self.analyze_backup_compression(target['backups'], **kwargs)
        
        raise ValueError(f"Unsupported target type: {type(target)}")

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if available and not expired."""
        if not self.cache_results or cache_key not in self.results_cache:
            return None
            
        timestamp = self.cache_timestamps.get(cache_key)
        if not timestamp:
            return None
            
        # Check if cache has expired
        elapsed = (datetime.now() - timestamp).total_seconds()
        if elapsed > self.cache_ttl_seconds:
            # Cache expired
            del self.results_cache[cache_key]
            del self.cache_timestamps[cache_key]
            return None
            
        logger.info(f"Returning cached result for {cache_key}")
        return self.results_cache[cache_key]

    def _store_in_cache(self, cache_key: str, result: Any) -> None:
        """Store result in cache."""
        if not self.cache_results:
            return
            
        self.results_cache[cache_key] = result
        self.cache_timestamps[cache_key] = datetime.now()
        logger.debug(f"Stored result in cache for {cache_key}")

    def analyze_database_files(
        self,
        root_path: Union[str, Path],
        recursive: bool = True,
        max_depth: Optional[int] = None,
        follow_symlinks: bool = False,
        max_files: Optional[int] = None,
        export_format: Optional[str] = None,
        export_filename: Optional[str] = None,
        notify_on_critical: bool = False,
        notification_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze database files in a directory.

        Args:
            root_path: Starting directory
            recursive: Whether to search recursively
            max_depth: Maximum directory depth to search
            follow_symlinks: Whether to follow symbolic links
            max_files: Maximum number of files to analyze
            export_format: Export format (json, csv, html)
            export_filename: Export filename
            notify_on_critical: Whether to send notifications for critical findings
            notification_email: Email address for notifications

        Returns:
            Analysis result dictionary
        """
        cache_key = f"db_files_{root_path}_{recursive}_{max_depth}_{follow_symlinks}_{max_files}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
            
        # Perform analysis
        analysis_result = self.file_detector.scan_directory(
            root_path=root_path,
            recursive=recursive,
            follow_symlinks=follow_symlinks,
            max_depth=max_depth,
            max_files=max_files,
        )
        
        # Export if requested
        if export_format and export_filename:
            self._export_result(analysis_result, export_format, export_filename)
            
        # Send notifications if requested
        if notify_on_critical and notification_email and analysis_result.recommendations:
            self.notification_interface.send_email_notification(
                recommendations=analysis_result.recommendations,
                recipient=notification_email,
                subject="Database File Analysis - Critical Findings",
            )
            
        # Cache result
        result_dict = json.loads(analysis_result.json())
        self._store_in_cache(cache_key, result_dict)
        
        return result_dict

    def analyze_transaction_logs(
        self,
        log_files: List[Dict[str, Any]],
        historical_sizes: Optional[Dict[str, List[Tuple[datetime, int]]]] = None,
        operation_frequencies: Optional[Dict[str, Dict[str, List[int]]]] = None,
        export_format: Optional[str] = None,
        export_filename: Optional[str] = None,
        notify_on_critical: bool = False,
        notification_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze transaction log files.

        Args:
            log_files: List of log file information dictionaries
            historical_sizes: Dictionary mapping file paths to historical size data
            operation_frequencies: Dictionary mapping engines to operation frequencies
            export_format: Export format (json, csv, html)
            export_filename: Export filename
            notify_on_critical: Whether to send notifications for critical findings
            notification_email: Email address for notifications

        Returns:
            Analysis result dictionary
        """
        from ..utils.types import DatabaseFile
        
        # Convert log files to DatabaseFile objects
        db_log_files = []
        for log_file in log_files:
            try:
                db_log_files.append(DatabaseFile(**log_file))
            except Exception as e:
                logger.error(f"Error converting log file data: {e}")
                
        # Generate cache key based on input data
        cache_key = f"tx_logs_{hash(str(log_files))}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
            
        # Perform analysis
        analysis_result = self.log_analyzer.analyze_logs(
            log_files=db_log_files,
            historical_sizes=historical_sizes,
            operation_frequencies=operation_frequencies,
        )
        
        # Export if requested
        if export_format and export_filename:
            self._export_result(analysis_result, export_format, export_filename)
            
        # Send notifications if requested
        if notify_on_critical and notification_email and analysis_result.recommendations:
            self.notification_interface.send_email_notification(
                recommendations=analysis_result.recommendations,
                recipient=notification_email,
                subject="Transaction Log Analysis - Critical Findings",
            )
            
        # Cache result
        result_dict = json.loads(analysis_result.json())
        self._store_in_cache(cache_key, result_dict)
        
        return result_dict

    def analyze_index_efficiency(
        self,
        indexes: List[Dict[str, Any]],
        tables_sizes: Optional[Dict[str, int]] = None,
        export_format: Optional[str] = None,
        export_filename: Optional[str] = None,
        notify_on_critical: bool = False,
        notification_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze index efficiency.

        Args:
            indexes: List of index information dictionaries
            tables_sizes: Dictionary mapping table names to sizes in bytes
            export_format: Export format (json, csv, html)
            export_filename: Export filename
            notify_on_critical: Whether to send notifications for critical findings
            notification_email: Email address for notifications

        Returns:
            Analysis result dictionary
        """
        from ..index_efficiency.index_analyzer import IndexInfo
        
        # Convert indexes to IndexInfo objects
        index_objects = []
        for index_data in indexes:
            try:
                index_objects.append(IndexInfo(**index_data))
            except Exception as e:
                logger.error(f"Error converting index data: {e}")
                
        # Generate cache key based on input data
        cache_key = f"indexes_{hash(str(indexes))}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
            
        # Perform analysis
        analysis_result = self.index_analyzer.analyze_indexes(
            indexes=index_objects,
            tables_sizes=tables_sizes,
        )
        
        # Export if requested
        if export_format and export_filename:
            self._export_result(analysis_result, export_format, export_filename)
            
        # Send notifications if requested
        if notify_on_critical and notification_email and analysis_result.recommendations:
            self.notification_interface.send_email_notification(
                recommendations=analysis_result.recommendations,
                recipient=notification_email,
                subject="Index Efficiency Analysis - Critical Findings",
            )
            
        # Cache result
        result_dict = json.loads(analysis_result.json())
        self._store_in_cache(cache_key, result_dict)
        
        return result_dict

    def analyze_tablespace_fragmentation(
        self,
        tablespaces: List[Dict[str, Any]],
        fragmentation_data: Optional[Dict[str, Dict[str, Any]]] = None,
        export_format: Optional[str] = None,
        export_filename: Optional[str] = None,
        notify_on_critical: bool = False,
        notification_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze tablespace fragmentation.

        Args:
            tablespaces: List of tablespace information dictionaries
            fragmentation_data: Dictionary with raw fragmentation data by tablespace name
            export_format: Export format (json, csv, html)
            export_filename: Export filename
            notify_on_critical: Whether to send notifications for critical findings
            notification_email: Email address for notifications

        Returns:
            Analysis result dictionary
        """
        from ..tablespace_fragmentation.fragmentation_analyzer import TablespaceInfo
        
        # Convert tablespaces to TablespaceInfo objects
        tablespace_objects = []
        for ts_data in tablespaces:
            try:
                tablespace_objects.append(TablespaceInfo(**ts_data))
            except Exception as e:
                logger.error(f"Error converting tablespace data: {e}")
                
        # Generate cache key based on input data
        cache_key = f"tablespaces_{hash(str(tablespaces))}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
            
        # Perform analysis
        analysis_result = self.fragmentation_analyzer.analyze_tablespace_fragmentation(
            tablespaces=tablespace_objects,
            fragmentation_data=fragmentation_data,
        )
        
        # Export if requested
        if export_format and export_filename:
            self._export_result(analysis_result, export_format, export_filename)
            
        # Send notifications if requested
        if notify_on_critical and notification_email and analysis_result.recommendations:
            self.notification_interface.send_email_notification(
                recommendations=analysis_result.recommendations,
                recipient=notification_email,
                subject="Tablespace Fragmentation Analysis - Critical Findings",
            )
            
        # Cache result
        result_dict = json.loads(analysis_result.json())
        self._store_in_cache(cache_key, result_dict)
        
        return result_dict

    def analyze_backup_compression(
        self,
        backups: List[Dict[str, Any]],
        export_format: Optional[str] = None,
        export_filename: Optional[str] = None,
        notify_on_critical: bool = False,
        notification_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze backup compression efficiency.

        Args:
            backups: List of backup information dictionaries
            export_format: Export format (json, csv, html)
            export_filename: Export filename
            notify_on_critical: Whether to send notifications for critical findings
            notification_email: Email address for notifications

        Returns:
            Analysis result dictionary
        """
        from ..backup_compression.compression_analyzer import BackupInfo
        
        # Convert backups to BackupInfo objects
        backup_objects = []
        for backup_data in backups:
            try:
                backup_objects.append(BackupInfo(**backup_data))
            except Exception as e:
                logger.error(f"Error converting backup data: {e}")
                
        # Generate cache key based on input data
        cache_key = f"backups_{hash(str(backups))}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
            
        # Perform analysis
        analysis_result = self.backup_analyzer.analyze_backup_compression(
            backups=backup_objects,
        )
        
        # Export if requested
        if export_format and export_filename:
            self._export_result(analysis_result, export_format, export_filename)
            
        # Send notifications if requested
        if notify_on_critical and notification_email and analysis_result.recommendations:
            self.notification_interface.send_email_notification(
                recommendations=analysis_result.recommendations,
                recipient=notification_email,
                subject="Backup Compression Analysis - Critical Findings",
            )
            
        # Cache result
        result_dict = json.loads(analysis_result.json())
        self._store_in_cache(cache_key, result_dict)
        
        return result_dict

    def comprehensive_analysis(
        self,
        root_path: Union[str, Path],
        recursive: bool = True,
        export_format: Optional[str] = None,
        export_filename: Optional[str] = None,
        notify_on_critical: bool = False,
        notification_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of all database storage aspects.

        Args:
            root_path: Starting directory
            recursive: Whether to search recursively
            export_format: Export format (json, csv, html)
            export_filename: Export filename
            notify_on_critical: Whether to send notifications for critical findings
            notification_email: Email address for notifications

        Returns:
            Comprehensive analysis result dictionary
        """
        # Generate cache key
        cache_key = f"comprehensive_{root_path}_{recursive}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
            
        # Start with database file analysis
        logger.info(f"Starting comprehensive analysis of {root_path}")
        
        file_analysis = self.analyze_database_files(
            root_path=root_path,
            recursive=recursive,
        )
        
        # Extract database files by category
        db_files = file_analysis.get("detected_files", [])
        
        # Group files by category
        log_files = [f for f in db_files if f.get("category") == "log"]
        backup_files = [f for f in db_files if f.get("category") == "backup"]
        
        # Perform log analysis if we found log files
        log_analysis = {}
        if log_files:
            logger.info(f"Analyzing {len(log_files)} log files")
            log_analysis = self.analyze_transaction_logs(log_files=log_files)
        
        # Perform backup analysis if we found backup files
        backup_analysis = {}
        if backup_files:
            logger.info(f"Analyzing {len(backup_files)} backup files")
            backup_analysis = self.analyze_backup_compression(backups=backup_files)
        
        # Combine all analysis results
        comprehensive_result = {
            "timestamp": datetime.now().isoformat(),
            "root_path": str(root_path),
            "file_analysis": file_analysis,
            "log_analysis": log_analysis,
            "backup_analysis": backup_analysis,
            
            # Combine recommendations from all analyses
            "all_recommendations": (
                file_analysis.get("recommendations", []) +
                log_analysis.get("recommendations", []) +
                backup_analysis.get("recommendations", [])
            ),
        }
        
        # Export if requested
        if export_format and export_filename:
            if export_format == "json":
                self.export_interface.export_json(
                    data=comprehensive_result,
                    filename=export_filename,
                )
            elif export_format == "html":
                self.export_interface.export_html_report(
                    data=comprehensive_result,
                    filename=export_filename,
                    title="Comprehensive Database Storage Analysis",
                )
            
        # Send notifications if requested
        if notify_on_critical and notification_email:
            self.notification_interface.send_email_notification(
                recommendations=comprehensive_result["all_recommendations"],
                recipient=notification_email,
                subject="Comprehensive Storage Analysis - Critical Findings",
            )
            
        # Cache result
        self._store_in_cache(cache_key, comprehensive_result)
        
        return comprehensive_result

    def _export_result(
        self, 
        result: Any, 
        export_format: str, 
        export_filename: str
    ) -> Optional[str]:
        """
        Export analysis result in the specified format.

        Args:
            result: Analysis result
            export_format: Export format (json, csv, html)
            export_filename: Export filename

        Returns:
            Path to exported file, or None on error
        """
        try:
            if export_format.lower() == "json":
                return self.export_interface.export_json(
                    data=result,
                    filename=export_filename,
                )
            elif export_format.lower() == "csv":
                # Convert result to list of dictionaries for CSV export
                if isinstance(result, dict):
                    # Flatten nested dictionaries
                    flat_result = []
                    for key, value in result.items():
                        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                            flat_result.extend(value)
                        else:
                            flat_result.append({key: value})
                            
                    return self.export_interface.export_csv(
                        data=flat_result,
                        filename=export_filename,
                    )
                else:
                    logger.error(f"Cannot export result of type {type(result)} to CSV")
                    return None
                    
            elif export_format.lower() == "html":
                return self.export_interface.export_html_report(
                    data=result,
                    filename=export_filename,
                    title="Database Storage Analysis Report",
                )
            else:
                logger.error(f"Unsupported export format: {export_format}")
                return None
                
        except Exception as e:
            logger.error(f"Error exporting result: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the results cache."""
        self.results_cache.clear()
        self.cache_timestamps.clear()
        logger.info("Cleared results cache")

    def get_cached_analysis_keys(self) -> List[str]:
        """Get list of cached analysis keys."""
        return list(self.results_cache.keys())