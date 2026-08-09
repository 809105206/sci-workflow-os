#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
console_dir="$project_dir/console"

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js 22.13+ and npm are required: https://nodejs.org/" >&2
  exit 1
fi

if [[ ! -d "$console_dir/node_modules" ]]; then
  npm --prefix "$console_dir" install
fi

echo "Research Console: http://127.0.0.1:4173"
exec npm --prefix "$console_dir" run dev -- --host 127.0.0.1 --port 4173
