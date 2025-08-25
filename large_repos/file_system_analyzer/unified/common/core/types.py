"""
Common type definitions for the File System Analyzer unified library.

This module provides common enums, base types, and data models shared across
both the Security Auditor and Database Administrator personas.
"""

import re
from enum import Enum, auto
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any, Pattern
from dataclasses import dataclass


class ScanStatus(str, Enum):
    """Status of a file system scan operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Priority levels for findings and recommendations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class SensitivityLevel(str, Enum):
    """Sensitivity level of detected data."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FileCategory(str, Enum):
    """File categories for both database and security contexts."""
    # Database categories
    DATA = "data"
    INDEX = "index"
    LOG = "log"
    TEMP = "temp"
    CONFIG = "config"
    BACKUP = "backup"
    
    # Security/General categories
    EXECUTABLE = "executable"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    MEDIA = "media"
    SOURCE_CODE = "source_code"
    CERTIFICATE = "certificate"
    KEY = "key"
    
    # Common
    UNKNOWN = "unknown"
    OTHER = "other"


class DatabaseEngine(str, Enum):
    """Supported database engines."""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    ORACLE = "oracle"
    MSSQL = "mssql"
    SQLITE = "sqlite"
    REDIS = "redis"
    UNKNOWN = "unknown"


class ComplianceCategory(str, Enum):
    """Regulatory compliance categories for detected data."""
    PII = "pii"          # Personally Identifiable Information
    PHI = "phi"          # Protected Health Information  
    PCI = "pci"          # Payment Card Industry Data
    FINANCIAL = "financial"
    PROPRIETARY = "proprietary"
    CREDENTIALS = "credentials"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    SOX = "sox"          # Sarbanes-Oxley
    OTHER = "other"


class MatchType(str, Enum):
    """Types of pattern matching."""
    REGEX = "regex"
    GLOB = "glob"
    EXACT = "exact"
    FUZZY = "fuzzy"
    HASH = "hash"


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    XML = "xml"
    YAML = "yaml"
    PDF = "pdf"


@dataclass
class FileInfo:
    """Basic file information structure."""
    path: Union[str, Path]
    name: str
    size_bytes: int
    last_modified: datetime
    creation_time: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    file_type: Optional[str] = None
    mime_type: Optional[str] = None
    permissions: Optional[str] = None
    owner: Optional[str] = None
    is_directory: bool = False
    is_symlink: bool = False
    
    def __post_init__(self):
        """Convert path to Path object if it's a string."""
        if isinstance(self.path, str):
            self.path = Path(self.path)


@dataclass
class PatternDefinition:
    """Definition of a pattern for matching."""
    name: str
    description: str
    pattern: str
    match_type: MatchType = MatchType.REGEX
    case_sensitive: bool = False
    category: Optional[ComplianceCategory] = None
    sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    priority: Priority = Priority.MEDIUM
    validation_func: Optional[str] = None
    context_rules: List[str] = None
    false_positive_examples: List[str] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.context_rules is None:
            self.context_rules = []
        if self.false_positive_examples is None:
            self.false_positive_examples = []


@dataclass
class Match:
    """A match found by pattern matching."""
    pattern_name: str
    matched_content: str
    file_path: Union[str, Path]
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    byte_offset: Optional[int] = None
    context: Optional[str] = None
    category: Optional[ComplianceCategory] = None
    sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    priority: Priority = Priority.MEDIUM
    validation_status: bool = True
    confidence_score: float = 1.0
    
    def __post_init__(self):
        """Convert path to Path object if it's a string."""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)


@dataclass
class Recommendation:
    """A recommendation from analysis."""
    id: str
    title: str
    description: str
    priority: Priority
    category: Optional[ComplianceCategory] = None
    affected_files: List[Union[str, Path]] = None
    related_recommendations: List[str] = None
    estimated_impact: Optional[str] = None
    implementation_complexity: Optional[str] = None
    estimated_space_savings_bytes: Optional[int] = None
    estimated_performance_impact_percent: Optional[float] = None
    remediation_steps: List[str] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.affected_files is None:
            self.affected_files = []
        if self.related_recommendations is None:
            self.related_recommendations = []
        if self.remediation_steps is None:
            self.remediation_steps = []
        
        # Convert string paths to Path objects
        self.affected_files = [
            Path(f) if isinstance(f, str) else f 
            for f in self.affected_files
        ]


class HashAlgorithm(str, Enum):
    """Supported hash algorithms."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class CompressionType(str, Enum):
    """Supported compression types."""
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
    XZ = "xz"
    ZIP = "zip"
    TAR = "tar"
    RAR = "rar"
    SEVENZ = "7z"


class AnalysisType(str, Enum):
    """Types of analysis that can be performed."""
    SENSITIVE_DATA_DETECTION = "sensitive_data_detection"
    DATABASE_FILE_RECOGNITION = "database_file_recognition"
    TRANSACTION_LOG_ANALYSIS = "transaction_log_analysis"
    INDEX_EFFICIENCY_ANALYSIS = "index_efficiency_analysis"
    TABLESPACE_FRAGMENTATION = "tablespace_fragmentation"
    BACKUP_COMPRESSION = "backup_compression"
    FILE_SYSTEM_AUDIT = "file_system_audit"
    SECURITY_ASSESSMENT = "security_assessment"
    COMPLIANCE_CHECK = "compliance_check"


# Type aliases for common uses
FilePath = Union[str, Path]
FileSize = int
TimestampType = Union[datetime, float, int]
PatternType = Union[str, Pattern]
MetadataDict = Dict[str, Any]


# Constants
DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
DEFAULT_CONTEXT_LINES = 3
DEFAULT_MAX_DEPTH = 10
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour
DEFAULT_THREAD_POOL_SIZE = 10

# Common file extensions by category
FILE_EXTENSIONS = {
    FileCategory.EXECUTABLE: {".exe", ".bin", ".sh", ".bat", ".cmd", ".app", ".msi"},
    FileCategory.DOCUMENT: {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages"},
    FileCategory.ARCHIVE: {".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z"},
    FileCategory.MEDIA: {".jpg", ".jpeg", ".png", ".gif", ".mp3", ".mp4", ".avi", ".mov"},
    FileCategory.SOURCE_CODE: {".py", ".java", ".c", ".cpp", ".js", ".html", ".css", ".sql"},
    FileCategory.CONFIG: {".conf", ".cfg", ".ini", ".yaml", ".yml", ".json", ".xml"},
    FileCategory.KEY: {".key", ".pem", ".p12", ".pfx", ".jks"},
    FileCategory.CERTIFICATE: {".crt", ".cer", ".der", ".p7b", ".p7c"},
}

# Common ignore patterns
COMMON_IGNORE_PATTERNS = [
    r"^\.git/",
    r"^\.svn/", 
    r"^\.hg/",
    r"^node_modules/",
    r"^__pycache__/",
    r"^\.pytest_cache/",
    r"^\.mypy_cache/",
    r"^build/",
    r"^dist/",
    r"^target/",
    r"^\.DS_Store$",
    r"^Thumbs\.db$",
]