"""Scenarios a user would run, against the SuperFaktura SANDBOX (skipped without
SANDBOX_SUPERFAKTURA_*). Everything created is named "MCP test <stamp>" and deleted
at the end. Validation cases assert the server returns a readable error, never raises.

Some cases come from the SlovenskaZnamka SuperFaktura client tests: errors inside an
HTTP 200 response, credit notes (type "cancel" + parent_id), and the loose
invoice_no_formatted filter.
"""

import time

import pytest

from sandbox_env import STAMP, ok, run, sandbox_env, sf_error, skip_without_sandbox  # noqa: F401

pytestmark = skip_without_sandbox

S = {"invoices": [], "clients": [], "expenses": []}
TODAY = time.strftime("%Y-%m-%d")
ICO = "5" + STAMP.replace("-", "")[-7:]  # unique 8-digit test ICO


def new_invoice(**kwargs):
    r = ok(run("create_invoice", client_id=S["client_id"], **kwargs))
    inv_id = int(r["data"]["Invoice"]["id"])
    S["invoices"].append(inv_id)
    return inv_id, r["data"]


def money(x):
    return round(float(x), 2)


# --- clients ---------------------------------------------------------------

def test_client_create_with_ids_and_address():
    r = ok(run("create_client", name=f"MCP test {STAMP} Košická Žilina s.r.o.", ico=ICO, dic="20" + ICO,
               address="Testovacia 1", city="Bratislava", zip_code="81101", email="mcp-test@example.com"))
    S["client_id"] = int(r["data"]["Client"]["id"])
    S["clients"].append(S["client_id"])


def test_client_get_by_id():
    r = ok(run("get_client", client_id=S["client_id"]))
    assert r["Client"]["ico"] == ICO


def test_client_search_by_name():
    r = ok(run("list_clients", search=f"MCP test {STAMP} Košická Žilina"))  # plain text, diacritics
    assert str(S["client_id"]) in {str(i["Client"]["id"]) for i in r["items"]}


def test_client_search_by_ico():
    r = ok(run("list_clients", search=ICO))
    assert str(S["client_id"]) in {str(i["Client"]["id"]) for i in r["items"]}


def test_client_update_address_and_email():
    ok(run("update_client", client_id=S["client_id"],
           updates={"address": "Nova 2", "city": "Kosice", "email": "mcp-test-2@example.com"}))
    c = ok(run("get_client", client_id=S["client_id"]))["Client"]
    assert (c["address"], c["city"], c["email"]) == ("Nova 2", "Kosice", "mcp-test-2@example.com")


def test_client_list_paging():
    p1 = ok(run("list_clients", page=1, per_page=1))
    p2 = ok(run("list_clients", page=2, per_page=1))
    assert len(p1["items"]) == 1 and len(p2["items"]) == 1
    assert p1["items"][0]["Client"]["id"] != p2["items"][0]["Client"]["id"]


# --- invoices --------------------------------------------------------------

def test_invoice_vat23_several_items_with_discount():
    inv_id, data = new_invoice(name=f"MCP test {STAMP} VAT 23", discount=10, invoice_items=[
        {"name": "Consulting", "unit_price": 100, "quantity": 1, "tax": 23},
        {"name": "Hosting", "unit_price": 50, "quantity": 2, "tax": 23},
    ])
    S["vat23"] = inv_id
    # 200 net, 10 % discount -> 180 net, 23 % VAT -> 221.40
    assert money(data["Invoice"]["amount"]) == 180.0
    assert money(data["Invoice"]["vat"]) == 41.4


def test_invoice_vat0_single_item():
    inv_id, data = new_invoice(name=f"MCP test {STAMP} VAT 0",
                               invoice_items=[{"name": "Training", "unit_price": 50, "quantity": 1, "tax": 0}])
    assert money(data["Invoice"]["amount"]) == 50.0 and money(data["Invoice"]["vat"]) == 0.0


def test_invoice_in_czk():
    inv_id, data = new_invoice(name=f"MCP test {STAMP} CZK", invoice_currency="CZK",
                               invoice_items=[{"name": "Licence", "unit_price": 1000, "quantity": 1, "tax": 21}])
    assert data["Invoice"]["invoice_currency"] == "CZK"


def test_invoice_get():
    r = ok(run("get_invoice", invoice_id=S["vat23"]))
    assert len(r["InvoiceItem"]) == 2
    S["vat23_items"] = r["InvoiceItem"]
    S["vat23_no"] = r["Invoice"]["invoice_no_formatted"]


def test_invoice_list_by_date_and_status():
    r = ok(run("list_invoices", client_id=S["client_id"], created_since=TODAY, created_to=TODAY,
               status="1", per_page=50))
    assert str(S["vat23"]) in {str(i["Invoice"]["id"]) for i in r["items"]}


def test_invoice_find_by_exact_number():
    # the invoice_no_formatted filter can match loosely; the exact one must be among the results
    r = ok(run("list_invoices", invoice_no_formatted=S["vat23_no"]))
    assert S["vat23_no"] in {i["Invoice"]["invoice_no_formatted"] for i in r["items"]}


def test_invoice_number_with_slash():
    number = f"MCPT/{STAMP.replace('-', '')}"
    new_invoice(name=f"MCP test {STAMP} slash number", invoice_no_formatted=number,
                invoice_items=[{"name": "x", "unit_price": 1, "quantity": 1, "tax": 0}])
    r = ok(run("list_invoices", invoice_no_formatted=number))
    assert number in {i["Invoice"]["invoice_no_formatted"] for i in r["items"]}


def test_invoice_list_multi_status():
    r = ok(run("list_invoices", client_id=S["client_id"], status="1|2", per_page=50))
    assert str(S["vat23"]) in {str(i["Invoice"]["id"]) for i in r["items"]}


def test_invoice_update_an_item():
    item = S["vat23_items"][0]
    ok(run("edit_invoice", invoice_id=S["vat23"], updates={
        "InvoiceItem": [{"id": item["id"], "name": item["name"], "unit_price": 120, "quantity": 1, "tax": 23},
                        {k: S["vat23_items"][1][k] for k in ("id", "name", "unit_price", "quantity", "tax")}]}))
    r = ok(run("get_invoice", invoice_id=S["vat23"]))
    assert 120.0 in {money(i["unit_price"]) for i in r["InvoiceItem"]}


def test_invoice_partial_then_full_payment():
    inv_id, data = new_invoice(name=f"MCP test {STAMP} payments",
                               invoice_items=[{"name": "Support", "unit_price": 100, "quantity": 1, "tax": 0}])
    ok(run("mark_invoice_paid", invoice_id=inv_id, amount=40, payment_date="2026-11-20", payment_type="cash"))
    inv = ok(run("get_invoice", invoice_id=inv_id))
    assert str(inv["Invoice"]["status"]) == "2"  # partially paid
    pay = inv["InvoicePayment"][0]
    assert pay["payment_type"] == "cash" and pay["payment_currency"] == "EUR"
    assert str(pay["created"]).startswith("2026-11-20"), pay  # the payment date we sent
    ok(run("mark_invoice_paid", invoice_id=inv_id, amount=60))
    assert str(ok(run("get_invoice", invoice_id=inv_id))["Invoice"]["status"]) == "3"  # paid


def test_invoice_proforma():
    inv_id, data = new_invoice(name=f"MCP test {STAMP} proforma", type="proforma",
                               invoice_items=[{"name": "Deposit", "unit_price": 300, "quantity": 1, "tax": 23}])
    assert data["Invoice"]["type"] == "proforma"


def test_invoice_credit_note():
    inv_id, data = new_invoice(name=f"MCP test {STAMP} credit note", type="cancel", parent_id=S["vat23"],
                               invoice_items=[{"name": "Consulting refund", "unit_price": -100, "quantity": 1, "tax": 23}])
    assert data["Invoice"]["type"] == "cancel"
    assert str(data["Invoice"]["parent_id"]) == str(S["vat23"])


def test_invoice_repeat_last_for_client():
    """Issue 5 workaround: the client's latest invoice, copied as a new one."""
    last = ok(run("list_invoices", client_id=S["client_id"], type="regular", per_page=1,
                  sort="created", direction="DESC"))["items"][0]["Invoice"]
    items = ok(run("get_invoice", invoice_id=int(last["id"])))["InvoiceItem"]
    copy = [{k: i[k] for k in ("name", "unit_price", "quantity", "tax")} for i in items]
    inv_id, data = new_invoice(name=f"MCP test {STAMP} repeat", invoice_items=copy)
    assert [i["name"] for i in data["InvoiceItem"]] == [i["name"] for i in copy]


@pytest.mark.parametrize("lang", [None, "slo", "eng"])
def test_invoice_pdf(lang):
    r = ok(run("get_invoice_pdf", invoice_id=S["vat23"], language=lang))
    with open(r["path"], "rb") as f:
        assert f.read(4) == b"%PDF"


# --- expenses --------------------------------------------------------------

def test_expense_categories_and_tags():
    ok(run("list_expense_categories"))
    ok(run("list_tags"))


def test_expense_create_list_delete():
    r = ok(run("create_expense", name=f"MCP test {STAMP} expense", amount=150, vat=23, currency="EUR",
               expense_date=TODAY))
    exp_id = int(r["data"]["Expense"]["id"])
    S["expenses"].append(exp_id)
    listed = ok(run("list_expenses", created_since=TODAY, created_to=TODAY, per_page=50))
    assert str(exp_id) in {str(i["Expense"]["id"]) for i in listed["items"]}


# --- validation: a readable error, never an exception ----------------------

def test_invalid_unknown_client_id():
    r = run("create_invoice", client_id=999999999, name=f"MCP test {STAMP} bad client",
            invoice_items=[{"name": "x", "unit_price": 1, "tax": 0}])
    if not sf_error(r):  # SuperFaktura accepted it: remember to delete
        S["invoices"].append(int(r["data"]["Invoice"]["id"]))
    assert isinstance(r, dict)


def test_invalid_missing_name_client():
    assert sf_error(run("create_client", name=""))


def test_invalid_unknown_invoice():
    r = run("get_invoice", invoice_id=999999999)
    assert isinstance(r, (dict, list))


def test_invalid_currency():
    r = run("create_invoice", client_id=S["client_id"], name=f"MCP test {STAMP} bad currency",
            invoice_currency="XXX", invoice_items=[{"name": "x", "unit_price": 1, "tax": 0}])
    if not sf_error(r):
        S["invoices"].append(int(r["data"]["Invoice"]["id"]))
    assert isinstance(r, dict)


def test_invalid_negative_expense():
    r = run("create_expense", name=f"MCP test {STAMP} negative", amount=-10, currency="EUR")
    if not sf_error(r):
        S["expenses"].append(int(r["data"]["Expense"]["id"]))
    assert isinstance(r, dict)


def test_invalid_ico_client():
    r = run("create_client", name=f"MCP test {STAMP} bad ico", ico="abc")
    if not sf_error(r):
        S["clients"].append(int(r["data"]["Client"]["id"]))
    assert isinstance(r, dict)


def test_invalid_empty_items():
    r = run("create_invoice", client_id=S["client_id"], name=f"MCP test {STAMP} no items", invoice_items=[])
    if not sf_error(r):
        S["invoices"].append(int(r["data"]["Invoice"]["id"]))
    assert isinstance(r, dict)


# --- cleanup ---------------------------------------------------------------

def test_zz_cleanup():
    for inv in reversed(S["invoices"]):
        ok(run("delete_invoice", invoice_id=inv))
    for exp in S["expenses"]:
        ok(run("delete_expense", expense_id=exp))
    for cl in S["clients"]:
        ok(run("delete_client", client_id=cl))
