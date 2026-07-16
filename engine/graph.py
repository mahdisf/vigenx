"""The pipeline graph: a validated, serializable DAG of block nodes.

A :class:`PipelineGraph` is the canonical representation a template stores and the
React Flow editor reads/writes. Validation rejects unknown blocks, cycles, port
type mismatches, and unsatisfied required inputs *before* a run starts.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from engine.ports import types_compatible
from engine.registry import get_block


class GraphValidationError(Exception):
    """Raised when a graph is structurally or type invalid."""


@dataclass
class GraphNode:
    id: str
    type_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=dict)  # {x, y} for the UI

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type_id": self.type_id,
            "params": self.params,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GraphNode":
        return cls(
            id=d["id"],
            type_id=d["type_id"],
            params=dict(d.get("params") or {}),
            position=dict(d.get("position") or {}),
        )


@dataclass
class GraphEdge:
    source: str          # source node id
    source_port: str     # source output port name
    target: str          # target node id
    target_port: str     # target input port name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "source_port": self.source_port,
            "target": self.target,
            "target_port": self.target_port,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GraphEdge":
        return cls(
            source=d["source"],
            source_port=d.get("source_port", "out"),
            target=d["target"],
            target_port=d.get("target_port", "in"),
        )


@dataclass
class PipelineGraph:
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Untitled"
    meta: Dict[str, Any] = field(default_factory=dict)

    # -- lookups ---------------------------------------------------------------
    def node(self, node_id: str) -> GraphNode:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(f"No node with id {node_id!r}")

    def node_ids(self) -> List[str]:
        return [n.id for n in self.nodes]

    def incoming(self, node_id: str) -> List[GraphEdge]:
        return [e for e in self.edges if e.target == node_id]

    def outgoing(self, node_id: str) -> List[GraphEdge]:
        return [e for e in self.edges if e.source == node_id]

    def terminal_nodes(self) -> List[GraphNode]:
        """Nodes with no outgoing edges (e.g. export nodes)."""
        with_out = {e.source for e in self.edges}
        return [n for n in self.nodes if n.id not in with_out]

    # -- serialization ---------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "meta": self.meta,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PipelineGraph":
        g = cls(
            id=d.get("id") or str(uuid.uuid4())[:8],
            name=d.get("name", "Untitled"),
            meta=dict(d.get("meta") or {}),
            nodes=[GraphNode.from_dict(n) for n in d.get("nodes", [])],
            edges=[GraphEdge.from_dict(e) for e in d.get("edges", [])],
        )
        return g

    # -- ordering --------------------------------------------------------------
    def topological_order(self) -> List[str]:
        """Return node ids in dependency order (Kahn's algorithm).

        Raises :class:`GraphValidationError` if the graph contains a cycle.
        """
        ids = self.node_ids()
        if len(set(ids)) != len(ids):
            raise GraphValidationError("Duplicate node ids in graph")

        indeg: Dict[str, int] = {i: 0 for i in ids}
        adj: Dict[str, List[str]] = {i: [] for i in ids}
        for e in self.edges:
            if e.source not in indeg or e.target not in indeg:
                raise GraphValidationError(
                    f"Edge references unknown node: {e.source} -> {e.target}"
                )
            adj[e.source].append(e.target)
            indeg[e.target] += 1

        queue = [i for i in ids if indeg[i] == 0]
        order: List[str] = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for m in adj[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)

        if len(order) != len(ids):
            raise GraphValidationError("Graph contains a cycle")
        return order

    def ancestors(self, node_id: str) -> List[str]:
        """Topologically ordered ids of all nodes ``node_id`` depends on, plus itself."""
        order = self.topological_order()
        keep: set = {node_id}
        # walk the order in reverse, pulling in sources of edges into kept nodes
        for nid in reversed(order):
            if nid in keep:
                for e in self.incoming(nid):
                    keep.add(e.source)
        return [nid for nid in order if nid in keep]

    # -- validation ------------------------------------------------------------
    def validate(self) -> None:
        """Validate structure and port typing. Raises on the first problem."""
        if not self.nodes:
            raise GraphValidationError("Graph has no nodes")

        # 1. every node references a known block
        block_classes = {}
        for n in self.nodes:
            try:
                block_classes[n.id] = get_block(n.type_id)
            except KeyError as exc:
                raise GraphValidationError(str(exc)) from None

        # 2. acyclic (also checks edges reference known nodes)
        self.topological_order()

        # 3. each edge connects existing, type-compatible ports; one value per input
        filled_inputs: Dict[str, set] = {n.id: set() for n in self.nodes}
        for e in self.edges:
            src_cls = block_classes[e.source]
            tgt_cls = block_classes[e.target]
            src_port = src_cls.output_spec(e.source_port)
            tgt_port = tgt_cls.input_spec(e.target_port)
            if src_port is None:
                raise GraphValidationError(
                    f"{e.source} ({src_cls.type_id}) has no output port "
                    f"{e.source_port!r}"
                )
            if tgt_port is None:
                raise GraphValidationError(
                    f"{e.target} ({tgt_cls.type_id}) has no input port "
                    f"{e.target_port!r}"
                )
            if not types_compatible(src_port.type, tgt_port.type):
                raise GraphValidationError(
                    f"Type mismatch on edge {e.source}.{e.source_port} "
                    f"({src_port.type}) -> {e.target}.{e.target_port} "
                    f"({tgt_port.type})"
                )
            if e.target_port in filled_inputs[e.target]:
                raise GraphValidationError(
                    f"Input {e.target}.{e.target_port} is connected more than once"
                )
            filled_inputs[e.target].add(e.target_port)

        # 4. every required input is satisfied
        for n in self.nodes:
            cls = block_classes[n.id]
            for port in cls.inputs:
                if port.required and port.name not in filled_inputs[n.id]:
                    raise GraphValidationError(
                        f"Required input {n.id}.{port.name} ({cls.type_id}) "
                        f"is not connected"
                    )


__all__ = [
    "GraphValidationError",
    "GraphNode",
    "GraphEdge",
    "PipelineGraph",
]
