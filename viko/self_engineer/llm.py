import os


def generate_text(prompt: str, system: str | None = None) -> str:
    """Route to Claude if ANTHROPIC_API_KEY is set, otherwise use Gemini."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _claude(prompt, system)
    return _gemini(prompt, system)


def _claude(prompt: str, system: str | None = None) -> str:
    import anthropic
    client = anthropic.Anthropic()
    kwargs = {
        "model":      "claude-sonnet-4-6",
        "max_tokens": 8096,
        "messages":   [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def _gemini(prompt: str, system: str | None = None) -> str:
    from google import genai
    from google.genai import types
    from viko.core.config import get_gemini_key
    client = genai.Client(api_key=get_gemini_key())
    config = types.GenerateContentConfig(system_instruction=system) if system else None
    return client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt, config=config
    ).text
