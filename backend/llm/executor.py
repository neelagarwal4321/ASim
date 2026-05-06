import logging
from config import settings

logger = logging.getLogger(__name__)


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
        for attempt in range(1, 3):
            try:
                return await self._provider.complete(
                    user_message=user_message,
                    static_system=static_system,
                    dynamic_context=dynamic_context,
                    api_key=api_key,
                )
            except Exception as exc:
                if attempt == 1:
                    logger.warning("LLM call attempt 1 failed: %s, retrying...", exc)
                else:
                    logger.error("LLM call attempt 2 failed: %s, raising", exc)
                    raise


llm_executor = LLMExecutor()
