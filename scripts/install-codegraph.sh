#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="v1.6.0"

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
  codegraph-darwin-arm64.tar.gz) expected="1c73033512d55f67be04717e81532e8beaf7be6fb8531f51a179fa23064ad480" ;;
  codegraph-darwin-x64.tar.gz) expected="cb86a2b62ee676b62a56bf8423600e7d867e752e57f323cdc98c0f6236efd908" ;;
  codegraph-linux-arm64.tar.gz) expected="6dc935a7b8f1a61e688a578b98ea34680eb2e36d7b91db079d64f4011f1a668f" ;;
  codegraph-linux-x64.tar.gz) expected="de3391f79ed42622d937e6cd5b7642a7ea8bb7d1473607e80b879ba73ef216b0" ;;
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
