# Rubric Storage Levels

Rubrics should be stored as close as possible to the scope that owns them.

## User-level rubrics

Use for reusable personal standards that apply across projects.

```text
~/.claude/evals/<rubric-name>.yaml
```

Examples: personal writing voice, generic code review, reusable research-quality rubric.

## Project-level rubrics

Use for standards shared by the whole repository.

```text
<project>/.claude/evals/<rubric-name>.yaml
```

Examples: product copy style, security requirements, PR quality gate, documentation quality.

## Sub-directory-level rubrics

Use when one part of a project has special constraints.

```text
<project>/<subdir>/.claude/evals/<rubric-name>.yaml
```

Examples: `apps/mobile/.claude/evals/mobile-accessibility.yaml`, `packages/payments/.claude/evals/payment-security.yaml`.

## Discovery order

When a skill needs a rubric by name, resolve in this order:

1. Explicit path provided by the user.
2. Nearest current directory upward: `./.claude/evals/<name>.yaml`.
3. Project root: `<project>/.claude/evals/<name>.yaml`.
4. User-level: `~/.claude/evals/<name>.yaml`.

If duplicate rubrics exist, prefer the nearest scoped rubric and state which one was used.
