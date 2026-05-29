#!/usr/bin/env python3
"""Manual deterministic eval runner for prompt/output cases."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def check(output: str, assertion: dict[str, Any]) -> tuple[bool, str]:
    typ = assertion.get("type")
    value = assertion.get("value", "")
    stripped = output.strip()
    if typ == "exact":
        ok = stripped.lower() == str(value).lower()
        return ok, f"exact expected={value!r} got={stripped!r}"
    if typ == "contains":
        ok = str(value).lower() in output.lower()
        return ok, f"contains expected={value!r}"
    if typ == "not_contains":
        ok = str(value).lower() not in output.lower()
        return ok, f"not_contains forbidden={value!r}"
    if typ == "regex":
        ok = bool(re.search(str(value), output, flags=re.MULTILINE))
        return ok, f"regex expected={value!r}"
    if typ == "min_length":
        ok = len(stripped) >= int(value)
        return ok, f"min_length expected>={value} got={len(stripped)}"
    if typ == "max_length":
        ok = len(stripped) <= int(value)
        return ok, f"max_length expected<={value} got={len(stripped)}"
    if typ == "json_key":
        try:
            current: Any = json.loads(output)
        except json.JSONDecodeError as exc:
            return False, f"invalid JSON: {exc}"
        for part in str(value).split("."):
            if not isinstance(current, dict) or part not in current:
                return False, f"missing JSON key path {value!r}"
            current = current[part]
        return True, f"json_key exists={value!r}"
    return False, f"unknown assertion type {typ!r}"


def run_command(command: str, prompt: str) -> str:
    proc = subprocess.run(
        command,
        input=prompt,
        text=True,
        capture_output=True,
        shell=True,
        timeout=120,
    )
    return proc.stdout if proc.returncode == 0 else proc.stdout + proc.stderr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("--command")
    parser.add_argument("--out", default="eval-test-results.json")
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    results = []
    for case in cases:
        output = run_command(args.command, case.get("input", "")) if args.command else case.get("output", "")
        assertion_results = []
        failures = []
        for assertion in case.get("assertions", []):
            passed, message = check(output, assertion)
            assertion_results.append({"passed": passed, "message": message, "assertion": assertion})
            if not passed:
                failures.append(message)
        results.append({
            "id": case.get("id"),
            "description": case.get("description", ""),
            "passed": not failures,
            "failures": failures,
            "assertions": assertion_results,
            "output": output,
        })

    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0,
        "results": results,
    }
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
