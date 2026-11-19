from pathlib import Path

import pytest

from local_llm.config import Settings
from local_llm.security.workspace import WorkspaceError
from local_llm.tools.analyze import analyze
from local_llm.tools.common import OUTPUT_RULES, bounded_text, load_source
from local_llm.tools.generate_tests import generate_tests
from local_llm.tools.summarize import summarize
from tests.conftest import StubClient


async def test_tools_use_workspace_source(tmp_path: Path, stub_client: StubClient) -> None:
    (tmp_path / "example.py").write_text("def add(a, b): return a + b", encoding="utf-8")
    settings = Settings(workspace=tmp_path)
    client = stub_client
    assert await analyze("example.py", "explain", settings, client) == "stub"
    assert await summarize("example.py", settings, client) == "stub"
    assert await generate_tests("example.py", settings, client) == "stub"
    prompts = [prompt for prompt, _ in stub_client.calls]
    assert all("def add(a, b)" in prompt for prompt in prompts)
    assert "explain" in prompts[0]


@pytest.mark.parametrize("tool", ["analyze", "summarize", "generate_tests"])
async def test_tools_reject_paths_outside_workspace(
    tmp_path: Path, stub_client: StubClient, tool: str
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "x.py").write_text("x", encoding="utf-8")
    settings = Settings(workspace=root)
    client = stub_client
    outside = str(tmp_path / "x.py")
    calls = {
        "analyze": analyze(outside, "q", settings, client),
        "summarize": summarize(outside, settings, client),
        "generate_tests": generate_tests(outside, settings, client),
    }
    for name, coro in calls.items():
        if name != tool:
            coro.close()
    with pytest.raises(WorkspaceError):
        await calls[tool]
    assert stub_client.calls == []


def test_load_source_reads_directory(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("A", encoding="utf-8")
    assert "--- FILE: a.py ---" in load_source(".", Settings(workspace=tmp_path))


def test_bounded_text_truncates() -> None:
    assert bounded_text("abc", max_chars=3) == "abc"
    assert bounded_text("abcd", max_chars=3) == "abc\n[TRUNCATED]"


async def test_every_tool_demands_final_answer_only(
    tmp_path: Path, stub_client: StubClient
) -> None:
    """Small reasoning models otherwise narrate their plan and run out of tokens."""
    (tmp_path / "a.py").write_text("x = 1", encoding="utf-8")
    settings = Settings(workspace=tmp_path)
    await analyze("a.py", "q", settings, stub_client)
    await summarize("a.py", settings, stub_client)
    await generate_tests("a.py", settings, stub_client)
    systems = [system for _, system in stub_client.calls]
    assert len(systems) == 3
    assert all(OUTPUT_RULES in system for system in systems)


def test_output_rules_forbid_preamble() -> None:
    lowered = OUTPUT_RULES.lower()
    assert "final answer only" in lowered
    assert "do not" in lowered
