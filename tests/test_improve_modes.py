"""Tests for WS3 dual-mode improvement loop: mode-aware prompt, model fail-soft,
and the model apply step."""
import improve_skill_loop as loop


RESULTS = {
    "pass_rate": 0.5,
    "results": [
        {"id": "c1", "passed": False, "failures": ["min_length"]},
        {"id": "c2", "passed": True, "failures": []},
    ],
}


def test_prompt_skill_mode(tmp_path):
    target = tmp_path / "SKILL.md"
    target.write_text("# Skill\nbody", encoding="utf-8")
    prompt = tmp_path / "p.md"
    loop.write_improvement_prompt(target, RESULTS, prompt, 0.95, "skill")
    text = prompt.read_text(encoding="utf-8")
    assert "skill mode" in text
    assert "SKILL.md content only" in text
    # Only failing cases are embedded.
    assert "c1" in text and '"id": "c2"' not in text


def test_prompt_output_mode(tmp_path):
    target = tmp_path / "report.md"
    target.write_text("draft", encoding="utf-8")
    prompt = tmp_path / "p.md"
    loop.write_improvement_prompt(target, RESULTS, prompt, 0.9, "output")
    text = prompt.read_text(encoding="utf-8")
    assert "output mode" in text
    assert "output artifact" in text
    assert "report.md" in text


def test_model_available():
    assert loop.model_available("python --version") is True
    assert loop.model_available("definitely-not-a-real-binary-xyz123") is False
    assert loop.model_available("") is False


def test_apply_with_model_writes_stdout_to_target(tmp_path):
    # `cat` echoes the prompt (stdin) to stdout, which is written to the target.
    target = tmp_path / "out.md"
    target.write_text("old", encoding="utf-8")
    prompt = tmp_path / "p.md"
    prompt.write_text("NEW CONTENT", encoding="utf-8")
    ok = loop.apply_with_model("cat", prompt, target)
    assert ok is True
    assert "NEW CONTENT" in target.read_text(encoding="utf-8")


def test_apply_with_model_fails_on_empty_output(tmp_path):
    target = tmp_path / "out.md"
    target.write_text("old", encoding="utf-8")
    prompt = tmp_path / "p.md"
    prompt.write_text("ignored", encoding="utf-8")
    # `true` produces no stdout -> treated as a failed apply, target untouched.
    ok = loop.apply_with_model("true", prompt, target)
    assert ok is False
    assert target.read_text(encoding="utf-8") == "old"
