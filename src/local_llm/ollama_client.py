"""Asynchronous Ollama API client."""

from typing import Any, Protocol

import httpx

from local_llm.config import Settings
from local_llm.errors import BackendError, error_detail


class OllamaError(BackendError):
    """Ollama request failed."""


class ChatClient(Protocol):
    """Minimal interface the tools need; lets tests inject a stub."""

    async def chat(self, prompt: str, *, system: str, model: str | None = None) -> str: ...


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(self, prompt: str, *, system: str, model: str | None = None) -> str:
        payload: dict[str, Any] = {
            "model": model or self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            # Reasoning models (e.g. qwen3) otherwise spend num_predict on hidden thinking.
            "think": self.settings.think,
            "options": {
                "num_predict": self.settings.max_output_tokens,
                # Without this Ollama silently uses its VRAM-dependent default (4k on <24 GiB).
                "num_ctx": self.settings.context_tokens,
            },
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.ollama_base_url.rstrip("/"),
                timeout=self.settings.request_timeout,
            ) as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            detail = error_detail(exc)
            raise OllamaError(f"Ollama request failed: {detail}") from exc
        content = response.json().get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaError("Ollama returned an empty or invalid message")
        return content
