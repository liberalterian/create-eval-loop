---
name: add-eval-loop
description: Upgrade an existing .claude/skills/<skill>/SKILL.md with a rubric-based evaluation gate, iterative feedback loop, and optional Python scripts for repeatable eval testing.
---

# Add Eval Loop Skill

Upgrade an existing skill so it can evaluate its own output, generate targeted feedback, improve the weakest criterion, and accept the output only when the configured score threshold and floors are met.

## Use this skill when

- The user asks to add, install, retrofit, upgrade, or patch an eval loop into an existing skill.
- The user has a skill directory such as `.claude/skills/<skill>/` and wants `SKILL.md` modified.
- The user wants a case-by-case choice between pure markdown evaluation and script-backed evaluation.
- The user wants generated Python scripts placed under `.claude/skills/<skill>/scripts/`.
- The user wants the skill to keep iterating until it passes rubric thresholds or hits a circuit breaker.

## Operating principle

Patch the smallest useful surface area. Make changes idempotent, auditable, and reversible.

Use bounded markers:

```markdown
<!-- eval-loop:start -->
...
<!-- eval-loop:end -->
```

If markers already exist, replace only that region. Do not duplicate eval-loop instructions.

## Inputs to collect

If not provided, infer from the target skill and ask at most one concise question.

Required:

1. **Target skill path** — e.g. `.claude/skills/research-writer/SKILL.md`.
2. **Rubric path or rubric intent** — existing `.yaml` or a description to create one.
3. **Loop mode** — markdown-only, script-backed, or hybrid (how the gate is embedded).
4. **Iteration target** — `output` (optimize one artifact until it passes) or `skill` (optimize the SKILL.md itself). Default `output`.
5. **Automation** — `agent` (scripts emit a prompt; Claude/you apply the fix) or `autonomous` (a model CLI closes the loop). Default `agent`.
6. **Thresholds** — default `overall >= 85`, `floor >= 70`, max rounds `4`.
7. **Acceptance behavior** — return final output, return final + report, or stop for human review.

Optional:

- Example prompts/outputs.
- Target output artifact path.
- Whether external model CLIs such as `codex` or `gemini` may be used.
- Whether to save history in `.claude/eval-results/`.

## Mode selection

### Markdown-only mode

Use when:

- The skill output is short or qualitative.
- The user wants no scripts.
- Manual judgement is acceptable.

Patch `SKILL.md` with an evaluation gate only.

### Script-backed mode

Use when:

- Deterministic test cases are needed.
- The output has schema/format constraints.
- Repeated testing is expected.
- The user wants a measurable log.

Create:

```text
.claude/skills/<skill>/scripts/eval_runner.py
.claude/skills/<skill>/scripts/improve_skill_loop.py
.claude/skills/<skill>/eval/eval-cases.json
.claude/skills/<skill>/eval/results/
```

### Hybrid mode

Use when deterministic assertions cover format/schema and LLM-as-judge covers content quality.

### Iteration target and automation (orthogonal to loop mode)

`scripts/improve_skill_loop.py` exposes two independent dimensions:

- **`--mode output`** rewrites a single output artifact (`--target <file>`)
  until it passes the rubric. **`--mode skill`** rewrites the target
  `SKILL.md` so it produces better outputs.
- **Automation:** by default the loop runs in *agent mode* — it writes an
  improvement prompt under `eval/results/` and exits with code `2` for Claude
  Code (or you) to apply, then re-runs. Pass **`--autonomous --model-cmd
  "claude -p"`** to close the loop with a model CLI (the prompt is fed on
  stdin; its stdout replaces the target). Autonomous mode fails soft to agent
  mode when no model CLI is found. You can also supply your own
  **`--apply-cmd`** for a custom closed loop.

Defaults stay conservative: `output` + agent. Choose `skill` and/or
`autonomous` only when the user asks for self-improvement or unattended runs.

Patch `SKILL.md`, add scripts, and link a YAML rubric in `.claude/evals/`.

## Patch workflow

### Step 1 — Inspect target skill

Read:

```text
.claude/skills/<skill>/SKILL.md
```

Identify:

- Skill purpose and output contract.
- Existing finalization instructions.
- Existing scripts directory.
- Any user, system, or project constraints.
- Whether the skill already has an evaluation loop.

### Step 2 — Choose or create rubric

If an explicit rubric path exists, use it.

If not, create or instruct the user to run `create-rubric` first. For straightforward cases, generate a minimal rubric immediately and store it at the nearest useful scope.

Default storage:

```text
./.claude/evals/<skill-name>-quality.yaml
```

### Step 3 — Insert evaluation gate

Insert before the skill's final response/output instructions when possible. If no obvious location exists, append near the end.

The inserted section must include:

- Rubric path or rubric name.
- Scoring method.
- Pass condition.
- Iteration cap.
- What to improve first.
- What to log.
- What to return to the user.

Use the snippet in `snippets/eval-gate-section.md` as a base.

### Step 4 — Add scripts if requested or useful

When script-backed/hybrid mode is selected, add scripts under the target skill's parent directory:

```text
.claude/skills/<skill>/scripts/eval_runner.py
.claude/skills/<skill>/scripts/improve_skill_loop.py
```

Also create:

```text
.claude/skills/<skill>/eval/eval-cases.json
.claude/skills/<skill>/eval/results/.gitkeep
```

### Step 5 — Validate idempotency

After patching:

- Confirm exactly one `<!-- eval-loop:start -->` marker.
- Confirm exactly one `<!-- eval-loop:end -->` marker.
- Confirm the referenced rubric exists or is clearly marked TODO.
- Confirm scripts compile if Python is available.

### Step 6 — Final response

Report:

- Target skill patched.
- Files created/updated.
- Rubric path.
- Loop mode.
- Pass condition.
- How to manually test with `test-eval`.

## Evaluation gate behavior to insert

Target skills should follow this logic after drafting their output but before returning it:

```text
1. Generate candidate output.
2. Evaluate candidate against configured rubric.
3. If overall >= threshold AND every required criterion >= floor AND no critical barrier is triggered: accept output.
4. If not passed: identify the single highest-priority failure.
   - Critical barriers first.
   - Floor violations second.
   - Lowest weighted criterion third.
5. Improve only the targeted issue.
6. Re-evaluate from a clean candidate output without including prior scores in the evaluator prompt.
7. Repeat until pass condition is met, max rounds is hit, or convergence stalls.
8. Return the best output and, when appropriate, a short eval summary.
```

## Evaluator prompt contract

Use this prompt shape for LLM-as-judge evaluation:

```text
You are a strict evaluator. Score only the artifact below using the rubric below.
Do not use prior round feedback or improvement history.
Return only JSON matching the schema.

## Rubric
[criteria, weights, checks, anchors, thresholds]

## Artifact
[output to evaluate]

## Required JSON
{
  "overall": 0,
  "passed": false,
  "criteria": {
    "criterion_id": {
      "score": 0,
      "passed": false,
      "checks": {"check_id": true},
      "feedback": "specific fix"
    }
  },
  "critical_barriers": [],
  "suggestions": ["single concrete action"]
}
```

## Improvement prompt contract

```text
Improve the artifact by addressing only the target failure.
Preserve user intent, correct content, working code, citations, and all passing requirements.
Do not rewrite unrelated sections.

Target failure:
[criterion/check/feedback]

Artifact:
[current candidate]
```

## Circuit breakers

Always include at least two:

- `max_rounds`: default 4.
- `convergence_min_delta`: default 2 points.
- `same_failure_limit`: default 3.
- `manual_review_required`: when a critical barrier remains after two attempts.

## Scripted patch helper

When filesystem access is available, you may use:

```bash
python .claude/skills/add-eval-loop/scripts/patch_skill_eval_loop.py \
  --skill .claude/skills/<skill>/SKILL.md \
  --rubric .claude/evals/<rubric>.yaml \
  --mode hybrid \
  --threshold 85 \
  --floor 70
```

The helper creates an idempotent eval section and, for script-backed/hybrid
mode, vendors `eval_core.py` + the runner scripts into the target.

To drive iteration after scaffolding, use the loop runner. Agent mode (default)
writes an improvement prompt and exits `2` for you/Claude to apply; add
`--autonomous` to close the loop with a model CLI:

```bash
python .claude/skills/<skill>/scripts/improve_skill_loop.py \
  --mode output \                 # or: skill (optimize the SKILL.md itself)
  --target <artifact-or-SKILL.md> \
  --cases .claude/skills/<skill>/eval/eval-cases.json \
  --threshold 0.95 --max-iterations 4 \
  # --autonomous --model-cmd "claude -p"
```

## Internal quality checklist

Before finishing, verify:

- [ ] Target skill path is correct.
- [ ] Existing skill content outside eval markers is preserved.
- [ ] The patch names the rubric path.
- [ ] The patch defines pass/fail logic.
- [ ] The patch instructs the skill to improve only the targeted issue.
- [ ] The loop has a circuit breaker.
- [ ] Script-backed mode has testable files.
- [ ] The user receives exact files changed.
