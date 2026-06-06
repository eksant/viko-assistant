import sys
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR = _get_base_dir()

VIKO_MANIFEST = {
    "viko.py":                      "Entry point: imports all skills, TOOL_DECLARATIONS list, _execute_tool handler",
    "viko/prompt.txt":              "System prompt: VIKO's personality, tool usage rules, routing rules",
    "viko/core/config.py":          "Config: API keys, settings",
    "viko/core/logger.py":          "Logging: structured RotatingFileHandler, get_logger(), read_recent()",
    "viko/core/client.py":          "LLM client: OpenRouter/Gemini API wrapper",
    "viko/core/memory.py":          "Memory: extract and store facts from conversations",
    "viko/core/conversation.py":    "Conversation: session management, message history",
    "viko/core/context_builder.py": "Context builder: builds system context for Gemini",
    "viko/core/vector_store.py":    "Vector store: semantic search over messages",
    "viko/core/workspace.py":       "Workspace: file storage for browser-rendered content",
    "viko/ui/window.py":            "UI: main window, PyQt6 widgets, browser panel toggle",
    "viko/ui/theme.py":             "UI theme: colors, fonts, stylesheet",
    "viko/ui/widgets.py":           "UI widgets: activity panel, chat bubbles",
}

SKILL_TEMPLATES = [
    "viko/skills/cmd_control.py",
    "viko/skills/weather_report.py",
]

TOKEN_BUDGET = 20_000  # rough: 1 token ≈ 4 chars


def _chars_to_tokens(n: int) -> int:
    return n // 4


def _read_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[Could not read: {e}]"


def _categorize_intent(intent: str) -> str:
    low = intent.lower()
    if any(k in low for k in ("skill baru", "tambah skill", "create skill", "add skill", "buat skill")):
        return "create_skill"
    if any(k in low for k in ("fix", "bug", "error", "perbaiki", "broken", "rusak")):
        return "fix_bug"
    if any(k in low for k in ("prompt", "perilaku", "jawab", "behav", "personality", "kepribadian", "formal", "singkat")):
        return "modify_prompt"
    if any(k in low for k in ("ui", "warna", "color", "theme", "tampilan", "interface", "gelap", "terang")):
        return "modify_ui"
    return "general"


def build_context(intent: str, target_files: list[str] | None = None, action: str = "") -> dict:
    category     = action if action in ("create_skill", "fix_bug", "modify_prompt", "modify_ui") else _categorize_intent(intent)
    files: dict  = {}
    total_tokens = 0

    def _add(rel_path: str):
        nonlocal total_tokens
        if rel_path in files or total_tokens >= TOKEN_BUDGET:
            return
        content = _read_safe(BASE_DIR / rel_path)
        tokens  = _chars_to_tokens(len(content))
        if total_tokens + tokens > TOKEN_BUDGET:
            budget_chars = (TOKEN_BUDGET - total_tokens) * 4
            files[rel_path] = content[:budget_chars] + "\n... [truncated]"
            total_tokens = TOKEN_BUDGET
        else:
            files[rel_path] = content
            total_tokens   += tokens

    for f in (target_files or []):
        _add(f)

    if category == "create_skill":
        for t in SKILL_TEMPLATES:
            _add(t)
        viko_head = _read_safe(BASE_DIR / "viko.py")[:6000]
        files["viko.py (excerpt)"] = viko_head
        total_tokens += _chars_to_tokens(len(viko_head))

    elif category == "fix_bug":
        if not target_files:
            for rel in VIKO_MANIFEST:
                _add(rel)
        # Include recent log entries so LLM can see actual error messages
        try:
            from viko.core.logger import read_recent
            recent_logs = read_recent(100)
            if recent_logs and "(no log file yet)" not in recent_logs:
                files["viko/logs/viko.log (recent)"] = recent_logs
                total_tokens += _chars_to_tokens(len(recent_logs))
        except Exception:
            pass

    elif category == "modify_prompt":
        _add("viko/prompt.txt")

    elif category == "modify_ui":
        _add("viko/ui_theme.py")
        _add("viko/ui.py")

    else:
        for rel in VIKO_MANIFEST:
            _add(rel)

    return {
        "intent":            intent,
        "action":            category,
        "files":             files,
        "structure_summary": VIKO_MANIFEST,
        "token_estimate":    total_tokens,
    }
