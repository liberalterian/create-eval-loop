# Upgrading Existing Skills with Eval Loops

Use this workflow when adding evaluation gates to `.claude/skills/<skill>/SKILL.md`.

## 1. Inspect the target skill

Identify:

- The skill's primary output artifact.
- Its quality-critical failure modes.
- Whether the output can be improved automatically without harming user intent.
- Existing scripts or directories.
- Whether the user wants markdown-only, script-backed, or hybrid evaluation.

## 2. Select or create a rubric

Prefer an existing rubric when possible. Otherwise create a new one in the nearest appropriate scope.

## 3. Patch `SKILL.md`

Insert an `Evaluation Gate` section near the output/finalization instructions. Keep the patch bounded by markers:

```markdown
<!-- eval-loop:start -->
...
<!-- eval-loop:end -->
```

This makes future updates idempotent and reversible.

## 4. Add scripts only when useful

Use pure markdown when the evaluator is simple and manually invoked. Add scripts when you need:

- Deterministic assertion checks.
- Repeatable prompt/output tests.
- Batch scoring and lift reports.
- JSON logs for auditability.
- A loop that can run without more user input.

## 5. Manual test before trusting

Run `test-eval` on 3–10 examples before letting the target skill automatically accept outputs.

## 6. Acceptance conditions

Default pass condition:

```text
overall_score >= threshold AND every required criterion >= floor AND no critical barriers are triggered
```

Use a circuit breaker:

```text
max_rounds = 3 to 5
stop if score improvement < 2 points for 2 consecutive rounds
stop if the same criterion fails for 3 consecutive rounds
```
