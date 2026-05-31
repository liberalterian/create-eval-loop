"""Tests for two-level (sections) rubric validation and the composite template."""
from pathlib import Path

import pytest

import validate_rubric

ROOT = Path(__file__).resolve().parents[1]
COMPOSITE = ROOT / "skills/create-rubric/templates/composite-rubric.yaml"


def _section_rubric(**overrides):
    base = {
        "name": "t",
        "version": "1.0.0",
        "description": "d",
        "rubric_type": "composite",
        "sections": {
            "must": {
                "type": "checklist",
                "weight": 60,
                "criteria": {
                    "x": {
                        "weight": 100,
                        "description": "d",
                        "method": "checklist",
                        "checks": [{"id": "c1", "statement": "s", "message": "m"}],
                    }
                },
            },
            "craft": {
                "type": "level_anchor",
                "weight": 40,
                "criteria": {
                    "y": {
                        "weight": 100,
                        "description": "d",
                        "method": "level_anchor",
                        "anchors": {"0": "a", "25": "b", "50": "c", "75": "d", "100": "e"},
                    }
                },
            },
        },
        "passing": {"min_score": 85, "required_sections": ["must"], "required_criteria": ["x"]},
    }
    base.update(overrides)
    return base


def test_valid_sections_rubric():
    assert validate_rubric.validate(_section_rubric()) == []


def test_section_weights_must_sum_to_100():
    r = _section_rubric()
    r["sections"]["craft"]["weight"] = 10
    errors = validate_rubric.validate(r)
    assert any("Section weights must sum to 100" in e for e in errors)


def test_within_section_criteria_weights_must_sum_to_100():
    r = _section_rubric()
    r["sections"]["must"]["criteria"]["x"]["weight"] = 50
    errors = validate_rubric.validate(r)
    assert any("Section must criteria weights must sum to 100" in e for e in errors)


def test_invalid_section_type():
    r = _section_rubric()
    r["sections"]["must"]["type"] = "bogus"
    errors = validate_rubric.validate(r)
    assert any("invalid type" in e for e in errors)


def test_unknown_required_section():
    r = _section_rubric()
    r["passing"]["required_sections"] = ["ghost"]
    errors = validate_rubric.validate(r)
    assert any("unknown section" in e for e in errors)


def test_required_sections_rejected_on_flat_rubric():
    flat = {
        "name": "t",
        "version": "1.0.0",
        "description": "d",
        "rubric_type": "checklist",
        "criteria": {
            "a": {
                "weight": 100,
                "description": "d",
                "method": "checklist",
                "checks": [{"id": "c1", "statement": "s", "message": "m"}],
            }
        },
        "passing": {"min_score": 85, "required_sections": ["nope"]},
    }
    errors = validate_rubric.validate(flat)
    assert any("only valid for rubrics that define sections" in e for e in errors)


@pytest.mark.skipif(not COMPOSITE.exists(), reason="template missing")
def test_composite_template_is_valid():
    pytest.importorskip("yaml")
    data = validate_rubric.load_file(COMPOSITE)
    assert validate_rubric.validate(data) == []
