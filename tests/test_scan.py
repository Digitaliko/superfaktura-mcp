"""The dependency scan and the SBOM check (scripts/scan/). Unit tests always run; the planted-lockfile tests run
osv-scanner itself and are skipped where it is not installed (the CI `security` job installs it)."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCAN = Path(__file__).resolve().parent.parent / "scripts" / "scan"
sys.path.insert(0, str(SCAN))

import scan  # noqa: E402


def result(score, gid="GHSA-aaaa-bbbb-cccc"):
    return {
        "results": [
            {
                "source": {"path": "uv.lock"},
                "packages": [
                    {
                        "package": {"name": "left-pad", "version": "1.0.0"},
                        "vulnerabilities": [
                            {
                                "id": gid,
                                "summary": "Something bad.",
                                "affected": [
                                    {
                                        "package": {"name": "left-pad"},
                                        "ranges": [{"events": [{"introduced": "0"}, {"fixed": "1.0.1"}]}],
                                    }
                                ],
                            }
                        ],
                        "groups": [{"ids": [gid], "aliases": ["CVE-2026-1"], "max_severity": score}],
                    }
                ],
            }
        ]
    }


NONE = {"entries": [], "problems": []}


def allow(expires):
    return scan.read_allowlist(json.dumps({"accepted": [{"id": "CVE-2026-1", "reason": "no fix yet", "expires": expires}]}))


def test_critical_and_high_block_medium_shows_only():
    assert scan.judge(scan.osv(result("9.8")), NONE, "2026-11-26")["blocking"][0]["severity"] == "critical"
    assert len(scan.judge(scan.osv(result("7.5")), NONE, "2026-11-26")["blocking"]) == 1
    medium = scan.judge(scan.osv(result("5.3")), NONE, "2026-11-26")
    assert medium["blocking"] == [] and len(medium["warnings"]) == 1
    assert scan.render("x", medium)[1] is True


def test_a_finding_names_the_fixed_version():
    f = scan.osv(result("9.8"))[0]
    assert f["id"] == "GHSA-aaaa-bbbb-cccc"
    assert "move left-pad to 1.0.1" in f["fix"]
    text, ok = scan.render("deps", scan.judge([f], NONE, "2026-11-26"))
    assert not ok and text.startswith("FAIL security: deps: 1 high or critical finding")


def test_allowlist_silences_by_any_id_until_it_expires():
    live = scan.judge(scan.osv(result("9.8")), allow("2026-12-31"), "2026-11-26")
    assert live["blocking"] == [] and len(live["accepted"]) == 1
    expired = scan.judge(scan.osv(result("9.8")), allow("2026-11-25"), "2026-11-26")
    assert len(expired["blocking"]) == 1
    assert "expired on 2026-11-25" in expired["notes"][0]


def test_an_incomplete_allowlist_entry_is_reported_and_silences_nothing():
    a = scan.read_allowlist(json.dumps({"accepted": [{"id": "CVE-2026-1", "expires": "2027-01-01"}]}))
    assert a["entries"] == []
    assert "needs an id, a reason and an expiry date" in a["problems"][0]
    assert len(scan.judge(scan.osv(result("9.8")), a, "2026-11-26")["blocking"]) == 1
    assert "not valid JSON" in scan.read_allowlist("{")["problems"][0]


def test_the_sbom_check_wants_every_direct_dependency():
    deps = scan.direct_deps({"project": {"dependencies": ["fastmcp>=2.6.0", "python_dotenv>=1.0", "requests[socks]"]}})
    assert deps == ["fastmcp", "python-dotenv", "requests"]
    bom = {"components": [{"name": "fastmcp"}, {"name": "python-dotenv"}]}
    assert scan.sbom_gaps(bom, deps) == ["direct dependency requests is not in the SBOM"]
    assert scan.sbom_gaps({"components": []}, deps) == ["the SBOM lists no components"]
    assert scan.sbom_gaps({"components": [*bom["components"], {"name": "requests"}]}, deps) == []


needs_osv = pytest.mark.skipif(shutil.which("osv-scanner") is None, reason="osv-scanner not installed")


def run(lock, **env):
    return subprocess.run(
        ["bash", str(SCAN / "osv.sh"), str(SCAN / "fixtures" / "osv" / lock / "uv.lock")],
        capture_output=True, text=True, env={**os.environ, **env}, timeout=300,
    )


@needs_osv
def test_osv_sh_planted_vulnerable_lockfile_is_red_clean_one_green():
    bad = run("bad")
    assert bad.returncode == 1, bad.stdout
    assert "FAIL security:" in bad.stdout and "requests@2.19.1" in bad.stdout
    good = run("good")
    assert good.returncode == 0, good.stdout
    assert good.stdout.startswith("PASS security")


@needs_osv
def test_osv_sh_allowlist_turns_it_green_its_expiry_red_again(tmp_path):
    f = tmp_path / "allow.json"
    f.write_text(json.dumps({"accepted": [{"id": "GHSA-x84v-xcm2-53pg", "reason": "test", "expires": "2027-01-15"}]}))
    assert run("bad", SCAN_ALLOWLIST=str(f), SCAN_TODAY="2027-01-15").returncode == 0
    after = run("bad", SCAN_ALLOWLIST=str(f), SCAN_TODAY="2027-01-16")
    assert after.returncode == 1
    assert "expired on 2027-01-15" in after.stdout
