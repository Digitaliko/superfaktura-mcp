# Changelog

## [0.1.0] - 2026-11-27

First tagged release and first PyPI package. The 1.0.0 and 2.0.0 entries below were
internal milestones before the package was versioned.

### Added
- `uvx superfaktura-mcp`: console script, PyPI metadata, `server.json` for the official MCP Registry
- Tests: every tool against mocked HTTP, a stdio smoke test that lists the tools, and an
  end-to-end suite against a SuperFaktura sandbox account (`tests/test_sandbox.py`)
- CI on Python 3.10 and 3.12
- PyPI release from a published GitHub release with Trusted Publishing (`.github/workflows/publish.yml`)
- The server reports its own version (`serverInfo.version` 0.1.0), not fastmcp's
- `send_invoice`: `pdf_language`
- `list_expense_categories`, `list_tags`
- `create_client` refuses an empty name with a readable error (SuperFaktura returns an empty error list)

### Fixed (aligned with https://github.com/superfaktura/docs)
- `send_invoice` sent `{"Invoice": ...}`; the API expects `{"Email": {"invoice_id", "to"}}`.
  `email` is now required (never guessed)
- `get_invoice_pdf` called `invoices/pdf/{id}` without the required token and parsed the PDF
  as JSON; it now reads the token, downloads the PDF and saves it to a file
- `set_invoice_language`: `GET invoices/setinvoicelanguage/{id}/lang:{lang}` (was a POST body)
- `mark_invoice_paid`: `invoice_payments/add/ajax:1/api:1`
- `delete_invoice`, `delete_expense`: GET, as documented (were DELETE)
- `SuperFakturaClient()` without arguments ignored `SUPERFAKTURA_COUNTRY`
- `mark_invoice_paid` and `get_invoice_pdf` accept an invoice only when the API returns an `Invoice`
  object; a body without `error` but without an invoice is a failure, not success (before, a payment
  could be posted for an invoice the API did not return)
- Every tool's HTTP method and URL is checked by a test against the docs at a pinned commit
  (`tests/test_docs.py`); `update_client` is PATCH and `delete_client` is DELETE, as clients.md documents
- `list_invoices` status values per the docs (1 issued, 2 partially paid, 3 paid, 99 overdue)

### Security and safety (pre-release review)
- Text from the model can no longer shape request URLs: every `key:value` path segment is
  percent-encoded and languages are checked against the 14 documented codes (before, a crafted
  `language` could turn the PDF call into `GET /invoices/delete/...`)
- MCP annotations on all 21 tools (read-only / destructive); `SUPERFAKTURA_READ_ONLY=1` leaves out
  the 12 write tools (9 tools remain), decided when the server starts (a `.env` counts), never on import; delete tools say PERMANENT; `send_invoice` needs an explicit recipient
- No HTTP mode: `--http` is refused, `PORT` no longer switches transport, and the dead per-request
  credential path is gone (it was never reachable through fastmcp's Context)
- `.env` is read only when the server is started, never on import
- The PDF is saved with `mkstemp` (private file, invoice id and language in the name)

### Changed
- `search` takes plain text and encodes it as the docs require (base64 with `-_,`)
- `list_invoices`: an invoice number containing `/` is looked up through search (the path filter never matches it)
- `mark_invoice_paid`: `payment_type` and `currency` (defaults to the invoice's currency); sends the payment date
- HTTP errors return the status, the first 500 characters of the body and `X-RateLimit-Message`; HTTP 429 is retried twice with a short backoff
- `SUPERFAKTURA_COUNTRY` is case-insensitive; the missing-credentials error is one line

### Removed
- `jsonpath-ng` (unused) and `uvicorn` (HTTP mode removed)

### Dependencies and supply chain
- `fastmcp>=2.11.3,<3`: with fastmcp 3 or newer (what a fresh `uvx` or `pip install` resolved to),
  `SUPERFAKTURA_READ_ONLY=1` crashed at start (`FastMCP.remove_tool` is gone). CI's wheel smoke
  test now also starts the server in read-only mode with freshly resolved dependencies
- The floor was `2.6.0`, which never worked with today's dependencies: fastmcp before 2.11.3 does
  not bound `mcp` below 2 and fails at import. CI now also runs the tests at the lowest declared
  versions (`--resolution lowest-direct`)
- `uv.lock` upgraded within that range (fastmcp 2.14.7, mcp 1.30, cryptography 50, urllib3 2.8,
  certifi 2026.11.20, starlette 1.x, ...): 45 baselined critical/high advisories down to 4, each
  re-triaged as not reachable in this server (fastmcp OpenAPI provider and OAuth proxy, dnspython on
  Python 3.10 only) in `security-allowlist.json`, expiring 2027-01-15
- CycloneDX SBOM, `SECURITY.md` and a pinned OSV dependency scan in CI (#8)

## [2.0.0] - 2025-11-02

### Major Enhancements

This release implements comprehensive SuperFaktura API coverage based on official documentation analysis.

### Added - Invoice Operations

#### List Invoices (Enhanced)
- ✅ Increased pagination from 100 to 200 items per page
- ✅ Added `direction` and `sort` parameters for flexible sorting
- ✅ Added `type` filter with multi-value support (e.g., 'regular|proforma')
- ✅ Added `listinfo` parameter for metadata
- ✅ Added comprehensive time-based filters:
  - `created_since`, `created_to`
  - `modified_since`, `modified_to`
  - `delivery_since`, `delivery_to`
  - `paydate_since`, `paydate_to`
- ✅ Added amount filters: `amount_from`, `amount_to`
- ✅ Added business filters:
  - `payment_type`, `delivery_type`
  - `invoice_no_formatted`, `order_no`, `variable`
  - `search` (base64 encoded full-text)
  - `tag` (filter by tag ID)
  - `ignore` (exclude specific invoice IDs)

#### Create Invoice (Enhanced)
Added 40+ optional parameters:
- ✅ Payment details: `payment_type`, `already_paid`, `paydate`, `deposit`
- ✅ Delivery: `delivery_date`, `delivery_type`
- ✅ Discounts: `discount`, `discount_total`
- ✅ Symbols: `constant_symbol`, `specific_symbol`
- ✅ Comments: `comment`, `header_comment`, `internal_comment`
- ✅ Issuer: `issued_by`, `issued_by_email`, `issued_by_phone`, `issued_by_web`
- ✅ Advanced: `bank_accounts`, `invoice_currency`, `rounding`, `vat_transfer`
- ✅ Linking: `estimate_id`, `proforma_id`, `parent_id`
- ✅ Settings: `invoice_setting` object (language, signature, payment_info, etc.)
- ✅ Extras: `invoice_extra`, `my_data` objects

#### New Invoice Operations
- ✅ `edit_invoice` - Edit existing invoices
- ✅ `delete_invoice` - Delete invoices
- ✅ `get_invoice_pdf` - Get PDF download URL with language support
- ✅ `set_invoice_language` - Set invoice language

### Added - Client Operations

#### List Clients (Enhanced)
- ✅ Added `direction` and `sort` parameters
- ✅ Added `listinfo` for metadata
- ✅ Added comprehensive filters:
  - `char_filter` - filter by first letter of name
  - `search` - base64 encoded search across 18+ fields
  - `search_uuid` - exact UUID search
  - `tag` - filter by tag ID
  - `created_since`, `created_to`
  - `modified_since`, `modified_to`

#### Create Client (Enhanced)
Added 30+ fields:
- ✅ Extended contact: `fax`
- ✅ Bank details: `bank_code`, `iban`, `swift`
- ✅ Tax: `ic_dph`, `country_id`
- ✅ Delivery address: `delivery_name`, `delivery_address`, `delivery_city`, `delivery_zip`, `delivery_country`, `delivery_country_id`, `delivery_phone`
- ✅ Defaults: `currency`, `default_variable`, `discount`, `due_date`
- ✅ Other: `uuid`, `tags`, `comment`, `match_address`, `update`

#### New Client Operations
- ✅ `delete_client` - Delete clients

### Added - Expense Operations

#### List Expenses (Enhanced - BREAKING CHANGE)
- ⚠️ **BREAKING**: Renamed `from_date`/`to_date` to `created_since`/`created_to` (matches API spec)
- ✅ Added `direction` and `sort` parameters
- ✅ Added `listinfo` for metadata
- ✅ Added comprehensive filters:
  - `amount_from`, `amount_to`
  - `category` - expense category ID
  - `client_id`
  - `status`, `type`, `payment_type`
  - `search` - base64 encoded search
  - Time filters: `created_since/to`, `modified_since/to`, `delivery_since/to`
  - `due` - due date filter

#### Create Expense (Enhanced)
Added 30+ optional parameters:
- ✅ Multiple VAT rates: `amount2`, `vat2`, `amount3`, `vat3`
- ✅ Symbols: `variable_symbol`, `constant_symbol`, `specific_symbol`
- ✅ Dates: `delivery_date`, `due_date`, `taxable_supply`
- ✅ Advanced: `client_id`, `already_paid`, `document_number`, `payment_type`, `type`, `version`
- ✅ **Attachment support**: `attachment` (base64 encoded, max 4MB, 15+ file types)
- ✅ Itemized expenses: `expense_items` array
- ✅ Extras: `expense_extra` object (vat_transfer)
- ✅ Client creation: `client_data` object

#### New Expense Operations
- ✅ `edit_expense` - Edit existing expenses
- ✅ `delete_expense` - Delete expenses

### Breaking Changes

#### list_expenses Parameter Rename
- **Old**: `from_date`, `to_date`
- **New**: `created_since`, `created_to`
- **Reason**: Align with official SuperFaktura API specification
- **Migration**: Update any code using `from_date`/`to_date` to use `created_since`/`created_to`

### Documentation

- ✅ Updated README with comprehensive feature documentation
- ✅ Added "Advanced Features" section with detailed filter documentation
- ✅ Added "API Coverage" section showing implemented features
- ✅ Updated example commands with advanced scenarios
- ✅ Enhanced tool descriptions with all parameters

### Technical Details

- **Total new parameters**: 100+ across all operations
- **New operations**: 6 (edit_invoice, delete_invoice, get_invoice_pdf, set_invoice_language, delete_client, edit_expense, delete_expense)
- **Enhanced operations**: 6 (list_invoices, create_invoice, list_clients, create_client, list_expenses, create_expense)
- **Code quality**: All changes tested and validated against official API documentation

### References

Implementation verified against:
- [SuperFaktura Official PHP API Client](https://github.com/superfaktura/apiclient)
- [SuperFaktura REST API Documentation](https://github.com/superfaktura/docs)
- [Community OpenAPI Specification](https://github.com/xseman/superfaktura.openapi)

## [1.0.0] - Initial Release

- Basic invoice management (create, list, get, send, mark paid)
- Basic client management (create, list, get, update)
- Basic expense management (create, list, get)
- Country-based API URL configuration
- Custom API URL support for sandbox environments
