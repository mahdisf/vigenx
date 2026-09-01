# Troubleshooting

Run diagnostics first:

```powershell
python -m vigenx doctor
python -m vigenx doctor --json
```

## Planning/UI ready is `no`

Activate the intended environment and install the core profile:

```powershell
python -m pip install -r requirements-core.txt
```

Run commands from the repository root so the default configuration and built-in
templates resolve correctly.

## Base rendering or full profile readiness is `no`

Install the full profile, then install FFmpeg separately:

```powershell
python -m pip install -r requirements.txt
ffmpeg -version
ffprobe -version
```

The full profile is large. Built-in blocks can remain visible because heavy
dependencies are imported lazily; a block that needs a missing package will fail
when run. Use the individual `doctor` checks to distinguish the base media
toolchain from AI provider SDKs.

## Editor is blank or CDN requests fail

The current no-build editor imports React, React Flow, HTM, and Bootstrap from
public CDNs. Local media stays local, but the UI is not yet fully offline. Check
browser console/network errors and use a network that can reach `esm.sh` and
`cdn.jsdelivr.net`. Bundling these dependencies is tracked as contributor work.

## A plugin does not appear

Install the plugin into the same Python environment as ViGenX, restart the app,
and inspect `python -m vigenx doctor --json`. The entry point group must be
`vigenx.blocks`, resolve to a `PipelineBlock` class, and use a unique `type_id`.

## `AI` planning fails

`AI` mode never falls back silently. Confirm the provider SDK, key, and model.
Use `Local` to verify the rest of the planner without a paid API call.

## Windows cannot activate `.venv`

PowerShell execution policy may block `Activate.ps1`. The environment's Python
can be called without activation:

```powershell
.\.venv\Scripts\python.exe -m vigenx doctor
.\.venv\Scripts\python.exe -m vigenx web
```
