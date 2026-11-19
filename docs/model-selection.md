# Model selection

Default: qwen2.5-coder:7b. A 6 GB GTX 1660 Super may require CPU offload; reduce context and evaluate latency. Inspect placement with `ollama ps` and `nvidia-smi`.

Use representative project tasks to evaluate quality and tool behavior. MCP outputs are suggestions, not authoritative results.

Measured on a GTX 1660 SUPER (6 GB): `qwen3:4b-instruct` (and `qwen3:4b`) run entirely in VRAM at about 70 tok/s; `qwen2.5-coder:7b` needs about 5.2 GB with context, partly offloads to CPU and runs at about 13 tok/s. Register a specific model with `scripts/register-mcp.sh --model <name>`.

Prefer `qwen3:4b-instruct` over `qwen3:4b`. The plain tag reports the `thinking` capability: with `LOCAL_LLM_THINK=false` it still narrates a draft inside the answer and exhausts the output limit, and with `true` it can spend the whole budget on thinking and return nothing. The instruct variant returned a clean 10-second summary on the same input.
