"""requirements.txt (Docker, Smithery) and pyproject.toml (PyPI, uvx) list the same deps,
and server.json and server.__version__ match the package version."""

import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib
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


def test_server_version_matches_package():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert f'__version__ = "{project["version"]}"' in (ROOT / "server.py").read_text()
