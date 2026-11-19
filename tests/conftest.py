"""Shared test fixtures."""

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from local_llm.config import Settings

Handler = Callable[[httpx.Request], httpx.Response]


class StubClient:
    """Stand-in for OllamaClient that records prompts."""

    def __init__(self, reply: str = "stub") -> None:
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    async def chat(self, prompt: str, *, system: str, model: str | None = None) -> str:
        self.calls.append((prompt, system))
        return self.reply


@pytest.fixture
def stub_client() -> StubClient:
    return StubClient()


@pytest.fixture
def mock_ollama(monkeypatch: pytest.MonkeyPatch) -> Callable[[Handler], None]:
    """Route every ``httpx.AsyncClient`` through a ``MockTransport`` handler."""
    original = httpx.AsyncClient

    def install(handler: Handler) -> None:
        class MockClient(original):
            def __init__(self, **kwargs: object) -> None:
                kwargs["transport"] = httpx.MockTransport(handler)
                super().__init__(**kwargs)  # ty: ignore[invalid-argument-type]

        monkeypatch.setattr(httpx, "AsyncClient", MockClient)

    return install


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent the developer's environment from leaking into Settings."""
    for name in (
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "LOCAL_LLM_WORKSPACE",
        "LOCAL_LLM_MAX_FILE_BYTES",
        "LOCAL_LLM_MAX_FILES",
        "LOCAL_LLM_REQUEST_TIMEOUT",
        "LOCAL_LLM_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(workspace=tmp_path)
