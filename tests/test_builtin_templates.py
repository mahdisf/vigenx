"""The three seeded templates must reference real blocks and form valid DAGs."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import engine
from engine.templates import load_template

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
BUILTINS = ["general", "speaker", "game"]


@pytest.mark.parametrize("template_id", BUILTINS)
def test_builtin_template_validates(template_id):
    engine.load_builtin_blocks()
    graph = load_template(template_id, TEMPLATES_DIR)
    graph.validate()  # raises on unknown block / cycle / type mismatch / missing input
    # every template ends in a terminal node
    assert graph.terminal_nodes()
    # topological order covers all nodes
    assert len(graph.topological_order()) == len(graph.nodes)


def test_all_referenced_block_types_exist():
    engine.load_builtin_blocks()
    known = {s["type_id"] for s in engine.block_schemas()}
    for template_id in BUILTINS:
        graph = load_template(template_id, TEMPLATES_DIR)
        for node in graph.nodes:
            assert node.type_id in known, f"{template_id}: unknown block {node.type_id}"
