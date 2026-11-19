#!/usr/bin/env bash
set -euo pipefail
command -v ollama >/dev/null || { echo "Install Ollama first." >&2; exit 1; }
if (($#)); then models=("$@"); else models=("qwen2.5-coder:7b"); fi
for model in "${models[@]}"; do ollama pull "$model"; done
