---
name: self-engineer-debug
description: Debug the VIKO self-modification pipeline. Check state files, backup manifest, and run tests.
---

# Debugging the SelfEngineer Pipeline

## Check State Files

```bash
# Check if there's a pending plan waiting for confirmation
cat viko/self_engineer/backups/pending_plan.json 2>/dev/null || echo "No pending plan"

# Check if there's a pending restart waiting for confirmation
cat viko/self_engineer/backups/pending_restart.json 2>/dev/null || echo "No pending restart"

# Check restart flag in temp dir
cat /tmp/viko_restart_pending.json 2>/dev/null || echo "No restart flag"
```

## Check Backup Manifest

```bash
python3 -c "
from viko.self_engineer.backup import list_history
for e in list_history():
    print(e['id'], e['timestamp'], e['intent'], '| restorable:', e['restorable'])
"
```

## Clear Stuck State

```bash
python3 -c "
from viko.self_engineer.engine import _clear_pending_plan, _clear_pending_restart
_clear_pending_plan()
_clear_pending_restart()
print('State cleared')
"
```

## Run Tests

```bash
python3 -m pytest tests/self_engineer/ -v
```

## Restore Latest Backup

```bash
python3 -c "
from viko.self_engineer.backup import restore_latest
print(restore_latest())
"
```

## Check Active LLM Provider

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
key = os.environ.get('ANTHROPIC_API_KEY')
print('Provider: Claude' if key else 'Provider: Gemini (fallback)')
"
```

## Pipeline Flow

```
self_update(action="create_skill"|"fix_bug"|"modify_prompt"|"modify_ui")
  → analyzer.build_context()
  → planner.generate()      ← LLM call (Claude or Gemini)
  → saves pending_plan.json
  → returns "Plan summary. Lanjutkan?"

self_update(action="confirm")   ← user said "ya"
  → generator.generate()    ← LLM call (Claude or Gemini)
  → backup.save()
  → generator.apply_changes()
  → tester.run()
  → saves pending_restart.json
  → returns "Test berhasil. Restart sekarang?"

self_update(action="confirm")   ← user said "ya restart"
  → restarter.restart()
  → os.execv (process replace)
  → new VIKO detects restart flag → announces update
```
