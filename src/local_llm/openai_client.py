"""Client for OpenAI-compatible ``/chat/completions`` servers.

Works with LM Studio, llama.cpp ``llama-server``, vLLM, LiteLLM, Ollama's ``/v1`` endpoint and
similar local servers. The context window cannot be set per request on this API, so
``LOCAL_LLM_CONTEXT_TOKENS`` must match how the server was started; it only sizes the prompt.
"""

from typing import Any

import httpx

from local_llm.config import Settings
from local_llm.errors import BackendError, error_detail


class OpenAICompatError(BackendError):
    """OpenAI-compatible request failed."""


class OpenAICompatClient:
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
            "max_tokens": self.settings.max_output_tokens,
        }
        headers: dict[str, str] = {}
        if self.settings.api_key is not None:
            headers["Authorization"] = f"Bearer {self.settings.api_key.get_secret_value()}"
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.openai_base_url.rstrip("/"),
                timeout=self.settings.request_timeout,
                headers=headers,
            ) as client:
                response = await client.post("/chat/completions", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            detail = error_detail(exc)
            raise OpenAICompatError(f"OpenAI-compatible request failed: {detail}") from exc
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenAICompatError("OpenAI-compatible server returned an unexpected body") from exc
        if not isinstance(content, str) or not content.strip():
            raise OpenAICompatError("OpenAI-compatible server returned an empty message")
        return content
