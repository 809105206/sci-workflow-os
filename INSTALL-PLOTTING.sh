#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

echo "SCI Workflow OS - open-source plotting setup"
echo "This installs uv, Python 3.12, Matplotlib and Plotly for the current user."

if ! command -v uv >/dev/null 2>&1; then
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required. Install curl with the system package manager, then run this file again." >&2
    exit 1
  fi
  echo "Installing uv from the official Astral installer..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv was installed but is not available in this terminal. Reopen the terminal and run this file again." >&2
  exit 1
fi

echo "Installing managed Python 3.12..."
uv python install 3.12
echo "Installing Matplotlib and Plotly in the project environment..."
uv sync --extra figures
echo "Checking plotting backends..."
uv run sciops figure doctor

echo
echo "Setup complete. No OriginPro or MATLAB installation is required."
