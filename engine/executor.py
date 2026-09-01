"""Graph executor: runs a :class:`~engine.graph.PipelineGraph` to completion and
serves the WYSIWYG preview / draft paths.

* :meth:`GraphExecutor.run` executes every node in topological order, wiring each
  node's inputs from its upstream nodes' outputs, emitting per-node progress.
* :meth:`GraphExecutor.preview_at` resolves only a node's ancestor chain (memoized
  by a params hash so editing one block doesn't recompute its ancestors) and calls
  the target block's ``preview()`` for sub-second feedback.
* :meth:`GraphExecutor.draft` runs the whole graph in preview mode for a fast,
  low-res, at-a-glance composite.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import AppConfig
from engine.context import ExecutionContext, ProgressCallback
from engine.graph import PipelineGraph
from engine.preview import params_hash
from engine.ports import ImageRef, MediaRef
from engine.registry import get_block

log = logging.getLogger(__name__)


class NodeExecutionError(Exception):
    """Wraps an exception raised while executing a specific node."""

    def __init__(self, node_id: str, type_id: str, cause: BaseException) -> None:
        self.node_id = node_id
        self.type_id = type_id
        self.cause = cause
        super().__init__(f"Node {node_id!r} ({type_id}) failed: {cause}")


@dataclass
class RunResult:
    node_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    terminal_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def media_paths(self) -> List[str]:
        """Filesystem paths of all media/image payloads from terminal nodes.

        A payload may fan out to several files (e.g. Export Clips writes one MP4 per
        moment) by listing them in ``MediaRef.meta['clips']``; those are expanded here.
        """
        paths: List[str] = []
        for outputs in self.terminal_outputs.values():
            for payload in outputs.values():
                if isinstance(payload, MediaRef):
                    clips = (payload.meta or {}).get("clips")
                    if clips:
                        paths.extend(clips)
                    elif payload.path:
                        paths.append(payload.path)
                elif isinstance(payload, ImageRef):
                    paths.append(payload.path)
        return paths

    def artifact_paths(self, key: str) -> List[str]:
        """Collect sidecar paths stored on terminal media payloads."""
        paths: List[str] = []
        singular = key[:-1] if key.endswith("s") else key
        for outputs in self.terminal_outputs.values():
            for payload in outputs.values():
                if not isinstance(payload, MediaRef):
                    continue
                value = (payload.meta or {}).get(key)
                if value is None:
                    value = (payload.meta or {}).get(singular)
                if isinstance(value, str) and value:
                    paths.append(value)
                elif isinstance(value, list):
                    paths.extend(str(path) for path in value if path)
        return paths


class GraphExecutor:
    def __init__(
        self,
        graph: PipelineGraph,
        config: AppConfig,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        self.graph = graph
        self.config = config
        self.progress_cb = progress_cb
        # persists across preview_at() calls so param tweaks reuse ancestors
        self._preview_cache: Dict[str, Dict[str, Any]] = {}

    # -- full run --------------------------------------------------------------
    def run(
        self,
        work_dir: Optional[str] = None,
        param_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> RunResult:
        """Execute the whole graph. ``param_overrides`` lets a batch caller inject
        per-node values (e.g. the source path for each selected media) without
        mutating the stored template."""
        self.graph.validate()
        overrides = param_overrides or {}
        ctx = self._make_context(work_dir, preview=False)

        order = self.graph.topological_order()
        total = len(order)
        node_outputs: Dict[str, Dict[str, Any]] = {}

        for i, node_id in enumerate(order):
            node = self.graph.node(node_id)
            params = {**node.params, **overrides.get(node_id, {})}
            block = get_block(node.type_id)(params)
            ctx.current_node = node_id
            ctx.node_progress(node_id, f"Running {block.title or node.type_id}", i / total)
            inputs = self._gather_inputs(node_id, node_outputs)
            try:
                node_outputs[node_id] = block.process(ctx, inputs) or {}
            except Exception as exc:  # noqa: BLE001 - re-wrapped with node identity
                log.exception("Node %s (%s) failed", node_id, node.type_id)
                raise NodeExecutionError(node_id, node.type_id, exc) from exc
            ctx.node_progress(node_id, f"Done {block.title or node.type_id}", (i + 1) / total)

        terminal = {n.id: node_outputs.get(n.id, {}) for n in self.graph.terminal_nodes()}
        return RunResult(node_outputs=node_outputs, terminal_outputs=terminal)

    # -- preview ---------------------------------------------------------------
    def preview_at(
        self,
        node_id: str,
        t: float = 1.0,
        param_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        work_dir: Optional[str] = None,
    ) -> Any:
        """Return a fast preview payload (frame/clip) for ``node_id`` at time ``t``.

        Ancestor nodes are executed via the memoizing resolver, so re-calling after
        changing only ``node_id``'s params reuses the cached upstream results.
        """
        overrides = param_overrides or {}
        ctx = self._make_context(work_dir, preview=True)

        node = self.graph.node(node_id)
        params = {**node.params, **overrides.get(node_id, {})}
        block_cls = get_block(node.type_id)
        inputs: Dict[str, Any] = {}
        for e in self.graph.incoming(node_id):
            _, up_outputs = self._resolve_preview(ctx, e.source, overrides)
            inputs[e.target_port] = up_outputs.get(e.source_port)

        # Friendly guard: a missing/empty required input is the #1 cause of
        # preview crashes (e.g. previewing a node before wiring a Source).
        for port in block_cls.inputs:
            if port.required and inputs.get(port.name) is None:
                raise ValueError(
                    f"Cannot preview '{block_cls.title}': its '{port.label}' input is "
                    f"not connected. Wire a Source upstream (and set its file/URL)."
                )

        return block_cls(params).preview(ctx, inputs, t)

    def _resolve_preview(
        self,
        ctx: ExecutionContext,
        node_id: str,
        overrides: Dict[str, Dict[str, Any]],
    ) -> tuple[str, Dict[str, Any]]:
        """Recursively produce ``node_id``'s outputs, memoized by a params hash."""
        node = self.graph.node(node_id)
        params = {**node.params, **overrides.get(node_id, {})}

        input_payloads: Dict[str, Any] = {}
        upstream_keys: List[Any] = []
        for e in self.graph.incoming(node_id):
            up_key, up_outputs = self._resolve_preview(ctx, e.source, overrides)
            upstream_keys.append((e.target_port, e.source_port, up_key))
            input_payloads[e.target_port] = up_outputs.get(e.source_port)

        key = params_hash(node.type_id, params, sorted(map(str, upstream_keys)))
        if key in self._preview_cache:
            return key, self._preview_cache[key]

        block = get_block(node.type_id)(params)
        ctx.current_node = node_id
        outputs = block.process(ctx, input_payloads) or {}
        self._preview_cache[key] = outputs
        return key, outputs

    def clear_preview_cache(self) -> None:
        self._preview_cache.clear()

    # -- draft -----------------------------------------------------------------
    def draft(
        self,
        node_id: Optional[str] = None,
        work_dir: Optional[str] = None,
        param_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> RunResult:
        """Run the graph (or the ancestors of ``node_id``) in preview mode.

        Media blocks honour ``ctx.preview`` to downscale/shorten, so this yields a
        fast, low-res composite without a full export.
        """
        self.graph.validate()
        overrides = param_overrides or {}
        ctx = self._make_context(work_dir, preview=True)

        if node_id is not None:
            order = self.graph.ancestors(node_id)
        else:
            order = self.graph.topological_order()

        node_outputs: Dict[str, Dict[str, Any]] = {}
        total = len(order)
        for i, nid in enumerate(order):
            node = self.graph.node(nid)
            params = {**node.params, **overrides.get(nid, {})}
            block = get_block(node.type_id)(params)
            ctx.current_node = nid
            ctx.node_progress(nid, f"Draft {block.title or node.type_id}", i / total)
            inputs = self._gather_inputs(nid, node_outputs)
            node_outputs[nid] = block.process(ctx, inputs) or {}

        if node_id is not None:
            terminal = {node_id: node_outputs.get(node_id, {})}
        else:
            terminal = {n.id: node_outputs.get(n.id, {}) for n in self.graph.terminal_nodes()}
        return RunResult(node_outputs=node_outputs, terminal_outputs=terminal)

    # -- helpers ---------------------------------------------------------------
    def _gather_inputs(
        self, node_id: str, node_outputs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        inputs: Dict[str, Any] = {}
        for e in self.graph.incoming(node_id):
            up = node_outputs.get(e.source, {})
            if e.source_port not in up:
                raise NodeExecutionError(
                    node_id,
                    self.graph.node(node_id).type_id,
                    KeyError(
                        f"upstream {e.source}.{e.source_port} produced no output"
                    ),
                )
            inputs[e.target_port] = up[e.source_port]
        return inputs

    def _make_context(self, work_dir: Optional[str], preview: bool) -> ExecutionContext:
        kwargs: Dict[str, Any] = {"config": self.config, "preview": preview}
        if work_dir:
            kwargs["work_dir"] = work_dir
        if self.progress_cb is not None:
            kwargs["progress_cb"] = self.progress_cb
        return ExecutionContext(**kwargs)


__all__ = ["GraphExecutor", "RunResult", "NodeExecutionError"]
