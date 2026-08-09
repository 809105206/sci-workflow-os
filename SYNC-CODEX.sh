#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
if [[ -x .tools/codegraph/node_modules/.bin/codegraph ]]; then
  .tools/codegraph/node_modules/.bin/codegraph sync .
elif command -v codegraph >/dev/null 2>&1; then
  codegraph sync .
else
  echo "CodeGraph is not installed. Run SETUP-CODEX.sh first." >&2
fi
uv run sciops codex resume
