---
name: add-skill
description: Add a new skill to VIKO. Creates the skill file, registers it in viko.py, and runs tests.
---

# Adding a New VIKO Skill

## Checklist

1. **Create** `viko/skills/<skill_name>.py`
   - Function signature: `def <skill_name>(parameters: dict, player=None, speak=None) -> str`
   - Return a string result (success message or error)
   - Use only stdlib or already-listed requirements for HTTP calls

2. **Import** in `viko.py` (after line ~47, with other skill imports):
   ```python
   from viko.skills.<skill_name> import <skill_name>
   ```

3. **Register** in `TOOL_DECLARATIONS` in `viko.py`:
   ```python
   {
       "name": "<skill_name>",
       "description": "What this skill does",
       "parameters": {
           "type": "OBJECT",
           "properties": {
               "param": {"type": "STRING", "description": "..."}
           },
           "required": ["param"]
       }
   },
   ```

4. **Handle** in `_execute_tool()` in `viko.py`:
   ```python
   elif name == "<skill_name>":
       r = await loop.run_in_executor(None, lambda: <skill_name>(parameters=args, player=self.ui, speak=self.speak))
       result = r or "Done."
   ```

5. **Verify import**:
   ```bash
   python3 -c "from viko.skills.<skill_name> import <skill_name>; print('OK')"
   ```

6. **Commit**:
   ```bash
   git add viko/skills/<skill_name>.py viko.py
   git commit -m "feat: add <skill_name> skill"
   ```

## Notes

- Skills run in a thread executor — they are blocking/synchronous
- `player` is the `VikoUI` instance — use it to control the browser panel or write logs
- `speak` is a callable — use it to make VIKO say something mid-execution
- Indonesian strings for user-facing messages, English for everything else
