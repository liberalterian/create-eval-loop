"""Pytest path setup so tests can import the plugin's modules directly."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for rel in (
    "skills/_shared",
    "skills/create-rubric/scripts",
    "skills/add-eval-loop/scripts",
):
    sys.path.insert(0, str(ROOT / rel))
