# Local LLM Gateway

**Local LLMs as read-only coding assistants for Claude Code.**

Local LLM Gateway exposes a small set of MCP tools that let Claude Code delegate bounded code-analysis tasks to a model running on your machine (or another endpoint you configure). It works with [Ollama](https://ollama.com/) out of the box and with any server that speaks the OpenAI chat-completions API, such as LM Studio, llama.cpp, vLLM or LiteLLM.

Use Claude Code for orchestration and decision-making, and use the local model for focused, lower-cost work such as source summarization, code analysis, diff review, and test-case suggestions.

> **Status:** Early-stage project. Review the limitations below and verify model-generated suggestions before relying on them.

## Why this project?

Claude Code is useful as the primary coding agent, but sending every analysis task to a hosted model can consume tokens quickly. This project adds a separate local inference path without replacing Claude Code's normal authentication or workflow.

- Keep Claude Code connected directly to Anthropic using its supported login.
- Delegate selected tasks to a local model through MCP, whichever server runs it.
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
Local model server
(Ollama or OpenAI-compatible)
 |
 | analysis result
 v
Local LLM Gateway  ---------------->  Claude Code
```

Claude Code remains the primary agent. It decides when to call an MCP tool, receives the result, and can use that result in its wider reasoning.

The MCP server reads files inside the configured workspace, applies input limits, and sends the selected text to the configured model endpoint. If the model server runs locally, inference is performed on your machine. If you point the endpoint (`OLLAMA_BASE_URL` or `LOCAL_LLM_OPENAI_BASE_URL`) at a remote host, the source text is sent to that host.

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
- A local model server: [Ollama](https://ollama.com/) (the default) or any OpenAI-compatible server (see [Using another LLM server](#using-another-llm-server))

The default backend is Ollama with the model `qwen2.5-coder:7b`. Model quality and inference speed depend on your hardware. A GPU with 6 GB VRAM may not fit the entire model; Ollama can use CPU/RAM offload, which may reduce generation speed.

## Quick start

The scripts below set up the default Ollama backend. For LM Studio, llama.cpp, vLLM or another OpenAI-compatible server, run `setup` and `register-mcp` as shown, skip `install-models`, and set the variables in [Using another LLM server](#using-another-llm-server) before launching Claude Code.

Run these commands from the repository root.

### Windows (PowerShell)

```powershell
# Create the virtual environment and install the project
.\scripts\setup.ps1

# Download the default Ollama model (Ollama backend only)
.\scripts\install-models.ps1

# Register the MCP server for the current project workspace
.\scripts\register-mcp.ps1 -Workspace (Get-Location).Path
```

### Linux / WSL (Bash)

```bash
# Create the virtual environment and install the project
bash scripts/setup.sh

# Download the default Ollama model (Ollama backend only)
bash scripts/install-models.sh

# Register the MCP server for the current project workspace
bash scripts/register-mcp.sh "$PWD"

# Or pick the model explicitly (it must already be pulled in Ollama)
bash scripts/install-models.sh qwen3:4b-instruct
bash scripts/register-mcp.sh --model qwen3:4b-instruct "$PWD"
```

`install-models.sh` falls back to the Ollama HTTP API (`OLLAMA_BASE_URL`) when the `ollama` CLI is not installed, which is the normal case in WSL with Ollama on Windows. On Windows use `.\scripts\register-mcp.ps1 -Model qwen3:4b-instruct`.

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

### Install as a Claude Code plugin

This repository is also a Claude Code plugin marketplace. You need [`uv`](https://docs.astral.sh/uv/) and a running local model server (Ollama with the model pulled, or an OpenAI-compatible server with a model loaded).

```bash
claude plugin marketplace add yusukensanta/local-llm-gateway
claude plugin install local-llm@local-llm-gateway
```

Claude Code prompts for the backend (`ollama` or `openai`), the model, the endpoint URL, an optional API key and the context size when the plugin is enabled. The plugin runs `uv run --locked` from its own directory (Python 3.14 is fetched by `uv` if missing; the first start downloads dependencies, so it can be slow), keeps its virtual environment in the plugin data directory, and sets `LOCAL_LLM_WORKSPACE` to the current project. If you registered the server earlier with `register-mcp.sh`, remove it with `claude mcp remove local-llm --scope user` so the tools do not appear twice. In the other direction, `register-mcp.sh` / `register-mcp.ps1` refuse to register while the plugin is installed; pass `--force` / `-Force` to override.

## Configuration

The MCP server reads the following environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `LOCAL_LLM_BACKEND` | `ollama` | `ollama` (native API) or `openai` (any OpenAI-compatible server, see below) |
| `LOCAL_LLM_MODEL` | `qwen2.5-coder:7b` | Model name as the selected backend knows it. `OLLAMA_MODEL` is accepted as a legacy alias |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint (backend `ollama`) |
| `LOCAL_LLM_OPENAI_BASE_URL` | `http://localhost:1234/v1` | Base URL of the OpenAI-compatible server (backend `openai`) |
| `LOCAL_LLM_API_KEY` | unset | Optional bearer token for the OpenAI-compatible server. Never logged |
| `LOCAL_LLM_CONTEXT_TOKENS` | `8192` | Context window the model is served with. Sent to Ollama as `num_ctx`; for other servers it must match the server's own setting. Also sizes how much source is sent (about `(context - output tokens - 500) * 3` characters, at most 80,000) |
| `LOCAL_LLM_WORKSPACE` | Current working directory | Allowed workspace root |
| `LOCAL_LLM_MAX_FILE_BYTES` | `200000` | Maximum size of an individual file, in bytes |
| `LOCAL_LLM_MAX_FILES` | `20` | Maximum number of files collected (maximum configurable value: 100) |
| `LOCAL_LLM_REQUEST_TIMEOUT` | `180` | Model request timeout, in seconds (maximum: 900) |
| `LOCAL_LLM_MAX_OUTPUT_TOKENS` | `1200` | Maximum generated output tokens (maximum: 8192) |
| `LOCAL_LLM_ALLOW_REMOTE` | `false` | Allow either endpoint to point at a host that is not loopback or private. Source text and the API key are sent to that host, so enable it only for endpoints you trust. `LOCAL_LLM_ALLOW_REMOTE_OLLAMA` is a legacy alias |
| `LOCAL_LLM_THINK` | `false` | Ollama backend only: let reasoning models (for example `qwen3`) think before answering. Thinking consumes output tokens, so keep it off unless you raise the token limit |

The registration scripts set `LOCAL_LLM_WORKSPACE` to the workspace path you provide. Other variables can be set in the environment inherited by Claude Code before it starts. The server does not read `.env` files; invalid values (for example `LOCAL_LLM_MAX_FILES=0`) fail at startup.

### Using another LLM server

Set `LOCAL_LLM_BACKEND=openai` to talk to any server that implements `POST /v1/chat/completions`.

```bash
export LOCAL_LLM_BACKEND=openai
export LOCAL_LLM_OPENAI_BASE_URL=http://localhost:1234/v1   # LM Studio's default
export LOCAL_LLM_MODEL=<model id as the server names it>
export LOCAL_LLM_CONTEXT_TOKENS=8192                         # must match how the server was started
# export LOCAL_LLM_API_KEY=...                               # only if the server requires one
```

| Server | Typical base URL | Context window is set by |
| --- | --- | --- |
| LM Studio | `http://localhost:1234/v1` | the context length control when loading the model |
| llama.cpp `llama-server` | `http://localhost:8080/v1` | `-c` / `--ctx-size` at startup |
| vLLM | `http://localhost:8000/v1` | `--max-model-len` at startup |
| LiteLLM proxy | `http://localhost:4000/v1` | the upstream model's server |
| Ollama (`/v1`) | `http://localhost:11434/v1` | the model's loaded context (`ollama ps`); prefer the native backend, which sets it for you |

Ports are the usual defaults; check your server. Only the Ollama `/v1` route has been exercised against a real server in this project's testing; the others are covered by the API contract and mocked tests.

Differences from the Ollama backend:

- The OpenAI API has no per-request context setting, so `LOCAL_LLM_CONTEXT_TOKENS` only sizes the prompt. Keep it equal to the server's own context, or requests will be rejected (or truncated, depending on the server).
- `LOCAL_LLM_THINK` is ignored.
- The same locality policy applies: the URL must be loopback or private unless `LOCAL_LLM_ALLOW_REMOTE=true`.

## Model selection and performance

The default model is a starting point, not a universal recommendation. The measurements below were taken with Ollama; other servers differ.

- Start with the default `qwen2.5-coder:7b` model, or `--model qwen3:4b-instruct` for a faster option that fits fully in 6 GB of VRAM (measured on a GTX 1660 SUPER: about 70 tok/s versus about 13 tok/s for the 7B model, which partly spills to CPU). Avoid the plain `qwen3:4b` tag for these tools: it is a thinking model and writes its reasoning draft into the answer even with `LOCAL_LLM_THINK=false`.
- Check model placement and resource usage with `ollama ps` and `nvidia-smi`.
- Whatever the server, check model placement and memory with its own tools. If inference is slow or memory is constrained, try a smaller model or reduce the amount of source text sent for a task.
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

Dependabot opens weekly update PRs for GitHub Actions and Python dependencies. It does not cover the optional LiteLLM image in `docker-compose.yml`: the image lives on `docker.litellm.ai`, which Dependabot cannot read. That image is pinned by digest, so update the tag and digest by hand when you want a newer LiteLLM release.

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

The LiteLLM image is pinned by digest and is not updated automatically; see [Development](#development).

The proxy is configured to bind to loopback on port `4000`. Treat the master key and provider credentials as secrets; do not commit your real `.env` file.

## Security and limitations

- **Workspace boundary:** requested paths must resolve inside `LOCAL_LLM_WORKSPACE`; symlinks that point outside are skipped or refused. Paths into `.git`, `.venv`, `node_modules` and similar directories are refused even when named directly. A workspace that is your home directory (or a parent of it) is rejected at startup; point it at a specific project.
- **Secrets are never read:** `.env` / `.env.*` / `*.env` (except `.env.example`), private keys, keystores, Terraform state and variables, `.ssh/`, `.aws/`, `.docker/`, `.netrc`, `.git-credentials` and similar files are blocked (case-insensitively for directories), and also excluded from `local_review_diff` using the same list.
- **Local endpoint by default:** `OLLAMA_BASE_URL` and `LOCAL_LLM_OPENAI_BASE_URL` must be loopback or a private address unless `LOCAL_LLM_ALLOW_REMOTE=true`; URLs with embedded credentials are rejected. The API key is held as a secret and sent only in the `Authorization` header.
- **Race-resistant reads:** files are opened with `O_NOFOLLOW` (POSIX) and checked to be regular files, so a path swapped for a symlink after validation is not followed. Directory components are not re-checked; this assumes no hostile local process writing to the workspace.
- **Bounded input:** file count, individual file size, total prompt size (reading stops at the limit), the `question` length and output tokens are limited. Git and OS error details are logged, not returned to the caller.
- **Read-only tools:** the MCP tools do not write files, apply patches, or run shell commands.
- **Prompt injection:** file and diff contents are fenced as untrusted data and the system prompt tells the model not to follow instructions found there. This reduces the risk but cannot remove it.
- **Untrusted output:** local model responses can be incorrect, incomplete, or misleading. Verify claims against source code and run tests independently.
- **Data handling:** source text is sent to the configured model endpoint. Use a trusted endpoint and do not assume data stays on the local machine when using a remote URL.
- **Not a replacement for review:** model-generated analysis is advisory and is not a substitute for tests, static analysis, or human review.

## Troubleshooting

- **Connection refused:** confirm the model server is running and that the endpoint (`OLLAMA_BASE_URL` or `LOCAL_LLM_OPENAI_BASE_URL`) is reachable.
- **WSL cannot reach Windows Ollama:** use the Windows host address described above and check Windows Firewall rules.
- **MCP server does not appear:** restart Claude Code, inspect `/mcp`, and verify that the registered Python executable exists.
- **File access is denied:** register the server with the intended workspace root.
- **Inference is slow:** inspect the server's resource view (`ollama ps` for Ollama), available RAM/VRAM, model size, and input length.
- **401/403 from an OpenAI-compatible server:** set `LOCAL_LLM_API_KEY`.

See the [troubleshooting guide](docs/troubleshooting.md) for additional notes.

## License

[MIT](LICENSE)
