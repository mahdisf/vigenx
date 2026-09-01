# Releasing ViGenX

ViGenX uses immutable Git tags and GitHub releases. Pre-1.0 releases describe
the capability that was actually verified; they do not imply that every model,
codec, operating system, or publisher combination works.

## Version policy

- Alpha releases may change the CLI, graph schema, and block API.
- Beta releases require a fresh-clone planner smoke test and a licensed render
  fixture on every supported operating system.
- A stable release additionally requires a documented migration policy and
  repeatable end-to-end render and provenance checks.

The Python version in `vigenx/__init__.py`, Git tag, changelog heading, and
release title must describe the same version. A release tag is never moved or
rebuilt after publication.

## Alpha checklist

1. Update `CHANGELOG.md` and move shipped work out of `Unreleased`.
2. Run the supported source-checkout path in a clean environment.
3. Run the complete unit suite on Python 3.10 and 3.12, on Linux and Windows.
4. Build the website and verify its repository links.
5. Run `git diff --check` and inspect the tracked file list for secrets, media,
   credentials, model weights, and generated output.
6. Merge to `master` and wait for required GitHub Actions checks.
7. Create an annotated immutable tag and a GitHub prerelease.
8. Include exact install and verification commands, known limitations, and
   contributor credit in the release notes.
9. Download the generated source archive and repeat the planner smoke test.

Current smoke commands:

```powershell
python scripts/bootstrap.py --profile dev
python -m vigenx doctor
python -m vigenx plan "Create three vertical clips with captions" --mode local
python -m pytest
cd website
npm ci
npm run build
```

## Current distribution limit

The repository is a source distribution. Do not publish the current flat module
layout to PyPI: top-level packages such as `core`, `web`, and `config` must first
move under a collision-resistant `vigenx.*` namespace, and runtime package data
must be declared and tested. Until then, GitHub source archives are the supported
release artifact.
