"""Models for the concurrent task scheduler."""

from concurrent_task_scheduler.models.checkpoint import (
    Checkpoint,
    CheckpointCompression,
    CheckpointManager,
    CheckpointMetadata,
    CheckpointPolicy,
    CheckpointStatus,
    CheckpointStorageType,
    CheckpointType,
)
from concurrent_task_scheduler.models.resource_forecast import (
    ForecastAccuracy,
    ForecastPeriod,
    ResourceForecast,
    ResourceProjection,
    ResourceUsagePattern,
    ResourceUtilizationHistory,
    UtilizationDataPoint,
)
from concurrent_task_scheduler.models.scenario import (
    ComparisonResult,
    ResourceAllocation,
    ResearchObjective,
    Scenario,
    ScenarioEvaluationResult,
    ScenarioStatus,
    ScientificMetric,
)
from concurrent_task_scheduler.models.simulation import (
    ClusterStatus,
    ComputeNode,
    ExtendedNodeStatus,
    NodeStatus,  # For backward compatibility, but will be from common
    NodeType,
    ResourceRequirement,
    ResourceType,  # Re-exported from common
    Simulation,
    SimulationPriority,  # Alias to common Priority
    SimulationStage,
    SimulationStageStatus,
    SimulationStatus,
)
# Import common library components for unified use
from common.core.models import Priority, JobStatus, BaseJob, BaseNode, NodeStatus
from concurrent_task_scheduler.models.utils import (
    DateTimeEncoder,
    PerformanceMetric,
    Result,
    SystemEvent,
    TimeRange,
    datetime_parser,
    generate_id,
)

__all__ = [
    # Checkpoint models
    "Checkpoint",
    "CheckpointCompression",
    "CheckpointManager",
    "CheckpointMetadata",
    "CheckpointPolicy",
    "CheckpointStatus",
    "CheckpointStorageType",
    "CheckpointType",
    
    # Resource forecast models
    "ForecastAccuracy",
    "ForecastPeriod",
    "ResourceForecast",
    "ResourceProjection",
    "ResourceUsagePattern",
    "ResourceUtilizationHistory",
    "UtilizationDataPoint",
    
    # Scenario models
    "ComparisonResult",
    "ResourceAllocation",
    "ResearchObjective",
    "Scenario",
    "ScenarioEvaluationResult",
    "ScenarioStatus",
    "ScientificMetric",
    
    # Simulation models
    "ClusterStatus",
    "ComputeNode",
    "ExtendedNodeStatus",
    "NodeStatus",
    "NodeType",
    "ResourceRequirement",
    "ResourceType",
    "Simulation",
    "SimulationPriority",
    "SimulationStage",
    "SimulationStageStatus",
    "SimulationStatus",
    
    # Common library models (re-exported for unified use)
    "BaseJob",
    "BaseNode",
    "JobStatus",
    "Priority",
    
    # Utility models
    "DateTimeEncoder",
    "PerformanceMetric",
    "Result",
    "SystemEvent",
    "TimeRange",
    "datetime_parser",
    "generate_id",
]