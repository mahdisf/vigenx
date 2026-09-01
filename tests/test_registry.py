import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.block import ParamSpec, PipelineBlock, PortSpec
from engine.ports import MEDIA
from engine.registry import (
    all_blocks,
    block_schemas,
    clear_registry,
    get_block,
    load_builtin_blocks,
    load_plugins,
    plugin_errors,
    register_block,
)
import engine.registry as registry


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


def test_param_coercion_enforces_choices_and_ranges():
    mode = ParamSpec("mode", "enum", "a", choices=["a", "b"])
    level = ParamSpec("level", "int", 3, min=0, max=10)
    ratio = ParamSpec("ratio", "float", 0.5, min=0.0, max=1.0)

    assert mode.coerce("not-a-choice") == "a"
    assert level.coerce(99) == 10
    assert level.coerce(-2) == 0
    assert ratio.coerce("1.7") == 1.0


def test_all_blocks_includes_registered():
    ids = {c.type_id for c in all_blocks()}
    assert "r_demo" in ids
    assert "source" in ids


def test_clear_registry_allows_builtin_rediscovery():
    load_builtin_blocks()

    clear_registry()

    try:
        assert get_block("source").type_id == "source"
    finally:
        register_block(_RDemo)


class _FakeDistribution:
    name = "vigenx-example-plugin"
    version = "1.2.3"


class _FakeEntryPoint:
    name = "example"
    dist = _FakeDistribution()

    def __init__(self, value):
        self.value = value

    def load(self):
        return self.value


class _FakeEntryPoints(list):
    def select(self, **_kwargs):
        return self


def test_plugin_entry_point_is_loaded_with_origin(monkeypatch):
    class _PluginBlock(PipelineBlock):
        type_id = "test_plugin_block"
        title = "Plugin Block"

        def process(self, ctx, inputs):
            return {}

    monkeypatch.setattr(registry, "_PLUGINS_LOADED", False)
    monkeypatch.setattr(registry, "_PLUGIN_ERRORS", [])
    monkeypatch.setattr(
        registry.metadata,
        "entry_points",
        lambda: _FakeEntryPoints([_FakeEntryPoint(_PluginBlock)]),
    )

    load_plugins()

    assert get_block("test_plugin_block") is _PluginBlock
    schema = next(item for item in block_schemas() if item["type_id"] == "test_plugin_block")
    assert schema["origin"] == "vigenx-example-plugin@1.2.3:example"


def test_plugin_cannot_replace_registered_block(monkeypatch):
    class _Collision(PipelineBlock):
        type_id = "r_demo"

        def process(self, ctx, inputs):
            return {}

    monkeypatch.setattr(registry, "_PLUGINS_LOADED", False)
    monkeypatch.setattr(registry, "_PLUGIN_ERRORS", [])
    monkeypatch.setattr(
        registry.metadata,
        "entry_points",
        lambda: _FakeEntryPoints([_FakeEntryPoint(_Collision)]),
    )

    load_plugins()

    assert get_block("r_demo") is _RDemo
    assert "already registered" in plugin_errors()[0]
