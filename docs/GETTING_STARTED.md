# Getting started

This path proves the planner and editor before installing the full render stack.
It makes no model API call and does not require source media.

## Requirements

- Git
- Python 3.10 or newer; Python 3.11 or 3.12 is recommended
- Internet access for the first dependency install and the current editor UI

FFmpeg is required only when you move from planning to rendering.

## Five-minute planning setup

```powershell
git clone https://github.com/mahdisf/vigenx.git
cd vigenx
python scripts/bootstrap.py --profile core
```

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

To use an existing Conda environment instead of `.venv`, install the core
profile directly:

```powershell
conda activate vigenx
python -m pip install -r requirements-core.txt
```

Verify the installation and generate a workflow without an API key:

```powershell
python -m vigenx doctor
python -m vigenx plan "Create three vertical clips with captions" --mode local --output first-workflow.json
```

Success means `doctor` reports `Planning/UI ready: yes` and
`first-workflow.json` contains a validated graph with `requires_approval: true`.

Start the editor:

```powershell
python -m vigenx web
```

Open <http://127.0.0.1:5000/editor>, enter a brief, select **Local**, and create
the workflow. Planning never starts a render.

## Full rendering profile

The complete profile installs Whisper, PyTorch, OpenCV, MoviePy, vision models,
and optional audio tools. It is large.

```powershell
python scripts/bootstrap.py --profile full
python -m vigenx doctor --strict
```

In a Conda environment, replace the bootstrap command with
`python -m pip install -r requirements.txt`.

Install FFmpeg separately and ensure `ffmpeg` and `ffprobe` are on `PATH`. Review
the workflow, choose licensed source and music files, preview, and run explicitly.

## Optional model-backed planning

Local planning is the default proof path. Model-backed planning is optional.
Set one supported provider key, restart the app, and choose **Auto** or **AI**:

```powershell
$env:GOOGLE_API_KEY = "..."
$env:GROQ_API_KEY = "..."
$env:NVIDIA_API_KEY = "..."
```

`Auto` falls back to the deterministic planner. `AI` fails explicitly when its
provider cannot run.

## Security boundary

The Flask app is a trusted single-user local tool. Keep it bound to `127.0.0.1`.
It has filesystem browsing and no production authentication or multi-user access
control. See [SECURITY.md](../SECURITY.md) before changing the bind address.

For common failures, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
