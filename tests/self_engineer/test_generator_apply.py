import pytest


def test_apply_creates_new_file(tmp_path, monkeypatch):
    from viko.self_engineer import generator
    monkeypatch.setattr(generator, "BASE_DIR", tmp_path)
    changes = [{"action": "create", "file": "viko/skills/test_skill.py", "content": "def test_skill(): pass\n"}]
    applied = generator.apply_changes(changes)
    dest = tmp_path / "viko" / "skills" / "test_skill.py"
    assert dest.exists()
    assert "test_skill" in dest.read_text()
    assert any("Created" in a for a in applied)


def test_apply_overwrites_file(tmp_path, monkeypatch):
    from viko.self_engineer import generator
    monkeypatch.setattr(generator, "BASE_DIR", tmp_path)
    f = tmp_path / "viko" / "prompt.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("old content", encoding="utf-8")
    changes = [{"action": "overwrite", "file": "viko/prompt.txt", "content": "new prompt"}]
    generator.apply_changes(changes)
    assert f.read_text(encoding="utf-8") == "new prompt"


def test_apply_patch_replaces_string(tmp_path, monkeypatch):
    from viko.self_engineer import generator
    monkeypatch.setattr(generator, "BASE_DIR", tmp_path)
    f = tmp_path / "viko.py"
    f.write_text("import os\nimport sys\n\nTOOL_DECLARATIONS = []\n", encoding="utf-8")
    changes = [{
        "action": "patch",
        "file": "viko.py",
        "patches": [{"before": "import os\nimport sys", "after": "import os\nimport sys\nfrom viko.skills.new_skill import new_skill"}]
    }]
    generator.apply_changes(changes)
    content = f.read_text(encoding="utf-8")
    assert "from viko.skills.new_skill import new_skill" in content


def test_apply_patch_miss_reported(tmp_path, monkeypatch):
    from viko.self_engineer import generator
    monkeypatch.setattr(generator, "BASE_DIR", tmp_path)
    f = tmp_path / "viko.py"
    f.write_text("import os\n", encoding="utf-8")
    changes = [{"action": "patch", "file": "viko.py", "patches": [{"before": "DOES_NOT_EXIST", "after": "x"}]}]
    applied = generator.apply_changes(changes)
    assert any("PATCH MISS" in a for a in applied)
