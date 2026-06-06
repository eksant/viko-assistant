import os


def generate_text(prompt: str) -> str:
    """Route to Claude if ANTHROPIC_API_KEY is set, otherwise use Gemini."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _claude(prompt)
    return _gemini(prompt)


def _claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _gemini(prompt: str) -> str:
    from google import genai
    from viko.config import get_gemini_key
    client = genai.Client(api_key=get_gemini_key())
    return client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt
    ).text
