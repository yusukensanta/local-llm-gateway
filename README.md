# Local LLM Gateway

**Local Ollama models as read-only coding assistants for Claude Code.**

Local LLM Gateway exposes a small set of MCP tools that let Claude Code delegate bounded code-analysis tasks to an Ollama model running on your machine (or another endpoint you configure).

Use Claude Code for orchestration and decision-making, and use the local model for focused, lower-cost work such as source summarization, code analysis, diff review, and test-case suggestions.

> **Status:** Early-stage project. Review the limitations below and verify model-generated suggestions before relying on them.

## Why this project?

Claude Code is useful as the primary coding agent, but sending every analysis task to a hosted model can consume tokens quickly. This project adds a separate local inference path without replacing Claude Code's normal authentication or workflow.

- Keep Claude Code connected directly to Anthropic using its supported login.
- Delegate selected tasks to Ollama through MCP.
- Keep the integration read-only: the tools do not edit source files or execute generated tests.
- Bound workspace access and input size to reduce accidental over-reading.

## How it works

```text
You
 |
 v
Claude Code  ---------------------->  Anthropic
 |
 | MCP (stdio)
 v
Local LLM Gateway
 |
 | validated workspace files / Git diff
 v
Ollama
 |
 | analysis result
 v
Local LLM Gateway  ---------------->  Claude Code
```

Claude Code remains the primary agent. It decides when to call an MCP tool, receives the result, and can use that result in its wider reasoning.

The MCP server reads files inside the configured workspace, applies input limits, and sends the selected text to the configured Ollama endpoint. If Ollama runs locally, inference is performed on your machine. If you point `OLLAMA_BASE_URL` at a remote host, the source text is sent to that host.

### Authentication boundary

Claude Code uses its normal direct Anthropic login. This project does **not** extract, store, or proxy Claude Code subscription OAuth credentials through LiteLLM.

The optional LiteLLM configuration is an independent gateway for Ollama and providers configured with separately provisioned API credentials. It is not required for the MCP integration.

## Features

| MCP tool | Purpose | Behavior |
| --- | --- | --- |
| `local_analyze(path, question)` | Analyze source code against a specific question | Reads a file or directory within the workspace |
| `local_summarize(path)` | Summarize source code | Summarizes purpose, symbols, dependencies, and uncertainties |
| `local_review_diff()` | Review current unstaged Git changes | Reviews the output of `git diff` in the configured workspace |
| `local_generate_tests(path)` | Suggest tests for source code | Returns test ideas and edge cases; does not create test files |

All tools are read-only. In particular, `local_review_diff` currently reviews **unstaged tracked changes**; staged changes and untracked files are not included.

## Requirements

- Windows, Linux, or WSL
- **Python 3.14.x** (the project intentionally rejects other Python versions)
- [uv](https://docs.astral.sh/uv/) (installs and manages Python 3.14 for you)
- [Git](https://git-scm.com/)
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Ollama](https://ollama.com/)

The default model is `qwen2.5-coder:7b`. Model quality and inference speed depend on your hardware. A GPU with 6 GB VRAM may not fit the entire model; Ollama can use CPU/RAM offload, which may reduce generation speed.

## Quick start

Run these commands from the repository root.

### Windows (PowerShell)

```powershell
# Create the virtual environment and install the project
.\scripts\setup.ps1

# Download the default Ollama model
.\scripts\install-models.ps1

# Register the MCP server for the current project workspace
.\scripts\register-mcp.ps1 -Workspace (Get-Location).Path
```

### Linux / WSL (Bash)

```bash
# Create the virtual environment and install the project
bash scripts/setup.sh

# Download the default Ollama model
bash scripts/install-models.sh

# Register the MCP server for the current project workspace
bash scripts/register-mcp.sh "$PWD"
```

After registration, restart Claude Code (or start a new session) and run:

```text
/mcp
```

Confirm that `local-llm` is listed and its tools are available.

### WSL with Ollama running on Windows

When Claude Code runs inside WSL but Ollama runs on Windows, the default `localhost` URL may not reach the Windows Ollama service. Set the Windows host address in the shell **before launching Claude Code**:

```bash
export OLLAMA_BASE_URL="http://$(ip route show default | awk '{print $3}'):11434"
curl -fsS "$OLLAMA_BASE_URL/api/tags"
claude
```

If Ollama runs inside the same WSL environment, the default `http://localhost:11434` endpoint is normally sufficient. Do not expose the Ollama API publicly; restrict network access appropriately.

More detailed guides:
- [Windows setup](docs/setup-windows.md)
- [Linux / WSL setup](docs/setup-linux-wsl.md)

## Configuration

The MCP server reads the following environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Model name available in Ollama |
| `LOCAL_LLM_WORKSPACE` | Current working directory | Allowed workspace root |
| `LOCAL_LLM_MAX_FILE_BYTES` | `200000` | Maximum size of an individual file, in bytes |
| `LOCAL_LLM_MAX_FILES` | `20` | Maximum number of files collected (maximum configurable value: 100) |
| `LOCAL_LLM_REQUEST_TIMEOUT` | `180` | Ollama request timeout, in seconds (maximum: 900) |
| `LOCAL_LLM_MAX_OUTPUT_TOKENS` | `1200` | Maximum generated output tokens (maximum: 8192) |

The registration scripts set `LOCAL_LLM_WORKSPACE` to the workspace path you provide. Other variables can be set in the environment inherited by Claude Code before it starts. The server does not read `.env` files; invalid values (for example `LOCAL_LLM_MAX_FILES=0`) fail at startup.

## Model selection and performance

The default model is a starting point, not a universal recommendation.

- Start with the default `qwen2.5-coder:7b` model.
- Check model placement and resource usage with `ollama ps` and `nvidia-smi`.
- If inference is slow or memory is constrained, try a smaller model or reduce the amount of source text sent for a task.
- Evaluate models using representative tasks from your own repositories; compare correctness and usefulness, not just generation speed.

See [model selection notes](docs/model-selection.md).

## Development

The toolchain is Python 3.14, [uv](https://docs.astral.sh/uv/), [Ruff](https://docs.astral.sh/ruff/) and [ty](https://docs.astral.sh/ty/) (a pre-1.0 type checker; its version is pinned by `uv.lock`).

```bash
uv sync                      # create .venv and install locked dependencies
bash scripts/check.sh        # ruff format --check, ruff check, ty check, pytest --cov (min 80%)

# or individually
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest --cov
```

On Windows use `.\scripts\check.ps1`. After changing dependencies, run `uv lock` and commit `uv.lock`.

GitHub Actions runs the same gates on Ubuntu and Windows, checks that `uv.lock` is current, runs ShellCheck and the Pester script tests, and validates the optional Docker Compose configuration.

## Optional: LiteLLM

LiteLLM is not needed for Claude Code to call the local MCP tools.

To run the optional gateway:

1. Copy `.env.example` to `.env`.
2. Set a strong `LITELLM_MASTER_KEY`.
3. Configure any provider credentials you intend to use.
4. Start the gateway:

```bash
docker compose --profile gateway up -d
```

The proxy is configured to bind to loopback on port `4000`. Treat the master key and provider credentials as secrets; do not commit your real `.env` file.

## Security and limitations

- **Workspace boundary:** requested paths must resolve inside `LOCAL_LLM_WORKSPACE`; symlinks that point outside are skipped or refused.
- **Secrets are never read:** `.env` / `.env.*` (except `.env.example`), private keys, `.ssh/`, `.aws/`, `.netrc` and similar files are blocked, and also excluded from `local_review_diff`.
- **Bounded input:** file count, individual file size, and prompt/output sizes are limited.
- **Read-only tools:** the MCP tools do not write files, apply patches, or run shell commands.
- **Untrusted output:** local model responses can be incorrect, incomplete, or misleading. Verify claims against source code and run tests independently.
- **Data handling:** source text is sent to the configured Ollama endpoint. Use a trusted endpoint and do not assume data stays on the local machine when using a remote URL.
- **Not a replacement for review:** model-generated analysis is advisory and is not a substitute for tests, static analysis, or human review.

## Troubleshooting

- **Connection refused:** confirm Ollama is running and that `OLLAMA_BASE_URL` is reachable.
- **WSL cannot reach Windows Ollama:** use the Windows host address described above and check Windows Firewall rules.
- **MCP server does not appear:** restart Claude Code, inspect `/mcp`, and verify that the registered Python executable exists.
- **File access is denied:** register the server with the intended workspace root.
- **Inference is slow:** inspect `ollama ps`, available RAM/VRAM, model size, and input length.

See the [troubleshooting guide](docs/troubleshooting.md) for additional notes.

## License

[MIT](LICENSE)
