#!/usr/bin/env bash
# Start the MCP server on stdio (normally launched by Claude Code, not by hand).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
[[ -x "$PYTHON" ]] || { echo "Run scripts/setup.sh first." >&2; exit 1; }
exec "$PYTHON" -m local_llm.server
