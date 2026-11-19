from pathlib import Path
import pytest

from local_llm.config import Settings
from local_llm.security.workspace import WorkspaceError, collect_text_files, read_file, resolve_allowed_path


def test_resolve_path_inside_workspace(tmp_path: Path) -> None:
    target = tmp_path / "main.py"
    target.write_text("pass", encoding="utf-8")
    assert resolve_allowed_path("main.py", Settings(workspace=tmp_path)) == target.resolve()


def test_reject_path_outside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "secret"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="outside"):
        resolve_allowed_path(str(outside), Settings(workspace=root))


def test_reject_nonexistent_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_allowed_path("missing", Settings(workspace=tmp_path))


def test_reject_oversized_file(tmp_path: Path) -> None:
    target = tmp_path / "large.txt"
    target.write_text("123456", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="exceeds"):
        read_file(target, Settings(workspace=tmp_path, max_file_bytes=5))


def test_file_collection_respects_max_files(tmp_path: Path) -> None:
    for name in ("a.py", "b.py", "c.py"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    text = collect_text_files(tmp_path, Settings(workspace=tmp_path, max_files=2))
    assert text.count("--- FILE:") == 2
