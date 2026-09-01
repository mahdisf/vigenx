"""Minimal third-party ViGenX block used by the authoring guide."""
from engine.block import ParamSpec, PipelineBlock, PortSpec
from engine.ports import TEXT


class PrefixTextBlock(PipelineBlock):
    type_id = "example_prefix_text"
    title = "Example: Prefix Text"
    description = "Prefix text to demonstrate external block discovery."
    category = "text"
    inputs = [PortSpec("text", TEXT)]
    outputs = [PortSpec("text", TEXT)]
    params = [
        ParamSpec("prefix", "str", "Edited: "),
        ParamSpec("uppercase", "bool", False),
    ]

    def process(self, ctx, inputs):
        value = f"{self.p('prefix')}{inputs['text']}"
        if self.p("uppercase"):
            value = value.upper()
        return {"text": value}


__all__ = ["PrefixTextBlock"]
