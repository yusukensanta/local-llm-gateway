"""Tool: analyze."""

from local_llm.config import Settings
from local_llm.ollama_client import ChatClient
from local_llm.tools.common import bounded_text, load_source, with_rules


async def analyze(path: str, question: str, settings: Settings, client: ChatClient) -> str:
    source = bounded_text(load_source(path, settings))
    return await client.chat(
        f"Question: {question}\n\nSource files:\n{source}",
        system=with_rules(
            "Analyze code carefully. Cite paths; distinguish evidence from assumptions."
        ),
    )
