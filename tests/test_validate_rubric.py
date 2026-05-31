"""Tests for validate_rubric (flat rubric validation)."""
import validate_rubric


VALID = {
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
    "passing": {"min_score": 85, "required_criteria": ["a"]},
}


def test_valid_rubric_has_no_errors():
    assert validate_rubric.validate(VALID) == []


def test_weights_must_sum_to_100():
    bad = {**VALID, "criteria": {"a": {**VALID["criteria"]["a"], "weight": 50}}}
    errors = validate_rubric.validate(bad)
    assert any("sum to 100" in e for e in errors)


def test_checklist_requires_checks():
    bad = {
        **VALID,
        "criteria": {"a": {"weight": 100, "description": "d", "method": "checklist", "checks": []}},
    }
    errors = validate_rubric.validate(bad)
    assert any("no checks" in e for e in errors)


def test_unknown_required_criterion():
    bad = {**VALID, "passing": {"min_score": 85, "required_criteria": ["ghost"]}}
    errors = validate_rubric.validate(bad)
    assert any("unknown criterion" in e for e in errors)


def test_level_anchor_requires_all_anchors():
    bad = {
        **VALID,
        "rubric_type": "level_anchor",
        "criteria": {
            "a": {"weight": 100, "description": "d", "method": "level_anchor", "anchors": {0: "x", 100: "y"}}
        },
    }
    errors = validate_rubric.validate(bad)
    assert any("missing anchors" in e for e in errors)
