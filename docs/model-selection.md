# Model selection

Default: qwen2.5-coder:7b. A 6 GB GTX 1660 Super may require CPU offload; reduce context and evaluate latency. Inspect placement with `ollama ps` and `nvidia-smi`.

Use representative project tasks to evaluate quality and tool behavior. MCP outputs are suggestions, not authoritative results.

Measured on a GTX 1660 SUPER (6 GB): `qwen3:4b-instruct` (and `qwen3:4b`) run entirely in VRAM at about 70 tok/s; `qwen2.5-coder:7b` needs about 5.2 GB with context, partly offloads to CPU and runs at about 13 tok/s. Register a specific model with `scripts/register-mcp.sh --model <name>`.

Prefer `qwen3:4b-instruct` over `qwen3:4b`. The plain tag reports the `thinking` capability: with `LOCAL_LLM_THINK=false` it still narrates a draft inside the answer and exhausts the output limit, and with `true` it can spend the whole budget on thinking and return nothing. The instruct variant returned a clean 10-second summary on the same input.

## Context window

Measured on Ollama 0.40.16 with `qwen3:4b-instruct`: without `num_ctx` the model loads with a 4096-token context and any longer request fails with HTTP 400 (`request (37195 tokens) exceeds the available context size`); nothing is truncated silently. The server therefore sends `num_ctx` (`LOCAL_LLM_CONTEXT_TOKENS`, default 8192) and limits the source it sends to what fits. Real source code measured about 4.3 characters per token and Markdown about 4.0, so the 3 characters-per-token estimate leaves a safety margin; digit-heavy or minified text can need up to about 2 and will be rejected loudly rather than truncated. A larger context uses more VRAM: check `ollama ps`.
