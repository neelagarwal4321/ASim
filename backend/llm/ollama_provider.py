import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT = 120.0  # seconds


class OllamaProvider:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def complete(self, system_blocks: list[dict], user_message: str, api_key: str | None = None) -> str:
        # api_key unused for Ollama — local provider
        system_text = "\n\n".join(b.get("text", "") for b in system_blocks if b.get("text"))

        payload = {
            "model": self.model,
            "prompt": user_message,
            "system": system_text,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response")
                if not text:
                    raise ValueError(f"Ollama returned empty response: {data}")
                return text
        except httpx.TimeoutException:
            raise TimeoutError(f"Ollama request timed out after {OLLAMA_TIMEOUT}s")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama HTTP error {e.response.status_code}: {e.response.text[:200]}")
