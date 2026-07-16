"""Block registry.

Blocks register themselves with :func:`register_block` (usually via the
decorator). :func:`load_builtin_blocks` imports :mod:`engine.blocks` once so all
built-in blocks are available; callers that only need the registry populated can
depend on it being idempotent.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Type

from engine.block import PipelineBlock

log = logging.getLogger(__name__)

_REGISTRY: Dict[str, Type[PipelineBlock]] = {}
_BUILTINS_LOADED = False


def register_block(cls: Type[PipelineBlock]) -> Type[PipelineBlock]:
    """Class decorator: register a block by its ``type_id``."""
    type_id = getattr(cls, "type_id", "")
    if not type_id:
        raise ValueError(f"{cls.__name__} must define a non-empty type_id")
    if type_id in _REGISTRY and _REGISTRY[type_id] is not cls:
        log.warning("Block type_id %r re-registered (overriding)", type_id)
    _REGISTRY[type_id] = cls
    return cls


def get_block(type_id: str) -> Type[PipelineBlock]:
    """Look up a registered block class by id (loads built-ins on demand)."""
    if type_id not in _REGISTRY:
        load_builtin_blocks()
    try:
        return _REGISTRY[type_id]
    except KeyError:
        raise KeyError(f"No block registered for type_id {type_id!r}") from None


def all_blocks() -> List[Type[PipelineBlock]]:
    load_builtin_blocks()
    return list(_REGISTRY.values())


def block_schemas() -> List[dict]:
    """Schema for every registered block, sorted by category then title."""
    blocks = sorted(
        all_blocks(),
        key=lambda c: (c.category, c.title or c.type_id),
    )
    return [c.schema() for c in blocks]


def load_builtin_blocks() -> None:
    """Import the built-in block package so registration side effects fire."""
    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return
    _BUILTINS_LOADED = True
    try:
        import engine.blocks  # noqa: F401  (import triggers @register_block)
    except Exception as exc:  # pragma: no cover - surfaced as a warning
        log.warning("Failed to import built-in blocks: %s", exc)


def clear_registry() -> None:
    """Test helper: drop all registrations and reset the builtins flag."""
    global _BUILTINS_LOADED
    _REGISTRY.clear()
    _BUILTINS_LOADED = False


__all__ = [
    "register_block",
    "get_block",
    "all_blocks",
    "block_schemas",
    "load_builtin_blocks",
    "clear_registry",
]
