# Windows setup

1. Install Python 3.11+, Git, Claude Code and Ollama.
2. Run `.scripts\setup.ps1` from this repository.
3. Run `.scripts\install-models.ps1`.
4. From your target project, run `.scripts\register-mcp.ps1 -Workspace (Get-Location).Path`.
5. Start Claude Code and inspect `/mcp`.
