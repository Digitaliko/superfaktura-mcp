# superfaktura-mcp v0.1.0: tools aligned with the SuperFaktura docs, uvx package, tests, registry files

> [!IMPORTANT]
> 6 of 19 tools called the API wrong (wrong URL, method or body) and are fixed against mocked HTTP; none is proven against a live SuperFaktura yet, because the sandbox keys are not in `~/.secrets.env`. Publishing to PyPI and the MCP Registry is ready and waits for Filip.

## Decide
### Needs you
- **OSS5b · Add the sandbox keys, then run the sandbox suite**
  - Why: the end-to-end run (every tool against sandbox.superfaktura.sk) is skipped without them.
  - Answer: `OSS5ba` keys added, run it / `OSS5bb` skip the live run for v0.1.0 -> `OSS5ba`
- **OSS5c · Publish to PyPI and the MCP Registry**
  - Why: a publish is public and one-way, so it is yours to run.
  - Goes out: PyPI `superfaktura-mcp` 0.1.0 and registry.modelcontextprotocol.io `io.github.Digitaliko/superfaktura-mcp`, public
  - Answer: `OSS5ca` publish after the sandbox run / `OSS5cb` publish now on the mocked tests -> `OSS5ca`

### FYI
- **OSS5 · Recurring invoices are not in the public API** The docs show only a `recurring` field on invoices, with no endpoint to list, edit or create recurring invoices.

## What happened
- Every tool's URL, method and body checked against https://github.com/superfaktura/docs. 6 tools did not match. They are fixed and each has a mocked test.
- `uvx superfaktura-mcp` works: added a console script and PyPI metadata, removed the unused `jsonpath-ng`, and `requirements.txt` now matches `pyproject.toml` (a test checks it).
- Tests: a mocked HTTP case per tool, a stdio smoke test (starts the server, lists 19 tools), and `tests/test_sandbox.py` (every tool end to end, runs only with `SUPERFAKTURA_SANDBOX_*` and refuses any non-sandbox URL). CI runs them on Python 3.10 and 3.12, then builds the wheel and starts it with uvx.
- Registry: `server.json` (validated against the 2025-12-11 schema), with an `mcp-name:` line in the README. README also gained badges (PyPI, CI, license, Glama score and card) and uvx / Claude Code install steps.
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
- Green, after: `29 passed, 20 skipped` (20 skipped = the sandbox suite, no keys yet).
- `uv build` builds the sdist and wheel. `uvx --from dist/...whl superfaktura-mcp </dev/null` starts the stdio server and exits 0.
- `server.json` validates against `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`.
- No screenshots: there is no UI change, and the sandbox demo waits for the keys (OSS5b).

## Details
<details><summary>Per tool: mocked / sandbox</summary>

| tool | mocked | sandbox |
|---|---|---|
| create_invoice, list_invoices, get_invoice, edit_invoice | pass | not run (no keys) |
| send_invoice | fixed (body was `Invoice`, API wants `Email`) | not run, needs `SUPERFAKTURA_SANDBOX_SEND_TO` (sends a real email) |
| mark_invoice_paid | fixed (URL) | not run |
| get_invoice_pdf | fixed (token missing, PDF parsed as JSON) | not run |
| set_invoice_language | fixed (GET `lang:`) | not run |
| delete_invoice, delete_expense | fixed (GET, not DELETE) | not run |
| create/list/get/update/delete client | pass | not run; `clients/view/{id}.json` vs the docs' `/clients/view/{id}` still unconfirmed |
| create/list/get/edit expense | pass | not run |
</details>

<details><summary>Integration readiness (for a superfaktura.sk/integracia and .cz/integrace listing)</summary>

- Works today (mocked; live run pending): invoices (create, list with 25+ filters, detail, edit, send, pay, PDF, language, delete), clients (CRUD), expenses (CRUD with attachments). SK, CZ, AT and both sandboxes.
- Install: one line in Claude Desktop or Claude Code (`uvx superfaktura-mcp`), open source (Apache-2.0), listed on Glama.
- Demo prompts for the sandbox:
  1. "Create a client ACME s.r.o., Bratislava, email billing@acme.example"
  2. "Issue an invoice to ACME for web design 500 EUR and hosting 50 EUR, due in 14 days"
  3. "Show unpaid invoices from this month over 100 EUR"
  4. "Mark invoice <n> paid today and give me its PDF"
  5. "Record an expense: office supplies 150 EUR yesterday"
- To produce before asking: a 30 s GIF of prompts 2 to 4 in Claude Desktop against sandbox.superfaktura.sk, plus an MCP Inspector screenshot of the tool list. Both need the sandbox keys.
- Missing, worth saying openly: recurring invoices (not in the API), eInvoice/Peppol (new in the docs), value lists.
</details>
