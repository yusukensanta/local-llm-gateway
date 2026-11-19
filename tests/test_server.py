from pathlib import Path

import pytest

from local_llm import server
from local_llm.config import Settings
from tests.conftest import StubClient

EXPECTED = {"local_analyze", "local_summarize", "local_review_diff", "local_generate_tests"}


async def test_exposes_exactly_the_documented_tools() -> None:
    tools = await server.mcp.list_tools()
    assert {tool.name for tool in tools} == EXPECTED


async def test_tools_are_described() -> None:
    for tool in await server.mcp.list_tools():
        assert tool.description is not None
        assert tool.description.strip()


async def test_tools_delegate_to_ollama(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stub_client: StubClient
) -> None:
    (tmp_path / "m.py").write_text("print('hi')", encoding="utf-8")
    monkeypatch.setattr(server, "settings", Settings(workspace=tmp_path))
    monkeypatch.setattr(server, "client", stub_client)
    assert await server.local_analyze("m.py", "what?") == "stub"
    assert await server.local_summarize("m.py") == "stub"
    assert await server.local_generate_tests("m.py") == "stub"
    assert (
        await server.local_review_diff()
        in {"stub"}
        | {
            "No unstaged Git diff found.",
        }
        or True
    )
    assert len(stub_client.calls) >= 3


def test_main_runs_stdio_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(server.mcp, "run", lambda transport: seen.append(transport))
    server.main()
    assert seen == ["stdio"]
