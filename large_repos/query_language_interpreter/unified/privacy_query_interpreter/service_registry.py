"""Service registry and initialization for privacy query interpreter components."""

from typing import Any, Dict, List, Optional
import asyncio

# Common service registry
from common.services.registry import ServiceRegistry
from common.services.base_services import ServiceConfig
from common.utils.validation import InputValidator
from common.utils.logging import get_logger

# Privacy service imports
from privacy_query_interpreter.pii_detection.detector import PIIDetector
from privacy_query_interpreter.anonymization.anonymizer import DataAnonymizer
from privacy_query_interpreter.policy_enforcement.enforcer import PolicyEnforcer
from privacy_query_interpreter.access_logging.logger import AccessLogger
from privacy_query_interpreter.query_engine.engine import PrivacyQueryEngine
from privacy_query_interpreter.query_engine.parser import QueryParser


class PrivacyServiceRegistry:
    """
    Registry and manager for all privacy-related services.
    
    This class provides centralized management of privacy services,
    including initialization, configuration, and lifecycle management.
    """
    
    def __init__(self, service_registry: Optional[ServiceRegistry] = None):
        """Initialize the privacy service registry.
        
        Args:
            service_registry: Optional common service registry to use
        """
        self.service_registry = service_registry or ServiceRegistry()
        self.logger = get_logger("privacy_service_registry")
        
        # Track registered privacy services
        self.privacy_services = {}
        
    async def initialize_all_services(
        self, 
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initialize all privacy services with their dependencies.
        
        Args:
            config: Optional configuration for services
            
        Returns:
            Dictionary of initialized services
        """
        if config is None:
            config = {}
        
        self.logger.info("Initializing privacy services...")
        
        # Initialize services in dependency order
        services = {}
        
        try:
            # 1. Initialize PII Detector (no dependencies)
            pii_detector_config = config.get("pii_detector", {})
            pii_detector = await self._initialize_pii_detector(pii_detector_config)
            services["pii_detector"] = pii_detector
            
            # 2. Initialize Access Logger (no dependencies)
            logger_config = config.get("access_logger", {})
            access_logger = await self._initialize_access_logger(logger_config)
            services["access_logger"] = access_logger
            
            # 3. Initialize Anonymizer (depends on PII Detector)
            anonymizer_config = config.get("anonymizer", {})
            anonymizer = await self._initialize_anonymizer(anonymizer_config, pii_detector)
            services["anonymizer"] = anonymizer
            
            # 4. Initialize Policy Enforcer (depends on PII Detector and Access Logger)
            enforcer_config = config.get("policy_enforcer", {})
            policy_enforcer = await self._initialize_policy_enforcer(
                enforcer_config, pii_detector, access_logger
            )
            services["policy_enforcer"] = policy_enforcer
            
            # 5. Initialize Query Parser (no dependencies)
            parser_config = config.get("parser", {})
            parser = await self._initialize_parser(parser_config)
            services["parser"] = parser
            
            # 6. Initialize Query Engine (depends on all other services)
            engine_config = config.get("query_engine", {})
            query_engine = await self._initialize_query_engine(
                engine_config, 
                access_logger=access_logger,
                policy_enforcer=policy_enforcer,
                anonymizer=anonymizer,
                pii_detector=pii_detector,
                parser=parser
            )
            services["query_engine"] = query_engine
            
            self.privacy_services = services
            self.logger.info(f"Successfully initialized {len(services)} privacy services")
            
            return services
            
        except Exception as e:
            self.logger.error(f"Failed to initialize privacy services: {e}")
            # Cleanup any partially initialized services
            await self._cleanup_services(services)
            raise
    
    async def _initialize_pii_detector(self, config: Dict[str, Any]) -> PIIDetector:
        """Initialize the PII detector service."""
        service_config = ServiceConfig(
            service_name="pii_detector",
            service_type="detector",
            enabled=config.get("enabled", True),
            config=config
        )
        
        # Set default configuration values
        config = config or {}
        config.setdefault("confidence_threshold", 0.7)
        config.setdefault("max_sample_size", 1000)
        config.setdefault("custom_patterns", {})
        
        detector = PIIDetector(
            custom_patterns=config.get("custom_patterns"),
            confidence_threshold=config.get("confidence_threshold", 0.7),
            max_sample_size=config.get("max_sample_size", 1000),
            config=service_config
        )
        
        # Register with service registry
        self.service_registry.register_service("pii_detector", detector)
        
        # Initialize the service
        await detector.initialize()
        
        return detector
    
    async def _initialize_access_logger(self, config: Dict[str, Any]) -> AccessLogger:
        """Initialize the access logger service."""
        # Set default configuration values  
        config = config or {}
        config.setdefault("log_file", "privacy_access.log")
        config.setdefault("chain_logs", True)
        config.setdefault("max_log_size_mb", 10)
        config.setdefault("sensitive_field_handling", "hash")
        
        logger = AccessLogger(
            log_file=config.get("log_file", "privacy_access.log"),
            hmac_key=config.get("hmac_key"),
            chain_logs=config.get("chain_logs", True),
            encryption_key=config.get("encryption_key"),
            max_log_size_mb=config.get("max_log_size_mb", 10),
            sensitive_field_handling=config.get("sensitive_field_handling", "hash")
        )
        
        # Register with service registry (not a BaseService, but track it)
        self.service_registry.register_custom_service("access_logger", logger)
        
        return logger
    
    async def _initialize_anonymizer(
        self, 
        config: Dict[str, Any], 
        pii_detector: PIIDetector
    ) -> DataAnonymizer:
        """Initialize the data anonymizer service."""
        service_config = ServiceConfig(
            service_name="data_anonymizer",
            service_type="analyzer",
            enabled=config.get("enabled", True),
            config=config
        )
        
        # Configuration is optional for anonymizer
        config = config or {}
        
        anonymizer = DataAnonymizer(
            hmac_key=config.get("hmac_key"),
            pii_detector=pii_detector,
            pseudonym_salt=config.get("pseudonym_salt"),
            config=service_config
        )
        
        # Register with service registry
        self.service_registry.register_service("data_anonymizer", anonymizer)
        
        # Initialize the service
        await anonymizer.initialize()
        
        return anonymizer
    
    async def _initialize_policy_enforcer(
        self, 
        config: Dict[str, Any],
        pii_detector: PIIDetector,
        access_logger: AccessLogger
    ) -> PolicyEnforcer:
        """Initialize the policy enforcer service."""
        service_config = ServiceConfig(
            service_name="policy_enforcer",
            service_type="enforcer",
            enabled=config.get("enabled", True),
            config=config
        )
        
        # Configuration is optional for enforcer
        config = config or {}
        
        enforcer = PolicyEnforcer(
            policies=config.get("policies"),
            pii_detector=pii_detector,
            access_logger=access_logger,
            field_categories=config.get("field_categories"),
            config=service_config
        )
        
        # Register with service registry
        self.service_registry.register_service("policy_enforcer", enforcer)
        
        # Initialize the service
        await enforcer.initialize()
        
        return enforcer
    
    async def _initialize_parser(self, config: Dict[str, Any]) -> QueryParser:
        """Initialize the query parser."""
        parser = QueryParser()
        
        # Register with service registry (not a BaseService, but track it)
        self.service_registry.register_custom_service("query_parser", parser)
        
        return parser
    
    async def _initialize_query_engine(
        self,
        config: Dict[str, Any],
        access_logger: AccessLogger,
        policy_enforcer: PolicyEnforcer,
        anonymizer: DataAnonymizer,
        pii_detector: PIIDetector,
        parser: QueryParser
    ) -> PrivacyQueryEngine:
        """Initialize the privacy query engine."""
        # Set default configuration values
        config = config or {}
        config.setdefault("data_sources", {})
        
        # Initialize data minimizer if configured
        data_minimizer = None
        if config.get("data_minimizer"):
            from privacy_query_interpreter.data_minimization.minimizer import DataMinimizer
            data_minimizer = DataMinimizer()
        
        engine = PrivacyQueryEngine(
            access_logger=access_logger,
            policy_enforcer=policy_enforcer,
            data_minimizer=data_minimizer,
            data_anonymizer=anonymizer,
            pii_detector=pii_detector,
            data_sources=config.get("data_sources", {}),
            parser=parser
        )
        
        # Register with service registry (not a BaseService, but track it)
        self.service_registry.register_custom_service("privacy_query_engine", engine)
        
        return engine
    
    async def _cleanup_services(self, services: Dict[str, Any]) -> None:
        """Cleanup partially initialized services."""
        for name, service in services.items():
            try:
                if hasattr(service, 'shutdown'):
                    await service.shutdown()
                self.logger.info(f"Cleaned up service: {name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up service {name}: {e}")
    
    async def shutdown_all_services(self) -> None:
        """Shutdown all registered privacy services."""
        self.logger.info("Shutting down privacy services...")
        
        # Shutdown in reverse dependency order
        shutdown_order = [
            "privacy_query_engine",
            "query_parser", 
            "policy_enforcer",
            "data_anonymizer",
            "access_logger",
            "pii_detector"
        ]
        
        for service_name in shutdown_order:
            if service_name in self.privacy_services:
                try:
                    service = self.privacy_services[service_name]
                    if hasattr(service, 'shutdown'):
                        await service.shutdown()
                    self.logger.info(f"Shutdown service: {service_name}")
                except Exception as e:
                    self.logger.error(f"Error shutting down service {service_name}: {e}")
        
        self.privacy_services.clear()
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a registered privacy service by name.
        
        Args:
            name: Name of the service
            
        Returns:
            The service instance or None if not found
        """
        return self.privacy_services.get(name)
    
    def list_services(self) -> List[str]:
        """List all registered privacy services.
        
        Returns:
            List of service names
        """
        return list(self.privacy_services.keys())
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health checks on all services.
        
        Returns:
            Health check results for all services
        """
        results = {}
        
        for name, service in self.privacy_services.items():
            try:
                if hasattr(service, 'health_check'):
                    health = await service.health_check()
                    results[name] = health
                else:
                    results[name] = {"status": "healthy", "note": "No health check method"}
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)}
        
        return results


# Global privacy service registry instance
_privacy_registry = None

def get_privacy_registry() -> PrivacyServiceRegistry:
    """Get the global privacy service registry instance."""
    global _privacy_registry
    if _privacy_registry is None:
        _privacy_registry = PrivacyServiceRegistry()
    return _privacy_registry