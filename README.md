# SuperFaktura MCP Server

Model Context Protocol (MCP) server for SuperFaktura invoicing system. Enables AI assistants to interact with SuperFaktura API for invoice management, client operations, and expense tracking.

**Author:** [@fillippofilip95](https://github.com/fillippofilip95)

## Features

### Invoice Management
- `create_invoice` - Create invoices with comprehensive options (40+ parameters including items, payment details, delivery info, VAT settings, advanced objects)
- `list_invoices` - List and filter invoices with advanced filtering (25+ filter options including date ranges, amounts, payment types, search, tags, sorting)
- `get_invoice` - Get detailed invoice information
- `edit_invoice` - Edit existing invoices
- `delete_invoice` - Delete invoices
- `send_invoice` - Send invoices via email
- `mark_invoice_paid` - Record invoice payments
- `get_invoice_pdf` - Get invoice PDF download URL
- `set_invoice_language` - Set invoice language

### Client Management
- `create_client` - Create clients with comprehensive details (30+ fields including contact info, bank details, delivery addresses, defaults, tags)
- `list_clients` - List clients with advanced filtering (search, tags, date ranges, sorting, first letter filter)
- `get_client` - Get detailed client information
- `update_client` - Update client details
- `delete_client` - Delete clients

### Expense Management
- `create_expense` - Create expenses with full features (30+ options including items, multiple VAT rates, attachments, client data)
- `list_expenses` - List expenses with comprehensive filtering (amount ranges, categories, dates, status, payment types, search)
- `get_expense` - Get detailed expense information
- `edit_expense` - Edit existing expenses
- `delete_expense` - Delete expenses

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

**Custom API URL (optional):**
For sandbox or custom environments, you can override the country-based URL:
```
SUPERFAKTURA_API_URL=https://sandbox.superfaktura.sk
```

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

For sandbox environment:
```json
{
  "mcpServers": {
    "superfaktura": {
      "command": "python3",
      "args": ["/absolute/path/to/superfaktura-mcp/server.py"],
      "env": {
        "SUPERFAKTURA_EMAIL": "your-email@example.com",
        "SUPERFAKTURA_API_KEY": "your-api-key-here",
        "SUPERFAKTURA_API_URL": "https://sandbox.superfaktura.sk"
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

**List recent invoices with advanced filtering:**
```
Show me all unpaid invoices from last month with amounts over €1000
List invoices by payment type 'transfer' sorted by amount
Search invoices containing 'Project Alpha'
```

**Create a new client:**
```
Add a new client: ACME Corp, email: billing@acme.com, IČO: 12345678
```

**Track an expense:**
```
Record an expense: Office supplies €150 from yesterday
Create an expense with attachment from a PDF file
Add expense with multiple VAT rates
```

**Advanced operations:**
```
Edit invoice 456 to update payment terms
Get PDF download link for invoice 789
Delete expired proforma invoice 321
Search clients by first letter 'A'
Filter expenses by category and amount range
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

## Advanced Features

### Invoice Filtering & Sorting
The `list_invoices` tool supports comprehensive filtering:
- **Pagination**: Up to 200 items per page
- **Time filters**: created_since/to, modified_since/to, delivery_since/to, paydate_since/to
- **Amount filters**: amount_from, amount_to
- **Type filters**: type (proforma, regular, etc.), status, payment_type, delivery_type
- **Search**: Base64 encoded full-text search, invoice_no_formatted, order_no, variable
- **Tags**: Filter by tag ID
- **Sorting**: direction (ASC/DESC), sort by any attribute
- **Exclusions**: ignore (exclude specific invoice IDs)

### Client Filtering & Sorting
The `list_clients` tool supports:
- **Search**: Base64 encoded search across 18+ fields (name, ICO, DIC, IC_DPH, bank_account, email, address, city, zip, phone, fax, comment, tags, UUID)
- **Char filter**: Filter by first letter of client name
- **UUID search**: Search by exact UUID
- **Time filters**: created_since/to, modified_since/to
- **Tags**: Filter by tag ID
- **Sorting**: direction, sort by any attribute

### Expense Filtering & Sorting
The `list_expenses` tool supports:
- **Pagination**: Up to 100 items per page
- **Amount filters**: amount_from, amount_to
- **Category filter**: Expense category ID
- **Time filters**: created_since/to, modified_since/to, delivery_since/to
- **Type filters**: status, type, payment_type
- **Search**: Base64 encoded search
- **Sorting**: direction, sort by any attribute

### Invoice Creation Options
The `create_invoice` tool supports 40+ parameters including:
- **Payment details**: payment_type, already_paid, paydate, deposit
- **Delivery**: delivery_date, delivery_type
- **Discounts**: discount (%), discount_total (nominal)
- **Symbols**: variable_symbol, constant_symbol, specific_symbol
- **Comments**: comment, header_comment, internal_comment
- **Issuer info**: issued_by, issued_by_email, issued_by_phone, issued_by_web
- **Advanced**: bank_accounts, invoice_currency, rounding, vat_transfer
- **Document linking**: estimate_id, proforma_id, parent_id
- **Settings**: InvoiceSetting object (language, signature, payment_info, online_payment, bysquare, paypal)
- **Extras**: InvoiceExtra, MyData objects

### Client Creation Options
The `create_client` tool supports 30+ fields including:
- **Contact**: email, phone, fax
- **Address**: address, city, zip_code, country, country_id
- **Bank**: bank_account, bank_code, iban, swift
- **Tax**: ico, dic, ic_dph
- **Delivery address**: delivery_name, delivery_address, delivery_city, delivery_zip, delivery_country
- **Defaults**: currency, default_variable, discount, due_date
- **Other**: uuid, tags, comment

### Expense Creation Options
The `create_expense` tool supports 30+ options including:
- **Multiple VAT rates**: amount, vat, amount2, vat2, amount3, vat3
- **Symbols**: variable_symbol, constant_symbol, specific_symbol
- **Dates**: expense_date, delivery_date, due_date, taxable_supply
- **Attachment**: Base64 encoded file (max 4MB, 15+ file types)
- **Items**: expense_items array for itemized expenses
- **Extras**: ExpenseExtra object (vat_transfer)
- **Client**: client_data object to create/update client with expense

## API Reference

Implementation based on:
- [SuperFaktura Official PHP API Client](https://github.com/superfaktura/apiclient)
- [SuperFaktura REST API Documentation](https://github.com/superfaktura/docs)
- [Community OpenAPI Specification](https://github.com/xseman/superfaktura.openapi) by [@xseman](https://github.com/xseman)

### API Coverage

This MCP server implements comprehensive SuperFaktura API features:
- ✅ **Invoice CRUD**: Create, Read, Update, Delete with 40+ parameters
- ✅ **Client CRUD**: Create, Read, Update, Delete with 30+ fields
- ✅ **Expense CRUD**: Create, Read, Update, Delete with 30+ options
- ✅ **Advanced filtering**: 25+ filters for invoices, comprehensive search for all resources
- ✅ **PDF generation**: Get invoice PDF download URLs
- ✅ **File attachments**: Base64 upload for expense attachments
- ✅ **Multi-language**: Invoice language settings
- ✅ **Payment tracking**: Mark invoices as paid, send via email

## License

Apache-2.0

## Author

Created by [@fillippofilip95](https://github.com/fillippofilip95)

## Contributing

Contributions welcome. Submit issues or pull requests for improvements.
