# tests/self_engineer/test_analyzer.py
import pytest


def test_categorize_intent_create_skill():
    from viko.self_engineer.analyzer import _categorize_intent
    assert _categorize_intent("tambah skill crypto price") == "create_skill"
    assert _categorize_intent("buat skill baru untuk cuaca") == "create_skill"


def test_categorize_intent_fix_bug():
    from viko.self_engineer.analyzer import _categorize_intent
    assert _categorize_intent("perbaiki bug di browser tool") == "fix_bug"
    assert _categorize_intent("ada error di weather skill") == "fix_bug"


def test_categorize_intent_modify_prompt():
    from viko.self_engineer.analyzer import _categorize_intent
    assert _categorize_intent("ubah perilaku menjadi lebih singkat") == "modify_prompt"
    assert _categorize_intent("jadilah lebih formal dalam menjawab") == "modify_prompt"


def test_categorize_intent_modify_ui():
    from viko.self_engineer.analyzer import _categorize_intent
    assert _categorize_intent("ubah warna UI jadi lebih gelap") == "modify_ui"


def test_build_context_returns_dict(tmp_path, monkeypatch):
    from viko.self_engineer import analyzer
    # Create minimal fake VIKO structure
    (tmp_path / "viko" / "skills").mkdir(parents=True)
    (tmp_path / "viko" / "prompt.txt").write_text("test prompt", encoding="utf-8")
    (tmp_path / "viko" / "skills" / "cmd_control.py").write_text("# cmd", encoding="utf-8")
    (tmp_path / "viko" / "skills" / "weather_report.py").write_text("# weather", encoding="utf-8")
    monkeypatch.setattr(analyzer, "BASE_DIR", tmp_path)

    ctx = analyzer.build_context("tambah skill crypto", action="create_skill")
    assert "intent" in ctx
    assert "files" in ctx
    assert "action" in ctx
    assert ctx["action"] == "create_skill"
