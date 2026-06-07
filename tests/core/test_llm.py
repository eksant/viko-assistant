import pytest
from unittest.mock import patch, MagicMock
import importlib


def _make_mock_anthropic_client(response_text: str):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


def test_generate_text_passes_max_tokens_to_claude():
    """generate_text(max_tokens=5) must pass max_tokens=5 to Claude."""
    mock_client = _make_mock_anthropic_client("YES")
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            from viko.self_engineer import llm
            importlib.reload(llm)
            llm.generate_text("Say YES or NO", max_tokens=5)
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 5, (
                f"Expected max_tokens=5, got {call_kwargs.get('max_tokens')}"
            )


def test_generate_text_default_max_tokens_is_8096():
    """generate_text() without max_tokens uses 8096."""
    mock_client = _make_mock_anthropic_client("hello")
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("anthropic.Anthropic", return_value=mock_client):
            from viko.self_engineer import llm
            importlib.reload(llm)
            llm.generate_text("hello")
            call_kwargs = mock_client.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 8096
