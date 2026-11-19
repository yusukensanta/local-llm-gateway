# Windows setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), Git, Claude Code and Ollama.
   Python 3.14 itself is downloaded by uv when it is not already installed.
2. Run `.\scripts\setup.ps1` from this repository (add `-NoDev` to skip development tools).
3. Run `.\scripts\install-models.ps1` (or `-Models name1,name2` to pull other models).
4. From your target project, run `<path-to-repo>\scripts\register-mcp.ps1 -Workspace (Get-Location).Path`.
   Re-running the script replaces the previous registration.
5. Start Claude Code and inspect `/mcp`.

Run all quality gates with `.\scripts\check.ps1`. Every script supports `-WhatIf` where it changes state.
