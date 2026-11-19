"""Shared source loading helpers."""

from local_llm.config import Settings
from local_llm.security.workspace import collect_text_files, resolve_allowed_path

OUTPUT_RULES = (
    "Output rules: give the final answer only. Do not narrate your plan, restate the task, "
    "list your steps, or repeat yourself. Start directly with the result, use concise "
    "Markdown, and state only what the provided text supports."
)
"""Appended to every system prompt; small models otherwise write drafts and truncate."""


def with_rules(system: str) -> str:
    return f"{system}\n\n{OUTPUT_RULES}"


def load_source(raw_path: str, settings: Settings) -> str:
    return collect_text_files(resolve_allowed_path(raw_path, settings), settings)


def bounded_text(text: str, max_chars: int = 80_000) -> str:
    return text if len(text) <= max_chars else text[:max_chars] + "\n[TRUNCATED]"
