"""
Configuration and options classes for the File System Analyzer unified library.

This module provides configuration classes for scanners, analyzers, and other
components, allowing for flexible customization of behavior.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Set, Any, Pattern
from dataclasses import dataclass, field

from .types import (
    ScanStatus, Priority, SensitivityLevel, FileCategory, DatabaseEngine,
    ComplianceCategory, MatchType, ExportFormat, HashAlgorithm,
    FilePath, DEFAULT_MAX_FILE_SIZE, DEFAULT_CONTEXT_LINES, DEFAULT_MAX_DEPTH,
    DEFAULT_THREAD_POOL_SIZE, COMMON_IGNORE_PATTERNS, FILE_EXTENSIONS
)


@dataclass
class BaseOptions:
    """Base configuration options."""
    verbose: bool = False
    debug: bool = False
    log_level: str = "INFO"
    max_workers: int = DEFAULT_THREAD_POOL_SIZE
    timeout_seconds: Optional[int] = None
    
    def validate(self) -> bool:
        """Validate the configuration options."""
        if self.max_workers <= 0:
            return False
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            return False
        return True


@dataclass
class ScanOptions(BaseOptions):
    """Configuration options for file system scanning."""
    # File filtering
    recursive: bool = True
    max_depth: Optional[int] = DEFAULT_MAX_DEPTH
    follow_symlinks: bool = False
    max_file_size: int = DEFAULT_MAX_FILE_SIZE
    min_file_size: int = 0
    
    # Extension and pattern filtering
    include_extensions: Set[str] = field(default_factory=set)
    exclude_extensions: Set[str] = field(default_factory=set)
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=lambda: COMMON_IGNORE_PATTERNS.copy())
    
    # File type filtering
    include_categories: Set[FileCategory] = field(default_factory=set)
    exclude_categories: Set[FileCategory] = field(default_factory=set)
    
    # Time-based filtering
    modified_after: Optional[datetime] = None
    modified_before: Optional[datetime] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    # Processing options
    skip_hidden_files: bool = True
    skip_system_files: bool = True
    skip_empty_files: bool = False
    calculate_hashes: bool = False
    hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256
    
    # Performance options
    max_files_per_scan: Optional[int] = None
    batch_size: int = 100
    memory_limit_mb: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Compile patterns for better performance
        self._compiled_include_patterns = [re.compile(p) for p in self.include_patterns]
        self._compiled_exclude_patterns = [re.compile(p) for p in self.exclude_patterns]
        
    def should_include_file(self, file_path: FilePath) -> bool:
        """
        Determine if a file should be included based on the options.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file should be included, False otherwise
        """
        path = Path(file_path)
        
        # Check extension filters
        if self.include_extensions and path.suffix.lower() not in self.include_extensions:
            return False
        if self.exclude_extensions and path.suffix.lower() in self.exclude_extensions:
            return False
            
        # Check include patterns
        if self.include_patterns:
            if not any(pattern.search(str(path)) for pattern in self._compiled_include_patterns):
                return False
                
        # Check exclude patterns  
        if any(pattern.search(str(path)) for pattern in self._compiled_exclude_patterns):
            return False
            
        # Check hidden files
        if self.skip_hidden_files and path.name.startswith('.'):
            return False
            
        return True
        
    def get_category_for_extension(self, extension: str) -> Optional[FileCategory]:
        """Get the file category for a given extension."""
        ext = extension.lower()
        for category, extensions in FILE_EXTENSIONS.items():
            if ext in extensions:
                return category
        return None
        
    def validate(self) -> bool:
        """Validate the scan options."""
        if not super().validate():
            return False
            
        if self.max_depth is not None and self.max_depth < 0:
            return False
        if self.max_file_size <= 0:
            return False
        if self.min_file_size < 0:
            return False
        if self.min_file_size >= self.max_file_size:
            return False
        if self.batch_size <= 0:
            return False
            
        return True


@dataclass
class PatternMatchingOptions(BaseOptions):
    """Configuration options for pattern matching."""
    # Pattern behavior
    case_sensitive: bool = False
    multiline: bool = False
    dot_all: bool = False
    unicode: bool = True
    
    # Context options
    context_lines: int = DEFAULT_CONTEXT_LINES
    max_context_length: int = 1000
    include_line_numbers: bool = True
    
    # Performance options
    max_matches_per_file: Optional[int] = None
    match_timeout_seconds: float = 5.0
    
    # Validation options
    enable_validation: bool = True
    validation_timeout_seconds: float = 1.0
    
    # Sensitivity filtering
    min_sensitivity: SensitivityLevel = SensitivityLevel.LOW
    max_sensitivity: Optional[SensitivityLevel] = None
    
    # Category filtering
    include_categories: Set[ComplianceCategory] = field(default_factory=set)
    exclude_categories: Set[ComplianceCategory] = field(default_factory=set)
    
    def validate(self) -> bool:
        """Validate the pattern matching options."""
        if not super().validate():
            return False
            
        if self.context_lines < 0:
            return False
        if self.max_context_length <= 0:
            return False
        if self.match_timeout_seconds <= 0:
            return False
        if self.validation_timeout_seconds <= 0:
            return False
            
        return True


@dataclass
class SensitiveDataScanOptions(ScanOptions, PatternMatchingOptions):
    """Configuration options for sensitive data scanning."""
    # Compliance frameworks to check
    compliance_frameworks: Set[ComplianceCategory] = field(default_factory=set)
    
    # Risk assessment
    risk_threshold: Priority = Priority.MEDIUM
    auto_classify_risk: bool = True
    
    # Output options
    redact_sensitive_content: bool = True
    max_content_length: int = 100
    
    # Custom patterns
    custom_patterns_file: Optional[FilePath] = None
    enable_builtin_patterns: bool = True
    
    def validate(self) -> bool:
        """Validate the sensitive data scan options."""
        if not ScanOptions.validate(self) or not PatternMatchingOptions.validate(self):
            return False
            
        if self.max_content_length <= 0:
            return False
            
        if self.custom_patterns_file and not Path(self.custom_patterns_file).exists():
            return False
            
        return True


@dataclass
class DatabaseScanOptions(ScanOptions):
    """Configuration options for database file scanning."""
    # Database engine filtering
    target_engines: Set[DatabaseEngine] = field(default_factory=set)
    exclude_engines: Set[DatabaseEngine] = field(default_factory=set)
    
    # File category filtering  
    target_categories: Set[FileCategory] = field(default_factory=set)
    
    # Analysis options
    estimate_growth_rates: bool = False
    calculate_access_frequency: bool = False
    analyze_fragmentation: bool = False
    check_compression: bool = False
    
    # Monitoring options
    historical_data_days: int = 30
    sample_period_hours: int = 24
    
    def validate(self) -> bool:
        """Validate the database scan options."""
        if not super().validate():
            return False
            
        if self.historical_data_days <= 0:
            return False
        if self.sample_period_hours <= 0:
            return False
            
        return True


@dataclass
class ExportOptions(BaseOptions):
    """Configuration options for data export."""
    # Output settings
    output_dir: FilePath = Path.cwd()
    filename_template: str = "{analysis_type}_{timestamp}"
    
    # Format settings
    formats: Set[ExportFormat] = field(default_factory=lambda: {ExportFormat.JSON})
    pretty_print: bool = True
    include_metadata: bool = True
    include_summary: bool = True
    
    # Content filtering
    include_file_content: bool = False
    redact_sensitive_data: bool = True
    max_content_preview: int = 200
    
    # HTML report options
    html_template: Optional[FilePath] = None
    include_charts: bool = True
    embed_css: bool = True
    
    # CSV options
    csv_delimiter: str = ","
    csv_quote_char: str = '"'
    flatten_nested_data: bool = True
    
    def __post_init__(self):
        """Post-initialization processing."""
        self.output_dir = Path(self.output_dir)
        if self.html_template:
            self.html_template = Path(self.html_template)
            
    def get_output_path(self, analysis_type: str, format: ExportFormat) -> Path:
        """
        Generate output path for a specific analysis and format.
        
        Args:
            analysis_type: Type of analysis
            format: Export format
            
        Returns:
            Path for the output file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.filename_template.format(
            analysis_type=analysis_type,
            timestamp=timestamp
        )
        return self.output_dir / f"{filename}.{format.value}"
        
    def validate(self) -> bool:
        """Validate the export options."""
        if not super().validate():
            return False
            
        if not self.output_dir.exists():
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                return False
                
        if self.html_template and not self.html_template.exists():
            return False
            
        if self.max_content_preview < 0:
            return False
            
        return True


@dataclass  
class CacheOptions(BaseOptions):
    """Configuration options for caching."""
    # Cache behavior
    enable_cache: bool = True
    cache_dir: FilePath = Path.home() / ".file_system_analyzer" / "cache"
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_size_mb: int = 100
    
    # Cache keys
    cache_file_hashes: bool = True
    cache_analysis_results: bool = True
    cache_pattern_matches: bool = False
    
    # Cleanup options
    auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    max_cache_age_days: int = 7
    
    def __post_init__(self):
        """Post-initialization processing."""
        self.cache_dir = Path(self.cache_dir)
        
    def validate(self) -> bool:
        """Validate the cache options."""
        if not super().validate():
            return False
            
        if self.cache_ttl_seconds <= 0:
            return False
        if self.max_cache_size_mb <= 0:
            return False
        if self.cleanup_interval_hours <= 0:
            return False
        if self.max_cache_age_days <= 0:
            return False
            
        return True


@dataclass
class NotificationOptions(BaseOptions):
    """Configuration options for notifications."""
    # Notification triggers
    enable_notifications: bool = False
    notify_on_completion: bool = False
    notify_on_critical_findings: bool = True
    notify_on_errors: bool = True
    
    # Severity thresholds
    min_priority_for_notification: Priority = Priority.HIGH
    max_notifications_per_run: int = 10
    
    # Email settings
    email_enabled: bool = False
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    email_recipients: List[str] = field(default_factory=list)
    email_subject_template: str = "File System Analyzer - {analysis_type} Results"
    
    # Webhook settings  
    webhook_enabled: bool = False
    webhook_urls: List[str] = field(default_factory=list)
    webhook_timeout_seconds: int = 30
    webhook_retry_attempts: int = 3
    
    def validate(self) -> bool:
        """Validate the notification options."""
        if not super().validate():
            return False
            
        if self.max_notifications_per_run <= 0:
            return False
        if self.smtp_port <= 0 or self.smtp_port > 65535:
            return False
        if self.webhook_timeout_seconds <= 0:
            return False
        if self.webhook_retry_attempts < 0:
            return False
            
        if self.email_enabled and not self.email_recipients:
            return False
        if self.webhook_enabled and not self.webhook_urls:
            return False
            
        return True


@dataclass
class ComprehensiveOptions:
    """Comprehensive configuration combining all option types."""
    scan: ScanOptions = field(default_factory=ScanOptions)
    sensitive_data: SensitiveDataScanOptions = field(default_factory=SensitiveDataScanOptions)
    database: DatabaseScanOptions = field(default_factory=DatabaseScanOptions)
    export: ExportOptions = field(default_factory=ExportOptions)
    cache: CacheOptions = field(default_factory=CacheOptions)
    notifications: NotificationOptions = field(default_factory=NotificationOptions)
    
    def validate(self) -> bool:
        """Validate all configuration options."""
        return all([
            self.scan.validate(),
            self.sensitive_data.validate(), 
            self.database.validate(),
            self.export.validate(),
            self.cache.validate(),
            self.notifications.validate(),
        ])
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert options to dictionary format."""
        from dataclasses import asdict
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComprehensiveOptions':
        """Create options from dictionary format."""
        return cls(
            scan=ScanOptions(**data.get('scan', {})),
            sensitive_data=SensitiveDataScanOptions(**data.get('sensitive_data', {})),
            database=DatabaseScanOptions(**data.get('database', {})),
            export=ExportOptions(**data.get('export', {})),
            cache=CacheOptions(**data.get('cache', {})),
            notifications=NotificationOptions(**data.get('notifications', {})),
        )


# Preset configurations for common use cases
class PresetConfigurations:
    """Predefined configuration presets."""
    
    @staticmethod
    def quick_scan() -> ComprehensiveOptions:
        """Configuration for a quick, basic scan."""
        options = ComprehensiveOptions()
        options.scan.max_depth = 3
        options.scan.max_file_size = 10 * 1024 * 1024  # 10MB
        options.scan.skip_hidden_files = True
        options.sensitive_data.context_lines = 1
        options.sensitive_data.max_matches_per_file = 10
        return options
        
    @staticmethod
    def thorough_scan() -> ComprehensiveOptions:
        """Configuration for a comprehensive, thorough scan."""
        options = ComprehensiveOptions()
        options.scan.recursive = True
        options.scan.max_depth = None  # No depth limit
        options.scan.calculate_hashes = True
        options.sensitive_data.context_lines = 5
        options.sensitive_data.enable_validation = True
        options.database.estimate_growth_rates = True
        options.database.analyze_fragmentation = True
        return options
        
    @staticmethod
    def compliance_focused() -> ComprehensiveOptions:
        """Configuration focused on compliance checking."""
        options = ComprehensiveOptions()
        options.sensitive_data.compliance_frameworks = {
            ComplianceCategory.PII,
            ComplianceCategory.PHI, 
            ComplianceCategory.PCI,
            ComplianceCategory.GDPR
        }
        options.sensitive_data.min_sensitivity = SensitivityLevel.MEDIUM
        options.sensitive_data.redact_sensitive_content = True
        options.export.formats = {ExportFormat.JSON, ExportFormat.HTML}
        options.notifications.notify_on_critical_findings = True
        return options
        
    @staticmethod
    def database_optimization() -> ComprehensiveOptions:
        """Configuration for database optimization analysis."""
        options = ComprehensiveOptions()
        options.database.target_engines = {
            DatabaseEngine.MYSQL,
            DatabaseEngine.POSTGRESQL,
            DatabaseEngine.MONGODB
        }
        options.database.estimate_growth_rates = True
        options.database.calculate_access_frequency = True  
        options.database.analyze_fragmentation = True
        options.database.check_compression = True
        options.export.formats = {ExportFormat.JSON, ExportFormat.CSV, ExportFormat.HTML}
        return options