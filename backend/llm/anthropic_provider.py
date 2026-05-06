import logging
import anthropic
from config import settings

logger = logging.getLogger(__name__)


class AnthropicProvider:
    def __init__(self) -> None:
        self._default_client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key or None
        )

    def _get_client(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        if api_key:
            return anthropic.AsyncAnthropic(api_key=api_key)
        return self._default_client

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
        )
        return response.content[0].text
