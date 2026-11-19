# Model selection

Default: qwen2.5-coder:7b. A 6 GB GTX 1660 Super may require CPU offload; reduce context and evaluate latency. Inspect placement with `ollama ps` and `nvidia-smi`.

Use representative project tasks to evaluate quality and tool behavior. MCP outputs are suggestions, not authoritative results.

Measured on a GTX 1660 SUPER (6 GB): `qwen3:4b` runs entirely in VRAM at about 70 tok/s; `qwen2.5-coder:7b` needs about 5.2 GB with context, partly offloads to CPU and runs at about 13 tok/s. Register a specific model with `scripts/register-mcp.sh --model <name>`.
