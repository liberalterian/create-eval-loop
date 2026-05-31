---
name: create-rubric
description: Create scoped, production-ready rubrics and eval-case files for skill outputs, content, code, behavior, and batch evaluation. Use this when the user wants to create, refine, store, validate, or template a rubric.
---

# Create Rubric Skill

Create rubrics that are practical for humans, reliable for LLM evaluators, and easy to store at user, project, or sub-directory scope.

## Use this skill when

- The user asks to create a rubric, scoring framework, evaluator, quality gate, or eval cases.
- The user wants different rubric types: checklist, level anchors, weighted criteria, binary assertions, pairwise ranking, batch regeneration, test-driven code evaluation, or hybrid evaluation.
- A downstream skill needs a quality contract before it can run an eval loop.
- The user wants the rubric stored under `~/.claude/evals`, `./.claude/evals`, or a sub-directory `.claude/evals` folder.

## Non-goals

- Do not silently create high-stakes legal, medical, financial, or employment scoring rubrics without stating that domain-expert validation is required.
- Do not create subjective-only rubrics unless each subjective dimension has observable anchors.
- Do not optimize for complexity when a short deterministic eval file would solve the problem.

## Workflow

### Phase 0 — Determine mode

Infer the mode from the user request. If unclear, default to `interactive`.

| Mode | Use when |
|---|---|
| `interactive` | The user describes an assessment target but has not specified criteria. |
| `template` | The user names a common domain such as document quality, code review, research quality, brand voice, safety, or skill output quality. |
| `from-example` | The user gives an existing rubric or asks for a variant. |
| `eval-cases` | The desired evaluator is mostly deterministic prompt/output testing. |
| `hybrid` | Some checks are deterministic and others require LLM-as-judge. |

### Phase 1 — Collect the minimum viable context

Ask no more than one grouped question unless the user has already supplied the answers.

Collect:

1. **Assessment target** — content, code, behavior, skill output, batch outputs, or another artifact.
2. **Intended use** — draft feedback, go/no-go, production gate, ranking, compliance, skill self-improvement.
3. **Scope/storage level** — user, project, or sub-directory.
4. **Strictness** — suggested defaults: draft 60, PR/review 75, production 85, critical 90+.
5. **Rubric type** — checklist, level anchors, binary assertions, hybrid, pairwise, batch, test-driven.
6. **Hard stops** — any critical barrier that should fail the output regardless of total score.

### Phase 2 — Choose the rubric design

Prefer the simplest rubric that can reliably drive the decision.

| Rubric type | Best for | Scoring |
|---|---|---|
| `checklist` | Most LLM-evaluated quality gates | Each criterion has 5–10 yes/no observable checks. Score = checked / total × 100. |
| `level_anchor` | Tone, quality, judgment-heavy outputs | Five anchored levels: 0, 25, 50, 75, 100. Each level has observable indicators. |
| `binary_assertion` | Classifiers, formats, exact behavior | Pass/fail assertions such as exact, contains, regex, max_length. |
| `hybrid` | Production skills | Deterministic checks for format + LLM judge for quality. |
| `pairwise` | Choosing best of several outputs | Compare candidates against the same criteria; require rationale. |
| `batch_lift` | Improving many generated items | Judge all, regenerate bottom N%, re-judge, report lift. |
| `test_driven` | Code or structured output | Generate or use tests, run them, fix failures. |
| `composite` | Outputs that need multiple methods at once | Group criteria into weighted `sections`, each with its own method (e.g. a must-pass checklist + a level-anchor craft section). |

Use a **composite** rubric when one method cannot capture the decision — for
example, a deterministic must-pass section plus a subjective craft section.
Rules for sections:

- Each section declares a single `type` (its method) and a `weight`; section
  weights sum to 100.
- Criteria weights sum to 100 *within each section*.
- Mark sections that must pass on their own in `passing.required_sections`.
- Start from `templates/composite-rubric.yaml`.

### Phase 3 — Draft criteria

Rules for criteria:

- Use 3–8 criteria for most rubrics.
- Weights must sum to 100.
- Every criterion must be independently scorable.
- Avoid double-counting.
- Every criterion must have either checklist items or 5-level anchors.
- Add at least one pass and fail example for each criterion when possible.
- Mark required criteria and critical barriers explicitly.

Checklist item rules:

- Each item must be binary observable.
- Avoid vague language such as “good,” “beautiful,” “high quality,” or “feels right.”
- Convert subjective claims into visible evidence.
- Write the failure message as a concrete fix.

Level-anchor rules:

- Use exactly five levels: 0, 25, 50, 75, 100.
- Each level needs a concrete observable indicator.
- Make boundaries mutually exclusive.

### Phase 4 — Set acceptance conditions

Default settings:

```yaml
scoring:
  scale: 0-100
  aggregation: weighted_average
  threshold: 85
  per_criterion_floor: 70
  max_rounds: 4
  convergence:
    min_delta: 2
    patience: 2
passing:
  min_score: 85
  required_criteria: []
  critical_barriers: []
```

Use lower thresholds for draft feedback and higher thresholds for production or customer-facing output.

Critical barrier examples:

- Security vulnerability present.
- Required JSON schema invalid.
- Fabricated citation in research output.
- Missing required section in a generated contract-like document.
- Output violates a hard brand/safety/product constraint.

### Phase 5 — Pick storage path

Resolve storage from the user's intent.

| User says | Store at |
|---|---|
| “Use this everywhere,” “my default,” “personal rubric” | `~/.claude/evals/<name>.yaml` |
| “For this repo/project/app” | `./.claude/evals/<name>.yaml` |
| “Only for this feature/package/folder” | `./<subdir>/.claude/evals/<name>.yaml` |
| Gives explicit path | Use the explicit path. |

Always create the directory if needed.

### Phase 6 — Generate files

Generate at least the rubric file. Add eval cases when deterministic tests are useful.

Recommended outputs:

```text
.claude/evals/<rubric-name>.yaml
.claude/evals/<rubric-name>.eval-cases.json   # optional deterministic cases
.claude/eval-results/<rubric-name>/           # created during test runs
```

### Phase 7 — Validate

Before finalizing:

- Confirm weights sum to 100.
- Confirm every criterion has checks or anchors.
- Confirm each required criterion exists.
- Confirm threshold and floors are numeric 0–100.
- Confirm no purely subjective criterion lacks anchors.
- Confirm critical barriers have consequences.

When script access is available, run:

```bash
python .claude/skills/create-rubric/scripts/validate_rubric.py <path-to-rubric.yaml>
```

### Phase 8 — Final response

Report:

- Rubric path.
- Rubric type.
- Criteria count.
- Threshold/floor.
- Critical barriers.
- Suggested next step: run `test-eval` with 3–10 examples or patch a target skill with `add-eval-loop`.

## Built-in templates

### Skill Output Quality

Use for evaluating an AI skill's final answer or generated artifact.

Criteria:

1. **Task fulfillment** — The output satisfies the user's explicit request.
2. **Instruction adherence** — The output follows tool, format, citation, and style constraints.
3. **Completeness** — The output covers all required components without unexplained gaps.
4. **Accuracy/grounding** — Factual claims are sourced or reasonably justified.
5. **Usability** — The output is easy to apply, copy, run, or review.

### Code Review

Criteria:

1. Correctness and edge cases.
2. Security and input validation.
3. Maintainability and structure.
4. Tests and observability.
5. Performance where relevant.

### Research / Claims

Criteria:

1. Factual accuracy.
2. Source quality.
3. Balance and limitations.
4. Citation specificity.
5. Actionability.

### Brand / Voice

Criteria:

1. Voice match.
2. Specificity.
3. Differentiation.
4. Audience fit.
5. Conversion clarity.

### Deterministic Eval Cases

Use JSON cases when the output should follow a fixed behavior.

```json
[
  {
    "id": "case-id",
    "description": "What behavior is being tested",
    "input": "User prompt or test input",
    "expected_output": "Optional expected output",
    "assertions": [
      {"type": "contains", "value": "required string"},
      {"type": "not_contains", "value": "forbidden string"},
      {"type": "max_length", "value": 500},
      {"type": "regex", "value": "^#[ ]"}
    ]
  }
]
```

## Quality bar for generated rubrics

A rubric is not acceptable until it meets this internal checklist:

- [ ] Purpose and target are explicit.
- [ ] Storage scope is explicit.
- [ ] Criteria are observable and non-overlapping.
- [ ] Weights sum to 100.
- [ ] Overall threshold and per-criterion floor are present.
- [ ] Required criteria and hard stops are listed.
- [ ] Feedback messages tell the generator how to fix failures.
- [ ] The evaluator output format is JSON-compatible.
- [ ] The user can manually test it with `test-eval`.

## Output contract

When creating a rubric, write the actual file. Do not merely describe it unless the environment is read-only.
