import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR  = Path(__file__).resolve().parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "viko.log"
_FORMAT   = "[%(asctime)s][%(levelname)s][%(name)s] %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def _init():
    global _initialized
    if _initialized:
        return
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("viko")
    root.setLevel(logging.DEBUG)

    if not root.handlers:
        # File handler — rotate at 5 MB, keep 3 backups
        fh = RotatingFileHandler(
            _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FMT))
        root.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FMT))
        root.addHandler(ch)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    _init()
    return logging.getLogger(f"viko.{name}")


def read_recent(n_lines: int = 100) -> str:
    """Return the last n_lines of the log file as a string."""
    if not _LOG_FILE.exists():
        return "(no log file yet)"
    try:
        lines = _LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n_lines:])
    except Exception as e:
        return f"(could not read log: {e})"
