# ViGenX roadmap

This file tracks engineering work, not marketing targets. Repository stars are
not an acceptance criterion.

## P0: trustworthy agent loop

- [x] Plain-language brief to constrained, validated workflow graph
- [x] Deterministic offline planner when no provider key is configured
- [x] Explicit human-visible graph before execution
- [x] Atomic job progress/state persistence
- [x] Approval-gated scheduler with atomic external-side-effect claims
- [x] Rights and metadata sidecars propagated into graph review jobs
- [ ] Add prompt-to-graph evaluation cases with structural expectations
- [ ] Add licensed tiny-video fixtures for render smoke tests
- [ ] Add bounded render verification and at most two proposed revisions
- [ ] Add workflow diff and explicit approval for every agent revision
- [ ] Record planner model/version, graph hash, runtime, and token/cost data per job

## P1: editing correctness and performance

- [x] Re-transcribe assembled highlight timelines before burning captions
- [x] Enforce declared parameter enum choices and numeric bounds
- [ ] Model timeline provenance in the port/type system
- [ ] Bound all AI-selected moments to source duration
- [ ] Close MoviePy resources and clean temporary execution directories reliably
- [ ] Add a persistent content-addressed node cache
- [ ] Add a materializing run-from-node path
- [ ] Profile render paths and replace measured bottlenecks with FFmpeg filters
- [ ] Export OpenTimelineIO/EDL alongside the processing graph

## P1: product and ecosystem

- [ ] Add workflow dry-run estimates for models, disk, render time, and paid calls
- [ ] Add subgraphs and collapse-to-template
- [ ] Discover third-party blocks through Python entry points
- [ ] Add a stable block/plugin compatibility contract
- [ ] Add import/export examples and a small template gallery
- [ ] Add objective onboarding telemetry that is opt-in and self-hostable

## P2: legacy consolidation

- [ ] Build parity fixtures for general, speaker, and game legacy pipelines
- [ ] Express legacy-only behavior as registered blocks/templates
- [ ] Deprecate monolithic pipelines after render parity is demonstrated

## Release gates

- [ ] CI passes on Python 3.10 and 3.12
- [ ] Landing page passes desktop/mobile visual and accessibility checks
- [ ] Fresh clone can plan a workflow with no API key
- [ ] Sample render produces video, rights manifest, and metadata
- [ ] No tracked credentials, private media, model weights, or generated renders
- [ ] Security boundary and known limitations remain accurate in public docs
