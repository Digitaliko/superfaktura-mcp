# SuperFaktura MCP Server

Model Context Protocol (MCP) server for SuperFaktura invoicing system. Enables AI assistants to interact with SuperFaktura API for invoice management, client operations, and expense tracking.

**Author:** [@fillippofilip95](https://github.com/fillippofilip95)

## Features

### Invoice Management
- `create_invoice` - Create new invoices with items
- `list_invoices` - List and filter invoices by status, date, client
- `get_invoice` - Get detailed invoice information
- `send_invoice` - Send invoices via email
- `mark_invoice_paid` - Record invoice payments

### Client Management
- `create_client` - Create new clients with contact details
- `list_clients` - List all clients with pagination
- `get_client` - Get detailed client information
- `update_client` - Update client details

### Expense Management
- `create_expense` - Create expense records
- `list_expenses` - List expenses with date filtering
- `get_expense` - Get detailed expense information

## Installation

1. Clone repository:
```bash
git clone https://github.com/digitaliko/superfaktura-mcp.git
cd superfaktura-mcp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
SUPERFAKTURA_EMAIL=your-email@example.com
SUPERFAKTURA_API_KEY=your-api-key-here
SUPERFAKTURA_COUNTRY=sk
```

**Country codes:**
- `sk` - Slovakia (moja.superfaktura.sk)
- `cz` - Czech Republic (moje.superfaktura.cz)
- `at` - Austria (meine.superfaktura.at)
- `sandbox-sk` - Slovakia Sandbox
- `sandbox-cz` - Czech Republic Sandbox

## Getting API Credentials

1. Log in to your SuperFaktura account
2. Navigate to **Tools** → **API**
3. Copy your API key
4. Use your login email as `SUPERFAKTURA_EMAIL`

Refer to [SuperFaktura API documentation](https://github.com/superfaktura/docs/blob/master/intro.md#authentication) for details.

## Usage

### Claude Desktop Configuration

Add to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "superfaktura": {
      "command": "python",
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

### Example Commands

**Create an invoice:**
```
Create an invoice for client ID 123 with items:
- Web design (€500)
- Hosting (€50/month)
```

**List recent invoices:**
```
Show me all unpaid invoices from last month
```

**Create a new client:**
```
Add a new client: ACME Corp, email: billing@acme.com, IČO: 12345678
```

**Track an expense:**
```
Record an expense: Office supplies €150 from yesterday
```

## Development

Run server directly:
```bash
python server.py
```

Test with MCP inspector:
```bash
npx @modelcontextprotocol/inspector python server.py
```

## API Reference

Implementation based on:
- [SuperFaktura Official PHP API Client](https://github.com/superfaktura/apiclient)
- [SuperFaktura REST API Documentation](https://github.com/superfaktura/docs)
- [Community OpenAPI Specification](https://github.com/xseman/superfaktura.openapi) by [@xseman](https://github.com/xseman)

## License

Apache-2.0

## Author

Created by [@fillippofilip95](https://github.com/fillippofilip95)

## Contributing

Contributions welcome. Submit issues or pull requests for improvements.
