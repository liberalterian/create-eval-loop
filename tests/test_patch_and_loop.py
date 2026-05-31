"""Tests for patch idempotency and the improvement-loop circuit breaker."""
import argparse

import patch_skill_eval_loop as patch
import improve_skill_loop as loop


def _section():
    args = argparse.Namespace(rubric="r.yaml", mode="hybrid", threshold=85, floor=70, max_rounds=4)
    return patch.render(args)


def test_patch_is_idempotent():
    section = _section()
    out1 = patch.patch_text("# Skill\n\nbody text", section)
    out2 = patch.patch_text(out1, section)
    assert out1.count(patch.START) == 1
    assert out1.count(patch.END) == 1
    assert out2.count(patch.START) == 1
    assert out2.count(patch.END) == 1


def test_patch_appends_when_no_markers():
    out = patch.patch_text("# Skill\n\nbody", _section())
    assert patch.START in out and patch.END in out
    assert out.startswith("# Skill")


def test_should_stop_on_stall():
    assert loop.should_stop([0.5, 0.5, 0.5], min_delta=0.01, patience=2) is True


def test_should_stop_needs_enough_samples():
    assert loop.should_stop([0.5, 0.7], min_delta=0.01, patience=2) is False


def test_should_stop_false_when_improving():
    assert loop.should_stop([0.5, 0.6, 0.8], min_delta=0.01, patience=2) is False
