#!/usr/bin/env python3
"""Run deterministic prompt/output eval cases.

Thin CLI over the shared ``eval_core`` engine. Evaluates recorded outputs or
outputs produced by a command. Does not call an LLM.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Import the shared core: prefer a vendored sibling copy (when this script has
# been installed into a target skill), else fall back to the plugin's _shared.
try:
    import eval_core
except ImportError:  # pragma: no cover - path shim
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
    import eval_core


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", help="Path to eval-cases.json")
    parser.add_argument("--command", help="Optional command that receives case input on stdin and prints output")
    parser.add_argument("--out", default="eval/results/latest.json", help="Output JSON path")
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    result = eval_core.evaluate_cases(cases, args.command)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] == result["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
