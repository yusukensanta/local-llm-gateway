import subprocess

from local_llm.config import Settings
from local_llm.ollama_client import OllamaClient
from local_llm.tools.common import bounded_text


async def review_diff(settings: Settings, client: OllamaClient) -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--no-ext-diff", "--", "."],
            cwd=settings.resolved_workspace,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=15, check=False,
        )
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
