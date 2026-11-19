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


async def test_diff_excludes_every_sensitive_pattern(repo: Path, stub_client: StubClient) -> None:
    from local_llm.security.workspace import is_sensitive

    names = [
        "x.pfx",
        "id_ecdsa",
        ".npmrc",
        "credentials.json",
        "prod.env",
        ".SSH/config",
        "a.tfvars",
    ]
    for name in names:
        assert is_sensitive(Path(name)), name
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("v1\n", encoding="utf-8")
    git(repo, "add", "-A", "-f")
    git(repo, "commit", "-qm", "secrets")
    for name in names:
        (repo / name).write_text("LEAKED\n", encoding="utf-8")
    (repo / "a.py").write_text("x = 7\n", encoding="utf-8")
    await review_diff(Settings(workspace=repo), stub_client)
    prompt = stub_client.calls[0][0]
    assert "LEAKED" not in prompt
    assert "+x = 7" in prompt


async def test_review_prompt_fences_diff(repo: Path, stub_client: StubClient) -> None:
    from local_llm.tools.common import INJECTION_GUARD, UNTRUSTED_TAG

    (repo / "a.py").write_text("x = 8\n", encoding="utf-8")
    await review_diff(Settings(workspace=repo), stub_client)
    prompt, system = stub_client.calls[0]
    assert f"<{UNTRUSTED_TAG}>" in prompt
    assert INJECTION_GUARD in system


async def test_git_failure_does_not_leak_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stub_client: StubClient
) -> None:
    def fail(*_a: object, **_k: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 128, "", f"fatal: not a repo: {tmp_path}/secret")

    monkeypatch.setattr(review.subprocess, "run", fail)
    result = await review_diff(Settings(workspace=tmp_path), stub_client)
    assert result.startswith("git diff failed (exit code 128")
    assert str(tmp_path) not in result


async def test_os_error_does_not_leak_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stub_client: StubClient
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise OSError(f"cannot exec in {tmp_path}/private")

    monkeypatch.setattr(review.subprocess, "run", boom)
    result = await review_diff(Settings(workspace=tmp_path), stub_client)
    assert result.startswith("Unable to run git diff")
    assert str(tmp_path) not in result


def test_git_diff_disables_textconv_and_ext_diff() -> None:
    captured: list[list[str]] = []

    def fake_run(argv: list[str], **_k: object) -> subprocess.CompletedProcess[str]:
        captured.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    original = review.subprocess.run
    review.subprocess.run = fake_run  # ty: ignore[invalid-assignment]
    try:
        review._run_git_diff(Settings(workspace=Path.cwd()))
    finally:
        review.subprocess.run = original
    assert "--no-textconv" in captured[0]
    assert "--no-ext-diff" in captured[0]
