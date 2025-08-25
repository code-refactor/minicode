"""Data type definitions for the Database Storage Optimization Analyzer."""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from pydantic import BaseModel, Field


class DatabaseEngine(str, Enum):
    """Supported database engines."""

    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    ORACLE = "oracle"
    MSSQL = "mssql"
    UNKNOWN = "unknown"


class FileCategory(str, Enum):
    """Database file categories."""

    DATA = "data"
    INDEX = "index"
    LOG = "log"
    TEMP = "temp"
    CONFIG = "config"
    BACKUP = "backup"
    UNKNOWN = "unknown"


class ScanStatus(str, Enum):
    """Status of a file system scan."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class OptimizationPriority(str, Enum):
    """Priority levels for optimization recommendations."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class DatabaseFile(BaseModel):
    """Represents a database file in the file system."""

    path: str
    engine: DatabaseEngine
    category: FileCategory
    size_bytes: int
    last_modified: datetime
    creation_time: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    growth_rate_bytes_per_day: Optional[float] = None
    access_frequency: Optional[float] = None
    is_compressed: bool = False
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "path": "/var/lib/mysql/mydatabase/users.ibd",
                "engine": "mysql",
                "category": "data",
                "size_bytes": 1073741824,
                "last_modified": "2023-04-15T14:30:00",
                "creation_time": "2023-01-10T08:15:00",
                "last_accessed": "2023-04-15T12:45:00",
                "growth_rate_bytes_per_day": 1048576,
                "access_frequency": 142.5,
                "is_compressed": False,
                "metadata": {"tablespace_id": 12, "table_name": "users"},
            }
        }


class OptimizationRecommendation(BaseModel):
    """Optimization recommendation for database storage."""

    id: str
    title: str
    description: str
    priority: OptimizationPriority
    estimated_space_savings_bytes: Optional[int] = None
    estimated_performance_impact_percent: Optional[float] = None
    implementation_complexity: str
    affected_files: List[str] = Field(default_factory=list)
    related_recommendations: List[str] = Field(default_factory=list)

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "IDX-001",
                "title": "Remove redundant indexes on users table",
                "description": "The table has multiple indexes with overlapping columns",
                "priority": "high",
                "estimated_space_savings_bytes": 536870912,
                "estimated_performance_impact_percent": 5.2,
                "implementation_complexity": "medium",
                "affected_files": [
                    "/var/lib/mysql/mydatabase/users.ibd",
                    "/var/lib/mysql/mydatabase/users_index.ibd",
                ],
                "related_recommendations": ["IDX-002", "TBL-004"],
            }
        }


class AnalysisResult(BaseModel):
    """Base class for analysis results."""

    timestamp: datetime = Field(default_factory=datetime.now)
    analysis_duration_seconds: float
    scan_status: ScanStatus
    error_message: Optional[str] = None
    recommendations: List[OptimizationRecommendation] = Field(default_factory=list)