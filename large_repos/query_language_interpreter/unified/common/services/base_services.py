"""Base service classes for the unified query language interpreter."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import asyncio
from datetime import datetime

from ..core.base_models import BaseDocument, QueryResult, ExecutionContext
from ..core.exceptions import ServiceError


class ServiceStatus(str, Enum):
    """Status of a service."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    INITIALIZING = "initializing"
    SHUTTING_DOWN = "shutting_down"


class ServiceConfig:
    """Configuration for a base service."""
    
    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None
    ):
        """Initialize service configuration.
        
        Args:
            service_name: Name of the service
            version: Service version
            enabled: Whether service is enabled
            config: Service-specific configuration
            dependencies: List of service dependencies
        """
        self.service_name = service_name
        self.version = version
        self.enabled = enabled
        self.config = config or {}
        self.dependencies = dependencies or []
        self.created_at = datetime.now()


class BaseService(ABC):
    """Base class for all services in the system."""
    
    def __init__(self, config: ServiceConfig):
        """Initialize the base service.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.status = ServiceStatus.INACTIVE
        self.error_message: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.metrics: Dict[str, Any] = {}
        self._is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service.
        
        Raises:
            ServiceError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the service gracefully.
        
        Raises:
            ServiceError: If shutdown fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the service.
        
        Returns:
            Dictionary containing health status information
        """
        pass
    
    async def start(self) -> None:
        """Start the service."""
        if not self.config.enabled:
            self.status = ServiceStatus.INACTIVE
            return
        
        self.status = ServiceStatus.INITIALIZING
        self.start_time = datetime.now()
        
        try:
            await self.initialize()
            self.status = ServiceStatus.ACTIVE
            self._is_initialized = True
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self.error_message = str(e)
            raise ServiceError(
                f"Failed to start service {self.config.service_name}: {str(e)}",
                service_name=self.config.service_name,
                operation="start"
            )
    
    async def stop(self) -> None:
        """Stop the service."""
        if self.status == ServiceStatus.INACTIVE:
            return
        
        self.status = ServiceStatus.SHUTTING_DOWN
        
        try:
            await self.shutdown()
            self.status = ServiceStatus.INACTIVE
            self._is_initialized = False
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self.error_message = str(e)
            raise ServiceError(
                f"Failed to stop service {self.config.service_name}: {str(e)}",
                service_name=self.config.service_name,
                operation="stop"
            )
    
    def is_active(self) -> bool:
        """Check if service is active.
        
        Returns:
            True if service is active
        """
        return self.status == ServiceStatus.ACTIVE
    
    def is_initialized(self) -> bool:
        """Check if service is initialized.
        
        Returns:
            True if service is initialized
        """
        return self._is_initialized
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information.
        
        Returns:
            Dictionary containing service information
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "name": self.config.service_name,
            "version": self.config.version,
            "status": self.status.value,
            "enabled": self.config.enabled,
            "uptime_seconds": uptime,
            "error_message": self.error_message,
            "metrics": self.metrics
        }
    
    def record_metric(self, name: str, value: Any) -> None:
        """Record a metric for this service.
        
        Args:
            name: Metric name
            value: Metric value
        """
        self.metrics[name] = {
            "value": value,
            "timestamp": datetime.now()
        }


class BaseDetectorService(BaseService):
    """Base class for detection services (PII, privilege, etc.)."""
    
    @abstractmethod
    async def detect(
        self,
        content: Union[str, BaseDocument, List[BaseDocument]],
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Detect patterns in content.
        
        Args:
            content: Content to analyze
            context: Optional execution context
            
        Returns:
            Detection results
        """
        pass
    
    @abstractmethod
    async def scan_document(
        self,
        document: BaseDocument,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Scan a single document for patterns.
        
        Args:
            document: Document to scan
            context: Optional execution context
            
        Returns:
            Scan results
        """
        pass
    
    async def batch_scan(
        self,
        documents: List[BaseDocument],
        context: Optional[ExecutionContext] = None,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Scan multiple documents in batches.
        
        Args:
            documents: List of documents to scan
            context: Optional execution context
            batch_size: Number of documents to process in each batch
            
        Returns:
            List of scan results
        """
        results = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_tasks = [self.scan_document(doc, context) for doc in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append({"error": str(result)})
                else:
                    results.append(result)
        
        return results


class BaseEnforcerService(BaseService):
    """Base class for enforcement services (policy, privacy, etc.)."""
    
    @abstractmethod
    async def enforce(
        self,
        query: str,
        context: ExecutionContext,
        proposed_result: Optional[QueryResult] = None
    ) -> Dict[str, Any]:
        """Enforce policies on a query or result.
        
        Args:
            query: Query string
            context: Execution context
            proposed_result: Proposed query result
            
        Returns:
            Enforcement decision and any modifications
        """
        pass
    
    @abstractmethod
    async def check_compliance(
        self,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Check compliance status.
        
        Args:
            context: Execution context
            
        Returns:
            Compliance status information
        """
        pass
    
    async def audit_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Audit access to resources.
        
        Args:
            user_id: ID of the user
            resource: Resource being accessed
            action: Action being performed
            context: Optional execution context
            
        Returns:
            Audit information
        """
        audit_record = {
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "timestamp": datetime.now(),
            "context": context.query_id if context else None
        }
        
        # Default implementation just records the access
        # Subclasses should implement actual audit logic
        return audit_record


class BaseAnalyzerService(BaseService):
    """Base class for analysis services (document, communication, etc.)."""
    
    @abstractmethod
    async def analyze(
        self,
        data: Any,
        analysis_type: str,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Analyze data.
        
        Args:
            data: Data to analyze
            analysis_type: Type of analysis to perform
            context: Optional execution context
            
        Returns:
            Analysis results
        """
        pass
    
    @abstractmethod
    async def extract_features(
        self,
        data: Any,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Extract features from data.
        
        Args:
            data: Data to extract features from
            context: Optional execution context
            
        Returns:
            Extracted features
        """
        pass
    
    async def batch_analyze(
        self,
        data_items: List[Any],
        analysis_type: str,
        context: Optional[ExecutionContext] = None,
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """Analyze multiple data items in batches.
        
        Args:
            data_items: List of data items to analyze
            analysis_type: Type of analysis to perform
            context: Optional execution context
            batch_size: Number of items to process in each batch
            
        Returns:
            List of analysis results
        """
        results = []
        
        for i in range(0, len(data_items), batch_size):
            batch = data_items[i:i + batch_size]
            batch_tasks = [self.analyze(item, analysis_type, context) for item in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    results.append({"error": str(result)})
                else:
                    results.append(result)
        
        return results
    
    async def compare(
        self,
        data1: Any,
        data2: Any,
        comparison_type: str,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """Compare two data items.
        
        Args:
            data1: First data item
            data2: Second data item
            comparison_type: Type of comparison
            context: Optional execution context
            
        Returns:
            Comparison results
        """
        # Default implementation extracts features and compares them
        try:
            features1 = await self.extract_features(data1, context)
            features2 = await self.extract_features(data2, context)
            
            return {
                "comparison_type": comparison_type,
                "features1": features1,
                "features2": features2,
                "similarity_score": self._calculate_similarity(features1, features2)
            }
        except Exception as e:
            return {
                "comparison_type": comparison_type,
                "error": str(e),
                "similarity_score": 0.0
            }
    
    def _calculate_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate similarity between two feature sets.
        
        Args:
            features1: First feature set
            features2: Second feature set
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Simple implementation based on common keys
        keys1 = set(features1.keys())
        keys2 = set(features2.keys())
        
        if not keys1 or not keys2:
            return 0.0
        
        common_keys = keys1.intersection(keys2)
        total_keys = keys1.union(keys2)
        
        return len(common_keys) / len(total_keys) if total_keys else 0.0


class ServiceHealthChecker:
    """Health checker for services."""
    
    def __init__(self):
        """Initialize the health checker."""
        self.services: List[BaseService] = []
    
    def register_service(self, service: BaseService) -> None:
        """Register a service for health checking.
        
        Args:
            service: Service to register
        """
        self.services.append(service)
    
    def unregister_service(self, service_name: str) -> bool:
        """Unregister a service.
        
        Args:
            service_name: Name of the service to unregister
            
        Returns:
            True if service was found and removed
        """
        original_count = len(self.services)
        self.services = [s for s in self.services if s.config.service_name != service_name]
        return len(self.services) < original_count
    
    async def check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all registered services.
        
        Returns:
            Dictionary mapping service names to health status
        """
        results = {}
        
        health_checks = [
            self._check_service_health(service) 
            for service in self.services
        ]
        
        health_results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        for service, result in zip(self.services, health_results):
            service_name = service.config.service_name
            
            if isinstance(result, Exception):
                results[service_name] = {
                    "healthy": False,
                    "error": str(result),
                    "status": service.status.value
                }
            else:
                results[service_name] = result
        
        return results
    
    async def _check_service_health(self, service: BaseService) -> Dict[str, Any]:
        """Check health of a single service.
        
        Args:
            service: Service to check
            
        Returns:
            Health status information
        """
        try:
            # Get basic service info
            service_info = service.get_service_info()
            
            # Perform health check if service is active
            if service.is_active():
                health_result = await service.health_check()
                service_info.update(health_result)
                service_info["healthy"] = True
            else:
                service_info["healthy"] = False
                service_info["reason"] = f"Service is {service.status.value}"
            
            return service_info
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": service.status.value,
                "name": service.config.service_name
            }