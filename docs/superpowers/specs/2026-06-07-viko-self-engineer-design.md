# VIKO SelfEngineer Pipeline — Design Spec

**Date:** 2026-06-07
**Status:** Approved

---

## Overview

VIKO can modify its own code when instructed by voice. This includes: adding new skills, fixing bugs, changing behavior/prompt, modifying the UI, and restoring previous changes. The approach uses a state machine pipeline (SelfEngineer) with user confirmation at two critical points: before execution and before restart.

---

## Modification Scope

- **All VIKO files** may be modified (skills, prompt, config, memory, UI, core)
- **Safety**: backup is mandatory before any byte is changed
- **Versioning**: file-based initially (backup + manifest); git-based after the system proves stable

---

## Module Architecture

```
viko/
  self_engineer/
    __init__.py
    engine.py       ← main orchestrator (state machine)
    analyzer.py     ← reads and understands the VIKO codebase
    planner.py      ← LLM generates a structured plan
    generator.py    ← generates code changes/patches
    backup.py       ← file versioning & restore
    tester.py       ← syntax + import + smoke test
    restarter.py    ← graceful VIKO restart
    backups/        ← backup folder (auto-created, gitignored)

viko/skills/
  self_update.py    ← voice-facing skill, wraps engine.py
```

---

## State Machine

```
ANALYZE → PLAN → [user confirm] → GENERATE → BACKUP → APPLY → TEST → [user confirm restart] → RESTART
                      ↑ cancel                                              ↑ skip / rollback
```

**States:**

| State | Description |
|---|---|
| ANALYZE | Scan relevant files based on intent |
| PLAN | LLM generates a structured plan + announces to user |
| USER_CONFIRM_PLAN | Wait for user confirmation ("continue?") |
| GENERATE | LLM generates actual code changes |
| BACKUP | Save originals + record in manifest |
| APPLY | Write changes to disk |
| TEST | Syntax + import + smoke test in a subprocess |
| USER_CONFIRM_RESTART | Announce test result + ask to restart |
| RESTART | Graceful VIKO restart |
| ROLLBACK | Restore from backup (on test FAIL or user cancel) |

---

## Component Details

### analyzer.py

Goal: build a context package sufficient for the planner without overflowing the token budget.

```
Input: intent string + optional target_files
Output: {files: {path: content}, structure_summary, intent_category}

Logic:
  - Read VIKO manifest (all files + sizes + brief descriptions)
  - Identify relevant files based on intent:
      "new skill"    → read 1-2 existing skills as templates
      "fix bug"      → read mentioned file + recent error context
      "change prompt" → read prompt.txt only
      "change UI"    → read ui.py + ui_widgets.py header
  - Token budget: max ~20K tokens for context package
```

### planner.py

Goal: produce a structured plan that can be announced to the user and executed by the generator.

```json
{
  "intent": "Add crypto price skill",
  "summary_for_voice": "I will create a new file crypto_price.py and register it in viko.py.",
  "changes": [
    {
      "action": "create",
      "file": "viko/skills/crypto_price.py",
      "description": "New skill: fetch crypto price from CoinGecko API"
    },
    {
      "action": "modify",
      "file": "viko.py",
      "targets": ["import section", "TOOL_DECLARATIONS"],
      "description": "Register the crypto_price skill"
    }
  ],
  "test_strategy": ["syntax", "import", "mock_call"]
}
```

### generator.py

Goal: produce the actual content for each change in the plan.

```
For "create" → generate full file content
For "modify" → generate targeted patches:
    {
      "file": "viko.py",
      "patches": [
        {"before": "from viko.skills.web_search import...",
         "after": "from viko.skills.web_search import...\nfrom viko.skills.crypto_price import crypto_price"}
      ]
    }
For "prompt" → generate updated full prompt.txt content
```

Patch strategy: string-based replace (not AST manipulation) — more predictable for LLM output.

### backup.py

Goal: zero data loss before every change.

```
Backup structure:
backups/
  2026-06-07_143022_viko.py
  2026-06-07_143022_viko__skills__crypto_price.py  (path separator → __)
  manifest.json

manifest.json entry:
{
  "id": "bk_001",
  "timestamp": "2026-06-07 14:30:22",
  "intent": "add crypto price skill",
  "files_changed": ["viko.py"],
  "files_created": ["viko/skills/crypto_price.py"],
  "restorable": true
}
```

Voice restore commands:
- *"Viko, kembalikan perubahan terakhir"* → restore most recent manifest entry
- *"Viko, lihat history perubahan kamu"* → list manifest entries

### tester.py

Goal: validate changes before confirming restart, run in a separate subprocess.

```
Test sequence:
1. AST parse all modified files → syntax valid?
2. python -c "import <module>" → clean import?
3. If new skill → call function with mock args, check no crash
4. If core modification (viko.py/ui.py) → python -c "from viko.ui import VikoUI"

Result: PASS / FAIL + error message
On FAIL → automatic rollback + announce error to user
On PASS → announce: "Test passed. Restart VIKO now?"
```

### restarter.py

Goal: gracefully restart VIKO from within its own process.

```python
def restart():
    # 1. Save restart_pending flag to temp file
    # 2. QApplication.quit() on main thread
    # 3. os.execv(sys.executable, [sys.executable] + sys.argv)
    #    → replace process with new process (no zombie)

# On VIKO startup:
# - Check restart_pending flag
# - If found → announce via voice: "I have been updated and am ready"
# - Delete flag
```

### engine.py

Goal: orchestrate the full pipeline, maintain state, handle errors and rollback.

```python
class SelfEngineerEngine:
    def run(self, intent: str, target_files: list[str] = None):
        # 1. ANALYZE
        context = analyzer.build_context(intent, target_files)

        # 2. PLAN
        plan = planner.generate(context)
        announce(plan["summary_for_voice"])  # via VIKO voice

        # 3. USER CONFIRM
        if not await_user_confirm("Continue?"):
            return "Cancelled."

        # 4. GENERATE
        changes = generator.generate(plan, context)

        # 5. BACKUP (before apply)
        backup_id = backup.save(plan)

        # 6. APPLY
        apply_changes(changes)

        # 7. TEST
        result = tester.run(plan)
        if result.failed:
            backup.restore(backup_id)
            return f"Test failed: {result.error}. Changes reverted."

        # 8. USER CONFIRM RESTART
        announce("Test passed. Restart VIKO now?")
        if await_user_confirm("Restart?"):
            restarter.restart()
        else:
            return "Changes saved. Restart manually to activate."
```

---

## Voice Tool Declaration

```python
# in viko.py TOOL_DECLARATIONS
{
    "name": "self_update",
    "description": (
        "Modify VIKO's own code: add a new skill, fix a bug, change behavior/prompt, "
        "modify the UI, or restore a previous backup."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "description": "Full description of the change requested by the user"
            },
            "target_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: specific files that are relevant"
            },
            "action": {
                "type": "string",
                "enum": ["create_skill", "fix_bug", "modify_prompt", "modify_ui", "restore", "history"],
                "description": "Action category"
            }
        },
        "required": ["intent", "action"]
    }
}
```

---

## Voice Trigger Examples

| User Says | Action | Target Files |
|---|---|---|
| "Add a skill to check Bitcoin price" | create_skill | viko/skills/ + viko.py |
| "Fix the bug in the browser tool, there was an error" | fix_bug | viko/skills/browser_tool.py |
| "From now on give shorter answers" | modify_prompt | viko/prompt.txt |
| "Change the UI color to something darker" | modify_ui | viko/ui_theme.py |
| "Revert the last change" | restore | from manifest |
| "Show me your change history" | history | manifest.json |

---

## Error Handling

| Condition | Response |
|---|---|
| Analyzer fails to read file | Announce error, ask if user wants to specify file manually |
| Planner fails to generate plan | Retry once with a simpler prompt |
| Test FAIL | Automatic rollback, announce detailed error |
| Backup fails (disk full) | Abort entire operation, do not apply anything |
| Restart fails | Changes remain saved, user restarts manually |

---

## Constraints

- **Analyzer token budget**: max ~20K tokens context per operation
- **Patch size**: generator does not rewrite entire file if >200 lines; patches only the relevant sections
- **Backup retention**: keep all backups (no auto-delete); manual cleanup via voice command
- **Test timeout**: subprocess test max 30 seconds before considered FAIL
- **No automatic git ops**: no automatic git commit; git used manually after system proves stable

---

## Out of Scope (this version)

- Git-based versioning (to be implemented after system is stable)
- Multi-step rollback (only 1 level of restore for now)
- Unit test generation (smoke test only)
- Remote deployment or update from server
