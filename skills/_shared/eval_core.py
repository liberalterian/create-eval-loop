#!/usr/bin/env python3
"""Shared evaluation core for the rubric-eval-loop plugin.

This single module is the one source of truth for:

1. Deterministic assertion checking (``check_assertion``).
2. Command execution that records non-zero exits explicitly (``run_command``).
3. A deterministic rubric scoring engine (``score_rubric``) that aggregates
   per-criterion results, applies floors, required criteria/sections, and
   critical barriers. It supports both flat (``criteria``) and multimodal
   (``sections``) rubrics.

It is intentionally dependency-free (stdlib only) so it can be vendored into a
target skill's ``scripts/`` directory and run anywhere Python 3.9+ is present.
"""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any

VERSION = "0.1.0"

# --------------------------------------------------------------------------- #
# Assertions
# --------------------------------------------------------------------------- #

# Canonical assertion vocabulary. This list is the single source of truth and
# must stay in sync with docs/RUBRIC_SCHEMA.md.
ASSERTION_TYPES = (
    "exact",
    "contains",
    "not_contains",
    "regex",
    "presence",      # alias of regex/contains: required pattern must exist
    "absence",       # required pattern must NOT exist
    "pattern",       # full-output structural regex match
    "min_length",
    "max_length",
    "json_key",      # dotted key path must exist
    "json_schema",   # alias of json_key for back-compat with the schema doc
)


def check_assertion(output: str, assertion: dict[str, Any]) -> tuple[bool, str]:
    """Evaluate a single assertion against ``output``.

    Returns ``(passed, message)``.
    """
    atype = assertion.get("type")
    value = assertion.get("value", "")
    text = output.strip()

    if atype == "exact":
        return text.lower() == str(value).lower(), f"exact expected={value!r} got={text!r}"
    if atype in ("contains", "presence"):
        return str(value).lower() in output.lower(), f"{atype} expected={value!r}"
    if atype in ("not_contains", "absence"):
        return str(value).lower() not in output.lower(), f"{atype} forbidden={value!r}"
    if atype == "regex":
        return bool(re.search(str(value), output, flags=re.MULTILINE)), f"regex expected={value!r}"
    if atype == "pattern":
        return bool(re.fullmatch(str(value), text, flags=re.DOTALL)), f"pattern expected={value!r}"
    if atype == "min_length":
        return len(text) >= int(value), f"min_length expected>={value} got={len(text)}"
    if atype == "max_length":
        return len(text) <= int(value), f"max_length expected<={value} got={len(text)}"
    if atype in ("json_key", "json_schema"):
        try:
            current: Any = json.loads(output)
        except json.JSONDecodeError as exc:
            return False, f"invalid JSON: {exc}"
        for part in str(value).split("."):
            if not isinstance(current, dict) or part not in current:
                return False, f"missing JSON key path {value!r}"
            current = current[part]
        return True, f"json_key exists={value!r}"
    return False, f"unknown assertion type {atype!r}"


# --------------------------------------------------------------------------- #
# Command execution
# --------------------------------------------------------------------------- #


def run_command(command: str, case_input: str, timeout: int = 120) -> tuple[str, bool, str]:
    """Run ``command`` feeding ``case_input`` on stdin.

    Returns ``(output, ok, note)``. ``ok`` is False when the command times out
    or exits non-zero, so callers never silently treat an error trace as a
    valid candidate output.
    """
    try:
        proc = subprocess.run(
            command,
            input=case_input,
            text=True,
            shell=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "", False, f"command timed out after {timeout}s"
    if proc.returncode != 0:
        combined = (proc.stdout or "") + (proc.stderr or "")
        return combined, False, f"command exited {proc.returncode}"
    return proc.stdout, True, ""


def evaluate_cases(cases: list[dict[str, Any]], command: str | None = None) -> dict[str, Any]:
    """Run deterministic assertion cases and return a report dict."""
    from datetime import datetime, timezone

    results = []
    for case in cases:
        if command:
            output, ok, note = run_command(command, case.get("input", ""))
        else:
            output, ok, note = case.get("output", ""), True, ""
        assertion_results = []
        failures = []
        if not ok:
            # A failed generator command fails the case outright; we do not run
            # assertions against an error trace.
            failures.append(f"command_failed: {note}")
        else:
            for assertion in case.get("assertions", []):
                passed, message = check_assertion(output, assertion)
                assertion_results.append({"assertion": assertion, "passed": passed, "message": message})
                if not passed:
                    failures.append(message)
        results.append({
            "id": case.get("id"),
            "description": case.get("description", ""),
            "passed": not failures,
            "command_ok": ok,
            "failures": failures,
            "assertions": assertion_results,
            "output": output,
        })
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0,
        "results": results,
    }


# --------------------------------------------------------------------------- #
# Rubric scoring engine
# --------------------------------------------------------------------------- #


def normalize_sections(rubric: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a sections mapping for either flat or multimodal rubrics.

    A flat rubric (top-level ``criteria``) becomes one implicit section named
    ``default`` weighted 100, typed by ``rubric_type`` (default ``checklist``).
    """
    if isinstance(rubric.get("sections"), dict) and rubric["sections"]:
        return rubric["sections"]
    return {
        "default": {
            "type": rubric.get("rubric_type", "checklist"),
            "weight": 100,
            "criteria": rubric.get("criteria", {}),
        }
    }


def _criterion_score(crit_id: str, criterion: dict[str, Any], evaluation: dict[str, Any]) -> float:
    """Resolve a 0-100 score for one criterion from the evaluation input.

    Accepts either an explicit ``score`` or a ``checks`` map of booleans
    (score = checked / total * 100).
    """
    crit_eval = evaluation.get("criteria", {}).get(crit_id, {})
    if "score" in crit_eval and crit_eval["score"] is not None:
        return float(crit_eval["score"])
    checks = crit_eval.get("checks")
    if isinstance(checks, dict) and checks:
        passed = sum(1 for v in checks.values() if v)
        return round(passed / len(checks) * 100, 4)
    return 0.0


def _weighted_average(items: list[tuple[float, float]]) -> float:
    """items = list of (weight, value). Falls back to a plain mean if weights
    are absent or sum to zero."""
    total_w = sum(w for w, _ in items)
    if total_w <= 0:
        return round(sum(v for _, v in items) / len(items), 4) if items else 0.0
    return round(sum(w * v for w, v in items) / total_w, 4)


def score_rubric(rubric: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    """Deterministically aggregate per-criterion results into a pass/fail.

    ``evaluation`` shape::

        {
          "criteria": {crit_id: {"score": 0-100} | {"checks": {id: bool}}},
          "critical_barriers_triggered": [barrier_id, ...]
        }

    Returns a result dict with overall score, per-section/criterion breakdown,
    floor/required violations, triggered barriers, and ``passed``.
    """
    scoring = rubric.get("scoring", {}) or {}
    passing = rubric.get("passing", {}) or {}
    global_floor = scoring.get("per_criterion_floor")
    min_score = passing.get("min_score", scoring.get("threshold", 0))
    required_criteria = set(passing.get("required_criteria", []) or [])
    required_sections = set(passing.get("required_sections", []) or [])

    sections = normalize_sections(rubric)
    section_results: dict[str, Any] = {}
    criterion_results: dict[str, Any] = {}
    floor_violations: list[str] = []

    section_items: list[tuple[float, float]] = []
    for sid, section in sections.items():
        criteria = section.get("criteria", {}) or {}
        crit_items: list[tuple[float, float]] = []
        for cid, criterion in criteria.items():
            score = _criterion_score(cid, criterion, evaluation)
            weight = float(criterion.get("weight", 0) or 0)
            floor = criterion.get("threshold", global_floor)
            passed = floor is None or score >= float(floor)
            criterion_results[cid] = {
                "section": sid,
                "score": score,
                "weight": weight,
                "floor": floor,
                "passed": passed,
            }
            if not passed:
                floor_violations.append(cid)
            crit_items.append((weight, score))
        section_score = _weighted_average(crit_items)
        section_weight = float(section.get("weight", 0) or 0)
        section_passed = all(
            criterion_results[cid]["passed"] for cid in criteria
        ) if criteria else True
        section_results[sid] = {
            "score": section_score,
            "weight": section_weight,
            "passed": section_passed,
        }
        section_items.append((section_weight, section_score))

    overall = _weighted_average(section_items)

    triggered = list(evaluation.get("critical_barriers_triggered", []) or [])
    required_criteria_failed = [c for c in required_criteria if not criterion_results.get(c, {}).get("passed", False)]
    required_sections_failed = [s for s in required_sections if not section_results.get(s, {}).get("passed", False)]

    passed = (
        overall >= float(min_score)
        and not floor_violations
        and not required_criteria_failed
        and not required_sections_failed
        and not triggered
    )

    return {
        "overall": overall,
        "passed": passed,
        "min_score": min_score,
        "sections": section_results,
        "criteria": criterion_results,
        "floor_violations": floor_violations,
        "required_criteria_failed": required_criteria_failed,
        "required_sections_failed": required_sections_failed,
        "critical_barriers_triggered": triggered,
    }
