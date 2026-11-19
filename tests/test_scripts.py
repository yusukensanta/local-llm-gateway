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
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{minimal}",
        "FAKE_LOG": str(log),
        "HOME": str(tmp_path),
        # Unreachable on purpose: tests must never talk to a real local Ollama.
        "OLLAMA_BASE_URL": "http://127.0.0.1:1",
    }
    # Default curl fails like an unreachable server (no real network, even on WSL where
    # closed ports hang). Individual tests overwrite it with a scripted fake.
    make_fake(bin_dir, "curl", "exit 7")
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
    assert "Could not reach Ollama" in result.stderr
    make_fake(bin_dir, "ollama")
    run("install-models.sh", env={**env, "OLLAMA_MODEL": "custom:1"})
    assert log.read_text().splitlines()[-1] == "ollama pull custom:1"


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


def fake_venv_python(root: Path) -> None:
    fake_python = root / "repo" / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("#!/usr/bin/env bash\n")
    fake_python.chmod(0o755)


def test_register_passes_model_when_given(
    sandbox: tuple[Path, Path, dict[str, str]], tmp_path: Path
) -> None:
    bin_dir, log, env = sandbox
    make_fake(bin_dir, "claude")
    fake_venv_python(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = run("register-mcp.sh", "--model", "qwen3:4b", str(workspace), env=env)
    assert result.returncode == 0, result.stderr
    add = log.read_text().splitlines()[1]
    assert "--env OLLAMA_MODEL=qwen3:4b" in add
    assert f"--env LOCAL_LLM_WORKSPACE={workspace.resolve()}" in add


def test_register_omits_model_by_default(
    sandbox: tuple[Path, Path, dict[str, str]], tmp_path: Path
) -> None:
    bin_dir, log, env = sandbox
    make_fake(bin_dir, "claude")
    fake_venv_python(tmp_path)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    assert run("register-mcp.sh", str(workspace), env=env).returncode == 0
    assert "OLLAMA_MODEL" not in log.read_text()


def test_register_rejects_unknown_option_and_missing_model_value(
    sandbox: tuple[Path, Path, dict[str, str]], tmp_path: Path
) -> None:
    bin_dir, _, env = sandbox
    make_fake(bin_dir, "claude")
    fake_venv_python(tmp_path)
    assert run("register-mcp.sh", "--bogus", env=env).returncode == 2
    assert run("register-mcp.sh", "--model", env=env).returncode == 2


def test_install_models_falls_back_to_api_without_cli(
    sandbox: tuple[Path, Path, dict[str, str]],
) -> None:
    bin_dir, log, env = sandbox
    make_fake(bin_dir, "curl", 'echo \'{"status":"success"}\'')
    result = run(
        "install-models.sh", "qwen3:4b", env={**env, "OLLAMA_BASE_URL": "http://h.test:11434"}
    )
    assert result.returncode == 0, result.stderr
    call = log.read_text()
    assert "http://h.test:11434/api/pull" in call
    assert '"model":"qwen3:4b"' in call


def test_install_models_api_fallback_reports_ollama_error(
    sandbox: tuple[Path, Path, dict[str, str]],
) -> None:
    bin_dir, _, env = sandbox
    make_fake(bin_dir, "curl", 'echo \'{"error":"pull model manifest: file does not exist"}\'')
    result = run("install-models.sh", "nope:1", env=env)
    assert result.returncode == 1
    assert "file does not exist" in result.stderr
