# superfaktura-mcp: PyPI release workflow for v0.1.0

> [!IMPORTANT]
> One PR, nothing published. It adds a Trusted Publishing workflow that uploads to PyPI when a GitHub release is published, dates 0.1.0 to 2026-11-27 and makes the server report 0.1.0. PyPI only accepts the upload after Filip adds the pending publisher on pypi.org; then merge and one `gh release create` line.

## Decide
### Needs you
- **sfmcp-rel-b · Release v0.1.0 to PyPI**
  - Why: publishing is Filip's; the workflow cannot upload until PyPI trusts it.
  - Answer: (1) pypi.org pending publisher, (2) merge, (3) `gh release create` (exact steps in the PR) / hold the release -> `sfmcp-rel-b` all three

## What happened
- Nothing could publish the package: no workflow had PyPI access, and the brief rules out tokens.
- `publish.yml` runs on a published release: checks the tag is `v` + the pyproject version, runs the suite, builds, smoke-tests the wheel through `uvx`, then a separate `pypi` job (environment `pypi`, only job with `id-token: write`) uploads with `pypa/gh-action-pypi-publish` v1.14.3, pinned to its commit.
- Release, not a tag push: `gh release create` makes the tag and the release in one step, and `sbom.yml` already attaches the SBOM on the same event. One trigger means one upload.
- `initialize` returned `serverInfo.version` 2.14.7 (fastmcp's). `server.__version__ = "0.1.0"` is passed to `FastMCP`, and a test keeps it equal to pyproject (it also works in the Docker image, which runs `server.py` without package metadata).
- CHANGELOG 0.1.0 dated 2026-11-27 (was 2026-11-25), two lines added. pyproject, server.json and server.py are all 0.1.0.

## Change
| repo | file | what |
|---|---|---|
| superfaktura-mcp | `.github/workflows/publish.yml` | new: release -> version check, tests, build, wheel smoke, PyPI via OIDC |
| superfaktura-mcp | `server.py` | `__version__ = "0.1.0"`, `FastMCP(..., version=__version__)` |
| superfaktura-mcp | `tests/test_stdio_smoke.py` | new `test_initialize_reports_the_package_version` |
| superfaktura-mcp | `tests/test_packaging.py` | new `test_server_version_matches_package` |
| superfaktura-mcp | `CHANGELOG.md` | 0.1.0 dated 2026-11-27, publish and version lines |

## Goes out
Nothing on merge. The workflow runs only when a release is published; that and the PyPI publisher are Filip's.

## Proof
- Red: `test_initialize_reports_the_package_version` on main code: `AssertionError: assert ('superfaktura', '2.14.7') == ('superfaktura', '0.1.0')`.
- Green: `uv run pytest -q`: `123 passed, 54 skipped` (skipped: sandbox tests without sandbox keys).
- `uv build`: `superfaktura_mcp-0.1.0.tar.gz` and `superfaktura_mcp-0.1.0-py3-none-any.whl`; `twine check`: PASSED for both.
- The wheel run by `uvx --isolated --from dist/superfaktura_mcp-0.1.0-py3-none-any.whl superfaktura-mcp` (`SMOKE_COMMAND`): `3 passed` (initialize reports 0.1.0, 21 tools, 9 in read-only mode).
- `actionlint .github/workflows/publish.yml`: no findings.
- Not run: the publish job itself; it needs the PyPI publisher and a release.
- No screenshots: no UI.
