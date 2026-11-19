# Troubleshooting

- **Connection refused:** check that Ollama is running and `OLLAMA_BASE_URL` is correct.
- **WSL cannot reach Windows Ollama:** use the Windows host address from `ip route show default`; check Windows Firewall.
- **MCP server missing:** restart Claude Code, inspect `/mcp`, and verify that `.venv` exists (run `scripts/setup.sh`).
- **`Python 3.14.x is required`:** run `uv sync --python 3.14`; the project rejects other interpreters on purpose.
- **File access denied / outside workspace:** register with the intended workspace root. Symlinks pointing outside the workspace are refused.
- **`Access to likely-sensitive or ignored directory ... is blocked`:** direct paths into `.git`, `.venv`, `node_modules`, `.ssh` and similar directories are refused.
- **`Workspace ... is too broad`:** set `LOCAL_LLM_WORKSPACE` (or register from a project directory), not your home directory or one of its parents.
- **`Access to likely-sensitive file is blocked`:** `.env*`, private keys, `.ssh/`, `.aws/` and similar files are never sent to the model.
- **`No unstaged Git diff found`:** `local_review_diff` only reviews unstaged tracked changes; staged and untracked files are ignored.
- **Slow inference:** inspect `ollama ps`, VRAM/RAM and context length.
- **`.env` has no effect on the MCP server:** the server reads environment variables only. Set them in the shell that launches Claude Code, or with `claude mcp add --env`.
- **Requests hang or `Server disconnected without sending a response`:** Ollama itself may be stuck (seen on Windows after loading several models). Restart Ollama and retry; in WSL mirrored mode, connections to closed ports also hang instead of failing fast.
- **Rambling, truncated, or empty replies from `qwen3:4b`:** it is a thinking model. Switch to `qwen3:4b-instruct` (`scripts/install-models.sh qwen3:4b-instruct`, then `scripts/register-mcp.sh --model qwen3:4b-instruct`).
- **`OLLAMA_BASE_URL host ... is not local or private`:** source text would leave your network. Use a local/private address, or set `LOCAL_LLM_ALLOW_REMOTE_OLLAMA=true` if you trust the endpoint.
- **Plugin: MCP server fails to start on first run:** `uv` is downloading Python 3.14 and dependencies. Run `uv sync --locked` once in the plugin directory or retry after a minute; check `uv` is on the `PATH` Claude Code sees.
