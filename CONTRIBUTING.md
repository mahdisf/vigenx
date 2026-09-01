# Contributing to ViGenX

ViGenX is pre-1.0 software. The useful contributions are reproducible fixes,
small editing blocks, prompt-to-graph evaluations, media-fixture tests, and
measured render improvements. Broad rewrites without parity tests are unlikely to
be accepted.

## Start here

1. Search [issues](https://github.com/mahdisf/vigenx/issues) and
   [discussions](https://github.com/mahdisf/vigenx/discussions).
2. For a large change, open a design discussion before writing it.
3. Keep source media owned, licensed, public domain, or generated specifically
   for the test. Never commit downloaded creator content, credentials, or model
   weights.

## Development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
```

Install `requirements.txt` and FFmpeg when working on real render paths. The unit
suite deliberately avoids downloading models or calling paid APIs.

Before opening a pull request:

```powershell
python -m compileall -q config core engine pipelines publishing sources web tests
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

Describe the user-visible behavior, the failure mode being fixed, and the exact
verification performed. Screenshots are required for meaningful UI changes.
Benchmark claims need a reproducible fixture and command, not an anecdote.

By contributing, you agree that your contribution is licensed under Apache-2.0.
