---
name: build-eval-loop
description: >
  Orchestrate end-to-end setup of a rubric-based eval loop for a target skill:
  create a rubric, patch the skill with an evaluation gate, scaffold test cases,
  run the gate, and iterate to green with human sign-off. Use when the user
  wants to stand up evaluation for a skill from scratch in one guided flow.
disable-model-invocation: true
allowed-tools: Read Edit Write Bash(python3 *) Bash(python *) AskUserQuestion
arguments: [target_skill, rubric_intent]
---

# Build Eval Loop Skill

Orchestrates `create-rubric`, `add-eval-loop`, and `test-eval` into one guided
flow, then drives the loop to a passing state or a circuit breaker.

## Use this skill when

- The user wants to set up evaluation for a skill from scratch.
- They say "add an eval loop to X", "make X self-checking", or "wire up a
  rubric + gate + tests for X".

## Operating principles

- Run **inline**, never `context: fork` — the sign-off checkpoints need the live
  conversation and `AskUserQuestion`.
- Separate the phases: create, patch, and test stay distinct and reversible.
- Honor circuit breakers. On max rounds, return the best state and name the
  remaining failures instead of looping forever.
- Keep a live status checklist in your replies so the user can see progress.

## Inputs

- `$target_skill` — path to the target `SKILL.md`.
- `$rubric_intent` — an existing rubric path, or a description to create one.

If either is missing, ask one concise question before starting.

## Flow

Maintain this checklist and update it as you go:

```text
[ ] 1. Preflight
[ ] 2. Create + validate rubric        (sign-off #1)
[ ] 3. Patch target skill              (sign-off #2)
[ ] 4. Scaffold + run test-eval        (sign-off #3)
[ ] 5. Iterate to green or breaker
[ ] 6. Final report
```

### 1. Preflight

Confirm the target exists and the environment is ready:

```bash
python .claude/skills/build-eval-loop/scripts/preflight.py \
  --target $target_skill --rubric <rubric-path-if-existing>
```

### 2. Create + validate rubric → sign-off #1

- Invoke `create-rubric` (or reuse an existing rubric) for `$rubric_intent`.
  Read any `context.references` so the rubric reflects expert grounding.
- Validate it with `create-rubric/scripts/validate_rubric.py`.
- **Sign-off #1 (draft criteria):** surface criteria, weights, thresholds, and
  barriers; `AskUserQuestion` → approve / edit / reject. Apply edits and
  re-validate. Record the decision:

```bash
python .claude/skills/_shared/feedback.py --rubric <name> \
  --stage draft-criteria --decision <approve|edit|reject> --text "<note>"
```

### 3. Patch target skill → sign-off #2

- **Sign-off #2 (pre-patch):** confirm target path, rubric, thresholds, loop
  mode (`output`/`skill`) and automation (`agent`/`autonomous`) via
  `AskUserQuestion` before writing changes (patching is a side effect).
- Patch with `add-eval-loop/scripts/patch_skill_eval_loop.py`. This vendors the
  runner scripts, `eval_core.py`, and `feedback.py` into the target. Record the
  decision (`--stage pre-patch`).

### 4. Scaffold + run test-eval → sign-off #3

- Author or refine `eval/eval-cases.json` (use `test-eval` for prompt/output
  cases) and run the deterministic gate:

```bash
python <target-dir>/scripts/eval_runner.py \
  <target-dir>/eval/eval-cases.json --out <target-dir>/eval/results/latest.json
```

- **Sign-off #3 (post test-eval):** show the first results; `AskUserQuestion`
  before trusting the rubric. Record the decision (`--stage post-test-eval`).

### 5. Iterate to green or breaker

Drive the loop. Agent mode (default) applies fixes yourself between runs;
autonomous closes the loop unattended:

```bash
python <target-dir>/scripts/improve_skill_loop.py \
  --mode output --target <artifact-or-SKILL.md> \
  --cases <target-dir>/eval/eval-cases.json \
  --threshold 0.95 --max-iterations 4
  # add --autonomous --model-cmd "claude -p" only if the user authorized it
```

Re-diagnose on each failure. Stop when the gate passes, max rounds are reached,
or improvement stalls (`should_stop`). Never weaken cases to pass.

### 6. Final report

Report: rubric path, target patched, loop mode/automation, final pass rate,
remaining failures (if any), and the files changed. Point to the feedback log at
`.claude/eval-results/<rubric>/feedback.md`.

## Circuit breakers

- `max-iterations` (default 4).
- Convergence stall via `--min-delta` / `--patience`.
- Manual review required when a critical barrier remains after two rounds.
