import json
import re

MODEL = "gemini-2.5-flash"


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


def generate(context: dict) -> dict:
    files_summary = "\n".join(
        f"  [{path}]:\n{content[:400]}{'...' if len(content) > 400 else ''}"
        for path, content in context["files"].items()
    )

    prompt = f"""You are an expert Python developer analyzing the VIKO voice assistant codebase.

User intent: {context['intent']}
Action category: {context['action']}

Relevant files:
{files_summary}

VIKO project structure:
{json.dumps(context['structure_summary'], indent=2)}

Generate a minimal, precise modification plan. Return ONLY valid JSON — no markdown, no explanation:
{{
  "intent": "short description",
  "summary_for_voice": "1-2 kalimat bahasa Indonesia yang menjelaskan perubahan apa yang akan dilakukan",
  "changes": [
    {{
      "action": "create",
      "file": "viko/skills/new_skill.py",
      "description": "what this file does",
      "targets": []
    }},
    {{
      "action": "modify",
      "file": "viko.py",
      "description": "add import and TOOL_DECLARATIONS entry for new_skill",
      "targets": ["import section", "TOOL_DECLARATIONS", "_execute_tool handler"]
    }}
  ],
  "test_strategy": ["syntax", "import"],
  "new_skill_function": "function_name_or_null"
}}

Rules:
- For create_skill: ALWAYS include (1) the new skill file AND (2) viko.py modification for import + TOOL_DECLARATIONS + _execute_tool handler
- For modify_prompt: only modify viko/prompt.txt, action must be "modify"
- For fix_bug: identify the specific file(s) to patch
- Keep changes minimal — only what's strictly needed
- All file paths must be relative to VIKO root (e.g. "viko/skills/crypto_price.py")
- summary_for_voice must be in Indonesian

JSON:"""

    raw = None
    for attempt in range(2):
        try:
            raw = _generate(prompt)
            return json.loads(_strip_fences(raw))
        except json.JSONDecodeError:
            if attempt == 0:
                continue
            raise ValueError(f"Planner returned invalid JSON after 2 attempts. Raw: {(raw or '')[:200]}")
        except Exception:
            if attempt == 0:
                continue
            raise
