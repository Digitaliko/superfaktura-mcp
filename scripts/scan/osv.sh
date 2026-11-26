#!/usr/bin/env bash
# Known vulnerabilities in the dependencies: OSV-Scanner over uv.lock, against a local copy of the OSV database
# (package names never leave the machine), judged by scan.py: critical and high fail, medium and low only show.
#   bash scripts/scan/osv.sh [lockfile ...]     default: every uv.lock git knows, without the test fixtures
set -uo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$here/../.." || exit 2
command -v osv-scanner >/dev/null || {
  echo "FAIL security: osv-scanner is not installed (brew install osv-scanner, or bash scripts/scan/install.sh <dir>)"; exit 1; }

locks=("$@")
if [ ${#locks[@]} -eq 0 ]; then
  while read -r f; do locks+=("$f"); done < <(git ls-files '*uv.lock' | grep -v '^scripts/scan/fixtures/')
fi
[ ${#locks[@]} -gt 0 ] || { echo "PASS security: osv-scanner: no lockfile to scan"; exit 0; }
args=(); for f in "${locks[@]}"; do args+=(-L "$f"); done

out=$(mktemp); trap 'rm -f "$out"' EXIT
# exit 1 = vulnerabilities found (scan.py judges them), anything above is the scanner failing
osv-scanner scan source --offline-vulnerabilities --download-offline-databases --format json "${args[@]}" >"$out" 2>/dev/null
code=$?
if [ $code -gt 1 ]; then
  echo "FAIL security: osv-scanner stopped with exit code $code, so the scan did not finish (it needs the internet once for its database)"
  exit 1
fi
python3 "$here/scan.py" osv "$out" "osv-scanner, ${#locks[@]} lockfile(s)"
