#!/usr/bin/env python3
"""Manual deterministic eval runner for prompt/output cases.

Thin CLI over the shared ``eval_core`` engine.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import eval_core
except ImportError:  # pragma: no cover - path shim
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
    import eval_core


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("--command")
    parser.add_argument("--out", default="eval-test-results.json")
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    report = eval_core.evaluate_cases(cases, args.command)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
