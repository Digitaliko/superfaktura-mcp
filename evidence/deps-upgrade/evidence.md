# superfaktura-mcp: dependency upgrade, fastmcp bounded below 3

> [!IMPORTANT]
> One PR, nothing deployed, nothing published. It fixes a real crash for anyone installing fresh (read-only mode with fastmcp 3+) and takes the baselined advisories from 45 to 4. Merge is Filip's; the v0.1.0 tag and PyPI publish still wait on him after this.

## Decide
### May need you
- **oss-fwd-sfa · Merge this before tagging v0.1.0**
  - Why: without the `<3` bound, a fresh `uvx` or `pip install` of this package resolves fastmcp 4.2.6 and `SUPERFAKTURA_READ_ONLY=1` crashes at start. Publishing 0.1.0 without this ships that crash.
  - Answer: `oss-fwd-sfa` merge, then tag v0.1.0 / `oss-fwd-sfb` port to fastmcp 4 first (bigger: tests use `.fn` and `get_tools`, read-only uses `remove_tool`) -> `oss-fwd-sfa`

## What happened
- `uv lock --upgrade` with the old `fastmcp>=2.6.0` range pulled fastmcp 4.2.6 and mcp 2.3: 70 tests failed (`get_tools`, `.fn` gone) and the server's read-only mode calls `mcp.remove_tool`, which fastmcp 3+ removed.
- That is not only a lockfile problem: `uvx` and `pip install` ignore `uv.lock` and resolve the `pyproject.toml` range fresh, so a user installing today already gets fastmcp 4.2.6. CI's wheel smoke test resolves fresh too, but only listed tools without read-only, so it stayed green.
- Fix: `fastmcp>=2.11.3,<3` in `pyproject.toml` and `requirements.txt` (the tested major), then `uv lock --upgrade` inside that range.
- Review: the old floor `2.6.0` was never installable with today's dependencies. fastmcp before 2.11.3 does not bound `mcp` below 2, so it pulls mcp 2.3 and fails at import (2.6.0, 2.8.0, 2.10.0, 2.11.0 tried). 2.11.3 is the first that bounds it; CI now runs the whole suite at the lowest declared versions.

## Change
| repo | file | what |
|---|---|---|
| superfaktura-mcp | `pyproject.toml`, `requirements.txt` | `fastmcp>=2.11.3,<3` |
| superfaktura-mcp | `.github/workflows/ci.yml` | new step: the whole suite at `--resolution lowest-direct` from `requirements.txt` |
| superfaktura-mcp | `uv.lock` | upgraded: fastmcp 2.14.1 -> 2.14.7, mcp 1.24 -> 1.30, cryptography 46 -> 50, urllib3 2.6.2 -> 2.8.0, certifi 2025.11.12 -> 2026.11.20, starlette 0.50 -> 1.x, python-multipart 0.0.20 -> 0.0.32+, lupa 2.6 -> 2.8, ... |
| superfaktura-mcp | `tests/test_stdio_smoke.py` | new `test_stdio_read_only_lists_only_read_tools`: starts the server with `SUPERFAKTURA_READ_ONLY=1`, expects the 9 read tools |
| superfaktura-mcp | `security-allowlist.json` | 45 baseline entries -> 4, each re-triaged with the reason it is not reachable here |
| superfaktura-mcp | `CHANGELOG.md` | 0.1.0 (still untagged): "Dependencies and supply chain" section; it also records #8 (SBOM, SECURITY.md, OSV scan), merged without a changelog line |

## Goes out
Nothing on merge (no deploy, no publish). It changes what the next PyPI release will resolve.

## Proof
- Red: the new test against the main wheel run by `uvx --refresh` (fresh deps, as CI and users run it): `FAILED test_stdio_read_only_lists_only_read_tools`, `AttributeError: 'FastMCP' object has no attribute 'remove_tool'`; fresh fastmcp there: 4.2.6.
- Green: the same against this branch's wheel: `2 passed` on Python 3.10 and 3.12.
- Full suite: `uv run --python 3.10 pytest -q` and `--python 3.12`: `121 passed, 54 skipped` each (skipped: sandbox tests without sandbox keys).
- Scan, pinned osv-scanner 2.7.1: with the allowlist `PASS ... no high or critical finding (2 medium, 4 accepted in the allowlist)`; with an empty allowlist `FAIL ... 4 high or critical findings` (before this PR: 45).
- The 4 left: fastmcp GHSA-vv7q-7jx5-f767 (OpenAPI provider) and GHSA-rww4-4w9c-7733 (OAuth proxy), both fixed only in fastmcp 3.2+ and not used by this stdio server; dnspython GHSA-45c3-73f7-pv4m and GHSA-vvf4-9x63-8xvv on Python 3.10 only (the fix needs 3.11).
- Floor, red: `uv run --no-project --isolated --resolution lowest-direct --with-requirements requirements.txt` with `fastmcp>=2.6.0`: fastmcp 2.6.0 + mcp 1.30, collection error `TypeError: cannot specify both default and default_factory`. Green with `>=2.11.3`: fastmcp 2.11.3, `121 passed, 54 skipped`.
- Raw stdio from the built wheel via `uvx --refresh`, no credentials: `initialize` ok (protocol 2025-06-18), `tools/list` 21 tools, `tools/call list_clients` returns `isError` with the credentials message. `pip install` of the wheel into a fresh 3.12 venv with `SUPERFAKTURA_READ_ONLY=1`: 9 tools.
- SBOM: `PASS sbom: sbom.cdx.json: 128 components, all 3 direct dependencies`.
- No screenshots: no UI.
