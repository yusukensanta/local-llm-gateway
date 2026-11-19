"""Runtime settings."""
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if sys.version_info[:2] != (3, 14):
    raise RuntimeError(f"Python 3.14.x is required; found {sys.version.split()[0]}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5-coder:7b", validation_alias="OLLAMA_MODEL")
    workspace: Path = Field(default_factory=Path.cwd, validation_alias="LOCAL_LLM_WORKSPACE")
    max_file_bytes: int = Field(default=200_000, gt=0, validation_alias="LOCAL_LLM_MAX_FILE_BYTES")
    max_files: int = Field(default=20, gt=0, le=100, validation_alias="LOCAL_LLM_MAX_FILES")
    request_timeout: float = Field(default=180, gt=0, le=900, validation_alias="LOCAL_LLM_REQUEST_TIMEOUT")
    max_output_tokens: int = Field(default=1200, gt=0, le=8192, validation_alias="LOCAL_LLM_MAX_OUTPUT_TOKENS")

    @property
    def resolved_workspace(self) -> Path:
        return self.workspace.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
