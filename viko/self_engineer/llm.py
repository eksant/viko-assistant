import os


def generate_text(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    """Route to Claude if ANTHROPIC_API_KEY is set, otherwise use Gemini."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _claude(prompt, system, max_tokens)
    return _gemini(prompt, system, max_tokens)


def _claude(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    import anthropic
    client = anthropic.Anthropic()
    kwargs = {
        "model":      "claude-sonnet-4-6",
        "max_tokens": max_tokens if max_tokens is not None else 8096,
        "messages":   [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def _gemini(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    from google import genai
    from google.genai import types
    from viko.core.config import get_gemini_key
    client = genai.Client(api_key=get_gemini_key())
    config_kwargs = {}
    if system:
        config_kwargs["system_instruction"] = system
    if max_tokens is not None:
        config_kwargs["max_output_tokens"] = max_tokens
    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
    return client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt, config=config
    ).text
