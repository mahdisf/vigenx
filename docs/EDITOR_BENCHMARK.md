# ViGenX Pipeline Editor — Benchmark vs. Best-in-Class DAG / Node Engines

A practical comparison of the ViGenX graph editor + engine against the node/DAG
tools people consider best-in-class, plus a prioritized backlog of what to adopt.

## Reference engines

| Engine | Domain | Why it's a benchmark |
|--------|--------|----------------------|
| **ComfyUI** (LiteGraph.js) | AI media generation | Typed sockets, per-node previews, reroute, groups, huge ecosystem |
| **n8n** | Workflow automation | Polished UX, run-per-node, data pinning, execution history, error branches |
| **Node-RED** | IoT / flow-based | Mature flow model, subflows, import/export, palette manager |
| **Rete.js** | Node-editor framework | Clean plugin arch, typed connections, validation |
| **Blender** geometry/shader nodes | 3D/procedural | Node groups, frames, muting, live viewport feedback |
| **Unreal Blueprints** | Game logic | Reroute nodes, comments, collapse-to-function, debugging |
| **Airflow / Prefect / Dagster** | Data orchestration | Scheduling, retries, backfills, observability, lineage, params |

## Capability matrix

Legend: ✅ have · 🟡 partial · ❌ missing

| Capability | ViGenX today | ComfyUI | n8n | Airflow/Dagster |
|---|---|---|---|---|
| Typed ports + connection validation | ✅ (`graph.validate`) | ✅ | 🟡 | 🟡 |
| Visual canvas (pan/zoom/minimap) | ✅ (React Flow) | ✅ | ✅ | 🟡 |
| Per-node live preview | ✅ (frame/draft) | ✅ | 🟡 (data) | ❌ |
| Add / connect / **delete** nodes & edges | ✅ | ✅ | ✅ | n/a |
| Parameter inspector w/ widget types | ✅ | ✅ | ✅ | 🟡 |
| Templates / save-load graphs | ✅ (JSON) | ✅ | ✅ | ✅ (code) |
| Batch over many inputs | ✅ (`source_refs`) | 🟡 | ✅ | ✅ |
| Scheduling / auto-publish | ✅ (scheduler) | ❌ | ✅ | ✅ |
| **Run-per-node / partial run** | ✅ (draft-from-node + preview) | ✅ | ✅ | ✅ |
| **Intermediate result caching across runs** | 🟡 (preview cache) | ✅ | 🟡 | ✅ |
| **Per-node run status overlay on canvas** | ✅ (live SSE coloring) | ✅ | ✅ | ✅ |
| **Reroute / groups / comments / frames** | ❌ | ✅ | 🟡 | ✅ |
| **Undo / redo, copy / paste, duplicate** | ✅ (Ctrl+Z/Y/C/V/D) | ✅ | ✅ | n/a |
| **Search / quick-add node palette** | ✅ (filter + dbl-click) | ✅ | ✅ | n/a |
| **Graph validation feedback** | ✅ (Validate button) | 🟡 | 🟡 | ✅ |
| **Auto-layout** | ✅ (topological) | 🟡 | 🟡 | ✅ |
| **Retries / error branches / on-failure** | ❌ | 🟡 | ✅ | ✅ |
| **Data pinning / mock inputs** | ❌ | 🟡 | ✅ | ✅ |
| Subgraphs / collapse-to-block | ❌ | 🟡 | ✅ | ✅ |
| Versioning / run history / lineage | 🟡 (jobs) | ❌ | ✅ | ✅ |

## Where ViGenX is already strong
- **Typed DAG with real validation** (cycles, type mismatches, unsatisfied inputs) before a run — stronger than n8n/Node-RED, on par with Rete/Dagster.
- **WYSIWYG per-node preview** with ancestor memoization — the ComfyUI-class feature most workflow tools lack.
- **Clip-passing execution** (lazy MoviePy; only `export` writes) — efficient, no per-block re-encode.
- **Scheduling + batch + auto-publish** baked in — Airflow-class concerns most node editors don't touch.

## Gaps & prioritized recommendations

### P0 — correctness & core editing — ✅ DONE
1. **Delete nodes & edges** — ✅ (Delete key, toolbar, inspector).
2. **Robust preview errors** — ✅ (friendly messages, no `NoneType.get_frame`).
3. **Undo/redo + copy/paste/duplicate** — ✅ (snapshot stack; Ctrl+Z/Y/C/V/D).
4. **Node search / quick-add** — ✅ (palette filter + double-click searchable add-menu).
5. **Auto-layout + Validate button** — ✅ (topological layout; `/api/validate`).

### P1 — execution engine parity
6. **Per-node run status on canvas** — ✅ (SSE `node_status` → live running/done/error
   coloring). Backend [web/routes/jobs.py](web/routes/jobs.py) + [web/worker.py](web/worker.py).
7. **Run-from-here** — 🟡 partial: per-node **draft** is wired
   (`executor.draft(node_id=…)`); a full materializing run-from-node (`/api/run` +
   `target_node`) is the remaining step. ([engine/executor.py](engine/executor.py))
8. **Persistent intermediate cache** — generalize the preview memo cache to full runs so
   re-running after a param tweak skips unchanged ancestors (ComfyUI's killer feature).
   Cache key = `params_hash` in [engine/preview.py](engine/preview.py); add a
   content-addressed file cache keyed by upstream hashes.
9. **Retries / on-error policy per node** — add `retries`, `on_error` (`stop|skip|route`)
   to block params; honor in [engine/executor.py](engine/executor.py) `run`.

### P2 — scale & authoring ergonomics
9. **Reroute nodes, groups/frames, comments** — pure React Flow additions; improves large graphs.
10. **Subgraphs / collapse-to-template** — embed a saved template as a single node
    (engine: a `SubgraphBlock` that runs a nested `GraphExecutor`).
11. **Data pinning / mock inputs** — pin a node's output (e.g. a fixed transcript) so
    downstream iteration skips slow upstream (Whisper/Gemini). Store pins in the graph `meta`.
12. **Run history & lineage view** — list past jobs per template with inputs/outputs and
    the rights manifest; partially covered by `output/history.csv` + the jobs store.
13. **Palette manager / plugin blocks** — auto-discover third-party blocks via entry points
    (registry already supports `@register_block`; add a plugins dir scan).

## One-line takeaway
ViGenX already matches ComfyUI on **typed graphs + per-node preview** and beats most node
editors on **scheduling/auto-publish**. The biggest gaps are **authoring ergonomics**
(undo/redo, search-add, reroute/groups) and **execution observability** (on-canvas node
status, run-from-here, persistent caching, retries) — all incremental additions on the
current architecture, none requiring a rewrite.
