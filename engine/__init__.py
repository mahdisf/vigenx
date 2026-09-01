"""ViGenX processing engine.

A data-driven DAG of reusable blocks. The fixed pipelines of the old
Content-Regenerator are expressed as graphs assembled from blocks that wrap the
existing ``core/`` utilities.

Public surface:
    from engine import (
        PipelineBlock, ParamSpec, PortSpec,
        register_block, get_block, all_blocks, block_schemas, load_builtin_blocks,
        PipelineGraph, GraphNode, GraphEdge, GraphValidationError,
        GraphExecutor, ExecutionContext,
    )
"""
from __future__ import annotations

from engine.block import ParamSpec, PipelineBlock, PortSpec
from engine.context import ExecutionContext
from engine.executor import GraphExecutor, NodeExecutionError
from engine.graph import GraphEdge, GraphNode, GraphValidationError, PipelineGraph
from engine.registry import (
    all_blocks,
    block_schemas,
    get_block,
    load_builtin_blocks,
    register_block,
)
from engine.planner import WorkflowPlan, WorkflowPlanner, WorkflowPlanningError

__all__ = [
    "ParamSpec",
    "PipelineBlock",
    "PortSpec",
    "ExecutionContext",
    "GraphExecutor",
    "NodeExecutionError",
    "GraphEdge",
    "GraphNode",
    "GraphValidationError",
    "PipelineGraph",
    "all_blocks",
    "block_schemas",
    "get_block",
    "load_builtin_blocks",
    "register_block",
    "WorkflowPlan",
    "WorkflowPlanner",
    "WorkflowPlanningError",
]
