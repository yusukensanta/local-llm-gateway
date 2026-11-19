from pathlib import Path

import pytest
from pydantic import ValidationError

from local_llm.config import Settings, get_settings


def test_defaults() -> None:
    s = Settings()
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.model == "qwen2.5-coder:7b"
    assert s.max_files == 20
    assert s.workspace == Path.cwd()
    assert s.think is False


def test_environment_aliases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://192.168.1.5:1")
    monkeypatch.setenv("OLLAMA_MODEL", "tiny")
    monkeypatch.setenv("LOCAL_LLM_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("LOCAL_LLM_MAX_FILES", "3")
    s = Settings()
    assert (s.ollama_base_url, s.model, s.max_files) == ("http://192.168.1.5:1", "tiny", 3)
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
    assert Settings().model == "qwen2.5-coder:7b"


@pytest.mark.parametrize(("raw", "expected"), [("true", True), ("0", False)])
def test_think_flag_from_environment(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool
) -> None:
    monkeypatch.setenv("LOCAL_LLM_THINK", raw)
    assert Settings().think is expected


def _fake_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))


def test_workspace_equal_to_home_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_home(monkeypatch, tmp_path)
    with pytest.raises(ValidationError, match="too broad"):
        Settings(workspace=tmp_path)


def test_workspace_parent_of_home_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "users" / "me"
    home.mkdir(parents=True)
    _fake_home(monkeypatch, home)
    with pytest.raises(ValidationError, match="too broad"):
        Settings(workspace=tmp_path)


def test_default_cwd_workspace_is_checked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The default (``Path.cwd()``) is not validated by pydantic; the model validator must be."""
    _fake_home(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError, match="too broad"):
        Settings()


def test_workspace_below_home_is_allowed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _fake_home(monkeypatch, tmp_path)
    assert Settings(workspace=project).resolved_workspace == project.resolve()


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://[::1]:11434",
        "http://172.24.0.1:11434",
        "http://192.168.0.10:11434",
        "http://169.254.1.1:11434",
        "http://host.docker.internal:11434",
        "https://LOCALHOST",
    ],
)
def test_local_and_private_ollama_urls_are_accepted(url: str) -> None:
    assert Settings(ollama_base_url=url).ollama_base_url == url


@pytest.mark.parametrize(
    "url", ["http://example.test:11434", "https://8.8.8.8", "http://ollama.internal.corp"]
)
def test_remote_ollama_url_requires_opt_in(url: str) -> None:
    with pytest.raises(ValidationError, match="LOCAL_LLM_ALLOW_REMOTE"):
        Settings(ollama_base_url=url)
    assert Settings(ollama_base_url=url, allow_remote=True).ollama_base_url == url


def test_remote_opt_in_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.example.test")
    monkeypatch.setenv("LOCAL_LLM_ALLOW_REMOTE", "true")
    assert Settings().allow_remote is True


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("ftp://localhost", "http"),
        ("localhost:11434", "http"),
        ("http://", "http"),
        ("http://user:pw@localhost:11434", "credentials"),
    ],
)
def test_malformed_ollama_urls_are_rejected(url: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(ollama_base_url=url, allow_remote=True)


def test_prompt_budget_follows_context_and_is_capped() -> None:
    assert Settings().prompt_char_budget == (8192 - 1200 - 500) * 3
    assert Settings(context_tokens=1_000_000).prompt_char_budget == 80_000


def test_context_too_small_for_output_is_rejected() -> None:
    with pytest.raises(ValidationError, match="too little room"):
        Settings(context_tokens=1024, max_output_tokens=1000)


def test_context_tokens_bounds() -> None:
    with pytest.raises(ValidationError):
        Settings(context_tokens=512)


def test_backend_defaults_and_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings().backend == "ollama"
    monkeypatch.setenv("LOCAL_LLM_BACKEND", "openai")
    assert Settings().backend == "openai"
    monkeypatch.setenv("LOCAL_LLM_BACKEND", "bogus")
    with pytest.raises(ValidationError):
        Settings()


def test_openai_base_url_gets_the_same_locality_policy() -> None:
    with pytest.raises(ValidationError, match="LOCAL_LLM_OPENAI_BASE_URL"):
        Settings(openai_base_url="https://api.example.test/v1")
    ok = Settings(openai_base_url="https://api.example.test/v1", allow_remote=True)
    assert ok.openai_base_url.endswith("/v1")
    with pytest.raises(ValidationError, match="credentials"):
        Settings(openai_base_url="http://u:p@localhost:1234/v1")


def test_api_key_is_secret_and_empty_means_none(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings().api_key is None
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "")
    assert Settings().api_key is None
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "sk-secret")
    key = Settings().api_key
    assert key is not None
    assert key.get_secret_value() == "sk-secret"
    assert "sk-secret" not in repr(Settings())


def test_model_neutral_name_wins_over_legacy_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "legacy")
    assert Settings().model == "legacy"
    monkeypatch.setenv("LOCAL_LLM_MODEL", "neutral")
    assert Settings().model == "neutral"


def test_allow_remote_accepts_neutral_and_legacy_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_ALLOW_REMOTE_OLLAMA", "true")
    assert Settings().allow_remote is True
    monkeypatch.delenv("LOCAL_LLM_ALLOW_REMOTE_OLLAMA")
    monkeypatch.setenv("LOCAL_LLM_ALLOW_REMOTE", "true")
    assert Settings().allow_remote is True
