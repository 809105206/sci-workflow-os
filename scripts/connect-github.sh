#!/usr/bin/env bash
set -euo pipefail

repo_name="${1:-sci-workflow-os}"
visibility="${2:-public}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
gh_bin="$(command -v gh || true)"

if [[ -z "$gh_bin" && -x "$project_dir/.tools/gh/gh" ]]; then
  gh_bin="$project_dir/.tools/gh/gh"
fi
if [[ -z "$gh_bin" ]]; then
  echo "GitHub CLI not found. Run scripts/install-gh.sh first." >&2
  exit 1
fi

if ! "$gh_bin" auth status >/dev/null 2>&1; then
  "$gh_bin" auth login --hostname github.com --git-protocol https --web
fi
"$gh_bin" auth setup-git

cd "$project_dir"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -b main
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  "$gh_bin" repo create "$repo_name" "--$visibility" --source . --remote origin --push
else
  git push -u origin main
fi
