#!/usr/bin/env bash
# Installs the pinned osv-scanner and syft (versions.env) into one folder. Every download is a release file checked
# against the sha256 pinned in versions.env before it is used; nothing is piped into a shell.
#   bash scripts/scan/install.sh <dir>     then add <dir>/bin to PATH (CI: >> "$GITHUB_PATH")
# On a laptop: brew install osv-scanner syft
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$here/versions.env"
dir=${1:?usage: install.sh <dir>}
mkdir -p "$dir/bin" "$dir/dl"
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) plat=linux_amd64 osv_sha=$OSV_SHA256_LINUX_AMD64 syft_sha=$SYFT_SHA256_LINUX_AMD64 ;;
  Darwin-arm64) plat=darwin_arm64 osv_sha=$OSV_SHA256_DARWIN_ARM64 syft_sha=$SYFT_SHA256_DARWIN_ARM64 ;;
  *) echo "install.sh: no pinned checksum for $(uname -s)-$(uname -m); add one to versions.env" >&2; exit 1 ;;
esac

fetch() { # $1 url, $2 file, $3 sha256
  curl -sSfL --retry 3 -o "$2" "$1"
  echo "$3  $2" | sha256sum -c - 2>/dev/null || echo "$3  $2" | shasum -a 256 -c -
}

fetch "https://github.com/google/osv-scanner/releases/download/v${OSV_VERSION}/osv-scanner_${plat}" "$dir/dl/osv-scanner" "$osv_sha"
install -m 0755 "$dir/dl/osv-scanner" "$dir/bin/osv-scanner"
fetch "https://github.com/anchore/syft/releases/download/v${SYFT_VERSION}/syft_${SYFT_VERSION}_${plat}.tar.gz" "$dir/dl/syft.tar.gz" "$syft_sha"
tar -xzf "$dir/dl/syft.tar.gz" -C "$dir/bin" syft
rm -rf "$dir/dl"

"$dir/bin/osv-scanner" --version | head -1
"$dir/bin/syft" version | sed -n 2p
