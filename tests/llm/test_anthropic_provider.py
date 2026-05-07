import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_response(text="hello"):
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    return resp


async def test_complete_returns_text():
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_make_response("hello"))
    with patch("llm.anthropic_provider.anthropic.AsyncAnthropic", return_value=mock_client):
        from llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        result = await provider.complete("test prompt")
    assert result == "hello"


async def test_complete_uses_cache_control_on_static_system():
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_make_response("ok"))
    captured = {}

    async def cap(**kwargs):
        captured.update(kwargs)
        return _make_response("ok")

    mock_client.messages.create = cap
    with patch("llm.anthropic_provider.anthropic.AsyncAnthropic", return_value=mock_client):
        from llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        await provider.complete("msg", static_system="SYSTEM_STATIC")

    system_blocks = captured.get("system", [])
    assert isinstance(system_blocks, list)
    static_block = next((b for b in system_blocks if b.get("text") == "SYSTEM_STATIC"), None)
    assert static_block is not None
    assert static_block.get("cache_control") == {"type": "ephemeral"}


async def test_complete_passes_api_key_to_new_client():
    """When api_key is provided, a new AsyncAnthropic client is created with that key."""
    clients_created = []

    def make_client(api_key=None):
        c = AsyncMock()
        c.messages.create = AsyncMock(return_value=_make_response("ok"))
        clients_created.append(api_key)
        return c

    with patch("llm.anthropic_provider.anthropic.AsyncAnthropic", side_effect=make_client):
        from llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        await provider.complete("msg", api_key="sk-user-key")

    # First call is __init__, second is _get_client with the provided key
    assert "sk-user-key" in clients_created


async def test_dynamic_context_block_has_no_cache_control():
    mock_client = AsyncMock()
    captured = {}

    async def cap(**kwargs):
        captured.update(kwargs)
        return _make_response("ok")

    mock_client.messages.create = cap
    with patch("llm.anthropic_provider.anthropic.AsyncAnthropic", return_value=mock_client):
        from llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider()
        await provider.complete("msg", static_system="STATIC", dynamic_context="DYNAMIC")

    system_blocks = captured.get("system", [])
    dyn_block = next((b for b in system_blocks if b.get("text") == "DYNAMIC"), None)
    assert dyn_block is not None
    assert "cache_control" not in dyn_block
