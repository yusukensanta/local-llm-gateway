"""Review of unstaged Git changes."""

import asyncio
import logging
import shutil
import subprocess

from local_llm.config import Settings
from local_llm.ollama_client import ChatClient
from local_llm.security.workspace import SENSITIVE_DIRS, SENSITIVE_FILE_PATTERNS
from local_llm.tools.common import bounded_text, fence_untrusted, with_rules

logger = logging.getLogger(__name__)

GIT_TIMEOUT_SECONDS = 15
# Keep likely secrets out of the diff even when they are tracked. Derived from the same
# constants as ``is_sensitive`` so the two policies cannot drift apart.
EXCLUDE_PATHSPECS = (
    *(f":(exclude,glob,icase)**/{pattern}" for pattern in SENSITIVE_FILE_PATTERNS),
    *(f":(exclude,glob,icase)**/{name}/**" for name in sorted(SENSITIVE_DIRS)),
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
            "--no-textconv",
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
    except OSError, subprocess.TimeoutExpired:
        # Details (absolute paths, OS messages) stay in the server log, not in the tool result.
        logger.warning("Unable to run git diff", exc_info=True)
        return "Unable to run git diff (see the local-llm server log)."
    if result.returncode:
        logger.warning("git diff exited %s: %s", result.returncode, result.stderr.strip())
        return f"git diff failed (exit code {result.returncode}; see the server log)."
    if not result.stdout.strip():
        return "No unstaged Git diff found."
    return await client.chat(
        "Review this diff for actionable bugs, regressions, security concerns and missing tests. "
        "Cite file/hunk. Do not claim tests were run.\n\n"
        + fence_untrusted(bounded_text(result.stdout)),
        system=with_rules("You are a conservative code reviewer."),
    )
