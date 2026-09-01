# Architecture

ViGenX separates intent translation from media side effects.

```text
brief -> planner -> validated PipelineGraph -> visual review -> executor
                                                        |          |
                                                        |          +-> artifacts + sidecars
                                                        +-> explicit approval -> scheduler/publisher
```

## Components

| Path | Responsibility |
|---|---|
| `engine/planner.py` | Constrained local/model-backed brief compiler |
| `engine/graph.py` | Serializable DAG and connection validation |
| `engine/block.py` | Block, port, and parameter contracts |
| `engine/registry.py` | Built-in and third-party block discovery |
| `engine/executor.py` | Topological block execution and artifact collection |
| `web/` | Trusted local Flask UI, API, worker, and review flow |
| `publishing/` | Approved publishing adapters and atomic scheduling claims |
| `core/` | Media, transcription, metadata, rights, and model utilities |

## Planning boundary

The model-backed planner sees the editing brief and registered block catalog. It
cannot create commands, arbitrary Python, undeclared parameters, unknown ports,
file paths, or publishing destinations. The generated graph is parsed, coerced,
and validated. Planning endpoints return data and never enqueue execution.

## Execution boundary

The executor instantiates only registered blocks and processes nodes in
topological order. Job state is updated through locked atomic mutations. Outputs
carry artifact paths so the review queue can expose media, rights manifests, and
metadata sidecars together.

## Publishing boundary

Scheduling requires an existing approved job and a path owned by that job. Due
items are claimed and persisted before an uploader runs, preventing overlapping
scheduler calls from issuing the same external side effect twice. An interrupted
claim is not retried automatically because the remote upload may already have
succeeded.

## Extension boundary

Third-party Python distributions may expose a `PipelineBlock` class through a
`vigenx.blocks` entry point. ViGenX isolates discovery failures and records the
plugin origin in the block schema. Duplicate type ids are rejected. See
[BLOCK_AUTHORING.md](BLOCK_AUTHORING.md).

## Known limitations

- Processing graphs are not yet a full editorial timeline model.
- MoviePy resource cleanup and persistent node caching need more work.
- The editor currently loads UI libraries from public CDNs and is not fully
  offline despite local media processing.
- The full render stack lacks a licensed cross-platform smoke fixture.
- The local Flask UI is not safe to expose as a multi-user service.
