"""Every tool's HTTP method and URL checked against the SuperFaktura API docs themselves,
not against what server.py builds. The docs are pinned to one commit, so the check is stable:
https://github.com/superfaktura/docs/tree/67a95f7b55cb5dc8689bddbef082b7dc77d84f11

Needs network (raw.githubusercontent.com); skips only when the docs cannot be fetched."""

import re
import urllib.request
from functools import cache

import pytest
from test_tools import CASES

DOCS_SHA = "67a95f7b55cb5dc8689bddbef082b7dc77d84f11"
RAW = f"https://raw.githubusercontent.com/superfaktura/docs/{DOCS_SHA}/"

# tool -> (docs file, section heading)
DOCS = {
    "create_invoice": ("invoice.md", "Add invoice"),
    "list_invoices": ("invoice.md", "Get list of invoices"),
    "get_invoice": ("invoice.md", "Get invoice detail"),
    "edit_invoice": ("invoice.md", "Edit invoice"),
    "delete_invoice": ("invoice.md", "Delete invoice"),
    "send_invoice": ("invoice.md", "Send invoice via mail"),
    "mark_invoice_paid": ("invoice.md", "Pay invoice"),
    "get_invoice_pdf": ("invoice.md", "Get invoice PDF"),
    "set_invoice_language": ("invoice.md", "Set invoice language"),
    "create_client": ("clients.md", "Create client"),
    "list_clients": ("clients.md", "Get client list"),
    "get_client": ("clients.md", "View client detail"),
    "update_client": ("clients.md", "Edit client"),  # PATCH
    "delete_client": ("clients.md", "Delete client"),  # DELETE
    "create_expense": ("expenses.md", "Add expense"),
    "list_expenses": ("expenses.md", "Get list of expenses"),
    "get_expense": ("expenses.md", "Expense detail"),
    "edit_expense": ("expenses.md", "Edit expense"),
    "delete_expense": ("expenses.md", "Delete expense"),
    "list_expense_categories": ("value-lists.md", "Expense categories"),
    "list_tags": ("tags.md", "Get list of tags"),
}

# Where the code knowingly differs from the docs' **URL** line, and why. The method always matches.
KNOWN = {
    # clients.md documents /clients/view/{ID}; the .json suffix is the form every other
    # view endpoint documents and it returns the same JSON (sandbox suite).
    "get_client": "clients/view/3.json",
    # expenses.md's URL line says /expense/view/{ID}.json, but its own curl example and the
    # sandbox both use /expenses/view/{ID}.json; the URL line is a typo in the docs.
    "get_expense": "expenses/view/5.json",
}


@cache
def docs_file(name):
    try:
        with urllib.request.urlopen(RAW + name, timeout=20) as r:
            return r.read().decode("utf-8")
    except OSError as e:
        pytest.skip(f"SuperFaktura docs not reachable: {e}")


def documented(name, heading):
    """(method, URL template) from the docs section `## <heading>`."""
    text = docs_file(name)
    start = text.index(f"\n## {heading}\n")
    end = text.find("\n## ", start + 1)
    section = text[start:end if end > 0 else None]
    url = re.search(r"\*\*URL\*\*:\s*`([^`]+)`", section).group(1)
    method = re.search(r"\*\*HTTP method:?\*\*:?\s*([A-Z]+)", section).group(1)
    return method, url


def template_regex(template):
    """Docs URL template -> regex: {X} is one segment, [...] optional, [...]* repeated."""
    out, i = "", 0
    while i < len(template):
        c = template[i]
        if c == "[":
            depth, j = 1, i + 1
            while depth:
                depth += {"[": 1, "]": -1}.get(template[j], 0)
                j += 1
            rep = "*" if template[j:j + 1] == "*" else "?"
            out += f"(?:{template_regex(template[i + 1:j - 1])}){rep}"
            i = j + (rep == "*")
        elif c == "{":
            j = template.index("}", i)
            out += "[^/]+"
            i = j + 1
        else:
            out += re.escape(c)
            i += 1
    return out


def test_every_tool_is_mapped_to_a_docs_section():
    assert sorted(DOCS) == sorted(c[0] for c in CASES)


@pytest.mark.parametrize("tool,method,path", [(c[0], c[2], c[3]) for c in CASES], ids=[c[0] for c in CASES])
def test_tool_matches_the_docs(tool, method, path):
    doc_method, doc_url = documented(*DOCS[tool])
    assert method == doc_method, f"{tool}: code {method}, docs {doc_method} ({doc_url})"
    if tool in KNOWN:
        assert path == KNOWN[tool]
        return
    pattern = template_regex(doc_url.lstrip("/"))
    if path.endswith("/"):  # list tools: CASES holds the prefix with a trailing slash
        assert re.fullmatch(pattern, path.rstrip("/")), f"{tool}: {path} vs docs {doc_url}"
    else:
        assert re.fullmatch(pattern, path), f"{tool}: {path} vs docs {doc_url}"


def test_template_regex():
    assert re.fullmatch(template_regex("[{LANGUAGE}/]invoices/pdf/{ID}/token:{T}[/{P}:{V}]*"),
                        "eng/invoices/pdf/7/token:abc")
    assert not re.fullmatch(template_regex("clients/edit/{ID}"), "clients/edit/3/x")
