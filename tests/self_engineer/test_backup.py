# tests/self_engineer/test_backup.py
import json
import shutil
import sys
import tempfile
from pathlib import Path
import pytest

@pytest.fixture
def tmp_viko(tmp_path, monkeypatch):
    """Creates a fake VIKO tree inside tmp_path."""
    (tmp_path / "viko" / "skills").mkdir(parents=True)
    fake_skill = tmp_path / "viko" / "skills" / "fake.py"
    fake_skill.write_text("# fake skill", encoding="utf-8")

    import viko.self_engineer.backup as bk
    monkeypatch.setattr(bk, "BASE_DIR", tmp_path)
    backup_dir = tmp_path / "viko" / "self_engineer" / "backups"
    monkeypatch.setattr(bk, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(bk, "MANIFEST", backup_dir / "manifest.json")
    return tmp_path

def test_save_creates_backup_file(tmp_viko):
    import viko.self_engineer.backup as bk
    plan = {"intent": "test intent"}
    entry_id = bk.save(plan, ["viko/skills/fake.py"], [])
    assert entry_id.startswith("bk_")
    backup_dir = tmp_viko / "viko" / "self_engineer" / "backups"
    backups = list(backup_dir.glob("*fake.py"))
    assert len(backups) == 1

def test_save_writes_manifest(tmp_viko):
    import viko.self_engineer.backup as bk
    plan = {"intent": "add crypto skill"}
    bk.save(plan, ["viko/skills/fake.py"], ["viko/skills/new.py"])
    history = bk.list_history()
    assert len(history) == 1
    assert history[0]["intent"] == "add crypto skill"
    assert history[0]["restorable"] is True

def test_restore_latest_restores_file(tmp_viko):
    import viko.self_engineer.backup as bk
    original = "# original content"
    fake = tmp_viko / "viko" / "skills" / "fake.py"
    fake.write_text(original, encoding="utf-8")

    plan = {"intent": "change fake"}
    bk.save(plan, ["viko/skills/fake.py"], [])

    # Simulate a bad change
    fake.write_text("# bad change", encoding="utf-8")

    msg = bk.restore_latest()
    assert "fake.py" in msg
    assert fake.read_text(encoding="utf-8") == original

def test_restore_latest_no_backup(tmp_viko):
    import viko.self_engineer.backup as bk
    msg = bk.restore_latest()
    assert "tidak ada" in msg.lower()

def test_restore_deletes_created_files(tmp_viko):
    import viko.self_engineer.backup as bk
    new_file = tmp_viko / "viko" / "skills" / "new_skill.py"
    new_file.write_text("# new", encoding="utf-8")

    plan = {"intent": "add new skill"}
    bk.save(plan, [], ["viko/skills/new_skill.py"])
    bk.restore_latest()
    assert not new_file.exists()
