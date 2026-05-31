#!/usr/bin/env python3
"""Iterative improvement loop for skill prompt iteration.

By default this runs in *agent mode*: it runs eval cases, and when they fail it
writes an improvement prompt for Claude Code (or another agent) to apply, then
stops with exit code 2 ("agent action required"). The agent applies the fix and
re-invokes.

When ``--apply-cmd`` is supplied the loop is fully closed: after each failing
round it runs that command (which is expected to mutate the target skill using
the written improvement prompt), then re-evaluates -- repeating until the pass
threshold is met, ``--max-iterations`` is hit, or improvement converges. WS3's
``--autonomous`` mode is a thin wrapper that supplies a model CLI as the
apply command.
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


def should_stop(history: list[float], min_delta: float, patience: int) -> bool:
    """Return True when the last ``patience`` pass-rate gains are all below
    ``min_delta`` (improvement has stalled). Needs at least ``patience+1``
    samples to trigger."""
    if patience <= 0 or len(history) < patience + 1:
        return False
    recent = history[-(patience + 1):]
    deltas = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
    return all(d < min_delta for d in deltas)


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
    parser.add_argument("--min-delta", type=float, default=0.0, help="Min pass-rate gain per round before convergence stop")
    parser.add_argument("--patience", type=int, default=2, help="Rounds of sub-min-delta gain before stopping")
    parser.add_argument("--apply-cmd", help="Command that applies the improvement prompt to the skill (closes the loop). Receives the prompt path as its final argument.")
    args = parser.parse_args()

    skill = Path(args.skill)
    cases = Path(args.cases)
    runner = Path(args.runner)
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    history: list[float] = []
    for i in range(1, args.max_iterations + 1):
        out = results_dir / f"iteration-{i}.json"
        results = run_evals(runner, cases, args.command, out)
        pass_rate = results.get("pass_rate", 0)
        history.append(pass_rate)
        print(f"Iteration {i}: pass_rate={pass_rate:.1%}")

        if pass_rate >= args.threshold:
            print("Target reached.")
            return 0
        if should_stop(history, args.min_delta, args.patience):
            print(f"Improvement stalled (last {args.patience} gains < {args.min_delta}). Stopping.")
            return 1

        prompt_path = results_dir / f"improvement-prompt-{i}.md"
        write_improvement_prompt(skill, results, prompt_path, args.threshold)
        print(f"Wrote improvement prompt: {prompt_path}")

        if not args.apply_cmd:
            # Agent mode: hand off to Claude Code / the user to apply the fix.
            print("Apply the prompt with Claude Code or manually update the skill, then re-run.")
            return 2
        # Closed-loop mode: apply the fix, then continue iterating.
        proc = subprocess.run(f"{args.apply_cmd} {prompt_path}", shell=True, text=True)
        if proc.returncode != 0:
            print(f"Apply command failed (exit {proc.returncode}). Stopping.")
            return 1

    print("Max iterations reached without passing threshold.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
