#!/usr/bin/env bash
# Register the MCP server with Claude Code (user scope) for one workspace.
# Usage: scripts/register-mcp.sh [--model NAME] [workspace-dir]
#   workspace-dir defaults to the current directory.
#   --model sets OLLAMA_MODEL for the registered server (default: the server's built-in model).
set -euo pipefail

usage() { echo "Usage: $0 [--model NAME] [workspace-dir]" >&2; exit 2; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
MODEL=""
WORKSPACE=""

while (($#)); do
  case "$1" in
    --model)
      (($# >= 2)) || usage
      MODEL="$2"
      shift 2
      ;;
    -h | --help) usage ;;
    -*) echo "Unknown option: $1" >&2; usage ;;
    *)
      [[ -z "$WORKSPACE" ]] || usage
      WORKSPACE="$1"
      shift
      ;;
  esac
done
WORKSPACE="${WORKSPACE:-$PWD}"

[[ -x "$PYTHON" ]] || { echo "Run scripts/setup.sh first." >&2; exit 1; }
command -v claude >/dev/null || { echo "Claude Code CLI not found." >&2; exit 1; }
[[ -d "$WORKSPACE" ]] || { echo "Workspace is not a directory: $WORKSPACE" >&2; exit 1; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
env_args=(--env "LOCAL_LLM_WORKSPACE=$WORKSPACE")
[[ -z "$MODEL" ]] || env_args+=(--env "OLLAMA_MODEL=$MODEL")

# Replace a previous registration so re-running the script is idempotent.
claude mcp remove local-llm --scope user >/dev/null 2>&1 || true
claude mcp add local-llm --scope user "${env_args[@]}" -- "$PYTHON" -m local_llm.server
echo "Registered local-llm for workspace: $WORKSPACE${MODEL:+ (model: $MODEL)}"
