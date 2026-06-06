# tests/self_engineer/test_tester.py
import sys
import tempfile
from pathlib import Path
import pytest


def test_syntax_check_valid_file(tmp_path):
    f = tmp_path / "good.py"
    f.write_text("x = 1\nprint(x)\n", encoding="utf-8")
    from viko.self_engineer.tester import _syntax_check
    result = _syntax_check(f)
    assert result.passed is True


def test_syntax_check_invalid_file(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("def foo(\n    broken syntax here\n", encoding="utf-8")
    from viko.self_engineer.tester import _syntax_check
    result = _syntax_check(f)
    assert result.passed is False
    assert "SyntaxError" in result.message or "syntax" in result.message.lower()


def test_import_check_stdlib():
    from viko.self_engineer import tester
    result = tester._import_check("json")
    assert result.passed is True


def test_import_check_bad_module():
    from viko.self_engineer.tester import _import_check
    result = _import_check("viko_nonexistent_module_xyz_abc")
    assert result.passed is False


def test_run_fails_on_syntax_error(tmp_path, monkeypatch):
    bad = tmp_path / "bad_skill.py"
    bad.write_text("def broken(\n    not valid python\n", encoding="utf-8")
    from viko.self_engineer import tester
    monkeypatch.setattr(tester, "BASE_DIR", tmp_path)
    changes = [{"action": "create", "file": "bad_skill.py"}]
    result = tester.run({}, changes)
    assert result.passed is False
    assert "SyntaxError" in result.message or "syntax" in result.message.lower()
