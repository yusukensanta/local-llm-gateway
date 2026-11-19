import json
from collections.abc import Callable

import httpx
import pytest

from local_llm.config import Settings
from local_llm.ollama_client import OllamaClient, OllamaError

Install = Callable[[Callable[[httpx.Request], httpx.Response]], None]


async def test_chat_payload_and_response(mock_ollama: Install) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "ok"}})

    mock_ollama(handler)
    settings = Settings(
        ollama_base_url="http://unit.test/", allow_remote=True, max_output_tokens=77
    )
    assert await OllamaClient(settings).chat("hello", system="sys") == "ok"
    assert seen["url"] == "http://unit.test/api/chat"
    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["model"] == "qwen2.5-coder:7b"
    assert payload["options"] == {"num_predict": 77, "num_ctx": 8192}
    assert payload["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]


async def test_chat_model_override(mock_ollama: Install) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["model"] = json.loads(request.content)["model"]
        return httpx.Response(200, json={"message": {"content": "ok"}})

    mock_ollama(handler)
    await OllamaClient(Settings()).chat("p", system="s", model="other")
    assert seen["model"] == "other"


async def test_chat_raises_for_http_error(mock_ollama: Install) -> None:
    mock_ollama(lambda _request: httpx.Response(503, text="offline"))
    with pytest.raises(OllamaError, match="request failed"):
        await OllamaClient(Settings()).chat("hello", system="test")


async def test_chat_raises_for_connection_error(mock_ollama: Install) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    mock_ollama(handler)
    with pytest.raises(OllamaError, match="refused"):
        await OllamaClient(Settings()).chat("hello", system="test")


@pytest.mark.parametrize(
    "body",
    [{}, {"message": {}}, {"message": {"content": "   "}}, {"message": {"content": 5}}],
)
async def test_chat_rejects_empty_or_invalid_message(
    mock_ollama: Install, body: dict[str, object]
) -> None:
    mock_ollama(lambda _request: httpx.Response(200, json=body))
    with pytest.raises(OllamaError, match="empty or invalid"):
        await OllamaClient(Settings()).chat("hello", system="test")


async def test_chat_timeout_error_names_exception_type(mock_ollama: Install) -> None:
    # httpx timeout exceptions stringify to "", so the type name must appear in the message.
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("", request=request)

    mock_ollama(handler)
    with pytest.raises(OllamaError, match=r"request failed: ReadTimeout"):
        await OllamaClient(Settings()).chat("hello", system="test")


async def test_chat_error_includes_type_and_detail(mock_ollama: Install) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    mock_ollama(handler)
    with pytest.raises(OllamaError, match=r"request failed: ConnectError: refused"):
        await OllamaClient(Settings()).chat("hello", system="test")


async def test_chat_sends_think_when_enabled(mock_ollama: Install) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["think"] = json.loads(request.content)["think"]
        return httpx.Response(200, json={"message": {"content": "ok"}})

    mock_ollama(handler)
    await OllamaClient(Settings(think=True)).chat("p", system="s")
    assert seen["think"] is True


async def test_http_error_includes_server_reason_and_context_hint(mock_ollama: Install) -> None:
    reason = '{"error":"request (37195 tokens) exceeds the available context size (4096 tokens)"}'
    mock_ollama(lambda _request: httpx.Response(400, text=reason))
    with pytest.raises(OllamaError) as info:
        await OllamaClient(Settings()).chat("p", system="s")
    message = str(info.value)
    assert "exceeds the available context size" in message
    assert "LOCAL_LLM_CONTEXT_TOKENS" in message


async def test_http_error_without_body_has_no_server_suffix(mock_ollama: Install) -> None:
    mock_ollama(lambda _request: httpx.Response(500))
    with pytest.raises(OllamaError) as info:
        await OllamaClient(Settings()).chat("p", system="s")
    assert "server said" not in str(info.value)
