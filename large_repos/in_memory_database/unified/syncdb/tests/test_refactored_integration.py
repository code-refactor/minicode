"""
Test the refactored SyncDB implementation to ensure compatibility with common library.
"""
import sys
import traceback
from typing import Dict, List, Any, Optional

def test_basic_database_operations():
    """Test basic database operations using refactored components."""
    print("Testing basic database operations...")
    
    try:
        # Import refactored components
        from ..db.schema import DatabaseSchema, TableSchema, Column
        from ..db.database import Database
        
        # Create a schema
        user_columns = [
            Column("id", int, primary_key=True),
            Column("username", str),
            Column("email", str),
            Column("description", str, nullable=True)
        ]
        user_table = TableSchema("users", user_columns)
        tables = {"users": user_table}
        schema = DatabaseSchema(tables, version=1)
        
        # Create a database
        db = Database(schema)
        
        # Test insert
        user_record = {
            "id": 1,
            "username": "test_user",
            "email": "test@example.com",
            "description": "Test user"
        }
        
        inserted = db.insert("users", user_record)
        print(f"✓ Insert successful: {inserted['username']}")
        
        # Test get
        retrieved = db.get("users", [1])
        if retrieved and retrieved["username"] == "test_user":
            print("✓ Get operation successful")
        else:
            print("✗ Get operation failed")
            return False
        
        # Test update
        updated_record = retrieved.copy()
        updated_record["username"] = "updated_user"
        updated = db.update("users", updated_record)
        print(f"✓ Update successful: {updated['username']}")
        
        # Test query
        results = db.query("users", {"username": "updated_user"})
        if len(results) == 1 and results[0]["username"] == "updated_user":
            print("✓ Query operation successful")
        else:
            print("✗ Query operation failed")
            return False
        
        # Test transaction
        with db.begin_transaction() as txn:
            txn.insert("users", {
                "id": 2,
                "username": "txn_user",
                "email": "txn@example.com"
            })
            print("✓ Transaction insert successful")
        
        # Verify transaction worked
        txn_user = db.get("users", [2])
        if txn_user and txn_user["username"] == "txn_user":
            print("✓ Transaction commit successful")
        else:
            print("✗ Transaction commit failed")
            return False
        
        print("✓ All basic database operations passed!")
        return True
        
    except Exception as e:
        print(f"✗ Basic database operations failed: {e}")
        traceback.print_exc()
        return False


def test_change_tracking():
    """Test change tracking with common library integration."""
    print("\nTesting change tracking...")
    
    try:
        from ..sync.change_tracker import ChangeTracker, ChangeRecord, VersionVector
        
        # Create change tracker
        tracker = ChangeTracker()
        
        # Record a change
        change = tracker.record_change(
            table_name="users",
            primary_key=(1,),
            operation="insert",
            old_data=None,
            new_data={"id": 1, "username": "test"},
            client_id="test_client"
        )
        
        print(f"✓ Change recorded with ID: {change.id}")
        
        # Test serialization
        changes = [change]
        serialized = tracker.serialize_changes(changes)
        deserialized = tracker.deserialize_changes(serialized)
        
        if len(deserialized) == 1 and deserialized[0].client_id == "test_client":
            print("✓ Serialization/deserialization successful")
        else:
            print("✗ Serialization/deserialization failed")
            return False
        
        # Test version vector
        vector = VersionVector("test_client")
        vector.increment()
        
        vector_dict = vector.to_dict()
        vector_restored = VersionVector.from_dict(vector_dict)
        
        if vector_restored.client_id == "test_client" and vector_restored.vector["test_client"] == 1:
            print("✓ Version vector operations successful")
        else:
            print("✗ Version vector operations failed")
            return False
        
        print("✓ All change tracking operations passed!")
        return True
        
    except Exception as e:
        print(f"✗ Change tracking failed: {e}")
        traceback.print_exc()
        return False


def test_conflict_resolution():
    """Test conflict resolution with common library integration."""
    print("\nTesting conflict resolution...")
    
    try:
        from ..sync.conflict_resolution import (
            ConflictManager, 
            MergeFieldsResolver, 
            ClientWinsResolver,
            ConflictAuditLog
        )
        from ..sync.change_tracker import ChangeRecord
        import time
        
        # Create conflict manager with audit log
        audit_log = ConflictAuditLog()
        conflict_manager = ConflictManager(audit_log)
        
        # Set up resolver for users table
        field_priorities = {"users": ["username", "email"]}
        resolver = MergeFieldsResolver(field_priorities)
        conflict_manager.register_resolver("users", resolver)
        
        # Create a client change
        client_change = ChangeRecord(
            id=1,
            table_name="users",
            primary_key=(1,),
            operation="update",
            timestamp=time.time(),
            client_id="test_client",
            old_data=None,
            new_data={"id": 1, "username": "client_user", "email": "client@test.com", "description": "Client desc"}
        )
        
        # Server record
        server_record = {"id": 1, "username": "server_user", "email": "server@test.com", "description": "Server desc"}
        
        # Resolve conflict
        resolution = conflict_manager.resolve_conflict("users", client_change, server_record)
        
        if (resolution and 
            resolution["username"] == "client_user" and  # Priority field from client
            resolution["email"] == "client@test.com" and  # Priority field from client
            resolution["description"] == "Server desc"):  # Non-priority field from server
            print("✓ Conflict resolution successful")
        else:
            print("✗ Conflict resolution failed")
            return False
        
        # Test audit log
        conflicts = audit_log.get_conflicts_for_table("users")
        if len(conflicts) == 1:
            print("✓ Conflict audit logging successful")
        else:
            print("✗ Conflict audit logging failed")
            return False
        
        # Test JSON export/import
        json_data = audit_log.export_to_json()
        audit_log2 = ConflictAuditLog()
        audit_log2.import_from_json(json_data)
        
        if len(audit_log2.conflicts) == 1:
            print("✓ Audit log JSON export/import successful")
        else:
            print("✗ Audit log JSON export/import failed")
            return False
        
        print("✓ All conflict resolution operations passed!")
        return True
        
    except Exception as e:
        print(f"✗ Conflict resolution failed: {e}")
        traceback.print_exc()
        return False


def test_schema_management():
    """Test schema management with common library integration."""
    print("\nTesting schema management...")
    
    try:
        from ..schema.schema_manager import (
            SchemaVersionManager,
            SchemaMigrator, 
            SchemaSynchronizer,
            SchemaMigration,
            MigrationPlan
        )
        from ..db.schema import DatabaseSchema, TableSchema, Column
        
        # Create version manager
        version_manager = SchemaVersionManager()
        
        # Create initial schema
        columns_v1 = [
            Column("id", int, primary_key=True),
            Column("name", str)
        ]
        table_v1 = TableSchema("test_table", columns_v1)
        schema_v1 = DatabaseSchema({"test_table": table_v1}, version=1)
        
        # Register schema
        version_manager.register_schema(1, schema_v1)
        
        # Verify schema retrieval
        retrieved_schema = version_manager.get_schema(1)
        if retrieved_schema and retrieved_schema.version == 1:
            print("✓ Schema registration and retrieval successful")
        else:
            print("✗ Schema registration and retrieval failed")
            return False
        
        # Test migration creation
        migration = SchemaMigration(
            source_version=1,
            target_version=2,
            description="Add email column"
        )
        
        # Test migration serialization
        migration_dict = migration.to_dict()
        migration_restored = SchemaMigration.from_dict(migration_dict)
        
        if migration_restored.description == "Add email column":
            print("✓ Migration serialization successful")
        else:
            print("✗ Migration serialization failed")
            return False
        
        # Test synchronizer
        migrator = SchemaMigrator(version_manager)
        synchronizer = SchemaSynchronizer(version_manager, migrator)
        
        # Create a mock migration plan
        plan = MigrationPlan(migration=migration)
        
        # Test serialization
        json_str = synchronizer.serialize_migration_plan(plan)
        plan_restored = synchronizer.deserialize_migration_plan(json_str)
        
        if plan_restored.migration.description == "Add email column":
            print("✓ Migration plan serialization successful")
        else:
            print("✗ Migration plan serialization failed")
            return False
        
        print("✓ All schema management operations passed!")
        return True
        
    except Exception as e:
        print(f"✗ Schema management failed: {e}")
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests."""
    print("Running SyncDB refactoring integration tests...\n")
    
    tests = [
        test_basic_database_operations,
        test_change_tracking,
        test_conflict_resolution,
        test_schema_management
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Refactoring successful.")
        return True
    else:
        print("❌ Some tests failed. Review the refactoring.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)