import shutil
import subprocess
from pathlib import Path

import pytest

from local_llm.config import Settings
from local_llm.tools import review
from local_llm.tools.common import OUTPUT_RULES
from local_llm.tools.review import review_diff
from tests.conftest import StubClient

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


def git(root: Path, *args: str) -> None:
    subprocess.run(
        [str(shutil.which("git")), "-C", str(root), *args], check=True, capture_output=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.test")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=1\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "init")
    return tmp_path


async def test_no_diff(repo: Path, stub_client: StubClient) -> None:
    result = await review_diff(Settings(workspace=repo), stub_client)
    assert result == "No unstaged Git diff found."
    assert stub_client.calls == []


async def test_reviews_unstaged_changes(repo: Path, stub_client: StubClient) -> None:
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    assert await review_diff(Settings(workspace=repo), stub_client) == "stub"
    prompt = stub_client.calls[0][0]
    assert "+x = 2" in prompt


async def test_staged_changes_are_not_reviewed(repo: Path, stub_client: StubClient) -> None:
    (repo / "a.py").write_text("x = 3\n", encoding="utf-8")
    git(repo, "add", "a.py")
    result = await review_diff(Settings(workspace=repo), stub_client)
    assert result == "No unstaged Git diff found."


async def test_secret_files_are_excluded_from_diff(repo: Path, stub_client: StubClient) -> None:
    (repo / ".env").write_text("TOKEN=SUPERSECRET\n", encoding="utf-8")
    assert await review_diff(Settings(workspace=repo), stub_client) == (
        "No unstaged Git diff found."
    )
    (repo / "a.py").write_text("x = 9\n", encoding="utf-8")
    await review_diff(Settings(workspace=repo), stub_client)
    assert "SUPERSECRET" not in stub_client.calls[0][0]


async def test_not_a_git_repository(tmp_path: Path, stub_client: StubClient) -> None:
    # Isolate from any enclosing repository on the machine.
    result = await review_diff(Settings(workspace=tmp_path), stub_client)
    assert result.startswith("git diff failed") or result == "No unstaged Git diff found."


async def test_git_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stub_client: StubClient
) -> None:
    monkeypatch.setattr(review.shutil, "which", lambda _name: None)
    result = await review_diff(Settings(workspace=tmp_path), stub_client)
    assert result.startswith("Unable to run git diff")


async def test_git_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stub_client: StubClient
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr(review.subprocess, "run", boom)
    result = await review_diff(Settings(workspace=tmp_path), stub_client)
    assert result.startswith("Unable to run git diff")


async def test_review_prompt_demands_final_answer_only(repo: Path, stub_client: StubClient) -> None:
    (repo / "a.py").write_text("x = 5\n", encoding="utf-8")
    await review_diff(Settings(workspace=repo), stub_client)
    assert OUTPUT_RULES in stub_client.calls[0][1]
