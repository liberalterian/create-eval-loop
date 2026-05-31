"""Tests for the build-eval-loop preflight readiness check."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/build-eval-loop/scripts"))
import preflight  # noqa: E402


def test_all_required_ok_true_when_target_and_rubric_valid(tmp_path):
    target = tmp_path / "SKILL.md"
    target.write_text("# s", encoding="utf-8")
    rubric = tmp_path / "r.yaml"
    rubric.write_text("x", encoding="utf-8")
    checks = preflight.run_checks(target, rubric, validate_fn=lambda p: [])
    assert preflight.all_required_ok(checks) is True


def test_missing_target_fails():
    checks = preflight.run_checks(Path("/no/such/SKILL.md"), None, validate_fn=lambda p: [])
    assert preflight.all_required_ok(checks) is False


def test_invalid_rubric_fails(tmp_path):
    target = tmp_path / "SKILL.md"
    target.write_text("# s", encoding="utf-8")
    rubric = tmp_path / "r.yaml"
    rubric.write_text("bad", encoding="utf-8")
    checks = preflight.run_checks(target, rubric, validate_fn=lambda p: ["weights must sum to 100"])
    assert preflight.all_required_ok(checks) is False
    rubric_check = next(c for c in checks if c["name"] == "rubric valid")
    assert "weights must sum to 100" in rubric_check["detail"]


def test_missing_rubric_path_fails(tmp_path):
    target = tmp_path / "SKILL.md"
    target.write_text("# s", encoding="utf-8")
    checks = preflight.run_checks(target, tmp_path / "absent.yaml", validate_fn=lambda p: [])
    assert preflight.all_required_ok(checks) is False


def test_no_rubric_only_checks_target(tmp_path):
    target = tmp_path / "SKILL.md"
    target.write_text("# s", encoding="utf-8")
    checks = preflight.run_checks(target, None, validate_fn=lambda p: [])
    assert len(checks) == 1
    assert preflight.all_required_ok(checks) is True
