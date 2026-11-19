"""Read-only MCP tools backed by Ollama."""

from mcp.server.mcpserver import MCPServer

from local_llm.clients import build_client
from local_llm.config import get_settings
from local_llm.tools.analyze import analyze
from local_llm.tools.generate_tests import generate_tests
from local_llm.tools.review import review_diff
from local_llm.tools.summarize import summarize

mcp = MCPServer("local-llm")
settings = get_settings()
client = build_client(settings)


@mcp.tool()
async def local_analyze(path: str, question: str) -> str:
    """Analyze a file/directory inside the configured workspace."""
    return await analyze(path, question, settings, client)


@mcp.tool()
async def local_summarize(path: str) -> str:
    """Summarize a file/directory inside the configured workspace."""
    return await summarize(path, settings, client)


@mcp.tool()
async def local_review_diff() -> str:
    """Review unstaged Git changes in the configured workspace (read-only)."""
    return await review_diff(settings, client)


@mcp.tool()
async def local_generate_tests(path: str) -> str:
    """Suggest tests for source files; does not create or modify files."""
    return await generate_tests(path, settings, client)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
