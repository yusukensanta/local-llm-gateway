from local_llm.config import Settings
from local_llm.ollama_client import OllamaClient
from local_llm.tools.common import bounded_text, load_source


async def generate_tests(path: str, settings: Settings, client: OllamaClient) -> str:
    source = bounded_text(load_source(path, settings))
    return await client.chat(
        "Propose focused unit tests, edge cases and suggested test names. Do not write files.\n\n"
        + source,
        system="You are an experienced test engineer. Mark assumptions explicitly.",
    )
