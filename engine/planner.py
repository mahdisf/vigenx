"""Compile a natural-language editing brief into a validated ViGenX graph.

The planner has two paths:

* A constrained LLM planner when the selected provider has an API key.
* A deterministic local compiler for common editing intents and offline use.

Both paths pass through the same allow-list sanitizer and graph validator. Model
output is never executed directly and the caller receives an editable graph.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from engine.graph import GraphEdge, GraphNode, PipelineGraph
from engine.registry import all_blocks, block_schemas, get_block, load_builtin_blocks


MAX_BRIEF_CHARS = 4000
MAX_PLAN_NODES = 30


class WorkflowPlanningError(ValueError):
    """Raised when a brief cannot produce a safe, valid workflow."""


@dataclass
class WorkflowPlan:
    graph: PipelineGraph
    summary: str
    planner: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph": self.graph.to_dict(),
            "summary": self.summary,
            "planner": self.planner,
            "warnings": list(self.warnings),
        }


def _contains(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _slug(value: str, fallback: str = "workflow") -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (clean[:48] or fallback).strip("-")


def _target_duration(text: str, default: int = 59) -> int:
    patterns = (
        r"(?:under|max(?:imum)?|up to|about|around)\s+(\d{1,3})\s*(?:seconds?|secs?|s)\b",
        r"(\d{1,3})\s*(?:seconds?|secs?|s)\s+(?:long|short|clip|video|reel)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return max(5, min(600, int(match.group(1))))
    return default


def _clip_count(text: str, default: int = 10) -> int:
    match = re.search(
        r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"(?:separate\s+|vertical\s+|short\s+){0,2}(?:clips?|shorts?|highlights?)\b",
        text,
    )
    if not match:
        return default
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    value = words.get(match.group(1), int(match.group(1)) if match.group(1).isdigit() else default)
    return max(1, min(50, value))


def _requests_multiple_outputs(text: str) -> bool:
    match = re.search(
        r"\b(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"(?:separate\s+|vertical\s+|short\s+){0,2}(?:clips?|shorts?|highlights?)\b",
        text,
    )
    counted_multiple = False
    if match:
        token = match.group(0).split()[0]
        words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        }
        counted_multiple = (int(token) if token.isdigit() else words.get(token, 1)) > 1
    return counted_multiple or _contains(
        text,
        ("separate clips", "multiple clips", "clips from", "shorts from", "each clip"),
    )


def _language(text: str) -> str:
    languages = {
        "english": "en", "spanish": "es", "french": "fr", "german": "de",
        "italian": "it", "portuguese": "pt", "dutch": "nl", "russian": "ru",
        "turkish": "tr", "arabic": "ar", "persian": "fa", "farsi": "fa",
        "hindi": "hi", "japanese": "ja", "korean": "ko", "chinese": "zh",
    }
    for name, code in languages.items():
        if name in text:
            return code
    return "auto"


def _catalog_for_prompt() -> List[Dict[str, Any]]:
    catalog = []
    for schema in block_schemas():
        catalog.append({
            "type_id": schema["type_id"],
            "description": schema.get("description", ""),
            "inputs": [
                {"name": p["name"], "type": p["type"], "required": p["required"]}
                for p in schema.get("inputs", [])
            ],
            "outputs": [
                {"name": p["name"], "type": p["type"]}
                for p in schema.get("outputs", [])
            ],
            "params": [
                {
                    "name": p["name"], "type": p["type"],
                    "default": p.get("default"), "choices": p.get("choices"),
                    "min": p.get("min"), "max": p.get("max"),
                }
                for p in schema.get("params", [])
            ],
        })
    return catalog


class WorkflowPlanner:
    """Create inspectable workflows from plain-language editing briefs."""

    def __init__(self, config: Any = None) -> None:
        self.config = config
        load_builtin_blocks()

    def plan(
        self,
        brief: str,
        *,
        source: str = "",
        mode: str = "auto",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> WorkflowPlan:
        brief = (brief or "").strip()
        if not brief:
            raise WorkflowPlanningError("Describe the edit you want.")
        if len(brief) > MAX_BRIEF_CHARS:
            raise WorkflowPlanningError(
                f"Brief is too long ({len(brief)} characters); maximum is {MAX_BRIEF_CHARS}."
            )
        mode = (mode or "auto").strip().lower()
        if mode not in {"auto", "ai", "local"}:
            raise WorkflowPlanningError("Planner mode must be auto, ai, or local.")

        selected_provider = provider or getattr(self.config, "llm_provider", "gemini")
        if mode in {"auto", "ai"} and self._has_api_key(selected_provider):
            try:
                return self._plan_with_llm(
                    brief, source=source, provider=selected_provider, model=model
                )
            except Exception as exc:  # model planning is optional in auto mode
                if mode == "ai":
                    raise WorkflowPlanningError(f"AI planning failed: {exc}") from exc
                fallback = self._plan_locally(brief, source=source)
                fallback.warnings.insert(
                    0, f"AI planning failed; used the local planner instead: {exc}"
                )
                return fallback

        if mode == "ai":
            raise WorkflowPlanningError(
                f"No API key is configured for {selected_provider!r}; use auto/local "
                "or add a key in Settings."
            )
        plan = self._plan_locally(brief, source=source)
        if mode == "auto":
            plan.warnings.insert(
                0, "No planner API key is configured; used the deterministic local planner."
            )
        return plan

    def _has_api_key(self, provider: str) -> bool:
        if self.config is None:
            return False
        try:
            from core.llm import api_key_for

            return bool(api_key_for(self.config, provider))
        except (KeyError, ValueError):
            return False

    def _plan_with_llm(
        self,
        brief: str,
        *,
        source: str,
        provider: str,
        model: Optional[str],
    ) -> WorkflowPlan:
        try:
            from pydantic import BaseModel, Field
        except ImportError as exc:
            raise RuntimeError("pydantic is required for AI workflow planning") from exc

        class ModelNode(BaseModel):
            id: str
            type_id: str
            params: Dict[str, Any] = Field(default_factory=dict)

        class ModelEdge(BaseModel):
            source: str
            source_port: str
            target: str
            target_port: str

        class ModelPlan(BaseModel):
            name: str
            summary: str
            nodes: List[ModelNode]
            edges: List[ModelEdge]
            warnings: List[str] = Field(default_factory=list)

        prompt = (
            "You are the planning compiler for ViGenX, a typed video workflow editor. "
            "Translate the user's brief into one small executable DAG. Use only the "
            "block types, ports, parameters, enum choices, and value ranges in the "
            "catalog. Include exactly one source block and at least one export or "
            "export_clips block. Never invent file paths, URLs, credentials, commands, "
            "or block capabilities. Leave file/folder parameters empty. Keep node IDs "
            "short and unique. Prefer deterministic blocks; use ai_extract or ai_text "
            "only when the request needs semantic judgment. Return a concise result, "
            "not chain-of-thought.\n\n"
            f"USER BRIEF:\n{brief}\n\n"
            f"BLOCK CATALOG:\n{json.dumps(_catalog_for_prompt(), ensure_ascii=True)}"
        )
        from core.llm import api_key_for, generate_structured

        result = generate_structured(
            prompt,
            ModelPlan,
            provider=provider,
            model=model,
            api_key=api_key_for(self.config, provider),
            max_retries=2,
        )
        raw = result.model_dump()
        graph, sanitize_warnings = self._sanitize_graph(
            {
                "id": f"agent-{uuid.uuid4().hex[:8]}",
                "name": raw.get("name") or "Agent workflow",
                "nodes": raw.get("nodes") or [],
                "edges": raw.get("edges") or [],
            },
            source=source,
            brief=brief,
            planner=f"llm:{provider}",
        )
        return WorkflowPlan(
            graph=graph,
            summary=(raw.get("summary") or "Generated a validated editing workflow.").strip(),
            planner=f"llm:{provider}",
            warnings=[*(raw.get("warnings") or []), *sanitize_warnings],
        )

    def _plan_locally(self, brief: str, *, source: str) -> WorkflowPlan:
        text = brief.lower()
        duration = _target_duration(text)
        count = _clip_count(text)
        separate = _requests_multiple_outputs(text)
        highlights = separate or _contains(
            text,
            ("highlight", "best moment", "viral moment", "key moment", "most engaging"),
        )
        wants_subtitles = _contains(
            text,
            ("subtitle", "caption", "transcribe", "transcript", "closed caption"),
        )
        wants_vertical = _contains(
            text,
            ("vertical", "portrait", "9:16", "shorts", "reel", "tiktok"),
        )
        wants_silence = _contains(
            text,
            ("silence", "dead air", "pause", "tighten", "remove gaps"),
        )
        wants_color = _contains(
            text,
            ("cinematic", "vibrant", "color grade", "colour grade", "saturation", "contrast"),
        )
        wants_blur = _contains(text, ("blur face", "blur faces", "anonymize", "privacy"))
        wants_logo = _contains(text, ("logo", "watermark", "brand mark"))
        wants_music = _contains(text, ("music", "soundtrack", "background track"))
        wants_intro = _contains(text, ("intro", "outro"))
        wants_thumbnail = _contains(text, ("thumbnail", "cover image", "cover frame"))
        wants_ai_selection = _contains(
            text,
            ("ai choose", "ai select", "semantic", "viral", "most engaging"),
        ) and self._has_api_key(getattr(self.config, "llm_provider", "gemini"))

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, str]] = []
        warnings: List[str] = []
        used_ids: Dict[str, int] = {}

        def add(type_id: str, params: Optional[Dict[str, Any]] = None) -> str:
            used_ids[type_id] = used_ids.get(type_id, 0) + 1
            suffix = "" if used_ids[type_id] == 1 else str(used_ids[type_id])
            node_id = f"{type_id}{suffix}"
            nodes.append({"id": node_id, "type_id": type_id, "params": params or {}})
            return node_id

        def connect(a: str, a_port: str, b: str, b_port: str) -> None:
            edges.append({
                "source": a, "source_port": a_port,
                "target": b, "target_port": b_port,
            })

        src = add("source", {"source": source, "source_type": "auto" if source else "local"})
        media = src

        if _contains(text, ("trim", "cut", "first ", "start at", "end at")) and not highlights:
            cut = add("cut_trim", {"max_duration": duration})
            connect(media, "media", cut, "media")
            media = cut
        if wants_silence:
            silence = add("silence_trim")
            connect(media, "media", silence, "media")
            media = silence

        transcript = None
        caption_transcript = None
        moments = None
        if wants_subtitles or highlights:
            transcript = add("transcribe", {"language": _language(text)})
            connect(media, "media", transcript, "media")
            caption_transcript = transcript
        if highlights and transcript:
            selector_type = "ai_extract" if wants_ai_selection else "key_moments"
            selector_params: Dict[str, Any]
            if selector_type == "ai_extract":
                selector_params = {
                    "mode": "virality", "count": count,
                    "max_clip": duration,
                }
            else:
                selector_params = {
                    "mode": "highlights" if separate else "reel",
                    "count": count, "max_clip": duration,
                    "max_duration": duration,
                }
            moments = add(selector_type, selector_params)
            connect(transcript, "subtitles", moments, "subtitles")
            if not separate:
                assembled = add("moments_cut", {"max_duration": duration})
                connect(media, "media", assembled, "media")
                connect(moments, "moments", assembled, "moments")
                media = assembled
                if wants_subtitles:
                    caption_transcript = add("transcribe", {"language": _language(text)})
                    connect(media, "media", caption_transcript, "media")

        if wants_vertical:
            vertical = add("vertical_crop", {"mode": "crop"})
            connect(media, "media", vertical, "media")
            media = vertical
        if wants_color:
            color = add("color_filter", {"contrast": 1.05, "saturation": 1.15})
            connect(media, "media", color, "media")
            media = color
        if wants_blur:
            blur = add("face_blur")
            connect(media, "media", blur, "media")
            media = blur
        if wants_subtitles and caption_transcript:
            subtitle_params: Dict[str, Any] = {}
            if "yellow" in text:
                subtitle_params["color"] = "yellow"
            if "top captions" in text or "captions at the top" in text:
                subtitle_params["position"] = "top"
            subtitles = add("subtitles", subtitle_params)
            connect(media, "media", subtitles, "media")
            connect(caption_transcript, "subtitles", subtitles, "subtitles")
            media = subtitles
        if wants_logo:
            logo = add("logo")
            connect(media, "media", logo, "media")
            media = logo
            warnings.append("Choose the logo file in the Logo block before running.")
        if wants_intro:
            intro = add("intro_outro")
            connect(media, "media", intro, "media")
            media = intro
            warnings.append("Choose the intro/outro files in the block before running.")
        if wants_music:
            music = add("background_music")
            connect(media, "media", music, "media")
            media = music
            warnings.append("Choose a licensed music track or folder before running.")

        if separate and moments:
            output = add("export_clips", {"prefix": "vigenx", "quality": "High"})
            connect(media, "media", output, "media")
            connect(moments, "moments", output, "moments")
        else:
            output = add("export", {"quality": "High"})
            connect(media, "media", output, "media")

        if wants_thumbnail:
            thumbnail = add("thumbnail")
            connect(output, "video", thumbnail, "video")

        raw = {
            "id": f"agent-{uuid.uuid4().hex[:8]}",
            "name": f"Agent: {_slug(brief, 'video-edit')}",
            "nodes": nodes,
            "edges": edges,
        }
        graph, sanitize_warnings = self._sanitize_graph(
            raw, source=source, brief=brief, planner="local"
        )
        titles = [get_block(n.type_id).title for n in graph.nodes]
        summary = "Built a validated workflow: " + " -> ".join(titles) + "."
        return WorkflowPlan(
            graph=graph,
            summary=summary,
            planner="local",
            warnings=[*warnings, *sanitize_warnings],
        )

    def _sanitize_graph(
        self,
        raw: Dict[str, Any],
        *,
        source: str,
        brief: str,
        planner: str,
    ) -> Tuple[PipelineGraph, List[str]]:
        raw_nodes = raw.get("nodes") or []
        raw_edges = raw.get("edges") or []
        if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
            raise WorkflowPlanningError("Planner returned malformed nodes or edges.")
        if not raw_nodes or len(raw_nodes) > MAX_PLAN_NODES:
            raise WorkflowPlanningError(
                f"Planner must return between 1 and {MAX_PLAN_NODES} nodes."
            )

        known = {cls.type_id: cls for cls in all_blocks()}
        nodes: List[GraphNode] = []
        warnings: List[str] = []
        seen: set[str] = set()
        source_count = 0

        for index, item in enumerate(raw_nodes):
            if not isinstance(item, dict):
                raise WorkflowPlanningError("Planner returned a non-object node.")
            type_id = str(item.get("type_id") or "")
            if type_id not in known:
                raise WorkflowPlanningError(f"Planner selected unknown block {type_id!r}.")
            node_id = re.sub(r"[^A-Za-z0-9_-]", "-", str(item.get("id") or type_id))[:64]
            node_id = node_id.strip("-") or f"node-{index + 1}"
            base = node_id
            serial = 2
            while node_id in seen:
                node_id = f"{base}-{serial}"
                serial += 1
            seen.add(node_id)

            cls = known[type_id]
            incoming_params = item.get("params") if isinstance(item.get("params"), dict) else {}
            params: Dict[str, Any] = {}
            for spec in cls.params:
                value = incoming_params.get(spec.name, spec.default)
                if spec.type in {"file", "folder"} and value:
                    warnings.append(
                        f"Cleared model-supplied path for {node_id}.{spec.name}; choose it in the editor."
                    )
                    value = spec.default
                value = spec.coerce(value)
                if spec.type in {"int", "float"} and isinstance(value, (int, float)):
                    if spec.min is not None:
                        value = max(value, spec.min)
                    if spec.max is not None:
                        value = min(value, spec.max)
                    if spec.type == "int":
                        value = int(value)
                if spec.type == "enum" and value not in (spec.choices or []):
                    value = spec.default
                params[spec.name] = value
            if type_id == "source":
                source_count += 1
                params["source"] = source
                params["source_type"] = "auto" if source else "local"
            nodes.append(
                GraphNode(
                    id=node_id,
                    type_id=type_id,
                    params=params,
                    position={"x": float((index % 6) * 260), "y": float((index // 6) * 180)},
                )
            )

        if source_count != 1:
            raise WorkflowPlanningError("Planner must create exactly one Source block.")
        if not any(n.type_id in {"export", "export_clips"} for n in nodes):
            raise WorkflowPlanningError("Planner must include Export MP4 or Export Clips.")

        edges: List[GraphEdge] = []
        node_ids = {n.id for n in nodes}
        for item in raw_edges:
            if not isinstance(item, dict):
                raise WorkflowPlanningError("Planner returned a non-object edge.")
            edge = GraphEdge(
                source=str(item.get("source") or ""),
                source_port=str(item.get("source_port") or ""),
                target=str(item.get("target") or ""),
                target_port=str(item.get("target_port") or ""),
            )
            if edge.source not in node_ids or edge.target not in node_ids:
                raise WorkflowPlanningError("Planner returned an edge with an unknown node.")
            edges.append(edge)

        name = str(raw.get("name") or "Agent workflow").strip()[:100] or "Agent workflow"
        graph = PipelineGraph(
            id=str(raw.get("id") or f"agent-{uuid.uuid4().hex[:8]}")[:64],
            name=name,
            nodes=nodes,
            edges=edges,
            meta={
                "agent_generated": True,
                "brief": brief,
                "planner": planner,
                "requires_approval": True,
            },
        )
        graph.validate()
        return graph, warnings


__all__ = [
    "MAX_BRIEF_CHARS",
    "WorkflowPlan",
    "WorkflowPlanner",
    "WorkflowPlanningError",
]
