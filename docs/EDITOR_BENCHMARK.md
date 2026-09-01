# ViGenX benchmark: agentic video editing and workflow systems

Snapshot date: 2026-09-01. Star counts are approximate and will change. They are
included as a rough adoption signal, not as a quality score or product target.

## Repositories reviewed

| Project | Approx. stars | License | What matters for ViGenX |
|---|---:|---|---|
| [n8n](https://github.com/n8n-io/n8n) | 203k | Sustainable Use + Enterprise | Mature visual workflows, templates, approvals, execution history, integrations, and observability. Its product patterns are useful; its code is not permissively licensed. |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI) | 131k | GPL-3.0 | JSON node graphs, custom nodes, queues, cached partial execution, subgraphs, and API mode. This is the closest large-scale precedent for an inspectable media workflow ecosystem. |
| [FFmpeg](https://github.com/FFmpeg/FFmpeg) | 64k | LGPL/GPL depending on build | The deterministic codec, container, and filter layer. ViGenX should generate validated plans that call known operations, never arbitrary model-written shell commands. |
| [Remotion](https://github.com/remotion-dev/remotion) | 58k | Custom license | Editable React source, composition templates, previews, and batch rendering. The important lesson is to keep an editable artifact in addition to the final MP4. |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 41k | MIT | Durable state, checkpoints, interrupts, human approval, and tracing. These patterns fit long-running, failure-prone media jobs. |
| [MoviePy](https://github.com/Zulko/moviepy) | 15k | MIT | A productive Python composition layer. It is convenient, but hot render paths should move toward direct FFmpeg filters where profiling proves the benefit. |
| [auto-editor](https://github.com/WyattBlue/auto-editor) | 5k | Unlicense | Deterministic audio/motion-based editing and exports to professional editors. Cheap signal processing should precede expensive semantic model calls. |
| [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) | 2k | Apache-2.0 | A stable editorial timeline model with adapters. ViGenX eventually needs a timeline/EDL artifact separate from its processing DAG. |
| [Agentic Video Editor](https://github.com/poseljacob/agentic-video-editor) | 480 | MIT | Direct comparable with typed briefs/plans, director and reviewer stages, bounded revision, manifests, and versioned output. This proves “first agentic video editor” would be a false claim. |
| [Velorn](https://github.com/VelornLabs/velorn) | 460 | GPL-3.0 | Direct comparable with an editable timeline, ComfyUI bridge, agent tools, preview-first writes, approval, and undo. Agent actions should use the same audited command surface as the UI. |

## Decisions applied in ViGenX

1. Keep the existing typed `PipelineGraph`, block registry, executor, and JSON
   templates. A rewrite would discard the strongest part of the project.
2. Compile natural language into a constrained workflow document. The model may
   only select registered block types, declared ports, declared parameters, enum
   values, and bounded numeric values.
3. Validate before execution. Generated graphs require exactly one source, a
   materializing export, valid typed connections, no cycles, and all required
   inputs.
4. Keep the generated graph editable and visible. Planning does not silently run
   a render or publish anything.
5. Provide a deterministic local planner. Common workflows must remain usable
   without sending a brief or source media to a model provider.
6. Persist provenance. The graph stores the brief, planner path, approval
   requirement, and output sidecars; every exported clip receives a rights
   manifest and metadata file.
7. Claim publishing work atomically and require an approved review job. External
   side effects cannot be retried blindly because a timeout may occur after a
   platform accepted the upload.

## Current position

ViGenX now covers this bounded loop:

```text
brief -> constrained plan -> deterministic validation -> editable graph
      -> preview/run -> output + provenance -> human review -> optional schedule
```

It does not yet implement a full autonomous inspect/plan/render/quality-review/
revise loop. It also lacks a professional timeline model, durable intermediate
cache, subgraphs, plugin discovery, and objective render-quality evaluation.

## Next benchmark-driven work

| Priority | Work | Reference pattern |
|---|---|---|
| P0 | Tiny licensed video fixtures and prompt-to-graph structural evals | auto-editor, agentic-video-editor |
| P0 | Bounded render verification and revision, with explicit user approval | LangGraph interrupts/retries |
| P1 | Content-addressed node cache keyed by input, params, code, and model version | ComfyUI partial execution |
| P1 | Workflow diff, dry-run resource estimate, and run-from-node | n8n execution UX |
| P1 | Timeline/EDL model plus OpenTimelineIO export | OpenTimelineIO |
| P2 | Subgraphs and third-party block entry points | ComfyUI custom nodes |
| P2 | Direct FFmpeg filter paths for measured render bottlenecks | FFmpeg, auto-editor |

## License cautions

- Do not copy code from GPL projects into this Apache-2.0 repository without a
  deliberate license decision.
- n8n and Remotion are not general-purpose permissive code sources.
- FFmpeg redistribution obligations depend on the exact build flags and linked
  codecs. ViGenX invokes a user-installed FFmpeg binary and does not bundle one.

## Adoption metric

One million GitHub stars cannot be engineered or promised. Stars measure
attention, are easy to distort, and do not prove that users can complete edits.
The useful release metrics are successful first workflow, validated render rate,
time to first preview, revision count, crash-free jobs, and contributor retention.
