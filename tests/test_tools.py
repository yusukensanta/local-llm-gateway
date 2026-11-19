from pathlib import Path

import pytest

from local_llm.config import Settings
from local_llm.tools.analyze import analyze
from local_llm.tools.generate_tests import generate_tests
from local_llm.tools.summarize import summarize


class StubClient:
    async def chat(self, prompt: str, *, system: str, model: str | None = None) -> str:
        assert prompt and system
        return "stub"


@pytest.mark.asyncio
async def test_tools_use_workspace_source(tmp_path: Path) -> None:
    (tmp_path / "example.py").write_text("def add(a, b): return a + b", encoding="utf-8")
    settings = Settings(workspace=tmp_path)
    client = StubClient()
    assert await analyze("example.py", "explain", settings, client) == "stub"  # type: ignore[arg-type]
    assert await summarize("example.py", settings, client) == "stub"  # type: ignore[arg-type]
    assert await generate_tests("example.py", settings, client) == "stub"  # type: ignore[arg-type]
