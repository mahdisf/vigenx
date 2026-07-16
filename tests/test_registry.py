import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.block import ParamSpec, PipelineBlock, PortSpec
from engine.ports import MEDIA
from engine.registry import (
    all_blocks,
    block_schemas,
    get_block,
    load_builtin_blocks,
    register_block,
)


@register_block
class _RDemo(PipelineBlock):
    type_id = "r_demo"
    title = "R Demo"
    category = "testing"
    inputs = [PortSpec("in", MEDIA)]
    outputs = [PortSpec("out", MEDIA)]
    params = [
        ParamSpec("level", "int", 3, min=0, max=10),
        ParamSpec("mode", "enum", "a", choices=["a", "b"]),
    ]

    def process(self, ctx, inputs):
        return {"out": inputs.get("in")}


def test_register_requires_type_id():
    with pytest.raises(ValueError):
        @register_block
        class _NoId(PipelineBlock):  # noqa: N801
            def process(self, ctx, inputs):
                return {}


def test_get_block_round_trip():
    assert get_block("r_demo") is _RDemo


def test_builtin_source_block_discovered():
    load_builtin_blocks()
    src = get_block("source")
    assert src.type_id == "source"
    assert any(p.name == "media" for p in src.outputs)


def test_block_schemas_shape():
    schemas = {s["type_id"]: s for s in block_schemas()}
    assert "r_demo" in schemas
    s = schemas["r_demo"]
    assert s["category"] == "testing"
    assert [p["name"] for p in s["inputs"]] == ["in"]
    assert [p["name"] for p in s["outputs"]] == ["out"]
    names = {p["name"]: p for p in s["params"]}
    assert names["level"]["min"] == 0 and names["level"]["max"] == 10
    assert names["mode"]["choices"] == ["a", "b"]


def test_enum_param_requires_choices():
    with pytest.raises(ValueError):
        ParamSpec("bad", "enum", "x")


def test_all_blocks_includes_registered():
    ids = {c.type_id for c in all_blocks()}
    assert "r_demo" in ids
    assert "source" in ids
