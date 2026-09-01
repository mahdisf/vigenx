"""Command-line interface for compiling an editing brief into workflow JSON."""
from __future__ import annotations

import argparse
import json
import sys

from config import load_config
from engine.planner import WorkflowPlanner, WorkflowPlanningError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Turn a plain-language video-editing brief into a validated ViGenX graph."
    )
    parser.add_argument("brief", help="What the workflow should do")
    parser.add_argument("--source", default="", help="Optional local path or media URL")
    parser.add_argument("--mode", choices=("auto", "local", "ai"), default="auto")
    parser.add_argument("--provider", choices=("gemini", "groq", "nvidia"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--config", default="config/default_config.toml")
    parser.add_argument("--output", help="Write graph JSON to this path instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = WorkflowPlanner(load_config(args.config)).plan(
            args.brief,
            source=args.source,
            mode=args.mode,
            provider=args.provider,
            model=args.model,
        )
    except WorkflowPlanningError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload = plan.to_dict()
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
        print(args.output)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
