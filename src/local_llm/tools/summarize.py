from local_llm.config import Settings
from local_llm.ollama_client import OllamaClient
from local_llm.tools.common import bounded_text, load_source


async def summarize(path: str, settings: Settings, client: OllamaClient) -> str:
    source = bounded_text(load_source(path, settings))
    return await client.chat(
        f"Summarize purpose, symbols, dependencies and uncertainties.\n\n{source}",
        system="You are a precise source-code analyst. Do not infer unseen behavior.",
    )
