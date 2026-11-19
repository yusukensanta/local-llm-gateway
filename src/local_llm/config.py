"""Runtime settings, read from environment variables only."""

import ipaddress
import sys
from functools import lru_cache
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if sys.version_info[:2] != (3, 14):
    raise RuntimeError(f"Python 3.14.x is required; found {sys.version.split()[0]}")


_LOCAL_HOSTNAMES = frozenset({"localhost", "host.docker.internal"})


def _is_local_host(host: str) -> bool:
    """True for loopback, private or link-local addresses and well-known local names."""
    if host.lower() in _LOCAL_HOSTNAMES:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


class Settings(BaseSettings):
    """Server settings.

    Values come from environment variables (``OLLAMA_BASE_URL`` etc.). Field names are
    accepted as keyword arguments too, which keeps tests and programmatic use readable.
    Unknown keyword arguments are rejected instead of silently dropped. No ``.env`` file
    is read: the server's working directory is the user's project, not this repository.
    """

    model_config = SettingsConfigDict(extra="forbid", populate_by_name=True)

    ollama_base_url: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="qwen2.5-coder:7b", validation_alias="OLLAMA_MODEL")
    workspace: Path = Field(default_factory=Path.cwd, validation_alias="LOCAL_LLM_WORKSPACE")
    max_file_bytes: int = Field(default=200_000, gt=0, validation_alias="LOCAL_LLM_MAX_FILE_BYTES")
    max_files: int = Field(default=20, gt=0, le=100, validation_alias="LOCAL_LLM_MAX_FILES")
    request_timeout: float = Field(
        default=180, gt=0, le=900, validation_alias="LOCAL_LLM_REQUEST_TIMEOUT"
    )
    think: bool = Field(default=False, validation_alias="LOCAL_LLM_THINK")
    max_output_tokens: int = Field(
        default=1200, gt=0, le=8192, validation_alias="LOCAL_LLM_MAX_OUTPUT_TOKENS"
    )

    allow_remote_ollama: bool = Field(
        default=False, validation_alias="LOCAL_LLM_ALLOW_REMOTE_OLLAMA"
    )

    @model_validator(mode="after")
    def _check_ollama_endpoint(self) -> Self:
        """Keep source code on this machine or LAN unless the user opts in explicitly.

        Loopback, private/link-local addresses and ``localhost`` are accepted, which covers
        the documented WSL-to-Windows setup. Any other host needs
        ``LOCAL_LLM_ALLOW_REMOTE_OLLAMA=true``, because file contents are sent to it.
        """
        parsed = urlsplit(self.ollama_base_url)
        host = parsed.hostname
        if parsed.scheme not in {"http", "https"} or host is None or host == "":
            raise ValueError("OLLAMA_BASE_URL must be an http(s) URL with a host")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("OLLAMA_BASE_URL must not embed credentials")
        if not self.allow_remote_ollama and not _is_local_host(host):
            raise ValueError(
                f"OLLAMA_BASE_URL host '{host}' is not local or private; source "
                "text would be sent to it. Set LOCAL_LLM_ALLOW_REMOTE_OLLAMA=true to allow this"
            )
        return self

    @model_validator(mode="after")
    def _reject_broad_workspace(self) -> Self:
        """Refuse a workspace that is, or contains, the user's home directory.

        The default workspace is the process's current directory, so starting the server
        from ``$HOME`` or ``/`` would otherwise expose everything beneath it.
        """
        root = self.resolved_workspace
        home = Path.home().resolve()
        if root == home or root in home.parents:
            raise ValueError(
                f"Workspace '{root}' is too broad (home directory or a parent of it); "
                "set LOCAL_LLM_WORKSPACE to a specific project directory"
            )
        return self

    @property
    def resolved_workspace(self) -> Path:
        return self.workspace.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
