import logging
import anthropic
from config import settings

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 60.0  # seconds per individual LLM call


class AnthropicProvider:
    def __init__(self) -> None:
        self._default_client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key or None
        )
        # Cache clients keyed by user-supplied API key to avoid creating a new
        # HTTP connection pool per agent per round (100 agents = 100 pools otherwise).
        self._client_cache: dict[str, anthropic.AsyncAnthropic] = {}

    def _get_client(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        if not api_key:
            return self._default_client
        if api_key not in self._client_cache:
            self._client_cache[api_key] = anthropic.AsyncAnthropic(api_key=api_key)
        return self._client_cache[api_key]

    async def complete(
        self,
        user_message: str,
        static_system: str = "",
        dynamic_context: str = "",
        api_key: str | None = None,
    ) -> str:
        client = self._get_client(api_key)

        # Blocks 1-3 (static_system) cached; Blocks 4-5 (dynamic_context) not cached
        system_blocks: list[dict] = []
        if static_system:
            system_blocks.append({
                "type": "text",
                "text": static_system,
                "cache_control": {"type": "ephemeral"},
            })
        if dynamic_context:
            system_blocks.append({
                "type": "text",
                "text": dynamic_context,
            })

        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=system_blocks if system_blocks else anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": user_message}],
            timeout=_REQUEST_TIMEOUT,
        )
        return response.content[0].text
