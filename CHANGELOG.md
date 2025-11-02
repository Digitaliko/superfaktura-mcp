# Changelog

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
