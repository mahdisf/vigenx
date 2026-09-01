## Related issue

<!-- Link the issue or discussion. Explain why no issue was needed for a trivial change. -->

## Problem

<!-- What reproducible failure or missing workflow exists? -->

## Why this approach

<!-- Why does this belong in ViGenX, and why is this the right ownership boundary? -->

## User impact

<!-- State the behavior visible to an editor, block author, or operator. -->

## Evidence

<!-- Exact commands, fixtures, and results. Add before/after screenshots for UI changes. -->

## Verification

- [ ] `python -m compileall -q config core engine pipelines publishing scripts sources vigenx web tests`
- [ ] `python -m pytest`
- [ ] `git diff --check`
- [ ] UI changes: `cd website`, `npm ci`, `npm run typecheck`, and `npm run build`
- [ ] Render/quality claims include a redistributable fixture and reproducible measurements.

<!-- Remove checks that do not apply and explain why. Do not check commands you did not run. -->

## AI assistance

- [ ] No material AI assistance was used.
- [ ] AI was used; I reviewed every changed line and describe the use below.

<!-- If used, state where AI materially affected code, tests, documentation, or assets. -->

## Risk and safety

- [ ] No credentials, personal media, model weights, or generated renders are included.
- [ ] Model-generated data is validated before execution or external side effects.
- [ ] Output/provenance and review behavior remain correct.
- [ ] Tests cover the changed behavior.

<!-- State compatibility effects, side effects, media-rights concerns, and remaining test gaps. -->
