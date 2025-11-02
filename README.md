# SuperFaktura MCP Server

Model Context Protocol (MCP) server for SuperFaktura invoicing system. Enables AI assistants to interact with SuperFaktura API for managing invoices, clients, and expenses.

**Author:** [@fillippofilip95](https://github.com/fillippofilip95)

---

## Features

- **Invoice Management** - Create, list, edit, delete, send invoices with 40+ parameters
- **Client Management** - Full CRUD operations with 30+ fields
- **Expense Management** - Complete expense tracking with file attachments
- **Advanced Filtering** - 25+ filter options for invoices, comprehensive search across all resources
- **Multi-tenant Support** - Deploy as public MCP server or run locally

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/digitaliko/superfaktura-mcp.git
cd superfaktura-mcp
pip install -r requirements.txt
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
      "command": "python3",
      "args": ["/absolute/path/to/superfaktura-mcp/server.py"],
      "env": {
        "SUPERFAKTURA_EMAIL": "your-email@example.com",
        "SUPERFAKTURA_API_KEY": "your-api-key-here",
        "SUPERFAKTURA_COUNTRY": "sk"
      }
    }
  }
}
```

Restart Claude Desktop after configuration.

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

---

## Development

Run server:
```bash
python server.py
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

Apache-2.0

## Contributing

Contributions welcome. Submit issues or pull requests for improvements.
