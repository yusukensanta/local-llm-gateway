#!/usr/bin/env bash
# Register the MCP server with Claude Code (user scope) for one workspace.
# Usage: scripts/register-mcp.sh [workspace-dir]   (defaults to the current directory)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
WORKSPACE="${1:-$PWD}"

[[ -x "$PYTHON" ]] || { echo "Run scripts/setup.sh first." >&2; exit 1; }
command -v claude >/dev/null || { echo "Claude Code CLI not found." >&2; exit 1; }
[[ -d "$WORKSPACE" ]] || { echo "Workspace is not a directory: $WORKSPACE" >&2; exit 1; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
# Replace a previous registration so re-running the script is idempotent.
claude mcp remove local-llm --scope user >/dev/null 2>&1 || true
claude mcp add local-llm --scope user --env "LOCAL_LLM_WORKSPACE=$WORKSPACE" -- \
  "$PYTHON" -m local_llm.server
echo "Registered local-llm for workspace: $WORKSPACE"
