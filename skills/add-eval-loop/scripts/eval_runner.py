#!/usr/bin/env python3
"""Run deterministic prompt/output eval cases.

This runner does not call an LLM. It evaluates recorded outputs or outputs produced
by a command. Use it for manual testing and regression checks.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def check_assertion(output: str, assertion: dict[str, Any]) -> tuple[bool, str]:
    atype = assertion.get("type")
    value = assertion.get("value", "")
    text = output.strip()

    if atype == "exact":
        passed = text.lower() == str(value).lower()
        return passed, f"expected exact {value!r}, got {text!r}"
    if atype == "contains":
        passed = str(value).lower() in output.lower()
        return passed, f"expected output to contain {value!r}"
    if atype == "not_contains":
        passed = str(value).lower() not in output.lower()
        return passed, f"expected output not to contain {value!r}"
    if atype == "regex":
        passed = bool(re.search(str(value), output, flags=re.MULTILINE))
        return passed, f"expected regex match {value!r}"
    if atype == "min_length":
        passed = len(text) >= int(value)
        return passed, f"expected length >= {value}, got {len(text)}"
    if atype == "max_length":
        passed = len(text) <= int(value)
        return passed, f"expected length <= {value}, got {len(text)}"
    if atype == "json_key":
        try:
            data = json.loads(output)
        except json.JSONDecodeError as exc:
            return False, f"output is not valid JSON: {exc}"
        current: Any = data
        for part in str(value).split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False, f"missing JSON key path {value!r}"
        return True, f"JSON key path {value!r} exists"
    return False, f"unknown assertion type: {atype}"


def run_command(command: str, case_input: str) -> str:
    proc = subprocess.run(
        command,
        input=case_input,
        text=True,
        shell=True,
        capture_output=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return proc.stdout + proc.stderr
    return proc.stdout


def evaluate_cases(cases: list[dict[str, Any]], command: str | None = None) -> dict[str, Any]:
    results = []
    for case in cases:
        output = run_command(command, case.get("input", "")) if command else case.get("output", "")
        failures = []
        assertion_results = []
        for assertion in case.get("assertions", []):
            passed, message = check_assertion(output, assertion)
            assertion_results.append({"assertion": assertion, "passed": passed, "message": message})
            if not passed:
                failures.append(message)
        results.append({
            "id": case.get("id"),
            "description": case.get("description", ""),
            "passed": not failures,
            "failures": failures,
            "output": output,
            "assertions": assertion_results,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", help="Path to eval-cases.json")
    parser.add_argument("--command", help="Optional command that receives case input on stdin and prints output")
    parser.add_argument("--out", default="eval/results/latest.json", help="Output JSON path")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    result = evaluate_cases(cases, args.command)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
