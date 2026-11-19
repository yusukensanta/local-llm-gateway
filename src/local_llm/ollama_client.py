"""Asynchronous Ollama API client."""
from typing import Any

import httpx

from local_llm.config import Settings


class OllamaError(RuntimeError):
    """Ollama request failed."""


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(self, prompt: str, *, system: str, model: str | None = None) -> str:
        payload: dict[str, Any] = {
            "model": model or self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"num_predict": self.settings.max_output_tokens},
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.ollama_base_url.rstrip("/"),
                timeout=self.settings.request_timeout,
            ) as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        content = response.json().get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama returned an empty or invalid message")
        return content
