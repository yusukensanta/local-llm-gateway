import json

import httpx
import pytest

from local_llm.config import Settings
from local_llm.ollama_client import OllamaClient, OllamaError


@pytest.mark.asyncio
async def test_chat_payload_and_response(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "ok"}})

    original = httpx.AsyncClient

    class MockClient(original):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", MockClient)
    result = await OllamaClient(Settings(ollama_base_url="http://unit.test")).chat(
        "hello", system="test"
    )
    assert result == "ok"
    assert seen["path"] == "/api/chat"
    assert isinstance(seen["payload"], dict)
    assert seen["payload"]["stream"] is False  # type: ignore[index]


@pytest.mark.asyncio
async def test_chat_raises_for_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="offline")

    original = httpx.AsyncClient

    class MockClient(original):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", MockClient)
    with pytest.raises(OllamaError):
        await OllamaClient(Settings()).chat("hello", system="test")
