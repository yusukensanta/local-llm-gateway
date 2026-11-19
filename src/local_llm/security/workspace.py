"""Constrained read-only workspace file access."""
from pathlib import Path

from local_llm.config import Settings


class WorkspaceError(ValueError):
    """Workspace access policy violation."""


def resolve_allowed_path(raw_path: str, settings: Settings) -> Path:
    root = settings.resolved_workspace
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise WorkspaceError(f"Path is outside the configured workspace: {raw_path}") from exc
    if not resolved.is_file() and not resolved.is_dir():
        raise WorkspaceError(f"Not a regular file or directory: {raw_path}")
    return resolved


def read_file(path: Path, settings: Settings) -> str:
    if not path.is_file():
        raise WorkspaceError(f"Not a file: {path}")
    if path.stat().st_size > settings.max_file_bytes:
        raise WorkspaceError(f"File exceeds {settings.max_file_bytes} byte limit: {path.name}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise WorkspaceError(f"File is not UTF-8 text: {path.name}") from exc


def collect_text_files(path: Path, settings: Settings) -> str:
    ignored = {".git", ".venv", "venv", "node_modules", "__pycache__", ".idea"}
    candidates = [path] if path.is_file() else sorted(
        p for p in path.rglob("*") if p.is_file() and not any(part in ignored for part in p.parts)
    )
    chunks: list[str] = []
    for file_path in candidates[: settings.max_files]:
        try:
            content = read_file(file_path, settings)
        except (WorkspaceError, OSError):
            continue
        chunks.append(
            f"\n--- FILE: {file_path.relative_to(settings.resolved_workspace).as_posix()} ---\n"
            f"{content}"
        )
    if not chunks:
        raise WorkspaceError("No readable UTF-8 files found within configured limits")
    return "\n".join(chunks)
