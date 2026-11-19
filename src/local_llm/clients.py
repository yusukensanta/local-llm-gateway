"""Backend selection."""

from local_llm.config import Settings
from local_llm.ollama_client import ChatClient, OllamaClient
from local_llm.openai_client import OpenAICompatClient


def build_client(settings: Settings) -> ChatClient:
    """Return the chat client for ``settings.backend``."""
    if settings.backend == "openai":
        return OpenAICompatClient(settings)
    return OllamaClient(settings)
