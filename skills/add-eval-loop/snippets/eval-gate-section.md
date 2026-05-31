<!-- eval-loop:start -->

## Evaluation Gate

Before returning final output, run a rubric-based quality gate.

**Rubric:** `{rubric}`  
**Mode:** `{mode}`  
**Overall threshold:** `{threshold}` / 100  
**Per-criterion floor:** `{floor}` / 100  
**Max rounds:** `{max_rounds}`

### Pass condition

Return the output only when:

```text
overall_score >= {threshold}
AND every required criterion >= {floor}
AND no critical barrier is triggered
```

### Evaluation procedure

1. Draft the candidate output.
2. Evaluate the candidate against the rubric.
3. Return JSON-compatible evaluation results with overall score, per-criterion scores, failed checks, and targeted feedback.
4. If the candidate passes, return the final output.
5. If the candidate fails, improve exactly one target:
   - Critical barrier first.
   - Per-criterion floor violation second.
   - Lowest weighted criterion third.
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

Bundled scripts are referenced via `${CLAUDE_SKILL_DIR}` so they run regardless
of the current working directory:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/eval_runner.py" \
  "${CLAUDE_SKILL_DIR}/eval/eval-cases.json" \
  --out "${CLAUDE_SKILL_DIR}/eval/results/latest.json"

# Iterate. Agent mode (default) writes an improvement prompt and stops;
# add --autonomous --model-cmd "claude -p" to close the loop.
python "${CLAUDE_SKILL_DIR}/scripts/improve_skill_loop.py" \
  --mode output --target <artifact> --threshold 0.95
```

<!-- eval-loop:end -->
