#!/usr/bin/env python3
"""Patch a .claude/skills/<skill>/SKILL.md with an eval gate section.

This helper is intentionally conservative: it only inserts/replaces content between
<!-- eval-loop:start --> and <!-- eval-loop:end --> markers.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

# Source locations within the plugin, resolved relative to this script.
_SCRIPTS_DIR = Path(__file__).resolve().parent
_SHARED_DIR = _SCRIPTS_DIR.parents[1] / "_shared"

START = "<!-- eval-loop:start -->"
END = "<!-- eval-loop:end -->"

SNIPPET = f"""{START}

## Evaluation Gate

Before returning final output, run a rubric-based quality gate.

**Rubric:** `{{rubric}}`  
**Mode:** `{{mode}}`  
**Overall threshold:** `{{threshold}}` / 100  
**Per-criterion floor:** `{{floor}}` / 100  
**Max rounds:** `{{max_rounds}}`

### Pass condition

Return the output only when:

```text
overall_score >= {{threshold}}
AND every required criterion >= {{floor}}
AND no critical barrier is triggered
```

### Evaluation procedure

1. Draft the candidate output.
2. Evaluate the candidate against the rubric.
3. Return JSON-compatible evaluation results with overall score, per-criterion scores, failed checks, and targeted feedback.
4. If the candidate passes, return the final output.
5. If the candidate fails, improve exactly one target: critical barrier first, floor violation second, lowest weighted criterion third.
6. Re-evaluate the revised candidate from scratch. Do not include previous scores in the evaluator prompt.
7. Stop when the candidate passes, max rounds are reached, or score improvement stalls.
8. If max rounds are reached, return the best candidate and a concise note naming the remaining failed criteria.

### Improvement constraints

- Preserve the user's intent and requested format.
- Do not rewrite unrelated sections just to raise the score.
- Do not fabricate citations, tests, sources, or tool results.
- Do not hide evaluator uncertainty.
- Keep a brief score history when scripts or files are available.

### Running the scripted gate (script-backed / hybrid)

Bundled scripts are referenced via `${{{{CLAUDE_SKILL_DIR}}}}` so they run regardless
of the current working directory:

```bash
python "${{{{CLAUDE_SKILL_DIR}}}}/scripts/eval_runner.py" \\
  "${{{{CLAUDE_SKILL_DIR}}}}/eval/eval-cases.json" \\
  --out "${{{{CLAUDE_SKILL_DIR}}}}/eval/results/latest.json"

# Iterate. Agent mode (default) writes an improvement prompt and stops;
# add --autonomous --model-cmd "claude -p" to close the loop.
python "${{{{CLAUDE_SKILL_DIR}}}}/scripts/improve_skill_loop.py" \\
  --mode output --target <artifact> --threshold 0.95
```

{END}
"""


def render(args: argparse.Namespace) -> str:
    return SNIPPET.format(
        rubric=args.rubric,
        mode=args.mode,
        threshold=args.threshold,
        floor=args.floor,
        max_rounds=args.max_rounds,
    )


def patch_text(original: str, section: str) -> str:
    if START in original and END in original:
        before = original.split(START, 1)[0].rstrip()
        after = original.split(END, 1)[1].lstrip()
        return before + "\n\n" + section.rstrip() + "\n\n" + after
    return original.rstrip() + "\n\n" + section.rstrip() + "\n"


def scaffold_scripts(skill_dir: Path) -> None:
    scripts = skill_dir / "scripts"
    eval_dir = skill_dir / "eval" / "results"
    scripts.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / ".gitkeep").write_text("", encoding="utf-8")

    # Vendor the runner scripts and the shared core so the patched skill is
    # self-contained and runnable without the plugin on the path.
    for src in (
        _SHARED_DIR / "eval_core.py",
        _SCRIPTS_DIR / "eval_runner.py",
        _SCRIPTS_DIR / "improve_skill_loop.py",
    ):
        if src.exists():
            shutil.copy2(src, scripts / src.name)

    cases = skill_dir / "eval" / "eval-cases.json"
    if not cases.exists():
        cases.write_text("""[
  {
    "id": "example-format-check",
    "description": "Replace with a real prompt/output eval case.",
    "input": "Example user prompt",
    "output": "Example output",
    "assertions": [
      {"type": "min_length", "value": 20}
    ]
  }
]
""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True, help="Path to target SKILL.md")
    parser.add_argument("--rubric", required=True, help="Path/name of rubric")
    parser.add_argument("--mode", choices=["markdown-only", "script-backed", "hybrid"], default="hybrid")
    parser.add_argument("--threshold", type=float, default=85)
    parser.add_argument("--floor", type=float, default=70)
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument("--no-scaffold", action="store_true", help="Do not create eval/scripts scaffold")
    args = parser.parse_args()

    skill_path = Path(args.skill)
    if not skill_path.exists():
        raise SystemExit(f"Target skill not found: {skill_path}")
    original = skill_path.read_text(encoding="utf-8")
    updated = patch_text(original, render(args))
    skill_path.write_text(updated, encoding="utf-8")

    if args.mode in {"script-backed", "hybrid"} and not args.no_scaffold:
        scaffold_scripts(skill_path.parent)

    print(f"Patched {skill_path}")
    if args.mode in {"script-backed", "hybrid"} and not args.no_scaffold:
        print(f"Scaffolded scripts/eval directories under {skill_path.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
