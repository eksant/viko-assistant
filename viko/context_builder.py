"""
viko/context_builder.py

Builds context strings and initial conversation turns for Gemini Live sessions
from stored conversation history and long-term memory.
"""

from viko.conversation import get_recent_messages, get_recent_summaries
from viko.memory import load_memory, format_memory_for_prompt


def build_system_context() -> str:
    """
    Build a context string from stored history to inject into Gemini system_instruction.

    Combines:
    1. Facts summary from long-term memory (if any)
    2. Recent session summaries (last 5), newest-first

    Returns empty string if no history exists.
    """
    try:
        parts = []

        memory = load_memory()
        memory_text = format_memory_for_prompt(memory)
        if memory_text:
            parts.append(memory_text)

        summaries = get_recent_summaries(5)
        if summaries:
            lines = ["[PERCAKAPAN SEBELUMNYA — untuk konteks, jangan dibahas kecuali relevan]"]
            for i, summary in enumerate(summaries):
                if i == 0:
                    lines.append(f"Sesi terbaru: {summary}")
                else:
                    lines.append(f"Sesi sebelumnya: {summary}")
            parts.append("\n".join(lines))

        return "\n\n".join(parts)

    except Exception:
        return ""


def get_initial_turns() -> list[dict]:
    """
    Return last 20 messages formatted as Gemini turns for context injection.

    Maps DB roles: "user" -> "user", "assistant"/"viko"/anything else -> "model"
    Skips messages with empty content.
    Returns empty list if no history.
    """
    try:
        messages = get_recent_messages(20)
        turns = []
        for msg in messages:
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            role = "user" if msg.get("role") == "user" else "model"
            turns.append({"role": role, "parts": [{"text": content}]})
        return turns

    except Exception:
        return []
