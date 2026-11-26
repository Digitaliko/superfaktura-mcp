#!/usr/bin/env python3
"""The verdict of the dependency scan and the SBOM check, in plain lines.

Python port of the scanner verdict used in app-template and stack (scripts/scan/scan.mjs, itself adapted from the
GreenWay App Factory's scripts/scan/findings.ts). Standard library only.

    python3 scripts/scan/scan.py osv <osv-result.json> <label>       critical/high block (exit 1), medium/low show
    python3 scripts/scan/scan.py sbom <sbom.cdx.json> <pyproject.toml>   every direct dependency is in the SBOM

The allowlist (security-allowlist.json at the repo root, SCAN_ALLOWLIST overrides) silences one advisory id until its
expiry date. An expired or incomplete entry silences nothing, so the scan turns red again on that day.
    {"accepted": [{"id": "GHSA-...", "reason": "why it cannot be fixed yet", "expires": "YYYY-MM-DD"}]}
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

BLOCKS = ("critical", "high")
RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
MAX_LINES = 15


def one_line(s, limit=160):
    t = " ".join(str(s or "").split())
    return t if len(t) <= limit else t[: limit - 1] + "…"


def from_score(score: float) -> str:
    """CVSS base score to a word, the GitHub advisory bands."""
    if score >= 9:
        return "critical"
    if score >= 7:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _sev(word):
    w = str(word or "").lower()
    if w == "moderate":
        return "medium"
    return w if w in RANK else None


def osv(d: dict) -> list[dict]:
    """osv-scanner --format json to findings, one per advisory group and package version."""
    out = []
    for res in (d or {}).get("results") or []:
        path = (res.get("source") or {}).get("path", "")
        try:
            path = os.path.relpath(path) if os.path.isabs(path) else path
        except ValueError:
            pass
        for p in res.get("packages") or []:
            name = (p.get("package") or {}).get("name")
            version = (p.get("package") or {}).get("version")
            vulns = p.get("vulnerabilities") or []
            for g in p.get("groups") or [{"ids": [v.get("id") for v in vulns]}]:
                ids = list(dict.fromkeys([*(g.get("ids") or []), *(g.get("aliases") or [])]))
                vs = [v for v in vulns if v.get("id") in ids]
                words = [s for s in (_sev((v.get("database_specific") or {}).get("severity")) for v in vs) if s]
                try:
                    words.append(from_score(float(g.get("max_severity"))))
                except (TypeError, ValueError):
                    pass
                # no severity at all: medium, shown but not blocking
                severity = min(words, key=RANK.get) if words else "medium"
                fixed = [
                    e["fixed"]
                    for v in vs
                    for a in v.get("affected") or []
                    if (a.get("package") or {}).get("name") == name
                    for r in a.get("ranges") or []
                    for e in r.get("events") or []
                    if e.get("fixed")
                ]
                first = vs[0] if vs else {}
                out.append(
                    {
                        "id": next((i for i in ids if i.startswith("GHSA-")), ids[0] if ids else "?"),
                        "ids": ids,
                        "severity": severity,
                        "where": f"{name}@{version} in {path}",
                        "title": one_line(first.get("summary") or first.get("details") or "known vulnerability"),
                        "fix": f"move {name} to {fixed[-1]} or later"
                        if fixed
                        else f"no fixed version yet: drop {name}, or accept it in security-allowlist.json",
                    }
                )
    return out


def read_allowlist(text: str | None) -> dict:
    """The allowlist, checked: an entry without an id, a reason or a valid expiry date is reported, never applied."""
    if text is None:
        return {"entries": [], "problems": []}
    try:
        d = json.loads(text)
    except ValueError:
        return {"entries": [], "problems": ["security-allowlist.json is not valid JSON"]}
    entries, problems = [], []
    for i, e in enumerate(d.get("accepted") or [] if isinstance(d, dict) else []):
        ok = isinstance(e, dict) and isinstance(e.get("id"), str) and e["id"]
        ok = ok and isinstance(e.get("reason"), str) and e["reason"].strip()
        ok = ok and isinstance(e.get("expires"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["expires"])
        if ok:
            try:
                dt.date.fromisoformat(e["expires"])
            except ValueError:
                ok = False
        if ok:
            entries.append(e)
        else:
            problems.append(f"security-allowlist.json entry {i + 1} needs an id, a reason and an expiry date (YYYY-MM-DD)")
    return {"entries": entries, "problems": problems}


def judge(findings: list[dict], allow: dict, today: str) -> dict:
    v = {"blocking": [], "warnings": [], "accepted": [], "notes": list(allow["problems"])}
    expired = {}
    for f in findings:
        match = [e for e in allow["entries"] if e["id"] in f["ids"]]
        for e in match:
            if e["expires"] < today:
                expired[e["id"]] = e["expires"]
        if any(e["expires"] >= today for e in match):
            v["accepted"].append(f)
        elif f["severity"] in BLOCKS:
            v["blocking"].append(f)
        else:
            v["warnings"].append(f)
    for i, d in expired.items():
        v["notes"].append(f"allowlist entry {i} expired on {d}: it no longer silences anything")
    for k in ("blocking", "warnings"):
        v[k].sort(key=lambda f: (RANK[f["severity"]], f["where"]))
    return v


def render(label: str, v: dict) -> tuple[str, bool]:
    def count(s):
        return sum(1 for f in v["warnings"] if f["severity"] == s)

    rest = [x for x in (count("medium") and f"{count('medium')} medium", count("low") and f"{count('low')} low",
                        v["accepted"] and f"{len(v['accepted'])} accepted in the allowlist") if x]
    tail = f" ({', '.join(rest)})" if rest else ""
    n = len(v["blocking"])
    ok = n == 0
    out = [f"PASS security: {label}: no high or critical finding{tail}" if ok
           else f"FAIL security: {label}: {n} high or critical finding{'' if n == 1 else 's'}{tail}"]
    out += [f"     {f['severity']} {f['where']} {f['id']}: {f['title']} Fix: {f['fix']}" for f in v["blocking"]]
    out += [f"     note: {note}" for note in v["notes"]]
    out += [f"     {f['severity']} {f['where']} {f['id']}: {f['title']}" for f in v["warnings"][:MAX_LINES]]
    if len(v["warnings"]) > MAX_LINES:
        out.append(f"     ... and {len(v['warnings']) - MAX_LINES} more medium or low")
    return "\n".join(out), ok


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def direct_deps(pyproject: dict) -> list[str]:
    """[project].dependencies names, normalised (PEP 503)."""
    deps = (pyproject.get("project") or {}).get("dependencies") or []
    return sorted({_norm(re.split(r"[\s<>=!~;\[(@]", d.strip(), maxsplit=1)[0]) for d in deps if d.strip()})


def sbom_gaps(bom: dict, deps: list[str]) -> list[str]:
    """What a CycloneDX SBOM lacks: an empty component list, or a direct dependency that is not in it."""
    comps = (bom or {}).get("components") or []
    if not comps:
        return ["the SBOM lists no components"]
    names = {_norm(c.get("name", "")) for c in comps}
    return [f"direct dependency {d} is not in the SBOM" for d in deps if d not in names]


def _load_toml(path: str) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def main(argv: list[str]) -> int:
    cmd, file, rest = (argv + [None, None])[0], (argv + [None, None])[1], argv[2:]
    try:
        data = json.loads(Path(file or "").read_text())
    except (OSError, ValueError):
        print(f"FAIL {'sbom' if cmd == 'sbom' else 'security'}: {file} is missing or not JSON, so the step did not finish")
        return 1
    if cmd == "osv" and rest:
        list_file = os.environ.get("SCAN_ALLOWLIST") or str(Path(__file__).resolve().parents[2] / "security-allowlist.json")
        allow = read_allowlist(Path(list_file).read_text() if Path(list_file).exists() else None)
        today = os.environ.get("SCAN_TODAY") or dt.date.today().isoformat()
        text, ok = render(rest[0], judge(osv(data), allow, today))
        print(text)
        return 0 if ok else 1
    if cmd == "sbom" and rest:
        deps = direct_deps(_load_toml(rest[0]))
        gaps = sbom_gaps(data, deps)
        n = len(data.get("components") or [])
        print(f"FAIL sbom: {file}" if gaps else f"PASS sbom: {file}: {n} components, all {len(deps)} direct dependencies")
        for g in gaps:
            print(f"     {g}")
        return 1 if gaps else 0
    print("usage: scan.py osv <result.json> <label> | scan.py sbom <sbom.cdx.json> <pyproject.toml>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
