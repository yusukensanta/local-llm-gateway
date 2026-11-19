from pathlib import Path

import pytest
from pydantic import ValidationError

from local_llm.config import Settings, get_settings


def test_defaults() -> None:
    s = Settings()
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.ollama_model == "qwen2.5-coder:7b"
    assert s.max_files == 20
    assert s.workspace == Path.cwd()


def test_environment_aliases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example.test:1")
    monkeypatch.setenv("OLLAMA_MODEL", "tiny")
    monkeypatch.setenv("LOCAL_LLM_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("LOCAL_LLM_MAX_FILES", "3")
    s = Settings()
    assert (s.ollama_base_url, s.ollama_model, s.max_files) == ("http://example.test:1", "tiny", 3)
    assert s.resolved_workspace == tmp_path.resolve()


def test_field_names_are_honoured(tmp_path: Path) -> None:
    """Regression: aliased fields used to ignore keyword arguments silently."""
    s = Settings(workspace=tmp_path, max_file_bytes=5, max_files=2)
    assert s.workspace == tmp_path
    assert s.max_file_bytes == 5
    assert s.max_files == 2


def test_unknown_argument_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(wrokspace=Path("."))  # ty: ignore[unknown-argument]


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("LOCAL_LLM_MAX_FILES", "101"),
        ("LOCAL_LLM_MAX_FILES", "0"),
        ("LOCAL_LLM_REQUEST_TIMEOUT", "901"),
        ("LOCAL_LLM_MAX_OUTPUT_TOKENS", "8193"),
        ("LOCAL_LLM_MAX_FILE_BYTES", "0"),
    ],
)
def test_limits_are_enforced(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings()


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
    get_settings.cache_clear()


def test_env_file_in_cwd_is_not_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("OLLAMA_MODEL=from-dotenv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert Settings().ollama_model == "qwen2.5-coder:7b"
