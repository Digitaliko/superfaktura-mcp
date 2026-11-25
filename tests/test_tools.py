"""Every tool against mocked HTTP: method, URL and body match the SuperFaktura docs
(https://github.com/superfaktura/docs). No network."""

import json

import pytest

import server

FAKE = {"SUPERFAKTURA_EMAIL": "test@example.com", "SUPERFAKTURA_API_KEY": "fake-key",
        "SUPERFAKTURA_COUNTRY": "sandbox-sk"}


class FakeResponse:
    def __init__(self, payload=None, content=b""):
        self._payload = payload if payload is not None else {"error": 0}
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def calls(monkeypatch):
    for k, v in FAKE.items():
        monkeypatch.setenv(k, v)
    seen = []
    invoice_view = {"Invoice": {"id": "7", "token": "abc123"},
                    "Client": {"email": "client@example.com"}}

    def fake_request(method, url, json=None, headers=None, timeout=None):
        seen.append((method, url, json))
        if "/invoices/view/" in url:
            return FakeResponse(invoice_view)
        if "/invoices/pdf/" in url:
            return FakeResponse(content=b"%PDF-1.4 fake")
        return FakeResponse()

    monkeypatch.setattr(server.requests, "request", fake_request)
    return seen


def run(_tool, **kwargs):
    return getattr(server, _tool).fn(**kwargs)


BASE = "https://sandbox.superfaktura.sk/"

# (tool, kwargs, method, path) per the SuperFaktura docs, last call of the tool
CASES = [
    ("create_invoice", {"client_id": 1, "name": "T", "invoice_items": [{"name": "a", "unit_price": 1}]},
     "POST", "invoices/create"),
    ("list_invoices", {}, "GET", "invoices/index.json/page:1/"),
    ("get_invoice", {"invoice_id": 7}, "GET", "invoices/view/7.json"),
    ("edit_invoice", {"invoice_id": 7, "updates": {"name": "x"}}, "POST", "invoices/edit"),
    ("delete_invoice", {"invoice_id": 7}, "GET", "invoices/delete/7"),
    ("send_invoice", {"invoice_id": 7, "email": "a@example.com"}, "POST", "invoices/send"),
    ("mark_invoice_paid", {"invoice_id": 7, "amount": 10}, "POST", "invoice_payments/add/ajax:1/api:1"),
    ("get_invoice_pdf", {"invoice_id": 7}, "GET", "invoices/pdf/7/token:abc123"),
    ("set_invoice_language", {"invoice_id": 7, "language": "eng"}, "GET", "invoices/setinvoicelanguage/7/lang:eng"),
    ("create_client", {"name": "ACME"}, "POST", "clients/create"),
    ("list_clients", {}, "GET", "clients/index.json/page:1/"),
    ("get_client", {"client_id": 3}, "GET", "clients/view/3.json"),
    ("update_client", {"client_id": 3, "updates": {"name": "B"}}, "PATCH", "clients/edit/3"),
    ("delete_client", {"client_id": 3}, "DELETE", "clients/delete/3"),
    ("create_expense", {"name": "Paper", "amount": 10}, "POST", "expenses/add"),
    ("list_expenses", {}, "GET", "expenses/index.json/page:1/"),
    ("get_expense", {"expense_id": 5}, "GET", "expenses/view/5.json"),
    ("edit_expense", {"expense_id": 5, "updates": {"name": "y"}}, "POST", "expenses/edit"),
    ("delete_expense", {"expense_id": 5}, "GET", "expenses/delete/5"),
]


def test_every_tool_has_a_case():
    import asyncio
    tools = asyncio.run(server.mcp.get_tools())
    assert sorted(tools) == sorted(c[0] for c in CASES)


@pytest.mark.parametrize("tool,kwargs,method,path", CASES, ids=[c[0] for c in CASES])
def test_tool_endpoint(calls, tool, kwargs, method, path):
    run(tool, **kwargs)
    got_method, got_url, _ = calls[-1]
    assert got_method == method
    if path.endswith("/"):  # list tools: filters follow the prefix
        assert got_url.startswith(BASE + path)
    else:
        assert got_url == BASE + path


def test_send_invoice_body_matches_docs(calls):
    run("send_invoice", invoice_id=7, email="a@example.com", pdf_language="slo")
    assert calls[-1][2] == {"Email": {"invoice_id": 7, "to": "a@example.com", "pdf_language": "slo"}}


def test_send_invoice_defaults_to_client_email(calls):
    run("send_invoice", invoice_id=7)
    assert calls[-1][2]["Email"]["to"] == "client@example.com"


def test_pdf_is_saved_to_a_file(calls):
    # docs, invoice.md "Get invoice PDF": /[{LANGUAGE}/]invoices/pdf/{INVOICE_ID}/token:{TOKEN},
    # example https://moja.superfaktura.sk/slo/invoices/pdf/1275/token:09feb1bd
    out = run("get_invoice_pdf", invoice_id=7, language="eng")
    assert calls[-1][1] == BASE + "eng/invoices/pdf/7/token:abc123"
    with open(out["path"], "rb") as f:
        assert f.read().startswith(b"%PDF")


def test_pdf_failed_view_is_returned_as_is(calls, monkeypatch):
    monkeypatch.setattr(server.SuperFakturaClient, "get",
                        lambda self, e: {"error": "401 Unauthorized", "status": "failed"})
    assert run("get_invoice_pdf", invoice_id=7) == {"error": "401 Unauthorized", "status": "failed"}


def test_pdf_api_error_is_returned_as_is(calls, monkeypatch):
    err = {"error": 1, "error_message": "Invoice not found"}
    monkeypatch.setattr(server.SuperFakturaClient, "get", lambda self, e: err)
    assert run("get_invoice_pdf", invoice_id=7) == err


def test_repeat_last_invoice_flow(calls):
    """The 'issue this month's invoice like last time' flow the tools support:
    list the client's invoices, read the last one, create a new one from its items."""
    run("list_invoices", client_id=3, per_page=1)
    assert "client_id:3" in calls[-1][1]
    run("create_invoice", client_id=3, name="Monthly",
        invoice_items=[{"name": "Hosting", "unit_price": 50, "tax": 23}])
    assert calls[-1][2]["Invoice"]["client_id"] == 3
    assert calls[-1][2]["InvoiceItem"][0]["name"] == "Hosting"


def test_auth_header_and_sandbox_url(calls):
    c = server.SuperFakturaClient()
    assert c.base_url == "https://sandbox.superfaktura.sk"
    assert c._get_headers()["Authorization"].startswith("SFAPI email=test%40example.com&apikey=fake-key")


def test_fields_filter_rows():
    data = {"items": [{"Invoice": {"id": 1, "name": "A"}}, {"Invoice": {"id": 2, "name": "B"}}]}
    assert server._apply_fields_filter(data, ["items.Invoice.id", "items.Invoice.name"]) == [[1, "A"], [2, "B"]]
    assert server._apply_fields_filter(data, []) == []
    assert server._apply_fields_filter(data, None) is data
