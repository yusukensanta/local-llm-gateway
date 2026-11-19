import shutil
import subprocess
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


@pytest.fixture
def repo_with_unstaged_change(tmp_path: Path) -> Path:
    git = str(shutil.which("git"))
    source = tmp_path / "m.py"
    source.write_text("print('hi')\n", encoding="utf-8")
    # Stage the file, then edit it: `git diff` (unstaged) is non-empty without needing a commit.
    subprocess.run([git, "-C", str(tmp_path), "init", "-q"], check=True, capture_output=True)
    subprocess.run([git, "-C", str(tmp_path), "add", "m.py"], check=True, capture_output=True)
    source.write_text("print('changed')\n", encoding="utf-8")
    return tmp_path


@pytest.mark.skipif(shutil.which("git") is None, reason="git is required")
async def test_tools_delegate_to_client(
    monkeypatch: pytest.MonkeyPatch, repo_with_unstaged_change: Path, stub_client: StubClient
) -> None:
    tmp_path = repo_with_unstaged_change
    monkeypatch.setattr(server, "settings", Settings(workspace=tmp_path))
    monkeypatch.setattr(server, "client", stub_client)

    assert await server.local_analyze("m.py", "what?") == "stub"
    assert await server.local_summarize("m.py") == "stub"
    assert await server.local_generate_tests("m.py") == "stub"
    assert await server.local_review_diff() == "stub"

    assert len(stub_client.calls) == 4
    assert "what?" in stub_client.calls[0][0]
    assert all("print(" in prompt for prompt, _ in stub_client.calls)
    assert "print('changed')" in stub_client.calls[3][0]


def test_main_runs_stdio_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(server.mcp, "run", lambda transport: seen.append(transport))
    server.main()
    assert seen == ["stdio"]
