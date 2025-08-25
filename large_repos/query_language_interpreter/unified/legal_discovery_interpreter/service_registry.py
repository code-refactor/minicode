"""Service registry and initialization for legal discovery interpreter components."""

from typing import Any, Dict, List, Optional
import asyncio

# Common service registry
from common.services.registry import ServiceRegistry
from common.services.base_services import ServiceConfig
from common.utils.validation import validate_config
from common.utils.logging import get_logger

# Legal service imports
from legal_discovery_interpreter.privilege.detector import PrivilegeDetector
from legal_discovery_interpreter.communication_analysis.analyzer import CommunicationAnalyzer
from legal_discovery_interpreter.document_analysis.analyzer import DocumentAnalyzer
from legal_discovery_interpreter.ontology.service import OntologyService
from legal_discovery_interpreter.core.interpreter import LegalQueryEngine
from legal_discovery_interpreter.core.document import DocumentCollection


class LegalServiceRegistry:
    """
    Registry and manager for all legal discovery services.
    
    This class provides centralized management of legal services,
    including initialization, configuration, and lifecycle management.
    """
    
    def __init__(self, service_registry: Optional[ServiceRegistry] = None):
        """Initialize the legal service registry.
        
        Args:
            service_registry: Optional common service registry to use
        """
        self.service_registry = service_registry or ServiceRegistry()
        self.logger = get_logger("legal_service_registry")
        
        # Track registered legal services
        self.legal_services = {}
        
    async def initialize_all_services(
        self, 
        config: Optional[Dict[str, Any]] = None,
        document_collection: Optional[DocumentCollection] = None
    ) -> Dict[str, Any]:
        """Initialize all legal services with their dependencies.
        
        Args:
            config: Optional configuration for services
            document_collection: Document collection for the query engine
            
        Returns:
            Dictionary of initialized services
        """
        if config is None:
            config = {}
        
        self.logger.info("Initializing legal discovery services...")
        
        # Initialize services in dependency order
        services = {}
        
        try:
            # 1. Initialize Ontology Service (no dependencies)
            ontology_config = config.get("ontology_service", {})
            ontology_service = await self._initialize_ontology_service(ontology_config)
            services["ontology_service"] = ontology_service
            
            # 2. Initialize Document Analyzer (depends on proximity engine - internal dependency)
            document_analyzer_config = config.get("document_analyzer", {})
            document_analyzer = await self._initialize_document_analyzer(document_analyzer_config)
            services["document_analyzer"] = document_analyzer
            
            # 3. Initialize Communication Analyzer (no dependencies)
            communication_analyzer_config = config.get("communication_analyzer", {})
            communication_analyzer = await self._initialize_communication_analyzer(communication_analyzer_config)
            services["communication_analyzer"] = communication_analyzer
            
            # 4. Initialize Privilege Detector (no dependencies)
            privilege_detector_config = config.get("privilege_detector", {})
            privilege_detector = await self._initialize_privilege_detector(privilege_detector_config)
            services["privilege_detector"] = privilege_detector
            
            # 5. Initialize Temporal Manager if configured
            temporal_manager = None
            if config.get("temporal_manager"):
                # This would initialize the temporal manager if it exists
                # For now, we'll skip it as it's not implemented in the refactor
                pass
            
            # 6. Initialize Query Engine (depends on all other services)
            engine_config = config.get("query_engine", {})
            query_engine = await self._initialize_query_engine(
                engine_config,
                document_collection=document_collection,
                ontology_service=ontology_service,
                document_analyzer=document_analyzer,
                communication_analyzer=communication_analyzer,
                temporal_manager=temporal_manager,
                privilege_detector=privilege_detector
            )
            services["query_engine"] = query_engine
            
            self.legal_services = services
            self.logger.info(f"Successfully initialized {len(services)} legal services")
            
            return services
            
        except Exception as e:
            self.logger.error(f"Failed to initialize legal services: {e}")
            # Cleanup any partially initialized services
            await self._cleanup_services(services)
            raise
    
    async def _initialize_ontology_service(self, config: Dict[str, Any]) -> OntologyService:
        """Initialize the ontology service."""
        service_config = ServiceConfig(
            service_name="ontology_service",
            enabled=config.get("enabled", True),
            config={**config, "service_type": "service"}
        )
        
        # Validate configuration
        await validate_config(config, {
            "default_ontologies": {"type": list, "default": []},
            "cache_size": {"type": int, "default": 1000}
        })
        
        ontology_service = OntologyService(config=service_config)
        
        # Register with service registry
        self.service_registry.register_service("ontology_service", ontology_service)
        
        # Initialize the service
        await ontology_service.start()
        
        return ontology_service
    
    async def _initialize_document_analyzer(self, config: Dict[str, Any]) -> DocumentAnalyzer:
        """Initialize the document analyzer service."""
        service_config = ServiceConfig(
            service_name="document_analyzer",
            enabled=config.get("enabled", True),
            config={**config, "service_type": "analyzer"}
        )
        
        # Validate configuration
        await validate_config(config, {
            "proximity_engine_config": {"type": dict, "default": {}},
            "similarity_threshold": {"type": float, "default": 0.7}
        })
        
        document_analyzer = DocumentAnalyzer(config=service_config)
        
        # Register with service registry
        self.service_registry.register_service("document_analyzer", document_analyzer)
        
        # Initialize the service
        await document_analyzer.start()
        
        return document_analyzer
    
    async def _initialize_communication_analyzer(self, config: Dict[str, Any]) -> CommunicationAnalyzer:
        """Initialize the communication analyzer service."""
        service_config = ServiceConfig(
            service_name="communication_analyzer",
            enabled=config.get("enabled", True),
            config={**config, "service_type": "analyzer"}
        )
        
        # Validate configuration
        await validate_config(config, {
            "participant_cache_size": {"type": int, "default": 1000}
        })
        
        communication_analyzer = CommunicationAnalyzer(config=service_config)
        
        # Register with service registry
        self.service_registry.register_service("communication_analyzer", communication_analyzer)
        
        # Initialize the service
        await communication_analyzer.start()
        
        return communication_analyzer
    
    async def _initialize_privilege_detector(self, config: Dict[str, Any]) -> PrivilegeDetector:
        """Initialize the privilege detector service."""
        service_config = ServiceConfig(
            service_name="privilege_detector",
            enabled=config.get("enabled", True),
            config={**config, "service_type": "detector"}
        )
        
        # Validate configuration
        await validate_config(config, {
            "confidence_threshold": {"type": float, "default": 0.5},
            "attorneys_file": {"type": str, "optional": True},
            "indicators_file": {"type": str, "optional": True}
        })
        
        privilege_detector = PrivilegeDetector(config=service_config)
        
        # Load attorneys and indicators if specified
        if config.get("attorneys_file"):
            privilege_detector.load_attorneys_from_file(config["attorneys_file"])
        
        if config.get("indicators_file"):
            privilege_detector.load_indicators_from_file(config["indicators_file"])
        
        # Register with service registry
        self.service_registry.register_service("privilege_detector", privilege_detector)
        
        # Initialize the service
        await privilege_detector.start()
        
        return privilege_detector
    
    async def _initialize_query_engine(
        self,
        config: Dict[str, Any],
        document_collection: Optional[DocumentCollection],
        ontology_service: OntologyService,
        document_analyzer: DocumentAnalyzer,
        communication_analyzer: CommunicationAnalyzer,
        temporal_manager: Any,
        privilege_detector: PrivilegeDetector
    ) -> LegalQueryEngine:
        """Initialize the legal query engine."""
        # Validate configuration
        await validate_config(config, {
            "max_results": {"type": int, "default": 10000},
            "enable_query_logging": {"type": bool, "default": True},
            "enable_performance_monitoring": {"type": bool, "default": True}
        })
        
        # Create or use provided document collection
        if document_collection is None:
            document_collection = DocumentCollection()
        
        from common.core.query_engine import QueryEngineConfig
        engine_config = QueryEngineConfig(
            max_results=config.get("max_results", 10000),
            enable_query_logging=config.get("enable_query_logging", True),
            enable_performance_monitoring=config.get("enable_performance_monitoring", True)
        )
        
        # Create a simple parser for now (would be more sophisticated in real implementation)
        from common.core.query_parser import BaseQueryParser
        
        class SimpleParser(BaseQueryParser):
            def parse_query(self, query_string: str) -> Dict[str, Any]:
                return {"query_string": query_string, "type": "legal"}
            
            def validate_query(self, parsed_query: Dict[str, Any]) -> tuple[bool, Optional[str]]:
                return True, None
        
        parser = SimpleParser()
        
        engine = LegalQueryEngine(
            document_collection=document_collection,
            ontology_service=ontology_service,
            document_analyzer=document_analyzer,
            communication_analyzer=communication_analyzer,
            temporal_manager=temporal_manager,
            privilege_detector=privilege_detector,
            parser=parser,
            config=engine_config
        )
        
        # Register with service registry (not a BaseService, but track it)
        self.service_registry.register_custom_service("legal_query_engine", engine)
        
        return engine
    
    async def _cleanup_services(self, services: Dict[str, Any]) -> None:
        """Cleanup partially initialized services."""
        for name, service in services.items():
            try:
                if hasattr(service, 'stop'):
                    await service.stop()
                elif hasattr(service, 'shutdown'):
                    await service.shutdown()
                self.logger.info(f"Cleaned up service: {name}")
            except Exception as e:
                self.logger.error(f"Error cleaning up service {name}: {e}")
    
    async def shutdown_all_services(self) -> None:
        """Shutdown all registered legal services."""
        self.logger.info("Shutting down legal services...")
        
        # Shutdown in reverse dependency order
        shutdown_order = [
            "legal_query_engine",
            "privilege_detector",
            "communication_analyzer",
            "document_analyzer",
            "ontology_service"
        ]
        
        for service_name in shutdown_order:
            if service_name in self.legal_services:
                try:
                    service = self.legal_services[service_name]
                    if hasattr(service, 'stop'):
                        await service.stop()
                    elif hasattr(service, 'shutdown'):
                        await service.shutdown()
                    self.logger.info(f"Shutdown service: {service_name}")
                except Exception as e:
                    self.logger.error(f"Error shutting down service {service_name}: {e}")
        
        self.legal_services.clear()
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a registered legal service by name.
        
        Args:
            name: Name of the service
            
        Returns:
            The service instance or None if not found
        """
        return self.legal_services.get(name)
    
    def list_services(self) -> List[str]:
        """List all registered legal services.
        
        Returns:
            List of service names
        """
        return list(self.legal_services.keys())
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health checks on all services.
        
        Returns:
            Health check results for all services
        """
        results = {}
        
        for name, service in self.legal_services.items():
            try:
                if hasattr(service, 'health_check'):
                    health = await service.health_check()
                    results[name] = health
                else:
                    results[name] = {"status": "healthy", "note": "No health check method"}
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)}
        
        return results


# Global legal service registry instance
_legal_registry = None

def get_legal_registry() -> LegalServiceRegistry:
    """Get the global legal service registry instance."""
    global _legal_registry
    if _legal_registry is None:
        _legal_registry = LegalServiceRegistry()
    return _legal_registry