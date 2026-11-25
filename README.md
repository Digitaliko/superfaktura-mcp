# SuperFaktura MCP Server

[![PyPI](https://img.shields.io/pypi/v/superfaktura-mcp)](https://pypi.org/project/superfaktura-mcp/)
[![License](https://img.shields.io/github/license/Digitaliko/superfaktura-mcp)](LICENSE)
[![Glama score](https://glama.ai/mcp/servers/Digitaliko/superfaktura-mcp/badges/score.svg)](https://glama.ai/mcp/servers/Digitaliko/superfaktura-mcp)

Model Context Protocol (MCP) server for SuperFaktura invoicing system. Enables AI assistants to interact with SuperFaktura API for managing invoices, clients, and expenses.

**Author:** [@filippofilip95](https://github.com/filippofilip95), [Digitaliko](https://www.digitaliko.com)

<a href="https://glama.ai/mcp/servers/Digitaliko/superfaktura-mcp"><img width="380" height="200" src="https://glama.ai/mcp/servers/Digitaliko/superfaktura-mcp/badge" alt="SuperFaktura MCP server on Glama" /></a>

<!-- mcp-name: io.github.Digitaliko/superfaktura-mcp -->

---

## Features

- **Invoice Management** - Create, list, edit, delete, send invoices with 40+ parameters
- **Client Management** - Full CRUD operations with 30+ fields
- **Expense Management** - Complete expense tracking with file attachments
- **Advanced Filtering** - 25+ filter options for invoices, comprehensive search across all resources
- **Field Filtering** - Extract specific fields as tabular data (array of arrays) for easy processing
- **Safe by default** - Tools carry MCP read-only/destructive hints; `SUPERFAKTURA_READ_ONLY=1` exposes only the read tools; deleting and emailing ask the agent to confirm with you first
- **Runs locally** - stdio server on your computer, one SuperFaktura account per server (no hosted/HTTP mode in 0.1.0)

---

## Quick Start

### 1. Install

You need [uv](https://docs.astral.sh/uv/) (macOS: `brew install uv`, others: `curl -LsSf https://astral.sh/uv/install.sh | sh`). Then `uvx superfaktura-mcp` downloads and runs the server; step 3 does this for you. From source:

```bash
git clone https://github.com/Digitaliko/superfaktura-mcp.git
cd superfaktura-mcp
uv run server.py        # or: pip install -r requirements.txt && python server.py
```

### 2. Get API Credentials

1. Log in to [SuperFaktura](https://moja.superfaktura.sk)
2. Go to **Tools** → **API**
3. Copy your API key

### 3. Configure Claude Desktop

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "superfaktura": {
      "command": "uvx",
      "args": ["superfaktura-mcp"],
      "env": {
        "SUPERFAKTURA_EMAIL": "your-email@example.com",
        "SUPERFAKTURA_API_KEY": "your-api-key-here",
        "SUPERFAKTURA_COUNTRY": "sk"
      }
    }
  }
}
```

Claude Desktop does not read your shell's PATH: if it cannot start the server, replace `"uvx"` with the full path that `which uvx` prints (for example `/opt/homebrew/bin/uvx`).

Restart Claude Desktop after configuration. From a source checkout use `"command": "python3", "args": ["/absolute/path/to/superfaktura-mcp/server.py"]` instead.

Claude Code: `claude mcp add superfaktura -e SUPERFAKTURA_EMAIL=you@example.com -e SUPERFAKTURA_API_KEY=your-key -- uvx superfaktura-mcp`

Optional: `"SUPERFAKTURA_COMPANY_ID"` for accounts with several companies, `"SUPERFAKTURA_READ_ONLY": "1"` to let the assistant only read.

Try it first against the SuperFaktura sandbox (`SUPERFAKTURA_COUNTRY=sandbox-sk`, account at [sandbox.superfaktura.sk](https://sandbox.superfaktura.sk)), not your live account.

---

## Usage Examples

**Create an invoice:**
```
Create an invoice for client ID 123 with items:
- Web design (€500)
- Hosting (€50/month)
```

**List unpaid invoices:**
```
Show me all unpaid invoices from last month with amounts over €1000
```

**Add a client:**
```
Add a new client: ACME Corp, email: billing@acme.com, IČO: 12345678
```

**Track an expense:**
```
Record an expense: Office supplies €150 from yesterday
```

**Repeat last month's invoice:**
```
Issue this month's invoice for ACME Corp with the same items as their last invoice
```

Recurring invoices (the SuperFaktura "pravidelné faktúry" feature) are not in the public SuperFaktura API, so the server cannot list, edit or create them; the prompt above is the workaround.

---

## Documentation

- **[API Reference](docs/API.md)** - Complete list of all tools and parameters
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Local and public MCP server deployment options

---

## Available Tools

### Invoices (9 tools)
`create_invoice`, `list_invoices`, `get_invoice`, `edit_invoice`, `delete_invoice`, `send_invoice`, `mark_invoice_paid`, `get_invoice_pdf`, `set_invoice_language`

### Clients (5 tools)
`create_client`, `list_clients`, `get_client`, `update_client`, `delete_client`

### Expenses (5 tools)
`create_expense`, `list_expenses`, `get_expense`, `edit_expense`, `delete_expense`

### Lookups (2 tools)
`list_expense_categories`, `list_tags`

See [API Reference](docs/API.md) for detailed documentation.

---

## Country Support

| Country | Code | URL |
|---------|------|-----|
| Slovakia | `sk` | moja.superfaktura.sk |
| Czech Republic | `cz` | moje.superfaktura.cz |
| Austria | `at` | meine.superfaktura.at |
| Sandbox (SK) | `sandbox-sk` | sandbox.superfaktura.sk |
| Sandbox (CZ) | `sandbox-cz` | sandbox.superfaktura.cz |

Tested end to end on sandbox.superfaktura.sk. CZ and AT use the URLs from the SuperFaktura docs and are not tested yet.

---

## Development

Run server:
```bash
uv run server.py
```

Tests (mocked HTTP and a stdio smoke test, no account needed):
```bash
uv run --with pytest pytest -q
```

End to end against a SuperFaktura **sandbox** account: every tool (`tests/test_sandbox.py`) and 30 user scenarios with validation cases (`tests/test_sandbox_scenarios.py`). Skipped without these vars, refuses any non-sandbox URL, deletes its test data:
```bash
SANDBOX_SUPERFAKTURA_EMAIL=... SANDBOX_SUPERFAKTURA_API_KEY=... uv run pytest tests/test_sandbox.py tests/test_sandbox_scenarios.py -v
```

Test with MCP Inspector:
```bash
npx @modelcontextprotocol/inspector python server.py
```

---

## References

Implementation based on:
- [SuperFaktura Official API Client](https://github.com/superfaktura/apiclient)
- [SuperFaktura REST API Docs](https://github.com/superfaktura/docs)
- [OpenAPI Specification](https://github.com/xseman/superfaktura.openapi) by [@xseman](https://github.com/xseman)

---

## License

Apache-2.0, see [LICENSE](LICENSE).

## Contributing

Contributions welcome. Submit issues or pull requests for improvements.

## About

Built and maintained by [Digitaliko](https://www.digitaliko.com). How we design MCP servers like this one: [How to build an MCP server](https://www.digitaliko.com/blog/how-to-build-an-mcp-server).
