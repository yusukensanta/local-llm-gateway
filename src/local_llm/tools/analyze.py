"""Tool: analyze."""

from local_llm.config import Settings
from local_llm.ollama_client import ChatClient
from local_llm.tools.common import bounded_text, fence_untrusted, load_source, with_rules

MAX_QUESTION_CHARS = 4_000


async def analyze(path: str, question: str, settings: Settings, client: ChatClient) -> str:
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"question exceeds {MAX_QUESTION_CHARS} characters")
    source = fence_untrusted(bounded_text(load_source(path, settings), settings.prompt_char_budget))
    return await client.chat(
        f"Question: {question}\n\nSource files:\n{source}",
        system=with_rules(
            "Analyze code carefully. Cite paths; distinguish evidence from assumptions."
        ),
    )
