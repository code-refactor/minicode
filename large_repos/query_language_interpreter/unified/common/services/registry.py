"""Service registry for managing services in the unified query language interpreter."""

import asyncio
from typing import Dict, List, Optional, Any, Type, Set
from enum import Enum
from datetime import datetime
from collections import defaultdict

from .base_services import BaseService, ServiceConfig, ServiceStatus, ServiceHealthChecker
from ..core.exceptions import ServiceError, ConfigurationError


class ServiceType(str, Enum):
    """Types of services that can be registered."""
    
    DETECTOR = "detector"
    ENFORCER = "enforcer"
    ANALYZER = "analyzer"
    PARSER = "parser"
    ENGINE = "engine"
    TRANSFORMER = "transformer"
    LOGGER = "logger"
    CACHE = "cache"
    CUSTOM = "custom"


class ServiceDependency:
    """Represents a dependency between services."""
    
    def __init__(
        self,
        service_name: str,
        dependency_name: str,
        required: bool = True,
        version_constraint: Optional[str] = None
    ):
        """Initialize service dependency.
        
        Args:
            service_name: Name of the service
            dependency_name: Name of the dependency
            required: Whether the dependency is required
            version_constraint: Version constraint for the dependency
        """
        self.service_name = service_name
        self.dependency_name = dependency_name
        self.required = required
        self.version_constraint = version_constraint


class ServiceRegistry:
    """Registry for managing services and their lifecycle."""
    
    def __init__(self):
        """Initialize the service registry."""
        self._services: Dict[str, BaseService] = {}
        self._service_types: Dict[str, ServiceType] = {}
        self._service_configs: Dict[str, ServiceConfig] = {}
        self._dependencies: Dict[str, List[ServiceDependency]] = defaultdict(list)
        self._startup_order: List[str] = []
        self._shutdown_order: List[str] = []
        self.health_checker = ServiceHealthChecker()
        self._is_shutting_down = False
    
    def register_service(
        self,
        service: BaseService,
        service_type: ServiceType = ServiceType.CUSTOM,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """Register a service with the registry.
        
        Args:
            service: Service instance to register
            service_type: Type of service
            dependencies: List of service dependencies
            
        Raises:
            ServiceError: If registration fails
        """
        service_name = service.config.service_name
        
        if service_name in self._services:
            raise ServiceError(
                f"Service '{service_name}' is already registered",
                service_name=service_name,
                operation="register"
            )
        
        # Validate dependencies
        if dependencies:
            missing_deps = [dep for dep in dependencies if dep not in self._services]
            if missing_deps:
                raise ServiceError(
                    f"Missing dependencies for service '{service_name}': {missing_deps}",
                    service_name=service_name,
                    operation="register"
                )
        
        # Register the service
        self._services[service_name] = service
        self._service_types[service_name] = service_type
        self._service_configs[service_name] = service.config
        
        # Register dependencies
        if dependencies:
            for dep_name in dependencies:
                dependency = ServiceDependency(service_name, dep_name)
                self._dependencies[service_name].append(dependency)
        
        # Update startup order based on dependencies
        self._update_startup_order()
        
        # Register with health checker
        self.health_checker.register_service(service)
    
    def unregister_service(self, service_name: str) -> bool:
        """Unregister a service from the registry.
        
        Args:
            service_name: Name of the service to unregister
            
        Returns:
            True if service was found and removed
        """
        if service_name not in self._services:
            return False
        
        # Stop the service if it's running
        service = self._services[service_name]
        if service.is_active():
            asyncio.create_task(service.stop())
        
        # Remove from all registries
        del self._services[service_name]
        del self._service_types[service_name]
        del self._service_configs[service_name]
        
        if service_name in self._dependencies:
            del self._dependencies[service_name]
        
        # Remove from startup order
        if service_name in self._startup_order:
            self._startup_order.remove(service_name)
        
        if service_name in self._shutdown_order:
            self._shutdown_order.remove(service_name)
        
        # Unregister from health checker
        self.health_checker.unregister_service(service_name)
        
        return True
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """Get a service by name.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance or None if not found
        """
        return self._services.get(service_name)
    
    def get_services_by_type(self, service_type: ServiceType) -> List[BaseService]:
        """Get all services of a specific type.
        
        Args:
            service_type: Type of services to retrieve
            
        Returns:
            List of services of the specified type
        """
        return [
            service for service_name, service in self._services.items()
            if self._service_types.get(service_name) == service_type
        ]
    
    def list_services(self) -> List[str]:
        """List all registered service names.
        
        Returns:
            List of service names
        """
        return list(self._services.keys())
    
    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service information dictionary or None if not found
        """
        service = self._services.get(service_name)
        if not service:
            return None
        
        info = service.get_service_info()
        info["type"] = self._service_types.get(service_name, ServiceType.CUSTOM).value
        info["dependencies"] = [
            dep.dependency_name for dep in self._dependencies.get(service_name, [])
        ]
        
        return info
    
    async def start_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Start all registered services in dependency order.
        
        Returns:
            Dictionary of service startup results
        """
        results = {}
        
        for service_name in self._startup_order:
            service = self._services.get(service_name)
            if not service:
                continue
            
            try:
                await service.start()
                results[service_name] = {
                    "success": True,
                    "status": service.status.value,
                    "started_at": service.start_time
                }
            except Exception as e:
                results[service_name] = {
                    "success": False,
                    "error": str(e),
                    "status": service.status.value
                }
        
        return results
    
    async def stop_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Stop all services in reverse dependency order.
        
        Returns:
            Dictionary of service shutdown results
        """
        self._is_shutting_down = True
        results = {}
        
        # Stop in reverse order
        for service_name in reversed(self._shutdown_order or self._startup_order):
            service = self._services.get(service_name)
            if not service:
                continue
            
            try:
                await service.stop()
                results[service_name] = {
                    "success": True,
                    "status": service.status.value
                }
            except Exception as e:
                results[service_name] = {
                    "success": False,
                    "error": str(e),
                    "status": service.status.value
                }
        
        return results
    
    async def start_service(self, service_name: str) -> bool:
        """Start a specific service and its dependencies.
        
        Args:
            service_name: Name of the service to start
            
        Returns:
            True if service started successfully
        """
        service = self._services.get(service_name)
        if not service:
            return False
        
        # Start dependencies first
        dependencies = self._dependencies.get(service_name, [])
        for dep in dependencies:
            if dep.required:
                dep_service = self._services.get(dep.dependency_name)
                if dep_service and not dep_service.is_active():
                    await dep_service.start()
        
        # Start the service
        try:
            await service.start()
            return True
        except Exception:
            return False
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop a specific service.
        
        Args:
            service_name: Name of the service to stop
            
        Returns:
            True if service stopped successfully
        """
        service = self._services.get(service_name)
        if not service:
            return False
        
        try:
            await service.stop()
            return True
        except Exception:
            return False
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a specific service.
        
        Args:
            service_name: Name of the service to restart
            
        Returns:
            True if service restarted successfully
        """
        if await self.stop_service(service_name):
            return await self.start_service(service_name)
        return False
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health checks on all services.
        
        Returns:
            Dictionary of health check results
        """
        return await self.health_checker.check_all_services()
    
    async def health_check_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Perform health check on a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Health check result or None if service not found
        """
        service = self._services.get(service_name)
        if not service:
            return None
        
        try:
            if service.is_active():
                return await service.health_check()
            else:
                return {
                    "healthy": False,
                    "reason": f"Service is {service.status.value}",
                    "status": service.status.value
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "status": service.status.value
            }
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get the dependency graph for all services.
        
        Returns:
            Dictionary mapping service names to their dependencies
        """
        graph = {}
        for service_name in self._services:
            dependencies = self._dependencies.get(service_name, [])
            graph[service_name] = [dep.dependency_name for dep in dependencies]
        return graph
    
    def validate_dependencies(self) -> List[str]:
        """Validate all service dependencies.
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        for service_name, dependencies in self._dependencies.items():
            for dep in dependencies:
                if dep.dependency_name not in self._services:
                    errors.append(
                        f"Service '{service_name}' has missing dependency: '{dep.dependency_name}'"
                    )
        
        # Check for circular dependencies
        circular_deps = self._find_circular_dependencies()
        if circular_deps:
            errors.append(f"Circular dependencies detected: {circular_deps}")
        
        return errors
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get overall registry status.
        
        Returns:
            Dictionary containing registry status information
        """
        active_services = sum(1 for service in self._services.values() if service.is_active())
        inactive_services = sum(1 for service in self._services.values() if not service.is_active())
        error_services = sum(1 for service in self._services.values() if service.status == ServiceStatus.ERROR)
        
        return {
            "total_services": len(self._services),
            "active_services": active_services,
            "inactive_services": inactive_services,
            "error_services": error_services,
            "service_types": {
                service_type.value: len(self.get_services_by_type(service_type))
                for service_type in ServiceType
            },
            "is_shutting_down": self._is_shutting_down,
            "startup_order": self._startup_order
        }
    
    def _update_startup_order(self) -> None:
        """Update the startup order based on dependencies using topological sort."""
        # Build adjacency list
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize in_degree for all services
        for service_name in self._services:
            in_degree[service_name] = 0
        
        # Build graph and calculate in-degrees
        for service_name, dependencies in self._dependencies.items():
            for dep in dependencies:
                graph[dep.dependency_name].append(service_name)
                in_degree[service_name] += 1
        
        # Topological sort using Kahn's algorithm
        queue = [service for service in self._services if in_degree[service] == 0]
        startup_order = []
        
        while queue:
            service = queue.pop(0)
            startup_order.append(service)
            
            for dependent in graph[service]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        self._startup_order = startup_order
        self._shutdown_order = list(reversed(startup_order))
    
    def _find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the service graph.
        
        Returns:
            List of circular dependency cycles
        """
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(service: str, path: List[str]) -> bool:
            visited.add(service)
            rec_stack.add(service)
            path.append(service)
            
            dependencies = self._dependencies.get(service, [])
            for dep in dependencies:
                if dep.dependency_name not in self._services:
                    continue
                
                if dep.dependency_name in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(dep.dependency_name)
                    cycle = path[cycle_start:] + [dep.dependency_name]
                    cycles.append(cycle)
                    return True
                elif dep.dependency_name not in visited:
                    if dfs(dep.dependency_name, path.copy()):
                        return True
            
            rec_stack.remove(service)
            return False
        
        for service in self._services:
            if service not in visited:
                dfs(service, [])
        
        return cycles
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_all_services()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_all_services()


# Default service registry instance
default_service_registry = ServiceRegistry()