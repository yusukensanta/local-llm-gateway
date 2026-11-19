"""Constrained read-only workspace file access."""

import fnmatch
import os
from collections.abc import Iterator
from pathlib import Path

from local_llm.config import Settings

IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".idea",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".ty_cache",
        ".tox",
    }
)
"""Directories skipped while walking a directory (matched against each relative part)."""

SENSITIVE_DIRS = frozenset({".ssh", ".aws", ".gnupg", ".kube"})
SENSITIVE_FILE_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials*",
)
SENSITIVE_FILE_ALLOWLIST = frozenset({".env.example", ".env.sample", ".env.template"})


class WorkspaceError(ValueError):
    """Workspace access policy violation."""


def is_sensitive(path: Path) -> bool:
    """Return True for files that commonly hold secrets and must never reach a model."""
    if any(part in SENSITIVE_DIRS for part in path.parts[:-1]):
        return True
    name = path.name.lower()
    if name in SENSITIVE_FILE_ALLOWLIST:
        return False
    return any(fnmatch.fnmatch(name, pattern) for pattern in SENSITIVE_FILE_PATTERNS)


def _is_inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def resolve_allowed_path(raw_path: str, settings: Settings) -> Path:
    """Resolve ``raw_path`` and ensure it stays inside the workspace.

    Raises:
        FileNotFoundError: the path does not exist.
        WorkspaceError: the path escapes the workspace, is special, or looks sensitive.
    """
    root = settings.resolved_workspace
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=True)
    if not _is_inside(resolved, root):
        raise WorkspaceError(f"Path is outside the configured workspace: {raw_path}")
    if not resolved.is_file() and not resolved.is_dir():
        raise WorkspaceError(f"Not a regular file or directory: {raw_path}")
    if resolved.is_file() and is_sensitive(resolved.relative_to(root)):
        raise WorkspaceError(f"Access to likely-sensitive file is blocked: {raw_path}")
    return resolved


def read_file(path: Path, settings: Settings) -> str:
    """Read one UTF-8 text file, enforcing the configured size limit."""
    if not path.is_file():
        raise WorkspaceError(f"Not a file: {path}")
    limit = settings.max_file_bytes
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise WorkspaceError(f"File exceeds {limit} byte limit: {path.name}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkspaceError(f"File is not UTF-8 text: {path.name}") from exc


def _iter_candidates(path: Path) -> Iterator[Path]:
    if path.is_file():
        yield path
        return
    for current, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and d not in SENSITIVE_DIRS)
        for name in sorted(files):
            yield Path(current) / name


def collect_text_files(path: Path, settings: Settings) -> str:
    """Concatenate up to ``max_files`` readable text files under ``path``.

    Symlinks that resolve outside the workspace, sensitive files, oversized files and
    non-UTF-8 files are skipped.
    """
    root = settings.resolved_workspace
    chunks: list[str] = []
    for candidate in _iter_candidates(path):
        if len(chunks) >= settings.max_files:
            break
        try:
            real = candidate.resolve(strict=True)
            if not _is_inside(real, root) or not real.is_file():
                continue
            relative = real.relative_to(root)
            if is_sensitive(relative):
                continue
            content = read_file(real, settings)
        except WorkspaceError, OSError:
            continue
        chunks.append(f"\n--- FILE: {relative.as_posix()} ---\n{content}")
    if not chunks:
        raise WorkspaceError("No readable UTF-8 files found within configured limits")
    return "\n".join(chunks)
