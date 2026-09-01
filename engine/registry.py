"""Block registry.

Blocks register themselves with :func:`register_block` (usually via the
decorator). :func:`load_builtin_blocks` imports :mod:`engine.blocks` once so all
built-in blocks are available; callers that only need the registry populated can
depend on it being idempotent.
"""
from __future__ import annotations

from importlib import metadata
import logging
import sys
from typing import Dict, List, Type

from engine.block import PipelineBlock

log = logging.getLogger(__name__)

PLUGIN_ENTRY_POINT_GROUP = "vigenx.blocks"

_REGISTRY: Dict[str, Type[PipelineBlock]] = {}
_ORIGINS: Dict[str, str] = {}
_PLUGIN_ERRORS: List[str] = []
_BUILTINS_LOADED = False
_PLUGINS_LOADED = False
_ACTIVE_ORIGIN: str | None = None


def register_block(cls: Type[PipelineBlock]) -> Type[PipelineBlock]:
    """Register a block class without allowing silent type-id replacement."""
    type_id = getattr(cls, "type_id", "")
    if not type_id:
        raise ValueError(f"{cls.__name__} must define a non-empty type_id")
    if type_id in _REGISTRY and _REGISTRY[type_id] is not cls:
        raise ValueError(
            f"Block type_id {type_id!r} is already registered by "
            f"{_ORIGINS.get(type_id, _REGISTRY[type_id].__module__)}"
        )
    _REGISTRY[type_id] = cls
    _ORIGINS[type_id] = _ACTIVE_ORIGIN or (
        "builtin" if cls.__module__.startswith("engine.blocks.") else "local"
    )
    return cls


def get_block(type_id: str) -> Type[PipelineBlock]:
    """Look up a registered block after built-in and plugin discovery."""
    if type_id not in _REGISTRY:
        load_builtin_blocks()
        load_plugins()
    try:
        return _REGISTRY[type_id]
    except KeyError:
        raise KeyError(f"No block registered for type_id {type_id!r}") from None


def all_blocks() -> List[Type[PipelineBlock]]:
    load_builtin_blocks()
    load_plugins()
    return list(_REGISTRY.values())


def block_schemas() -> List[dict]:
    """Return sorted editor schemas including each block's origin."""
    blocks = sorted(
        all_blocks(),
        key=lambda cls: (cls.category, cls.title or cls.type_id),
    )
    schemas = []
    for cls in blocks:
        schema = cls.schema()
        schema["origin"] = _ORIGINS.get(cls.type_id, "unknown")
        schemas.append(schema)
    return schemas


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


def _available_entry_points():
    points = metadata.entry_points()
    if hasattr(points, "select"):
        return points.select(group=PLUGIN_ENTRY_POINT_GROUP)
    return points.get(PLUGIN_ENTRY_POINT_GROUP, ())


def load_plugins() -> None:
    """Load installed ``PipelineBlock`` classes from Python entry points."""
    global _ACTIVE_ORIGIN, _PLUGINS_LOADED
    if _PLUGINS_LOADED:
        return
    _PLUGINS_LOADED = True

    try:
        points = sorted(_available_entry_points(), key=lambda point: point.name)
    except Exception as exc:  # pragma: no cover - broken environment metadata
        message = f"Could not enumerate {PLUGIN_ENTRY_POINT_GROUP}: {exc}"
        _PLUGIN_ERRORS.append(message)
        log.warning(message)
        return

    for point in points:
        distribution = getattr(point, "dist", None)
        package = getattr(distribution, "name", None) or "third-party"
        version = getattr(distribution, "version", None)
        origin = f"{package}{'@' + version if version else ''}:{point.name}"
        previous_origin = _ACTIVE_ORIGIN
        try:
            _ACTIVE_ORIGIN = origin
            block_class = point.load()
            if not isinstance(block_class, type) or not issubclass(block_class, PipelineBlock):
                raise TypeError("entry point must resolve to a PipelineBlock class")
            register_block(block_class)
        except Exception as exc:  # noqa: BLE001 - isolate third-party failures
            message = f"Plugin {origin} was skipped: {exc}"
            _PLUGIN_ERRORS.append(message)
            log.warning(message)
        finally:
            _ACTIVE_ORIGIN = previous_origin


def plugin_errors() -> List[str]:
    """Return plugin discovery failures for diagnostics and support reports."""
    load_plugins()
    return list(_PLUGIN_ERRORS)


def clear_registry() -> None:
    """Test helper: drop registrations and discovery state."""
    global _BUILTINS_LOADED, _PLUGINS_LOADED
    _REGISTRY.clear()
    _ORIGINS.clear()
    _PLUGIN_ERRORS.clear()
    _BUILTINS_LOADED = False
    _PLUGINS_LOADED = False
    for module_name in tuple(sys.modules):
        if module_name == "engine.blocks" or module_name.startswith("engine.blocks."):
            del sys.modules[module_name]


__all__ = [
    "PLUGIN_ENTRY_POINT_GROUP",
    "register_block",
    "get_block",
    "all_blocks",
    "block_schemas",
    "load_builtin_blocks",
    "load_plugins",
    "plugin_errors",
    "clear_registry",
]
