import json
import re
import sys
from pathlib import Path

MODEL = "gemini-2.5-flash"


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR = _get_base_dir()


def _get_api_key() -> str:
    from viko.config import get_gemini_key
    return get_gemini_key()


def _generate(prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=_get_api_key())
    return client.models.generate_content(model=MODEL, contents=prompt).text


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()


def _generate_new_file(change: dict, context: dict) -> str:
    templates = "\n\n".join(
        f"--- {k} ---\n{v[:1500]}"
        for k, v in context["files"].items()
        if "skills" in k
    )
    prompt = f"""Write a complete Python skill file for VIKO voice assistant.

File: {change['file']}
Purpose: {change.get('description', '')}
User intent: {context['intent']}

Reference skill files (follow the same pattern):
{templates}

Rules:
- Main function signature: def func_name(parameters: dict, player=None, speak=None) -> str
- Return a string result (success message or error description)
- Use only requests or stdlib for external HTTP calls — no heavy dependencies
- Output ONLY raw Python code, no markdown, no explanations

Code:"""
    return _strip_fences(_generate(prompt))


def _generate_patch(change: dict, context: dict) -> list[dict]:
    file_path = change["file"]
    current   = context["files"].get(file_path) or context["files"].get(file_path + " (excerpt)", "")
    if not current:
        full = BASE_DIR / file_path
        if full.exists():
            current = full.read_text(encoding="utf-8")

    prompt = f"""You are modifying a Python file for the VIKO voice assistant.

File: {file_path}
What to change: {change.get('description', '')}
Specific targets: {', '.join(change.get('targets', []))}
User intent: {context['intent']}

Current file content:
{current[:8000]}

Generate the MINIMAL set of string patches. Return ONLY valid JSON array — no markdown:
[
  {{
    "before": "exact unique substring from file to replace",
    "after": "replacement string"
  }}
]

Rules:
- "before" must be an EXACT copy-paste substring from the current file content above
- "before" must be long enough to be unique in the file
- Make only the minimal necessary change
- For new import: include surrounding lines as context to make "before" unique
- For new TOOL_DECLARATIONS entry: include the closing bracket ] in "before" and place new entry before it

JSON array:"""

    raw = None
    for attempt in range(2):
        try:
            raw = _generate(prompt)
            return json.loads(_strip_fences(raw))
        except (json.JSONDecodeError, Exception):
            if attempt == 0:
                continue
            raise ValueError(f"Generator returned invalid JSON patches for {file_path}. Raw: {(raw or '')[:200]}")


def _generate_prompt_update(context: dict) -> str:
    current = context["files"].get("viko/prompt.txt", "")
    prompt  = f"""Update the VIKO voice assistant system prompt based on the user's request.

User intent: {context['intent']}

Current prompt:
{current}

Return ONLY the updated prompt text. No explanations, no markdown fences.

Updated prompt:"""
    return _generate(prompt).strip()


def generate(plan: dict, context: dict) -> list[dict]:
    results = []
    for change in plan.get("changes", []):
        action    = change.get("action", "")
        file_path = change.get("file", "")

        if action == "create":
            content = _generate_new_file(change, context)
            results.append({"action": "create", "file": file_path, "content": content})

        elif action == "modify":
            if file_path == "viko/prompt.txt":
                content = _generate_prompt_update(context)
                results.append({"action": "overwrite", "file": file_path, "content": content})
            else:
                patches = _generate_patch(change, context)
                results.append({"action": "patch", "file": file_path, "patches": patches})

    return results


def apply_changes(changes: list[dict]) -> list[str]:
    log = []
    for change in changes:
        fpath  = BASE_DIR / change["file"]
        action = change["action"]

        if action == "create":
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(change["content"], encoding="utf-8")
            log.append(f"Created: {change['file']}")

        elif action == "overwrite":
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(change["content"], encoding="utf-8")
            log.append(f"Updated: {change['file']}")

        elif action == "patch":
            if not fpath.exists():
                log.append(f"SKIP (not found): {change['file']}")
                continue
            content = fpath.read_text(encoding="utf-8")
            for patch in change.get("patches", []):
                before = patch.get("before", "")
                after  = patch.get("after", "")
                if before and before in content:
                    content = content.replace(before, after, 1)
                else:
                    log.append(f"PATCH MISS in {change['file']}: '{before[:60]}'")
            fpath.write_text(content, encoding="utf-8")
            log.append(f"Patched: {change['file']}")

    return log
