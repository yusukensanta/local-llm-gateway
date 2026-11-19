# Architecture

Claude Code authenticates directly with Anthropic using its normal supported login. This project does not extract, store, or forward Claude subscription OAuth credentials through LiteLLM.

Claude delegates selected read-only analysis tasks through MCP (stdio). Only the result returns to Claude.

## Components

| Module | Responsibility |
| --- | --- |
| `local_llm.server` | MCP server (`MCPServer`); registers the four `local_*` tools |
| `local_llm.config` | Environment-driven `Settings` with validated limits; Python 3.14 guard |
| `local_llm.security.workspace` | Path resolution, workspace boundary, sensitive-file deny-list, bounded UTF-8 reads |
| `local_llm.ollama_client` | Async Ollama `/api/chat` client and the `ChatClient` protocol the tools depend on |
| `local_llm.openai_client` | Client for OpenAI-compatible `/v1/chat/completions` servers |
| `local_llm.clients` | `build_client`: picks the backend from `LOCAL_LLM_BACKEND` |
| `local_llm.errors` | `BackendError`, the base of all backend failures |
| `local_llm.tools.*` | Prompt construction per tool; `review` shells out to `git diff` |

## Data flow

1. Claude Code calls a tool with a path (or none, for `local_review_diff`).
2. The path is resolved and must stay inside `LOCAL_LLM_WORKSPACE`; sensitive files are refused.
3. Up to `LOCAL_LLM_MAX_FILES` UTF-8 files, each at most `LOCAL_LLM_MAX_FILE_BYTES`, are concatenated and truncated to 80,000 characters.
4. The text is sent to the configured model server (Ollama or an OpenAI-compatible endpoint); the reply is returned to Claude Code unchanged.

Nothing in this path writes files or executes generated code.

LiteLLM is optional, intended for Ollama and providers using separately provisioned API credentials.
