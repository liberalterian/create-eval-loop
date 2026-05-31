#!/usr/bin/env python3
"""Preflight readiness check for the build-eval-loop orchestrator.

Confirms the target skill exists and, if a rubric is supplied, that it validates
before any side-effecting steps run. Prints a checklist and exits non-zero when
a required check fails.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

_PLUGIN_SKILLS = Path(__file__).resolve().parents[2]


def run_checks(target: Path, rubric: Path | None, validate_fn: Callable[[Path], list[str]]) -> list[dict]:
    """Return a list of checklist entries. ``validate_fn`` maps a rubric path to
    a list of validation errors (empty = valid); injected for testability."""
    checks: list[dict] = [
        {"name": "target skill exists", "ok": target.exists(), "detail": str(target), "required": True},
    ]
    if rubric is not None:
        if not rubric.exists():
            checks.append({"name": "rubric exists", "ok": False, "detail": str(rubric), "required": True})
        else:
            errors = validate_fn(rubric)
            checks.append({
                "name": "rubric valid",
                "ok": not errors,
                "detail": "; ".join(errors) if errors else "ok",
                "required": True,
            })
    return checks


def all_required_ok(checks: list[dict]) -> bool:
    return all(c["ok"] for c in checks if c.get("required"))


def _default_validate(rubric: Path) -> list[str]:
    sys.path.insert(0, str(_PLUGIN_SKILLS / "create-rubric" / "scripts"))
    import validate_rubric  # noqa: E402
    return validate_rubric.validate(validate_rubric.load_file(rubric))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--rubric")
    args = parser.parse_args()

    rubric = Path(args.rubric) if args.rubric else None
    checks = run_checks(Path(args.target), rubric, _default_validate)
    for c in checks:
        mark = "ok" if c["ok"] else "FAIL"
        print(f"[{mark}] {c['name']}: {c['detail']}")
    if all_required_ok(checks):
        print("Preflight OK.")
        return 0
    print("Preflight failed. Resolve the items above before continuing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
