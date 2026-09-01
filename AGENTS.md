# Repository instructions for coding agents

## Scope

- Read `README.md`, `CONTRIBUTING.md`, and the relevant document under `docs/`
  before editing.
- Keep changes scoped to one reported problem. Do not rewrite unrelated modules.
- Treat the registered block catalog, typed graph, approval gate, and provenance
  sidecars as compatibility and safety boundaries.

## Implementation

- Prefer registered blocks over new monolithic pipelines.
- Validate all model output before execution. Planning must not create side
  effects, arbitrary commands, unknown parameters, or upload destinations.
- Keep heavyweight and provider-specific dependencies optional and lazily loaded.
- Preserve approval checks for publishing and rights/metadata sidecars for output.
- Never add credentials, cookies, personal media, model weights, downloaded
  creator content, or generated renders.

## Verification

Run the focused test first, then the repository checks:

```powershell
python -m compileall -q config core engine examples pipelines publishing scripts sources vigenx web tests
python -m pytest
git diff --check
```

For `website/` changes, also run `npm ci`, `npm run typecheck`, and `npm run build`
from that directory. State exactly which checks ran and any gaps; never invent a
test result, benchmark, API, citation, or supported capability.

## Pull requests

Follow `.github/PULL_REQUEST_TEMPLATE.md`. Explain the problem, why the change
belongs at the chosen boundary, user impact, reproducible evidence, risk, and any
material AI assistance.
