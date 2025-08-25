"""
SyncDB: In-Memory Database with Mobile Synchronization

A specialized in-memory database designed for mobile application backends that efficiently
manages data synchronization between server and client applications with intermittent
connectivity. The system optimizes for minimal data transfer, handles conflict resolution,
and supports evolving application requirements through schema migration.
"""

__version__ = "0.1.0"

# Database schema and engine
from syncdb.db.schema import DatabaseSchema, TableSchema, Column
from syncdb.db.database import Database, Table, Transaction

# Client and server APIs
from syncdb.client import SyncClient, SyncServer

# Conflict resolution
from syncdb.sync.conflict_resolution import (
    ConflictResolver, LastWriteWinsResolver, ServerWinsResolver,
    ClientWinsResolver, MergeFieldsResolver, CustomMergeResolver,
    ConflictManager, ConflictAuditLog
)

# Compression
from syncdb.compression.type_compressor import (
    CompressionLevel, PayloadCompressor
)

# Power management
from syncdb.power.power_manager import (
    PowerMode, PowerProfile, OperationPriority,
    PowerManager, BatteryAwareClient
)

# Schema management
from syncdb.schema.schema_manager import (
    SchemaVersionManager, SchemaMigrator, SchemaSynchronizer,
    SchemaMigration, MigrationPlan
)

# Network simulation
from syncdb.sync.sync_protocol import NetworkSimulator

# Version tracking
from syncdb.sync.change_tracker import ChangeTracker, VersionVector