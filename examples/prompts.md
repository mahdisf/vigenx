# Prompt examples

These briefs exercise the deterministic local planner. Each committed JSON file
was generated from the repository root with `python -m vigenx plan` and then
given a stable graph ID so diffs remain reproducible.

| Brief | Source | Workflow |
| --- | --- | --- |
| Create three vertical podcast clips under 45 seconds with yellow captions and background music. | `media/podcast.mp4` | [`workflows/podcast-shorts.json`](workflows/podcast-shorts.json) |
| Make one privacy-safe highlight reel under 45 seconds, blur faces, and add captions. | `media/interview.mp4` | [`workflows/privacy-highlight.json`](workflows/privacy-highlight.json) |
| Make a cinematic vertical branded reel with a logo, intro, outro, background music, and a thumbnail. | `media/product-demo.mp4` | [`workflows/branded-reel.json`](workflows/branded-reel.json) |

Regenerate an example before changing planner behavior:

```bash
python -m vigenx plan \
  "Create three vertical podcast clips under 45 seconds with yellow captions and background music." \
  --source media/podcast.mp4 \
  --mode local \
  --output examples/workflows/podcast-shorts.json
```

The planner deliberately leaves logo, intro/outro, and music paths empty. Review
and select licensed assets in the editor before running a generated workflow.
