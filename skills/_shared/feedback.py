#!/usr/bin/env python3
"""Append-only audit trail for human sign-off and expert feedback.

Each sign-off checkpoint or captured expert note is written as a timestamped
entry under ``.claude/eval-results/<rubric>/feedback.md`` so the human-in-the-loop
decisions are reviewable later. Stdlib only, so it can be vendored.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE = ".claude/eval-results"


def feedback_path(rubric_name: str, base: str = DEFAULT_BASE) -> Path:
    return Path(base) / rubric_name / "feedback.md"


def append_feedback(
    rubric_name: str,
    stage: str,
    text: str,
    decision: str | None = None,
    base: str = DEFAULT_BASE,
) -> Path:
    """Append a sign-off / feedback entry and return the file path."""
    path = feedback_path(rubric_name, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# Feedback log: {rubric_name}\n", encoding="utf-8")
    stamp = datetime.now(timezone.utc).isoformat()
    entry = [f"\n## {stamp} — {stage}"]
    if decision:
        entry.append(f"- Decision: {decision}")
    if text:
        entry.append("")
        entry.append(text.rstrip())
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(entry) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rubric", required=True, help="Rubric name (log directory)")
    parser.add_argument("--stage", required=True, help="Checkpoint name, e.g. draft-criteria")
    parser.add_argument("--decision", help="approve | edit | reject")
    parser.add_argument("--text", default="", help="Free-form note / expert feedback")
    parser.add_argument("--base", default=DEFAULT_BASE)
    args = parser.parse_args()
    path = append_feedback(args.rubric, args.stage, args.text, args.decision, args.base)
    print(f"Recorded feedback at {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
