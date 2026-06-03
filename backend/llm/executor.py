import asyncio
import logging
import random as _random

from config import settings

logger = logging.getLogger(__name__)

# Retryable HTTP status codes: rate limit, server errors, bad gateway, etc.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

_jitter_rng = _random.Random()

# Max concurrent LLM calls — prevents hammering rate limits when many agents fire in parallel.
# Anthropic Tier 1: 50 req/min, 8k tokens/min. Batch of 10 keeps us well under both.
_CONCURRENCY_LIMIT = 10


class LLMExecutor:
    def __init__(self) -> None:
        if settings.llm_provider == "anthropic":
            from llm.anthropic_provider import AnthropicProvider
            self._provider = AnthropicProvider()
        else:
            from llm.ollama_provider import OllamaProvider
            self._provider = OllamaProvider()
        self._sem = asyncio.Semaphore(_CONCURRENCY_LIMIT)
        logger.info("LLM executor initialized with provider: %s", settings.llm_provider)

    async def complete(
        self,
        user_message: str,
        static_system: str = "",
        dynamic_context: str = "",
        api_key: str | None = None,
    ) -> str:
        async with self._sem:
            last_exc: Exception | None = None
            for attempt in range(1, 4):  # 3 attempts: immediate, ~2s, ~4s (with ±25% jitter)
                try:
                    return await self._provider.complete(
                        user_message=user_message,
                        static_system=static_system,
                        dynamic_context=dynamic_context,
                        api_key=api_key,
                    )
                except Exception as exc:
                    last_exc = exc
                    status = getattr(exc, 'status_code', None) or getattr(exc, 'status', None)
                    is_retryable = (
                        status in _RETRYABLE_STATUS_CODES
                        or isinstance(exc, (TimeoutError, ConnectionError))
                    )
                    if not is_retryable or attempt == 3:
                        logger.error("LLM execute failed (attempt %d/3): %s", attempt, exc)
                        raise
                    # Exponential base with ±25% jitter to avoid thundering-herd retries.
                    base_wait = 2 ** attempt  # 4s after attempt 1, 8s after attempt 2
                    wait = base_wait * (0.75 + _jitter_rng.random() * 0.5)
                    logger.warning(
                        "LLM execute retrying (attempt %d/3) after %.1fs: %s", attempt, wait, exc
                    )
                    await asyncio.sleep(wait)
            raise last_exc  # type: ignore[misc]


llm_executor = LLMExecutor()
