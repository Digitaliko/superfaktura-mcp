"""requirements.txt (Docker, Smithery) and pyproject.toml (PyPI, uvx) list the same deps,
and server.json matches the package version."""

import json
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")  # Python 3.11+
ROOT = Path(__file__).resolve().parent.parent


def test_requirements_match_pyproject():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    reqs = [l.strip() for l in (ROOT / "requirements.txt").read_text().splitlines()
            if l.strip() and not l.startswith("#")]
    assert sorted(reqs) == sorted(project["dependencies"])


def test_server_json_matches_package():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    meta = json.loads((ROOT / "server.json").read_text())
    pkg = meta["packages"][0]
    assert meta["version"] == pkg["version"] == project["version"]
    assert pkg["identifier"] == project["name"]
    assert f"mcp-name: {meta['name']}" in (ROOT / "README.md").read_text()
