#!/usr/bin/env bash
set -euo pipefail

version="${GH_VERSION:-2.97.0}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
install_dir="$project_dir/.tools/gh"
tmp_dir="$(mktemp -d)"
archive="gh_${version}_linux_amd64.tar.gz"

curl -fsSL --retry 3 "https://github.com/cli/cli/releases/download/v${version}/${archive}" -o "$tmp_dir/$archive"
curl -fsSL --retry 3 "https://github.com/cli/cli/releases/download/v${version}/gh_${version}_checksums.txt" -o "$tmp_dir/checksums.txt"

expected="$(awk -v archive="$archive" '$2 == archive {print $1}' "$tmp_dir/checksums.txt")"
actual="$(sha256sum "$tmp_dir/$archive" | awk '{print $1}')"
test -n "$expected"
test "$expected" = "$actual"

mkdir -p "$install_dir"
tar --no-same-owner -xzf "$tmp_dir/$archive" -C "$tmp_dir"
install -m 0755 "$tmp_dir/gh_${version}_linux_amd64/bin/gh" "$install_dir/gh"
"$install_dir/gh" --version
