"""Pipeline template persistence.

A template is just a serialized :class:`~engine.graph.PipelineGraph` stored as JSON
under the configured ``templates_dir`` (defaults to ``templates/``). The same JSON
is what the React Flow editor loads and saves.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from engine.graph import PipelineGraph

log = logging.getLogger(__name__)

DEFAULT_TEMPLATES_DIR = "templates"
TEMPLATE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _templates_dir(templates_dir: Optional[str]) -> str:
    path = templates_dir or DEFAULT_TEMPLATES_DIR
    os.makedirs(path, exist_ok=True)
    return path


def template_path(template_id: str, templates_dir: Optional[str] = None) -> str:
    if not isinstance(template_id, str) or not TEMPLATE_ID_PATTERN.fullmatch(template_id):
        raise ValueError("Template id may contain only letters, numbers, hyphens, and underscores")
    return os.path.join(_templates_dir(templates_dir), f"{template_id}.json")


def save_template(
    graph: PipelineGraph, templates_dir: Optional[str] = None
) -> str:
    """Write ``graph`` to ``<templates_dir>/<graph.id>.json``. Returns the path."""
    path = template_path(graph.id, templates_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph.to_dict(), f, indent=2, ensure_ascii=False)
    log.info("Saved template %s -> %s", graph.name, path)
    return path


def load_template(
    id_or_path: str, templates_dir: Optional[str] = None
) -> PipelineGraph:
    """Load a template by id (within ``templates_dir``) or by direct file path."""
    if templates_dir is None and os.path.isfile(id_or_path):
        path = id_or_path
    else:
        path = template_path(id_or_path, templates_dir)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return PipelineGraph.from_dict(data)


def list_templates(templates_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return ``{id, name, path, nodes}`` summaries for every stored template."""
    directory = _templates_dir(templates_dir)
    out: List[Dict[str, Any]] = []
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(directory, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            out.append(
                {
                    "id": data.get("id", fname[:-5]),
                    "name": data.get("name", fname[:-5]),
                    "path": path,
                    "nodes": len(data.get("nodes", [])),
                }
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Skipping unreadable template %s: %s", fname, exc)
    return out


def delete_template(template_id: str, templates_dir: Optional[str] = None) -> bool:
    path = template_path(template_id, templates_dir)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


__all__ = [
    "save_template",
    "load_template",
    "list_templates",
    "delete_template",
    "template_path",
    "DEFAULT_TEMPLATES_DIR",
    "TEMPLATE_ID_PATTERN",
]
