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


SECTION_TYPES = {"checklist", "level_anchor", "binary_assertion", "hybrid", "pairwise", "test_driven"}


def _validate_criteria(criteria: Any, default_method: str | None, label: str, errors: list[str]) -> float:
    """Validate a criteria mapping and return its total weight.

    ``label`` prefixes messages so section context is clear (e.g.
    "Section craft criterion x"). ``default_method`` is the method assumed when
    a criterion does not declare its own.
    """
    if not isinstance(criteria, dict) or not criteria:
        errors.append(f"{label} criteria must be a non-empty mapping")
        return 0.0

    total_weight = 0.0
    for cid, criterion in criteria.items():
        where = f"{label} criterion {cid}".strip()
        if not isinstance(criterion, dict):
            errors.append(f"{where} must be an object")
            continue
        weight = criterion.get("weight")
        if not isinstance(weight, (int, float)):
            errors.append(f"{where} missing numeric weight")
        else:
            total_weight += float(weight)
        if not criterion.get("description"):
            errors.append(f"{where} missing description")
        method = criterion.get("method", default_method)
        if method in {"checklist", "hybrid"}:
            checks = criterion.get("checks", [])
            if not isinstance(checks, list) or not checks:
                errors.append(f"{where} uses checklist method but has no checks")
            for i, check in enumerate(checks):
                if not isinstance(check, dict):
                    errors.append(f"{where} check {i} must be object")
                    continue
                if not check.get("id"):
                    errors.append(f"{where} check {i} missing id")
                if not (check.get("statement") or check.get("pattern") or check.get("value")):
                    errors.append(f"{where} check {i} missing statement/pattern/value")
                if not check.get("message"):
                    errors.append(f"{where} check {i} missing actionable message")
        if method == "level_anchor":
            anchors = criterion.get("anchors", {})
            expected = {"0", "25", "50", "75", "100"}
            actual = {str(k) for k in anchors.keys()} if isinstance(anchors, dict) else set()
            missing = expected - actual
            if missing:
                errors.append(f"{where} missing anchors: {sorted(missing)}")
    return total_weight


def _validate_context(context: Any) -> list[str]:
    """Validate the optional ``context`` grounding block (expert references and
    notes). Absent context is valid; a present block must be well-formed."""
    errors: list[str] = []
    if context is None:
        return errors
    if not isinstance(context, dict):
        errors.append("context must be an object")
        return errors
    references = context.get("references")
    if references is not None:
        if not isinstance(references, list):
            errors.append("context.references must be a list")
        else:
            for i, ref in enumerate(references):
                if not isinstance(ref, dict):
                    errors.append(f"context.references[{i}] must be an object")
                    continue
                if not ref.get("path") or not isinstance(ref.get("path"), str):
                    errors.append(f"context.references[{i}] missing non-empty string path")
    notes = context.get("expert_notes")
    if notes is not None and not isinstance(notes, str):
        errors.append("context.expert_notes must be a string")
    return errors


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    has_sections = isinstance(data.get("sections"), dict) and data.get("sections")
    base_fields = ["name", "version", "description", "passing"]
    base_fields.append("sections" if has_sections else "criteria")
    for field in base_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Collect the set of all criterion ids for required_criteria checks.
    all_criteria: set[str] = set()

    if has_sections:
        sections = data["sections"]
        section_weight_total = 0.0
        for sid, section in sections.items():
            if not isinstance(section, dict):
                errors.append(f"Section {sid} must be an object")
                continue
            sweight = section.get("weight")
            if not isinstance(sweight, (int, float)):
                errors.append(f"Section {sid} missing numeric weight")
            else:
                section_weight_total += float(sweight)
            stype = section.get("type", data.get("rubric_type"))
            if stype not in SECTION_TYPES:
                errors.append(f"Section {sid} has invalid type: {stype!r}")
            criteria = section.get("criteria", {})
            all_criteria.update(criteria.keys() if isinstance(criteria, dict) else [])
            crit_total = _validate_criteria(criteria, stype, f"Section {sid}", errors)
            if criteria and abs(crit_total - 100.0) > 0.01:
                errors.append(f"Section {sid} criteria weights must sum to 100; found {crit_total:g}")
        if abs(section_weight_total - 100.0) > 0.01:
            errors.append(f"Section weights must sum to 100; found {section_weight_total:g}")
    else:
        criteria = data.get("criteria", {})
        all_criteria.update(criteria.keys() if isinstance(criteria, dict) else [])
        total_weight = _validate_criteria(criteria, data.get("rubric_type"), "", errors)
        if isinstance(criteria, dict) and criteria and abs(total_weight - 100.0) > 0.01:
            errors.append(f"Criteria weights must sum to 100; found {total_weight:g}")

    passing = data.get("passing", {})
    if isinstance(passing, dict):
        for req in passing.get("required_criteria", []) or []:
            if req not in all_criteria:
                errors.append(f"required_criteria references unknown criterion: {req}")
        if has_sections:
            for req in passing.get("required_sections", []) or []:
                if req not in data["sections"]:
                    errors.append(f"required_sections references unknown section: {req}")
        elif passing.get("required_sections"):
            errors.append("required_sections is only valid for rubrics that define sections")
        min_score = passing.get("min_score")
        if min_score is not None and not isinstance(min_score, (int, float)):
            errors.append("passing.min_score must be numeric")
    else:
        errors.append("passing must be an object")

    errors.extend(_validate_context(data.get("context")))

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
