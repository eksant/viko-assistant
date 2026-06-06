import json
import sys
import threading
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR             = _get_base_dir()
_STATE_DIR           = BASE_DIR / "viko" / "self_engineer" / "backups"
PENDING_PLAN_FILE    = _STATE_DIR / "pending_plan.json"
PENDING_RESTART_FILE = _STATE_DIR / "pending_restart.json"


def _ensure_dir():
    _STATE_DIR.mkdir(parents=True, exist_ok=True)


# ── State helpers ─────────────────────────────────────────────────────────────

def _save_pending_plan(plan: dict, context: dict):
    _ensure_dir()
    PENDING_PLAN_FILE.write_text(
        json.dumps({"plan": plan, "context": context}), encoding="utf-8"
    )


def _load_pending_plan() -> tuple[dict | None, dict | None]:
    if not PENDING_PLAN_FILE.exists():
        return None, None
    try:
        data = json.loads(PENDING_PLAN_FILE.read_text(encoding="utf-8"))
        return data["plan"], data["context"]
    except Exception:
        return None, None


def _clear_pending_plan():
    PENDING_PLAN_FILE.unlink(missing_ok=True)


def _save_pending_restart(changes: list[dict], backup_id: str):
    _ensure_dir()
    PENDING_RESTART_FILE.write_text(
        json.dumps({"changes": changes, "backup_id": backup_id}), encoding="utf-8"
    )


def _load_pending_restart() -> tuple[list | None, str | None]:
    if not PENDING_RESTART_FILE.exists():
        return None, None
    try:
        data = json.loads(PENDING_RESTART_FILE.read_text(encoding="utf-8"))
        return data["changes"], data["backup_id"]
    except Exception:
        return None, None


def _clear_pending_restart():
    PENDING_RESTART_FILE.unlink(missing_ok=True)


# ── Engine ────────────────────────────────────────────────────────────────────

class SelfEngineerEngine:

    def __init__(self):
        self._lock = threading.Lock()

    def run(
        self,
        intent:       str,
        action:       str,
        target_files: list[str] | None = None,
        speak=None,
    ) -> str:
        # Utility actions (cancel/history/restore/confirm) bypass the lock
        if action in ("cancel", "history", "restore", "confirm"):
            return self._run_inner(intent, action, target_files, speak)

        if not self._lock.acquire(blocking=False):
            return "Sedang memproses permintaan sebelumnya. Tunggu sebentar ya, nanti lanjut."

        try:
            return self._run_inner(intent, action, target_files, speak)
        finally:
            self._lock.release()

    def _run_inner(
        self,
        intent:       str,
        action:       str,
        target_files: list[str] | None = None,
        speak=None,
    ) -> str:
        from viko.self_engineer import analyzer, planner, generator, backup, tester, restarter

        if action == "cancel":
            _clear_pending_plan()
            _clear_pending_restart()
            return "Dibatalkan."

        if action == "history":
            history = backup.list_history()
            if not history:
                return "Belum ada history perubahan."
            lines = [f"{e['id']}: {e['timestamp']} — {e['intent']}" for e in history[-5:]]
            return "5 perubahan terakhir:\n" + "\n".join(lines)

        if action == "restore":
            return backup.restore_latest()

        if action == "confirm":
            changes, backup_id = _load_pending_restart()
            if changes is not None:
                _clear_pending_restart()
                restarter.restart(speak_fn=speak)
                return "Memulai ulang VIKO..."

            plan, context = _load_pending_plan()
            if plan is None:
                return "Tidak ada operasi yang menunggu konfirmasi."

            _clear_pending_plan()
            return self._execute_plan(plan, context, speak)

        try:
            context = analyzer.build_context(intent, target_files, action)
        except Exception as e:
            return f"Gagal menganalisis codebase: {e}"

        try:
            plan = planner.generate(context)
        except Exception as e:
            return f"Gagal membuat plan: {e}"

        _save_pending_plan(plan, context)
        summary = plan.get("summary_for_voice", "Saya akan melakukan perubahan pada kode.")
        return f"{summary} Lanjutkan?"

    def _execute_plan(self, plan: dict, context: dict, speak=None) -> str:
        from viko.self_engineer import generator, backup, tester, restarter

        try:
            changes = generator.generate(plan, context)
        except Exception as e:
            return f"Gagal generate kode: {e}"

        files_changed = [c["file"] for c in changes if c["action"] in ("patch", "overwrite")]
        files_created = [c["file"] for c in changes if c["action"] == "create"]

        try:
            backup_id = backup.save(plan, files_changed, files_created)
        except Exception as e:
            return f"Gagal membuat backup: {e}. Operasi dibatalkan."

        try:
            applied = generator.apply_changes(changes)
            print(f"[SelfEngineer] Applied: {applied}")
        except Exception as e:
            backup.restore(backup_id)
            return f"Gagal apply perubahan: {e}. Perubahan dikembalikan."

        result = tester.run(plan, changes)
        if not result.passed:
            backup.restore(backup_id)
            return f"Test gagal: {result.message}. Perubahan dikembalikan ke backup."

        _save_pending_restart(changes, backup_id)
        return f"Test berhasil: {result.message}. Restart VIKO sekarang?"


# Module-level convenience
_engine = SelfEngineerEngine()


def run(intent: str, action: str, target_files: list[str] | None = None, speak=None) -> str:
    return _engine.run(intent=intent, action=action, target_files=target_files, speak=speak)
