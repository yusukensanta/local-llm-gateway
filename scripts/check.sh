#!/usr/bin/env bash
# Run every quality gate: format check, lint, type check (ty), tests with coverage.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v uv >/dev/null || { echo "uv is required." >&2; exit 1; }

uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check
uv run --locked pytest --cov
