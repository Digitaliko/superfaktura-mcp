# SuperFaktura MCP - API Reference

Complete reference for all available MCP tools.

## Invoice Operations

### create_invoice

Create a new invoice with comprehensive options.

**Required parameters:**
- `client_id` (int) - ID of the client to invoice
- `name` (str) - Invoice name/description
- `invoice_items` (list) - List of items, each with: `name`, `description`, `unit_price`, `quantity`, `tax`

**Optional parameters (40+):**
- **Basic**: `issued_date`, `due_date`, `variable_symbol`, `payment_type`, `order_no`
- **Comments**: `comment`, `header_comment`, `internal_comment`
- **Delivery**: `delivery_date`, `delivery_type`
- **Payment**: `already_paid`, `paydate`, `deposit`
- **Discounts**: `discount` (%), `discount_total` (nominal)
- **Symbols**: `constant_symbol`, `specific_symbol`
- **Currency**: `invoice_currency`
- **Issuer**: `issued_by`, `issued_by_email`, `issued_by_phone`, `issued_by_web`
- **Advanced**: `bank_accounts`, `rounding`, `vat_transfer`, `tax_document`
- **Numbering**: `invoice_no_formatted`, `sequence_id`
- **Document linking**: `estimate_id`, `proforma_id`, `parent_id`
- **Settings**: `invoice_setting` (language, signature, payment_info, online_payment, bysquare, paypal)
- **Extras**: `invoice_extra`, `my_data`
- **Email**: `mark_sent`, `mark_sent_message`, `mark_sent_subject`
- **Other**: `add_rounding_item`, `logo_id`, `type`

### list_invoices

List and filter invoices with advanced options.

**Pagination:**
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 50, max: 200) - Items per page
- `listinfo` (int, default: 1) - Include metadata

**Sorting:**
- `direction` (str, default: "DESC") - ASC or DESC
- `sort` (str, default: "regular_count") - Attribute to sort by

**Filters:**
- **Type**: `type` (proforma, regular, etc. - use `|` for multiple)
- **Status**: `status` (1=draft, 2=sent, 3=paid, 99=cancelled - use `|` for multiple)
- **Client**: `client_id`
- **Time ranges**:
  - `created_since`, `created_to`
  - `modified_since`, `modified_to`
  - `delivery_since`, `delivery_to`
  - `paydate_since`, `paydate_to`
- **Amount**: `amount_from`, `amount_to`
- **Payment/Delivery**: `payment_type`, `delivery_type` (use `|` for multiple)
- **Search**:
  - `invoice_no_formatted` - Invoice number
  - `order_no` - Order number
  - `variable` - Variable symbol
  - `search` - Base64 encoded full-text search
- **Tags**: `tag` - Tag ID
- **Exclusions**: `ignore` - Invoice IDs to exclude (use `|` separator)

### get_invoice

Get detailed information about a specific invoice.

**Parameters:**
- `invoice_id` (int) - Invoice ID

**Returns:** Invoice details including items, client info, payment status

### edit_invoice

Edit an existing invoice.

**Parameters:**
- `invoice_id` (int) - Invoice ID
- `updates` (dict) - Fields to update (same structure as create_invoice)

**Supported updates:**
- `Invoice` object fields
- `InvoiceItem` array
- `InvoiceSetting` object
- `InvoiceExtra` object
- `Client` object

### delete_invoice

Delete an invoice.

**Parameters:**
- `invoice_id` (int) - Invoice ID

### send_invoice

Send invoice via email.

**Parameters:**
- `invoice_id` (int) - Invoice ID
- `email` (str, optional) - Override email address (uses client email by default)

### mark_invoice_paid

Mark invoice as paid by recording a payment.

**Parameters:**
- `invoice_id` (int) - Invoice ID
- `amount` (float) - Payment amount
- `payment_date` (str, optional) - Payment date (YYYY-MM-DD), defaults to today

### get_invoice_pdf

Get invoice PDF download URL and metadata.

**Parameters:**
- `invoice_id` (int) - Invoice ID
- `language` (str, optional) - Language code (eng, slo, cze, deu, etc.)

### set_invoice_language

Set invoice language.

**Parameters:**
- `invoice_id` (int) - Invoice ID
- `language` (str) - Language code (eng, slo, cze, deu, hun, pol, rom, rus, ukr, hrv)

---

## Client Operations

### create_client

Create a new client with comprehensive details.

**Required parameters:**
- `name` (str) - Client/company name

**Optional parameters (30+):**
- **Contact**: `email`, `phone`, `fax`
- **Address**: `address`, `city`, `zip_code`, `country`, `country_id`
- **Tax IDs**: `ico`, `dic`, `ic_dph`
- **Banking**: `bank_account`, `bank_code`, `iban`, `swift`
- **Delivery address**: `delivery_name`, `delivery_address`, `delivery_city`, `delivery_zip`, `delivery_country`, `delivery_country_id`, `delivery_phone`
- **Defaults**: `currency`, `default_variable`, `discount`, `due_date`
- **Other**: `comment`, `uuid`, `tags`, `match_address`, `update`

### list_clients

List clients with filtering and sorting.

**Pagination:**
- `page` (int, default: 1)
- `per_page` (int, default: 50)
- `listinfo` (int, default: 1)

**Sorting:**
- `direction` (str, default: "DESC")
- `sort` (str, default: "regular_count")

**Filters:**
- `char_filter` - Filter by first letter of client name (use `#` for non-letters)
- `search` - Base64 encoded search (searches across: name, ICO, DIC, IC_DPH, bank_account, email, address, city, zip, state, country, phone, fax, comment, tags, UUID)
- `search_uuid` - Search by exact UUID
- `tag` - Tag ID
- **Time ranges**:
  - `created_since`, `created_to`
  - `modified_since`, `modified_to`

### get_client

Get detailed information about a specific client.

**Parameters:**
- `client_id` (int) - Client ID

**Returns:** Client details including contact information and invoice history

### update_client

Update client information.

**Parameters:**
- `client_id` (int) - Client ID
- `updates` (dict) - Fields to update (name, email, phone, address, etc.)

### delete_client

Delete a client.

**Parameters:**
- `client_id` (int) - Client ID

---

## Expense Operations

### create_expense

Create a new expense record with full features.

**Required parameters:**
- `name` (str) - Expense name

**Optional parameters (30+):**
- **Basic**: `amount`, `vat`, `expense_date`, `currency`, `expense_category_id`, `comment`
- **Symbols**: `variable_symbol`, `constant_symbol`, `specific_symbol`
- **Multiple VAT rates** (for version: basic):
  - `amount2`, `vat2`
  - `amount3`, `vat3`
- **Dates**: `delivery_date`, `due_date`, `taxable_supply`
- **Payment**: `client_id`, `already_paid`, `payment_type`
- **Document**: `document_number`, `type`, `version`
- **Attachment**: `attachment` - Base64 encoded file (max 4MB, supported formats: jpg, jpeg, png, tif, tiff, gif, pdf, tmp, xls, xlsx, ods, doc, docx, xml, csv, msg, heic, isdoc)
- **Advanced objects**:
  - `expense_items` - List of items (for version: items)
  - `expense_extra` - Extra settings (vat_transfer)
  - `client_data` - Create/update client with expense

### list_expenses

List expenses with comprehensive filtering.

**Pagination:**
- `page` (int, default: 1)
- `per_page` (int, default: 50, max: 100)
- `listinfo` (int, default: 1)

**Sorting:**
- `direction` (str, default: "DESC")
- `sort` (str, default: "regular_count")

**Filters:**
- **Amount**: `amount_from`, `amount_to`
- **Category**: `category` - Expense category ID
- **Client**: `client_id`
- **Time ranges**:
  - `created_since`, `created_to`
  - `modified_since`, `modified_to`
  - `delivery_since`, `delivery_to`
- **Other**:
  - `due` - Due date (YYYY-MM-DD)
  - `payment_type`
  - `search` - Base64 encoded search
  - `status` - Use `|` for multiple
  - `type`

### get_expense

Get detailed information about a specific expense.

**Parameters:**
- `expense_id` (int) - Expense ID

**Returns:** Expense details

### edit_expense

Edit an existing expense.

**Parameters:**
- `expense_id` (int) - Expense ID
- `updates` (dict) - Fields to update (same structure as create_expense)

**Supported updates:**
- `Expense` object fields
- `ExpenseItem` array
- `ExpenseExtra` object
- `Client` object

### delete_expense

Delete an expense.

**Parameters:**
- `expense_id` (int) - Expense ID

---

## Data Formats

### Dates
All dates use format: `YYYY-MM-DD`

### Base64 Search
When providing base64 encoded search strings, replace special characters:
- `+` → `-`
- `/` → `_`
- `=` → `,`

### Multiple Values
Use `|` as separator for multiple values (e.g., `type:regular|proforma`)

---

## API Coverage

This MCP server implements comprehensive SuperFaktura API features:
- ✅ **Invoice CRUD**: Create, Read, Update, Delete with 40+ parameters
- ✅ **Client CRUD**: Create, Read, Update, Delete with 30+ fields
- ✅ **Expense CRUD**: Create, Read, Update, Delete with 30+ options
- ✅ **Advanced filtering**: 25+ filters for invoices, comprehensive search for all resources
- ✅ **PDF generation**: Get invoice PDF download URLs
- ✅ **File attachments**: Base64 upload for expense attachments
- ✅ **Multi-language**: Invoice language settings
- ✅ **Payment tracking**: Mark invoices as paid, send via email

---

## References

- [SuperFaktura Official PHP API Client](https://github.com/superfaktura/apiclient)
- [SuperFaktura REST API Documentation](https://github.com/superfaktura/docs)
- [Community OpenAPI Specification](https://github.com/xseman/superfaktura.openapi) by [@xseman](https://github.com/xseman)
