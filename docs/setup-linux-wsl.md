# Linux / WSL setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, Claude Code and Ollama.
   Python 3.14 itself is downloaded by uv when it is not already installed.
2. Run `bash scripts/setup.sh` (creates `.venv` from `uv.lock`; pass `--no-dev` to skip development tools).
3. Run `bash scripts/install-models.sh` (or pass model names to pull other models).
4. From a target project, run `bash /path/to/local-llm-gateway/scripts/register-mcp.sh "$PWD"`.
   Re-running the script replaces the previous registration.
5. Restart Claude Code and inspect `/mcp`.

Run all quality gates (format, lint, ty, tests with coverage) with `bash scripts/check.sh`.

## WSL with Ollama on Windows

If Ollama runs on Windows and Claude Code in WSL, set the Windows host address before launching Claude Code:

```bash
export OLLAMA_BASE_URL="http://$(ip route show default | awk '{print $3}'):11434"
curl -fsS "$OLLAMA_BASE_URL/api/tags"
```

If Ollama runs inside WSL, the default localhost endpoint is sufficient. Restrict Windows Firewall rules to the WSL virtual network; never expose Ollama publicly.
