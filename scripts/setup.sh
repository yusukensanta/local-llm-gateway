#!/usr/bin/env bash
# Create .venv with Python 3.14 and install locked dependencies using uv.
# Usage: scripts/setup.sh [--no-dev]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v uv >/dev/null || {
  echo "uv is required. Install it: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
}

# uv downloads a managed CPython 3.14 automatically if none is installed.
uv sync --locked --python 3.14 "$@"
echo "Setup complete. Run tests with: bash scripts/check.sh"
