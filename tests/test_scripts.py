"""Behavioural tests for the POSIX shell scripts, using fake executables on PATH."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REAL_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
SCRIPTS = REAL_SCRIPTS
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None or os.name == "nt", reason="requires bash")


def make_fake(directory: Path, name: str, body: str = "") -> Path:
    path = directory / name
    path.write_text(f'#!/usr/bin/env bash\necho "{name} $*" >> "$FAKE_LOG"\n{body}\n')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def sandbox(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    log.touch()
    # Copy the scripts into a fake repo root so tests never depend on a real .venv.
    shutil.copytree(REAL_SCRIPTS, tmp_path / "repo" / "scripts")
    # Keep system tools (dirname, cd, ...) but nothing that could be a real uv/ollama/claude.
    minimal = os.pathsep.join(["/usr/bin", "/bin"])
    env = {"PATH": f"{bin_dir}{os.pathsep}{minimal}", "FAKE_LOG": str(log), "HOME": str(tmp_path)}
    return bin_dir, log, env


def run(script: str, *args: str, env: dict[str, str], cwd: Path | None = None):
    repo_scripts = Path(env["HOME"]) / "repo" / "scripts"
    return subprocess.run(
        [str(BASH), str(repo_scripts / script), *args],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("script", sorted(p.name for p in SCRIPTS.glob("*.sh")))
def test_scripts_have_valid_syntax(script: str) -> None:
    result = subprocess.run(
        [str(BASH), "-n", str(SCRIPTS / script)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_scripts_pass_shellcheck() -> None:
    scripts = sorted(str(p) for p in SCRIPTS.glob("*.sh"))
    result = subprocess.run(
        [str(shutil.which("shellcheck")), *scripts], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout


def test_setup_requires_uv(sandbox: tuple[Path, Path, dict[str, str]]) -> None:
    _, _, env = sandbox
    result = run("setup.sh", env=env)
    assert result.returncode == 1
    assert "uv is required" in result.stderr


def test_setup_runs_locked_sync_for_python_314(sandbox: tuple[Path, Path, dict[str, str]]) -> None:
    bin_dir, log, env = sandbox
    make_fake(bin_dir, "uv")
    result = run("setup.sh", "--no-dev", env=env)
    assert result.returncode == 0, result.stderr
    assert log.read_text().strip() == "uv sync --locked --python 3.14 --no-dev"


def test_install_models_default_and_explicit(sandbox: tuple[Path, Path, dict[str, str]]) -> None:
    bin_dir, log, env = sandbox
    make_fake(bin_dir, "ollama")
    assert run("install-models.sh", env=env).returncode == 0
    assert run("install-models.sh", "a:1", "b:2", env=env).returncode == 0
    assert log.read_text().splitlines() == [
        "ollama pull qwen2.5-coder:7b",
        "ollama pull a:1",
        "ollama pull b:2",
    ]


def test_install_models_honours_env_and_fails_without_ollama(
    sandbox: tuple[Path, Path, dict[str, str]],
) -> None:
    bin_dir, log, env = sandbox
    result = run("install-models.sh", env=env)
    assert result.returncode == 1
    assert "Install Ollama first" in result.stderr
    make_fake(bin_dir, "ollama")
    run("install-models.sh", env={**env, "OLLAMA_MODEL": "custom:1"})
    assert log.read_text().strip() == "ollama pull custom:1"


def test_install_models_propagates_pull_failure(
    sandbox: tuple[Path, Path, dict[str, str]],
) -> None:
    bin_dir, _, env = sandbox
    make_fake(bin_dir, "ollama", "exit 3")
    assert run("install-models.sh", env=env).returncode == 3


def test_register_requires_setup(
    sandbox: tuple[Path, Path, dict[str, str]], tmp_path: Path
) -> None:
    bin_dir, _, env = sandbox
    make_fake(bin_dir, "claude")
    result = run("register-mcp.sh", str(tmp_path), env=env)
    assert result.returncode == 1
    assert "setup.sh first" in result.stderr


def test_register_is_user_scoped_and_idempotent(
    sandbox: tuple[Path, Path, dict[str, str]], tmp_path: Path
) -> None:
    bin_dir, log, env = sandbox
    make_fake(bin_dir, "claude")
    fake_python = tmp_path / "repo" / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("#!/usr/bin/env bash\n")
    fake_python.chmod(0o755)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = run("register-mcp.sh", str(workspace), env=env)
    assert result.returncode == 0, result.stderr
    first, second = log.read_text().splitlines()
    assert first == "claude mcp remove local-llm --scope user"
    assert second.startswith("claude mcp add local-llm --scope user --env LOCAL_LLM_WORKSPACE=")
    assert str(workspace.resolve()) in second
    assert second.endswith("-m local_llm.server")


def test_register_rejects_missing_workspace(
    sandbox: tuple[Path, Path, dict[str, str]], tmp_path: Path
) -> None:
    bin_dir, _, env = sandbox
    make_fake(bin_dir, "claude")
    fake_python = tmp_path / "repo" / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("#!/usr/bin/env bash\n")
    fake_python.chmod(0o755)
    result = run("register-mcp.sh", str(tmp_path / "nope"), env=env)
    assert result.returncode == 1
    assert "not a directory" in result.stderr


def test_start_requires_setup(sandbox: tuple[Path, Path, dict[str, str]]) -> None:
    _, _, env = sandbox
    result = run("start.sh", env=env)
    assert result.returncode == 1
    assert "setup.sh first" in result.stderr
