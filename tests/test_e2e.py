"""End-to-end: real MCP server subprocess over stdio, talking to a fake Ollama over HTTP."""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import override

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REQUESTS: list[dict[str, object]] = []


class FakeOllama(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers["Content-Length"])
        REQUESTS.append(json.loads(self.rfile.read(length)))
        body = json.dumps({"message": {"content": "fake-review"}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @override
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def fake_ollama():
    REQUESTS.clear()
    server = HTTPServer(("127.0.0.1", 0), FakeOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


async def test_full_round_trip(fake_ollama: str, tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def hello(): return 'world'\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=TOPSECRET\n", encoding="utf-8")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "local_llm.server"],
        env={
            "OLLAMA_BASE_URL": fake_ollama,
            "LOCAL_LLM_WORKSPACE": str(tmp_path),
            "PATH": "/usr/bin:/bin",
        },
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        assert {t.name for t in tools.tools} == {
            "local_analyze",
            "local_summarize",
            "local_review_diff",
            "local_generate_tests",
        }

        ok = await session.call_tool("local_analyze", {"path": "app.py", "question": "what?"})
        assert not ok.is_error
        assert "fake-review" in json.dumps([c.model_dump() for c in ok.content])

        blocked = await session.call_tool("local_summarize", {"path": ".env"})
        assert blocked.is_error
        escaped = await session.call_tool("local_summarize", {"path": "../../etc/passwd"})
        assert escaped.is_error

    prompts = json.dumps(REQUESTS)
    assert "def hello()" in prompts
    assert "TOPSECRET" not in prompts
