from pathlib import Path

import pytest

from local_llm.config import Settings
from local_llm.security.workspace import (
    WorkspaceError,
    collect_text_files,
    is_sensitive,
    read_file,
    resolve_allowed_path,
)


def test_resolve_path_inside_workspace(tmp_path: Path) -> None:
    target = tmp_path / "main.py"
    target.write_text("pass", encoding="utf-8")
    assert resolve_allowed_path("main.py", Settings(workspace=tmp_path)) == target.resolve()


def test_resolve_accepts_absolute_path_and_workspace_root(tmp_path: Path) -> None:
    target = tmp_path / "a.py"
    target.write_text("x", encoding="utf-8")
    s = Settings(workspace=tmp_path)
    assert resolve_allowed_path(str(target), s) == target.resolve()
    assert resolve_allowed_path(".", s) == tmp_path.resolve()


def test_reject_path_outside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "secret"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="outside"):
        resolve_allowed_path(str(outside), Settings(workspace=root))


def test_reject_dotdot_traversal(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "secret").write_text("s", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="outside"):
        resolve_allowed_path("../secret", Settings(workspace=root))


def test_reject_sibling_directory_with_shared_prefix(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    sibling = tmp_path / "proj-evil"
    root.mkdir()
    sibling.mkdir()
    (sibling / "x.py").write_text("x", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="outside"):
        resolve_allowed_path(str(sibling / "x.py"), Settings(workspace=root))


def test_reject_symlink_escaping_workspace(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    (root / "link.txt").symlink_to(secret)
    with pytest.raises(WorkspaceError, match="outside"):
        resolve_allowed_path("link.txt", Settings(workspace=root))


def test_reject_nonexistent_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_allowed_path("missing", Settings(workspace=tmp_path))


@pytest.mark.parametrize("name", [".env", ".env.production", "server.pem", "id_rsa", "deploy.key"])
def test_reject_sensitive_file(tmp_path: Path, name: str) -> None:
    (tmp_path / name).write_text("secret", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="sensitive"):
        resolve_allowed_path(name, Settings(workspace=tmp_path))


def test_is_sensitive() -> None:
    assert is_sensitive(Path(".ssh/config"))
    assert is_sensitive(Path("deep/dir/.env"))
    assert is_sensitive(Path("Credentials.json"))
    assert not is_sensitive(Path(".env.example"))
    assert not is_sensitive(Path("src/main.py"))


def test_reject_oversized_file(tmp_path: Path) -> None:
    target = tmp_path / "large.txt"
    target.write_text("123456", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="exceeds"):
        read_file(target, Settings(workspace=tmp_path, max_file_bytes=5))


def test_read_file_at_exact_limit(tmp_path: Path) -> None:
    target = tmp_path / "ok.txt"
    target.write_text("12345", encoding="utf-8")
    assert read_file(target, Settings(workspace=tmp_path, max_file_bytes=5)) == "12345"


def test_reject_non_utf8(tmp_path: Path) -> None:
    target = tmp_path / "bin.dat"
    target.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(WorkspaceError, match="UTF-8"):
        read_file(target, Settings(workspace=tmp_path))


def test_read_file_rejects_directory(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="Not a file"):
        read_file(tmp_path, Settings(workspace=tmp_path))


def test_file_collection_respects_max_files(tmp_path: Path) -> None:
    for name in ("a.py", "b.py", "c.py"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    text = collect_text_files(tmp_path, Settings(workspace=tmp_path, max_files=2))
    assert text.count("--- FILE:") == 2
    assert text.index("a.py") < text.index("b.py")


def test_collection_skips_unreadable_but_fills_quota(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"\xff\xfe")
    (tmp_path / "b.py").write_text("b", encoding="utf-8")
    (tmp_path / "c.py").write_text("c", encoding="utf-8")
    text = collect_text_files(tmp_path, Settings(workspace=tmp_path, max_files=2))
    assert "b.py" in text
    assert "c.py" in text


def test_collection_skips_ignored_and_sensitive(tmp_path: Path) -> None:
    for rel in ("keep.py", ".git/config", "node_modules/x.js", ".ssh/id", ".env", "sub/ok.py"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(rel, encoding="utf-8")
    text = collect_text_files(tmp_path, Settings(workspace=tmp_path))
    assert "keep.py" in text
    assert "sub/ok.py" in text
    for banned in (".git/config", "node_modules", ".ssh", "--- FILE: .env"):
        assert banned not in text


def test_collection_ignores_only_relative_parts(tmp_path: Path) -> None:
    """A workspace living under a directory called ``venv`` must still work."""
    root = tmp_path / "venv" / "proj"
    root.mkdir(parents=True)
    (root / "a.py").write_text("a", encoding="utf-8")
    assert "a.py" in collect_text_files(root, Settings(workspace=root))


def test_collection_skips_symlink_escaping_workspace(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("TOPSECRET", encoding="utf-8")
    (root / "ok.py").write_text("ok", encoding="utf-8")
    (root / "leak.txt").symlink_to(tmp_path / "secret.txt")
    (root / "leakdir").symlink_to(tmp_path, target_is_directory=True)
    text = collect_text_files(root, Settings(workspace=root))
    assert "TOPSECRET" not in text
    assert "ok.py" in text


def test_collection_single_file(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print()", encoding="utf-8")
    text = collect_text_files(tmp_path / "a.py", Settings(workspace=tmp_path))
    assert text.startswith("\n--- FILE: a.py ---")


def test_collection_without_readable_files_raises(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceError, match="No readable"):
        collect_text_files(tmp_path, Settings(workspace=tmp_path))
