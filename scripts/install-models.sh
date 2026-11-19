#!/usr/bin/env bash
# Pull Ollama models. Defaults to the project's default model.
# Usage: scripts/install-models.sh [model ...]
set -euo pipefail

command -v ollama >/dev/null || { echo "Install Ollama first." >&2; exit 1; }

if (($#)); then
  models=("$@")
else
  models=("${OLLAMA_MODEL:-qwen2.5-coder:7b}")
fi

for model in "${models[@]}"; do
  ollama pull "$model"
done
