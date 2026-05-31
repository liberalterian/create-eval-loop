"""Tests for the shared eval_core engine: assertions and scoring."""
import eval_core


# --------------------------- assertions --------------------------- #

def test_contains_and_not_contains():
    ok, _ = eval_core.check_assertion("hello world", {"type": "contains", "value": "world"})
    assert ok
    ok, _ = eval_core.check_assertion("hello world", {"type": "not_contains", "value": "TODO"})
    assert ok
    ok, _ = eval_core.check_assertion("has TODO", {"type": "not_contains", "value": "TODO"})
    assert not ok


def test_presence_absence_aliases():
    ok, _ = eval_core.check_assertion("abc", {"type": "presence", "value": "b"})
    assert ok
    ok, _ = eval_core.check_assertion("abc", {"type": "absence", "value": "z"})
    assert ok


def test_regex_and_pattern():
    ok, _ = eval_core.check_assertion("## Install", {"type": "regex", "value": r"^##\s+Install"})
    assert ok
    ok, _ = eval_core.check_assertion("ABC123", {"type": "pattern", "value": r"[A-Z]+\d+"})
    assert ok
    ok, _ = eval_core.check_assertion("ABC123 extra", {"type": "pattern", "value": r"[A-Z]+\d+"})
    assert not ok  # fullmatch


def test_length_and_json():
    ok, _ = eval_core.check_assertion("abcd", {"type": "min_length", "value": 3})
    assert ok
    ok, _ = eval_core.check_assertion("abcd", {"type": "max_length", "value": 3})
    assert not ok
    ok, _ = eval_core.check_assertion('{"a": {"b": 1}}', {"type": "json_key", "value": "a.b"})
    assert ok
    ok, _ = eval_core.check_assertion('{"a": 1}', {"type": "json_schema", "value": "a.missing"})
    assert not ok


def test_unknown_assertion_type():
    ok, msg = eval_core.check_assertion("x", {"type": "bogus"})
    assert not ok and "unknown" in msg


# --------------------------- command failures --------------------------- #

def test_evaluate_cases_marks_command_failure(tmp_path):
    cases = [{"id": "c", "assertions": [{"type": "contains", "value": "ok"}]}]
    report = eval_core.evaluate_cases(cases, command="echo 'ok'; exit 1")
    # Even though stderr/stdout contains 'ok', a non-zero exit must fail the case.
    assert report["results"][0]["passed"] is False
    assert any("command_failed" in f for f in report["results"][0]["failures"])


# --------------------------- scoring: flat --------------------------- #

FLAT = {
    "rubric_type": "checklist",
    "scoring": {"threshold": 85, "per_criterion_floor": 70},
    "criteria": {
        "a": {"weight": 50, "threshold": 70},
        "b": {"weight": 50, "threshold": 70},
    },
    "passing": {"min_score": 85, "required_criteria": ["a"]},
}


def test_flat_pass():
    res = eval_core.score_rubric(FLAT, {"criteria": {"a": {"score": 90}, "b": {"score": 80}}})
    assert res["overall"] == 85
    assert res["passed"] is True


def test_flat_floor_violation():
    res = eval_core.score_rubric(FLAT, {"criteria": {"a": {"score": 90}, "b": {"score": 60}}})
    assert "b" in res["floor_violations"]
    assert res["passed"] is False


def test_checks_to_score():
    res = eval_core.score_rubric(
        FLAT,
        {"criteria": {"a": {"checks": {"c1": True, "c2": False}}, "b": {"score": 100}}},
    )
    assert res["criteria"]["a"]["score"] == 50


# --------------------------- scoring: sections --------------------------- #

SECTIONS = {
    "rubric_type": "composite",
    "scoring": {"threshold": 80},
    "sections": {
        "must": {"type": "checklist", "weight": 60, "criteria": {"x": {"weight": 100, "threshold": 70}}},
        "craft": {"type": "level_anchor", "weight": 40, "criteria": {"y": {"weight": 100, "threshold": 50}}},
    },
    "passing": {"min_score": 80, "required_sections": ["must"]},
}


def test_sections_weighted_overall():
    res = eval_core.score_rubric(SECTIONS, {"criteria": {"x": {"score": 100}, "y": {"score": 50}}})
    assert res["overall"] == 80  # 0.6*100 + 0.4*50
    assert res["passed"] is True


def test_required_section_failure():
    res = eval_core.score_rubric(SECTIONS, {"criteria": {"x": {"score": 50}, "y": {"score": 100}}})
    assert "must" in res["required_sections_failed"]
    assert res["passed"] is False


def test_critical_barrier_fails_regardless():
    res = eval_core.score_rubric(
        SECTIONS,
        {"criteria": {"x": {"score": 100}, "y": {"score": 100}}, "critical_barriers_triggered": ["sec"]},
    )
    assert res["overall"] == 100
    assert res["passed"] is False
