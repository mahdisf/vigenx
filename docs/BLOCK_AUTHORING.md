# Authoring an external block

Blocks are ViGenX's public extension unit. A block declares typed inputs, outputs,
parameters, and a deterministic `process` method. The same declaration drives
graph validation, the editor palette, inspector controls, and planner allow-list.

## Run the example

From an activated ViGenX source environment:

```powershell
python -m pip install -e examples/block_plugin
python -m vigenx doctor
```

Restart the editor. `Example: Prefix Text` appears in the block catalog with an
origin such as `vigenx-example-block@0.1.0:prefix_text`.

## Minimal class

```python
from engine.block import ParamSpec, PipelineBlock, PortSpec
from engine.ports import TEXT


class PrefixTextBlock(PipelineBlock):
    type_id = "acme_prefix_text"
    title = "ACME: Prefix Text"
    category = "text"
    inputs = [PortSpec("text", TEXT)]
    outputs = [PortSpec("text", TEXT)]
    params = [ParamSpec("prefix", "str", "Edited: ")]

    def process(self, ctx, inputs):
        return {"text": self.p("prefix") + str(inputs["text"])}
```

Expose the class from the plugin's `pyproject.toml`:

```toml
[project.entry-points."vigenx.blocks"]
prefix_text = "acme_vigenx:PrefixTextBlock"
```

## Contract

- Use a globally distinctive, stable `type_id`; prefix it with your project name.
- Entry points must resolve directly to one `PipelineBlock` subclass.
- Declare every accepted parameter. Unknown model-generated parameters are
  discarded before execution.
- Use existing port types from `engine.ports` unless a coordinated core change is
  required.
- Do not perform network, filesystem, upload, or subprocess side effects in the
  constructor.
- Return only declared outputs from `process`.
- Close clips, files, and subprocesses you create, including on failure.
- Preserve or extend provenance metadata when producing media.
- Never publish or upload directly from an editing block.
- Add unit tests with synthetic values and a licensed fixture for render behavior.

## Compatibility

The plugin API is experimental until ViGenX 1.0. Pin the ViGenX commit or release
you test against and state it in the plugin README. A future compatibility field
will replace commit pinning before a stable plugin registry is announced.

Plugin import failures appear in `python -m vigenx doctor --json`. A broken plugin
is skipped without preventing built-in blocks from loading.
