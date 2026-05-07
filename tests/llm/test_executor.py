import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


async def test_executor_retries_once_on_failure():
    call_count = 0

    async def flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("timeout")
        return "recovered"

    mock_provider = MagicMock()
    mock_provider.complete = flaky

    with patch("llm.executor.LLMExecutor.__init__", return_value=None):
        from llm.executor import LLMExecutor
        executor = LLMExecutor.__new__(LLMExecutor)
        executor._provider = mock_provider
        result = await executor.complete("test")

    assert result == "recovered"
    assert call_count == 2


async def test_executor_raises_after_two_failures():
    async def always_fail(*args, **kwargs):
        raise RuntimeError("broken")

    mock_provider = MagicMock()
    mock_provider.complete = always_fail

    with patch("llm.executor.LLMExecutor.__init__", return_value=None):
        from llm.executor import LLMExecutor
        executor = LLMExecutor.__new__(LLMExecutor)
        executor._provider = mock_provider
        with pytest.raises(RuntimeError):
            await executor.complete("test")


async def test_executor_passes_api_key():
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value="ok")

    with patch("llm.executor.LLMExecutor.__init__", return_value=None):
        from llm.executor import LLMExecutor
        executor = LLMExecutor.__new__(LLMExecutor)
        executor._provider = mock_provider
        await executor.complete("msg", api_key="sk-test")

    call_kwargs = mock_provider.complete.call_args.kwargs
    assert call_kwargs.get("api_key") == "sk-test"
