# Implementation Plan — Rubric Eval Loop Plugin

Status: approved (plan-only round). Work tracked on branch
`claude/eval-loop-rubric-features-YA7IJ`.

## Locked decisions

1. **Self-improvement automation** — agent-in-the-loop is the default; an opt-in
   `--autonomous` flag wires a model CLI to close the loop unattended.
2. **Multimodal rubrics** — a new `sections` layer, with a compatibility shim
   that treats a flat top-level `criteria:` as one implicit section.
3. **Human-in-the-loop** — interactive sign-off checkpoints (via
   `AskUserQuestion`) plus an asset/reference grounding block in the rubric.
4. **Scope** — this round is plan + WS0 foundation/bugfixes; later milestones
   implement the features.

## Grounding facts (Claude Code docs)

- The plugin manifest is optional metadata only (`name`, `description`,
  `version`, `author`, `homepage`, `repository`, `license`, `keywords`).
  Skills are auto-discovered from `skills/<name>/SKILL.md`. The current
  `manifest.json` `skills` array and `rubric_storage` field are non-standard.
- SKILL.md frontmatter supports `name`, `description`, `allowed-tools`,
  `disallowed-tools`, `disable-model-invocation`, `context: fork`, `agent`,
  `arguments`, `user-invocable`.
- `${CLAUDE_SKILL_DIR}` references files bundled with a skill; dynamic context
  injection via `` !`cmd` `` runs a command and inlines its output.
- Interactive (sign-off) skills must run **inline**, not `context: fork`
  (forked subagents have no conversation access). Autonomous/background loops
  should set `disallowed-tools: AskUserQuestion` so they never block on a human.

Sources: https://code.claude.com/docs/en/plugins-reference ,
https://code.claude.com/docs/en/skills

## WS0 — Foundation & bugfixes (this milestone, M0)

- **0.1** New shared module `skills/_shared/eval_core.py` (single file for easy
  vendoring): canonical assertion engine, command runner that records non-zero
  exits explicitly, and a deterministic rubric **scoring engine** (weighted
  aggregation, per-criterion floors, required criteria/sections, critical
  barriers, section-aware).
- **0.2** Collapse the two duplicate runners into thin CLIs over `eval_core`.
- **0.3** Fix `improve_skill_loop.py` so the loop actually iterates and honors
  convergence + circuit breakers.
- **0.4** Fix `patch_skill_eval_loop.py::scaffold_scripts` to vendor the runner
  scripts + `eval_core.py` into the target, not just `mkdir`.
- **0.5** Test harness: `requirements.txt`, `pytest` suite, SessionStart hook.
- **0.6** Housekeeping: README install block, remove committed
  `test-results.json`, reconcile snippet placeholders, fix manifest to the
  documented schema, fix author.

## WS1 — Multimodal `sections` rubrics (M1)

Additive `sections` schema; flat `criteria` shim; two-level weight validation;
section-aware aggregation; `composite-rubric.yaml` template; doc updates.

## WS2 — Human-in-the-loop (M3)

`context.references` + `context.expert_notes` grounding block; sign-off
checkpoints at (1) draft criteria, (2) post test-eval, (3) pre-patch; audit
trail under `.claude/eval-results/<rubric>/feedback.md`.

## WS3 — `add-eval-loop` dual mode (M2)

`--mode {output,skill}` (optimize the artifact vs the SKILL.md) and
`--autonomous` (model CLI closes the loop) with all circuit breakers.

## WS4 — Orchestrator skill `build-eval-loop` (M4)

Chains create-rubric → add-eval-loop → test-eval, runs tests, iterates to green
or circuit-breaker, with sign-off checkpoints. Runs inline;
`disable-model-invocation: true`.

## Sequencing

M0 (WS0) → M1 (WS1) → M2 (WS3) → M3 (WS2) → M4 (WS4). Each milestone ships with
green `pytest` and a real-asset dry run before the next begins.

## Open items to confirm during implementation

- Vendor `eval_core.py` into each patched target's `scripts/` (self-contained
  installs) with a version stamp.
- `--autonomous` fails soft to agent mode when no model CLI is present.
- Sections are single-`type`; the rubric is multimodal across sections.
- Keep `hybrid` = deterministic+judge; introduce `composite` = multi-section.
</content>
</invoke>
