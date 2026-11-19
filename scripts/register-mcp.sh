#!/usr/bin/env bash
# Register the MCP server with Claude Code (user scope) for one workspace.
# Usage: scripts/register-mcp.sh [--model NAME] [--force] [workspace-dir]
#   workspace-dir defaults to the current directory.
#   --model sets OLLAMA_MODEL for the registered server (default: the server's built-in model).
#   --force registers even when the local-llm plugin is installed (which duplicates the server).
set -euo pipefail

usage() { echo "Usage: $0 [--model NAME] [--force] [workspace-dir]" >&2; exit 2; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"
MODEL=""
WORKSPACE=""
FORCE=0
PLUGIN_ID="local-llm@local-llm-gateway"

while (($#)); do
  case "$1" in
    --model)
      (($# >= 2)) || usage
      MODEL="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
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

# The plugin already provides this MCP server; a second registration would show up twice.
if ((FORCE == 0)); then
  plugins="$(claude plugin list 2>/dev/null || true)"
  if grep -qF "$PLUGIN_ID" <<<"$plugins"; then
    echo "The plugin $PLUGIN_ID is installed and already provides this MCP server." >&2
    echo "Registering it again would duplicate the tools. Re-run with --force to register anyway," >&2
    echo "or remove the plugin first: claude plugin uninstall $PLUGIN_ID" >&2
    exit 1
  fi
fi

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
env_args=(--env "LOCAL_LLM_WORKSPACE=$WORKSPACE")
[[ -z "$MODEL" ]] || env_args+=(--env "OLLAMA_MODEL=$MODEL")

# Replace a previous registration so re-running the script is idempotent.
claude mcp remove local-llm --scope user >/dev/null 2>&1 || true
claude mcp add local-llm --scope user "${env_args[@]}" -- "$PYTHON" -m local_llm.server
echo "Registered local-llm for workspace: $WORKSPACE${MODEL:+ (model: $MODEL)}"
