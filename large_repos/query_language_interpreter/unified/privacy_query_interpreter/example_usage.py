#!/usr/bin/env python3
"""Example usage of the refactored privacy query interpreter with common base classes."""

import asyncio
import pandas as pd
from typing import Dict, Any

from privacy_query_interpreter import (
    get_privacy_registry,
    PrivacyServiceRegistry,
    DataPolicy,
    PolicySet,
    PolicyAction,
    PolicyType,
    FieldCategory,
    get_logger
)

# Set up logging
logger = get_logger("privacy_example")

async def main():
    """Demonstrate the refactored privacy query interpreter usage."""
    logger.info("Starting privacy query interpreter example...")
    
    # Create sample data
    customers_df = pd.DataFrame([
        {"id": 1, "name": "John Doe", "email": "john@example.com", "ssn": "123-45-6789"},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "ssn": "987-65-4321"}
    ])
    
    # Configuration for privacy services
    config = {
        "pii_detector": {
            "confidence_threshold": 0.8,
            "max_sample_size": 1000
        },
        "access_logger": {
            "log_file": "privacy_access_example.log",
            "chain_logs": True,
            "sensitive_field_handling": "hash"
        },
        "anonymizer": {
            "hmac_key": "example_key_do_not_use_in_production"
        },
        "policy_enforcer": {
            "enabled": True
        },
        "query_engine": {
            "data_sources": {
                "customers": customers_df
            }
        }
    }
    
    try:
        # Get the privacy service registry
        registry = get_privacy_registry()
        
        # Initialize all services
        logger.info("Initializing privacy services...")
        services = await registry.initialize_all_services(config)
        
        # Get the query engine
        query_engine = services["query_engine"]
        policy_enforcer = services["policy_enforcer"]
        
        # Create a sample privacy policy
        policy = DataPolicy(
            name="SSN_Restriction",
            policy_type=PolicyType.FIELD_RESTRICTION,
            action=PolicyAction.DENY,
            restricted_fields=["ssn"],
            description="Deny access to SSN field for non-privileged users"
        )
        
        # Add policy to enforcer
        policy_enforcer.add_policy(policy)
        
        logger.info("Privacy services initialized successfully!")
        
        # Example 1: Execute a safe query
        logger.info("Executing safe query...")
        safe_query = "SELECT name, email FROM customers"
        user_context = {
            "user_id": "user123",
            "roles": ["analyst"],
            "purpose": "data_analysis"
        }
        
        try:
            result = query_engine.execute_query(safe_query, user_context)
            logger.info(f"Safe query result: {result.status}, {result.total_hits} rows")
        except Exception as e:
            logger.error(f"Safe query failed: {e}")
        
        # Example 2: Execute a query that should be denied
        logger.info("Executing restricted query...")
        restricted_query = "SELECT name, email, ssn FROM customers"
        
        try:
            result = query_engine.execute_query(restricted_query, user_context)
            logger.info(f"Restricted query result: {result.status}, reason: {result.reason}")
        except Exception as e:
            logger.error(f"Restricted query failed: {e}")
        
        # Example 3: Use individual services directly
        logger.info("Testing individual services...")
        
        # Test PII detector
        pii_detector = services["pii_detector"]
        pii_result = await pii_detector.detect("john@example.com", "email_field")
        logger.info(f"PII detection result: {pii_result}")
        
        # Test anonymizer
        anonymizer = services["anonymizer"]
        anon_result = await anonymizer.analyze(
            {"name": "John Doe", "email": "john@example.com"}, 
            "anonymize"
        )
        logger.info(f"Anonymization result: {anon_result['success']}")
        
        # Health check all services
        logger.info("Performing health checks...")
        health_results = await registry.health_check_all()
        for service_name, health in health_results.items():
            logger.info(f"{service_name}: {health['status']}")
        
        logger.info("Privacy query interpreter example completed successfully!")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise
    
    finally:
        # Cleanup
        try:
            await registry.shutdown_all_services()
            logger.info("Services shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    asyncio.run(main())