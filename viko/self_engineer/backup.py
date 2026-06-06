import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR   = _get_base_dir()
BACKUP_DIR = BASE_DIR / "viko" / "self_engineer" / "backups"
MANIFEST   = BACKUP_DIR / "manifest.json"


def _ensure_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")


def _next_id(entries: list) -> str:
    if not entries:
        return "bk_001"
    nums = []
    for e in entries:
        try:
            nums.append(int(e["id"].split("_")[1]))
        except (KeyError, ValueError, IndexError):
            pass
    return f"bk_{(max(nums) + 1) if nums else 1:03d}"


def _load_manifest() -> list:
    if not MANIFEST.exists():
        return []
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return []


def save(plan: dict, files_changed: list[str], files_created: list[str]) -> str:
    _ensure_dir()
    ts      = _ts()
    entries = _load_manifest()
    entry_id = _next_id(entries)

    for rel_path in files_changed:
        src = BASE_DIR / rel_path
        if src.exists():
            safe = rel_path.replace("/", "__").replace("\\", "__")
            shutil.copy2(src, BACKUP_DIR / f"{ts}_{entry_id}_{safe}")

    entry = {
        "id":            entry_id,
        "timestamp":     ts,
        "intent":        plan.get("intent", ""),
        "files_changed": files_changed,
        "files_created": files_created,
        "restorable":    True,
    }
    entries.append(entry)
    MANIFEST.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return entry_id


def restore(entry_id: str) -> str:
    entries = _load_manifest()
    entry   = next((e for e in entries if e["id"] == entry_id), None)
    if not entry:
        return f"Backup {entry_id} tidak ditemukan."

    ts           = entry["timestamp"]
    entry_id_val = entry["id"]
    restored = []
    for rel_path in entry["files_changed"]:
        safe = rel_path.replace("/", "__").replace("\\", "__")
        src  = BACKUP_DIR / f"{ts}_{entry_id_val}_{safe}"
        dst  = BASE_DIR / rel_path
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            restored.append(rel_path)

    for rel_path in entry["files_created"]:
        dst = BASE_DIR / rel_path
        if dst.exists():
            dst.unlink()

    entry["restorable"] = False
    MANIFEST.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return f"Restored: {', '.join(restored)}" if restored else "Tidak ada file yang di-restore."


def restore_latest() -> str:
    entries    = _load_manifest()
    restorable = [e for e in entries if e.get("restorable")]
    if not restorable:
        return "Tidak ada backup yang bisa di-restore."
    return restore(restorable[-1]["id"])


def list_history() -> list[dict]:
    return _load_manifest()
