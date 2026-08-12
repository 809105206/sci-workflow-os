#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Run ./SETUP-CODEX.sh first." >&2
  exit 1
fi
uv run --frozen sciops credentials export
chmod 600 .sciops-credentials.local.json
echo "Private file: $script_dir/.sciops-credentials.local.json"
