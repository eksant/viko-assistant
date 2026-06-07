import pytest
from unittest.mock import patch


def test_should_extract_memory_returns_false_on_none_result():
    """should_extract_memory() must return False (not crash) when generate_text returns None."""
    from viko.core.memory import should_extract_memory
    with patch("viko.self_engineer.llm.generate_text", return_value=None):
        result = should_extract_memory("hello", "hi there")
    assert result is False


def test_should_extract_memory_returns_true_on_yes():
    """should_extract_memory() returns True when generate_text returns 'YES'."""
    from viko.core.memory import should_extract_memory
    with patch("viko.self_engineer.llm.generate_text", return_value="YES"):
        result = should_extract_memory("my name is Ali", "nice to meet you Ali")
    assert result is True


def test_extract_memory_returns_empty_on_none_result():
    """extract_memory() must return {} (not crash) when generate_text returns None."""
    from viko.core.memory import extract_memory
    with patch("viko.self_engineer.llm.generate_text", return_value=None):
        result = extract_memory("hello", "hi there")
    assert result == {}


def test_extract_memory_parses_valid_json():
    """extract_memory() returns parsed dict on valid JSON response."""
    from viko.core.memory import extract_memory
    json_str = '{"identity": {"name": {"value": "Ali"}}}'
    with patch("viko.self_engineer.llm.generate_text", return_value=json_str):
        result = extract_memory("my name is Ali", "nice to meet you")
    assert result == {"identity": {"name": {"value": "Ali"}}}
