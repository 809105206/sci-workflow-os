#!/usr/bin/env bash
set -euo pipefail

version="${QUARTO_VERSION:-1.10.18}"
expected_sha256="${QUARTO_SHA256:-afad071b5bd22c02f2d300695743189d3650e0537a53073e654b630cff2b0c73}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
install_dir="$project_dir/.tools/quarto"
tmp_dir="$(mktemp -d)"
archive="quarto-${version}-linux-amd64.tar.gz"

curl -fsSL --retry 3 "https://github.com/quarto-dev/quarto-cli/releases/download/v${version}/${archive}" -o "$tmp_dir/$archive"
actual_sha256="$(sha256sum "$tmp_dir/$archive" | awk '{print $1}')"
test "$actual_sha256" = "$expected_sha256"

mkdir -p "$install_dir"
tar --no-same-owner -xzf "$tmp_dir/$archive" -C "$install_dir" --strip-components=1
"$install_dir/bin/quarto" --version
