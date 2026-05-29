---
name: test-eval
description: Manually test a rubric, eval cases, or evaluator against example prompts and outputs. Use this before trusting a rubric or newly upgraded skill.
---

# Test Eval Skill

Manually test rubrics and evaluator behavior against example prompts/outputs so users can catch vague criteria, brittle assertions, false positives, false negatives, and threshold problems before using an eval loop in a real skill.

## Use this skill when

- The user wants to test a rubric against sample outputs.
- The user wants to test an evaluator prompt.
- The user wants to compare outputs before/after improvement.
- The user wants to run deterministic eval cases.
- The user asks whether a rubric is too strict, too vague, or production-ready.
- The user wants to measure lift after regenerating weak outputs.

## Inputs

Accept any of the following:

1. A rubric path, name, or pasted rubric.
2. Prompt/output examples.
3. An eval-cases JSON file.
4. A target skill path.
5. A command that produces outputs from test prompts.
6. Desired threshold and floor.

## Testing modes

### Mode A — Deterministic assertion test

Use when examples include assertions such as exact, contains, regex, min_length, json_key.

Run:

```bash
python .claude/skills/test-eval/scripts/test_eval_runner.py path/to/eval-cases.json
```

Or against a command:

```bash
python .claude/skills/test-eval/scripts/test_eval_runner.py path/to/eval-cases.json \
  --command "python path/to/generate.py"
```

### Mode B — Rubric scoring smoke test

Use when a rubric has checklist or level-anchor criteria.

For each sample output:

1. Score against each criterion.
2. Identify which checks passed/failed.
3. Compute weighted total.
4. Apply threshold, floor, and critical barriers.
5. Explain whether the result matches human intuition.

### Mode C — Evaluator prompt test

Use when testing LLM-as-judge reliability.

Run the same example multiple times or through multiple judges when available. Flag instability if:

- Scores vary by more than 15 points on the same output.
- The judge misses deterministic format failures.
- Feedback is vague or not tied to failed checks.
- The judge rewards verbosity instead of meeting the rubric.

### Mode D — Batch lift test

Use when testing a regeneration loop.

1. Score all original outputs.
2. Select the bottom 25% or all failing outputs.
3. Regenerate only the weak outputs using judge feedback.
4. Re-score.
5. Report average lift, per-axis lift, and remaining failures.

## Manual scoring procedure

When script execution is not available, perform this procedure in the conversation:

1. Normalize the rubric into criteria, weights, thresholds, floors, and hard stops.
2. For each output, evaluate one criterion at a time.
3. For checklist criteria, mark each check true/false.
4. For level-anchor criteria, choose one of 0, 25, 50, 75, 100.
5. Compute weighted total.
6. Identify floor violations and critical barriers.
7. Decide pass/fail.
8. Provide concrete, targeted feedback.

## Required report format

```markdown
## Eval Test Report

**Rubric:** [name/path]
**Examples tested:** [N]
**Threshold:** [overall]
**Floor:** [floor]

### Results

| Case | Overall | Pass/Fail | Floor Violations | Critical Barriers |
|---|---:|---|---|---|
| case-1 | 87 | PASS | None | None |
| case-2 | 62 | FAIL | clarity | None |

### Failure Analysis

- [case-id]: [specific reason]

### Evaluator Quality Notes

- False positives: [none/list]
- False negatives: [none/list]
- Vague criteria: [none/list]
- Suggested rubric edits: [list]

### Next Actions

1. [Most important change]
2. [Second change]
```

## What makes a test successful

A test run is successful when:

- The evaluator catches known bad examples.
- The evaluator passes known good examples.
- Feedback points to specific failed criteria/checks.
- Thresholds separate acceptable from unacceptable examples.
- The rubric does not encourage unwanted behavior.

## Common evaluator problems and fixes

| Problem | Fix |
|---|---|
| Vague feedback such as “improve clarity” | Require feedback to name failed checks and a concrete edit. |
| All outputs score 80+ | Add harder checks or raise anchors. |
| Good examples fail due to format-only checks | Separate required criteria from optional polish. |
| Subjective criteria vary wildly | Convert to checklist items or add 5-level anchors. |
| Regeneration rewrites unrelated sections | Improve only the lowest failed criterion. |
| Output passes overall while one dimension is bad | Add per-criterion floor. |

## Safety rules

- Do not weaken eval cases just to make a skill pass.
- Do not treat a single LLM-judge score as authoritative for high-stakes decisions.
- Do not accept outputs with critical barriers, even if overall score is high.
- Do not hide disagreement between evaluators.

## Output contract

Always end with a practical recommendation:

- `Rubric ready to use`
- `Rubric needs edits before use`
- `Evaluator needs more examples`
- `Skill should not be auto-gated yet`
