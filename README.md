# Local LLM Gateway

Cross-platform (Windows, Linux, WSL) read-only MCP tools for Claude Code to delegate selected coding analysis to local Ollama models.

## Authentication boundary

Claude Code keeps its normal direct Anthropic login. This project does not extract or proxy Claude Code subscription OAuth credentials through LiteLLM. The MCP server calls Ollama independently. The optional LiteLLM profile is for Ollama and providers using separately provisioned API keys.

## Quick start

Windows PowerShell:
```powershell
.\scripts\setup.ps1
.\scripts\install-models.ps1
.\scripts\register-mcp.ps1 -Workspace (Get-Location).Path
```

Linux / WSL:
```bash
bash scripts/setup.sh
bash scripts/install-models.sh
bash scripts/register-mcp.sh "$PWD"
```

If Ollama runs on Windows and Claude Code in WSL, set `OLLAMA_BASE_URL` to the Windows host IP. See [Linux/WSL setup](docs/setup-linux-wsl.md).

## Tools

- `local_analyze(path, question)`
- `local_summarize(path)`
- `local_review_diff()`
- `local_generate_tests(path)`

All tools are read-only. Paths must resolve inside `LOCAL_LLM_WORKSPACE`; file count and size are bounded. Treat model output as untrusted and verify it.

## Tests

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
python -m pytest -q
```

GitHub Actions validates Python on Ubuntu and Windows, PowerShell/Bash scripts, Pester tests and Docker Compose configuration.

## Optional LiteLLM

LiteLLM is an independent optional gateway for Ollama and providers using separately provisioned API credentials; it does not proxy Claude Code subscription OAuth. Copy `.env.example` to `.env`, set `LITELLM_MASTER_KEY`, then run `docker compose --profile gateway up -d`. The proxy binds to loopback port 4000.
