# Troubleshooting

- Connection refused: check Ollama and `OLLAMA_BASE_URL`.
- WSL cannot reach Windows Ollama: use the Windows host address from `ip route show default`; check Windows Firewall.
- MCP missing: restart Claude Code, inspect `/mcp`, and verify Python path.
- File access denied: register with the intended workspace root.
- Slow inference: inspect `ollama ps`, VRAM/RAM and context length.
