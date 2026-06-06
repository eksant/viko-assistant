import json
import os
import sys
import tempfile
import threading
from pathlib import Path

FLAG_FILE = Path(tempfile.gettempdir()) / "viko_restart_pending.json"


def set_restart_flag(message: str = "Saya sudah diperbarui dan siap."):
    FLAG_FILE.write_text(json.dumps({"message": message}), encoding="utf-8")


def check_and_clear_flag() -> str | None:
    """Returns the restart message if flag exists, clears it, else returns None."""
    if not FLAG_FILE.exists():
        return None
    try:
        data    = json.loads(FLAG_FILE.read_text(encoding="utf-8"))
        message = data.get("message", "Saya sudah diperbarui dan siap.")
        FLAG_FILE.unlink(missing_ok=True)
        return message
    except Exception:
        FLAG_FILE.unlink(missing_ok=True)
        return None


def restart(speak_fn=None):
    """Gracefully quit PyQt6 then os.execv to replace this process with a fresh VIKO."""
    if speak_fn:
        try:
            speak_fn("Memulai ulang. Sebentar.")
        except Exception:
            pass

    set_restart_flag("Saya sudah diperbarui dan siap.")

    def _do_restart():
        import time
        time.sleep(1.5)  # let speak_fn audio finish
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.quit()
        except Exception:
            pass
        os.execv(sys.executable, [sys.executable] + sys.argv)

    threading.Thread(target=_do_restart, daemon=True).start()
