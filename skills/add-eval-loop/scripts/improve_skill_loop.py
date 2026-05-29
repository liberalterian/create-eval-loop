#!/usr/bin/env python3
"""Skeleton improvement loop for skill prompt iteration.

This script intentionally avoids making API calls by default. It runs eval cases,
records failures, and writes an improvement prompt that Claude Code or another
agent can use to update SKILL.md safely.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run_evals(runner: Path, cases: Path, command: str | None, out: Path) -> dict:
    cmd = ["python", str(runner), str(cases), "--out", str(out)]
    if command:
        cmd.extend(["--command", command])
    proc = subprocess.run(cmd, text=True, capture_output=True)
    try:
        return json.loads(out.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Eval runner failed: {proc.stdout}\n{proc.stderr}") from exc


def write_improvement_prompt(skill_path: Path, results: dict, prompt_path: Path, threshold: float) -> None:
    failures = [r for r in results.get("results", []) if not r.get("passed")]
    current_skill = skill_path.read_text(encoding="utf-8")
    prompt = f"""# Skill Improvement Prompt

You are improving `{skill_path}` using deterministic eval failures.

Current pass rate: {results.get('pass_rate', 0):.1%}
Target pass rate: {threshold:.1%}
Generated: {datetime.now(timezone.utc).isoformat()}

## Rules

- Modify only the target skill unless the user explicitly authorizes other files.
- Preserve all behavior that already passes.
- Fix root causes, not just individual examples.
- Keep the skill concise and readable.
- Do not weaken tests to pass.

## Failing cases

```json
{json.dumps(failures, indent=2)}
```

## Current SKILL.md

```markdown
{current_skill}
```

Return the improved SKILL.md content only.
"""
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", default="SKILL.md")
    parser.add_argument("--cases", default="eval/eval-cases.json")
    parser.add_argument("--runner", default="scripts/eval_runner.py")
    parser.add_argument("--command", help="Command to run candidate skill; receives prompt on stdin")
    parser.add_argument("--threshold", type=float, default=0.95, help="Pass rate threshold, 0-1")
    parser.add_argument("--max-iterations", type=int, default=5)
    args = parser.parse_args()

    skill = Path(args.skill)
    cases = Path(args.cases)
    runner = Path(args.runner)
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, args.max_iterations + 1):
        out = results_dir / f"iteration-{i}.json"
        results = run_evals(runner, cases, args.command, out)
        pass_rate = results.get("pass_rate", 0)
        print(f"Iteration {i}: pass_rate={pass_rate:.1%}")
        if pass_rate >= args.threshold:
            print("Target reached.")
            return 0
        prompt_path = results_dir / f"improvement-prompt-{i}.md"
        write_improvement_prompt(skill, results, prompt_path, args.threshold)
        print(f"Wrote improvement prompt: {prompt_path}")
        print("Apply the prompt with Claude Code or manually update the skill, then re-run.")
        return 1

    print("Max iterations reached without passing threshold.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
