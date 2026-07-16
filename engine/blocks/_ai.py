"""Shared helpers for AI blocks (provider/model params + LLM dispatch).

Every AI block exposes a ``provider`` choice and a free-text ``model`` field. The
key for the chosen provider is resolved from ``ctx.config`` (Settings / env). Use
:func:`llm_param_specs` to declare the params and :func:`resolve_llm` to read them.
"""
from __future__ import annotations

from typing import Any, List, Tuple, Type, TypeVar

from engine.block import ParamSpec
from engine.context import ExecutionContext

T = TypeVar("T")


def llm_param_specs(advanced_model: bool = True) -> List[ParamSpec]:
    """The standard provider + model params shared by all AI blocks."""
    from core.llm import DEFAULT_MODELS, PROVIDERS

    model_help = "Blank = provider default (" + ", ".join(
        f"{p}: {DEFAULT_MODELS[p]}" for p in PROVIDERS) + ")."
    return [
        ParamSpec("provider", "enum", "gemini", choices=list(PROVIDERS),
                  label="AI provider"),
        ParamSpec("model", "str", "", advanced=advanced_model, label="Model",
                  help=model_help),
    ]


def resolve_llm(ctx: ExecutionContext, block) -> Tuple[str, str, str]:
    """Return ``(provider, model, api_key)`` for ``block`` using ``ctx.config``."""
    from core.llm import api_key_for, default_model, normalize_provider

    provider = normalize_provider(block.p("provider", "gemini"))
    model = block.p("model", "") or default_model(provider)
    api_key = api_key_for(ctx.config, provider)
    return provider, model, api_key


def llm_text(ctx: ExecutionContext, block, prompt: str) -> str:
    from core.llm import generate_text

    provider, model, api_key = resolve_llm(ctx, block)
    return generate_text(prompt, provider=provider, model=model, api_key=api_key or None)


def llm_structured(ctx: ExecutionContext, block, prompt: str, schema: Type[T]) -> T:
    from core.llm import generate_structured

    provider, model, api_key = resolve_llm(ctx, block)
    return generate_structured(
        prompt, schema, provider=provider, model=model, api_key=api_key or None
    )


__all__ = ["llm_param_specs", "resolve_llm", "llm_text", "llm_structured"]
