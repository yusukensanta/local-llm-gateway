import json
from collections.abc import Callable

import httpx
import pytest

from local_llm.clients import build_client
from local_llm.config import Settings
from local_llm.errors import BackendError
from local_llm.ollama_client import OllamaClient
from local_llm.openai_client import OpenAICompatClient, OpenAICompatError

Install = Callable[[Callable[[httpx.Request], httpx.Response]], None]
OK = {"choices": [{"message": {"content": "ok"}}]}


async def test_payload_url_and_response(mock_ollama: Install) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json=OK)

    mock_ollama(handler)
    settings = Settings(backend="openai", max_output_tokens=77)
    assert await OpenAICompatClient(settings).chat("hello", system="sys") == "ok"
    assert seen["url"] == "http://localhost:1234/v1/chat/completions"
    assert seen["auth"] is None
    assert seen["payload"] == {
        "model": "qwen2.5-coder:7b",
        "messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ],
        "stream": False,
        "max_tokens": 77,
    }


async def test_api_key_is_sent_as_bearer_header(mock_ollama: Install) -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json=OK)

    mock_ollama(handler)
    settings = Settings(backend="openai", api_key="sk-secret")
    await OpenAICompatClient(settings).chat("p", system="s")
    assert seen["auth"] == "Bearer sk-secret"


async def test_model_override_and_trailing_slash(mock_ollama: Install) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["model"] = json.loads(request.content)["model"]
        return httpx.Response(200, json=OK)

    mock_ollama(handler)
    settings = Settings(openai_base_url="http://localhost:8080/v1/")
    await OpenAICompatClient(settings).chat("p", system="s", model="other")
    assert seen == {"url": "http://localhost:8080/v1/chat/completions", "model": "other"}


async def test_http_error_does_not_leak_api_key(mock_ollama: Install) -> None:
    mock_ollama(lambda _request: httpx.Response(401, text="nope"))
    settings = Settings(api_key="sk-secret")
    with pytest.raises(OpenAICompatError, match="request failed") as info:
        await OpenAICompatClient(settings).chat("p", system="s")
    assert "sk-secret" not in str(info.value)


async def test_connection_error_names_the_type(mock_ollama: Install) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("", request=request)

    mock_ollama(handler)
    with pytest.raises(OpenAICompatError, match="ReadTimeout"):
        await OpenAICompatClient(Settings()).chat("p", system="s")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": "   "}}]},
        {"choices": [{"message": {"content": 5}}]},
        ["not", "a", "dict"],
    ],
)
async def test_unexpected_bodies_are_rejected(mock_ollama: Install, body: object) -> None:
    mock_ollama(lambda _request: httpx.Response(200, json=body))
    with pytest.raises(BackendError):
        await OpenAICompatClient(Settings()).chat("p", system="s")


async def test_non_json_body_is_rejected(mock_ollama: Install) -> None:
    mock_ollama(lambda _request: httpx.Response(200, text="<html>"))
    with pytest.raises(OpenAICompatError, match="unexpected body"):
        await OpenAICompatClient(Settings()).chat("p", system="s")


def test_factory_selects_backend() -> None:
    assert isinstance(build_client(Settings()), OllamaClient)
    assert isinstance(build_client(Settings(backend="openai")), OpenAICompatClient)


def test_ollama_error_is_a_backend_error() -> None:
    from local_llm.ollama_client import OllamaError

    assert issubclass(OllamaError, BackendError)


async def test_http_error_includes_server_reason(mock_ollama: Install) -> None:
    mock_ollama(lambda _request: httpx.Response(400, text="context length exceeded"))
    with pytest.raises(OpenAICompatError) as info:
        await OpenAICompatClient(Settings()).chat("p", system="s")
    assert "server said: context length exceeded" in str(info.value)
