"""Shared source loading helpers."""

from local_llm.config import Settings
from local_llm.security.workspace import collect_text_files, resolve_allowed_path


def load_source(raw_path: str, settings: Settings) -> str:
    return collect_text_files(resolve_allowed_path(raw_path, settings), settings)


def bounded_text(text: str, max_chars: int = 80_000) -> str:
    return text if len(text) <= max_chars else text[:max_chars] + "\n[TRUNCATED]"
