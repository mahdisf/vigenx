"""Create a ViGenX virtual environment with an explicit dependency profile."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Sequence


PROFILE_REQUIREMENTS = {
    "core": "requirements-core.txt",
    "full": "requirements.txt",
    "dev": "requirements-dev.txt",
}


def environment_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def build_commands(
    repo_root: Path,
    venv_dir: Path,
    profile: str,
    bootstrap_python: str = sys.executable,
) -> list[list[str]]:
    requirements = repo_root / PROFILE_REQUIREMENTS[profile]
    python = environment_python(venv_dir)
    return [
        [bootstrap_python, "-m", "venv", str(venv_dir)],
        [str(python), "-m", "pip", "install", "--upgrade", "pip"],
        [str(python), "-m", "pip", "install", "-r", str(requirements)],
    ]


def _activation_command(venv_dir: Path) -> str:
    if os.name == "nt":
        return f"& '{venv_dir / 'Scripts' / 'Activate.ps1'}'"
    return f"source {shlex.quote(str(venv_dir / 'bin' / 'activate'))}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a local ViGenX environment without guessing dependency scope."
    )
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILE_REQUIREMENTS),
        default="core",
        help="core=planning/UI, full=render/AI stack, dev=tests and planning",
    )
    parser.add_argument("--venv", default=".venv", help="Virtual environment path")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if sys.version_info < (3, 10):
        print("ViGenX requires Python 3.10 or newer.", file=sys.stderr)
        return 2

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    repo_root = Path(__file__).resolve().parents[1]
    venv_dir = Path(args.venv).expanduser().resolve()
    commands = build_commands(repo_root, venv_dir, args.profile)
    for command in commands:
        print(shlex.join(command))
        if not args.dry_run:
            subprocess.run(command, cwd=repo_root, check=True)

    if not args.dry_run:
        print("\nEnvironment ready.")
        print(f"Activate: {_activation_command(venv_dir)}")
        print(f"Verify:   {environment_python(venv_dir)} -m vigenx doctor")
        print(f"Start:    {environment_python(venv_dir)} -m vigenx web")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
