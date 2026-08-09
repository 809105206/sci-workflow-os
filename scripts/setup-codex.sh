#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
trusted=false
if [[ "${1:-}" == "--trusted" ]]; then
  trusted=true
fi

if ! command -v uv >/dev/null 2>&1; then
  if [[ "$trusted" != true ]]; then
    echo "uv is missing. Re-run with --trusted to install it for the current user." >&2
    exit 2
  fi
  command -v curl >/dev/null 2>&1 || { echo "curl is required to install uv." >&2; exit 2; }
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

echo "Installing the isolated SCI Workflow OS environment..."
uv sync --extra data --extra figures --group dev

codegraph_cmd=""
if command -v npm >/dev/null 2>&1; then
  echo "Installing project-local CodeGraph 1.5.0..."
  npm install --prefix .tools/codegraph --no-save --cache /tmp/sciops-npm-cache \
    @colbymchenry/codegraph@1.5.0
  codegraph_cmd="$project_dir/.tools/codegraph/node_modules/.bin/codegraph"
elif command -v codegraph >/dev/null 2>&1; then
  codegraph_cmd="$(command -v codegraph)"
elif [[ "$trusted" == true ]]; then
  echo "Installing the pinned standalone CodeGraph build in this project..."
  bash scripts/install-codegraph.sh
  codegraph_cmd="$project_dir/.tools/codegraph-standalone/v1.5.0/bin/codegraph"
else
  echo "CodeGraph skipped because npm is missing. Core research workflow remains available." >&2
fi

if [[ -n "$codegraph_cmd" ]]; then
  if [[ -d .codegraph ]]; then
    "$codegraph_cmd" sync .
  else
    "$codegraph_cmd" init .
  fi
fi

if [[ "$trusted" == true ]]; then
  uv run sciops codex trust --yes
fi

uv run sciops doctor
uv run sciops codex resume
echo "Codex takeover environment is ready. Open this repository in Codex and state the research direction."
