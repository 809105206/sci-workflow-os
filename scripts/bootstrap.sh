#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
cd "$project_dir"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1 && [[ ! -x "$project_dir/.tools/gh/gh" ]]; then
  "$project_dir/scripts/install-gh.sh"
fi

if ! command -v quarto >/dev/null 2>&1 && [[ ! -x "$project_dir/.tools/quarto/bin/quarto" ]]; then
  "$project_dir/scripts/install-quarto.sh"
fi

uv sync --extra data --extra figures --group dev
uv run sciops audit templates/project
uv run pytest

echo "SCI Workflow OS is ready. Run: uv run sciops doctor"
