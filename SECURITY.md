# Security policy

## Supported versions

| Version | Supported |
|---|---|
| latest release (currently 0.1.x) and `main` | yes |
| older releases | no, please upgrade |

## Reporting a vulnerability

Please report a vulnerability privately, never in a public issue, pull request or discussion.

- Email: [security@ mailbox: Filip creates]
- Or GitHub private vulnerability reporting: the "Report a vulnerability" button under this repository's Security tab, when it is turned on.

Include what is affected (version or commit), how to reproduce it, and the impact you see. Tell us if you want to be credited.

## What happens next

- We acknowledge your report within 3 working days.
- We aim to fix critical issues within 30 days and tell you when the fix is out. These are our targets, not a legal deadline.
- We publish an advisory once a fix is available, and credit you if you want.
- For a product in scope of the EU Cyber Resilience Act, an actively exploited vulnerability is reported to ENISA's single reporting platform within 24 hours of us becoming aware of it.

## How this repository checks its dependencies

- Every pull request runs OSV-Scanner over `uv.lock` (`scripts/scan/osv.sh`, pinned in `scripts/scan/versions.env`). A critical or high advisory fails the check. An advisory that cannot be fixed yet goes in `security-allowlist.json` with a reason and an expiry date; on that date it fails again.
- Every push to `main` and every published release builds a CycloneDX SBOM (`scripts/scan/sbom.sh`, syft), kept as a workflow artifact and attached to the release as `sbom.cdx.json`.
