# superfaktura-mcp v0.1.0: tools aligned with the SuperFaktura docs, uvx package, tests, registry files

> [!IMPORTANT]
> 6 of 19 tools called the API wrong (wrong URL, method or body). They are fixed, and all 18 tools that can run were proven end to end against sandbox.superfaktura.sk (19 passed, 1 skipped: send_invoice sends a real email). A user-style demo through Claude created invoice 2026019 in the sandbox. Publishing to PyPI and the MCP Registry is ready and waits for one token: `OSS5ca`.

## Decide
### Needs you
- **OSS5c · Publish to PyPI and the MCP Registry**
  - Why: a publish is public and one-way, so it is yours to run.
  - Goes out: PyPI `superfaktura-mcp` 0.1.0 and registry.modelcontextprotocol.io `io.github.Digitaliko/superfaktura-mcp`, public
  - Answer: `OSS5ca` publish 0.1.0 now (the sandbox run is green) / `OSS5cb` wait -> `OSS5ca`

### FYI
- **OSS5d · Demo data stays in the sandbox** Client "Demo s.r.o." (id 104114) and invoice 2026019 "MCP demo (test data)" are kept for you to look at. The suite's own test data deletes itself.
- **OSS5 · Recurring invoices are not in the public API** The docs show only a `recurring` field on invoices, with no endpoint to list, edit or create recurring invoices.

## What happened
- Every tool's URL, method and body checked against the SuperFaktura docs (https://github.com/superfaktura/docs). 6 tools did not match. They are fixed and each has a mocked test.
- `uvx superfaktura-mcp` works: added a console script and PyPI metadata, removed the unused `jsonpath-ng`, and `requirements.txt` now matches `pyproject.toml` (a test checks it).
- Tests: a mocked HTTP case per tool, a stdio smoke test (starts the server, lists 19 tools), and `tests/test_sandbox.py` (every tool end to end, runs only with `SANDBOX_SUPERFAKTURA_*` and refuses any non-sandbox URL). CI runs them on Python 3.10 and 3.12, then builds the wheel and starts it with uvx.
- Sandbox: the suite passed (19 passed, 1 skipped). As a user test, `claude -p` (sonnet) got the MCP over stdio with the prompt "Vytvor faktúru pre testovacieho klienta Demo s.r.o. na 1 hodinu konzultácie za 50 EUR a potom mi ju vypíš". It searched the clients, created Demo s.r.o., created invoice 2026019 (50 EUR) and listed it back.
- Registry: `server.json` (validated against the 2025-12-11 schema), with an `mcp-name:` line in the README. README also gained badges (PyPI, license, Glama score and card; a CI badge can follow once the workflow is on main) and uvx / Claude Code install steps.
- Gaps against the docs went to repo issue `superfaktura-mcp#6` (Inbox): eInvoice/Peppol, missing invoice and expense endpoints, value lists, and the PDF tool in hosted mode.

## Change
| repo | file | what |
|---|---|---|
| Digitaliko/superfaktura-mcp | `server.py` | send_invoice body `{"Email": {invoice_id, to}}`, PDF via token + file, set_invoice_language GET `lang:`, payments `ajax:1/api:1`, deletes as GET, country default, `main()` |
| | `pyproject.toml`, `requirements.txt`, `uv.lock` | uvx script, metadata, deps in sync, no jsonpath-ng |
| | `tests/` | mocked tools, stdio smoke, sandbox suite, packaging checks |
| | `.github/workflows/ci.yml` | CI |
| | `server.json`, `README.md`, `CHANGELOG.md`, `docs/API.md` | registry entry, badges, install, 0.1.0 notes |

## Goes out
| token | channel | audience | item |
|---|---|---|---|
| OSS5c | PyPI + MCP Registry | public | package 0.1.0 and the registry entry (Filip runs it) |

Merging deploys nothing. The tag and GitHub release only publish the source.

## Proof
- Red, before the fix (`04b812e`, tests only): `9 failed, 17 passed`. Failing: delete_invoice, mark_invoice_paid, get_invoice_pdf, set_invoice_language, delete_expense endpoints, the send_invoice body (x2), the PDF file, and the country default.
- Green, after (mocked): `29 passed, 20 skipped` (20 skipped = the sandbox suite without keys).
- Sandbox, end to end: `19 passed, 1 skipped in 10.88s` (re-run after review fixes; the PDF is checked with and without the `/eng/` language prefix) (`tests/test_sandbox.py`; skipped = send_invoice).
- Demo, tool calls in order: `list_clients(search "Demo s.r.o.")` -> none, `list_clients(search "Demo")` -> none, `create_client("Demo s.r.o.")` -> id 104114, `create_invoice(client 104114, "Konzultácia" 1 x 50 EUR)` -> id 381212, number 2026019.
- Image: `01-demo-invoice-sandbox-after.jpg` (invoice 2026019 in the sandbox UI; the supplier fields are sandbox placeholders)

![Invoice 2026019 created through the MCP, in the SuperFaktura sandbox](01-demo-invoice-sandbox-after.jpg)
- `uv build` builds the sdist and wheel. `uvx --from dist/...whl superfaktura-mcp </dev/null` starts the stdio server and exits 0.
- `server.json` validates against `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`.

## Details
<details><summary>Per tool: mocked / sandbox</summary>

| tool | mocked | sandbox |
|---|---|---|
| create_invoice, list_invoices, get_invoice, edit_invoice | pass | works |
| "repeat last invoice" (get_invoice items -> create_invoice) | pass | works |
| send_invoice | fixed (body was `Invoice`, API wants `Email`) | not run: it sends a real email, set `SANDBOX_SUPERFAKTURA_SEND_TO` to run it |
| mark_invoice_paid | fixed (URL) | works |
| get_invoice_pdf | fixed (token missing, PDF parsed as JSON) | works (real `%PDF` file) |
| set_invoice_language | fixed (GET `lang:`) | works |
| delete_invoice, delete_expense | fixed (GET, not DELETE) | works |
| create/list/get/update/delete client | pass | works (`clients/view/{id}.json` is accepted) |
| create/list/get/edit expense | pass | works |
</details>

<details><summary>Integration readiness (for a superfaktura.sk/integracia and .cz/integrace listing)</summary>

- Works today (proven on sandbox.superfaktura.sk, 25. 11. 2026): invoices (create, list with 25+ filters, detail, edit, send, pay, PDF, language, delete), clients (CRUD), expenses (CRUD with attachments). SK, CZ, AT and both sandboxes.
- Install: one line in Claude Desktop or Claude Code (`uvx superfaktura-mcp`), open source (Apache-2.0), listed on Glama.
- Demo prompts for the sandbox:
  1. "Create a client ACME s.r.o., Bratislava, email billing@acme.example"
  2. "Issue an invoice to ACME for web design 500 EUR and hosting 50 EUR, due in 14 days"
  3. "Show unpaid invoices from this month over 100 EUR"
  4. "Mark invoice <n> paid today and give me its PDF"
  5. "Record an expense: office supplies 150 EUR yesterday"
- Demo shown: a Slovak prompt in Claude created client Demo s.r.o. and invoice 2026019 (screenshot above). Still to make for the listing: a 30 s screen recording of prompts 2 to 4 in Claude Desktop.
- Missing, worth saying openly: recurring invoices (not in the API), eInvoice/Peppol (new in the docs), value lists.
</details>
