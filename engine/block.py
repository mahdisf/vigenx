"""Block base class, parameter/port specifications, and the preview hook.

Every processing capability in ViGenX is a :class:`PipelineBlock` subclass. A
block declares its input/output ports and a list of :class:`ParamSpec` settings.
The same declarations drive (a) graph validation, (b) the JSON ``schema()`` the
React Flow palette and node inspector are generated from, and (c) the WYSIWYG
``preview()`` hook.

Blocks are thin adapters: the actual work happens in the existing ``core/``
utilities. ``process()`` runs the full effect; ``preview()`` produces a fast,
at-a-glance result (a single composited frame for overlay/style blocks, a short
low-res clip for structural blocks).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:  # avoid import cycle at runtime
    from engine.context import ExecutionContext

# preview_kind values
PREVIEW_FRAME = "frame"  # cheap: apply effect to one sampled frame
PREVIEW_CLIP = "clip"    # apply to a short low-res subclip (structural blocks)
PREVIEW_NONE = "none"    # non-visual block, no preview


# Parameter widget/value types understood by the inspector UI.
PARAM_TYPES = ("str", "int", "float", "bool", "enum", "text", "file", "folder",
               "color", "font")


@dataclass
class ParamSpec:
    """One configurable setting on a block.

    ``advanced`` params are collapsed into an "Advanced" section in the inspector.
    ``choices`` is required for ``enum``. ``min``/``max`` bound numeric widgets.
    """

    name: str
    type: str = "str"
    default: Any = None
    label: str = ""
    help: str = ""
    advanced: bool = False
    choices: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None

    def __post_init__(self) -> None:
        if self.type not in PARAM_TYPES:
            raise ValueError(f"ParamSpec {self.name!r}: unknown type {self.type!r}")
        if self.type == "enum" and not self.choices:
            raise ValueError(f"ParamSpec {self.name!r}: enum requires choices")
        if not self.label:
            self.label = self.name.replace("_", " ").title()

    def coerce(self, value: Any) -> Any:
        """Coerce an incoming value and enforce declared choices/ranges."""
        if value is None:
            return self.default
        try:
            if self.type == "int":
                value = int(value)
            if self.type == "float":
                value = float(value)
            if self.type == "bool":
                if isinstance(value, str):
                    return value.strip().lower() in ("1", "true", "yes", "on")
                return bool(value)
        except (TypeError, ValueError):
            return self.default
        if self.type in ("int", "float"):
            if self.min is not None:
                value = max(value, self.min)
            if self.max is not None:
                value = min(value, self.max)
            return int(value) if self.type == "int" else float(value)
        if self.type == "enum" and value not in (self.choices or []):
            return self.default
        return value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "default": self.default,
            "label": self.label,
            "help": self.help,
            "advanced": self.advanced,
            "choices": self.choices,
            "min": self.min,
            "max": self.max,
        }


@dataclass
class PortSpec:
    """A named, typed input or output socket on a block."""

    name: str
    type: str = "any"
    label: str = ""
    required: bool = True

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.name.replace("_", " ").title()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "label": self.label,
            "required": self.required,
        }


class PipelineBlock(abc.ABC):
    """Base class for all processing blocks.

    Subclasses set the class attributes ``type_id``, ``title``, ``category``,
    ``inputs``, ``outputs``, ``params`` and implement :meth:`process`. They may
    override :meth:`preview` and set :attr:`preview_kind` for WYSIWYG feedback.
    """

    # Identity / metadata -- set on each subclass.
    type_id: str = ""
    title: str = ""
    category: str = "general"
    description: str = ""

    # Port + parameter declarations.
    inputs: List[PortSpec] = []
    outputs: List[PortSpec] = []
    params: List[ParamSpec] = []

    # Preview behaviour.
    preview_kind: str = PREVIEW_NONE

    def __init__(self, params: Optional[Dict[str, Any]] = None) -> None:
        self.values: Dict[str, Any] = self._merge_params(params or {})

    # -- params ----------------------------------------------------------------
    @classmethod
    def _spec_map(cls) -> Dict[str, ParamSpec]:
        return {p.name: p for p in cls.params}

    @classmethod
    def _merge_params(cls, given: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for spec in cls.params:
            merged[spec.name] = spec.coerce(given.get(spec.name, spec.default))
        return merged

    def p(self, name: str, default: Any = None) -> Any:
        """Read a coerced parameter value."""
        return self.values.get(name, default)

    # -- ports -----------------------------------------------------------------
    @classmethod
    def input_spec(cls, name: str) -> Optional[PortSpec]:
        for port in cls.inputs:
            if port.name == name:
                return port
        return None

    @classmethod
    def output_spec(cls, name: str) -> Optional[PortSpec]:
        for port in cls.outputs:
            if port.name == name:
                return port
        return None

    # -- work ------------------------------------------------------------------
    @abc.abstractmethod
    def process(
        self, ctx: "ExecutionContext", inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run the block. Return a dict mapping output port name -> payload."""

    def preview(
        self, ctx: "ExecutionContext", inputs: Dict[str, Any], t: float
    ) -> Any:
        """Produce a fast, at-a-glance preview result.

        Default behaviour:
          * ``PREVIEW_CLIP`` / ``PREVIEW_FRAME`` blocks reuse :meth:`process` —
            the executor is responsible for handing in a single-frame or short
            low-res clip as the upstream ``inputs`` so this stays cheap.
          * ``PREVIEW_NONE`` blocks return their primary input unchanged.

        Overlay/style blocks should override this to composite their effect onto
        the sampled frame directly for sub-second feedback.
        """
        if self.preview_kind == PREVIEW_NONE:
            # Pass through the first available input payload.
            for port in self.inputs:
                if port.name in inputs:
                    return inputs[port.name]
            return None
        outputs = self.process(ctx, inputs)
        if not outputs:
            return None
        # Prefer a media/image output if present, else first output.
        for port in self.outputs:
            if port.name in outputs:
                return outputs[port.name]
        return next(iter(outputs.values()))

    # -- schema ----------------------------------------------------------------
    @classmethod
    def schema(cls) -> Dict[str, Any]:
        """JSON description used by the API / React Flow palette + inspector."""
        return {
            "type_id": cls.type_id,
            "title": cls.title or cls.type_id,
            "category": cls.category,
            "description": cls.description,
            "preview_kind": cls.preview_kind,
            "inputs": [p.to_dict() for p in cls.inputs],
            "outputs": [p.to_dict() for p in cls.outputs],
            "params": [p.to_dict() for p in cls.params],
        }

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<{type(self).__name__} {self.type_id!r}>"


__all__ = [
    "ParamSpec",
    "PortSpec",
    "PipelineBlock",
    "PREVIEW_FRAME",
    "PREVIEW_CLIP",
    "PREVIEW_NONE",
    "PARAM_TYPES",
]
