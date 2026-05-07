import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from llm.ollama_provider import OllamaProvider


def _mock_http(text):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"response": text}
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


async def test_complete_returns_text():
    with patch("llm.ollama_provider.httpx.AsyncClient", return_value=_mock_http("hello")):
        result = await OllamaProvider().complete("prompt")
    assert result == "hello"


async def test_complete_merges_system_parts():
    captured = {}
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"response": "ok"}
    client = AsyncMock()

    async def cap(url, json=None, **kw):
        captured["json"] = json
        return resp

    client.post = cap
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    with patch("llm.ollama_provider.httpx.AsyncClient", return_value=client):
        await OllamaProvider().complete("msg", static_system="STATIC", dynamic_context="DYN")
    assert "STATIC" in captured["json"]["system"]
    assert "DYN" in captured["json"]["system"]


async def test_complete_raises_on_http_error():
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("404")
    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    with patch("llm.ollama_provider.httpx.AsyncClient", return_value=client):
        with pytest.raises(Exception, match="404"):
            await OllamaProvider().complete("hi")
