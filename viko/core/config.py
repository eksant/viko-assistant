import os
from pathlib import Path
from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _BASE_DIR / ".env"

load_dotenv(_ENV_PATH, override=False)


def get_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in .env")
    return key


def get_openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set in .env")
    return key


def get_os() -> str:
    return os.environ.get("OS_SYSTEM", "mac").lower()


def is_windows() -> bool: return get_os() == "windows"
def is_mac()     -> bool: return get_os() == "mac"
def is_linux()   -> bool: return get_os() == "linux"


def save_keys(gemini_api_key: str = "", openrouter_api_key: str = "", os_system: str = "") -> None:
    data = _load_env_dict()
    if gemini_api_key.strip():
        data["GEMINI_API_KEY"] = gemini_api_key.strip()
        os.environ["GEMINI_API_KEY"] = gemini_api_key.strip()
    if openrouter_api_key.strip():
        data["OPENROUTER_API_KEY"] = openrouter_api_key.strip()
        os.environ["OPENROUTER_API_KEY"] = openrouter_api_key.strip()
    if os_system.strip():
        data["OS_SYSTEM"] = os_system.strip()
        os.environ["OS_SYSTEM"] = os_system.strip()
    _write_env_dict(data)


def is_configured() -> bool:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        key = _load_env_dict().get("GEMINI_API_KEY", "")
    return bool(key and len(key) > 15)


def _load_env_dict() -> dict:
    result = {}
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, _, v = stripped.partition("=")
                result[k.strip()] = v.strip()
    return result


def _write_env_dict(data: dict) -> None:
    lines = [f"{k}={v}" for k, v in data.items()]
    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
