#!/usr/bin/env python3
"""Iterative improvement loop with two orthogonal choices.

**What is optimized** (`--mode`):

- ``skill``  — rewrite the target ``SKILL.md`` so it produces better outputs.
- ``output`` — rewrite a single output artifact until it passes the rubric.

**How fixes are applied** (automation):

- *agent* (default): run evals, and on failure write an improvement prompt for
  Claude Code (or you) to apply, then stop with exit code 2 ("agent action
  required"). The agent applies the fix and re-invokes.
- *closed loop*: either ``--apply-cmd CMD`` (CMD mutates the target using the
  written prompt) or ``--autonomous --model-cmd "claude -p"`` (a model CLI is
  fed the prompt on stdin and its stdout replaces the target). Both iterate
  until the threshold is met, ``--max-iterations`` is hit, or improvement
  stalls. ``--autonomous`` fails soft to agent mode when no model CLI is found.
"""
from __future__ import annotations

import argparse
import json
import shutil
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


def write_improvement_prompt(target: Path, results: dict, prompt_path: Path, threshold: float, mode: str) -> None:
    failures = [r for r in results.get("results", []) if not r.get("passed")]
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    if mode == "output":
        artifact_label = f"output artifact `{target}`"
        return_line = f"Return the improved contents of `{target}` only."
        current_label = f"Current `{target.name}`"
    else:
        artifact_label = f"skill `{target}`"
        return_line = "Return the improved SKILL.md content only."
        current_label = "Current SKILL.md"
    prompt = f"""# Improvement Prompt ({mode} mode)

You are improving the {artifact_label} using deterministic eval failures.

Current pass rate: {results.get('pass_rate', 0):.1%}
Target pass rate: {threshold:.1%}
Generated: {datetime.now(timezone.utc).isoformat()}

## Rules

- Modify only the target above unless the user explicitly authorizes other files.
- Preserve all behavior that already passes.
- Fix root causes, not just individual examples.
- Do not weaken tests to pass.

## Failing cases

```json
{json.dumps(failures, indent=2)}
```

## {current_label}

```
{current}
```

{return_line}
"""
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")


def model_available(model_cmd: str) -> bool:
    """Return True when the first token of ``model_cmd`` resolves to an
    executable on PATH (used for --autonomous fail-soft)."""
    if not model_cmd:
        return False
    first = model_cmd.split()[0]
    return shutil.which(first) is not None


def apply_with_model(model_cmd: str, prompt_path: Path, target: Path) -> bool:
    """Feed the prompt to ``model_cmd`` on stdin and write its stdout to the
    target. Returns True on success."""
    prompt = prompt_path.read_text(encoding="utf-8")
    proc = subprocess.run(model_cmd, input=prompt, text=True, shell=True, capture_output=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        return False
    target.write_text(proc.stdout, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["output", "skill"], default="skill",
                        help="Optimize the SKILL.md (skill) or a single output artifact (output)")
    parser.add_argument("--skill", default="SKILL.md", help="Target file (alias of --target)")
    parser.add_argument("--target", help="File to optimize; defaults to --skill")
    parser.add_argument("--cases", default="eval/eval-cases.json")
    parser.add_argument("--runner", default="scripts/eval_runner.py")
    parser.add_argument("--command", help="Command to produce candidate output; receives input on stdin")
    parser.add_argument("--threshold", type=float, default=0.95, help="Pass rate threshold, 0-1")
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--min-delta", type=float, default=0.0, help="Min pass-rate gain per round before convergence stop")
    parser.add_argument("--patience", type=int, default=2, help="Rounds of sub-min-delta gain before stopping")
    parser.add_argument("--apply-cmd", help="Command that applies the improvement prompt to the target. Receives the prompt path as its final argument.")
    parser.add_argument("--autonomous", action="store_true", help="Close the loop with a model CLI (see --model-cmd)")
    parser.add_argument("--model-cmd", default="claude -p", help="Model CLI used in --autonomous mode; fed the prompt on stdin, stdout replaces the target")
    args = parser.parse_args()

    target = Path(args.target or args.skill)
    cases = Path(args.cases)
    runner = Path(args.runner)
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # Resolve automation strategy, with --autonomous fail-soft to agent mode.
    autonomous = args.autonomous
    if autonomous and not model_available(args.model_cmd):
        print(f"--autonomous requested but model CLI not found: {args.model_cmd!r}. Falling back to agent mode.")
        autonomous = False

    history: list[float] = []
    for i in range(1, args.max_iterations + 1):
        out = results_dir / f"iteration-{i}.json"
        results = run_evals(runner, cases, args.command, out)
        pass_rate = results.get("pass_rate", 0)
        history.append(pass_rate)
        print(f"Iteration {i} ({args.mode}): pass_rate={pass_rate:.1%}")

        if pass_rate >= args.threshold:
            print("Target reached.")
            return 0
        if should_stop(history, args.min_delta, args.patience):
            print(f"Improvement stalled (last {args.patience} gains < {args.min_delta}). Stopping.")
            return 1

        prompt_path = results_dir / f"improvement-prompt-{i}.md"
        write_improvement_prompt(target, results, prompt_path, args.threshold, args.mode)
        print(f"Wrote improvement prompt: {prompt_path}")

        if autonomous:
            if not apply_with_model(args.model_cmd, prompt_path, target):
                print("Model apply step failed or produced empty output. Stopping.")
                return 1
            continue
        if args.apply_cmd:
            proc = subprocess.run(f"{args.apply_cmd} {prompt_path}", shell=True, text=True)
            if proc.returncode != 0:
                print(f"Apply command failed (exit {proc.returncode}). Stopping.")
                return 1
            continue
        # Agent mode: hand off to Claude Code / the user to apply the fix.
        print("Apply the prompt with Claude Code or manually update the target, then re-run.")
        return 2

    print("Max iterations reached without passing threshold.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
