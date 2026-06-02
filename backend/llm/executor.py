import asyncio
import logging
from config import settings

logger = logging.getLogger(__name__)

# Retryable HTTP status codes: rate limit, server errors, bad gateway, etc.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMExecutor:
    def __init__(self) -> None:
        if settings.llm_provider == "anthropic":
            from llm.anthropic_provider import AnthropicProvider
            self._provider = AnthropicProvider()
        else:
            from llm.ollama_provider import OllamaProvider
            self._provider = OllamaProvider()
        logger.info("LLM executor initialized with provider: %s", settings.llm_provider)

    async def complete(
        self,
        user_message: str,
        static_system: str = "",
        dynamic_context: str = "",
        api_key: str | None = None,
    ) -> str:
        last_exc: Exception | None = None
        for attempt in range(1, 4):  # 3 attempts with exponential backoff: 0s, 2s, 4s
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
                wait = 2 ** (attempt - 1)  # 1s after attempt 1, 2s after attempt 2
                logger.warning(
                    "LLM execute retrying (attempt %d/3) after %ds: %s", attempt, wait, exc
                )
                await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]


llm_executor = LLMExecutor()
