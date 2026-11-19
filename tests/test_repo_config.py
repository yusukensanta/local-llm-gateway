"""Guards for repository-level automation config."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_dependabot_covers_every_dependency_surface() -> None:
    text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    ecosystems = set(re.findall(r"package-ecosystem:\s*(\S+)", text))
    assert ecosystems == {"github-actions", "uv", "docker-compose"}
    # Every ecosystem entry needs a schedule, otherwise Dependabot rejects the file.
    assert text.count("schedule:") == len(ecosystems)


def test_workflow_actions_are_pinned_to_commit_shas() -> None:
    uses = [
        line.split("uses:", 1)[1].strip()
        for path in (ROOT / ".github" / "workflows").glob("*.yml")
        for line in path.read_text(encoding="utf-8").splitlines()
        if "uses:" in line
    ]
    assert uses
    for ref in uses:
        assert re.match(r"[\w./-]+@[0-9a-f]{40}\s+#\s*v\S+$", ref), ref


def test_compose_image_is_pinned_by_digest() -> None:
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert re.search(r"image:\s*\S+@sha256:[0-9a-f]{64}", text)
