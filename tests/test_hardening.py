"""Fixes from the pre-release review of PR #7 (C1-C9, P1, P5). Mocked HTTP, no network."""

import base64
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import server
from sandbox_env import is_sandbox_url
from test_tools import FAKE, BASE, run

ROOT = Path(__file__).resolve().parent.parent


class Resp:
    def __init__(self, status=200, payload=None, content=b"", headers=None, text=""):
        self.status_code = status
        self._payload = payload if payload is not None else {"error": 0}
        self.content = content
        self.headers = headers or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise server.requests.exceptions.HTTPError(f"{self.status_code} Error")

    def json(self):
        return self._payload


@pytest.fixture
def http(monkeypatch):
    for k, v in FAKE.items():
        monkeypatch.setenv(k, v)
    state = {"calls": [], "queue": []}

    def fake_request(method, url, json=None, headers=None, timeout=None):
        state["calls"].append((method, url, json))
        if state["queue"]:
            return state["queue"].pop(0)
        if "/invoices/view/" in url:
            return Resp(payload={"Invoice": {"id": "7", "token": "abc", "invoice_currency": "CZK"}})
        if "/invoices/pdf/" in url:
            return Resp(content=b"%PDF-1.4 fake")
        return Resp()

    monkeypatch.setattr(server.requests, "request", fake_request)
    monkeypatch.setattr(server.time, "sleep", lambda s: None)
    return state


def sf_b64(text):
    return base64.b64encode(text.encode()).decode().replace("+", "-").replace("/", "_").replace("=", ",")


# C1: values from the model never shape the URL path
@pytest.mark.parametrize("tool", ["get_invoice_pdf", "set_invoice_language"])
@pytest.mark.parametrize("lang", ["../invoices/delete/5#", "xx", "eng/../x"])
def test_c1_language_whitelist(http, tool, lang):
    r = run(tool, invoice_id=7, language=lang)
    assert r["status"] == "failed" and http["calls"] == []


def test_c1_language_any_case(http):
    run("set_invoice_language", invoice_id=7, language="ENG")
    assert http["calls"][-1][1] == BASE + "invoices/setinvoicelanguage/7/lang:eng"


def test_c1_invoice_number_with_slash(http):
    # an encoded slash never matches in SuperFaktura's path filter (sandbox); search finds it
    run("list_invoices", invoice_no_formatted="2026/001")
    assert http["calls"][-1][1].endswith(f"/search:{sf_b64('2026/001')}")


@pytest.mark.parametrize("tool,kw", [
    ("list_invoices", {"order_no": "a/b#c?d"}), ("list_invoices", {"variable": "../x"}),
    ("list_clients", {"char_filter": "a/b"}), ("list_expenses", {"type": "x#y"}),
])
def test_c1_list_values_are_quoted(http, tool, kw):
    run(tool, **kw)
    url = http["calls"][-1][1]
    value_part = url.split("index.json/", 1)[1]
    assert "#" not in value_part and "?" not in value_part and "/.." not in value_part


# C2: search takes plain text and encodes it the SuperFaktura way
@pytest.mark.parametrize("tool", ["list_invoices", "list_clients", "list_expenses"])
@pytest.mark.parametrize("text", ["Demo s.r.o.", "Košická Žilina"])
def test_c2_search_is_encoded(http, tool, text):
    run(tool, search=text)
    assert f"/search:{sf_b64(text)}" in http["calls"][-1][1]


# C4: payments carry type, currency and the documented date field
def test_c4_payment_defaults_to_invoice_currency(http):
    run("mark_invoice_paid", invoice_id=7, amount=10, payment_date="2026-11-20")
    body = http["calls"][-1][2]["InvoicePayment"]
    assert body == {"invoice_id": 7, "amount": 10, "payment_type": "transfer", "date": "2026-11-20",
                    "created": "2026-11-20", "currency": "CZK"}


def test_c4_payment_type_and_currency(http):
    run("mark_invoice_paid", invoice_id=7, amount=10, payment_type="cash", currency="EUR")
    body = http["calls"][-1][2]["InvoicePayment"]
    assert (body["payment_type"], body["currency"]) == ("cash", "EUR")
    assert len(http["calls"]) == 1  # no lookup when currency is given


# C5: importing the module never reads a .env
def test_c5_import_does_not_load_dotenv(tmp_path):
    (tmp_path / ".env").write_text("SUPERFAKTURA_EMAIL=real@example.com\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("SUPERFAKTURA_")}
    env["PYTHONPATH"] = str(ROOT)
    out = subprocess.run([sys.executable, "-c", "import os, server; print(os.getenv('SUPERFAKTURA_EMAIL'))"],
                         cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert out.stdout.strip() == "None", out.stderr


# C6: the PDF is a private file named by invoice and language
def test_c6_pdf_private_file(http):
    r = run("get_invoice_pdf", invoice_id=7, language="eng")
    name = os.path.basename(r["path"])
    assert name.startswith("superfaktura-invoice-7-eng-") and name.endswith(".pdf")
    assert stat.S_IMODE(os.stat(r["path"]).st_mode) == 0o600
    assert "this computer" in r["note"]


# C7: HTTP errors are explained; 429 is retried
def test_c7_http_error_details(http):
    http["queue"] = [Resp(status=500, text="x" * 900, headers={})]
    r = run("get_invoice", invoice_id=7)
    assert r["status"] == "failed" and r["http_status"] == 500 and len(r["body"]) == 500


def test_c7_429_retries_then_succeeds(http):
    http["queue"] = [Resp(status=429, headers={"X-RateLimit-Message": "slow down"}), Resp(payload={"ok": 1})]
    assert run("get_invoice", invoice_id=7) == {"ok": 1}
    assert len(http["calls"]) == 2


def test_c7_429_gives_up_with_message(http):
    http["queue"] = [Resp(status=429, headers={"X-RateLimit-Message": "daily limit"}) for _ in range(5)]
    r = run("get_invoice", invoice_id=7)
    assert r["http_status"] == 429 and r["rate_limit_message"] == "daily limit"


# C3 + C8: no HTTP mode in 0.1.0; PORT never switches transport
def test_c8_http_flag_is_refused():
    out = subprocess.run([sys.executable, str(ROOT / "server.py"), "--http"], capture_output=True, text=True,
                         timeout=60, env={"PATH": os.environ["PATH"]})
    assert out.returncode == 2 and "stdio" in out.stderr


def test_c3_no_per_request_credentials():
    assert not hasattr(server, "get_credentials_from_context")


# C9: the sandbox guard checks the exact host
@pytest.mark.parametrize("url,ok", [
    ("https://sandbox.superfaktura.sk", True), ("https://sandbox.superfaktura.cz/", True),
    ("https://sandbox.superfaktura.sk.evil.com", False), ("http://sandbox.superfaktura.sk", False),
    ("https://moja.superfaktura.sk", False), ("https://sandbox.superfaktura.at", False),
])
def test_c9_sandbox_guard(url, ok):
    assert is_sandbox_url(url) is ok


# P1: annotations, read-only mode, explicit recipient
WRITE = {"create_invoice", "edit_invoice", "delete_invoice", "send_invoice", "mark_invoice_paid",
         "set_invoice_language", "create_client", "update_client", "delete_client", "create_expense",
         "edit_expense", "delete_expense"}
DESTRUCTIVE = {"delete_invoice", "delete_client", "delete_expense", "send_invoice"}


def test_p1_annotations():
    import asyncio
    tools = asyncio.run(server.mcp.get_tools())
    assert len(tools) == 21
    for name, tool in tools.items():
        a = tool.annotations
        assert a is not None, name
        assert a.readOnlyHint is (name not in WRITE), name
        if name in WRITE:
            assert a.destructiveHint is (name in DESTRUCTIVE), name
    for name in ("delete_invoice", "delete_client", "delete_expense"):
        assert tools[name].description.startswith("PERMANENT"), name
    assert "credit note" in tools["delete_invoice"].description
    assert tools["send_invoice"].description.startswith("Sends a real email to the customer. Confirm with the user first.")


def test_p1_read_only_mode():
    code = "import asyncio, server; print(sorted(asyncio.run(server.mcp.get_tools())))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
                         env={"PATH": os.environ["PATH"], "PYTHONPATH": str(ROOT), "SUPERFAKTURA_READ_ONLY": "1"})
    names = set(eval(out.stdout))
    assert names and not (names & WRITE)


def test_p1_send_invoice_needs_recipient(http):
    with pytest.raises(TypeError):
        server.send_invoice.fn(invoice_id=7)


# P5: one-line credentials error; country in any case
def test_p5_credentials_error_one_line(monkeypatch):
    with pytest.raises(ValueError) as e:
        server._get_client()
    assert "\n" not in str(e.value) and "SUPERFAKTURA_API_KEY" in str(e.value)


def test_p5_country_any_case(monkeypatch):
    for k, v in FAKE.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("SUPERFAKTURA_COUNTRY", "CZ")
    assert server._get_client().base_url == "https://moje.superfaktura.cz"
