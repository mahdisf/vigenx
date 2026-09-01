import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.graph import GraphEdge, GraphNode, PipelineGraph
from engine.templates import (
    delete_template,
    list_templates,
    load_template,
    save_template,
    template_path,
)


def _graph():
    return PipelineGraph(
        id="tmpl1",
        name="Demo Template",
        nodes=[
            GraphNode("s", "source", {"source": "in.mp4", "source_type": "local"},
                      position={"x": 0, "y": 0}),
            GraphNode("e", "export", {"crf": 20}, position={"x": 300, "y": 0}),
        ],
        edges=[GraphEdge("s", "media", "e", "media")],
    )


def test_save_and_load_round_trip(tmp_path):
    g = _graph()
    path = save_template(g, str(tmp_path))
    assert os.path.isfile(path)
    loaded = load_template("tmpl1", str(tmp_path))
    assert loaded.to_dict() == g.to_dict()


def test_load_by_direct_path(tmp_path):
    g = _graph()
    path = save_template(g, str(tmp_path))
    loaded = load_template(path)
    assert loaded.name == "Demo Template"
    assert len(loaded.nodes) == 2


def test_list_templates(tmp_path):
    save_template(_graph(), str(tmp_path))
    items = list_templates(str(tmp_path))
    assert len(items) == 1
    assert items[0]["id"] == "tmpl1"
    assert items[0]["nodes"] == 2


def test_delete_template(tmp_path):
    save_template(_graph(), str(tmp_path))
    assert delete_template("tmpl1", str(tmp_path)) is True
    assert delete_template("tmpl1", str(tmp_path)) is False
    assert list_templates(str(tmp_path)) == []


@pytest.mark.parametrize("template_id", ["../outside", "nested/name", "bad.json", "white space"])
def test_template_id_rejects_path_traversal(template_id, tmp_path):
    with pytest.raises(ValueError):
        template_path(template_id, str(tmp_path))
