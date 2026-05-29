#!/usr/bin/env python3
"""Validate rubric YAML/JSON structure for rubric-eval-loop-plugin.

Usage:
  python validate_rubric.py path/to/rubric.yaml
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "YAML support requires PyYAML. Install with `pip install pyyaml` "
            "or provide a .json rubric."
        ) from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("Rubric root must be a mapping/object.")
    return data


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ["name", "version", "description", "criteria", "passing"]:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    criteria = data.get("criteria", {})
    if not isinstance(criteria, dict) or not criteria:
        errors.append("criteria must be a non-empty mapping")
        return errors

    total_weight = 0.0
    for cid, criterion in criteria.items():
        if not isinstance(criterion, dict):
            errors.append(f"Criterion {cid} must be an object")
            continue
        weight = criterion.get("weight")
        if not isinstance(weight, (int, float)):
            errors.append(f"Criterion {cid} missing numeric weight")
        else:
            total_weight += float(weight)
        if not criterion.get("description"):
            errors.append(f"Criterion {cid} missing description")
        method = criterion.get("method", data.get("rubric_type"))
        if method in {"checklist", "hybrid"}:
            checks = criterion.get("checks", [])
            if not isinstance(checks, list) or not checks:
                errors.append(f"Criterion {cid} uses checklist method but has no checks")
            for i, check in enumerate(checks):
                if not isinstance(check, dict):
                    errors.append(f"Criterion {cid} check {i} must be object")
                    continue
                if not check.get("id"):
                    errors.append(f"Criterion {cid} check {i} missing id")
                if not (check.get("statement") or check.get("pattern") or check.get("value")):
                    errors.append(f"Criterion {cid} check {i} missing statement/pattern/value")
                if not check.get("message"):
                    errors.append(f"Criterion {cid} check {i} missing actionable message")
        if method == "level_anchor":
            anchors = criterion.get("anchors", {})
            expected = {"0", "25", "50", "75", "100"}
            actual = {str(k) for k in anchors.keys()} if isinstance(anchors, dict) else set()
            missing = expected - actual
            if missing:
                errors.append(f"Criterion {cid} missing anchors: {sorted(missing)}")

    if abs(total_weight - 100.0) > 0.01:
        errors.append(f"Criteria weights must sum to 100; found {total_weight:g}")

    passing = data.get("passing", {})
    if isinstance(passing, dict):
        required = passing.get("required_criteria", []) or []
        for req in required:
            if req not in criteria:
                errors.append(f"required_criteria references unknown criterion: {req}")
        min_score = passing.get("min_score")
        if min_score is not None and not isinstance(min_score, (int, float)):
            errors.append("passing.min_score must be numeric")
    else:
        errors.append("passing must be an object")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2
    try:
        data = load_file(path)
        errors = validate(data)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("Rubric validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Rubric OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
