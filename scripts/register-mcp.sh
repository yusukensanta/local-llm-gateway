#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
WORKSPACE="${1:-$PWD}"
[[ -x "$PYTHON" ]] || { echo "Run scripts/setup.sh first." >&2; exit 1; }
command -v claude >/dev/null || { echo "Claude Code CLI not found." >&2; exit 1; }
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
claude mcp add local-llm --scope user --env "LOCAL_LLM_WORKSPACE=$WORKSPACE" -- "$PYTHON" -m local_llm.server
