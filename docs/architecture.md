# Architecture

Claude Code authenticates directly with Anthropic using its normal supported login. This project does not extract, store, or forward Claude subscription OAuth credentials through LiteLLM.

Claude delegates selected read-only analysis tasks through MCP. The server validates workspace paths, reads bounded UTF-8 files and sends them to Ollama. Only the result returns to Claude.

LiteLLM is optional, intended for Ollama and providers using separately provisioned API credentials.
