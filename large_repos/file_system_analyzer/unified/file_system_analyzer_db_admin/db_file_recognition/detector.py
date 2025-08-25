"""Database file detection and categorization."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Iterator, Union
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from collections import Counter

from common.core.base import BaseAnalyzer, BaseScanner
from common.core.types import DatabaseEngine, FileCategory, ScanStatus, AnalysisType
from common.core.results import DatabaseAnalysisResult, DatabaseFileInfo
from common.utils.file_utils import get_file_stats, find_files
from common.patterns.engine import PatternEngine

from ..utils.types import DatabaseFile, AnalysisResult
from .file_patterns import COMPILED_DB_PATTERNS, COMPILED_DIR_PATTERNS


logger = logging.getLogger(__name__)


class DatabaseFileAnalysisResult(AnalysisResult):
    """Results from database file analysis."""

    total_files_scanned: int
    total_size_bytes: int
    files_by_engine: Dict[DatabaseEngine, int]
    size_by_engine: Dict[DatabaseEngine, int]
    files_by_category: Dict[FileCategory, int]
    size_by_category: Dict[FileCategory, int]
    detected_files: List[DatabaseFile]


class DatabaseFileDetector(BaseAnalyzer[str, DatabaseAnalysisResult]):
    """
    Detects and categorizes database files across multiple database engines.
    
    This class identifies files associated with various database engines
    (MySQL, PostgreSQL, MongoDB, Oracle, SQL Server) and categorizes them
    by their function (data, index, log, etc.).
    """

    def __init__(
        self,
        ignore_extensions: Optional[Set[str]] = None,
        content_sampling_size: int = 8192,
        max_workers: int = 10,
    ):
        """
        Initialize the database file detector.

        Args:
            ignore_extensions: Set of file extensions to ignore
            content_sampling_size: Number of bytes to read for content-based detection
            max_workers: Maximum number of worker threads for parallel processing
        """
        super().__init__(analysis_type=AnalysisType.DATABASE_FILE_RECOGNITION)
        self.ignore_extensions = ignore_extensions or {
            '.exe', '.dll', '.so', '.pyc', '.pyo', '.class', '.jar',
            '.zip', '.tar', '.gz', '.7z', '.rar', '.bz2',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.doc', '.docx',
            '.xls', '.xlsx', '.ppt', '.pptx',
        }
        self.content_sampling_size = content_sampling_size
        self.max_workers = max_workers
        
        # File utilities are now imported as functions
    
    def analyze(self, data: str) -> DatabaseAnalysisResult:
        """Analyze a directory path for database files."""
        return self.scan_directory(data)

    def detect_engine_from_path(self, file_path: Path) -> Optional[DatabaseEngine]:
        """
        Detect database engine based on file path pattern.

        Args:
            file_path: Path to the file

        Returns:
            Detected database engine, or None if not detected
        """
        path_str = str(file_path)
        parent_path_str = str(file_path.parent)
        
        # Check directory patterns for engine hints
        for engine, patterns in COMPILED_DIR_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(parent_path_str):
                    return engine
        
        # Check file extension patterns
        for engine, categories in COMPILED_DB_PATTERNS.items():
            for category, patterns in categories.items():
                for pattern in patterns:
                    if pattern.search(path_str):
                        return engine
                        
        return None

    def detect_category_from_path(
        self, file_path: Path, engine: Optional[DatabaseEngine] = None
    ) -> FileCategory:
        """
        Detect file category based on file path pattern.

        Args:
            file_path: Path to the file
            engine: Database engine to limit the search (optional)

        Returns:
            Detected file category, or FileCategory.UNKNOWN if not detected
        """
        path_str = str(file_path)

        # Special case for PostgreSQL WAL files for test compatibility
        if "pg_wal" in path_str or "pg_xlog" in path_str:
            return FileCategory.LOG

        # Special case for MongoDB index files
        if "index-" in path_str and engine == DatabaseEngine.MONGODB:
            return FileCategory.INDEX

        # If engine is specified, only check patterns for that engine
        engines_to_check = [engine] if engine and engine != DatabaseEngine.UNKNOWN else list(COMPILED_DB_PATTERNS.keys())

        for check_engine in engines_to_check:
            for category, patterns in COMPILED_DB_PATTERNS[check_engine].items():
                for pattern in patterns:
                    if pattern.search(path_str):
                        return category

        return FileCategory.UNKNOWN

    def sample_file_content(self, file_path: Path) -> Optional[bytes]:
        """
        Read a sample of file content for content-based detection.

        Args:
            file_path: Path to the file

        Returns:
            Sample of file content, or None if file can't be read
        """
        try:
            with open(file_path, 'rb') as f:
                return f.read(self.content_sampling_size)
        except (PermissionError, OSError, IOError) as e:
            logger.debug(f"Cannot read content from {file_path}: {e}")
            return None

    def detect_engine_from_content(self, content: bytes) -> Optional[DatabaseEngine]:
        """
        Detect database engine based on file content.

        Args:
            content: File content sample

        Returns:
            Detected database engine, or None if not detected
        """
        # MySQL signature detection
        if b"MySQL" in content or b"InnoDB" in content:
            return DatabaseEngine.MYSQL
            
        # PostgreSQL signature detection
        if b"PostgreSQL" in content or b"PGDMP" in content:
            return DatabaseEngine.POSTGRESQL
            
        # MongoDB signature detection
        if b"MongoDB" in content or b"WiredTiger" in content:
            return DatabaseEngine.MONGODB
            
        # Oracle signature detection
        if b"Oracle" in content or b"ORACLE" in content:
            return DatabaseEngine.ORACLE
            
        # SQL Server signature detection
        if b"Microsoft SQL Server" in content or b"MSSQL" in content:
            return DatabaseEngine.MSSQL
            
        return None

    def analyze_file(self, file_path: Path) -> Optional[DatabaseFile]:
        """
        Analyze a single file to determine if it's a database file.

        Args:
            file_path: Path to the file

        Returns:
            DatabaseFile object if it's a database file, None otherwise
        """
        try:
            # Skip files with ignored extensions
            if file_path.suffix.lower() in self.ignore_extensions:
                return None
                
            # Get file stats
            stats = get_file_stats(file_path)
            
            # Skip directories and non-existent files
            if not stats.get("is_file", False) or not stats.get("exists", False):
                return None
                
            # Try to detect database engine from path
            engine = self.detect_engine_from_path(file_path)
            
            # If we couldn't detect from path and file is not too large, sample content
            if (not engine or engine == DatabaseEngine.UNKNOWN) and stats.get("size_bytes", 0) < 10_000_000:
                content = self.sample_file_content(file_path)
                if content:
                    content_engine = self.detect_engine_from_content(content)
                    if content_engine:
                        engine = content_engine
            
            # If still no engine detected, skip this file
            if not engine:
                return None
                
            # Detect file category
            category = self.detect_category_from_path(file_path, engine)
            
            # Create database file object
            return DatabaseFile(
                path=str(file_path),
                engine=engine,
                category=category,
                size_bytes=stats.get("size_bytes", 0),
                last_modified=stats.get("last_modified", datetime.now()),
                creation_time=stats.get("creation_time"),
                last_accessed=stats.get("last_accessed"),
                is_compressed=file_path.suffix.lower() in {'.gz', '.zip', '.bz2', '.xz', '.7z', '.rar'},
            )
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None

    def scan_directory(
        self,
        root_path: Union[str, Path],
        recursive: bool = True,
        follow_symlinks: bool = False,
        max_depth: Optional[int] = None,
        max_files: Optional[int] = None,
    ) -> DatabaseFileAnalysisResult:
        """
        Scan a directory for database files.

        Args:
            root_path: Starting directory for search
            recursive: Whether to search recursively
            follow_symlinks: Whether to follow symbolic links
            max_depth: Maximum directory depth to search
            max_files: Maximum number of files to process

        Returns:
            Analysis result containing detected database files and statistics
        """
        start_time = datetime.now()
        root = Path(root_path)
        
        if not root.exists() or not root.is_dir():
            return DatabaseFileAnalysisResult(
                analysis_duration_seconds=0,
                scan_status=ScanStatus.FAILED,
                error_message=f"Root path {root_path} does not exist or is not a directory",
                total_files_scanned=0,
                total_size_bytes=0,
                files_by_engine={},
                size_by_engine={},
                files_by_category={},
                size_by_category={},
                detected_files=[],
            )
        
        try:
            # Find all files matching criteria
            all_files = list(find_files(
                root_path=root,
                recursive=recursive,
                follow_symlinks=follow_symlinks,
                max_depth=max_depth
            ))
            
            total_files = len(all_files)
            logger.info(f"Found {total_files} files to analyze in {root_path}")
            
            # Process files in parallel
            detected_files = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {executor.submit(self.analyze_file, f): f for f in all_files}
                for future in as_completed(future_to_file):
                    result = future.result()
                    if result:
                        detected_files.append(result)
            
            # Compute statistics
            total_size = sum(f.size_bytes for f in detected_files)
            
            files_by_engine = Counter()
            size_by_engine = Counter()
            files_by_category = Counter()
            size_by_category = Counter()
            
            for file in detected_files:
                files_by_engine[file.engine] += 1
                size_by_engine[file.engine] += file.size_bytes
                files_by_category[file.category] += 1
                size_by_category[file.category] += file.size_bytes
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return DatabaseFileAnalysisResult(
                analysis_duration_seconds=duration,
                scan_status=ScanStatus.COMPLETED,
                total_files_scanned=total_files,
                total_size_bytes=total_size,
                files_by_engine=dict(files_by_engine),
                size_by_engine=dict(size_by_engine),
                files_by_category=dict(files_by_category),
                size_by_category=dict(size_by_category),
                detected_files=detected_files,
            )
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"Error scanning directory {root_path}: {e}")
            return DatabaseFileAnalysisResult(
                analysis_duration_seconds=duration,
                scan_status=ScanStatus.FAILED,
                error_message=str(e),
                total_files_scanned=0,
                total_size_bytes=0,
                files_by_engine={},
                size_by_engine={},
                files_by_category={},
                size_by_category={},
                detected_files=[],
            )
    
    def validate_configuration(self) -> bool:
        """
        Validate the DatabaseFileDetector configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        # Check if ignore_extensions is valid
        if self.ignore_extensions and not isinstance(self.ignore_extensions, set):
            return False
            
        # Check content sampling size
        if self.content_sampling_size <= 0:
            return False
            
        # Check max workers
        if self.max_workers <= 0:
            return False
            
        return True