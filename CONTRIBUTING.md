# Contributing to ViGenX

ViGenX is pre-1.0 software. The useful contributions are reproducible fixes,
small editing blocks, prompt-to-graph evaluations, media-fixture tests, and
measured render improvements. Broad rewrites without parity tests are unlikely to
be accepted.

## Start here

1. Search [issues](https://github.com/mahdisf/vigenx/issues) and
   [discussions](https://github.com/mahdisf/vigenx/discussions).
2. Choose an issue labeled `good first issue` for a bounded first change, or
   `help wanted` for work where maintainer context is available.
3. Comment on the issue before starting work that can reasonably overlap with
   another contribution.
4. For a large change, open a design discussion before writing it.
5. Keep the pull request scoped to one problem. Split unrelated refactors.

Route requests by type:

| Request | Route |
|---|---|
| Reproducible defect | Bug report issue form |
| Documentation defect | Documentation issue form |
| New block or scoped behavior | Feature proposal issue form |
| Large architecture or product change | GitHub Discussion first |
| Setup or usage question | GitHub Discussion |
| Vulnerability | Private security advisory; never a public issue |

Before opening an issue, run `python -m vigenx doctor` and include the commit or
release, operating system, exact command, and relevant capability output. Do not
paste credentials, private paths, or unredacted personal media metadata.

## Current priorities

- Prompt-to-graph structural evaluations with explicit expected nodes and edges
- Licensed tiny-video fixtures and cross-platform FFmpeg render smoke tests
- Offline editor dependencies instead of public CDN imports
- Resource lifecycle fixes for MoviePy clips, files, and subprocesses
- Plugin compatibility and authoring tools around the `vigenx.blocks` contract
- Reproducible showcase workflows with rights and provenance evidence

Work outside these areas is valid when it fixes a documented user problem and
includes focused evidence. Broad rewrites without behavioral parity tests are
unlikely to be accepted.

## Media and data rules

Keep source media owned, licensed, public domain, or generated specifically for
the test. Never commit downloaded creator content, credentials, model weights,
private media, or generated render artifacts.

## Development setup

```powershell
python scripts/bootstrap.py --profile dev
.\.venv\Scripts\Activate.ps1
python -m vigenx doctor
python -m pytest
```

On macOS or Linux, activate with `source .venv/bin/activate`. Install the `full`
profile and FFmpeg when working on real render paths. The unit suite deliberately
avoids downloading models or calling paid APIs.

Before opening a pull request:

```powershell
python -m compileall -q config core engine examples pipelines publishing scripts sources vigenx web tests
python -m pytest
git diff --check
```

For landing-page changes:

```powershell
cd website
npm ci
npm run typecheck
npm run build
```

## Change rules

- Extend the registered block catalog instead of adding another monolithic
  pipeline unless compatibility requires it.
- A planner may only emit registered blocks, declared parameters, and typed
  connections. Model output must be validated before any side effect.
- Uploads and other external writes require an approved review job.
- New output paths must preserve rights and metadata sidecars.
- Add focused tests for bug fixes and behavioral changes.
- Keep optional heavyweight dependencies lazily imported.
- Do not include drive-specific paths, tokens, cookies, personal media, or
  generated render artifacts.

## Pull requests

Every pull request must state:

- **Problem:** the reproducible failure or missing workflow
- **Why:** why this belongs in ViGenX and why the chosen boundary is appropriate
- **User impact:** behavior visible to an editor, block author, or operator
- **Evidence:** exact commands, fixtures, results, and before/after UI evidence
- **Risk:** side effects, compatibility, media rights, and remaining test gaps

Screenshots are required for meaningful UI changes. Benchmark and quality claims
need a redistributable fixture, exact command, hardware context when relevant,
and measured result. An anecdote is not evidence.

## AI-assisted contributions

AI-assisted code is accepted under the same accountability standard as any other
code. The pull-request author is responsible for every changed line and must:

- disclose material AI assistance in the pull-request template;
- review generated code, licenses, dependency choices, and security boundaries;
- run the stated checks rather than reporting generated or assumed results;
- remove fabricated APIs, tests, citations, benchmarks, and unsupported claims;
- respond to review with technical reasoning, not a model transcript.

Maintainers may close generated bulk changes that lack a reproducible problem,
focused scope, or verified behavior.

Merged contributors are credited in release notes. Showcase submissions retain
their named author and source/license attribution.

By contributing, you agree that your contribution is licensed under Apache-2.0.
