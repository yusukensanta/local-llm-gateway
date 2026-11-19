"""Review of unstaged Git changes."""

import asyncio
import shutil
import subprocess

from local_llm.config import Settings
from local_llm.ollama_client import ChatClient
from local_llm.tools.common import bounded_text

GIT_TIMEOUT_SECONDS = 15
# Keep likely secrets out of the diff even when they are tracked.
EXCLUDE_PATHSPECS = (
    ":(exclude,glob)**/.env",
    ":(exclude,glob)**/.env.*",
    ":(exclude,glob)**/*.pem",
    ":(exclude,glob)**/*.key",
    ":(exclude,glob)**/id_rsa*",
    ":(exclude,glob)**/id_ed25519*",
    ":(exclude,glob)**/.netrc",
)


def _run_git_diff(settings: Settings) -> subprocess.CompletedProcess[str]:
    git = shutil.which("git")
    if git is None:
        raise FileNotFoundError("git executable not found on PATH")
    return subprocess.run(  # noqa: S603 - fixed argv, no shell, resolved executable
        [
            git,
            "--no-pager",
            "diff",
            "--no-ext-diff",
            "--no-color",
            "--",
            ".",
            *EXCLUDE_PATHSPECS,
        ],
        cwd=settings.resolved_workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT_SECONDS,
        check=False,
    )


async def review_diff(settings: Settings, client: ChatClient) -> str:
    try:
        result = await asyncio.to_thread(_run_git_diff, settings)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Unable to run git diff: {exc}"
    if result.returncode:
        return f"git diff failed: {result.stderr.strip()}"
    if not result.stdout.strip():
        return "No unstaged Git diff found."
    return await client.chat(
        "Review this diff for actionable bugs, regressions, security concerns and missing tests. "
        "Cite file/hunk. Do not claim tests were run.\n\n" + bounded_text(result.stdout),
        system="You are a conservative code reviewer.",
    )
