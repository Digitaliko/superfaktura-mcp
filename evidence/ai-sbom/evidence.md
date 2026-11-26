# SBOM, SECURITY.md and a pinned dependency scan for superfaktura-mcp

> [!IMPORTANT]
> One PR, nothing deployed, nothing leaves. Two things wait on Filip: the baseline allowlist (`ai-sbom-superfaktura-mcpa`) and the `security@` mailbox.

## Decide
### May need you
- **ai-sbom-superfaktura-mcpa · Accept the baseline allowlist until 2027-01-15**
  - Why: 45 critical/high advisories already sit in `uv.lock`. A blocking scan would fail every PR today, so they are allowlisted as a dated baseline (each entry names the package and says "baseline"). New advisories fail from this PR on; on 2027-01-16 the baseline expires and the scan is red until they are upgraded or re-triaged.
  - Answer: `ai-sbom-superfaktura-mcpa` keep the baseline as is / `ai-sbom-superfaktura-mcpb` upgrade the dependencies in this PR first -> `ai-sbom-superfaktura-mcpa`
- **ai-sbom-superfaktura-mcp-mail · The `security@` address is a placeholder**
  - Why: SECURITY.md says `[security@ mailbox: Filip creates]`; the mailbox does not exist. Create it (or drop the line and keep GitHub private reporting only), and turn on GitHub private vulnerability reporting for this public repo (a repo setting: Filip).

## What happened
- CRA hygiene from `rooms/team/legal/ai-act-cra/enforcement-plan.md` B1-B3 (approved as `ai-act-kb-5a`).
- B1: a CycloneDX SBOM (syft 1.57.1, pinned with sha256) on every push to `main` as a workflow artifact and on every release as a release asset; the step fails when the SBOM is empty or misses a direct dependency.
- B2: `SECURITY.md`: private reporting, 3 working days to acknowledge, 30 days target for critical fixes, supported versions, CRA 24 h line.
- B3: OSV-Scanner 2.7.1 (same pins and checksums as the GreenWay App Factory's `scripts/scan/versions.env`) over `uv.lock` on every PR, critical and high fail; the findings parser and the expiring allowlist are adapted from GreenWay's `scripts/scan/findings.ts`.
- Checked first that both tools read `uv.lock`: syft finds every direct dependency in it, osv-scanner reads it as a lockfile.

## Change
| repo | file | what |
|---|---|---|
| superfaktura-mcp | `.github/workflows/ci.yml` | new `security` job (pinned install, scan, scanner tests) |
| superfaktura-mcp | `.github/workflows/sbom.yml` | SBOM on push to main (artifact) and on a published release (asset) |
| superfaktura-mcp | `scripts/scan/*` | versions.env, install.sh, osv.sh, sbom.sh, scan.py (Python port of the parser, stdlib only), fixtures |
| superfaktura-mcp | `tests/test_scan.py` | unit + planted lockfile tests |
| superfaktura-mcp | `security-allowlist.json` | the dated baseline (45 ids) |
| superfaktura-mcp | `SECURITY.md` | vulnerability policy, supported versions table |

## Goes out
Nothing leaves. The wheel is unchanged (`py-modules = ["server"]`, scripts are not packaged).

## Proof
- Planted vulnerable lockfile (`scripts/scan/fixtures/osv/bad/`) red, clean one green, the allowlist turns it green and its expiry red again: scanner tests, run locally with the pinned osv-scanner.
- `uv run --python 3.12 pytest -q tests/test_scan.py`: 7 passed; same on 3.10.
- `bash scripts/scan/osv.sh`: `PASS ... (34 medium, 6 low, 45 accepted in the allowlist)`; with `SCAN_TODAY=2027-01-16`: `FAIL ... 45 high or critical findings`.
- `bash scripts/scan/sbom.sh`: `PASS sbom: 98 components, all 3 direct dependencies`.
- The baseline is in the lock only: `uvx superfaktura-mcp` resolves fresh versions from the `pyproject.toml` ranges, so users are not pinned to them.
- Full suite: `uv run --python 3.12 pytest -q`: 122 passed, 52 skipped (the sandbox tests without sandbox keys). `wizrd pr gate` ran only its doc tier here (the repo has no package.json, so the gate never runs code checks), so the pytest runs above are the code proof; `tests/test_scan.py` fails on `main` by construction (`import scan`: no `scripts/scan/scan.py` there).
- `actionlint` clean on the new and changed workflows (one SC2086 info in an existing line that is already on `main`).
- CI: not run yet; it runs on the PR. If Actions are billing-limited, the local runs above are the proof.
