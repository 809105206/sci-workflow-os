#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
cd "$project_dir"

quarto_bin="$(command -v quarto || true)"
if [[ -z "$quarto_bin" && -x "$project_dir/.tools/quarto/bin/quarto" ]]; then
  quarto_bin="$project_dir/.tools/quarto/bin/quarto"
fi

if [[ -n "$quarto_bin" ]] && "$quarto_bin" render; then
  exit 0
fi

echo "Quarto could not render in this environment; using the Pandoc fallback." >&2
if ! command -v pandoc >/dev/null 2>&1; then
  echo "Neither a working Quarto nor Pandoc was found." >&2
  exit 1
fi

mkdir -p _site/docs _site/manuscript
pandoc --from markdown --standalone --metadata title="SCI Workflow OS" index.qmd -o _site/index.html
pandoc --from markdown --standalone --metadata title="SCI Workflow SOP" SCI.md -o _site/SCI.html
for source in docs/*.qmd; do
  output="_site/${source%.qmd}.html"
  pandoc --from markdown --standalone "$source" -o "$output"
done
pandoc --from markdown --standalone manuscript/paper.qmd -o _site/manuscript/paper.html
pandoc --from markdown manuscript/paper.qmd -o _site/manuscript/paper.docx

echo "Pandoc fallback output: $project_dir/_site"
