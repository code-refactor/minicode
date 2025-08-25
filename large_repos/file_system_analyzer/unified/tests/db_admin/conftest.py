"""Pytest configuration for the database storage optimizer analyzer tests."""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from datetime import datetime, timedelta

from file_system_analyzer_db_admin.utils.types import (
    DatabaseEngine,
    FileCategory,
    DatabaseFile,
)
from file_system_analyzer_db_admin.tablespace_fragmentation.fragmentation_analyzer import TablespaceInfo
from file_system_analyzer_db_admin.backup_compression.compression_analyzer import (
    BackupStrategy,
    CompressionAlgorithm,
)
from file_system_analyzer_db_admin.index_efficiency.index_analyzer import IndexInfo
from file_system_analyzer_db_admin.db_file_recognition.detector import DatabaseFileDetector
from file_system_analyzer_db_admin.interfaces.api import StorageOptimizerAPI


@pytest.fixture
def mock_data_dir():
    """Path to the mock data directory."""
    return Path(__file__).parent / "mock_data"


@pytest.fixture
def temp_output_dir():
    """Temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def file_detector():
    """Database file detector instance."""
    return DatabaseFileDetector()


@pytest.fixture
def storage_optimizer_api(temp_output_dir):
    """Storage optimizer API instance."""
    return StorageOptimizerAPI(output_dir=temp_output_dir)


@pytest.fixture
def mock_database_files():
    """List of mock database files for testing."""
    now = datetime.now()
    
    return [
        DatabaseFile(
            path="/var/lib/mysql/mydatabase/users.ibd",
            engine=DatabaseEngine.MYSQL,
            category=FileCategory.DATA,
            size_bytes=1073741824,  # 1GB
            last_modified=now - timedelta(days=1),
            creation_time=now - timedelta(days=30),
            last_accessed=now - timedelta(hours=2),
            growth_rate_bytes_per_day=1048576,  # 1MB
            access_frequency=142.5,
            is_compressed=False,
            metadata={"tablespace_id": 12, "table_name": "users"},
        ),
        DatabaseFile(
            path="/var/lib/mysql/mydatabase/products.ibd",
            engine=DatabaseEngine.MYSQL,
            category=FileCategory.DATA,
            size_bytes=536870912,  # 512MB
            last_modified=now - timedelta(days=2),
            creation_time=now - timedelta(days=45),
            last_accessed=now - timedelta(hours=1),
            growth_rate_bytes_per_day=524288,  # 512KB
            access_frequency=98.2,
            is_compressed=False,
            metadata={"tablespace_id": 13, "table_name": "products"},
        ),
        DatabaseFile(
            path="/var/lib/mysql/mysql-bin.000001",
            engine=DatabaseEngine.MYSQL,
            category=FileCategory.LOG,
            size_bytes=104857600,  # 100MB
            last_modified=now - timedelta(days=3),
            creation_time=now - timedelta(days=5),
            last_accessed=now - timedelta(hours=3),
            growth_rate_bytes_per_day=20971520,  # 20MB
            access_frequency=50.0,
            is_compressed=False,
            metadata={"log_type": "binary"},
        ),
        DatabaseFile(
            path="/var/lib/postgresql/data/base/16384/16385",
            engine=DatabaseEngine.POSTGRESQL,
            category=FileCategory.DATA,
            size_bytes=268435456,  # 256MB
            last_modified=now - timedelta(days=1),
            creation_time=now - timedelta(days=20),
            last_accessed=now - timedelta(hours=4),
            growth_rate_bytes_per_day=2097152,  # 2MB
            access_frequency=120.3,
            is_compressed=False,
            metadata={"relname": "users", "relfilenode": 16385},
        ),
        DatabaseFile(
            path="/var/lib/postgresql/data/pg_wal/000000010000000A00000001",
            engine=DatabaseEngine.POSTGRESQL,
            category=FileCategory.LOG,
            size_bytes=16777216,  # 16MB
            last_modified=now - timedelta(hours=6),
            creation_time=now - timedelta(days=2),
            last_accessed=now - timedelta(hours=6),
            growth_rate_bytes_per_day=8388608,  # 8MB
            access_frequency=40.5,
            is_compressed=False,
            metadata={"log_type": "wal"},
        ),
        DatabaseFile(
            path="/var/lib/mongodb/collection-0-1234567890123456789012.wt",
            engine=DatabaseEngine.MONGODB,
            category=FileCategory.DATA,
            size_bytes=134217728,  # 128MB
            last_modified=now - timedelta(days=1),
            creation_time=now - timedelta(days=15),
            last_accessed=now - timedelta(hours=1),
            growth_rate_bytes_per_day=1048576,  # 1MB
            access_frequency=110.7,
            is_compressed=False,
            metadata={"collection": "users", "database": "myapp"},
        ),
        DatabaseFile(
            path="/var/lib/mongodb/backup.tar.gz",
            engine=DatabaseEngine.MONGODB,
            category=FileCategory.BACKUP,
            size_bytes=536870912,  # 512MB
            last_modified=now - timedelta(days=1),
            creation_time=now - timedelta(days=1),
            last_accessed=now - timedelta(days=1),
            is_compressed=True,
            metadata={"backup_type": "full"},
        ),
    ]


@pytest.fixture
def mock_tablespaces():
    """List of mock tablespaces for testing."""
    return [
        TablespaceInfo(
            name="USERS_TS",
            engine=DatabaseEngine.ORACLE,
            file_paths=["/opt/oracle/oradata/users01.dbf"],
            total_size_bytes=1073741824,  # 1GB
            used_size_bytes=805306368,    # 768MB
            free_size_bytes=268435456,    # 256MB
            max_size_bytes=2147483648,    # 2GB
            autoextend=True,
            tables=["USERS", "PROFILES", "USER_ROLES"],
            creation_time=datetime.now() - timedelta(days=180),
            last_modified=datetime.now() - timedelta(days=1),
            metadata={"status": "ONLINE", "blocksize": 8192},
        ),
        TablespaceInfo(
            name="PRODUCTS_TS",
            engine=DatabaseEngine.ORACLE,
            file_paths=["/opt/oracle/oradata/products01.dbf"],
            total_size_bytes=536870912,   # 512MB
            used_size_bytes=402653184,    # 384MB
            free_size_bytes=134217728,    # 128MB
            max_size_bytes=1073741824,    # 1GB
            autoextend=True,
            tables=["PRODUCTS", "CATEGORIES", "SUPPLIERS"],
            creation_time=datetime.now() - timedelta(days=150),
            last_modified=datetime.now() - timedelta(days=2),
            metadata={"status": "ONLINE", "blocksize": 8192},
        ),
        TablespaceInfo(
            name="ORDERS_TS",
            engine=DatabaseEngine.ORACLE,
            file_paths=["/opt/oracle/oradata/orders01.dbf"],
            total_size_bytes=2147483648,  # 2GB
            used_size_bytes=1879048192,   # 1.75GB
            free_size_bytes=268435456,    # 256MB
            max_size_bytes=3221225472,    # 3GB
            autoextend=True,
            tables=["ORDERS", "ORDER_ITEMS", "SHIPMENTS"],
            creation_time=datetime.now() - timedelta(days=120),
            last_modified=datetime.now() - timedelta(hours=12),
            metadata={"status": "ONLINE", "blocksize": 8192},
        ),
    ]


@pytest.fixture
def mock_indexes():
    """List of mock indexes for testing."""
    return [
        IndexInfo(
            name="users_pk",
            table_name="users",
            columns=["id"],
            size_bytes=16777216,  # 16MB
            is_unique=True,
            is_primary=True,
            is_clustered=True,
            usage_count=1000,
            avg_query_time_ms=0.5,
            fragmentation_percent=5.0,
            database_name="myapp",
            schema_name="public",
            engine=DatabaseEngine.POSTGRESQL,
        ),
        IndexInfo(
            name="users_email_idx",
            table_name="users",
            columns=["email"],
            size_bytes=8388608,  # 8MB
            is_unique=True,
            usage_count=800,
            avg_query_time_ms=0.8,
            fragmentation_percent=8.0,
            database_name="myapp",
            schema_name="public",
            engine=DatabaseEngine.POSTGRESQL,
        ),
        IndexInfo(
            name="users_name_idx",
            table_name="users",
            columns=["first_name", "last_name"],
            size_bytes=12582912,  # 12MB
            is_unique=False,
            usage_count=200,
            avg_query_time_ms=1.2,
            fragmentation_percent=12.0,
            database_name="myapp",
            schema_name="public",
            engine=DatabaseEngine.POSTGRESQL,
        ),
        IndexInfo(
            name="users_unused_idx",
            table_name="users",
            columns=["registration_date"],
            size_bytes=4194304,  # 4MB
            is_unique=False,
            usage_count=5,
            avg_query_time_ms=2.0,
            fragmentation_percent=20.0,
            database_name="myapp",
            schema_name="public",
            engine=DatabaseEngine.POSTGRESQL,
        ),
        IndexInfo(
            name="products_pk",
            table_name="products",
            columns=["id"],
            size_bytes=8388608,  # 8MB
            is_unique=True,
            is_primary=True,
            is_clustered=True,
            usage_count=900,
            avg_query_time_ms=0.6,
            fragmentation_percent=6.0,
            database_name="myapp",
            schema_name="public",
            engine=DatabaseEngine.POSTGRESQL,
        ),
        IndexInfo(
            name="products_name_idx",
            table_name="products",
            columns=["name"],
            size_bytes=4194304,  # 4MB
            is_unique=False,
            usage_count=700,
            avg_query_time_ms=0.9,
            fragmentation_percent=9.0,
            database_name="myapp",
            schema_name="public",
            engine=DatabaseEngine.POSTGRESQL,
        ),
        IndexInfo(
            name="products_redundant_idx",
            table_name="products",
            columns=["name"],  # Duplicate of products_name_idx
            size_bytes=4194304,  # 4MB
            is_unique=False,
            usage_count=0,
            avg_query_time_ms=None,
            fragmentation_percent=15.0,
            database_name="myapp",
            schema_name="public",
            engine=DatabaseEngine.POSTGRESQL,
        ),
    ]


@pytest.fixture
def mock_backup_files():
    """List of mock backup files for testing."""
    now = datetime.now()
    
    return [
        {
            "path": "/var/backups/mysql/full_backup_20230101.sql",
            "engine": DatabaseEngine.MYSQL,
            "size_bytes": 1073741824,  # 1GB
            "original_size_bytes": 2147483648,  # 2GB
            "compression_algorithm": CompressionAlgorithm.GZIP,
            "compression_level": 6,
            "backup_date": now - timedelta(days=30),
            "backup_strategy": BackupStrategy.FULL,
            "is_compressed": True,
            "databases": ["mydatabase"],
            "backup_duration_seconds": 3600,  # 1 hour
            "restore_duration_seconds": 7200,  # 2 hours
        },
        {
            "path": "/var/backups/mysql/incremental_backup_20230102.xbstream",
            "engine": DatabaseEngine.MYSQL,
            "size_bytes": 134217728,  # 128MB
            "original_size_bytes": 268435456,  # 256MB
            "compression_algorithm": CompressionAlgorithm.GZIP,
            "compression_level": 6,
            "backup_date": now - timedelta(days=29),
            "backup_strategy": BackupStrategy.INCREMENTAL,
            "is_compressed": True,
            "databases": ["mydatabase"],
            "backup_duration_seconds": 900,  # 15 minutes
            "restore_duration_seconds": 1800,  # 30 minutes
        },
        {
            "path": "/var/backups/postgresql/full_backup_20230101.dump",
            "engine": DatabaseEngine.POSTGRESQL,
            "size_bytes": 805306368,  # 768MB
            "original_size_bytes": 1610612736,  # 1.5GB
            "compression_algorithm": CompressionAlgorithm.NONE,
            "backup_date": now - timedelta(days=30),
            "backup_strategy": BackupStrategy.FULL,
            "is_compressed": False,
            "databases": ["myapp"],
            "backup_duration_seconds": 2700,  # 45 minutes
            "restore_duration_seconds": 5400,  # 90 minutes
        },
        {
            "path": "/var/backups/mongodb/full_backup_20230101.archive",
            "engine": DatabaseEngine.MONGODB,
            "size_bytes": 536870912,  # 512MB
            "original_size_bytes": 1073741824,  # 1GB
            "compression_algorithm": CompressionAlgorithm.SNAPPY,
            "backup_date": now - timedelta(days=30),
            "backup_strategy": BackupStrategy.FULL,
            "is_compressed": True,
            "databases": ["myapp"],
            "backup_duration_seconds": 1800,  # 30 minutes
            "restore_duration_seconds": 3600,  # 60 minutes
        },
        {
            "path": "/var/backups/mysql/full_backup_20230201.sql.bz2",
            "engine": DatabaseEngine.MYSQL,
            "size_bytes": 671088640,  # 640MB
            "original_size_bytes": 2147483648,  # 2GB
            "compression_algorithm": CompressionAlgorithm.BZIP2,
            "compression_level": 9,
            "backup_date": now - timedelta(days=15),
            "backup_strategy": BackupStrategy.FULL,
            "is_compressed": True,
            "databases": ["mydatabase"],
            "backup_duration_seconds": 4500,  # 75 minutes
            "restore_duration_seconds": 9000,  # 150 minutes
        },
    ]


@pytest.fixture
def fragmentation_data():
    """Mock fragmentation data for tablespaces."""
    return {
        "USERS_TS": {
            "fragmentation_percent": 25.0,
            "fragmentation_type": "internal",
            "free_chunks_sizes": [4194304, 8388608, 4194304, 16777216, 4194304],  # Scattered chunks
            "free_chunks_positions": [(100, 4194304), (200, 8388608), (300, 4194304), 
                                      (500, 16777216), (800, 4194304)],
            "data_chunks": [(0, 50331648), (150, 100663296), (250, 67108864), 
                            (350, 83886080), (600, 134217728), (900, 50331648)],
            "growth_bytes_per_day": 5242880,  # 5MB/day
        },
        "PRODUCTS_TS": {
            "fragmentation_percent": 15.0,
            "fragmentation_type": "mixed",
            "free_chunks_sizes": [33554432, 67108864, 33554432],  # Fewer, larger chunks
            "free_chunks_positions": [(150, 33554432), (400, 67108864), (700, 33554432)],
            "data_chunks": [(0, 67108864), (200, 100663296), (500, 83886080), (750, 151165824)],
            "growth_bytes_per_day": 2097152,  # 2MB/day
        },
        "ORDERS_TS": {
            "fragmentation_percent": 45.0,
            "fragmentation_type": "external",
            "free_chunks_sizes": [1048576, 2097152, 4194304, 8388608, 2097152, 4194304, 
                                   1048576, 2097152, 1048576, 8388608, 4194304, 2097152],  # Many small fragments
            "free_chunks_positions": [(50, 1048576), (150, 2097152), (200, 4194304), 
                                      (300, 8388608), (400, 2097152), (500, 4194304),
                                      (600, 1048576), (700, 2097152), (800, 1048576),
                                      (900, 8388608), (1000, 4194304), (1100, 2097152)],
            "data_chunks": [(0, 33554432), (100, 83886080), (250, 167772160), 
                           (350, 100663296), (450, 83886080), (550, 167772160),
                           (650, 83886080), (750, 50331648), (850, 167772160),
                           (950, 33554432), (1050, 67108864), (1150, 134217728)],
            "growth_bytes_per_day": 10485760,  # 10MB/day
        },
    }