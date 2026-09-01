# ViGenX vision

Video editing automation should produce an artifact an editor can inspect, not a
render whose decisions are hidden inside a prompt. ViGenX turns editing intent
into a typed workflow graph, keeps that graph editable, and requires an explicit
decision before execution or publishing.

## Product thesis

The workflow is the product.

- Natural language is an input format, not an execution authority.
- Every automated decision should map to a known block and declared parameter.
- A workflow should be serializable, diffable, repeatable, and reviewable.
- Rendering and publishing are side effects and remain behind approval gates.
- Provenance should travel with output media.

## Core and extensions

Core owns contracts that must stay coherent: graph validation, typed ports,
planning constraints, execution state, approval, and provenance.

Editing techniques, model providers, source adapters, and publishers should be
extensions whenever they can evolve without changing those contracts. Installed
block plugins use the `vigenx.blocks` Python entry-point group. A plugin may add a
new type id; it may never replace a core block silently.

## Current priorities

1. Make a fresh clone reach a validated local workflow in minutes.
2. Prove render correctness with licensed synthetic fixtures.
3. Publish a stable block authoring contract and useful external blocks.
4. Add bounded agent revisions with visible diffs and repeated approval.
5. Build a gallery from reproducible prompts, workflows, and owned outputs.

## Non-goals

- Pretending an LLM response is a safe execution plan without validation.
- Hiding editing decisions to make the product appear more autonomous.
- Claiming copyright clearance, fair use, or platform eligibility.
- Auto-publishing without an approved job and explicit destination.
- Growing core by accepting every integration that could be a plugin.
- Optimizing repository stars instead of successful user workflows.

## Community contract

Small fixes may go directly to a pull request. New behavior should start with a
problem statement and acceptance criteria. Maintainer decisions should favor
editing correctness, reproducibility, and a narrow stable core over feature
count. AI-assisted contributions are welcome when the author understands the
change and supplies the same evidence required from any other contribution.
