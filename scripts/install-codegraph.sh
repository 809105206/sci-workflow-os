#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="v1.5.0"

case "$(uname -s)" in
  Darwin) platform="darwin" ;;
  Linux) platform="linux" ;;
  *) echo "Unsupported CodeGraph operating system: $(uname -s)" >&2; exit 2 ;;
esac
case "$(uname -m)" in
  arm64|aarch64) architecture="arm64" ;;
  x86_64|amd64) architecture="x64" ;;
  *) echo "Unsupported CodeGraph architecture: $(uname -m)" >&2; exit 2 ;;
esac

asset="codegraph-${platform}-${architecture}.tar.gz"
case "$asset" in
  codegraph-darwin-arm64.tar.gz) expected="cf5ee435a6e44d097b2f98f2b7b8b9422bb1094844404efed82519c5da1af2cf" ;;
  codegraph-darwin-x64.tar.gz) expected="0a0ccc29bf7da9d10be1458d89d7e15c55927ae24cd95e9fa3de4bdfea059dde" ;;
  codegraph-linux-arm64.tar.gz) expected="9f17750aedf45d51f68caae39ed21d6e2a7290b2326e5c53f95a165918ebd1d8" ;;
  codegraph-linux-x64.tar.gz) expected="2ba65e87a1210b706bb1e67d5e48b5fc4a1935e43dbb3fb5f31c5597840d2e58" ;;
esac

destination="$project_dir/.tools/codegraph-standalone/$version"
executable="$destination/bin/codegraph"
if [[ -x "$executable" ]]; then
  echo "CodeGraph $version is already installed at $executable"
  exit 0
fi

command -v curl >/dev/null 2>&1 || { echo "curl is required to install CodeGraph." >&2; exit 2; }
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT
url="https://github.com/colbymchenry/codegraph/releases/download/$version/$asset"
curl -fsSL --retry 3 "$url" -o "$temporary/$asset"

if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "$temporary/$asset" | awk '{print $1}')"
else
  actual="$(shasum -a 256 "$temporary/$asset" | awk '{print $1}')"
fi
if [[ "$actual" != "$expected" ]]; then
  echo "CodeGraph checksum verification failed." >&2
  exit 1
fi

mkdir -p "$destination"
tar -xzf "$temporary/$asset" -C "$destination" --strip-components=1
[[ -x "$executable" ]] || { echo "CodeGraph executable is missing after extraction." >&2; exit 1; }
echo "Installed verified CodeGraph $version at $executable"
