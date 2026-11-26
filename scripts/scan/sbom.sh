#!/usr/bin/env bash
# The CycloneDX SBOM of the dependencies (syft over uv.lock), then a check that it is not empty and names every direct
# dependency in pyproject.toml.
#   bash scripts/scan/sbom.sh [out]     default out: sbom.cdx.json
set -uo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$here/../.." || exit 2
out=${1:-sbom.cdx.json}
command -v syft >/dev/null || { echo "FAIL sbom: syft is not installed (brew install syft, or bash scripts/scan/install.sh <dir>)"; exit 1; }
syft dir:. -q --exclude './scripts/scan/fixtures/**' --exclude './.venv/**' -o "cyclonedx-json=$out" \
  || { echo "FAIL sbom: syft stopped, no SBOM"; exit 1; }
python3 "$here/scan.py" sbom "$out" pyproject.toml
