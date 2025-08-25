"""Database file pattern definitions for various database engines."""

from typing import Dict, List, Pattern, Set, Tuple
import re
from enum import Enum

from ..utils.types import DatabaseEngine, FileCategory


# MySQL file patterns
MYSQL_PATTERNS = {
    FileCategory.DATA: [
        r".*\.ibd$",  # InnoDB tablespace files
        r".*\.MYD$",  # MyISAM data files
        r".*\.sdi$",  # Serialized Dictionary Information files
    ],
    FileCategory.INDEX: [
        r".*\.MYI$",  # MyISAM index files
    ],
    FileCategory.LOG: [
        r".*bin\.([0-9]+)$",  # Binary logs
        r".*\.err$",  # Error log
        r".*\.log$",  # General log
        r"ib_logfile[0-9]+$",  # InnoDB log files
        r".*relay-log.*\.([0-9]+)$",  # Relay logs
        r".*slow\.log$",  # Slow query log
    ],
    FileCategory.TEMP: [
        r".*\.TMP$",  # Temporary files
        r".*\.tmp$",
        r"ib_temporary.*",  # InnoDB temporary tablespaces
    ],
    FileCategory.CONFIG: [
        r".*\.cnf$",  # Configuration files
        r".*\.ini$",
        r"my\.cnf$",
    ],
    FileCategory.BACKUP: [
        r".*\.bak$",
        r".*\.backup$",
        r".*\.xbstream$",  # XtraBackup files
        r".*\.gz$",
        r".*\.sql$",  # SQL dump files
    ],
}

# PostgreSQL file patterns
POSTGRESQL_PATTERNS = {
    FileCategory.DATA: [
        r"[0-9]+$",  # Data files are named with OIDs
        r"[0-9]+\.[0-9]+$",  # Segment files
        r"[0-9]+_fsm$",  # Free space maps
        r"[0-9]+_vm$",  # Visibility maps
    ],
    FileCategory.INDEX: [
        r"[0-9]+_[0-9]+$",  # Index files
    ],
    FileCategory.LOG: [
        r"postgresql-.*\.log$",
        r"pg_log/.*\.log$",
        r"pg_wal/.*$",  # Write-ahead logs
        r"pg_xlog/.*$",  # Pre-10 WAL directory
    ],
    FileCategory.TEMP: [
        r"pgsql_tmp/.*",  # Temporary files
        r"pg_tmp/.*",
    ],
    FileCategory.CONFIG: [
        r"postgresql\.conf$",
        r"pg_hba\.conf$",
        r"pg_ident\.conf$",
        r"recovery\.conf$",
    ],
    FileCategory.BACKUP: [
        r"base\.([0-9]+)\.backup$",
        r".*\.bak$",
        r".*\.sql$",
        r".*\.dump$",
    ],
}

# MongoDB file patterns
MONGODB_PATTERNS = {
    FileCategory.DATA: [
        r".*\.wt$",  # WiredTiger data files
        r"collection-[0-9]+-[0-9A-F]{24}\.wt$",  # Collection data files
    ],
    FileCategory.INDEX: [
        r"index-[0-9]+-[0-9A-F]{24}\.wt$",  # Index files
    ],
    FileCategory.LOG: [
        r"mongodb\.log$",
        r"mongod\.log.*",
        r"WiredTiger\.wt\.([0-9]+)$",  # WiredTiger log files
        r"journal/.*",  # Journal files
    ],
    FileCategory.TEMP: [
        r"_tmp_.*",
        r".*\.tmp$",
    ],
    FileCategory.CONFIG: [
        r"mongod\.conf$",
    ],
    FileCategory.BACKUP: [
        r".*\.bak$",
        r".*\.backup$",
        r".*\.archive$",
        r".*\.gz$",
    ],
}

# Oracle file patterns
ORACLE_PATTERNS = {
    FileCategory.DATA: [
        r".*\.dbf$",  # Database files
    ],
    FileCategory.INDEX: [
        r".*idx\.dbf$",  # Index files (convention)
    ],
    FileCategory.LOG: [
        r".*\.log$",
        r".*\.ctl$",  # Control files
        r".*\.arc$",  # Archived logs
        r"redo[0-9]+\.log$",  # Redo logs
    ],
    FileCategory.TEMP: [
        r".*temp\.dbf$",  # Temporary tablespace
        r".*\.tmp$",
    ],
    FileCategory.CONFIG: [
        r"init.*\.ora$",
        r".*\.ora$",
        r"listener\.ora$",
        r"tnsnames\.ora$",
        r"sqlnet\.ora$",
    ],
    FileCategory.BACKUP: [
        r".*\.bak$",
        r".*\.dmp$",  # Data Pump export files
        r".*\.exp$",  # Export files
        r".*\.rman$",  # RMAN backup files
    ],
}

# Microsoft SQL Server file patterns
MSSQL_PATTERNS = {
    FileCategory.DATA: [
        r".*\.mdf$",  # Primary data files
        r".*\.ndf$",  # Secondary data files
    ],
    FileCategory.INDEX: [
        r".*_idx\.ndf$",  # Index files (convention)
    ],
    FileCategory.LOG: [
        r".*\.ldf$",  # Log files
        r".*\.trn$",  # Transaction log backups
        r"ERRORLOG.*",  # Error logs
    ],
    FileCategory.TEMP: [
        r"tempdb.*\.mdf$",  # TempDB data files
        r"tempdb.*\.ndf$",  # TempDB secondary data files
        r"tempdb.*\.ldf$",  # TempDB log files
        r".*\.tmp$",
    ],
    FileCategory.CONFIG: [
        r".*\.ini$",
    ],
    FileCategory.BACKUP: [
        r".*\.bak$",  # Full database backups
        r".*\.dif$",  # Differential backups
        r".*\.trn$",  # Transaction log backups
    ],
}


# Directory patterns that might indicate a particular database engine
DIR_ENGINE_PATTERNS = {
    DatabaseEngine.MYSQL: [
        r"mysql$",
        r"mysql/data$",
        r"var/lib/mysql$",
    ],
    DatabaseEngine.POSTGRESQL: [
        r"postgresql$",
        r"postgres$",
        r"pgsql$",
        r"var/lib/postgresql$",
    ],
    DatabaseEngine.MONGODB: [
        r"mongodb$",
        r"mongo$",
        r"var/lib/mongodb$",
    ],
    DatabaseEngine.ORACLE: [
        r"oracle$",
        r"oradata$",
        r"app/oracle$",
    ],
    DatabaseEngine.MSSQL: [
        r"MSSQL$",
        r"Microsoft SQL Server$",
        r"MSSQL\d+\.MSSQLSERVER$",
    ],
}

# Combine all patterns into a single dictionary for easy access
ALL_DB_PATTERNS = {
    DatabaseEngine.MYSQL: MYSQL_PATTERNS,
    DatabaseEngine.POSTGRESQL: POSTGRESQL_PATTERNS,
    DatabaseEngine.MONGODB: MONGODB_PATTERNS,
    DatabaseEngine.ORACLE: ORACLE_PATTERNS,
    DatabaseEngine.MSSQL: MSSQL_PATTERNS,
}


# Precompile all regular expressions for better performance
def compile_patterns() -> Dict[DatabaseEngine, Dict[FileCategory, List[Pattern]]]:
    """
    Compile all regex patterns for better performance.

    Returns:
        Nested dictionary of compiled patterns
    """
    compiled_patterns = {}
    
    for engine, categories in ALL_DB_PATTERNS.items():
        compiled_patterns[engine] = {}
        for category, patterns in categories.items():
            compiled_patterns[engine][category] = [re.compile(pattern) for pattern in patterns]
            
    return compiled_patterns


COMPILED_DB_PATTERNS = compile_patterns()

# Compile directory patterns
COMPILED_DIR_PATTERNS = {
    engine: [re.compile(pattern) for pattern in patterns] 
    for engine, patterns in DIR_ENGINE_PATTERNS.items()
}