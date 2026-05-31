# Rubric Schema

The skills prefer YAML because it is easy to review and diff, but JSON is also acceptable for scripts and test cases.

## YAML rubric shape

```yaml
name: document-quality
version: 1.0.0
description: Evaluates a document against observable quality criteria.
scope:
  type: content            # content | behavior | combined | batch | skill
  file_patterns:
    - "*.md"
rubric_type: checklist     # checklist | level_anchor | binary_assertion | hybrid | pairwise | test_driven
scoring:
  scale: 0-100
  aggregation: weighted_average
  threshold: 85
  per_criterion_floor: 70
  max_rounds: 4
  convergence:
    min_delta: 2
    patience: 2
criteria:
  clarity:
    weight: 30
    threshold: 80
    description: The output is easy to understand and organized.
    method: checklist
    checks:
      - id: clear-purpose
        type: binary
        statement: The output states its purpose in the first section.
        message: Add a clear purpose statement near the top.
      - id: logical-order
        type: binary
        statement: Sections appear in a logical sequence.
        message: Reorder sections so the reader can follow the argument.
    examples:
      pass: The document opens with a clear objective and proceeds from context to actions.
      fail: The document jumps into details without explaining its purpose.
passing:
  min_score: 85
  required_criteria:
    - clarity
  allow_critical_barrier_override: false
reporting:
  save_history: true
  output_dir: .claude/eval-results
```

## Supported check types

| Type | Purpose |
|---|---|
| `binary` | Human/LLM-readable yes/no checklist item. |
| `presence` | Required string, regex, section, field, or pattern must exist. |
| `absence` | Forbidden string, regex, or pattern must not exist. |
| `pattern` | Output must fully match a structural regex pattern. |
| `regex` | A regex pattern must be found somewhere in the output. |
| `exact` | Output exactly equals a value. Useful for classifiers. |
| `contains` | Output contains a value. |
| `not_contains` | Output does not contain a value. |
| `min_length` | Output length is at least a minimum. |
| `max_length` | Output length is under a maximum. |
| `json_schema` | Output parses as JSON and contains a required dotted key path. Alias: `json_key`. |
| `custom` | LLM-as-judge or human evaluator prompt. Use sparingly. |

The deterministic types (everything except `binary` and `custom`) are implemented by `skills/_shared/eval_core.py`; `eval_core.ASSERTION_TYPES` is the canonical list.

## Evaluation result shape

```json
{
  "rubric": "document-quality",
  "overall": 87.5,
  "passed": true,
  "criteria": {
    "clarity": {
      "score": 90,
      "passed": true,
      "checks": {
        "clear-purpose": true,
        "logical-order": true
      },
      "feedback": "The purpose and order are clear."
    }
  },
  "violations": [],
  "suggestions": [
    "Tighten the conclusion to include one next action."
  ],
  "metadata": {
    "round": 1,
    "model_status": {"primary": "available"},
    "low_confidence": false
  }
}
```
