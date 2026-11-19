# Linux / WSL setup

1. Install Python 3.11+, Git, Claude Code and Ollama.
2. Run `bash scripts/setup.sh`.
3. Run `bash scripts/install-models.sh`.
4. From a target project, run `bash /path/to/local-llm-gateway/scripts/register-mcp.sh "$PWD"`.
5. Restart Claude Code and inspect `/mcp`.

## WSL with Ollama on Windows

If Ollama runs on Windows and Claude Code in WSL, set the Windows host address before launching Claude Code:

```bash
export OLLAMA_BASE_URL="http://$(ip route show default | awk '{print $3}'):11434"
curl -fsS "$OLLAMA_BASE_URL/api/tags"
```

If Ollama runs inside WSL, the default localhost endpoint is sufficient. Restrict Windows Firewall rules to the WSL virtual network; never expose Ollama publicly.
