# tests/self_engineer/test_engine_state.py
import json
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def tmp_engine(tmp_path, monkeypatch):
    import viko.self_engineer.engine as eng
    pending_plan    = tmp_path / "pending_plan.json"
    pending_restart = tmp_path / "pending_restart.json"
    monkeypatch.setattr(eng, "PENDING_PLAN_FILE",    pending_plan)
    monkeypatch.setattr(eng, "PENDING_RESTART_FILE", pending_restart)
    return tmp_path


def test_save_and_load_pending_plan(tmp_engine):
    import viko.self_engineer.engine as eng
    plan    = {"intent": "add skill", "changes": []}
    context = {"action": "create_skill", "files": {}}
    eng._save_pending_plan(plan, context)
    loaded_plan, loaded_ctx = eng._load_pending_plan()
    assert loaded_plan["intent"] == "add skill"
    assert loaded_ctx["action"] == "create_skill"


def test_clear_pending_plan(tmp_engine):
    import viko.self_engineer.engine as eng
    eng._save_pending_plan({"intent": "x"}, {"action": "y"})
    eng._clear_pending_plan()
    plan, ctx = eng._load_pending_plan()
    assert plan is None
    assert ctx is None


def test_load_pending_plan_missing(tmp_engine):
    import viko.self_engineer.engine as eng
    plan, ctx = eng._load_pending_plan()
    assert plan is None
    assert ctx is None


def test_save_and_load_pending_restart(tmp_engine):
    import viko.self_engineer.engine as eng
    changes = [{"action": "create", "file": "viko/skills/x.py"}]
    eng._save_pending_restart(changes, "bk_001")
    loaded_changes, backup_id = eng._load_pending_restart()
    assert backup_id == "bk_001"
    assert loaded_changes[0]["file"] == "viko/skills/x.py"


def test_clear_pending_restart(tmp_engine):
    import viko.self_engineer.engine as eng
    eng._save_pending_restart([], "bk_001")
    eng._clear_pending_restart()
    changes, bid = eng._load_pending_restart()
    assert changes is None
