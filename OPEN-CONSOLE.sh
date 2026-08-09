#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
offline_app="$script_dir/SCI-WORKFLOW-CONSOLE.html"
if [[ -f "$offline_app" ]]; then
  if command -v open >/dev/null 2>&1; then
    open "$offline_app"
    exit 0
  fi
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$offline_app"
    exit 0
  fi
fi
exec python3 "$script_dir/scripts/serve-console.py"
