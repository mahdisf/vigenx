import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import AppConfig
from engine.block import (
    PREVIEW_FRAME,
    ParamSpec,
    PipelineBlock,
    PortSpec,
)
from engine.executor import GraphExecutor
from engine.graph import GraphEdge, GraphNode, PipelineGraph
from engine.ports import ANY, Text
from engine.registry import register_block

# Track how many times each block's process() runs, to prove memoization.
CALLS: dict = {}


def _count(name):
    CALLS[name] = CALLS.get(name, 0) + 1


@register_block
class _XSource(PipelineBlock):
    type_id = "x_src"
    title = "X Source"
    inputs = []
    outputs = [PortSpec("out", ANY)]
    params = [ParamSpec("seed", "str", "S")]

    def process(self, ctx, inputs):
        _count("x_src")
        return {"out": Text(self.p("seed"))}


@register_block
class _XStyle(PipelineBlock):
    """A frame-style block that overrides preview() to composite cheaply."""

    type_id = "x_style"
    title = "X Style"
    preview_kind = PREVIEW_FRAME
    inputs = [PortSpec("in", ANY)]
    outputs = [PortSpec("out", ANY)]
    params = [ParamSpec("color", "color", "#fff")]

    def process(self, ctx, inputs):
        _count("x_style")
        base = inputs.get("in")
        val = base.value if isinstance(base, Text) else str(base)
        return {"out": Text(f"{val}|{self.p('color')}")}

    def preview(self, ctx, inputs, t):
        base = inputs.get("in")
        val = base.value if isinstance(base, Text) else str(base)
        return Text(f"{val}|{self.p('color')}|t={t}")


def _graph():
    return PipelineGraph(
        nodes=[GraphNode("s", "x_src", {"seed": "hello"}),
               GraphNode("st", "x_style", {"color": "#f00"})],
        edges=[GraphEdge("s", "out", "st", "in")],
    )


def setup_function(_):
    CALLS.clear()


def test_full_run_executes_all_nodes():
    ex = GraphExecutor(_graph(), AppConfig())
    result = ex.run()
    assert CALLS == {"x_src": 1, "x_style": 1}
    assert result.node_outputs["st"]["out"].value == "hello|#f00"
    assert "st" in result.terminal_outputs


def test_run_param_overrides_do_not_mutate_graph():
    g = _graph()
    ex = GraphExecutor(g, AppConfig())
    ex.run(param_overrides={"st": {"color": "#0f0"}})
    # original node params untouched
    assert g.node("st").params["color"] == "#f00"


def test_preview_calls_preview_not_process_on_target():
    ex = GraphExecutor(_graph(), AppConfig())
    out = ex.preview_at("st", t=2.0, param_overrides={"st": {"color": "#abc"}})
    assert isinstance(out, Text)
    assert out.value == "hello|#abc|t=2.0"
    # upstream ran once; target used preview(), so its process() never ran
    assert CALLS.get("x_src") == 1
    assert CALLS.get("x_style") is None


def test_preview_memoizes_ancestors_across_param_tweaks():
    ex = GraphExecutor(_graph(), AppConfig())
    ex.preview_at("st", t=1.0, param_overrides={"st": {"color": "#111"}})
    ex.preview_at("st", t=1.0, param_overrides={"st": {"color": "#222"}})
    ex.preview_at("st", t=1.0, param_overrides={"st": {"color": "#333"}})
    # source resolved once and reused for every subsequent tweak
    assert CALLS.get("x_src") == 1


def test_preview_recomputes_when_upstream_param_changes():
    ex = GraphExecutor(_graph(), AppConfig())
    ex.preview_at("st", param_overrides={"s": {"seed": "a"}})
    ex.preview_at("st", param_overrides={"s": {"seed": "b"}})
    # different upstream params -> two distinct cache keys -> two runs
    assert CALLS.get("x_src") == 2


def test_draft_runs_full_graph_in_preview_mode():
    ex = GraphExecutor(_graph(), AppConfig())
    result = ex.draft()
    assert result.node_outputs["st"]["out"].value == "hello|#f00"


def test_preview_missing_required_input_gives_friendly_error():
    import pytest

    # x_style requires an 'in' input; previewing it with nothing connected
    # should raise a clear, actionable message (not an AttributeError on None).
    g = PipelineGraph(nodes=[GraphNode("st", "x_style", {"color": "#f00"})], edges=[])
    ex = GraphExecutor(g, AppConfig())
    with pytest.raises(ValueError) as exc:
        ex.preview_at("st", t=1.0)
    assert "not connected" in str(exc.value)
