import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.block import ParamSpec, PipelineBlock, PortSpec
from engine.graph import GraphEdge, GraphNode, GraphValidationError, PipelineGraph
from engine.ports import AUDIO, MEDIA
from engine.registry import register_block


# --- stub blocks (typed ports) -------------------------------------------------
@register_block
class _GProducer(PipelineBlock):
    type_id = "g_producer"
    title = "G Producer"
    inputs = []
    outputs = [PortSpec("out", MEDIA)]
    params = [ParamSpec("seed", "int", 0)]

    def process(self, ctx, inputs):
        return {"out": object()}


@register_block
class _GConsumer(PipelineBlock):
    type_id = "g_consumer"
    title = "G Consumer"
    inputs = [PortSpec("in", MEDIA)]
    outputs = [PortSpec("out", MEDIA)]
    params = []

    def process(self, ctx, inputs):
        return {"out": inputs.get("in")}


@register_block
class _GAudioConsumer(PipelineBlock):
    type_id = "g_audio_consumer"
    title = "G Audio Consumer"
    inputs = [PortSpec("in", AUDIO)]
    outputs = [PortSpec("out", AUDIO)]
    params = []

    def process(self, ctx, inputs):
        return {"out": inputs.get("in")}


def _edge(a, b, sp="out", tp="in"):
    return GraphEdge(source=a, source_port=sp, target=b, target_port=tp)


def _valid_graph():
    return PipelineGraph(
        nodes=[
            GraphNode("p", "g_producer"),
            GraphNode("c", "g_consumer"),
        ],
        edges=[_edge("p", "c")],
    )


def test_valid_graph_passes():
    g = _valid_graph()
    g.validate()  # should not raise
    assert g.topological_order() == ["p", "c"]


def test_terminal_nodes():
    g = _valid_graph()
    assert [n.id for n in g.terminal_nodes()] == ["c"]


def test_unknown_block_rejected():
    g = PipelineGraph(nodes=[GraphNode("x", "does_not_exist")], edges=[])
    with pytest.raises(GraphValidationError):
        g.validate()


def test_missing_required_input_rejected():
    g = PipelineGraph(nodes=[GraphNode("c", "g_consumer")], edges=[])
    with pytest.raises(GraphValidationError):
        g.validate()


def test_type_mismatch_rejected():
    g = PipelineGraph(
        nodes=[GraphNode("p", "g_producer"), GraphNode("a", "g_audio_consumer")],
        edges=[_edge("p", "a")],  # MEDIA -> AUDIO
    )
    with pytest.raises(GraphValidationError):
        g.validate()


def test_unknown_port_rejected():
    g = PipelineGraph(
        nodes=[GraphNode("p", "g_producer"), GraphNode("c", "g_consumer")],
        edges=[_edge("p", "c", sp="nope")],
    )
    with pytest.raises(GraphValidationError):
        g.validate()


def test_duplicate_input_connection_rejected():
    g = PipelineGraph(
        nodes=[
            GraphNode("p1", "g_producer"),
            GraphNode("p2", "g_producer"),
            GraphNode("c", "g_consumer"),
        ],
        edges=[_edge("p1", "c"), _edge("p2", "c")],
    )
    with pytest.raises(GraphValidationError):
        g.validate()


def test_cycle_detected():
    g = PipelineGraph(
        nodes=[GraphNode("a", "g_consumer"), GraphNode("b", "g_consumer")],
        edges=[_edge("a", "b"), _edge("b", "a")],
    )
    with pytest.raises(GraphValidationError):
        g.topological_order()


def test_duplicate_node_ids_rejected():
    g = PipelineGraph(
        nodes=[GraphNode("dup", "g_producer"), GraphNode("dup", "g_producer")],
        edges=[],
    )
    with pytest.raises(GraphValidationError):
        g.topological_order()


def test_ancestors_chain():
    g = PipelineGraph(
        nodes=[
            GraphNode("p", "g_producer"),
            GraphNode("c1", "g_consumer"),
            GraphNode("c2", "g_consumer"),
        ],
        edges=[_edge("p", "c1"), _edge("c1", "c2")],
    )
    assert g.ancestors("c2") == ["p", "c1", "c2"]
    assert g.ancestors("c1") == ["p", "c1"]


def test_round_trip_dict():
    g = _valid_graph()
    g.name = "Round Trip"
    restored = PipelineGraph.from_dict(g.to_dict())
    assert restored.to_dict() == g.to_dict()
