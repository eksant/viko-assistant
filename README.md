# VIKO — Virtual Intelligent Knowledge Operator

VIKO is a personal AI voice assistant built with PyQt6 and Google Gemini Live API. It listens to your voice, executes tools, and can even modify its own source code on command.

> **Proprietary software. See [LICENSE](LICENSE) for terms.**

---

## Features

- **Real-time voice conversation** — powered by Gemini Live API (native audio streaming)
- **Embedded browser** — built-in Chromium browser panel with AI control
- **20+ skills** — web search, file management, app control, code generation, weather, flight lookup, reminders, and more
- **Self-modification** — VIKO can add new skills, fix bugs, update its own prompt, or modify its UI via voice command
- **Memory** — long-term vector memory and conversation history (SQLite + ChromaDB)
- **Workspace** — file storage for AI-generated content (documents, code, presentations, wireframes)
- **Claude + Gemini routing** — uses Claude (Sonnet) for code generation if `ANTHROPIC_API_KEY` is set, falls back to Gemini

---

## Requirements

- Python 3.11+
- macOS (primary target; Windows partially supported)
- Google Gemini API key
- Anthropic API key (optional — enables Claude for code generation)

---

## Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd viko-assistant

# 2. Install dependencies
python setup.py

# 3. Configure environment
cp .env.example .env   # then fill in your API keys
```

### Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here   # optional, enables Claude
OPENROUTER_API_KEY=your_openrouter_key_here     # optional
OS_SYSTEM=mac                                    # mac | windows
CAMERA_INDEX=0                                   # webcam index
```

---

## Running

```bash
python viko.py
```

---

## Architecture

```
viko.py                  — Main agent: Gemini Live session, tool routing
viko/
  prompt.txt             — System prompt (VIKO's personality + tool rules)
  ui.py                  — PyQt6 main window
  ui_widgets.py          — HUD widgets, activity panel
  ui_theme.py            — Colors, fonts, stylesheet
  memory.py              — Long-term memory extraction
  conversation.py        — Session management, SQLite history
  context_builder.py     — Builds context for Gemini
  vector_store.py        — ChromaDB semantic search
  workspace.py           — File storage for generated content
  config.py              — API key loading
  skills/
    self_update.py        — Voice-facing self-modification skill
    dev_agent.py          — Build complete projects from scratch
    code_helper.py        — Code assistance, debugging, file editing
    browser_tool.py       — Embedded browser control (JS + CDP)
    computer_control.py   — Mouse, keyboard, screenshot automation
    file_controller.py    — File system operations
    web_search.py         — DuckDuckGo search
    weather_report.py     — Weather lookup
    ... (20+ skills total)
  self_engineer/
    engine.py             — Self-modification state machine (mutex-protected)
    analyzer.py           — Reads codebase to build LLM context
    planner.py            — Generates structured change plan via LLM
    generator.py          — Generates code patches and new files
    backup.py             — File versioning + manifest before every change
    tester.py             — AST syntax + subprocess import + core load checks
    restarter.py          — Graceful restart via os.execv + flag file
    llm.py                — LLM router: Claude if key set, else Gemini
    backups/              — Timestamped backup files (gitignored)
```

### Self-Modification Voice Flow

```
User: "Viko, tambahkan skill untuk cek harga Bitcoin"
  → Gemini calls self_update(intent="...", action="create_skill")
  → ANALYZE → PLAN → "Saya akan buat crypto_price.py. Lanjutkan?"

User: "ya, lanjutkan"
  → self_update(action="confirm")
  → BACKUP → GENERATE → APPLY → TEST → "Test berhasil. Restart sekarang?"

User: "ya restart"
  → self_update(action="confirm")
  → os.execv restart → "Saya sudah diperbarui dan siap."
```

---

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run self-engineer tests only
python -m pytest tests/self_engineer/ -v

# Syntax check
python -m py_compile viko.py
```

### Adding a New Skill

1. Create `viko/skills/your_skill.py` with a function: `def your_skill(parameters: dict, player=None, speak=None) -> str`
2. Add import in `viko.py`
3. Add entry to `TOOL_DECLARATIONS` in `viko.py`
4. Add handler in `_execute_tool()` in `viko.py`

Or just say: *"Viko, tambahkan skill untuk [deskripsi]"* and let VIKO do it.

---

## License

Proprietary. See [LICENSE](LICENSE). All rights reserved.
