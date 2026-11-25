"""Shared setup for the sandbox suites: SANDBOX_SUPERFAKTURA_* only, sandbox URLs only.

SANDBOX_LOG=<file> appends one JSON line per tool call (tool, args, short result) for evidence."""

import json
import os
import time
from urllib.parse import urlparse

import pytest

import server

EMAIL = os.getenv("SANDBOX_SUPERFAKTURA_EMAIL")
KEY = os.getenv("SANDBOX_SUPERFAKTURA_API_KEY")
URL = os.getenv("SANDBOX_SUPERFAKTURA_URL", "https://sandbox.superfaktura.sk").rstrip("/")
COMPANY_ID = os.getenv("SANDBOX_SUPERFAKTURA_COMPANY_ID")
SEND_TO = os.getenv("SANDBOX_SUPERFAKTURA_SEND_TO")
LOG = os.getenv("SANDBOX_LOG")

SANDBOX_HOSTS = {"sandbox.superfaktura.sk", "sandbox.superfaktura.cz"}


def is_sandbox_url(url):
    raise NotImplementedError


skip_without_sandbox = pytest.mark.skipif(not (EMAIL and KEY), reason="no SuperFaktura sandbox credentials")
STAMP = time.strftime("%Y%m%d-%H%M%S")


@pytest.fixture(autouse=True, scope="module")
def sandbox_env():
    assert URL.startswith("https://sandbox.superfaktura."), "SANDBOX_SUPERFAKTURA_URL must be a sandbox URL"
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("SUPERFAKTURA_EMAIL", EMAIL)
        mp.setenv("SUPERFAKTURA_API_KEY", KEY)
        mp.setenv("SUPERFAKTURA_API_URL", URL)
        if COMPANY_ID:
            mp.setenv("SUPERFAKTURA_COMPANY_ID", COMPANY_ID)
        else:
            mp.delenv("SUPERFAKTURA_COMPANY_ID", raising=False)
        assert server._get_client().base_url.startswith("https://sandbox.superfaktura.")
        yield


def run(_tool, **kwargs):
    result = getattr(server, _tool).fn(**kwargs)
    if LOG:
        with open(LOG, "a") as f:
            f.write(json.dumps({"tool": _tool, "args": kwargs, "result": json.dumps(result, ensure_ascii=False)[:300]},
                               ensure_ascii=False, default=str) + "\n")
    return result


def ok(resp):
    assert isinstance(resp, (dict, list)), resp
    if isinstance(resp, dict):
        assert resp.get("status") != "failed", resp
        assert resp.get("error") in (None, 0, "0", False), resp
    return resp


def sf_error(resp):
    """True when the result is an error the agent can read (not a crash)."""
    return isinstance(resp, dict) and (resp.get("status") == "failed" or resp.get("error") not in (None, 0, "0", False))
