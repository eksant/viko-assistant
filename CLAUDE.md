# CLAUDE.md — VIKO Assistant Developer Guide

This file tells Claude Code how to work in this repository.

---

## Project Overview

VIKO is a personal AI voice assistant (PyQt6 + Gemini Live API). The main agent loop lives in `viko.py`. Skills are in `viko/skills/`. Self-modification pipeline is in `viko/self_engineer/`.

---

## Running the App

```bash
.venv/bin/python viko.py        # run VIKO
python -m pytest tests/ -v      # run all tests
python -m pytest tests/self_engineer/ -v   # self-engineer tests only
```

Find running process: `pgrep -f "python viko.py"`
Restart: kill the PID, then `nohup .venv/bin/python viko.py > /tmp/viko.log 2>&1 &`

---

## Code Conventions

- **Language**: All code, comments, docstrings, variable names → **English**
- **User-facing strings** (what VIKO says aloud) → **Indonesian** (VIKO speaks to its owner in Indonesian)
- **No unnecessary comments** — only add a comment when the WHY is non-obvious
- **No type annotation bloat** — use `| None` shorthand (Python 3.11+)
- **Tests first** for all testable modules (TDD)

---

## Architecture

### Entry Point: `viko.py`

- Holds `TOOL_DECLARATIONS` list — the full schema for every tool Gemini can call
- `_execute_tool()` method — dispatches tool calls to skill functions
- `run()` method — main async loop (Gemini Live session)

### Adding a Skill

1. Create `viko/skills/your_skill.py`
   ```python
   def your_skill(parameters: dict, player=None, speak=None) -> str:
       ...
       return "result string"
   ```
2. Import in `viko.py` (near line 40, with other skill imports)
3. Add entry to `TOOL_DECLARATIONS` in `viko.py`
4. Add `elif name == "your_skill":` handler in `_execute_tool()`

### LLM Routing (`viko/self_engineer/llm.py`)

All code-generation LLM calls route through `llm.generate_text(prompt)`:
- `ANTHROPIC_API_KEY` set → **Claude Sonnet** (`claude-sonnet-4-6`)
- Not set → **Gemini** (`gemini-2.5-flash`)

Used by: `self_engineer/planner.py`, `self_engineer/generator.py`, `skills/dev_agent.py`, `skills/code_helper.py`

**Voice agent (Gemini Live) is always Gemini — never routed through Claude.**

### Self-Engineer Pipeline (`viko/self_engineer/`)

State machine for voice-triggered self-modification. Two confirmation points:
1. Plan confirmed → `pending_plan.json` → execute
2. Test passed → `pending_restart.json` → restart

Mutex in `SelfEngineerEngine` prevents concurrent modifications.

Backup is mandatory before any file change. Automatic rollback on test failure.

---

## Key Files

| File | Purpose |
|---|---|
| `viko.py` | Main agent, tool routing, Gemini Live session |
| `viko/prompt.txt` | System prompt — VIKO's personality and tool rules |
| `viko/core/config.py` | API key loading from `.env` |
| `viko/core/logger.py` | Structured logging — `get_logger()`, `read_recent()` |
| `viko/core/client.py` | LLM client (OpenRouter / Gemini wrapper) |
| `viko/core/memory.py` | Long-term memory extraction and storage |
| `viko/core/conversation.py` | Session message history |
| `viko/core/context_builder.py` | Builds Gemini system context |
| `viko/ui/window.py` | PyQt6 main window |
| `viko/ui/theme.py` | Colors, fonts, stylesheet constants |
| `viko/ui/widgets.py` | HUD canvas, panels, chat bubbles |
| `viko/ui/browser_panel.py` | Embedded Chromium browser widget |
| `viko/self_engineer/engine.py` | Self-modification orchestrator |
| `viko/self_engineer/llm.py` | LLM router (Claude / Gemini) |
| `viko/skills/self_update.py` | Voice-facing self-modification skill |

---

## Environment

```env
GEMINI_API_KEY=...           # required — Gemini Live voice agent
ANTHROPIC_API_KEY=...        # optional — Claude for code generation
OPENROUTER_API_KEY=...       # optional
OS_SYSTEM=mac                # mac | windows
CAMERA_INDEX=0
```

`.env` is gitignored. Never commit API keys.

---

## What NOT to Do

- Do not commit `.env`, `memory/*.db`, `memory/*.sqlite3`, or `workspace/` files
- Do not modify `viko/self_engineer/backups/` manually (gitignored, managed by backup.py)
- Do not run destructive git commands (`reset --hard`, `push --force`) without explicit user confirmation
- Do not add Indonesian comments or docstrings — user-facing strings only
- Do not refactor beyond the task scope — YAGNI
- Do not skip tests — run `pytest tests/self_engineer/` after any self-engineer change

---

## Tests

```
tests/
  self_engineer/
    test_backup.py          — 5 tests: save, manifest, restore, delete created files
    test_tester.py          — 5 tests: syntax check, import check, run()
    test_analyzer.py        — 5 tests: intent categorization, build_context
    test_generator_apply.py — 4 tests: create, overwrite, patch, patch miss
    test_engine_state.py    — 5 tests: pending plan/restart state persistence
```

All 24 tests must pass before committing changes to `viko/self_engineer/`.
