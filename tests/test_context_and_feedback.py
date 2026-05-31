"""Tests for the WS2 context grounding block and feedback audit trail."""
import sys
from pathlib import Path

import validate_rubric

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/_shared"))
import feedback  # noqa: E402


# --------------------------- context validation --------------------------- #

def test_context_absent_is_valid():
    assert validate_rubric._validate_context(None) == []


def test_valid_context():
    ctx = {
        "references": [{"path": "./a.md", "note": "x"}, {"path": "./b/*.md"}],
        "expert_notes": "prefer active voice",
    }
    assert validate_rubric._validate_context(ctx) == []


def test_context_must_be_object():
    assert any("must be an object" in e for e in validate_rubric._validate_context("nope"))


def test_reference_requires_path():
    errors = validate_rubric._validate_context({"references": [{"note": "no path"}]})
    assert any("missing non-empty string path" in e for e in errors)


def test_references_must_be_list():
    errors = validate_rubric._validate_context({"references": {"path": "x"}})
    assert any("must be a list" in e for e in errors)


def test_expert_notes_must_be_string():
    errors = validate_rubric._validate_context({"expert_notes": ["a", "b"]})
    assert any("expert_notes must be a string" in e for e in errors)


# --------------------------- feedback audit trail --------------------------- #

def test_append_feedback_creates_and_appends(tmp_path):
    base = str(tmp_path)
    p1 = feedback.append_feedback("myrubric", "draft-criteria", "looks good", "approve", base)
    p2 = feedback.append_feedback("myrubric", "pre-patch", "tighten tone", "edit", base)
    assert p1 == p2
    text = p1.read_text(encoding="utf-8")
    assert text.startswith("# Feedback log: myrubric")
    assert "draft-criteria" in text and "pre-patch" in text
    assert "Decision: approve" in text and "Decision: edit" in text
    assert "looks good" in text and "tighten tone" in text


def test_feedback_path_layout(tmp_path):
    p = feedback.feedback_path("r", str(tmp_path))
    assert p.name == "feedback.md" and p.parent.name == "r"
