#!/usr/bin/env bash
# Pull Ollama models. Defaults to $OLLAMA_MODEL, else the project's default model.
# Uses the `ollama` CLI when available; otherwise (for example WSL talking to an Ollama
# running on Windows) pulls through the HTTP API at $OLLAMA_BASE_URL.
# Usage: scripts/install-models.sh [model ...]
set -euo pipefail

BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

if (($#)); then
  models=("$@")
else
  models=("${OLLAMA_MODEL:-qwen2.5-coder:7b}")
fi

pull_via_api() {
  local model="$1" response
  command -v curl >/dev/null || { echo "curl is required for the API fallback." >&2; exit 1; }
  response="$(curl -sS --connect-timeout 5 --fail-with-body -X POST "${BASE_URL%/}/api/pull" \
    -d "{\"model\":\"$model\",\"stream\":false}")" || {
    echo "Could not reach Ollama at $BASE_URL: $response" >&2
    exit 1
  }
  if [[ "$response" == *'"error"'* ]]; then
    echo "Failed to pull $model: $response" >&2
    exit 1
  fi
  echo "Pulled $model"
}

if command -v ollama >/dev/null; then
  for model in "${models[@]}"; do ollama pull "$model"; done
else
  echo "ollama CLI not found; using the HTTP API at $BASE_URL" >&2
  for model in "${models[@]}"; do pull_via_api "$model"; done
fi
