"""Query execution pipeline and utilities for the unified query language interpreter."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Callable, AsyncGenerator
from enum import Enum
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from .base_models import (
    BaseQuery, 
    QueryResult, 
    ExecutionContext, 
    QueryStatus,
    Hook,
    HookType
)
from .exceptions import ExecutionError, TimeoutError, QueryEngineError


class ExecutionPhase(str, Enum):
    """Phases of query execution."""
    
    INITIALIZATION = "initialization"
    PARSING = "parsing"
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    PREPROCESSING = "preprocessing"
    EXECUTION = "execution"
    POSTPROCESSING = "postprocessing"
    AGGREGATION = "aggregation"
    FORMATTING = "formatting"
    FINALIZATION = "finalization"


class ExecutionResult:
    """Result of an execution phase."""
    
    def __init__(
        self,
        phase: ExecutionPhase,
        success: bool,
        data: Optional[Any] = None,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None
    ):
        """Initialize execution result.
        
        Args:
            phase: Execution phase
            success: Whether the phase succeeded
            data: Data produced by the phase
            error: Error if phase failed
            metadata: Additional metadata
            execution_time: Time taken for this phase
        """
        self.phase = phase
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.execution_time = execution_time
        self.timestamp = datetime.now()


class ExecutionPipeline:
    """Pipeline for executing queries with hooks and phases."""
    
    def __init__(self, max_workers: int = 4, default_timeout: float = 30.0):
        """Initialize the execution pipeline.
        
        Args:
            max_workers: Maximum number of worker threads
            default_timeout: Default timeout for operations
        """
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Hook registry
        self._hooks: Dict[HookType, List[Hook]] = {hook_type: [] for hook_type in HookType}
        self._hook_functions: Dict[str, Callable] = {}
        
        # Phase handlers
        self._phase_handlers: Dict[ExecutionPhase, Callable] = {}
        
        # Execution state
        self._active_executions: Dict[str, ExecutionContext] = {}
    
    def register_hook(self, hook: Hook, handler: Callable) -> None:
        """Register a hook with its handler function.
        
        Args:
            hook: Hook configuration
            handler: Handler function for the hook
        """
        self._hooks[hook.hook_type].append(hook)
        self._hook_functions[hook.name] = handler
        
        # Sort hooks by priority (higher priority first)
        self._hooks[hook.hook_type].sort(key=lambda h: h.priority, reverse=True)
    
    def unregister_hook(self, hook_name: str) -> bool:
        """Unregister a hook by name.
        
        Args:
            hook_name: Name of the hook to unregister
            
        Returns:
            True if hook was found and removed
        """
        removed = False
        
        for hook_type, hooks in self._hooks.items():
            self._hooks[hook_type] = [h for h in hooks if h.name != hook_name]
            if len(hooks) != len(self._hooks[hook_type]):
                removed = True
        
        if hook_name in self._hook_functions:
            del self._hook_functions[hook_name]
            removed = True
        
        return removed
    
    def register_phase_handler(self, phase: ExecutionPhase, handler: Callable) -> None:
        """Register a handler for an execution phase.
        
        Args:
            phase: Execution phase
            handler: Handler function for the phase
        """
        self._phase_handlers[phase] = handler
    
    async def execute_hooks(
        self,
        hook_type: HookType,
        context: ExecutionContext,
        data: Optional[Any] = None,
        error: Optional[Exception] = None
    ) -> Dict[str, Any]:
        """Execute all hooks of a given type.
        
        Args:
            hook_type: Type of hooks to execute
            context: Execution context
            data: Data to pass to hooks
            error: Error to pass to hooks (for error hooks)
            
        Returns:
            Dictionary of hook results
        """
        results = {}
        hooks = [h for h in self._hooks[hook_type] if h.enabled]
        
        for hook in hooks:
            try:
                handler = self._hook_functions.get(hook.name)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(context, data, error)
                    else:
                        result = handler(context, data, error)
                    results[hook.name] = result
            except Exception as e:
                # Hook errors shouldn't stop execution
                results[hook.name] = {"error": str(e)}
        
        return results
    
    async def execute_phase(
        self,
        phase: ExecutionPhase,
        context: ExecutionContext,
        data: Optional[Any] = None,
        timeout: Optional[float] = None
    ) -> ExecutionResult:
        """Execute a specific phase of the pipeline.
        
        Args:
            phase: Phase to execute
            context: Execution context
            data: Input data for the phase
            timeout: Timeout for the phase
            
        Returns:
            ExecutionResult with the phase outcome
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        try:
            handler = self._phase_handlers.get(phase)
            if not handler:
                raise ExecutionError(
                    f"No handler registered for phase: {phase}",
                    query_id=context.query_id,
                    execution_phase=phase.value
                )
            
            # Execute the handler with timeout
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(context, data),
                    timeout=timeout
                )
            else:
                # Run synchronous handler in thread pool
                future = self.executor.submit(handler, context, data)
                try:
                    result = future.result(timeout=timeout)
                except FutureTimeoutError:
                    future.cancel()
                    raise TimeoutError(
                        f"Phase {phase} timed out after {timeout} seconds",
                        timeout_seconds=timeout,
                        operation=f"execute_phase_{phase.value}"
                    )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                phase=phase,
                success=True,
                data=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Execute error hooks
            await self.execute_hooks(HookType.ON_ERROR, context, data, e)
            
            return ExecutionResult(
                phase=phase,
                success=False,
                error=e,
                execution_time=execution_time
            )
    
    def get_active_executions(self) -> Dict[str, ExecutionContext]:
        """Get all currently active executions.
        
        Returns:
            Dictionary of active execution contexts
        """
        return self._active_executions.copy()
    
    def cancel_execution(self, query_id: str) -> bool:
        """Cancel an active execution.
        
        Args:
            query_id: ID of the query execution to cancel
            
        Returns:
            True if execution was found and cancelled
        """
        if query_id in self._active_executions:
            # Mark as cancelled in the context
            context = self._active_executions[query_id]
            context.execution_metadata["cancelled"] = True
            context.execution_metadata["cancelled_at"] = datetime.now()
            return True
        return False
    
    def cleanup(self) -> None:
        """Clean up the execution pipeline resources."""
        self.executor.shutdown(wait=True)


class QueryExecutor:
    """Main query executor that orchestrates the execution pipeline."""
    
    def __init__(
        self,
        pipeline: Optional[ExecutionPipeline] = None,
        enable_parallel_execution: bool = False,
        max_concurrent_queries: int = 10
    ):
        """Initialize the query executor.
        
        Args:
            pipeline: Execution pipeline (created if not provided)
            enable_parallel_execution: Whether to enable parallel query execution
            max_concurrent_queries: Maximum number of concurrent queries
        """
        self.pipeline = pipeline or ExecutionPipeline()
        self.enable_parallel_execution = enable_parallel_execution
        self.max_concurrent_queries = max_concurrent_queries
        
        # Execution tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.active_queries: Dict[str, ExecutionContext] = {}
        
        # Semaphore for controlling concurrent executions
        self._execution_semaphore = asyncio.Semaphore(max_concurrent_queries)
    
    async def execute_query(
        self,
        query: Union[str, BaseQuery],
        context: ExecutionContext,
        phases: Optional[List[ExecutionPhase]] = None
    ) -> QueryResult:
        """Execute a query through the complete pipeline.
        
        Args:
            query: Query to execute
            context: Execution context
            phases: List of phases to execute (all phases if None)
            
        Returns:
            Query result
        """
        if phases is None:
            phases = list(ExecutionPhase)
        
        start_time = time.time()
        query_id = context.query_id
        
        # Add to active queries
        self.active_queries[query_id] = context
        
        try:
            # Acquire semaphore for concurrent execution control
            async with self._execution_semaphore:
                # Execute pre-execution hooks
                await self.pipeline.execute_hooks(HookType.PRE_EXECUTE, context, query)
                
                # Execute each phase
                phase_results = []
                current_data = query
                
                for phase in phases:
                    # Check if execution was cancelled
                    if context.execution_metadata.get("cancelled", False):
                        raise ExecutionError(
                            "Query execution was cancelled",
                            query_id=query_id,
                            execution_phase=phase.value
                        )
                    
                    phase_result = await self.pipeline.execute_phase(phase, context, current_data)
                    phase_results.append(phase_result)
                    
                    if not phase_result.success:
                        # Phase failed, stop execution
                        raise phase_result.error or ExecutionError(
                            f"Phase {phase} failed",
                            query_id=query_id,
                            execution_phase=phase.value
                        )
                    
                    # Pass result to next phase
                    current_data = phase_result.data
                
                # Create final result
                execution_time = time.time() - start_time
                
                if isinstance(current_data, QueryResult):
                    result = current_data
                    result.execution_time = execution_time
                else:
                    # Create a basic result if the final data isn't a QueryResult
                    result = QueryResult(
                        query_id=query_id,
                        execution_time=execution_time,
                        status=QueryStatus.COMPLETED
                    )
                    
                    # Try to extract information from the data
                    if hasattr(current_data, 'document_ids'):
                        result.document_ids = current_data.document_ids
                    if hasattr(current_data, 'total_hits'):
                        result.total_hits = current_data.total_hits
                
                # Execute post-execution hooks
                await self.pipeline.execute_hooks(HookType.POST_EXECUTE, context, result)
                
                # Record execution history
                self.execution_history.append({
                    "query_id": query_id,
                    "execution_time": execution_time,
                    "status": result.status.value,
                    "phases": [p.value for p in phases],
                    "phase_times": [pr.execution_time for pr in phase_results],
                    "timestamp": datetime.now()
                })
                
                return result
                
        except Exception as e:
            # Execute error hooks
            await self.pipeline.execute_hooks(HookType.ON_ERROR, context, query, e)
            
            # Create error result
            execution_time = time.time() - start_time
            
            if isinstance(e, ExecutionError):
                raise e
            else:
                raise ExecutionError(
                    f"Query execution failed: {str(e)}",
                    query_id=query_id,
                    details={"original_error": str(e)}
                )
        
        finally:
            # Remove from active queries
            if query_id in self.active_queries:
                del self.active_queries[query_id]
    
    async def execute_queries_parallel(
        self,
        queries: List[Union[str, BaseQuery]],
        contexts: List[ExecutionContext]
    ) -> List[QueryResult]:
        """Execute multiple queries in parallel.
        
        Args:
            queries: List of queries to execute
            contexts: List of execution contexts
            
        Returns:
            List of query results
        """
        if not self.enable_parallel_execution:
            raise QueryEngineError("Parallel execution is not enabled")
        
        if len(queries) != len(contexts):
            raise QueryEngineError("Number of queries must match number of contexts")
        
        # Create tasks for parallel execution
        tasks = [
            asyncio.create_task(self.execute_query(query, context))
            for query, context in zip(queries, contexts)
        ]
        
        # Execute all tasks and collect results
        results = []
        for i, task in enumerate(tasks):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                # Create error result for failed query
                error_result = QueryResult(
                    query_id=contexts[i].query_id,
                    status=QueryStatus.FAILED,
                    execution_time=0.0,
                    error=str(e)
                )
                results.append(error_result)
        
        return results
    
    def register_phase_handler(self, phase: ExecutionPhase, handler: Callable) -> None:
        """Register a handler for an execution phase.
        
        Args:
            phase: Execution phase
            handler: Handler function
        """
        self.pipeline.register_phase_handler(phase, handler)
    
    def register_hook(self, hook: Hook, handler: Callable) -> None:
        """Register a hook with its handler.
        
        Args:
            hook: Hook configuration
            handler: Handler function
        """
        self.pipeline.register_hook(hook, handler)
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Dictionary of execution statistics
        """
        if not self.execution_history:
            return {
                "total_executions": 0,
                "active_queries": len(self.active_queries),
                "average_execution_time": 0.0,
                "success_rate": 0.0
            }
        
        total_executions = len(self.execution_history)
        successful_executions = sum(
            1 for exec_info in self.execution_history 
            if exec_info["status"] == QueryStatus.COMPLETED.value
        )
        
        total_time = sum(exec_info["execution_time"] for exec_info in self.execution_history)
        average_time = total_time / total_executions if total_executions > 0 else 0.0
        
        success_rate = (successful_executions / total_executions) * 100 if total_executions > 0 else 0.0
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": total_executions - successful_executions,
            "active_queries": len(self.active_queries),
            "average_execution_time": average_time,
            "success_rate": success_rate,
            "recent_executions": self.execution_history[-10:]  # Last 10 executions
        }
    
    def cancel_query(self, query_id: str) -> bool:
        """Cancel an active query execution.
        
        Args:
            query_id: ID of the query to cancel
            
        Returns:
            True if query was found and cancelled
        """
        return self.pipeline.cancel_execution(query_id)
    
    def clear_execution_history(self) -> None:
        """Clear the execution history."""
        self.execution_history.clear()
    
    def cleanup(self) -> None:
        """Clean up executor resources."""
        self.pipeline.cleanup()


class ResultAggregator:
    """Aggregates and processes query results."""
    
    def __init__(self):
        """Initialize the result aggregator."""
        self._aggregation_functions: Dict[str, Callable] = {
            "sum": self._sum_aggregation,
            "avg": self._avg_aggregation,
            "min": self._min_aggregation,
            "max": self._max_aggregation,
            "count": self._count_aggregation,
            "group_by": self._group_by_aggregation
        }
    
    def register_aggregation_function(self, name: str, func: Callable) -> None:
        """Register a custom aggregation function.
        
        Args:
            name: Name of the aggregation function
            func: Aggregation function
        """
        self._aggregation_functions[name] = func
    
    def aggregate_results(
        self,
        results: List[QueryResult],
        aggregation_specs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate multiple query results.
        
        Args:
            results: List of query results to aggregate
            aggregation_specs: List of aggregation specifications
            
        Returns:
            Dictionary of aggregated results
        """
        aggregated = {}
        
        for spec in aggregation_specs:
            agg_name = spec.get("name", "unnamed")
            agg_type = spec.get("type")
            agg_field = spec.get("field")
            agg_params = spec.get("params", {})
            
            if agg_type in self._aggregation_functions:
                try:
                    result = self._aggregation_functions[agg_type](
                        results, agg_field, agg_params
                    )
                    aggregated[agg_name] = result
                except Exception as e:
                    aggregated[agg_name] = {"error": str(e)}
        
        return aggregated
    
    def _sum_aggregation(
        self,
        results: List[QueryResult],
        field: str,
        params: Dict[str, Any]
    ) -> float:
        """Sum aggregation function."""
        total = 0.0
        for result in results:
            # This is a simplified implementation
            # In a real system, you'd extract the field value from result data
            if hasattr(result, field):
                value = getattr(result, field)
                if isinstance(value, (int, float)):
                    total += value
        return total
    
    def _avg_aggregation(
        self,
        results: List[QueryResult],
        field: str,
        params: Dict[str, Any]
    ) -> float:
        """Average aggregation function."""
        total = self._sum_aggregation(results, field, params)
        count = len([r for r in results if hasattr(r, field)])
        return total / count if count > 0 else 0.0
    
    def _min_aggregation(
        self,
        results: List[QueryResult],
        field: str,
        params: Dict[str, Any]
    ) -> Any:
        """Minimum aggregation function."""
        values = []
        for result in results:
            if hasattr(result, field):
                value = getattr(result, field)
                if value is not None:
                    values.append(value)
        return min(values) if values else None
    
    def _max_aggregation(
        self,
        results: List[QueryResult],
        field: str,
        params: Dict[str, Any]
    ) -> Any:
        """Maximum aggregation function."""
        values = []
        for result in results:
            if hasattr(result, field):
                value = getattr(result, field)
                if value is not None:
                    values.append(value)
        return max(values) if values else None
    
    def _count_aggregation(
        self,
        results: List[QueryResult],
        field: str,
        params: Dict[str, Any]
    ) -> int:
        """Count aggregation function."""
        if field:
            return len([r for r in results if hasattr(r, field) and getattr(r, field) is not None])
        else:
            return len(results)
    
    def _group_by_aggregation(
        self,
        results: List[QueryResult],
        field: str,
        params: Dict[str, Any]
    ) -> Dict[str, List[QueryResult]]:
        """Group by aggregation function."""
        groups = {}
        for result in results:
            if hasattr(result, field):
                group_value = str(getattr(result, field))
                if group_value not in groups:
                    groups[group_value] = []
                groups[group_value].append(result)
        return groups