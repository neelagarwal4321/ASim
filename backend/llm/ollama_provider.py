import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)


class OllamaProvider:
    async def complete(
        self,
        user_message: str,
        static_system: str = "",
        dynamic_context: str = "",
        api_key: str | None = None,
    ) -> str:
        system = "\n\n".join(filter(None, [static_system, dynamic_context]))
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": user_message,
                    "system": system,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]
