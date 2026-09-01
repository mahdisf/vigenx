# Changelog

Notable user-facing changes are recorded here. ViGenX follows Semantic
Versioning while pre-1.0 APIs remain subject to documented change.

## [Unreleased]

No changes yet.

## [0.1.0-alpha.1] - 2026-09-01

### Added

- Constrained natural-language workflow planner with deterministic local mode.
- Source-checkout CLI with `doctor`, `plan`, and `web` commands.
- Cross-platform environment bootstrap with core, full, and development profiles.
- Visual graph editor integration through `/api/agent/plan`.
- Strict graph, port, parameter, and template validation.
- Third-party block discovery through the `vigenx.blocks` entry-point group.
- Reproducible prompt-to-workflow examples and an external block example.
- Atomic job persistence and approval-gated publishing scheduler.
- Rights and metadata sidecars for single and multi-clip graph exports.
- Contributor-focused architecture, block-authoring, setup, showcase, support,
  and troubleshooting documentation.
- Apache-2.0 license, contribution guide, security policy, issue forms,
  cross-platform CI, dependency updates, and GitHub Pages deployment.

### Fixed

- Prevented stale worker objects from overwriting live job progress and logs.
- Prevented concurrent scheduler calls from publishing the same item twice.
- Re-transcribed assembled timelines before burning captions.
- Made the unimplemented Playwright uploader report failure instead of success.

[Unreleased]: https://github.com/mahdisf/vigenx/compare/v0.1.0-alpha.1...HEAD
[0.1.0-alpha.1]: https://github.com/mahdisf/vigenx/releases/tag/v0.1.0-alpha.1
