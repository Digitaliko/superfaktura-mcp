"""Every tool end to end against a SuperFaktura SANDBOX account.

Runs only when SANDBOX_SUPERFAKTURA_EMAIL and SANDBOX_SUPERFAKTURA_API_KEY are set;
skipped otherwise. It refuses any base URL that is not sandbox.superfaktura.*, so a
production key can never be used by mistake. Creates a test client, invoices and an
expense, and deletes them at the end.

    SANDBOX_SUPERFAKTURA_EMAIL=... SANDBOX_SUPERFAKTURA_API_KEY=... \\
    [SANDBOX_SUPERFAKTURA_COMPANY_ID=...] [SANDBOX_SUPERFAKTURA_URL=https://sandbox.superfaktura.cz] \\
    uv run --with pytest pytest tests/test_sandbox.py -v

send_invoice sends a real email, so it runs only with SANDBOX_SUPERFAKTURA_SEND_TO set.
"""

import pytest

from sandbox_env import SEND_TO, STAMP, EMAIL, ok, run, sandbox_env, skip_without_sandbox  # noqa: F401

pytestmark = skip_without_sandbox

STATE = {}


def test_create_client():
    r = ok(run("create_client", name=f"MCP sandbox test {STAMP}", email=EMAIL))
    STATE["client_id"] = int(r["data"]["Client"]["id"])


def test_list_clients():
    ok(run("list_clients", per_page=5))


def test_get_client():
    r = ok(run("get_client", client_id=STATE["client_id"]))
    assert str(r["Client"]["id"]) == str(STATE["client_id"])


def test_update_client():
    ok(run("update_client", client_id=STATE["client_id"], updates={"city": "Bratislava"}))


def test_create_invoice():
    r = ok(run("create_invoice", client_id=STATE["client_id"], name=f"MCP test {STAMP}",
               invoice_items=[{"name": "Hosting", "unit_price": 50, "quantity": 1, "tax": 23}]))
    STATE["invoice_id"] = int(r["data"]["Invoice"]["id"])


def test_list_invoices():
    r = ok(run("list_invoices", client_id=STATE["client_id"], per_page=5))
    assert r.get("items"), r


def test_get_invoice():
    r = ok(run("get_invoice", invoice_id=STATE["invoice_id"]))
    STATE["last_items"] = r["InvoiceItem"]


def test_repeat_last_invoice():
    """'Issue this month's invoice like last time': a new invoice from the last one's items."""
    items = [{k: i[k] for k in ("name", "unit_price", "quantity", "tax") if k in i} for i in STATE["last_items"]]
    r = ok(run("create_invoice", client_id=STATE["client_id"], name=f"MCP repeat {STAMP}", invoice_items=items))
    STATE["repeat_id"] = int(r["data"]["Invoice"]["id"])
    assert r["data"]["InvoiceItem"][0]["name"] == "Hosting"


def test_edit_invoice():
    ok(run("edit_invoice", invoice_id=STATE["invoice_id"], updates={"comment": "edited by MCP test"}))


def test_set_invoice_language():
    ok(run("set_invoice_language", invoice_id=STATE["invoice_id"], language="eng"))


def test_get_invoice_pdf():
    for lang in (None, "eng"):  # eng: the documented /eng/invoices/pdf/... prefix
        r = ok(run("get_invoice_pdf", invoice_id=STATE["invoice_id"], language=lang))
        with open(r["path"], "rb") as f:
            assert f.read(4) == b"%PDF"


def test_mark_invoice_paid():
    ok(run("mark_invoice_paid", invoice_id=STATE["invoice_id"], amount=61.5))


@pytest.mark.skipif(not SEND_TO, reason="SANDBOX_SUPERFAKTURA_SEND_TO not set (sends a real email)")
def test_send_invoice():
    ok(run("send_invoice", invoice_id=STATE["invoice_id"], email=SEND_TO))


def test_create_expense():
    r = ok(run("create_expense", name=f"MCP expense {STAMP}", amount=12.5, currency="EUR"))
    STATE["expense_id"] = int(r["data"]["Expense"]["id"])


def test_list_expenses():
    ok(run("list_expenses", per_page=5))


def test_get_expense():
    ok(run("get_expense", expense_id=STATE["expense_id"]))


def test_edit_expense():
    ok(run("edit_expense", expense_id=STATE["expense_id"], updates={"name": f"MCP expense edited {STAMP}"}))


def test_delete_expense():
    ok(run("delete_expense", expense_id=STATE["expense_id"]))


def test_delete_invoices():
    ok(run("delete_invoice", invoice_id=STATE["repeat_id"]))
    ok(run("delete_invoice", invoice_id=STATE["invoice_id"]))


def test_delete_client():
    ok(run("delete_client", client_id=STATE["client_id"]))
